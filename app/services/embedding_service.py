"""FinBERT embedding service — async-safe, CPU-bound work in thread pool."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

import structlog

from app.monitoring.metrics import EMBEDDING_DURATION_SECONDS

logger = structlog.get_logger(__name__)

# Module-level thread pool (single worker = no contention on FinBERT weights)
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="finbert")


class EmbeddingService:
    """Wraps ProsusAI/finbert for CLS-token sentence embeddings.

    Runs synchronous PyTorch inference in a dedicated thread-pool executor
    so it never blocks the asyncio event loop.
    """

    def __init__(
        self,
        model_name: str = "ProsusAI/finbert",
        strategy: Literal["cls", "mean"] = "cls",
        device: str = "cpu",
        batch_size: int = 16,
    ) -> None:
        self.model_name = model_name
        self.strategy = strategy
        self.device = device
        self.batch_size = batch_size
        self._ready = False
        self._tokenizer = None
        self._model = None
        self._load_model()

    # ── Public API ────────────────────────────────────────────────────────────

    def is_ready(self) -> bool:
        return self._ready

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts asynchronously."""
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(_EXECUTOR, self._encode_batch, texts)
        return embeddings

    # ── Internal sync implementation ──────────────────────────────────────────

    def _load_model(self) -> None:
        """Load tokenizer and model (called once at init)."""
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer

            logger.info("loading_finbert_model", model=self.model_name)
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name)
            self._model.eval()
            self._model.to(self.device)
            self._ready = True
            logger.info("finbert_model_loaded", model=self.model_name, device=self.device)
        except Exception as exc:
            logger.error("finbert_load_failed", error=str(exc))
            raise

    def _encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Synchronous batch encoding — runs in executor thread."""
        import time

        import numpy as np
        import torch

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_size_label = str(len(batch))
            t0 = time.perf_counter()

            encoded = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            encoded = {k: v.to(self.device) for k, v in encoded.items()}

            with torch.no_grad():
                outputs = self._model(**encoded)

            if self.strategy == "cls":
                # pooler_output: linear(tanh(hidden_state[CLS]))  — [batch, 768]
                embeddings = outputs.pooler_output
            else:
                # Mean pooling over non-padding tokens
                attention_mask = encoded["attention_mask"]
                token_embeddings = outputs.last_hidden_state
                mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                embeddings = torch.sum(token_embeddings * mask_expanded, 1) / torch.clamp(
                    mask_expanded.sum(1), min=1e-9
                )

            # L2-normalize for correct cosine similarity in ChromaDB
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            embeddings_np = embeddings.cpu().numpy().astype(np.float32)

            elapsed = time.perf_counter() - t0
            EMBEDDING_DURATION_SECONDS.labels(batch_size=batch_size_label).observe(elapsed)

            all_embeddings.extend(embeddings_np.tolist())

        return all_embeddings

    # ── Dimension property ────────────────────────────────────────────────────

    @property
    def embedding_dim(self) -> int:
        """Return embedding dimensionality (768 for BERT-base variants)."""
        if self._model is None:
            raise RuntimeError("Model not loaded")
        return self._model.config.hidden_size
