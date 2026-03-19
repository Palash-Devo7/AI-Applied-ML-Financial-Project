"""Forecast router: POST /forecast/event"""
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.auth_deps import require_credits, consume_after_success
from app.dependencies import (
    get_embedding_service,
    get_generation_service,
    get_retrieval_service,
)
from app.core.limiter import limiter
from app.models.forecast import ForecastRequest, ForecastResponse
from app.services.forecast_service import ForecastService

router = APIRouter(prefix="/forecast", tags=["forecast"])
logger = structlog.get_logger(__name__)


@router.post(
    "/event",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Multi-agent event-based financial forecast (Bull + Bear + Macro → Synthesis)",
)
@limiter.limit("10/minute")
async def forecast_event(
    request: Request,
    body: ForecastRequest,
    user: dict = Depends(require_credits),
    generation_service=Depends(get_generation_service),
    embedding_service=Depends(get_embedding_service),
    retrieval_service=Depends(get_retrieval_service),
) -> ForecastResponse:
    service = ForecastService(
        generation_service=generation_service,
        embedding_service=embedding_service,
        retrieval_service=retrieval_service,
    )
    try:
        result = await service.forecast(body)
        consume_after_success(request)
        return result
    except Exception as exc:
        logger.error("forecast_endpoint_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Forecast failed. Please try again.",
        ) from exc
