"""Market data service — fetches historical financials and stock prices via yfinance."""
import asyncio
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional

import structlog

from app.data.financial_db import (
    get_financials,
    get_stock_prices,
    get_stock_summary,
    get_ticker,
    upsert_financials,
    upsert_stock_prices,
    upsert_ticker,
)

logger = structlog.get_logger(__name__)


def _import_yfinance():
    try:
        import yfinance as yf
        return yf
    except ImportError:
        raise RuntimeError("yfinance not installed. Run: pip install yfinance")


class MarketDataService:
    """Fetches and caches financial data from Yahoo Finance."""

    # ── Ticker resolution ─────────────────────────────────────────────────────

    def register_ticker(self, company: str, ticker: str, exchange: str = "NSE") -> None:
        """Map a company name to its exchange ticker (e.g. 'Tata Steel' → 'TATASTEEL.NS')."""
        upsert_ticker(company, ticker, exchange)
        logger.info("ticker_registered", company=company, ticker=ticker)

    def resolve_ticker(self, company: str) -> Optional[str]:
        return get_ticker(company)

    # ── Fetch from Yahoo Finance ───────────────────────────────────────────────

    def fetch_financials(self, company: str, ticker: str) -> dict:
        """
        Fetch annual + quarterly income statement data from yfinance and persist to SQLite.
        Returns counts of records inserted.
        """
        yf = _import_yfinance()
        self.register_ticker(company, ticker)

        stock = yf.Ticker(ticker)
        records = []

        # Annual income statement
        try:
            fin = stock.financials  # columns = fiscal year end dates
            bs  = stock.balance_sheet
            cf  = stock.cashflow

            for col in fin.columns:
                year = col.year if hasattr(col, "year") else int(str(col)[:4])
                period_date = str(col)[:10]

                def safe(df, row):
                    try:
                        v = df.loc[row, col] if row in df.index else None
                        return float(v) if v is not None and str(v) != "nan" else None
                    except Exception:
                        return None

                revenue    = safe(fin, "Total Revenue")
                net_income = safe(fin, "Net Income")
                gross_prof = safe(fin, "Gross Profit")
                ebitda     = safe(fin, "EBITDA") or safe(fin, "Normalized EBITDA")
                total_assets = safe(bs, "Total Assets")
                total_debt   = safe(bs, "Total Debt") or safe(bs, "Long Term Debt")
                cash         = safe(bs, "Cash And Cash Equivalents") or safe(bs, "Cash")
                op_cf        = safe(cf, "Operating Cash Flow") or safe(cf, "Total Cash From Operating Activities")

                gross_margin = (gross_prof / revenue * 100) if gross_prof and revenue else None
                net_margin   = (net_income / revenue * 100) if net_income and revenue else None

                # EPS from info
                eps = None
                try:
                    eps = float(stock.info.get("trailingEps") or 0) or None
                except Exception:
                    pass

                records.append({
                    "company": company, "ticker": ticker,
                    "fiscal_year": year, "fiscal_quarter": "Annual",
                    "period_end_date": period_date,
                    "revenue": revenue, "net_income": net_income,
                    "ebitda": ebitda, "eps": eps,
                    "total_assets": total_assets, "total_debt": total_debt,
                    "cash": cash, "operating_cash_flow": op_cf,
                    "gross_margin": gross_margin, "net_margin": net_margin,
                })
        except Exception as e:
            logger.warning("annual_financials_fetch_failed", ticker=ticker, error=str(e))

        # Quarterly income statement
        try:
            qfin = stock.quarterly_financials
            for col in qfin.columns:
                year = col.year if hasattr(col, "year") else int(str(col)[:4])
                # Determine quarter
                month = col.month if hasattr(col, "month") else int(str(col)[5:7])
                quarter = f"Q{(month - 1) // 3 + 1}"
                period_date = str(col)[:10]

                def safe_q(row):
                    try:
                        v = qfin.loc[row, col] if row in qfin.index else None
                        return float(v) if v is not None and str(v) != "nan" else None
                    except Exception:
                        return None

                revenue    = safe_q("Total Revenue")
                net_income = safe_q("Net Income")
                gross_prof = safe_q("Gross Profit")
                gross_margin = (gross_prof / revenue * 100) if gross_prof and revenue else None
                net_margin   = (net_income / revenue * 100) if net_income and revenue else None

                records.append({
                    "company": company, "ticker": ticker,
                    "fiscal_year": year, "fiscal_quarter": quarter,
                    "period_end_date": period_date,
                    "revenue": revenue, "net_income": net_income,
                    "ebitda": None, "eps": None,
                    "total_assets": None, "total_debt": None,
                    "cash": None, "operating_cash_flow": None,
                    "gross_margin": gross_margin, "net_margin": net_margin,
                })
        except Exception as e:
            logger.warning("quarterly_financials_fetch_failed", ticker=ticker, error=str(e))

        inserted = upsert_financials(records)
        logger.info("financials_fetched", company=company, ticker=ticker, records=len(records))
        return {"company": company, "ticker": ticker, "records_upserted": len(records)}

    def fetch_stock_prices(self, company: str, ticker: str, period: str = "5y") -> dict:
        """Fetch historical OHLCV data and persist to SQLite."""
        yf = _import_yfinance()
        self.register_ticker(company, ticker)

        stock = yf.Ticker(ticker)
        try:
            hist = stock.history(period=period)
        except Exception as e:
            raise RuntimeError(f"Failed to fetch prices for {ticker}: {e}")

        records = []
        for date, row in hist.iterrows():
            date_str = str(date)[:10]
            records.append({
                "company": company, "ticker": ticker, "date": date_str,
                "open":   float(row.get("Open", 0) or 0),
                "high":   float(row.get("High", 0) or 0),
                "low":    float(row.get("Low", 0) or 0),
                "close":  float(row.get("Close", 0) or 0),
                "volume": int(row.get("Volume", 0) or 0),
            })

        inserted = upsert_stock_prices(records)
        logger.info("stock_prices_fetched", company=company, ticker=ticker, records=len(records))
        return {"company": company, "ticker": ticker, "records_upserted": len(records)}

    def fetch_all(self, company: str, ticker: str, period: str = "5y") -> dict:
        """Convenience: fetch both financials and stock prices in one call."""
        fin_result   = self.fetch_financials(company, ticker)
        price_result = self.fetch_stock_prices(company, ticker, period)
        return {
            "company": company, "ticker": ticker,
            "financials_upserted": fin_result["records_upserted"],
            "prices_upserted":     price_result["records_upserted"],
        }

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_financials(self, company: str, years: int = 5) -> list:
        return get_financials(company, years)

    def get_stock_prices(self, ticker: str, days: int = 365) -> list:
        return get_stock_prices(ticker, days)

    def get_stock_summary(self, ticker: str) -> Optional[dict]:
        return get_stock_summary(ticker)

    def get_ticker(self, company: str) -> Optional[str]:
        return get_ticker(company)

    # ── Async wrappers ─────────────────────────────────────────────────────────

    async def async_fetch_all(self, company: str, ticker: str, period: str = "5y") -> dict:
        """Run blocking yfinance calls in a thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.fetch_all, company, ticker, period)

    async def async_fetch_financials(self, company: str, ticker: str) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.fetch_financials, company, ticker)

    async def async_fetch_stock_prices(self, company: str, ticker: str, period: str = "5y") -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.fetch_stock_prices, company, ticker, period)


@lru_cache(maxsize=1)
def get_market_data_service() -> MarketDataService:
    return MarketDataService()
