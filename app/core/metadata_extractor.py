"""Heuristic metadata extraction from financial document text."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# ── Section type patterns (order matters — first match wins) ──────────────────
_SECTION_PATTERNS: list[tuple[str, str]] = [
    (r"\bRISK\s+FACTORS?\b", "RISK_FACTORS"),
    (r"\bITEM\s+1A\b", "RISK_FACTORS"),
    (r"\bQUANTITATIVE\s+AND\s+QUALITATIVE\s+DISCLOSURES?\s+ABOUT\s+MARKET\s+RISK\b", "MARKET_RISK"),
    (r"\bRESULTS?\s+OF\s+OPERATIONS?\b", "RESULTS_OF_OPERATIONS"),
    (r"\bREVENUE\b.*\bDISCUSSION\b|\bDISCUSSION\b.*\bREVENUE\b", "REVENUE"),
    (r"\bFINANCIAL\s+STATEMENTS?\b", "FINANCIAL_STATEMENTS"),
    (r"\bCONSOLIDATED\s+BALANCE\s+SHEET\b", "BALANCE_SHEET"),
    (r"\bCASH\s+FLOW\b", "CASH_FLOW"),
    (r"\bEARNINGS\s+PER\s+SHARE\b", "EPS"),
    (r"\bMANAGEMENT\s*[''S]*\s+DISCUSSION\b", "MD&A"),
    (r"\bLEGAL\s+PROCEEDINGS?\b", "LEGAL"),
    (r"\bBUSINESS\b", "BUSINESS_OVERVIEW"),
    (r"\bMARKET\s+FOR\s+REGISTRANT\b", "MARKET_INFO"),
    (r"\bCRITICAL\s+ACCOUNTING\b", "ACCOUNTING_POLICIES"),
    (r"\bCONTRACTUAL\s+OBLIGATIONS?\b", "CONTRACTUAL_OBLIGATIONS"),
    (r"\bSEGMENT\s+(INFORMATION|RESULTS)\b", "SEGMENT_RESULTS"),
]

# ── Report type patterns ───────────────────────────────────────────────────────
_REPORT_TYPE_PATTERNS: list[tuple[str, str]] = [
    (r"\b10-?K\b", "10-K"),
    (r"\b10-?Q\b", "10-Q"),
    (r"\b8-?K\b", "8-K"),
    (r"\bDEF\s*14A\b", "DEF14A"),
    (r"\bEARNINGS\s+CALL\b|\bEARNINGS\s+RELEASE\b", "EARNINGS"),
    (r"\bANNUAL\s+REPORT\b", "ANNUAL_REPORT"),
]

# ── Year patterns ─────────────────────────────────────────────────────────────
_YEAR_RE = re.compile(r"\b(20[0-2]\d)\b")

# ── Quarter patterns ──────────────────────────────────────────────────────────
_QUARTER_RE = re.compile(r"\b(Q[1-4]|first|second|third|fourth)\s+(?:quarter|fiscal)?\s*(?:of\s+)?(?:20[0-2]\d)?\b", re.IGNORECASE)
_QUARTER_MAP = {"first": "Q1", "second": "Q2", "third": "Q3", "fourth": "Q4"}

# ── Well-known company / ticker patterns ──────────────────────────────────────
_KNOWN_TICKERS: dict[str, str] = {
    "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Alphabet", "GOOG": "Alphabet",
    "AMZN": "Amazon", "META": "Meta Platforms", "NVDA": "NVIDIA", "TSLA": "Tesla",
    "BRK": "Berkshire Hathaway", "JPM": "JPMorgan Chase", "JNJ": "Johnson & Johnson",
    "V": "Visa", "PG": "Procter & Gamble", "UNH": "UnitedHealth", "HD": "Home Depot",
    "MA": "Mastercard", "DIS": "Walt Disney", "BAC": "Bank of America",
    "XOM": "ExxonMobil", "NFLX": "Netflix", "ADBE": "Adobe",
    "CRM": "Salesforce", "INTC": "Intel", "AMD": "AMD",
}
_TICKER_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in _KNOWN_TICKERS) + r")\b"
)

# ── Sector keywords ───────────────────────────────────────────────────────────
_SECTOR_KEYWORDS: list[tuple[str, str]] = [
    (r"\btechnology\b|\bsoftware\b|\bsemiconductor\b", "Technology"),
    (r"\bfinancial services?\b|\bbanking\b|\binsurance\b", "Financials"),
    (r"\bhealthcare\b|\bpharmaceutical\b|\bbiotech\b", "Healthcare"),
    (r"\benergy\b|\boil\s+and\s+gas\b|\bpetroleum\b", "Energy"),
    (r"\bconsumer\s+(discretionary|goods|staples)\b|\bretail\b", "Consumer"),
    (r"\bindustrials?\b|\bmanufacturing\b|\baerospace\b", "Industrials"),
    (r"\breal estate\b|\breit\b", "Real Estate"),
    (r"\butilities\b|\belectric\s+utility\b", "Utilities"),
    (r"\btelecommunications?\b|\bwireless\b", "Telecom"),
    (r"\bmaterials?\b|\bmining\b|\bchemicals?\b", "Materials"),
]


@dataclass
class ExtractedMetadata:
    company: Optional[str] = None
    ticker: Optional[str] = None
    year: Optional[int] = None
    quarter: Optional[str] = None
    section_type: Optional[str] = None
    report_type: Optional[str] = None
    sector: Optional[str] = None


class MetadataExtractor:
    """Extract financial document metadata using regex and heuristics."""

    def extract_document_metadata(
        self,
        text: str,
        filename: str,
        overrides: Optional[dict] = None,
    ) -> ExtractedMetadata:
        """Extract metadata from full document text with optional overrides."""
        meta = ExtractedMetadata()
        overrides = overrides or {}

        # Extract from text
        meta.ticker = self._extract_ticker(text)
        meta.company = self._extract_company(text, meta.ticker)
        meta.year = self._extract_year(text)
        meta.quarter = self._extract_quarter(text)
        meta.report_type = self._extract_report_type(text, filename)
        meta.sector = self._extract_sector(text)

        # Apply overrides
        for field_name, value in overrides.items():
            if value is not None and hasattr(meta, field_name):
                setattr(meta, field_name, value)

        # Attempt filename-based fallbacks
        if meta.year is None:
            meta.year = self._year_from_filename(filename)
        if meta.company is None:
            meta.company = self._company_from_filename(filename)

        logger.debug("metadata_extracted", filename=filename, meta=meta.__dict__)
        return meta

    def extract_section_type(self, section_text: str) -> Optional[str]:
        """Identify section type from the first ~500 chars of a section."""
        sample = section_text[:500].upper()
        for pattern, section_type in _SECTION_PATTERNS:
            if re.search(pattern, sample, re.IGNORECASE):
                return section_type
        return "GENERAL"

    # ── Field extractors ──────────────────────────────────────────────────────

    def _extract_ticker(self, text: str) -> Optional[str]:
        match = _TICKER_RE.search(text[:3000])
        return match.group(1) if match else None

    def _extract_company(self, text: str, ticker: Optional[str]) -> Optional[str]:
        if ticker and ticker in _KNOWN_TICKERS:
            return _KNOWN_TICKERS[ticker]
        # Try to find "Inc.", "Corp.", "Ltd." nearby
        company_re = re.compile(
            r"([A-Z][A-Za-z\s,\.&]{2,50}(?:Inc\.|Corp\.|Ltd\.|LLC|PLC|N\.V\.))",
        )
        match = company_re.search(text[:2000])
        if match:
            return match.group(1).strip().rstrip(",")
        return None

    def _extract_year(self, text: str) -> Optional[int]:
        # Look in first 2000 chars for fiscal year references
        sample = text[:2000]
        fiscal_re = re.compile(
            r"(?:fiscal|year\s+ended?|for\s+the\s+year)\s+(?:ended?\s+)?(?:\w+\s+\d{1,2},?\s+)?(20[0-2]\d)",
            re.IGNORECASE,
        )
        match = fiscal_re.search(sample)
        if match:
            return int(match.group(1))
        # Fallback: most common year in first 2000 chars
        years = _YEAR_RE.findall(sample)
        if years:
            from collections import Counter
            return int(Counter(years).most_common(1)[0][0])
        return None

    def _extract_quarter(self, text: str) -> Optional[str]:
        match = _QUARTER_RE.search(text[:2000])
        if not match:
            return None
        raw = match.group(1).upper()
        return _QUARTER_MAP.get(raw.lower(), raw if raw.startswith("Q") else None)

    def _extract_report_type(self, text: str, filename: str) -> Optional[str]:
        combined = (filename + " " + text[:1000]).upper()
        for pattern, report_type in _REPORT_TYPE_PATTERNS:
            if re.search(pattern, combined, re.IGNORECASE):
                return report_type
        return None

    def _extract_sector(self, text: str) -> Optional[str]:
        sample = text[:3000].lower()
        for pattern, sector in _SECTOR_KEYWORDS:
            if re.search(pattern, sample, re.IGNORECASE):
                return sector
        return None

    def _year_from_filename(self, filename: str) -> Optional[int]:
        # Don't use _YEAR_RE here — \b fails on underscores (e.g. report_2021.pdf)
        match = re.search(r"(20[0-2]\d)", filename)
        return int(match.group(1)) if match else None

    def _company_from_filename(self, filename: str) -> Optional[str]:
        # e.g. "apple_10k_2023.pdf" → "apple"
        stem = filename.rsplit(".", 1)[0]
        parts = re.split(r"[_\-\s]+", stem)
        if parts:
            return parts[0].title()
        return None
