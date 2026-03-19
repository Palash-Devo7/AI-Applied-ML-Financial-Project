"""Document ingestion router: POST /documents/upload."""
import asyncio
from typing import Dict

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel

from app.core.auth_deps import get_current_user, require_credits, consume_after_success
from app.core.limiter import limiter
from app.dependencies import get_embedding_service, get_vector_store
from app.models.documents import UploadResponse
from app.services.ingestion_service import IngestionService

router = APIRouter(tags=["ingestion"])
logger = structlog.get_logger(__name__)

_MAX_FILE_SIZE_MB = 50
_MAX_FILE_SIZE_BYTES = _MAX_FILE_SIZE_MB * 1024 * 1024

# In-memory job tracker: document_id -> status dict
_jobs: Dict[str, dict] = {}


class JobStatus(BaseModel):
    document_id: str
    filename: str
    status: str           # processing | ingested | failed
    detail: str = ""
    chunk_count: int = 0
    company: str = ""
    report_type: str = ""
    year: int | None = None


async def _run_ingestion(
    document_id: str,
    content: bytes,
    filename: str,
    overrides: dict,
    embedding_service,
    vector_store,
) -> None:
    """Background task: run full ingestion pipeline and update job status."""
    service = IngestionService(
        embedding_service=embedding_service,
        vector_store=vector_store,
    )
    try:
        result = await service.ingest(
            content=content,
            filename=filename,
            overrides=overrides,
            document_id=document_id,
        )
        _jobs[document_id] = {
            "document_id": document_id,
            "filename": filename,
            "status": "ingested",
            "chunk_count": result.chunk_count,
            "company": result.company or "",
            "report_type": result.report_type or "",
            "year": result.year,
        }
        logger.info("background_ingestion_complete", document_id=document_id, filename=filename)
    except Exception as exc:
        _jobs[document_id] = {
            "document_id": document_id,
            "filename": filename,
            "status": "failed",
            "detail": str(exc),
        }
        logger.error("background_ingestion_failed", document_id=document_id, error=str(exc))


@router.post(
    "/upload",
    response_model=JobStatus,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and ingest a financial document (PDF) — returns immediately, processes in background",
)
@limiter.limit("5/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to ingest"),
    company: str | None = Form(None, description="Company name override"),
    ticker: str | None = Form(None, description="Stock ticker override"),
    report_type: str | None = Form(None, description="Report type (10-K, 10-Q, 8-K, EARNINGS)"),
    year: int | None = Form(None, description="Fiscal year override"),
    sector: str | None = Form(None, description="Industry sector"),
    user: dict = Depends(require_credits),
    embedding_service=Depends(get_embedding_service),
    vector_store=Depends(get_vector_store),
) -> JobStatus:
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(content) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {_MAX_FILE_SIZE_MB} MB",
        )

    overrides = {
        k: v
        for k, v in {
            "company": company,
            "ticker": ticker,
            "report_type": report_type,
            "year": year,
            "sector": sector,
        }.items()
        if v is not None
    }

    # Generate document ID upfront so we can track it immediately
    from ulid import ULID
    document_id = str(ULID())

    # Register job as processing
    _jobs[document_id] = {
        "document_id": document_id,
        "filename": file.filename,
        "status": "processing",
    }

    # Kick off ingestion in background — returns immediately
    background_tasks.add_task(
        _run_ingestion,
        document_id=document_id,
        content=content,
        filename=file.filename,
        overrides=overrides,
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    logger.info("ingestion_queued", document_id=document_id, filename=file.filename)
    consume_after_success(request)

    return JobStatus(
        document_id=document_id,
        filename=file.filename,
        status="processing",
        detail="Ingestion started in background. Poll /documents/{document_id}/status to track progress.",
    )


@router.get(
    "/{document_id}/status",
    response_model=JobStatus,
    summary="Check ingestion status for a document",
)
async def get_ingestion_status(document_id: str, user: dict = Depends(get_current_user)) -> JobStatus:
    job = _jobs.get(document_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No job found for document_id={document_id}",
        )
    return JobStatus(**job)


@router.get(
    "/jobs",
    summary="List all ingestion jobs and their statuses (admin only)",
)
async def list_jobs(user: dict = Depends(get_current_user)) -> list[JobStatus]:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return [JobStatus(**j) for j in _jobs.values()]
