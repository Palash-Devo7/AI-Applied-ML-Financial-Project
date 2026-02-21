"""PDF document parser with pypdf primary and pdfplumber fallback."""
from __future__ import annotations

import io
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ParsedPage:
    page_num: int
    text: str
    char_count: int


@dataclass
class ParsedDocument:
    filename: str
    pages: list[ParsedPage]
    total_chars: int
    parser_used: str

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text.strip())

    @property
    def page_count(self) -> int:
        return len(self.pages)


class DocumentParser:
    """Parse PDFs using pypdf, falling back to pdfplumber for complex layouts."""

    MIN_CHARS_PER_PAGE = 50  # below this we try the fallback

    def parse(self, content: bytes, filename: str) -> ParsedDocument:
        """Parse PDF bytes, returning structured pages."""
        pages, parser_used = self._try_pypdf(content)

        # Quality check: if pypdf extracted too little text, try pdfplumber
        total_chars = sum(p.char_count for p in pages)
        if total_chars < self.MIN_CHARS_PER_PAGE * max(len(pages), 1):
            logger.warning(
                "pypdf_low_extraction",
                filename=filename,
                total_chars=total_chars,
                page_count=len(pages),
            )
            fallback_pages, fallback_parser = self._try_pdfplumber(content)
            fallback_chars = sum(p.char_count for p in fallback_pages)
            if fallback_chars > total_chars:
                pages = fallback_pages
                parser_used = fallback_parser
                total_chars = fallback_chars

        doc = ParsedDocument(
            filename=filename,
            pages=pages,
            total_chars=total_chars,
            parser_used=parser_used,
        )
        logger.info(
            "document_parsed",
            filename=filename,
            page_count=doc.page_count,
            total_chars=total_chars,
            parser=parser_used,
        )
        return doc

    # ── Parsers ───────────────────────────────────────────────────────────────

    def _try_pypdf(self, content: bytes) -> tuple[list[ParsedPage], str]:
        try:
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(content))
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                text = self._clean_text(text)
                pages.append(ParsedPage(page_num=i + 1, text=text, char_count=len(text)))
            return pages, "pypdf"
        except Exception as exc:
            logger.error("pypdf_failed", error=str(exc))
            return [], "pypdf_failed"

    def _try_pdfplumber(self, content: bytes) -> tuple[list[ParsedPage], str]:
        try:
            import pdfplumber

            pages = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    text = self._clean_text(text)
                    pages.append(ParsedPage(page_num=i + 1, text=text, char_count=len(text)))
            return pages, "pdfplumber"
        except Exception as exc:
            logger.error("pdfplumber_failed", error=str(exc))
            return [], "pdfplumber_failed"

    # ── Text cleaning ─────────────────────────────────────────────────────────

    @staticmethod
    def _clean_text(text: str) -> str:
        """Remove excessive whitespace and control characters."""
        import re

        # Replace multiple newlines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Replace multiple spaces with single space (but preserve newlines)
        text = re.sub(r"[ \t]+", " ", text)
        # Strip leading/trailing whitespace per line
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(lines)
        return text.strip()
