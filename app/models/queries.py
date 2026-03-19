"""Pydantic models for query requests and responses."""
from typing import Optional

from pydantic import BaseModel, Field


class QueryFilters(BaseModel):
    company: Optional[str] = None
    ticker: Optional[str] = None
    year: Optional[int] = None
    quarter: Optional[str] = None
    report_type: Optional[str] = None
    section_type: Optional[str] = None
    sector: Optional[str] = None


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000, description="The financial question to answer")
    company: Optional[str] = Field(None, description="Filter by company name (must match exactly as uploaded, e.g. 'Tata Steel')")
    filters: Optional[QueryFilters] = Field(None, description="Optional additional metadata filters")
    top_k: Optional[int] = Field(10, ge=1, le=50, description="Number of chunks to retrieve (default 10)")
    include_sources: bool = Field(True, description="Include source citations in response")


class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    score: float
    company: Optional[str] = None
    ticker: Optional[str] = None
    year: Optional[int] = None
    quarter: Optional[str] = None
    section_type: Optional[str] = None
    report_type: Optional[str] = None
    page_num: Optional[int] = None


class TokenUsageDetail(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class QueryResponse(BaseModel):
    query_id: str
    question: str
    answer: str
    sources: list[RetrievedChunk]
    query_type: str
    latency_ms: float
    tokens_used: TokenUsageDetail
    chunk_count: int
