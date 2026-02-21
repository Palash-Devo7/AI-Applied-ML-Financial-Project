"""Unit tests for MCPService."""
import pytest

from app.models.queries import QueryFilters, RetrievedChunk
from app.services.mcp_service import MCPService


@pytest.fixture
def mcp():
    return MCPService(max_context_tokens=6000)


# ── Query classification ───────────────────────────────────────────────────────

def test_classify_risk_query(mcp):
    assert mcp.classify_query("What are Apple's main risk factors?") == "RISK"


def test_classify_revenue_query(mcp):
    assert mcp.classify_query("What was Apple's revenue growth in 2023?") == "REVENUE"


def test_classify_macro_query(mcp):
    assert mcp.classify_query("How does inflation affect this company?") == "MACRO"


def test_classify_comparative_query(mcp):
    assert mcp.classify_query("Compare Apple vs Microsoft margins") == "COMPARATIVE"


def test_classify_historical_query(mcp):
    assert mcp.classify_query("What was the trend in revenue over the last 3 years?") == "HISTORICAL"


def test_classify_general_fallback(mcp):
    assert mcp.classify_query("Tell me about the company") == "GENERAL"


# ── Entity extraction ─────────────────────────────────────────────────────────

def test_extract_ticker(mcp):
    entities = mcp.extract_entities("What happened to AAPL in 2023?")
    assert entities.get("ticker") == "AAPL"
    assert entities.get("year") == 2023


def test_extract_company_name(mcp):
    entities = mcp.extract_entities("What are Apple's risk factors?")
    assert entities.get("ticker") == "AAPL"


def test_extract_quarter(mcp):
    entities = mcp.extract_entities("What was revenue in Q2 2022?")
    assert entities.get("quarter") == "Q2"
    assert entities.get("year") == 2022


# ── Filter construction ───────────────────────────────────────────────────────

def test_build_filter_from_entities(mcp):
    entities = {"ticker": "AAPL", "year": 2023}
    where = mcp.build_metadata_filters(entities)
    assert where is not None
    assert "$and" in where


def test_build_filter_single_entity(mcp):
    entities = {"ticker": "MSFT"}
    where = mcp.build_metadata_filters(entities)
    assert where == {"ticker": {"$eq": "MSFT"}}


def test_build_filter_empty(mcp):
    where = mcp.build_metadata_filters({})
    assert where is None


def test_explicit_filters_override(mcp):
    entities = {"ticker": "AAPL"}
    explicit = QueryFilters(report_type="10-K")
    where = mcp.build_metadata_filters(entities, explicit)
    assert where is not None


# ── Context assembly ──────────────────────────────────────────────────────────

def _make_chunk(chunk_id: str, text: str, score: float, year: int = 2023) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        text=text,
        score=score,
        company="Apple",
        ticker="AAPL",
        year=year,
        section_type="RISK_FACTORS",
        report_type="10-K",
        page_num=1,
    )


def test_assemble_context_sorted_by_score(mcp):
    chunks = [
        _make_chunk("c1", "Lower score text.", 0.5),
        _make_chunk("c2", "Higher score text.", 0.9),
    ]
    context_str, used = mcp.assemble_context(chunks)
    # Higher score chunk should appear first
    assert context_str.index("Higher score") < context_str.index("Lower score")


def test_assemble_context_deduplication(mcp):
    identical_text = "Apple faces significant competition in all of its markets."
    chunks = [
        _make_chunk("c1", identical_text, 0.9),
        _make_chunk("c2", identical_text, 0.8),  # near-duplicate
    ]
    _, used = mcp.assemble_context(chunks)
    assert len(used) == 1


def test_assemble_context_citation_format(mcp):
    chunks = [_make_chunk("c1", "Risk factor text here.", 0.9)]
    context_str, _ = mcp.assemble_context(chunks)
    assert "[Source 1:" in context_str
    assert "AAPL" in context_str


def test_assemble_empty_chunks(mcp):
    context_str, used = mcp.assemble_context([])
    assert context_str == ""
    assert used == []
