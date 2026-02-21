"""Dependency injection providers for FastAPI."""
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings


# ── Embedding Service ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_embedding_service_singleton():
    from app.services.embedding_service import EmbeddingService
    settings = get_settings()
    return EmbeddingService(
        model_name=settings.embedding_model,
        strategy=settings.embedding_strategy,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
    )


async def get_embedding_service():
    return _get_embedding_service_singleton()


# ── Vector Store ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_vector_store_singleton():
    from app.core.vector_store import VectorStoreClient
    settings = get_settings()
    return VectorStoreClient(
        persist_dir=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection_name,
        distance_function=settings.chroma_distance_function,
    )


async def get_vector_store():
    return _get_vector_store_singleton()


# ── Generation Service ────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_generation_service_singleton():
    from app.services.generation_service import GenerationService
    settings = get_settings()
    return GenerationService(
        api_key=settings.anthropic_api_key,
        model=settings.claude_model,
        temperature=settings.claude_temperature,
        max_tokens=settings.claude_max_tokens,
        collect_training_data=settings.collect_training_data,
        training_data_path=settings.training_data_path,
    )


async def get_generation_service():
    return _get_generation_service_singleton()


# ── Retrieval Service ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_retrieval_service_singleton():
    from app.services.retrieval_service import RetrievalService
    settings = get_settings()
    return RetrievalService(
        vector_store=_get_vector_store_singleton(),
        top_k=settings.retrieval_top_k,
        fetch_multiplier=settings.retrieval_fetch_multiplier,
        rrf_alpha=settings.retrieval_rrf_alpha,
    )


async def get_retrieval_service():
    return _get_retrieval_service_singleton()


# ── MCP Service ───────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_mcp_service_singleton():
    from app.services.mcp_service import MCPService
    settings = get_settings()
    return MCPService(max_context_tokens=settings.max_context_tokens)


async def get_mcp_service():
    return _get_mcp_service_singleton()


# ── Convenience type aliases ──────────────────────────────────────────────────
SettingsDep = Annotated[Settings, Depends(get_settings)]
