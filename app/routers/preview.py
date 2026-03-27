"""Guest preview endpoints — no auth required, 3 lifetime credits per guest.

Credit costs:
  - POST /query/preview    → 1 credit
  - POST /forecast/preview → 2 credits
"""
import hashlib
import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.limiter import limiter
from app.data.auth_db import check_and_consume_guest, consume_guest_credit
from app.dependencies import (
    get_embedding_service,
    get_generation_service,
    get_mcp_service,
    get_retrieval_service,
)
from app.models.forecast import ForecastRequest, ForecastResponse
from app.models.queries import QueryRequest
from app.services.forecast_service import ForecastService
from app.services.query_service import QueryService

router = APIRouter(tags=["preview"])
logger = structlog.get_logger(__name__)

GUEST_CREDIT_LIMIT = 3
QUERY_COST = 1
FORECAST_COST = 2


class PreviewQueryRequest(BaseModel):
    question: str
    company: str | None = None
    guest_token: str
    top_k: int = 10
    include_sources: bool = True


class PreviewForecastRequest(BaseModel):
    company: str
    event_type: str
    event_description: str = Field(..., min_length=10, max_length=1000)
    horizon_days: int = Field(90, ge=30, le=365)
    guest_token: str


def _make_guest_id(ip: str, token: str) -> str:
    return hashlib.sha256(f"{ip}:{token}".encode()).hexdigest()[:32]


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/preview/search")
async def preview_search(q: str = ""):
    """Public company search — no auth required. Powered by BSE securities cache."""
    if not q or len(q.strip()) < 2:
        return {"results": [], "query": q}
    from app.services.providers.bse_provider import BSEProvider
    results = BSEProvider.search(q.strip(), limit=12)
    return {"results": results, "query": q}


@router.get("/preview/company-status/{ticker}")
async def preview_company_status(ticker: str):
    """Public endpoint — check if a company is loaded and ready to query."""
    from app.data.financial_db import get_registry_by_ticker
    record = get_registry_by_ticker(ticker.upper())
    if not record:
        return {"status": "not_loaded", "ticker": ticker}
    return {"status": record.get("status"), "company": record.get("company"), "ticker": ticker}


@router.get("/preview/credits")
async def guest_credits(request: Request, guest_token: str):
    """Return remaining guest credits for a given token."""
    from app.data.auth_db import get_guest_credits_used
    ip = _get_client_ip(request)
    guest_id = _make_guest_id(ip, guest_token)
    used = get_guest_credits_used(guest_id)
    remaining = max(0, GUEST_CREDIT_LIMIT - used)
    return {"used": used, "limit": GUEST_CREDIT_LIMIT, "remaining": remaining}


@router.post("/query/preview")
@limiter.limit("5/day")
async def query_preview(
    request: Request,
    body: PreviewQueryRequest,
    embedding_service=Depends(get_embedding_service),
    retrieval_service=Depends(get_retrieval_service),
    generation_service=Depends(get_generation_service),
    mcp_service=Depends(get_mcp_service),
):
    """Full-capability guest query — costs 1 credit."""
    ip = _get_client_ip(request)
    guest_id = _make_guest_id(ip, body.guest_token)

    allowed, used, limit = check_and_consume_guest(guest_id, cost=QUERY_COST)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "guest_limit_reached",
                "message": "You've used all 3 free credits. Sign up free for 10 credits per day.",
                "used": used,
                "limit": limit,
            },
        )

    service = QueryService(
        embedding_service=embedding_service,
        retrieval_service=retrieval_service,
        generation_service=generation_service,
        mcp_service=mcp_service,
    )

    query_req = QueryRequest(
        question=body.question,
        company=body.company,
        top_k=body.top_k,
        include_sources=body.include_sources,
    )

    async def event_generator():
        try:
            query_type = service._mcp.classify_query(body.question)
            entities = service._mcp.extract_entities(body.question)
            if body.company:
                entities["company"] = body.company
                entities.pop("ticker", None)
            where_filter = service._mcp.build_metadata_filters(entities, None)

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
                    logger.warning("preview_structured_context_failed", error=str(e))

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
                yield f"data: {json.dumps({'type': 'token', 'text': 'No data found for this company yet. Try TATASTEEL, HDFCBANK, or RELIANCE.'})}\n\n"
            else:
                async for token in service._generation.stream_generate(
                    question=body.question,
                    context=context_str,
                    query_type=query_type,
                ):
                    yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

            consume_guest_credit(guest_id, cost=QUERY_COST)
            remaining = max(0, GUEST_CREDIT_LIMIT - (used + QUERY_COST))
            yield f"data: {json.dumps({'type': 'done', 'credits_remaining': remaining})}\n\n"

        except HTTPException:
            raise
        except Exception as exc:
            logger.error("preview_query_failed", error=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'text': 'Something went wrong. Please try again.'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/forecast/preview", response_model=ForecastResponse)
@limiter.limit("3/day")
async def forecast_preview(
    request: Request,
    body: PreviewForecastRequest,
    generation_service=Depends(get_generation_service),
    embedding_service=Depends(get_embedding_service),
    retrieval_service=Depends(get_retrieval_service),
):
    """Multi-agent event forecast for guests — costs 2 credits."""
    ip = _get_client_ip(request)
    guest_id = _make_guest_id(ip, body.guest_token)

    allowed, used, limit = check_and_consume_guest(guest_id, cost=FORECAST_COST)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "guest_limit_reached",
                "message": "Not enough credits. Forecasts cost 2 credits. Sign up free for 10 credits per day.",
                "used": used,
                "limit": limit,
            },
        )

    service = ForecastService(
        generation_service=generation_service,
        embedding_service=embedding_service,
        retrieval_service=retrieval_service,
    )

    forecast_req = ForecastRequest(
        company=body.company,
        event_type=body.event_type,
        event_description=body.event_description,
        horizon_days=body.horizon_days,
    )

    try:
        result = await service.forecast(forecast_req)
        consume_guest_credit(guest_id, cost=FORECAST_COST)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("preview_forecast_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Forecast failed. Please try again.",
        ) from exc
