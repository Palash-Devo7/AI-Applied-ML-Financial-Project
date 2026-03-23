"""Auth router — register, login, me, credits."""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

from app.core.security import (
    hash_password, verify_password, create_access_token,
    decode_token, generate_api_key,
)
from app.data.auth_db import (
    create_user, get_user_by_email, get_user_by_id,
    user_exists, get_credit_summary,
    create_verification_token, consume_verification_token,
    verify_user, list_all_users, get_admin_stats,
)
from app.core.email import send_verification_email, send_welcome_email

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)


# ─── Request / Response models ────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    api_key: str


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    api_key: str
    is_verified: bool = False
    credits: dict


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest):
    if user_exists(body.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    api_key = generate_api_key()
    user = create_user(
        email=body.email,
        password_hash=hash_password(body.password),
        role="trial",
        api_key=api_key,
    )
    token = create_access_token(user["id"], user["email"], user["role"])
    # Send verification email (non-blocking)
    verification_token = create_verification_token(user["id"])
    send_verification_email(user["email"], verification_token)
    return TokenResponse(access_token=token, role=user["role"], api_key=api_key)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    user = get_user_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(user["id"], user["email"], user["role"])
    return TokenResponse(
        access_token=token,
        role=user["role"],
        api_key=user["api_key"] or "",
    )


@router.get("/me", response_model=UserResponse)
async def get_me(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    user = _get_current_user(credentials)
    return UserResponse(
        id=user["id"],
        email=user["email"],
        role=user["role"],
        api_key=user["api_key"] or "",
        is_verified=bool(user.get("is_verified")),
        credits=get_credit_summary(user["id"], user["role"]),
    )


@router.get("/verify")
async def verify_email(token: str):
    """Verify email address via token link."""
    user_id = consume_verification_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")
    verify_user(user_id)
    user = get_user_by_id(user_id)
    send_welcome_email(user["email"])
    return {"status": "verified", "message": "Email verified successfully. You can now use all features."}


@router.get("/admin/users")
async def admin_list_users(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    """List all users with usage stats — admin only."""
    user = _get_current_user(credentials)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return {"users": list_all_users()}


@router.get("/admin/stats")
async def admin_stats(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    """Platform analytics — admin only."""
    user = _get_current_user(credentials)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    from app.data.financial_db import _get_conn as fin_conn
    stats = get_admin_stats()
    # Loaded companies from financial DB
    try:
        conn = fin_conn()
        rows = conn.execute(
            "SELECT company, ticker, status, loaded_at FROM company_registry ORDER BY loaded_at DESC LIMIT 20"
        ).fetchall()
        stats["loaded_companies"] = [dict(r) for r in rows]
    except Exception:
        stats["loaded_companies"] = []
    return stats


@router.post("/resend-verification")
async def resend_verification(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    """Resend verification email."""
    user = _get_current_user(credentials)
    if user.get("is_verified"):
        raise HTTPException(status_code=400, detail="Email already verified")
    token = create_verification_token(user["id"])
    send_verification_email(user["email"], token)
    return {"status": "sent", "message": "Verification email resent"}


# ─── Shared dependency ────────────────────────────────────────────────────────

def _get_current_user(credentials: HTTPAuthorizationCredentials) -> dict:
    """Decode JWT or API key from Authorization header."""
    from app.data.auth_db import get_user_by_api_key
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = credentials.credentials

    # API key format: fr_<random>
    if token.startswith("fr_"):
        user = get_user_by_api_key(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return user

    # JWT
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
