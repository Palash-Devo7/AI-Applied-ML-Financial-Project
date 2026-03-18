"""BSE India provider — uses pip install bse (unofficial) + direct PDF download."""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import ClassVar

import requests
import structlog

logger = structlog.get_logger(__name__)

BSE_ATTACH_URL = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/{}"
BSE_HOME       = "https://www.bseindia.com/"
YAHOO_SEARCH   = "https://query2.finance.yahoo.com/v1/finance/search?q={}&lang=en-US&region=IN&quotesCount=5"

RELEVANT_CATEGORIES = {
    "Result", "Company Update", "Investor Presentation", "Annual Report",
}


class BSEProvider:
    """
    Implements MarketDataProvider for BSE India.

    capabilities:
      - documents         : download BSE filings as PDFs
      - live_price        : real-time quote from BSE
      - recent_financials : last 2 quarters + current FY annual (in Crores)
    """

    capabilities: ClassVar[frozenset[str]] = frozenset({
        "documents", "live_price", "recent_financials",
    })

    # In-memory securities cache — loaded once at startup
    _securities_cache: ClassVar[list[dict]] = []
    _cache_loaded: ClassVar[bool] = False

    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": BSE_HOME,
            "Accept": "application/pdf,text/html,*/*",
        })
        self._warmup()

    def _warmup(self) -> None:
        try:
            self._session.get(BSE_HOME, timeout=10)
        except Exception:
            pass

    def _bse(self):
        from bse import BSE
        return BSE(download_folder="./data")

    # ── Securities cache (powers search bar) ──────────────────────────────────

    @classmethod
    def load_securities_cache(cls) -> int:
        """
        Load all BSE-listed securities into memory.
        Called once at server startup. Returns count loaded.
        """
        all_securities: list[dict] = []
        with cls._get_bse_instance() as bse:
            for group in ["A", "B", "F", "T", "Z"]:
                try:
                    rows = bse.listSecurities(
                        industry="", scripcode="", group=group, status="Active"
                    )
                    for r in rows:
                        all_securities.append({
                            "scrip_code": str(r.get("SCRIP_CD", "")),
                            "ticker":     r.get("scrip_id", ""),
                            "name":       r.get("Scrip_Name", ""),
                            "isin":       r.get("ISIN_NUMBER", ""),
                            "group":      group,
                            "industry":   r.get("INDUSTRY", ""),
                            "market_cap": r.get("Mktcap", ""),
                        })
                except Exception as exc:
                    logger.warning("securities_cache_group_failed", group=group, error=str(exc))

        cls._securities_cache = all_securities
        cls._cache_loaded = True
        logger.info("securities_cache_loaded", count=len(all_securities))
        return len(all_securities)

    @classmethod
    def search(cls, query: str, limit: int = 15) -> list[dict]:
        """Search cached securities by name or ticker. Returns list of matches."""
        if not cls._cache_loaded:
            return []
        q = query.lower().strip()
        results = [
            s for s in cls._securities_cache
            if q in s["name"].lower() or q in s["ticker"].lower()
        ]
        # Sort: ticker-start matches first, then name-start, then rest
        results.sort(key=lambda s: (
            0 if s["ticker"].lower().startswith(q) else
            1 if s["name"].lower().startswith(q) else 2
        ))
        return results[:limit]

    @classmethod
    def _get_bse_instance(cls):
        from bse import BSE
        return BSE(download_folder="./data")

    # ── Symbol resolution ─────────────────────────────────────────────────────

    def get_scrip_code(self, ticker: str) -> str:
        with self._bse() as bse:
            return bse.getScripCode(ticker.upper())

    def get_canonical_name(self, scrip_code: str) -> str:
        """Return proper display name from BSE securities list (e.g. 'Tata Steel Ltd')."""
        # Check cache first
        for s in BSEProvider._securities_cache:
            if s["scrip_code"] == str(scrip_code):
                return s["name"]
        # Fallback: live lookup
        try:
            with self._bse() as bse:
                rows = bse.listSecurities(
                    industry="", scripcode=scrip_code, group="", status="Active"
                )
                if rows:
                    return rows[0].get("Scrip_Name") or rows[0].get("scrip_id", scrip_code)
        except Exception:
            pass
        return scrip_code

    def get_isin(self, scrip_code: str) -> str | None:
        """Return ISIN for a scrip code — used to resolve yfinance ticker."""
        for s in BSEProvider._securities_cache:
            if s["scrip_code"] == str(scrip_code):
                return s["isin"] or None
        try:
            with self._bse() as bse:
                rows = bse.listSecurities(
                    industry="", scripcode=scrip_code, group="", status="Active"
                )
                if rows:
                    return rows[0].get("ISIN_NUMBER") or None
        except Exception:
            pass
        return None

    def resolve_yfinance_ticker(self, isin: str) -> str | None:
        """
        Use Yahoo Finance search API to find the correct yfinance ticker for an ISIN.
        e.g. INE081A01020 → 'TATASTEEL.NS'
        Free, no API key needed.
        """
        if not isin:
            return None
        try:
            url = YAHOO_SEARCH.format(isin)
            resp = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            quotes = resp.json().get("quotes", [])
            # Prefer NSE (.NS), fallback BSE (.BO)
            ns = next((q["symbol"] for q in quotes if q.get("symbol", "").endswith(".NS")), None)
            bo = next((q["symbol"] for q in quotes if q.get("symbol", "").endswith(".BO")), None)
            return ns or bo
        except Exception as exc:
            logger.warning("yfinance_ticker_resolve_failed", isin=isin, error=str(exc))
            return None

    # Kept for backward compatibility
    def get_company_name(self, scrip_code: str) -> str:
        return self.get_canonical_name(scrip_code)

    # ── Financial data (values returned in Crores) ────────────────────────────

    def get_financials(self, scrip_code: str) -> list[dict]:
        """
        Returns recent financials already in Crores.
        Covers: last 2 quarters + current FY annual (3 periods max).
        """
        with self._bse() as bse:
            snapshot = bse.resultsSnapshot(scrip_code)

        periods = snapshot.get("periods", [])
        data    = snapshot.get("results_in_crores", {}).get("data", [])

        if not periods or not data:
            return []

        # Build period → field → value map
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

        records = []
        for period, values in period_data.items():
            if not values:
                continue
            is_annual    = period.startswith("FY")
            fiscal_year  = _extract_year(period)
            fiscal_quarter = "Annual" if is_annual else _period_to_quarter(period)

            records.append({
                "fiscal_year":    fiscal_year,
                "fiscal_quarter": fiscal_quarter,
                "revenue":        values.get("Revenue"),        # Crores
                "net_income":     values.get("Net Profit"),     # Crores
                "eps":            values.get("EPS"),
                "gross_margin":   values.get("OPM %"),
                "net_margin":     values.get("NPM %"),
            })

        return records

    def get_price(self, scrip_code: str) -> dict:
        with self._bse() as bse:
            return bse.quote(scrip_code)

    # ── Announcements + PDF download ──────────────────────────────────────────

    def get_announcements(self, scrip_code: str, days_back: int = 365) -> list[dict]:
        to_date   = datetime.now()
        from_date = to_date - timedelta(days=days_back)
        with self._bse() as bse:
            data = bse.announcements(
                scripcode=scrip_code,
                from_date=from_date,
                to_date=to_date,
                page_no=1,
            )
        all_ann = data.get("Table", [])

        relevant = [
            a for a in all_ann
            if a.get("PDFFLAG") == 1
            and a.get("ATTACHMENTNAME")
            and a.get("Fld_Attachsize", 0) > 50_000
            and a.get("CATEGORYNAME", "") in RELEVANT_CATEGORIES
        ]

        logger.info(
            "bse_announcements_filtered",
            scrip_code=scrip_code,
            total=len(all_ann),
            relevant=len(relevant),
        )
        return relevant

    def download_pdf(self, attachment_name: str) -> bytes:
        url = BSE_ATTACH_URL.format(attachment_name)
        self._warmup()
        time.sleep(0.5)
        r = self._session.get(url, timeout=30)
        r.raise_for_status()
        if r.content[:4] != b"%PDF":
            raise ValueError(f"Downloaded file is not a valid PDF: {attachment_name}")
        return r.content


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_year(period: str) -> int:
    import re
    m = re.search(r"(\d{2,4})", period)
    if not m:
        return 2024
    yr = int(m.group(1))
    return yr + 2000 if yr < 100 else yr


def _period_to_quarter(period: str) -> str:
    month_map = {
        "Jun": "Q1", "Sep": "Q2", "Dec": "Q3", "Mar": "Q4",
        "Jan": "Q3", "Feb": "Q3", "Apr": "Q1", "May": "Q1",
        "Jul": "Q2", "Aug": "Q2", "Oct": "Q3", "Nov": "Q3",
    }
    for month, quarter in month_map.items():
        if period.startswith(month):
            return quarter
    return "Q1"
