"""Ingestion service: orchestrates parse → chunk → embed → store."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import structlog
from ulid import ULID

from app.core.chunker import FinancialChunker
from app.core.document_parser import DocumentParser
from app.core.metadata_extractor import ExtractedMetadata, MetadataExtractor
from app.core.vector_store import VectorStoreClient
from app.models.documents import DocumentMetadata, UploadResponse
from app.monitoring.metrics import (
    CHUNKS_CREATED_TOTAL,
    DOCUMENTS_INGESTED_TOTAL,
    INGESTION_DURATION_SECONDS,
)
from app.services.embedding_service import EmbeddingService

logger = structlog.get_logger(__name__)


class IngestionService:
    """End-to-end document ingestion pipeline."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreClient,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._parser = DocumentParser()
        self._extractor = MetadataExtractor()
        self._chunker = FinancialChunker()

    async def ingest(
        self,
        content: bytes,
        filename: str,
        overrides: Optional[dict] = None,
    ) -> UploadResponse:
        """Ingest a single PDF document end-to-end."""
        t0 = time.perf_counter()
        document_id = str(ULID())
        overrides = overrides or {}

        logger.info("ingestion_started", document_id=document_id, filename=filename)

        try:
            # 1. Parse PDF
            parsed_doc = self._parser.parse(content, filename)

            if parsed_doc.total_chars < 100:
                raise ValueError(
                    f"Document appears empty or unreadable: {parsed_doc.total_chars} chars extracted"
                )

            # 2. Extract metadata from full text
            doc_meta: ExtractedMetadata = self._extractor.extract_document_metadata(
                text=parsed_doc.full_text,
                filename=filename,
                overrides=overrides,
            )

            # 3. Chunk document
            chunks = self._chunker.chunk_document(parsed_doc.full_text)

            if not chunks:
                raise ValueError("No chunks produced from document")

            # 4. Assign page numbers heuristically (distribute pages over chunks)
            self._assign_page_numbers(chunks, parsed_doc)

            # 5. Build text list for batch embedding
            texts = [chunk.text for chunk in chunks]

            # 6. Embed (async, runs in executor)
            embeddings = await self._embedding_service.embed_texts(texts)

            # 7. Build ChromaDB payloads
            ingested_at = datetime.now(timezone.utc).isoformat()
            ids: list[str] = []
            metadatas: list[dict] = []
            documents: list[str] = []

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = f"{document_id}_{i:04d}"
                section_type = chunk.section_type or "GENERAL"

                meta_dict = self._build_metadata_dict(
                    document_id=document_id,
                    doc_meta=doc_meta,
                    section_type=section_type,
                    page_num=chunk.page_num,
                    token_count=chunk.token_count,
                    ingested_at=ingested_at,
                )

                ids.append(chunk_id)
                metadatas.append(meta_dict)
                documents.append(chunk.text)

                CHUNKS_CREATED_TOTAL.labels(section_type=section_type).inc()

            # 8. Upsert to ChromaDB
            await self._vector_store.upsert_chunks(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            elapsed = time.perf_counter() - t0
            INGESTION_DURATION_SECONDS.observe(elapsed)
            DOCUMENTS_INGESTED_TOTAL.labels(
                report_type=doc_meta.report_type or "UNKNOWN",
                status="success",
            ).inc()

            logger.info(
                "ingestion_complete",
                document_id=document_id,
                chunk_count=len(chunks),
                elapsed_s=round(elapsed, 2),
                company=doc_meta.company,
                year=doc_meta.year,
                report_type=doc_meta.report_type,
            )

            return UploadResponse(
                document_id=document_id,
                filename=filename,
                chunk_count=len(chunks),
                status="ingested",
                company=doc_meta.company,
                report_type=doc_meta.report_type,
                year=doc_meta.year,
            )

        except Exception as exc:
            DOCUMENTS_INGESTED_TOTAL.labels(
                report_type=overrides.get("report_type", "UNKNOWN"),
                status="error",
            ).inc()
            logger.error(
                "ingestion_failed",
                document_id=document_id,
                error=str(exc),
                filename=filename,
            )
            raise

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _assign_page_numbers(chunks, parsed_doc) -> None:
        """Heuristically assign page numbers to chunks."""
        total_chunks = len(chunks)
        total_pages = parsed_doc.page_count
        if total_pages == 0 or total_chunks == 0:
            return
        for i, chunk in enumerate(chunks):
            # Map chunk index to approximate page
            chunk.page_num = min(
                int(i / total_chunks * total_pages) + 1,
                total_pages,
            )

    @staticmethod
    def _build_metadata_dict(
        document_id: str,
        doc_meta: ExtractedMetadata,
        section_type: str,
        page_num: Optional[int],
        token_count: int,
        ingested_at: str,
    ) -> dict:
        """Build a ChromaDB-compatible flat metadata dict (no None values)."""
        meta: dict = {"document_id": document_id}

        if doc_meta.company:
            meta["company"] = doc_meta.company
        if doc_meta.ticker:
            meta["ticker"] = doc_meta.ticker
        if doc_meta.year is not None:
            meta["year"] = doc_meta.year
        if doc_meta.quarter:
            meta["quarter"] = doc_meta.quarter
        if doc_meta.report_type:
            meta["report_type"] = doc_meta.report_type
        if doc_meta.sector:
            meta["sector"] = doc_meta.sector
        if page_num is not None:
            meta["page_num"] = page_num

        meta["section_type"] = section_type
        meta["token_count"] = token_count
        meta["ingested_at"] = ingested_at

        return meta
