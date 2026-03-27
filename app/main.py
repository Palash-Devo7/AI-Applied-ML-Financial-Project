"""FastAPI application factory with lifespan management."""
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.core.limiter import limiter
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

    # Initialise auth DB + seed admin user
    try:
        from app.data.auth_db import init_auth_db, user_exists, create_user
        from app.core.security import hash_password, generate_api_key
        init_auth_db()
        logger.info("auth_db_initialised")

        if settings.admin_password and not user_exists(settings.admin_email):
            api_key = generate_api_key()
            create_user(
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                role="admin",
                api_key=api_key,
            )
            logger.info("admin_user_created", email=settings.admin_email[:3] + "***", api_key=api_key[:6] + "***")
    except Exception as exc:
        logger.error("auth_db_init_failed", error=str(exc))

    # Eagerly initialise singletons
    from app.dependencies import (
        _get_embedding_service_singleton,
        _get_mcp_service_singleton,
        _get_retrieval_service_singleton,
        _get_vector_store_singleton,
    )

    try:
        _get_vector_store_singleton()
        logger.info("vector_store_initialised")
    except Exception as exc:
        logger.error("vector_store_init_failed", error=str(exc))

    try:
        _get_embedding_service_singleton()
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

    try:
        from app.data.financial_db import init_db
        init_db()
        logger.info("financial_db_initialised")
    except Exception as exc:
        logger.error("financial_db_init_failed", error=str(exc))

    try:
        from app.services.providers.bse_provider import BSEProvider
        count = await asyncio.to_thread(BSEProvider.load_securities_cache)
        logger.info("bse_securities_cache_ready", count=count)
    except Exception as exc:
        logger.warning("bse_securities_cache_failed", error=str(exc))

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

    # ── Rate limiter ──────────────────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS — restrict to known origins only ─────────────────────────────────
    origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.add_middleware(RequestLoggingMiddleware)

    # ── Security headers middleware ────────────────────────────────────────────
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.routers import auth, collections, companies, feedback, forecast, health, ingestion, market_data, query, preview

    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(preview.router)
    app.include_router(ingestion.router, prefix="/documents")
    app.include_router(query.router)
    app.include_router(collections.router)
    app.include_router(market_data.router)
    app.include_router(forecast.router)
    app.include_router(companies.router)
    app.include_router(feedback.router)

    # ── Exception handlers ────────────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc):
        logger.error("unhandled_exception", error=str(exc), path=str(request.url))
        return JSONResponse(
            status_code=500,
            content={"detail": "An error occurred. Please try again or contact support."},
        )

    return app


app = create_app()
