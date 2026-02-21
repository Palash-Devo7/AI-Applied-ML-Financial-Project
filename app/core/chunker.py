"""Section-aware financial document chunker.

Phase 1: Split on financial section boundaries (regex for standard SEC headings).
Phase 2: Recursively split each section with langchain's RecursiveCharacterTextSplitter
         to keep chunks within the FinBERT 512-token limit.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# ── Section boundary regex patterns ──────────────────────────────────────────
# These match common SEC filing section headers (case-insensitive)
_SECTION_BOUNDARY_PATTERNS = [
    # Item-style headings (10-K / 10-Q)
    r"ITEM\s+\d+[A-Z]?\.\s+[A-Z][A-Z\s&,;]{5,}",
    # Named sections
    r"(?:^|\n)(?:PART\s+[IVX]+\.?\s+)?(?:RISK\s+FACTORS?|QUANTITATIVE\s+AND\s+QUALITATIVE"
    r"|RESULTS?\s+OF\s+OPERATIONS?|MANAGEMENT[''S]*\s+DISCUSSION|FINANCIAL\s+STATEMENTS?"
    r"|LEGAL\s+PROCEEDINGS?|CRITICAL\s+ACCOUNTING|BUSINESS\b|PROPERTIES\b"
    r"|SELECTED\s+FINANCIAL\s+DATA|MARKET\s+FOR\s+REGISTRANT"
    r"|CONTROLS?\s+AND\s+PROCEDURES?)(?:\s+AND\s+\w+)?",
]
_SECTION_BOUNDARY_RE = re.compile(
    "|".join(_SECTION_BOUNDARY_PATTERNS),
    re.IGNORECASE | re.MULTILINE,
)

# Tokens ≈ words * 1.3 for financial text. We target 480 to leave room for
# [CLS] / [SEP] special tokens inserted by the FinBERT tokenizer.
_SOFT_TOKEN_LIMIT = 480
_OVERLAP_TOKENS = 64


@dataclass
class DocumentChunk:
    text: str
    section_type: Optional[str] = None
    page_num: Optional[int] = None
    chunk_index: int = 0
    token_count: int = 0


class FinancialChunker:
    """Section-aware + recursive chunker for financial documents."""

    def __init__(
        self,
        chunk_size_tokens: int = _SOFT_TOKEN_LIMIT,
        chunk_overlap_tokens: int = _OVERLAP_TOKENS,
    ) -> None:
        self.chunk_size_tokens = chunk_size_tokens
        self.chunk_overlap_tokens = chunk_overlap_tokens
        self._splitter = self._build_splitter()

    # ── Public API ────────────────────────────────────────────────────────────

    def chunk_document(self, text: str) -> list[DocumentChunk]:
        """Split a document into chunks preserving section context."""
        sections = self._split_into_sections(text)
        chunks: list[DocumentChunk] = []
        chunk_index = 0

        for section_text, section_type in sections:
            if not section_text.strip():
                continue
            sub_chunks = self._splitter.split_text(section_text)
            for sub in sub_chunks:
                sub = sub.strip()
                if not sub:
                    continue
                token_count = self._estimate_tokens(sub)
                chunks.append(
                    DocumentChunk(
                        text=sub,
                        section_type=section_type,
                        chunk_index=chunk_index,
                        token_count=token_count,
                    )
                )
                chunk_index += 1

        logger.debug("document_chunked", total_chunks=len(chunks))
        return chunks

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _split_into_sections(self, text: str) -> list[tuple[str, Optional[str]]]:
        """Split document on section boundary patterns, return (text, section_type) pairs."""
        from app.core.metadata_extractor import MetadataExtractor

        extractor = MetadataExtractor()
        boundaries = [m.start() for m in _SECTION_BOUNDARY_RE.finditer(text)]

        if not boundaries:
            # No section boundaries found — treat as single section
            return [(text, extractor.extract_section_type(text))]

        sections: list[tuple[str, Optional[str]]] = []

        # Text before first boundary
        if boundaries[0] > 0:
            prefix = text[: boundaries[0]]
            if prefix.strip():
                sections.append((prefix, extractor.extract_section_type(prefix)))

        for i, start in enumerate(boundaries):
            end = boundaries[i + 1] if i + 1 < len(boundaries) else len(text)
            section_text = text[start:end]
            section_type = extractor.extract_section_type(section_text)
            sections.append((section_text, section_type))

        return sections

    def _build_splitter(self):
        """Build a LangChain RecursiveCharacterTextSplitter with token-aware sizing."""
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        # Approximate chars per token for financial text (~4 chars/token)
        chars_per_token = 4
        chunk_size = self.chunk_size_tokens * chars_per_token
        chunk_overlap = self.chunk_overlap_tokens * chars_per_token

        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", ", ", " ", ""],
            length_function=len,
        )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Approximate token count (chars / 4)."""
        return max(1, len(text) // 4)
