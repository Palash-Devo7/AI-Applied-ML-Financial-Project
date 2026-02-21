"""Integration tests for the ingestion pipeline."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ingestion_service import IngestionService


@pytest.fixture
def sample_pdf_text():
    """Simulate text extracted from a financial PDF."""
    return """Apple Inc. Annual Report 2023 - Form 10-K

RISK FACTORS

The following risk factors may materially affect our business, financial condition
and results of operations. AAPL operates in highly competitive markets.

Supply chain disruptions represent a significant operational risk for the Company.
Dependence on third-party manufacturers in Asia may expose us to geopolitical risk.

RESULTS OF OPERATIONS

Total net revenues for fiscal 2023 were $394.3 billion, an increase of 2.8 percent
compared to fiscal 2022. Products revenues were $298.1 billion, a decrease of
1.6 percent year-over-year.

Services revenues were $85.2 billion, an increase of 9.1 percent year-over-year.
The growth in Services was driven by App Store, Apple Music, iCloud, and Apple TV+.
"""


@pytest.fixture
def ingestion_service(mock_embedding_service, mock_vector_store):
    return IngestionService(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
    )


@pytest.mark.asyncio
async def test_ingestion_returns_upload_response(
    ingestion_service, sample_pdf_bytes, mock_embedding_service
):
    """Full ingestion pipeline returns a valid UploadResponse."""
    mock_embedding_service.embed_texts = AsyncMock(
        side_effect=lambda texts: [[0.1] * 768 for _ in texts]
    )

    with patch("app.core.document_parser.DocumentParser.parse") as mock_parse:
        from app.core.document_parser import ParsedDocument, ParsedPage

        text = "Apple Inc 10-K 2023. RISK FACTORS: The Company faces significant competition across all markets. Supply chain disruptions may materially affect operations."
        mock_page = ParsedPage(page_num=1, text=text, char_count=len(text))
        mock_parse.return_value = ParsedDocument(
            filename="apple_10k_2023.pdf",
            pages=[mock_page],
            total_chars=len(text),
            parser_used="pypdf",
        )

        result = await ingestion_service.ingest(
            content=sample_pdf_bytes,
            filename="apple_10k_2023.pdf",
            overrides={"company": "Apple", "ticker": "AAPL", "year": 2023},
        )

    assert result.document_id is not None
    assert result.chunk_count > 0
    assert result.status == "ingested"
    assert result.company == "Apple"
    assert result.year == 2023


@pytest.mark.asyncio
async def test_ingestion_calls_vector_store_upsert(
    ingestion_service, sample_pdf_bytes, mock_embedding_service, mock_vector_store
):
    """Vector store upsert is called with correct structure."""
    mock_embedding_service.embed_texts = AsyncMock(
        side_effect=lambda texts: [[0.1] * 768 for _ in texts]
    )

    with patch("app.core.document_parser.DocumentParser.parse") as mock_parse:
        from app.core.document_parser import ParsedDocument, ParsedPage

        mock_page = ParsedPage(page_num=1, text="Apple risk factors 2023. " * 20, char_count=500)
        mock_parse.return_value = ParsedDocument(
            filename="test.pdf",
            pages=[mock_page],
            total_chars=500,
            parser_used="pypdf",
        )

        await ingestion_service.ingest(content=sample_pdf_bytes, filename="test.pdf")

    mock_vector_store.upsert_chunks.assert_called_once()
    call_kwargs = mock_vector_store.upsert_chunks.call_args
    assert len(call_kwargs.kwargs["ids"]) > 0
    assert len(call_kwargs.kwargs["embeddings"]) > 0
    assert len(call_kwargs.kwargs["documents"]) > 0


@pytest.mark.asyncio
async def test_ingestion_fails_on_empty_content(ingestion_service):
    """Empty PDF raises ValueError."""
    with patch("app.core.document_parser.DocumentParser.parse") as mock_parse:
        from app.core.document_parser import ParsedDocument

        mock_parse.return_value = ParsedDocument(
            filename="empty.pdf", pages=[], total_chars=0, parser_used="pypdf"
        )

        with pytest.raises(ValueError, match="empty or unreadable"):
            await ingestion_service.ingest(content=b"fake", filename="empty.pdf")
