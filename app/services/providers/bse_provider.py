"""BSE India provider — uses pip install bse (unofficial) + direct PDF download."""
from __future__ import annotations

import time
from datetime import datetime, timedelta

import requests
import structlog

logger = structlog.get_logger(__name__)

BSE_ATTACH_URL = "https://www.bseindia.com/xml-data/corpfiling/AttachLive/{}"
BSE_HOME = "https://www.bseindia.com/"

# Announcement categories worth ingesting (financial results + concalls)
RELEVANT_CATEGORIES = {
    "Results", "Board Meeting", "Board Meeting Outcome",
    "Investor Presentation", "Annual Report",
}


class BSEProvider:
    """Implements MarketDataProvider using the free BSE India package."""

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
            pass  # warmup failure is non-fatal

    def _bse(self):
        from bse import BSE
        return BSE(download_folder="./data")

    # ── Symbol resolution ─────────────────────────────────────────────────────

    def get_scrip_code(self, ticker: str) -> str:
        with self._bse() as bse:
            return bse.getScripCode(ticker.upper())

    def get_company_name(self, scrip_code: str) -> str:
        with self._bse() as bse:
            return bse.getScripName(scrip_code)

    # ── Financial data ────────────────────────────────────────────────────────

    def get_financials(self, scrip_code: str) -> dict:
        with self._bse() as bse:
            return bse.resultsSnapshot(scrip_code)

    def get_price(self, scrip_code: str) -> dict:
        with self._bse() as bse:
            return bse.quote(scrip_code)

    # ── Announcements (filing metadata + PDF names) ───────────────────────────

    def get_announcements(self, scrip_code: str, days_back: int = 365) -> list[dict]:
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days_back)
        with self._bse() as bse:
            data = bse.announcements(
                scripcode=scrip_code,
                from_date=from_date,
                to_date=to_date,
                page_no=1,
            )
        all_ann = data.get("Table", [])

        # Filter: must have PDF, must be relevant category, must be > 50KB
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

    # ── PDF download ──────────────────────────────────────────────────────────

    def download_pdf(self, attachment_name: str) -> bytes:
        url = BSE_ATTACH_URL.format(attachment_name)
        # Re-warmup session before download to keep cookies fresh
        self._warmup()
        time.sleep(0.5)  # polite delay
        r = self._session.get(url, timeout=30)
        r.raise_for_status()
        if r.content[:4] != b"%PDF":
            raise ValueError(f"Downloaded file is not a valid PDF: {attachment_name}")
        return r.content
