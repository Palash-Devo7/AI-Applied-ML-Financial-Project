"""yfinance provider — historical financials and price history for Indian stocks."""
from __future__ import annotations

from typing import ClassVar

import structlog

logger = structlog.get_logger(__name__)


class YFinanceProvider:
    """
    Fetches deep historical data from Yahoo Finance.

    capabilities:
      - historical_financials : 5yr annual + quarterly income statement, balance sheet, cash flow
      - historical_prices     : daily OHLCV up to 5 years

    All financial values are normalized to CRORES before returning.
    (yfinance returns raw INR; divide by 1e7 to convert to Crores)
    """

    capabilities: ClassVar[frozenset[str]] = frozenset({
        "historical_financials", "historical_prices",
    })

    # ── Financials ─────────────────────────────────────────────────────────────

    def get_financials(self, yf_ticker: str) -> list[dict]:
        """
        Returns annual + quarterly financial records, values in Crores.
        yf_ticker: e.g. 'TATASTEEL.NS'
        """
        try:
            import yfinance as yf
        except ImportError:
            raise RuntimeError("yfinance not installed. Run: pip install yfinance")

        stock   = yf.Ticker(yf_ticker)
        records = []

        # Annual
        try:
            fin = stock.financials
            bs  = stock.balance_sheet
            cf  = stock.cashflow

            for col in fin.columns:
                year        = col.year if hasattr(col, "year") else int(str(col)[:4])
                period_date = str(col)[:10]

                def safe(df, row):
                    try:
                        v = df.loc[row, col] if row in df.index else None
                        return float(v) if v is not None and str(v) != "nan" else None
                    except Exception:
                        return None

                revenue      = safe(fin, "Total Revenue")
                net_income   = safe(fin, "Net Income")
                gross_profit = safe(fin, "Gross Profit")
                ebitda       = safe(fin, "EBITDA") or safe(fin, "Normalized EBITDA")
                total_assets = safe(bs, "Total Assets")
                total_debt   = safe(bs, "Total Debt") or safe(bs, "Long Term Debt")
                cash         = safe(bs, "Cash And Cash Equivalents") or safe(bs, "Cash")
                op_cf        = safe(cf, "Operating Cash Flow") or safe(cf, "Total Cash From Operating Activities")

                gross_margin = (gross_profit / revenue * 100) if gross_profit and revenue else None
                net_margin   = (net_income   / revenue * 100) if net_income   and revenue else None

                eps = None
                try:
                    eps = float(stock.info.get("trailingEps") or 0) or None
                except Exception:
                    pass

                records.append({
                    "fiscal_year":         year,
                    "fiscal_quarter":      "Annual",
                    "period_end_date":     period_date,
                    "revenue":             _to_cr(revenue),
                    "net_income":          _to_cr(net_income),
                    "ebitda":              _to_cr(ebitda),
                    "eps":                 eps,
                    "total_assets":        _to_cr(total_assets),
                    "total_debt":          _to_cr(total_debt),
                    "cash":                _to_cr(cash),
                    "operating_cash_flow": _to_cr(op_cf),
                    "gross_margin":        gross_margin,
                    "net_margin":          net_margin,
                })
        except Exception as exc:
            logger.warning("yfinance_annual_failed", ticker=yf_ticker, error=str(exc))

        # Quarterly
        try:
            qfin = stock.quarterly_financials
            for col in qfin.columns:
                year    = col.year  if hasattr(col, "year")  else int(str(col)[:4])
                month   = col.month if hasattr(col, "month") else int(str(col)[5:7])
                quarter = f"Q{(month - 1) // 3 + 1}"
                period_date = str(col)[:10]

                def safe_q(row):
                    try:
                        v = qfin.loc[row, col] if row in qfin.index else None
                        return float(v) if v is not None and str(v) != "nan" else None
                    except Exception:
                        return None

                revenue      = safe_q("Total Revenue")
                net_income   = safe_q("Net Income")
                gross_profit = safe_q("Gross Profit")
                gross_margin = (gross_profit / revenue * 100) if gross_profit and revenue else None
                net_margin   = (net_income   / revenue * 100) if net_income   and revenue else None

                records.append({
                    "fiscal_year":         year,
                    "fiscal_quarter":      quarter,
                    "period_end_date":     period_date,
                    "revenue":             _to_cr(revenue),
                    "net_income":          _to_cr(net_income),
                    "ebitda":              None,
                    "eps":                 None,
                    "total_assets":        None,
                    "total_debt":          None,
                    "cash":                None,
                    "operating_cash_flow": None,
                    "gross_margin":        gross_margin,
                    "net_margin":          net_margin,
                })
        except Exception as exc:
            logger.warning("yfinance_quarterly_failed", ticker=yf_ticker, error=str(exc))

        logger.info("yfinance_financials_fetched", ticker=yf_ticker, records=len(records))
        return records

    # ── Prices ─────────────────────────────────────────────────────────────────

    def get_prices(self, yf_ticker: str, period: str = "5y") -> list[dict]:
        """Returns daily OHLCV records. Prices are per-share INR (no Cr conversion)."""
        try:
            import yfinance as yf
        except ImportError:
            raise RuntimeError("yfinance not installed. Run: pip install yfinance")

        stock = yf.Ticker(yf_ticker)
        try:
            hist = stock.history(period=period)
        except Exception as exc:
            logger.warning("yfinance_prices_failed", ticker=yf_ticker, error=str(exc))
            return []

        records = []
        for date, row in hist.iterrows():
            records.append({
                "date":   str(date)[:10],
                "open":   float(row.get("Open",   0) or 0),
                "high":   float(row.get("High",   0) or 0),
                "low":    float(row.get("Low",    0) or 0),
                "close":  float(row.get("Close",  0) or 0),
                "volume": int(row.get("Volume",   0) or 0),
            })

        logger.info("yfinance_prices_fetched", ticker=yf_ticker, records=len(records))
        return records


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_cr(value: float | None) -> float | None:
    """Convert raw INR (yfinance) to Crores. Returns None if value is None."""
    if value is None:
        return None
    return value / 1e7
