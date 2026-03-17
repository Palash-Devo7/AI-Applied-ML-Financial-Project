"""Multi-agent event forecasting service.

Pipeline:
  1. Build context (SQLite financials + historical similar events + PDF chunks)
  2. Run Bull, Bear, Macro agents in parallel via asyncio.gather
  3. Synthesizer agent produces structured forecast from all 3 views
"""
from __future__ import annotations

import asyncio
import re
import time

import structlog
from ulid import ULID

from app.models.forecast import AgentView, ForecastRequest, ForecastResponse
from app.services.embedding_service import EmbeddingService
from app.services.generation_service import GenerationService
from app.services.retrieval_service import RetrievalService

logger = structlog.get_logger(__name__)


# ── Agent system prompts ───────────────────────────────────────────────────────

BULL_SYSTEM = """You are a bullish equity analyst. Identify every reason this company will \
OUTPERFORM following the given event. Focus on upside catalysts, recovery potential, \
competitive advantages, and positive market dynamics. Cite specific numbers where available. \
Be analytical, not promotional."""

BEAR_SYSTEM = """You are a bearish risk analyst. Identify every reason this company will \
UNDERPERFORM following the given event. Focus on downside risks, structural weaknesses, \
competitive threats, and adverse dynamics. Cite specific numbers where available. \
Be analytical, not alarmist."""

MACRO_SYSTEM = """You are a macroeconomic strategist. Analyze the broader macro and sector-level \
forces at play following this company event. Consider interest rates, commodity cycles, sector \
rotation, regulatory environment, and global trade. Assess whether macro tailwinds or headwinds \
dominate for this company over the forecast horizon."""

SYNTHESIZER_SYSTEM = """You are a senior research director synthesizing analyst views into a \
balanced investment research note. Do not favor any single view. Present the full picture clearly \
and give your best judgment on the base case, bull case, and bear case outcomes."""


# ── Prompt builders ────────────────────────────────────────────────────────────

def _agent_user_prompt(
    company: str,
    event_type: str,
    event_description: str,
    horizon_days: int,
    financial_context: str,
    similar_events_text: str,
    pdf_context: str,
) -> str:
    return f"""COMPANY: {company}
EVENT TYPE: {event_type}
EVENT: {event_description}
FORECAST HORIZON: {horizon_days} days

=== FINANCIAL DATA ===
{financial_context or "No structured financial data available."}

=== SIMILAR HISTORICAL EVENTS ===
{similar_events_text or "No similar historical events in database."}

=== DOCUMENT EXCERPTS (from company filings) ===
{pdf_context or "No document excerpts available."}

=== YOUR ANALYSIS ===
Respond EXACTLY in this format:

STANCE: [BULLISH / BEARISH / NEUTRAL]
ESTIMATED_IMPACT: [e.g. +5-10% over {horizon_days} days, or -15-20%]
KEY_POINTS:
- [point 1]
- [point 2]
- [point 3]
REASONING: [2-3 sentences explaining your core thesis]"""


def _synthesizer_user_prompt(
    company: str,
    event_description: str,
    horizon_days: int,
    bull_view: str,
    bear_view: str,
    macro_view: str,
) -> str:
    return f"""Synthesize these analyst views on {company}:
Event: "{event_description}"
Horizon: {horizon_days} days

=== BULL ANALYST ===
{bull_view}

=== BEAR ANALYST ===
{bear_view}

=== MACRO ANALYST ===
{macro_view}

Respond EXACTLY in this format:

BASE_CASE: [Most likely outcome in 2-3 sentences with specific magnitude.]
BULL_CASE: [Optimistic scenario in 1-2 sentences.]
BEAR_CASE: [Pessimistic scenario in 1-2 sentences.]
CONFIDENCE: [HIGH / MEDIUM / LOW]
KEY_RISKS:
- [risk 1]
- [risk 2]
- [risk 3]
KEY_CATALYSTS:
- [catalyst 1]
- [catalyst 2]
- [catalyst 3]"""


# ── Parsers ────────────────────────────────────────────────────────────────────

def _parse_agent(agent_name: str, raw: str) -> AgentView:
    stance_m   = re.search(r"STANCE:\s*([A-Z]+)", raw)
    impact_m   = re.search(r"ESTIMATED_IMPACT:\s*(.+)", raw)
    reason_m   = re.search(r"REASONING:\s*(.+?)(?=\n[A-Z_]+:|$)", raw, re.DOTALL)
    kp_section = re.search(r"KEY_POINTS:\s*((?:-.+\n?)+)", raw)

    key_points: list[str] = []
    if kp_section:
        key_points = [
            ln.lstrip("- ").strip()
            for ln in kp_section.group(1).splitlines()
            if ln.strip().startswith("-")
        ]

    return AgentView(
        agent=agent_name,
        stance=stance_m.group(1).strip() if stance_m else "NEUTRAL",
        estimated_impact=impact_m.group(1).strip() if impact_m else "Unknown",
        key_points=key_points[:5],
        reasoning=reason_m.group(1).strip() if reason_m else raw[:300],
    )


def _parse_synthesis(raw: str) -> dict:
    def extract(key: str) -> str:
        m = re.search(rf"{key}:\s*(.+?)(?=\n[A-Z_]+:|$)", raw, re.DOTALL)
        return m.group(1).strip() if m else ""

    def extract_bullets(key: str) -> list[str]:
        m = re.search(rf"{key}:\s*((?:-.+\n?)+)", raw)
        if not m:
            return []
        return [
            ln.lstrip("- ").strip()
            for ln in m.group(1).splitlines()
            if ln.strip().startswith("-")
        ]

    return {
        "base_case":      extract("BASE_CASE"),
        "bull_case":      extract("BULL_CASE"),
        "bear_case":      extract("BEAR_CASE"),
        "confidence":     extract("CONFIDENCE") or "MEDIUM",
        "key_risks":      extract_bullets("KEY_RISKS"),
        "key_catalysts":  extract_bullets("KEY_CATALYSTS"),
    }


