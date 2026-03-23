"""Query router: POST /query and POST /query/stream."""
import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.core.auth_deps import get_current_user, require_credits, consume_after_success
from app.dependencies import (
    get_embedding_service,
    get_generation_service,
    get_mcp_service,
    get_retrieval_service,
)
from app.core.limiter import limiter
from app.models.queries import QueryRequest, QueryResponse
from app.services.query_service import QueryService

router = APIRouter(tags=["query"])
logger = structlog.get_logger(__name__)


def _make_service(embedding_service, retrieval_service, generation_service, mcp_service):
    return QueryService(
        embedding_service=embedding_service,
        retrieval_service=retrieval_service,
        generation_service=generation_service,
        mcp_service=mcp_service,
    )


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a financial question for RAG-augmented answer",
)
@limiter.limit("5/minute")
async def query_documents(
    request: Request,
    body: QueryRequest,
    user: dict = Depends(require_credits),
    embedding_service=Depends(get_embedding_service),
    retrieval_service=Depends(get_retrieval_service),
    generation_service=Depends(get_generation_service),
    mcp_service=Depends(get_mcp_service),
) -> QueryResponse:
    service = _make_service(embedding_service, retrieval_service, generation_service, mcp_service)
    try:
        result = await service.query(body)
        consume_after_success(request)
        return result
    except Exception as exc:
        logger.error("query_endpoint_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query failed. Please try again.",
        ) from exc


@router.post(
    "/query/stream",
    summary="Stream a financial question answer token-by-token (SSE)",
)
@limiter.limit("5/minute")
async def query_stream(
    request: Request,
    body: QueryRequest,
    user: dict = Depends(require_credits),
    embedding_service=Depends(get_embedding_service),
    retrieval_service=Depends(get_retrieval_service),
    generation_service=Depends(get_generation_service),
    mcp_service=Depends(get_mcp_service),
):
    # Consume credit before streaming starts
    consume_after_success(request)

    service = _make_service(embedding_service, retrieval_service, generation_service, mcp_service)

    async def event_generator():
        try:
            query_type = service._mcp.classify_query(body.question)
            entities = service._mcp.extract_entities(body.question)
            if body.company:
                entities["company"] = body.company
                entities.pop("ticker", None)
            where_filter = service._mcp.build_metadata_filters(entities, body.filters)

            query_embeddings = await service._embedding.embed_texts([body.question])
            chunks = await service._retrieval.hybrid_query(
                query_embeddings=query_embeddings,
                query_text=body.question,
                where=where_filter,
                top_k=body.top_k,
            )
            context_str, used_chunks = service._mcp.assemble_context(chunks)

            company_name = body.company or entities.get("company")
            if company_name:
                try:
                    from app.data.financial_db import build_financial_context
                    structured = build_financial_context(company_name)
                    if structured:
                        context_str = structured + context_str
                except Exception as e:
                    logger.warning("structured_context_failed", error=str(e))

            sources = [
                {
                    "chunk_id": c.chunk_id,
                    "company": c.company,
                    "ticker": c.ticker,
                    "year": c.year,
                    "report_type": c.report_type,
                    "section_type": c.section_type,
                    "page_num": c.page_num,
                    "score": c.score,
                    "text": c.text[:400],
                }
                for c in used_chunks
            ]
            yield f"data: {json.dumps({'type': 'meta', 'query_type': query_type, 'chunk_count': len(used_chunks), 'sources': sources if body.include_sources else []})}\n\n"

            if not context_str:
                yield f"data: {json.dumps({'type': 'token', 'text': 'I was unable to find relevant information in the knowledge base. Please upload relevant financial documents first or refine your question.'})}\n\n"
            else:
                async for token in service._generation.stream_generate(
                    question=body.question,
                    context=context_str,
                    query_type=query_type,
                ):
                    yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            logger.error("stream_query_failed", error=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'text': 'An error occurred. Please try again.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
