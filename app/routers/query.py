"""Query router: POST /query and POST /query/stream."""
import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.dependencies import (
    get_embedding_service,
    get_generation_service,
    get_mcp_service,
    get_retrieval_service,
)
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
async def query_documents(
    request: QueryRequest,
    embedding_service=Depends(get_embedding_service),
    retrieval_service=Depends(get_retrieval_service),
    generation_service=Depends(get_generation_service),
    mcp_service=Depends(get_mcp_service),
) -> QueryResponse:
    service = _make_service(embedding_service, retrieval_service, generation_service, mcp_service)
    try:
        return await service.query(request)
    except Exception as exc:
        logger.error("query_endpoint_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {exc}",
        ) from exc


@router.post(
    "/query/stream",
    summary="Stream a financial question answer token-by-token (SSE)",
)
async def query_stream(
    request: QueryRequest,
    embedding_service=Depends(get_embedding_service),
    retrieval_service=Depends(get_retrieval_service),
    generation_service=Depends(get_generation_service),
    mcp_service=Depends(get_mcp_service),
):
    service = _make_service(embedding_service, retrieval_service, generation_service, mcp_service)

    async def event_generator():
        try:
            # Step 1: classify + retrieve (fast — happens before streaming)
            query_type = service._mcp.classify_query(request.question)
            entities = service._mcp.extract_entities(request.question)
            if request.company:
                entities["company"] = request.company
                entities.pop("ticker", None)
            where_filter = service._mcp.build_metadata_filters(entities, request.filters)

            query_embeddings = await service._embedding.embed_texts([request.question])
            chunks = await service._retrieval.hybrid_query(
                query_embeddings=query_embeddings,
                query_text=request.question,
                where=where_filter,
                top_k=request.top_k,
            )
            context_str, used_chunks = service._mcp.assemble_context(chunks)

            # Send metadata first so UI can show sources immediately
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
            meta_event = json.dumps({
                "type": "meta",
                "query_type": query_type,
                "chunk_count": len(used_chunks),
                "sources": sources if request.include_sources else [],
            })
            yield f"data: {meta_event}\n\n"

            if not context_str:
                no_data = json.dumps({"type": "token", "text": "I was unable to find relevant information in the knowledge base. Please upload relevant financial documents first or refine your question."})
                yield f"data: {no_data}\n\n"
            else:
                # Stream tokens
                async for token in service._generation.stream_generate(
                    question=request.question,
                    context=context_str,
                    query_type=query_type,
                ):
                    yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as exc:
            logger.error("stream_query_failed", error=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'text': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
