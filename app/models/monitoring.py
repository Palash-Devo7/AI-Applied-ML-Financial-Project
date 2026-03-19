"""Pydantic models for monitoring and observability."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RequestLog(BaseModel):
    request_id: str
    method: str
    path: str
    status_code: int
    latency_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class TokenUsage(BaseModel):
    query_id: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorRecord(BaseModel):
    request_id: str
    error_type: str
    error_message: str
    path: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    stack_trace: Optional[str] = None
