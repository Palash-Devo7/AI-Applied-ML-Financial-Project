"""Shared pytest fixtures."""
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop across the session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings(monkeypatch):
    """Override settings for tests."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key-for-testing")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", "/tmp/test_chroma")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")


@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService returning fixed-size embeddings."""
    service = MagicMock()
    service.is_ready.return_value = True
    service.embedding_dim = 768
    service.embed_texts = AsyncMock(
        return_value=[[0.1] * 768, [0.2] * 768]
    )
    return service


@pytest.fixture
def mock_vector_store():
    """Mock VectorStoreClient."""
    store = MagicMock()
    store.count = AsyncMock(return_value=42)
    store.upsert_chunks = AsyncMock(return_value=None)
    store.query = AsyncMock(return_value={
        "ids": [["chunk_001", "chunk_002"]],
        "documents": [["Risk factors text here.", "Revenue discussion here."]],
        "metadatas": [[
            {"company": "Apple", "ticker": "AAPL", "year": 2023, "section_type": "RISK_FACTORS",
             "report_type": "10-K", "page_num": 12, "token_count": 200, "ingested_at": "2024-01-01"},
            {"company": "Apple", "ticker": "AAPL", "year": 2023, "section_type": "RESULTS_OF_OPERATIONS",
             "report_type": "10-K", "page_num": 45, "token_count": 180, "ingested_at": "2024-01-01"},
        ]],
        "distances": [[0.15, 0.25]],
    })
    store.get_collection_info = AsyncMock(return_value={
        "name": "finance_docs",
        "count": 42,
        "distance_function": "cosine",
        "persist_dir": "/tmp/test_chroma",
    })
    store.delete_collection = AsyncMock(return_value=None)
    return store


@pytest.fixture
def mock_generation_service():
    """Mock GenerationService."""
    from app.models.queries import TokenUsageDetail
    service = MagicMock()
    service.generate = AsyncMock(return_value=(
        "Apple's primary risk factors include market competition and supply chain disruptions. [Source 1]",
        TokenUsageDetail(input_tokens=500, output_tokens=150, total_tokens=650),
    ))
    return service


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Generate a minimal valid PDF for testing."""
    # Minimal PDF with text content
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 200 >>
stream
BT
/F1 12 Tf
50 750 Td
(Apple Inc. Annual Report 2023 - Form 10-K) Tj
0 -20 Td
(RISK FACTORS) Tj
0 -20 Td
(The Company faces significant competition in all markets.) Tj
0 -20 Td
(Supply chain disruptions may materially affect our business.) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
525
%%EOF"""
    return pdf_content
