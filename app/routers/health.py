"""Health check and metrics endpoints."""
import time

import structlog
from fastapi import APIRouter, Depends, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.dependencies import get_embedding_service, get_vector_store
from app.monitoring.metrics import CHROMA_COLLECTION_SIZE

router = APIRouter(tags=["health"])
logger = structlog.get_logger(__name__)


@router.get("/health")
async def health_check(
    vector_store=Depends(get_vector_store),
    embedding_service=Depends(get_embedding_service),
) -> dict:
    """Comprehensive health check for all downstream services."""
    services: dict[str, str] = {}
    overall_status = "ok"

    # ChromaDB check
    try:
        count = await vector_store.count()
        services["chroma"] = "ok"
        # Update gauge
        from app.config import get_settings
        settings = get_settings()
        CHROMA_COLLECTION_SIZE.labels(
            collection_name=settings.chroma_collection_name
        ).set(count)
    except Exception as exc:
        logger.error("chroma_health_failed", error=str(exc))
        services["chroma"] = f"error: {exc}"
        overall_status = "degraded"

    # FinBERT check
    try:
        ready = embedding_service.is_ready()
        services["finbert"] = "ok" if ready else "loading"
        if not ready:
            overall_status = "degraded"
    except Exception as exc:
        logger.error("finbert_health_failed", error=str(exc))
        services["finbert"] = f"error: {exc}"
        overall_status = "degraded"

    # Claude API check (lightweight — just verify key is configured)
    try:
        from app.config import get_settings
        settings = get_settings()
        if settings.anthropic_api_key and len(settings.anthropic_api_key) > 10:
            services["claude"] = "ok"
        else:
            services["claude"] = "missing_api_key"
            overall_status = "degraded"
    except Exception as exc:
        services["claude"] = f"error: {exc}"
        overall_status = "degraded"

    return {
        "status": overall_status,
        "services": services,
        "timestamp": time.time(),
    }


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Expose Prometheus metrics in text format."""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
