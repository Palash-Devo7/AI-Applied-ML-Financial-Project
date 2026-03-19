"""Company registry router — auto-load company data from BSE."""
import asyncio

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.core.auth_deps import get_current_user, require_credits, consume_after_success
from app.dependencies import get_embedding_service, get_vector_store
from app.core.limiter import limiter

router = APIRouter(prefix="/companies", tags=["companies"])
logger = structlog.get_logger(__name__)


class LoadRequest(BaseModel):
    ticker: str
    company_name: str | None = None
    force: bool = False


@router.post("/load", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def load_company(
    request: Request,
    req: LoadRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_credits),
    embedding_service=Depends(get_embedding_service),
    vector_store=Depends(get_vector_store),
):
    """Trigger auto-load of a BSE-listed company. Runs in background. Pass force=true to reload."""
    from app.data.financial_db import get_registry_by_ticker, register_company, update_company_status
    from app.services.company_loader import CompanyLoader
    from app.services.ingestion_service import IngestionService

    ticker = req.ticker.upper().strip()

    # Check if already loading or loaded (skip if force=true)
    existing = get_registry_by_ticker(ticker)
    if not req.force:
        if existing and existing.get("status") == "loading":
            return {"status": "loading", "message": "Already loading, please wait."}
        if existing and existing.get("status") == "ready":
            return {"status": "ready", "company": existing["company"], "message": "Already loaded."}

    ingestion_service = IngestionService(
        embedding_service=embedding_service,
        vector_store=vector_store,
    )
    loader = CompanyLoader(ingestion_service=ingestion_service)

    async def _run():
        await loader.load(ticker=ticker, company_display_name=req.company_name)

    background_tasks.add_task(_run)
    consume_after_success(request)
    return {"status": "loading", "ticker": ticker, "message": "Load started in background."}


@router.get("/status/{ticker}")
async def company_status(ticker: str, user: dict = Depends(get_current_user)):
    """Get load status for a ticker."""
    from app.data.financial_db import get_registry_by_ticker
    record = get_registry_by_ticker(ticker.upper())
    if not record:
        return {"status": "not_loaded", "ticker": ticker}
    return record


@router.get("/list")
async def list_companies(user: dict = Depends(get_current_user)):
    """List all registered companies with their load status."""
    from app.data.financial_db import list_registered_companies
    return {"companies": list_registered_companies()}


@router.get("/search")
async def search_companies(q: str = "", user: dict = Depends(get_current_user)):
    """Search BSE-listed companies by name or ticker. Powered by in-memory cache."""
    if not q or len(q.strip()) < 2:
        return {"results": [], "query": q}
    from app.services.providers.bse_provider import BSEProvider
    results = BSEProvider.search(q.strip(), limit=15)
    return {"results": results, "query": q}
