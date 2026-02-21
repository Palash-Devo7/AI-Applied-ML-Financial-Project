"""LLM generation service using Claude via the Anthropic async SDK.

Implements a ModelBackend Protocol so a fine-tuned backend can slot in
without touching call sites (Phase 2 hook).
"""
from __future__ import annotations

import json
import time
from typing import Protocol, runtime_checkable

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.prompts import SYSTEM_PROMPT, build_user_prompt
from app.models.queries import TokenUsageDetail
from app.monitoring.metrics import (
    LLM_INPUT_TOKENS_TOTAL,
    LLM_LATENCY_SECONDS,
    LLM_OUTPUT_TOKENS_TOTAL,
)

logger = structlog.get_logger(__name__)


# ── ModelBackend Protocol (Phase 2 hook) ──────────────────────────────────────

@runtime_checkable
class ModelBackend(Protocol):
    async def generate(
        self,
        question: str,
        context: str,
        query_type: str,
    ) -> tuple[str, TokenUsageDetail]:
        """Generate an answer. Returns (answer_text, token_usage)."""
        ...


# ── Claude backend ─────────────────────────────────────────────────────────────

class ClaudeBackend:
    """Anthropic Claude async backend with retry and token tracking."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> None:
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def generate(
        self,
        question: str,
        context: str,
        query_type: str = "GENERAL",
    ) -> tuple[str, TokenUsageDetail]:
        """Call Claude API and return (answer, token_usage)."""
        import anthropic

        user_prompt = build_user_prompt(question=question, context=context, query_type=query_type)
        t0 = time.perf_counter()

        try:
            message = await self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.RateLimitError as exc:
            logger.warning("claude_rate_limit", error=str(exc))
            raise
        except anthropic.APIStatusError as exc:
            logger.error("claude_api_error", status=exc.status_code, error=str(exc))
            raise

        elapsed = time.perf_counter() - t0

        # Extract text content
        answer = message.content[0].text if message.content else ""

        # Token accounting
        usage = TokenUsageDetail(
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            total_tokens=message.usage.input_tokens + message.usage.output_tokens,
        )

        # Prometheus metrics
        LLM_INPUT_TOKENS_TOTAL.labels(model=self.model).inc(usage.input_tokens)
        LLM_OUTPUT_TOKENS_TOTAL.labels(model=self.model).inc(usage.output_tokens)
        LLM_LATENCY_SECONDS.labels(model=self.model).observe(elapsed)

        logger.info(
            "claude_generation_complete",
            model=self.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            latency_s=round(elapsed, 2),
        )
        return answer, usage


# ── Fine-tuned model stub backend (Phase 2) ───────────────────────────────────

class FineTunedModelBackend:
    """Stub: local LoRA-adapted model backend (Phase 2 implementation)."""

    def __init__(self, model_path: str) -> None:
        self.model_path = model_path
        logger.warning("finetuned_backend_stub", model_path=model_path)

    async def generate(
        self,
        question: str,
        context: str,
        query_type: str = "GENERAL",
    ) -> tuple[str, TokenUsageDetail]:
        raise NotImplementedError("Fine-tuned backend not yet implemented (Phase 2)")


# ── Generation Service ─────────────────────────────────────────────────────────

class GenerationService:
    """Orchestrates answer generation via a pluggable ModelBackend."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        collect_training_data: bool = False,
        training_data_path: str = "./data/training_data.jsonl",
        use_finetuned_model: bool = False,
        finetuned_model_path: str = "",
    ) -> None:
        if use_finetuned_model and finetuned_model_path:
            self._backend: ModelBackend = FineTunedModelBackend(finetuned_model_path)
        else:
            self._backend = ClaudeBackend(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        self._collect_training_data = collect_training_data
        self._training_data_path = training_data_path

    async def generate(
        self,
        question: str,
        context: str,
        query_type: str = "GENERAL",
    ) -> tuple[str, TokenUsageDetail]:
        """Generate an answer and optionally log training data."""
        answer, usage = await self._backend.generate(
            question=question,
            context=context,
            query_type=query_type,
        )

        if self._collect_training_data:
            await self._log_training_record(question, context, answer)

        return answer, usage

    async def _log_training_record(
        self, question: str, context: str, answer: str
    ) -> None:
        """Append (question, context, answer) to JSONL for LoRA dataset building."""
        import asyncio

        record = json.dumps({"question": question, "context": context, "answer": answer})
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._append_record, record)

    def _append_record(self, record: str) -> None:
        try:
            with open(self._training_data_path, "a", encoding="utf-8") as f:
                f.write(record + "\n")
        except Exception as exc:
            logger.warning("training_data_log_failed", error=str(exc))
