"""Application configuration via Pydantic BaseSettings."""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "Finance AI RAG"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1

    # ── LLM provider ─────────────────────────────────────────────────────────
    llm_provider: Literal["deepseek", "claude", "groq"] = "groq"

    # ── Groq (free tier, default) ─────────────────────────────────────────────
    groq_api_key: str = Field(default="", description="Groq API key")
    groq_model: str = "llama-3.3-70b-versatile"

    # ── DeepSeek (optional) ───────────────────────────────────────────────────
    deepseek_api_key: str = Field(default="", description="DeepSeek API key")
    deepseek_model: str = "deepseek-chat"

    # ── Claude / Anthropic (optional) ────────────────────────────────────────
    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    claude_model: str = "claude-sonnet-4-6"

    # ── Shared LLM settings ───────────────────────────────────────────────────
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048

    # ── Embeddings ────────────────────────────────────────────────────────────
    embedding_model: str = "ProsusAI/finbert"
    embedding_strategy: Literal["cls", "mean"] = "cls"
    embedding_batch_size: int = 16
    embedding_device: str = "cpu"

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma_db"
    chroma_collection_name: str = "finance_docs"
    chroma_distance_function: Literal["cosine", "l2", "ip"] = "cosine"

    # ── Retrieval ─────────────────────────────────────────────────────────────
    retrieval_top_k: int = 5
    retrieval_fetch_multiplier: int = 2  # over-fetch factor for hybrid
    retrieval_rrf_alpha: float = 0.7     # vector weight in RRF
    max_context_tokens: int = 6000

    # ── Chunking ──────────────────────────────────────────────────────────────
    chunk_size_tokens: int = 480
    chunk_overlap_tokens: int = 64

    # ── Phase 2 hooks ─────────────────────────────────────────────────────────
    collect_training_data: bool = False
    training_data_path: str = "./data/training_data.jsonl"
    use_finetuned_model: bool = False
    finetuned_model_path: str = ""

    # ── Auth + Security ───────────────────────────────────────────────────────
    jwt_secret: str = Field(default="change-me-in-production-use-openssl-rand-hex-32")
    jwt_expire_hours: int = 24
    admin_email: str = Field(default="admin@financerag.com")
    admin_password: str = Field(default="")   # Set in .env — empty disables auto-create
    allowed_origins: str = Field(default="http://localhost:3000")  # comma-separated

    # ── Email ─────────────────────────────────────────────────────────────────
    resend_api_key: str = Field(default="")
    email_from: str = Field(default="noreply@quantcortex.in")
    frontend_url: str = Field(default="https://quantcortex.in")

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_query: str = "5/minute"
    rate_limit_upload: str = "5/minute"
    rate_limit_global: str = "60/minute"

    # ── Monitoring ────────────────────────────────────────────────────────────
    prometheus_enabled: bool = True
    metrics_prefix: str = "finance_rag"


@lru_cache
def get_settings() -> Settings:
    return Settings()
