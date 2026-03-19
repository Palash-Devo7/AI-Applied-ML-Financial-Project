"""Pydantic models for document ingestion."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    company: Optional[str] = None
    ticker: Optional[str] = None
    year: Optional[int] = None
    quarter: Optional[str] = None          # "Q1", "Q2", "Q3", "Q4", "FY"
    section_type: Optional[str] = None     # "RISK_FACTORS", "REVENUE", etc.
    report_type: Optional[str] = None      # "10-K", "10-Q", "8-K", "EARNINGS"
    sector: Optional[str] = None
    page_num: Optional[int] = None
    token_count: Optional[int] = None
    ingested_at: Optional[str] = None      # ISO datetime string


class ChunkRecord(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    embedding: list[float]
    metadata: DocumentMetadata


class UploadRequest(BaseModel):
    company: Optional[str] = Field(None, description="Company name override")
    ticker: Optional[str] = Field(None, description="Stock ticker override")
    report_type: Optional[str] = Field(None, description="Report type override (10-K, 10-Q, 8-K)")
    year: Optional[int] = Field(None, description="Fiscal year override")
    sector: Optional[str] = Field(None, description="Industry sector")


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    status: str
    company: Optional[str] = None
    report_type: Optional[str] = None
    year: Optional[int] = None
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
