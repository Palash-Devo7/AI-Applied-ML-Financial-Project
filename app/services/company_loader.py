"""Company loader — resolves canonical name, fetches from BSE + yfinance, ingests PDFs.

Flow per company:
  1. BSE: ticker → scrip_code → canonical name (from listSecurities Scrip_Name)
  2. BSE: scrip_code → ISIN → Yahoo Finance search → yfinance ticker (e.g. TATASTEEL.NS)
  3. BSE: recent financials (last 2Q + FY annual) → SQLite under canonical name
  4. BSE: live price → SQLite
  5. yfinance: 5yr annual + quarterly history + balance sheet → SQLite under canonical name
  6. yfinance: 5yr daily price history → SQLite
  7. BSE: announcements → filter → download PDFs → ChromaDB (tagged canonical name)
  8. company_registry: status = ready
"""
from __future__ import annotations

import asyncio
import structlog

from app.services.providers.bse_provider import BSEProvider
from app.services.providers.yfinance_provider import YFinanceProvider

logger = structlog.get_logger(__name__)

MAX_PDFS = 6


class CompanyLoader:
    def __init__(self, ingestion_service) -> None:
        self._ingestion = ingestion_service
        self._bse       = BSEProvider()
        self._yf        = YFinanceProvider()

    async def load(self, ticker: str, company_display_name: str | None = None) -> dict:
        """Full company load. Designed to run as a background task."""
        from app.data.financial_db import (
            register_company, update_company_status,
            update_docs_synced, update_prices_synced,
            upsert_financials, upsert_stock_prices, upsert_ticker,
        )

        ticker = ticker.upper().strip()
        logger.info("company_load_started", ticker=ticker)

        # 1. Resolve scrip code
        try:
            scrip_code = await asyncio.to_thread(self._bse.get_scrip_code, ticker)
        except Exception as exc:
            logger.error("scrip_code_failed", ticker=ticker, error=str(exc))
            return {"status": "failed", "error": f"Ticker not found on BSE: {ticker}"}

        # 2. Resolve canonical name (from BSE listSecurities Scrip_Name)
        try:
            canonical_name = await asyncio.to_thread(self._bse.get_canonical_name, scrip_code)
        except Exception:
            canonical_name = company_display_name or ticker
        company = company_display_name or canonical_name

        # 3. Resolve ISIN → yfinance ticker
        yf_ticker = None
        try:
            isin = await asyncio.to_thread(self._bse.get_isin, scrip_code)
            if isin:
                yf_ticker = await asyncio.to_thread(self._bse.resolve_yfinance_ticker, isin)
                if yf_ticker:
                    logger.info("yfinance_ticker_resolved", company=company, isin=isin, yf_ticker=yf_ticker)
        except Exception as exc:
            logger.warning("isin_resolve_failed", company=company, error=str(exc))

        # Register immediately so UI can show "loading"
        register_company(company, ticker, scrip_code)
        update_company_status(company, "loading")
        upsert_ticker(company, ticker)
        if yf_ticker:
            upsert_ticker(company, yf_ticker)  # also register yfinance ticker for stock summary

        try:
            # 4. BSE recent financials
            await self._fetch_bse_financials(company, ticker, scrip_code)

            # 5. BSE live price
            await self._fetch_bse_price(company, ticker, scrip_code)
            update_prices_synced(company)

            # 6. yfinance historical financials + prices (if ticker resolved)
            if yf_ticker:
                await self._fetch_yfinance_data(company, yf_ticker)

            # 7. PDFs → ChromaDB
            doc_count = await self._fetch_and_ingest_pdfs(company, ticker, scrip_code)

            update_docs_synced(company, doc_count)
            update_company_status(company, "ready")
            logger.info("company_load_complete", company=company, docs=doc_count, yf_ticker=yf_ticker)
            return {"status": "ready", "company": company, "doc_count": doc_count}

        except Exception as exc:
            error_msg = str(exc)[:300]
            update_company_status(company, "failed", error_msg)
            logger.error("company_load_failed", company=company, error=error_msg)
            return {"status": "failed", "error": error_msg}

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _fetch_bse_financials(self, company: str, ticker: str, scrip_code: str) -> None:
        from app.data.financial_db import upsert_financials, upsert_ticker
        upsert_ticker(company, ticker)
        try:
            records = await asyncio.to_thread(self._bse.get_financials, scrip_code)
            if records:
                # BSEProvider.get_financials() already returns values in Crores
                db_records = [
                    {
                        "company":         company,
                        "ticker":          ticker,
                        "fiscal_year":     r["fiscal_year"],
                        "fiscal_quarter":  r["fiscal_quarter"],
                        "period_end_date": None,
                        "revenue":         r.get("revenue"),
                        "net_income":      r.get("net_income"),
                        "ebitda":          None,
                        "eps":             r.get("eps"),
                        "total_assets":    None,
                        "total_debt":      None,
                        "cash":            None,
                        "operating_cash_flow": None,
                        "gross_margin":    r.get("gross_margin"),
                        "net_margin":      r.get("net_margin"),
                    }
                    for r in records
                ]
                upsert_financials(db_records)
                logger.info("bse_financials_stored", company=company, records=len(db_records))
        except Exception as exc:
            logger.warning("bse_financials_failed", company=company, error=str(exc))

    async def _fetch_bse_price(self, company: str, ticker: str, scrip_code: str) -> None:
        from app.data.financial_db import upsert_stock_prices
        from datetime import date
        try:
            price = await asyncio.to_thread(self._bse.get_price, scrip_code)
            if price.get("LTP"):
                upsert_stock_prices([{
                    "company": company, "ticker": ticker,
                    "date":    str(date.today()),
                    "open":    price.get("Open"),
                    "high":    price.get("High"),
                    "low":     price.get("Low"),
                    "close":   price.get("LTP"),
                    "volume":  None,
                }])
                logger.info("bse_price_stored", company=company, ltp=price.get("LTP"))
        except Exception as exc:
            logger.warning("bse_price_failed", company=company, error=str(exc))

    async def _fetch_yfinance_data(self, company: str, yf_ticker: str) -> None:
        from app.data.financial_db import upsert_financials, upsert_stock_prices

        # Historical financials (already in Crores from YFinanceProvider)
        try:
            records = await asyncio.to_thread(self._yf.get_financials, yf_ticker)
            if records:
                db_records = [
                    {
                        "company":             company,
                        "ticker":              yf_ticker,
                        "fiscal_year":         r["fiscal_year"],
                        "fiscal_quarter":      r["fiscal_quarter"],
                        "period_end_date":     r.get("period_end_date"),
                        "revenue":             r.get("revenue"),
                        "net_income":          r.get("net_income"),
                        "ebitda":              r.get("ebitda"),
                        "eps":                 r.get("eps"),
                        "total_assets":        r.get("total_assets"),
                        "total_debt":          r.get("total_debt"),
                        "cash":                r.get("cash"),
                        "operating_cash_flow": r.get("operating_cash_flow"),
                        "gross_margin":        r.get("gross_margin"),
                        "net_margin":          r.get("net_margin"),
                    }
                    for r in records
                ]
                upsert_financials(db_records)
                logger.info("yfinance_financials_stored", company=company, records=len(db_records))
        except Exception as exc:
            logger.warning("yfinance_financials_failed", company=company, error=str(exc))

        # Historical prices
        try:
            prices = await asyncio.to_thread(self._yf.get_prices, yf_ticker)
            if prices:
                db_prices = [
                    {"company": company, "ticker": yf_ticker, **p}
                    for p in prices
                ]
                upsert_stock_prices(db_prices)
                logger.info("yfinance_prices_stored", company=company, records=len(db_prices))
        except Exception as exc:
            logger.warning("yfinance_prices_failed", company=company, error=str(exc))

    async def _fetch_and_ingest_pdfs(self, company: str, ticker: str, scrip_code: str) -> int:
        announcements = await asyncio.to_thread(
            self._bse.get_announcements, scrip_code, 365
        )
        to_ingest = announcements[:MAX_PDFS]
        ingested  = 0

        for ann in to_ingest:
            attachment = ann.get("ATTACHMENTNAME", "")
            category   = ann.get("CATEGORYNAME", "Document")
            news_dt    = ann.get("NEWS_DT", "")
            year       = int(news_dt[:4]) if news_dt else 2024

            try:
                pdf_bytes = await asyncio.to_thread(self._bse.download_pdf, attachment)
                await self._ingestion.ingest(
                    content=pdf_bytes,
                    filename=attachment,
                    overrides={
                        "company":     company,
                        "ticker":      ticker,
                        "year":        year,
                        "report_type": category,
                    },
                )
                ingested += 1
                logger.info("pdf_ingested", company=company, attachment=attachment)
                await asyncio.sleep(1)
            except Exception as exc:
                logger.warning("pdf_ingest_failed", attachment=attachment, error=str(exc))

        return ingested
