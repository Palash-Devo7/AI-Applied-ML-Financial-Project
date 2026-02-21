"""MCP (Model Context Protocol) orchestration layer.

Responsibilities:
- Query classification → one of 6 query types
- Entity extraction (company, ticker, year) from query text
- ChromaDB metadata filter construction
- Context assembly with dedup, sorting, citation formatting
"""
from __future__ import annotations

import re
from typing import Optional

import structlog

from app.models.queries import QueryFilters, RetrievedChunk

logger = structlog.get_logger(__name__)

# ── Query type definitions ─────────────────────────────────────────────────────
QUERY_TYPES = {
    "RISK": [
        "risk", "risks", "risk factor", "risk factors", "exposure",
        "litigation", "contingent", "regulatory", "compliance", "hazard",
        "threat", "vulnerability",
    ],
    "REVENUE": [
        "revenue", "revenues", "sales", "income", "earnings", "profit",
        "margin", "gross profit", "net income", "top line", "growth",
        "guidance", "forecast",
    ],
    "MACRO": [
        "macro", "macroeconomic", "economy", "inflation", "interest rate",
        "fed", "federal reserve", "gdp", "recession", "market", "sector",
        "industry", "commodity",
    ],
    "COMPARATIVE": [
        "compare", "comparison", "versus", "vs", "against", "relative",
        "peer", "competitor", "benchmark", "better than", "worse than",
        "outperform", "underperform",
    ],
    "HISTORICAL": [
        "historical", "history", "trend", "over time", "year over year",
        "yoy", "quarter over quarter", "qoq", "previous", "prior",
        "last year", "last quarter", "last 3 years", "last 5 years",
        "over the last", "over the past", "since", "since 20",
        "years ago", "multi-year", "long-term trend",
    ],
    "GENERAL": [],  # catch-all
}

# ── Entity extraction regexes ─────────────────────────────────────────────────
_YEAR_RE = re.compile(r"\b(20[0-2]\d)\b")
_QUARTER_RE = re.compile(r"\b(Q[1-4])\b", re.IGNORECASE)
_TICKER_RE = re.compile(
    r"\b(AAPL|MSFT|GOOGL?|AMZN|META|NVDA|TSLA|JPM|JNJ|V|PG|UNH|HD|MA|DIS|BAC|XOM|NFLX|ADBE|CRM|INTC|AMD)\b",
    re.IGNORECASE,
)
_COMPANY_NAME_RE = re.compile(
    r"\b(Apple|Microsoft|Google|Alphabet|Amazon|Meta|NVIDIA|Tesla|"
    r"JPMorgan|Johnson\s+&\s+Johnson|Visa|Mastercard|Disney|"
    r"Netflix|Adobe|Salesforce|Intel)\b",
    re.IGNORECASE,
)
_COMPANY_TO_TICKER = {
    "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL",
    "alphabet": "GOOGL", "amazon": "AMZN", "meta": "META",
    "nvidia": "NVDA", "tesla": "TSLA", "jpmorgan": "JPM",
    "johnson": "JNJ", "visa": "V", "mastercard": "MA",
    "disney": "DIS", "netflix": "NFLX", "adobe": "ADBE",
    "salesforce": "CRM", "intel": "INTC",
}


