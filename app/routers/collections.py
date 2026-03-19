"""Collection management endpoints."""
import structlog
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth_deps import get_current_user
from app.dependencies import get_vector_store

router = APIRouter(prefix="/collections", tags=["collections"])
logger = structlog.get_logger(__name__)


@router.get("")
async def list_collections(vector_store=Depends(get_vector_store), user: dict = Depends(get_current_user)) -> dict:
    """List all available collections and their metadata."""
    try:
        info = await vector_store.get_collection_info()
        return {"collections": [info]}
    except Exception as exc:
        logger.error("list_collections_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/companies")
async def list_companies(vector_store=Depends(get_vector_store), user: dict = Depends(get_current_user)) -> dict:
    """List all unique company names stored in the collection."""
    try:
        from starlette.concurrency import run_in_threadpool
        result = await run_in_threadpool(
            vector_store._collection.get,
            include=["metadatas"],
        )
        companies = sorted({
            m.get("company")
            for m in (result.get("metadatas") or [])
            if m.get("company")
        })
        return {"companies": companies, "count": len(companies)}
    except Exception as exc:
        logger.error("list_companies_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{collection_name}")
async def get_collection(
    collection_name: str,
    vector_store=Depends(get_vector_store),
    user: dict = Depends(get_current_user),
) -> dict:
    """Get metadata for a specific collection."""
    try:
        info = await vector_store.get_collection_info()
        if info.get("name") != collection_name:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        return info
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_collection_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{collection_name}")
async def delete_collection(
    collection_name: str,
    vector_store=Depends(get_vector_store),
    user: dict = Depends(get_current_user),
) -> dict:
    """Delete a collection and all its documents."""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        await vector_store.delete_collection(collection_name)
        logger.info("collection_deleted", collection=collection_name)
        return {"status": "deleted", "collection": collection_name}
    except Exception as exc:
        logger.error("delete_collection_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc
