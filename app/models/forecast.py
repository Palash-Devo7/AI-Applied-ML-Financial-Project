"""Pydantic models for multi-agent event forecasting."""
from typing import Optional
from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    company: str = Field(..., description="Company name (must match uploaded PDFs exactly)")
    event_type: str = Field(
        ...,
        description=(
            "Type of event: earnings_miss, earnings_beat, management_change, "
            "regulatory_action, acquisition, macro_shock, capacity_expansion, "
            "debt_restructuring, sector_disruption, geopolitical"
        ),
    )
    event_description: str = Field(
        ..., min_length=10, max_length=1000,
        description="Describe the specific event in detail",
    )
    horizon_days: int = Field(90, ge=30, le=365, description="Forecast horizon in days")


class AgentView(BaseModel):
    agent: str               # "bull" | "bear" | "macro"
    stance: str              # "BULLISH" | "BEARISH" | "NEUTRAL"
    estimated_impact: str    # e.g. "+5-10% over 90 days"
    key_points: list[str]
    reasoning: str


class ForecastResponse(BaseModel):
    forecast_id: str
    company: str
    event_type: str
    event_description: str
    horizon_days: int
    agent_views: list[AgentView]
    base_case: str
    bull_case: str
    bear_case: str
    confidence: str          # HIGH | MEDIUM | LOW
    key_risks: list[str]
    key_catalysts: list[str]
    similar_events: list[dict]
    latency_ms: float
    total_tokens: int
