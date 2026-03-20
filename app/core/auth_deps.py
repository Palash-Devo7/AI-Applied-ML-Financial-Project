"""Reusable FastAPI dependencies for auth + credit gating."""
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import decode_token
from app.data.auth_db import (
    get_user_by_id, get_user_by_api_key,
    check_and_consume, consume_credits, CREDIT_COSTS,
)

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    """Validate JWT or API key. Returns user dict."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = credentials.credentials

    if token.startswith("fr_"):
        user = get_user_by_api_key(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return user

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_verified(user: dict = Depends(get_current_user)) -> dict:
    """Require email verification. Admins bypass this check."""
    if user["role"] != "admin" and not user.get("is_verified"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "email_not_verified",
                "message": "Please verify your email address before using this feature. Check your inbox.",
            },
        )
    return user


def require_credits(request: Request, user: dict = Depends(require_verified)) -> dict:
    """
    Check if user has enough credits for this endpoint.
    Attaches cost to request.state so the router can consume after success.
    """
    path = request.url.path
    cost = CREDIT_COSTS.get(path, 0)

    if cost > 0:
        allowed, used, limit = check_and_consume(user["id"], user["role"], path)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "daily_credit_limit_reached",
                    "message": f"You've used all {limit} daily credits. Resets at midnight UTC.",
                    "used": used,
                    "limit": limit,
                },
            )
        request.state.credit_cost = cost
        request.state.user_id = user["id"]

    return user


def consume_after_success(request: Request) -> None:
    """Call this after a successful response to log credit usage."""
    cost = getattr(request.state, "credit_cost", 0)
    user_id = getattr(request.state, "user_id", None)
    if cost > 0 and user_id:
        consume_credits(user_id, request.url.path, cost)