# ── Service ────────────────────────────────────────────────────────────────────

class ForecastService:
    """Orchestrates multi-agent event forecasting."""

    def __init__(
        self,
        generation_service: GenerationService,
        embedding_service: EmbeddingService,
        retrieval_service: RetrievalService,
    ) -> None:
        self._gen = generation_service
        self._emb = embedding_service
        self._ret = retrieval_service

    async def forecast(self, request: ForecastRequest) -> ForecastResponse:
        t0 = time.perf_counter()
        forecast_id = str(ULID())
        total_tokens = 0

        logger.info(
            "forecast_started",
            forecast_id=forecast_id,
            company=request.company,
            event_type=request.event_type,
        )

        # 1. Structured financial context from SQLite
        financial_context = ""
        similar_events_raw: list[dict] = []
        try:
            from app.data.financial_db import build_financial_context, search_similar_events
            financial_context = build_financial_context(request.company)
            similar_events_raw = search_similar_events(
                request.event_type, request.company, limit=5
            )
        except Exception as exc:
            logger.warning("financial_context_failed", error=str(exc))

        similar_events_text = ""
        if similar_events_raw:
            lines = []
            for ev in similar_events_raw:
                lines.append(f"  [{ev['event_date']}] {ev['company']} — {ev['title']}")
                if ev.get("description"):
                    lines.append(f"    {ev['description'][:200]}")
            similar_events_text = "\n".join(lines)

        # 2. PDF chunk retrieval scoped to this company
        pdf_context = ""
        try:
            query_text = f"{request.event_type} {request.event_description}"
            embeddings = await self._emb.embed_texts([query_text])
            where = {"company": {"$eq": request.company}}
            chunks = await self._ret.hybrid_query(
                query_embeddings=embeddings,
                query_text=query_text,
                where=where,
                top_k=5,
            )
            if chunks:
                pdf_context = "\n\n".join(
                    f"[Excerpt {i}] {c.text[:400]}"
                    for i, c in enumerate(chunks, 1)
                )
        except Exception as exc:
            logger.warning("pdf_context_failed", error=str(exc))

        # 3. Build agent user prompt (shared across all 3 agents)
        agent_user = _agent_user_prompt(
            company=request.company,
            event_type=request.event_type,
            event_description=request.event_description,
            horizon_days=request.horizon_days,
            financial_context=financial_context,
            similar_events_text=similar_events_text,
            pdf_context=pdf_context,
        )

        # 4. Run Bull, Bear, Macro agents in parallel
        async def run_agent(name: str, system: str) -> tuple[str, str, int]:
            try:
                text, tokens = await self._gen.raw_generate(system=system, user=agent_user)
                return name, text, tokens
            except Exception as exc:
                logger.warning("agent_failed", agent=name, error=str(exc))
                fallback = (
                    f"STANCE: NEUTRAL\nESTIMATED_IMPACT: Unknown\n"
                    f"KEY_POINTS:\n- Analysis unavailable\nREASONING: {str(exc)[:100]}"
                )
                return name, fallback, 0

        agent_results = await asyncio.gather(
            run_agent("bull", BULL_SYSTEM),
            run_agent("bear", BEAR_SYSTEM),
            run_agent("macro", MACRO_SYSTEM),
        )

        agent_views: list[AgentView] = []
        agent_texts: dict[str, str] = {}
        for name, raw, tokens in agent_results:
            total_tokens += tokens
            agent_views.append(_parse_agent(name, raw))
            agent_texts[name] = raw

        # 5. Synthesize all views
        synth_user = _synthesizer_user_prompt(
            company=request.company,
            event_description=request.event_description,
            horizon_days=request.horizon_days,
            bull_view=agent_texts.get("bull", ""),
            bear_view=agent_texts.get("bear", ""),
            macro_view=agent_texts.get("macro", ""),
        )
        try:
            synth_raw, synth_tokens = await self._gen.raw_generate(
                system=SYNTHESIZER_SYSTEM, user=synth_user
            )
            total_tokens += synth_tokens
        except Exception as exc:
            logger.warning("synthesis_failed", error=str(exc))
            synth_raw = (
                "BASE_CASE: Analysis unavailable.\nBULL_CASE: N/A\nBEAR_CASE: N/A\n"
                "CONFIDENCE: LOW\nKEY_RISKS:\n- Synthesis failed\nKEY_CATALYSTS:\n- N/A"
            )

        synthesis = _parse_synthesis(synth_raw)
        latency_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            "forecast_complete",
            forecast_id=forecast_id,
            latency_ms=round(latency_ms, 2),
            total_tokens=total_tokens,
        )

        return ForecastResponse(
            forecast_id=forecast_id,
            company=request.company,
            event_type=request.event_type,
            event_description=request.event_description,
            horizon_days=request.horizon_days,
            agent_views=agent_views,
            base_case=synthesis["base_case"],
            bull_case=synthesis["bull_case"],
            bear_case=synthesis["bear_case"],
            confidence=synthesis["confidence"],
            key_risks=synthesis["key_risks"],
            key_catalysts=synthesis["key_catalysts"],
            similar_events=similar_events_raw,
            latency_ms=round(latency_ms, 2),
            total_tokens=total_tokens,
        )
