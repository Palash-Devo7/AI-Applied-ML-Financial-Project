"""Forecast router: POST /forecast/event"""
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    get_embedding_service,
    get_generation_service,
    get_retrieval_service,
)
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
async def forecast_event(
    request: ForecastRequest,
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
        return await service.forecast(request)
    except Exception as exc:
        logger.error("forecast_endpoint_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forecast failed: {exc}",
        ) from exc
