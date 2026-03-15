"""Market data router — financial history, stock prices, and events."""
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.data.financial_db import (
    get_events,
    get_financials,
    get_quarterly_financials,
    get_stock_summary,
    get_ticker,
    insert_event,
    list_tickers,
    search_similar_events,
)
from app.services.market_data_service import get_market_data_service

router = APIRouter(prefix="/market", tags=["market-data"])
logger = structlog.get_logger(__name__)


# ── Request / Response models ─────────────────────────────────────────────────

class FetchRequest(BaseModel):
    company: str = Field(..., description="Company name as stored in knowledge base")
    ticker:  str = Field(..., description="Exchange ticker, e.g. TATASTEEL.NS or RELIANCE.NS")
    period:  str = Field("5y", description="yfinance period: 1y, 2y, 5y, 10y, max")


class EventCreate(BaseModel):
    company:      str   = Field(..., description="Company name")
    ticker:       Optional[str] = None
    event_date:   str   = Field(..., description="Date in YYYY-MM-DD format")
    event_type:   str   = Field(..., description="EARNINGS | MACRO | SECTOR | REGULATORY | M&A | MANAGEMENT")
    title:        str   = Field(..., min_length=3)
    description:  Optional[str] = None
    impact_score: float = Field(0.0, ge=-1.0, le=1.0, description="-1 = very bearish, +1 = very bullish")
    source:       Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/fetch")
async def fetch_market_data(req: FetchRequest, background_tasks: BackgroundTasks):
    """
    Trigger a background fetch of financials + stock prices from Yahoo Finance.
    Returns immediately — check /market/financials/{company} after a few seconds.
    """
    svc = get_market_data_service()
    background_tasks.add_task(svc.async_fetch_all, req.company, req.ticker, req.period)
    logger.info("market_fetch_queued", company=req.company, ticker=req.ticker)
    return {
        "status": "fetching",
        "company": req.company,
        "ticker": req.ticker,
        "message": f"Fetching {req.period} of data for {req.ticker} in background.",
    }


@router.post("/fetch/sync")
async def fetch_market_data_sync(req: FetchRequest):
    """Synchronous fetch — waits for completion. Use for small tickers or testing."""
    svc = get_market_data_service()
    try:
        result = await svc.async_fetch_all(req.company, req.ticker, req.period)
        return {"status": "complete", **result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/tickers")
async def list_registered_tickers():
    """List all company → ticker mappings in the database."""
    return {"tickers": list_tickers()}


@router.get("/financials/{company}")
async def get_company_financials(company: str, years: int = 5):
    """Get annual financial history for a company."""
    data = get_financials(company, years)
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"No financial data for '{company}'. Use POST /market/fetch to load data.",
        )
    return {
        "company": company,
        "ticker": get_ticker(company),
        "annual_financials": data,
        "count": len(data),
    }


@router.get("/financials/{company}/quarterly")
async def get_quarterly(company: str, limit: int = 8):
    """Get quarterly financial history."""
    data = get_quarterly_financials(company, limit)
    return {"company": company, "quarterly_financials": data, "count": len(data)}


@router.get("/stock/{ticker}")
async def get_stock_history(ticker: str, days: int = 365):
    """Get OHLCV stock price history."""
    from app.data.financial_db import get_stock_prices
    data = get_stock_prices(ticker, days)
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"No price data for '{ticker}'. Use POST /market/fetch to load data.",
        )
    summary = get_stock_summary(ticker)
    return {
        "ticker": ticker,
        "summary": summary,
        "prices": data,
        "count": len(data),
    }


@router.get("/stock/{ticker}/summary")
async def get_stock_info(ticker: str):
    """Get 52-week summary for a ticker."""
    summary = get_stock_summary(ticker)
    if not summary:
        raise HTTPException(status_code=404, detail=f"No data for {ticker}.")
    return {"ticker": ticker, "summary": summary}


# ── Events ────────────────────────────────────────────────────────────────────

@router.post("/events")
async def create_event(event: EventCreate):
    """Manually add a financial event (earnings, macro shock, regulatory change, etc.)."""
    ev_id = insert_event(event.model_dump())
    logger.info("event_created", id=ev_id, company=event.company, type=event.event_type)
    return {"id": ev_id, "status": "created", **event.model_dump()}


@router.get("/events/{company}")
async def get_company_events(company: str, limit: int = 20):
    """Get all events for a company, newest first."""
    events = get_events(company, limit)
    return {"company": company, "events": events, "count": len(events)}


@router.get("/events/similar/{event_type}")
async def find_similar_events(event_type: str, exclude_company: Optional[str] = None, limit: int = 5):
    """
    Find historical events of the same type across other companies.
    Useful for analogical forecasting: 'what happened to other companies during similar MACRO events?'
    """
    events = search_similar_events(event_type, exclude_company, limit)
    return {
        "event_type": event_type,
        "similar_events": events,
        "count": len(events),
        "note": "Use these as analogical anchors for forecasting.",
    }
