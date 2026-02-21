"""Thread-safe async wrapper around ChromaDB PersistentClient."""
from __future__ import annotations

import asyncio
from typing import Any, Optional

import structlog
from starlette.concurrency import run_in_threadpool

logger = structlog.get_logger(__name__)


class VectorStoreClient:
    """Async-safe ChromaDB wrapper.

    ChromaDB's PersistentClient is synchronous. All methods are wrapped with
    ``starlette.concurrency.run_in_threadpool`` so they don't block the
    asyncio event loop.  Write operations are guarded by ``asyncio.Lock``
    to prevent concurrent write corruption.
    """

    def __init__(
        self,
        persist_dir: str = "./data/chroma_db",
        collection_name: str = "finance_docs",
        distance_function: str = "cosine",
    ) -> None:
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.distance_function = distance_function
        self._write_lock = asyncio.Lock()
        self._client = None
        self._collection = None
        self._init_client()

    # ── Initialization ────────────────────────────────────────────────────────

    def _init_client(self) -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self._client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": self.distance_function},
        )
        logger.info(
            "chroma_collection_ready",
            collection=self.collection_name,
            count=self._collection.count(),
        )

    # ── Write operations (lock-protected) ─────────────────────────────────────

    async def upsert_chunks(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        """Upsert chunks into ChromaDB. Thread-safe via asyncio.Lock."""
        async with self._write_lock:
            await run_in_threadpool(
                self._collection.upsert,
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

    async def delete_by_document_id(self, document_id: str) -> None:
        """Delete all chunks belonging to a document."""
        async with self._write_lock:
            await run_in_threadpool(
                self._collection.delete,
                where={"document_id": {"$eq": document_id}},
            )

    async def delete_collection(self, collection_name: str) -> None:
        """Delete a named collection."""
        async with self._write_lock:
            await run_in_threadpool(self._client.delete_collection, collection_name)
            # Re-create the default collection
            if collection_name == self.collection_name:
                self._collection = await run_in_threadpool(
                    self._client.get_or_create_collection,
                    name=self.collection_name,
                    metadata={"hnsw:space": self.distance_function},
                )

    # ── Read operations ───────────────────────────────────────────────────────

    async def query(
        self,
        query_embeddings: list[list[float]],
        n_results: int = 10,
        where: Optional[dict] = None,
        include: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Query the collection for nearest neighbours."""
        kwargs: dict[str, Any] = {
            "query_embeddings": query_embeddings,
            "n_results": min(n_results, await self.count() or 1),
            "include": include or ["documents", "metadatas", "distances", "embeddings"],
        }
        if where:
            kwargs["where"] = where

        return await run_in_threadpool(self._collection.query, **kwargs)

    async def get_by_ids(self, ids: list[str]) -> dict[str, Any]:
        """Fetch specific chunks by ID."""
        return await run_in_threadpool(
            self._collection.get,
            ids=ids,
            include=["documents", "metadatas", "embeddings"],
        )

    async def count(self) -> int:
        """Return total number of vectors in the collection."""
        return await run_in_threadpool(self._collection.count)

    async def get_collection_info(self) -> dict:
        """Return collection metadata."""
        count = await self.count()
        return {
            "name": self.collection_name,
            "count": count,
            "distance_function": self.distance_function,
            "persist_dir": self.persist_dir,
        }
