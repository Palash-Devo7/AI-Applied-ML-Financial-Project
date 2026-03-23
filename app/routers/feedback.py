"""Feedback router — POST /feedback"""
import json
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.data.auth_db import save_feedback
from app.routers.auth import _get_current_user

router = APIRouter(prefix="/feedback", tags=["feedback"])
bearer = HTTPBearer(auto_error=False)


class FeedbackRequest(BaseModel):
    feature: str                        # forecast | chat | both
    succeeded: str                      # yes | partially | no
    accuracy: Optional[int] = None      # 1–5
    speed: Optional[int] = None         # 1–5
    ease: Optional[int] = None          # 1–5
    issues: list[str] = []
    comment: Optional[str] = None
    # auto-captured context
    company: Optional[str] = None
    query: Optional[str] = None
    response_time_ms: Optional[int] = None
    had_error: bool = False


@router.post("", status_code=201)
async def submit_feedback(
    body: FeedbackRequest,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    user_id = None
    if credentials:
        try:
            user = _get_current_user(credentials)
            user_id = user["id"]
        except Exception:
            pass

    save_feedback(
        user_id=user_id,
        feature=body.feature,
        succeeded=body.succeeded,
        accuracy=body.accuracy,
        speed=body.speed,
        ease=body.ease,
        issues=json.dumps(body.issues) if body.issues else None,
        comment=body.comment,
        company=body.company,
        query=body.query,
        response_time_ms=body.response_time_ms,
        had_error=int(body.had_error),
    )
    return {"status": "received"}
