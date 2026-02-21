"""Document ingestion router: POST /documents/upload."""
import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.dependencies import get_embedding_service, get_vector_store
from app.models.documents import UploadResponse
from app.services.ingestion_service import IngestionService

router = APIRouter(tags=["ingestion"])
logger = structlog.get_logger(__name__)

_MAX_FILE_SIZE_MB = 50
_MAX_FILE_SIZE_BYTES = _MAX_FILE_SIZE_MB * 1024 * 1024


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and ingest a financial document (PDF)",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to ingest"),
    company: str | None = Form(None, description="Company name override"),
    ticker: str | None = Form(None, description="Stock ticker override"),
    report_type: str | None = Form(None, description="Report type (10-K, 10-Q, 8-K, EARNINGS)"),
    year: int | None = Form(None, description="Fiscal year override"),
    sector: str | None = Form(None, description="Industry sector"),
    embedding_service=Depends(get_embedding_service),
    vector_store=Depends(get_vector_store),
) -> UploadResponse:
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    # Read file content
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

    service = IngestionService(
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    try:
        result = await service.ingest(
            content=content,
            filename=file.filename,
            overrides=overrides,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("upload_failed", filename=file.filename, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {exc}",
        ) from exc
