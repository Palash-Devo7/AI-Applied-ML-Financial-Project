"""Unit tests for FinancialChunker."""
import pytest

from app.core.chunker import FinancialChunker


@pytest.fixture
def chunker():
    return FinancialChunker(chunk_size_tokens=480, chunk_overlap_tokens=64)


def test_chunk_empty_text(chunker):
    chunks = chunker.chunk_document("")
    assert chunks == []


def test_chunk_short_text_produces_at_least_one_chunk(chunker):
    text = "Apple Inc. reported strong earnings for fiscal year 2023."
    chunks = chunker.chunk_document(text)
    assert len(chunks) >= 1
    assert chunks[0].text


def test_chunk_preserves_content(chunker):
    text = "This is a test document with some financial information about revenue growth."
    chunks = chunker.chunk_document(text)
    reconstructed = " ".join(c.text for c in chunks)
    # All words from original should appear in reconstructed
    for word in text.split():
        assert word in reconstructed


def test_section_detection(chunker):
    text = """RISK FACTORS

    The Company faces significant competition in all of its markets.
    Supply chain disruptions may materially affect our business operations.

    RESULTS OF OPERATIONS

    Total net revenues increased 8% year-over-year to $394.3 billion.
    """
    chunks = chunker.chunk_document(text)
    section_types = {c.section_type for c in chunks}
    # At least one section should be detected
    assert len(section_types) >= 1


def test_chunk_token_count_estimate(chunker):
    text = "word " * 100  # 100 words ≈ 25 tokens
    chunks = chunker.chunk_document(text)
    for chunk in chunks:
        assert chunk.token_count > 0


def test_large_document_produces_multiple_chunks(chunker):
    # 2000 words ≈ ~10k characters → should split into multiple chunks
    text = "The company reported strong financial results. " * 200
    chunks = chunker.chunk_document(text)
    assert len(chunks) > 1


def test_chunk_index_sequential(chunker):
    text = "Financial report content. " * 300
    chunks = chunker.chunk_document(text)
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))
