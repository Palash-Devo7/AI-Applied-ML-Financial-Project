"""Company registry router — auto-load company data from BSE."""
import asyncio

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from app.dependencies import get_embedding_service, get_vector_store

router = APIRouter(prefix="/companies", tags=["companies"])
logger = structlog.get_logger(__name__)


class LoadRequest(BaseModel):
    ticker: str
    company_name: str | None = None


@router.post("/load", status_code=status.HTTP_202_ACCEPTED)
async def load_company(
    req: LoadRequest,
    background_tasks: BackgroundTasks,
    embedding_service=Depends(get_embedding_service),
    vector_store=Depends(get_vector_store),
):
    """Trigger auto-load of a BSE-listed company. Runs in background."""
    from app.data.financial_db import get_registry_by_ticker, register_company, update_company_status
    from app.services.company_loader import CompanyLoader
    from app.services.ingestion_service import IngestionService

    ticker = req.ticker.upper().strip()

    # Check if already loading
    existing = get_registry_by_ticker(ticker)
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
    return {"status": "loading", "ticker": ticker, "message": "Load started in background."}


@router.get("/status/{ticker}")
async def company_status(ticker: str):
    """Get load status for a ticker."""
    from app.data.financial_db import get_registry_by_ticker
    record = get_registry_by_ticker(ticker.upper())
    if not record:
        return {"status": "not_loaded", "ticker": ticker}
    return record


@router.get("/list")
async def list_companies():
    """List all registered companies with their load status."""
    from app.data.financial_db import list_registered_companies
    return {"companies": list_registered_companies()}
