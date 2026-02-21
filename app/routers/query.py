"""Query router: POST /query."""
import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    get_embedding_service,
    get_generation_service,
    get_mcp_service,
    get_retrieval_service,
)
from app.models.queries import QueryRequest, QueryResponse
from app.services.query_service import QueryService

router = APIRouter(tags=["query"])
logger = structlog.get_logger(__name__)


@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a financial question for RAG-augmented answer",
)
async def query_documents(
    request: QueryRequest,
    embedding_service=Depends(get_embedding_service),
    retrieval_service=Depends(get_retrieval_service),
    generation_service=Depends(get_generation_service),
    mcp_service=Depends(get_mcp_service),
) -> QueryResponse:
    service = QueryService(
        embedding_service=embedding_service,
        retrieval_service=retrieval_service,
        generation_service=generation_service,
        mcp_service=mcp_service,
    )

    try:
        return await service.query(request)
    except Exception as exc:
        logger.error("query_endpoint_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {exc}",
        ) from exc
