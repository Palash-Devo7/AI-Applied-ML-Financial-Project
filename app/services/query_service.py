"""Query service: orchestrates classify → filter → retrieve → generate."""
from __future__ import annotations

import time

import structlog
from ulid import ULID

from app.models.queries import QueryRequest, QueryResponse, TokenUsageDetail
from app.monitoring.metrics import QUERIES_TOTAL, QUERY_DURATION_SECONDS
from app.services.embedding_service import EmbeddingService
from app.services.generation_service import GenerationService
from app.services.mcp_service import MCPService
from app.services.retrieval_service import RetrievalService

logger = structlog.get_logger(__name__)


class QueryService:
    """End-to-end query pipeline."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        retrieval_service: RetrievalService,
        generation_service: GenerationService,
        mcp_service: MCPService,
    ) -> None:
        self._embedding = embedding_service
        self._retrieval = retrieval_service
        self._generation = generation_service
        self._mcp = mcp_service

    async def query(self, request: QueryRequest) -> QueryResponse:
        """Execute the full RAG query pipeline."""
        t0 = time.perf_counter()
        query_id = str(ULID())

        logger.info("query_started", query_id=query_id, question=request.question[:100])

        try:
            # 1. Classify query
            query_type = self._mcp.classify_query(request.question)

            # 2. Extract entities and build metadata filter
            entities = self._mcp.extract_entities(request.question)
            # Top-level company field takes precedence over entity extraction
            if request.company:
                entities["company"] = request.company
                entities.pop("ticker", None)  # company name filter is more precise
            where_filter = self._mcp.build_metadata_filters(
                entities=entities,
                explicit_filters=request.filters,
            )

            logger.debug(
                "query_classified",
                query_id=query_id,
                query_type=query_type,
                entities=entities,
                has_filter=where_filter is not None,
            )

            # 3. Embed the question
            query_embeddings = await self._embedding.embed_texts([request.question])

            # 4. Hybrid retrieval
            chunks = await self._retrieval.hybrid_query(
                query_embeddings=query_embeddings,
                query_text=request.question,
                where=where_filter,
                top_k=request.top_k,
            )

            # 5. Assemble context
            context_str, used_chunks = self._mcp.assemble_context(chunks)

            # 5b. Enrich with structured financial data if a company is known
            company_name = request.company or entities.get("company")
            if company_name:
                try:
                    from app.data.financial_db import build_financial_context
                    structured = build_financial_context(company_name)
                    if structured:
                        context_str = structured + context_str
                        logger.debug("structured_context_added", company=company_name)
                except Exception as e:
                    logger.warning("structured_context_failed", error=str(e))

            # 6. Generate answer
            if not context_str:
                answer = (
                    "I was unable to find relevant information in the knowledge base "
                    "to answer your question. Please try uploading relevant financial "
                    "documents first, or refine your question."
                )
                usage = TokenUsageDetail(input_tokens=0, output_tokens=0, total_tokens=0)
            else:
                answer, usage = await self._generation.generate(
                    question=request.question,
                    context=context_str,
                    query_type=query_type,
                )

            latency_ms = (time.perf_counter() - t0) * 1000
            QUERY_DURATION_SECONDS.labels(query_type=query_type).observe(latency_ms / 1000)
            QUERIES_TOTAL.labels(query_type=query_type, status="success").inc()

            logger.info(
                "query_complete",
                query_id=query_id,
                query_type=query_type,
                chunks_used=len(used_chunks),
                tokens=usage.total_tokens,
                latency_ms=round(latency_ms, 2),
            )

            sources = used_chunks if request.include_sources else []

            return QueryResponse(
                query_id=query_id,
                question=request.question,
                answer=answer,
                sources=sources,
                query_type=query_type,
                latency_ms=round(latency_ms, 2),
                tokens_used=usage,
                chunk_count=len(used_chunks),
            )

        except Exception as exc:
            QUERIES_TOTAL.labels(query_type="UNKNOWN", status="error").inc()
            logger.error("query_failed", query_id=query_id, error=str(exc))
            raise
