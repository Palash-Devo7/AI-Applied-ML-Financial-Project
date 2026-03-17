"""Company loader — auto-fetches BSE data and ingests PDFs into the RAG pipeline.

Flow per company:
  1. Resolve ticker → scrip_code
  2. Fetch financials → SQLite
  3. Fetch relevant announcements → filter PDFs
  4. Download + ingest PDFs into ChromaDB via existing IngestionService
  5. Mark company as ready in company_registry
"""
from __future__ import annotations

import asyncio
import structlog
from functools import lru_cache

from app.services.providers.bse_provider import BSEProvider

logger = structlog.get_logger(__name__)

MAX_PDFS = 6  # max PDFs to ingest per company load (most recent first)


def _get_provider() -> BSEProvider:
    """Swap provider here — change BSEProvider to any other implementation."""
    return BSEProvider()


class CompanyLoader:
    def __init__(self, ingestion_service) -> None:
        self._ingestion = ingestion_service
        self._provider = _get_provider()

    async def load(self, ticker: str, company_display_name: str | None = None) -> dict:
        """
        Full company load. Returns status dict.
        Designed to run as a background task.
        """
        from app.data.financial_db import (
            register_company, update_company_status,
            update_docs_synced, upsert_financials, upsert_ticker,
        )

        ticker = ticker.upper().strip()
        logger.info("company_load_started", ticker=ticker)

        # 1. Resolve scrip code
        try:
            scrip_code = await asyncio.to_thread(self._provider.get_scrip_code, ticker)
        except Exception as exc:
            logger.error("scrip_code_failed", ticker=ticker, error=str(exc))
            return {"status": "failed", "error": f"Ticker not found on BSE: {ticker}"}

        # 2. Get company name
        try:
            bse_name = await asyncio.to_thread(self._provider.get_company_name, scrip_code)
            company = company_display_name or bse_name or ticker
        except Exception:
            company = company_display_name or ticker

        # Register immediately so UI can show "loading" status
        register_company(company, ticker, scrip_code)
        update_company_status(company, "loading")

        try:
            # 3. Fetch financials → SQLite
            await self._fetch_financials(company, ticker, scrip_code)

            # 4. Fetch + ingest PDFs
            doc_count = await self._fetch_and_ingest_pdfs(company, ticker, scrip_code)

            # 5. Mark ready
            update_docs_synced(company, doc_count)
            update_company_status(company, "ready")
            logger.info("company_load_complete", company=company, docs=doc_count)
            return {"status": "ready", "company": company, "doc_count": doc_count}

        except Exception as exc:
            error_msg = str(exc)[:300]
            update_company_status(company, "failed", error_msg)
            logger.error("company_load_failed", company=company, error=error_msg)
            return {"status": "failed", "error": error_msg}

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _fetch_financials(self, company: str, ticker: str, scrip_code: str) -> None:
        from app.data.financial_db import upsert_financials, upsert_ticker, upsert_stock_prices

        # Register ticker mapping
        upsert_ticker(company, ticker)

        # Fetch results snapshot from BSE
        try:
            snapshot = await asyncio.to_thread(self._provider.get_financials, scrip_code)
            records = _parse_snapshot_to_records(company, ticker, snapshot)
            if records:
                upsert_financials(records)
                logger.info("financials_stored", company=company, records=len(records))
        except Exception as exc:
            logger.warning("financials_fetch_failed", company=company, error=str(exc))

        # Fetch live price
        try:
            price = await asyncio.to_thread(self._provider.get_price, scrip_code)
            if price.get("LTP"):
                from datetime import date
                upsert_stock_prices([{
                    "company": company, "ticker": ticker,
                    "date": str(date.today()),
                    "open": price.get("Open"), "high": price.get("High"),
                    "low": price.get("Low"), "close": price.get("LTP"),
                    "volume": None,
                }])
        except Exception as exc:
            logger.warning("price_fetch_failed", company=company, error=str(exc))

    async def _fetch_and_ingest_pdfs(self, company: str, ticker: str, scrip_code: str) -> int:
        announcements = await asyncio.to_thread(
            self._provider.get_announcements, scrip_code, 365
        )

        # Take most recent MAX_PDFS
        to_ingest = announcements[:MAX_PDFS]
        ingested = 0

        for ann in to_ingest:
            attachment = ann.get("ATTACHMENTNAME", "")
            category = ann.get("CATEGORYNAME", "Document")
            news_dt = ann.get("NEWS_DT", "")
            year = int(news_dt[:4]) if news_dt else 2024

            try:
                pdf_bytes = await asyncio.to_thread(self._provider.download_pdf, attachment)
                await self._ingestion.ingest(
                    content=pdf_bytes,
                    filename=attachment,
                    overrides={
                        "company": company,
                        "ticker": ticker,
                        "year": year,
                        "report_type": category,
                    },
                )
                ingested += 1
                logger.info("pdf_ingested", company=company, attachment=attachment)
                await asyncio.sleep(1)  # polite delay between downloads
            except Exception as exc:
                logger.warning("pdf_ingest_failed", attachment=attachment, error=str(exc))

        return ingested


# ── Parser ─────────────────────────────────────────────────────────────────────

def _parse_snapshot_to_records(company: str, ticker: str, snapshot: dict) -> list[dict]:
    """Convert BSE resultsSnapshot() into financial_db upsert records."""
    records = []
    periods = snapshot.get("periods", [])
    data = snapshot.get("results_in_crores", {}).get("data", [])

    if not periods or not data:
        return records

    # Build period → values mapping
    period_data: dict[str, dict] = {p: {} for p in periods}
    for row in data:
        field_name = row[0]
        for i, period in enumerate(periods, 1):
            if i < len(row):
                try:
                    val = float(str(row[i]).replace(",", ""))
                    period_data[period][field_name] = val
                except (ValueError, TypeError):
                    pass

    for period, values in period_data.items():
        if not values:
            continue
        # Determine if annual or quarterly
        is_annual = period.startswith("FY")
        fiscal_year = _extract_year(period)
        fiscal_quarter = "Annual" if is_annual else _period_to_quarter(period)

        records.append({
            "company": company,
            "ticker": ticker,
            "fiscal_year": fiscal_year,
            "fiscal_quarter": fiscal_quarter,
            "period_end_date": None,
            "revenue": values.get("Revenue"),
            "net_income": values.get("Net Profit"),
            "ebitda": None,
            "eps": values.get("EPS"),
            "total_assets": None,
            "total_debt": None,
            "cash": None,
            "operating_cash_flow": None,
            "gross_margin": values.get("OPM %"),
            "net_margin": values.get("NPM %"),
        })

    return records


def _extract_year(period: str) -> int:
    """Extract fiscal year from period string like 'FY24-25' or 'Dec-25'."""
    import re
    m = re.search(r"(\d{2,4})", period)
    if not m:
        return 2024
    yr = int(m.group(1))
    return yr + 2000 if yr < 100 else yr


def _period_to_quarter(period: str) -> str:
    """Map 'Dec-25' → 'Q3', 'Sep-25' → 'Q2' etc."""
    month_map = {
        "Jun": "Q1", "Sep": "Q2", "Dec": "Q3", "Mar": "Q4",
        "Jan": "Q3", "Feb": "Q3", "Apr": "Q1", "May": "Q1",
        "Jul": "Q2", "Aug": "Q2", "Oct": "Q3", "Nov": "Q3",
    }
    for month, quarter in month_map.items():
        if period.startswith(month):
            return quarter
    return "Q1"
