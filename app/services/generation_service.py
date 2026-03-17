"""LLM generation service — pluggable ModelBackend (DeepSeek default, Claude optional).

Implements a ModelBackend Protocol so backends can be swapped via env var
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


# ── DeepSeek backend (default) ────────────────────────────────────────────────

class DeepSeekBackend:
    """DeepSeek async backend via OpenAI-compatible API."""

    DEEPSEEK_BASE_URL = "https://api.deepseek.com"

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key, base_url=self.DEEPSEEK_BASE_URL)
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
        """Call DeepSeek API and return (answer, token_usage)."""
        user_prompt = build_user_prompt(question=question, context=context, query_type=query_type)
        t0 = time.perf_counter()

        response = await self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        elapsed = time.perf_counter() - t0
        answer = response.choices[0].message.content or ""

        usage = TokenUsageDetail(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

        LLM_INPUT_TOKENS_TOTAL.labels(model=self.model).inc(usage.input_tokens)
        LLM_OUTPUT_TOKENS_TOTAL.labels(model=self.model).inc(usage.output_tokens)
        LLM_LATENCY_SECONDS.labels(model=self.model).observe(elapsed)

        logger.info(
            "deepseek_generation_complete",
            model=self.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            latency_s=round(elapsed, 2),
        )
        return answer, usage

    async def raw_generate(self, system: str, user: str) -> tuple[str, int]:
        """Generate with fully custom system + user prompts. Returns (text, total_tokens)."""
        response = await self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or "", response.usage.total_tokens

    async def stream_generate(
        self,
        question: str,
        context: str,
        query_type: str = "GENERAL",
    ):
        """Stream tokens from DeepSeek API as an async generator."""
        user_prompt = build_user_prompt(question=question, context=context, query_type=query_type)
        stream = await self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        async for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token


# ── Groq backend (free tier, set LLM_PROVIDER=groq) ──────────────────────────

class GroqBackend:
    """Groq async backend via OpenAI-compatible API (free tier available)."""

    GROQ_BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key, base_url=self.GROQ_BASE_URL)
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
        """Call Groq API and return (answer, token_usage)."""
        user_prompt = build_user_prompt(question=question, context=context, query_type=query_type)
        t0 = time.perf_counter()

        response = await self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        elapsed = time.perf_counter() - t0
        answer = response.choices[0].message.content or ""

        usage = TokenUsageDetail(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

        LLM_INPUT_TOKENS_TOTAL.labels(model=self.model).inc(usage.input_tokens)
        LLM_OUTPUT_TOKENS_TOTAL.labels(model=self.model).inc(usage.output_tokens)
        LLM_LATENCY_SECONDS.labels(model=self.model).observe(elapsed)

        logger.info(
            "groq_generation_complete",
            model=self.model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            latency_s=round(elapsed, 2),
        )
        return answer, usage

    async def raw_generate(self, system: str, user: str) -> tuple[str, int]:
        """Generate with fully custom system + user prompts. Returns (text, total_tokens)."""
        response = await self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or "", response.usage.total_tokens

    async def stream_generate(
        self,
        question: str,
        context: str,
        query_type: str = "GENERAL",
    ):
        """Stream tokens from Groq API as an async generator."""
        user_prompt = build_user_prompt(question=question, context=context, query_type=query_type)
        stream = await self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        async for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                yield token


# ── Claude backend (optional, set LLM_PROVIDER=claude) ───────────────────────

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
        answer = message.content[0].text if message.content else ""

        usage = TokenUsageDetail(
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            total_tokens=message.usage.input_tokens + message.usage.output_tokens,
        )

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

    async def raw_generate(self, system: str, user: str) -> tuple[str, int]:
        """Generate with fully custom system + user prompts. Returns (text, total_tokens)."""
        import anthropic
        message = await self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = message.content[0].text if message.content else ""
        total = message.usage.input_tokens + message.usage.output_tokens
        return text, total


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
        model: str = "deepseek-chat",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        collect_training_data: bool = False,
        training_data_path: str = "./data/training_data.jsonl",
        use_finetuned_model: bool = False,
        finetuned_model_path: str = "",
        llm_provider: str = "deepseek",
    ) -> None:
        if use_finetuned_model and finetuned_model_path:
            self._backend: ModelBackend = FineTunedModelBackend(finetuned_model_path)
        elif llm_provider == "claude":
            self._backend = ClaudeBackend(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        elif llm_provider == "groq":
            self._backend = GroqBackend(
                api_key=api_key,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            self._backend = DeepSeekBackend(
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

    async def raw_generate(self, system: str, user: str) -> tuple[str, int]:
        """Generate with custom system + user prompts (used by forecast agents)."""
        if hasattr(self._backend, "raw_generate"):
            return await self._backend.raw_generate(system, user)
        # Fallback: pack into standard generate
        answer, usage = await self._backend.generate(user, "", "GENERAL")
        return answer, usage.total_tokens

    async def stream_generate(
        self,
        question: str,
        context: str,
        query_type: str = "GENERAL",
    ):
        """Stream tokens as async generator. Falls back to non-streaming if backend doesn't support it."""
        if hasattr(self._backend, "stream_generate"):
            async for token in self._backend.stream_generate(question, context, query_type):
                yield token
        else:
            # Fallback: generate full answer then yield it at once
            answer, _ = await self._backend.generate(question, context, query_type)
            yield answer

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
