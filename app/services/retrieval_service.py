"""Hybrid retrieval: ChromaDB vector search + BM25 rescore + RRF fusion."""
from __future__ import annotations

from typing import Optional

import structlog

from app.core.vector_store import VectorStoreClient
from app.models.queries import RetrievedChunk
from app.monitoring.metrics import RETRIEVAL_CHUNK_COUNT

logger = structlog.get_logger(__name__)


class RetrievalService:
    """Hybrid retrieval combining dense vector search with BM25 sparse rescore.

    Reciprocal Rank Fusion (RRF) blends both rankings:
        score = alpha * (1 / (k + vector_rank)) + (1 - alpha) * (1 / (k + bm25_rank))
    where k=60 (standard RRF constant) and alpha defaults to 0.7.
    """

    _RRF_K = 60

    def __init__(
        self,
        vector_store: VectorStoreClient,
        top_k: int = 5,
        fetch_multiplier: int = 2,
        rrf_alpha: float = 0.7,
    ) -> None:
        self._vector_store = vector_store
        self.top_k = top_k
        self.fetch_multiplier = fetch_multiplier
        self.rrf_alpha = rrf_alpha

    async def hybrid_query(
        self,
        query_embeddings: list[list[float]],
        query_text: str,
        where: Optional[dict] = None,
        top_k: Optional[int] = None,
    ) -> list[RetrievedChunk]:
        """Execute hybrid retrieval and return top-k ranked chunks."""
        k = top_k or self.top_k
        fetch_n = k * self.fetch_multiplier

        # 1. Vector search — over-fetch candidates
        results = await self._vector_store.query(
            query_embeddings=query_embeddings,
            n_results=fetch_n,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        if not results or not results.get("ids") or not results["ids"][0]:
            logger.warning("no_results_from_vector_search", where=where)
            return []

        # Flatten results (single query)
        ids: list[str] = results["ids"][0]
        docs: list[str] = results["documents"][0]
        metadatas: list[dict] = results["metadatas"][0]
        distances: list[float] = results["distances"][0]

        # Convert distance to similarity score (cosine: similarity = 1 - distance)
        vector_scores = [max(0.0, 1.0 - d) for d in distances]

        # 2. BM25 rescore on candidate documents
        bm25_scores = self._bm25_rescore(query_text, docs)

        # 3. Reciprocal Rank Fusion
        fused_scores = self._rrf_fuse(vector_scores, bm25_scores)

        # 4. Sort by fused score and select top-k
        ranked = sorted(
            range(len(ids)),
            key=lambda i: fused_scores[i],
            reverse=True,
        )[:k]

        chunks: list[RetrievedChunk] = []
        for i in ranked:
            meta = metadatas[i]
            chunks.append(
                RetrievedChunk(
                    chunk_id=ids[i],
                    text=docs[i],
                    score=round(fused_scores[i], 4),
                    company=meta.get("company"),
                    ticker=meta.get("ticker"),
                    year=meta.get("year"),
                    quarter=meta.get("quarter"),
                    section_type=meta.get("section_type"),
                    report_type=meta.get("report_type"),
                    page_num=meta.get("page_num"),
                )
            )

        RETRIEVAL_CHUNK_COUNT.observe(len(chunks))
        logger.info(
            "retrieval_complete",
            candidates=len(ids),
            returned=len(chunks),
            has_filter=where is not None,
        )
        return chunks

    # ── BM25 ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _bm25_rescore(query: str, documents: list[str]) -> list[float]:
        """Score documents with BM25 (rank-bm25 library)."""
        try:
            from rank_bm25 import BM25Okapi

            tokenized_corpus = [doc.lower().split() for doc in documents]
            tokenized_query = query.lower().split()

            bm25 = BM25Okapi(tokenized_corpus)
            scores = bm25.get_scores(tokenized_query).tolist()
            return scores
        except Exception as exc:
            logger.warning("bm25_failed", error=str(exc))
            # Fallback: equal weights
            return [1.0] * len(documents)

    # ── RRF ───────────────────────────────────────────────────────────────────

    def _rrf_fuse(
        self,
        vector_scores: list[float],
        bm25_scores: list[float],
    ) -> list[float]:
        """Reciprocal Rank Fusion of two score lists."""
        n = len(vector_scores)
        assert len(bm25_scores) == n, "Score list length mismatch"

        # Rank both lists (1-indexed, lower rank = higher score)
        vec_ranks = self._scores_to_ranks(vector_scores)
        bm25_ranks = self._scores_to_ranks(bm25_scores)

        k = self._RRF_K
        alpha = self.rrf_alpha
        fused = [
            alpha * (1.0 / (k + vec_ranks[i])) + (1 - alpha) * (1.0 / (k + bm25_ranks[i]))
            for i in range(n)
        ]
        return fused

    @staticmethod
    def _scores_to_ranks(scores: list[float]) -> list[int]:
        """Convert scores to 1-indexed ranks (higher score → lower rank number)."""
        indexed = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        ranks = [0] * len(scores)
        for rank, idx in enumerate(indexed, 1):
            ranks[idx] = rank
        return ranks
