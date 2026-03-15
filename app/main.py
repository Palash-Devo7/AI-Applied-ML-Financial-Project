"""FastAPI application factory with lifespan management."""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.monitoring.logger import configure_logging
from app.monitoring.middleware import RequestLoggingMiddleware

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle management."""
    settings = get_settings()
    configure_logging(settings.log_level)

    logger.info(
        "application_starting",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    # Eagerly initialise singletons so they are ready before first request
    from app.dependencies import (
        _get_embedding_service_singleton,
        _get_mcp_service_singleton,
        _get_retrieval_service_singleton,
        _get_vector_store_singleton,
    )

    try:
        vector_store = _get_vector_store_singleton()
        logger.info("vector_store_initialised")
    except Exception as exc:
        logger.error("vector_store_init_failed", error=str(exc))

    try:
        embedding_service = _get_embedding_service_singleton()
        logger.info("embedding_service_initialised", model=settings.embedding_model)
    except Exception as exc:
        logger.error("embedding_service_init_failed", error=str(exc))

    try:
        _get_retrieval_service_singleton()
        logger.info("retrieval_service_initialised")
    except Exception as exc:
        logger.error("retrieval_service_init_failed", error=str(exc))

    try:
        _get_mcp_service_singleton()
        logger.info("mcp_service_initialised")
    except Exception as exc:
        logger.error("mcp_service_init_failed", error=str(exc))

    # Initialise structured financial database
    try:
        from app.data.financial_db import init_db
        init_db()
        logger.info("financial_db_initialised")
    except Exception as exc:
        logger.error("financial_db_init_failed", error=str(exc))

    logger.info("application_ready")
    yield

    logger.info("application_shutting_down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Finance AI RAG System — hybrid retrieval with FinBERT + Claude",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.routers import collections, health, ingestion, market_data, query

    app.include_router(health.router)
    app.include_router(ingestion.router, prefix="/documents")
    app.include_router(query.router)
    app.include_router(collections.router)
    app.include_router(market_data.router)

    # ── Exception handlers ────────────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc):
        logger.error("unhandled_exception", error=str(exc), path=str(request.url))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": type(exc).__name__},
        )

    return app


app = create_app()
