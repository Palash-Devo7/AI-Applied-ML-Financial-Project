"""Integration tests for the query pipeline."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.queries import QueryRequest, TokenUsageDetail
from app.services.mcp_service import MCPService
from app.services.query_service import QueryService


@pytest.fixture
def mcp_service():
    return MCPService(max_context_tokens=6000)


@pytest.fixture
def query_service(
    mock_embedding_service,
    mock_vector_store,
    mock_generation_service,
    mcp_service,
):
    from app.services.retrieval_service import RetrievalService

    retrieval = RetrievalService(
        vector_store=mock_vector_store,
        top_k=5,
        fetch_multiplier=2,
        rrf_alpha=0.7,
    )
    return QueryService(
        embedding_service=mock_embedding_service,
        retrieval_service=retrieval,
        generation_service=mock_generation_service,
        mcp_service=mcp_service,
    )


@pytest.mark.asyncio
async def test_query_returns_response(query_service):
    """Full query pipeline returns a structured QueryResponse."""
    request = QueryRequest(question="What are Apple's risk factors?")
    response = await query_service.query(request)

    assert response.query_id is not None
    assert response.question == request.question
    assert response.answer
    assert response.query_type == "RISK"
    assert response.latency_ms > 0
    assert response.tokens_used.total_tokens > 0


@pytest.mark.asyncio
async def test_query_with_filters(query_service):
    """Query with explicit filters passes them to retrieval."""
    from app.models.queries import QueryFilters

    request = QueryRequest(
        question="What were the revenues?",
        filters=QueryFilters(ticker="AAPL", year=2023),
    )
    response = await query_service.query(request)
    assert response.answer


@pytest.mark.asyncio
async def test_query_no_results_graceful(
    mock_embedding_service, mock_generation_service, mcp_service
):
    """Query with no results returns a graceful 'no information' message."""
    from app.services.retrieval_service import RetrievalService

    empty_vector_store = MagicMock()
    empty_vector_store.query = AsyncMock(return_value={
        "ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]
    })
    empty_vector_store.count = AsyncMock(return_value=0)

    retrieval = RetrievalService(
        vector_store=empty_vector_store, top_k=5, fetch_multiplier=2
    )
    service = QueryService(
        embedding_service=mock_embedding_service,
        retrieval_service=retrieval,
        generation_service=mock_generation_service,
        mcp_service=mcp_service,
    )

    request = QueryRequest(question="What is the revenue?")
    response = await service.query(request)

    # Should return graceful message without calling generation
    assert "unable to find" in response.answer.lower() or response.answer
    assert response.chunk_count == 0


@pytest.mark.asyncio
async def test_query_sources_excluded_on_request(query_service):
    """Sources list is empty when include_sources=False."""
    request = QueryRequest(
        question="What are the risk factors?",
        include_sources=False,
    )
    response = await query_service.query(request)
    assert response.sources == []


@pytest.mark.asyncio
async def test_query_type_classification(query_service):
    """Different questions classify to expected types."""
    risk_req = QueryRequest(question="What are the main risk factors?")
    rev_req = QueryRequest(question="What was the revenue growth this year?")

    risk_resp = await query_service.query(risk_req)
    rev_resp = await query_service.query(rev_req)

    assert risk_resp.query_type == "RISK"
    assert rev_resp.query_type == "REVENUE"