class MCPService:
    """Query classification, filter building, and context assembly."""

    def __init__(self, max_context_tokens: int = 6000) -> None:
        self.max_context_tokens = max_context_tokens

    # ── Classification ─────────────────────────────────────────────────────────

    def classify_query(self, question: str) -> str:
        """Assign one of 6 query types using keyword scoring."""
        question_lower = question.lower()
        scores: dict[str, int] = {qt: 0 for qt in QUERY_TYPES}

        for query_type, keywords in QUERY_TYPES.items():
            for kw in keywords:
                if kw in question_lower:
                    scores[query_type] += 1

        # Exclude GENERAL from scoring (it's the fallback)
        candidate_scores = {k: v for k, v in scores.items() if k != "GENERAL"}
        if not candidate_scores or max(candidate_scores.values()) == 0:
            return "GENERAL"

        return max(candidate_scores, key=lambda k: candidate_scores[k])

    # ── Entity extraction ──────────────────────────────────────────────────────

    def extract_entities(self, question: str) -> dict:
        """Extract company, ticker, year, quarter from query text."""
        entities: dict = {}

        # Ticker
        ticker_match = _TICKER_RE.search(question)
        if ticker_match:
            entities["ticker"] = ticker_match.group(1).upper()

        # Company name → resolve ticker
        company_match = _COMPANY_NAME_RE.search(question)
        if company_match and "ticker" not in entities:
            company_lower = company_match.group(1).lower().split()[0]
            ticker = _COMPANY_TO_TICKER.get(company_lower)
            if ticker:
                entities["ticker"] = ticker
            entities["company"] = company_match.group(1)

        # Year
        year_match = _YEAR_RE.search(question)
        if year_match:
            entities["year"] = int(year_match.group(1))

        # Quarter
        quarter_match = _QUARTER_RE.search(question)
        if quarter_match:
            entities["quarter"] = quarter_match.group(1).upper()

        return entities

    # ── Filter construction ────────────────────────────────────────────────────

    def build_metadata_filters(
        self,
        entities: dict,
        explicit_filters: Optional[QueryFilters] = None,
    ) -> Optional[dict]:
        """Build ChromaDB where-clause from extracted entities + explicit filters."""
        conditions: list[dict] = []

        # Merge explicit filters (they take precedence over extracted)
        effective: dict = {**entities}
        if explicit_filters:
            for field in ("company", "ticker", "year", "quarter", "report_type", "section_type", "sector"):
                val = getattr(explicit_filters, field, None)
                if val is not None:
                    effective[field] = val

        if "ticker" in effective:
            conditions.append({"ticker": {"$eq": effective["ticker"]}})
        elif "company" in effective:
            conditions.append({"company": {"$eq": effective["company"]}})

        if "year" in effective:
            conditions.append({"year": {"$eq": effective["year"]}})

        if "quarter" in effective:
            conditions.append({"quarter": {"$eq": effective["quarter"]}})

        if "report_type" in effective:
            conditions.append({"report_type": {"$eq": effective["report_type"]}})

        if "section_type" in effective:
            conditions.append({"section_type": {"$eq": effective["section_type"]}})

        if "sector" in effective:
            conditions.append({"sector": {"$eq": effective["sector"]}})

        if len(conditions) == 0:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    # ── Context assembly ───────────────────────────────────────────────────────

    def assemble_context(self, chunks: list[RetrievedChunk]) -> tuple[str, list[RetrievedChunk]]:
        """Sort, deduplicate, trim, and format retrieved chunks into LLM context.

        Returns (context_str, used_chunks).
        """
        # Sort by score DESC (similarity), then year DESC (recency)
        sorted_chunks = sorted(
            chunks,
            key=lambda c: (c.score, c.year or 0),
            reverse=True,
        )

        # Deduplication via Jaccard similarity > 0.8
        unique_chunks = self._deduplicate_chunks(sorted_chunks, threshold=0.8)

        # Trim to max context tokens (approx 4 chars/token)
        max_chars = self.max_context_tokens * 4
        used_chunks: list[RetrievedChunk] = []
        total_chars = 0

        for chunk in unique_chunks:
            chunk_chars = len(chunk.text)
            if total_chars + chunk_chars > max_chars:
                break
            used_chunks.append(chunk)
            total_chars += chunk_chars

        # Format with citations
        context_parts: list[str] = []
        for i, chunk in enumerate(used_chunks, 1):
            citation = self._format_citation(chunk)
            context_parts.append(f"[Source {i}: {citation}]\n{chunk.text}")

        context_str = "\n\n---\n\n".join(context_parts)
        return context_str, used_chunks

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _deduplicate_chunks(
        chunks: list[RetrievedChunk], threshold: float = 0.8
    ) -> list[RetrievedChunk]:
        """Remove near-duplicate chunks using Jaccard similarity on token sets."""
        unique: list[RetrievedChunk] = []
        seen_tokens: list[set[str]] = []

        for chunk in chunks:
            tokens = set(chunk.text.lower().split())
            is_duplicate = False
            for seen in seen_tokens:
                if tokens and seen:
                    jaccard = len(tokens & seen) / len(tokens | seen)
                    if jaccard > threshold:
                        is_duplicate = True
                        break
            if not is_duplicate:
                unique.append(chunk)
                seen_tokens.append(tokens)

        return unique

    @staticmethod
    def _format_citation(chunk: RetrievedChunk) -> str:
        """Format a human-readable citation string."""
        parts: list[str] = []
        if chunk.ticker:
            parts.append(chunk.ticker)
        elif chunk.company:
            parts.append(chunk.company)
        if chunk.report_type:
            parts.append(chunk.report_type)
        if chunk.year:
            parts.append(str(chunk.year))
        if chunk.quarter:
            parts.append(chunk.quarter)
        if chunk.section_type:
            parts.append(chunk.section_type.replace("_", " ").title())
        if chunk.page_num:
            parts.append(f"p.{chunk.page_num}")
        return ", ".join(parts) if parts else "Unknown Source"
