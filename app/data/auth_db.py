"""User auth + credit tracking database operations."""
import sqlite3
import threading
from datetime import date, datetime, timezone
from typing import Optional
from pathlib import Path

from ulid import ULID

DB_PATH = Path("data/auth.db")
_lock = threading.Lock()

# Credit costs per endpoint path (exact match)
CREDIT_COSTS: dict[str, int] = {
    "/query": 1,
    "/query/stream": 1,
    "/forecast/event": 2,
    "/companies/load": 1,
    "/documents/upload": 2,
}

DAILY_LIMIT_TRIAL = 10   # credits per day for trial users
GUEST_CREDIT_LIMIT = 3   # lifetime credits for guest sessions


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_auth_db() -> None:
    """Create tables and run migrations."""
    with _lock, _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            TEXT PRIMARY KEY,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL DEFAULT 'trial',
                api_key       TEXT UNIQUE,
                is_active     INTEGER NOT NULL DEFAULT 1,
                is_verified   INTEGER NOT NULL DEFAULT 0,
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS verification_tokens (
                token       TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL,
                expires_at  TEXT NOT NULL,
                used        INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS daily_credits (
                user_id      TEXT NOT NULL,
                date         TEXT NOT NULL,
                credits_used INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, date),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS credit_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                endpoint    TEXT NOT NULL,
                credits     INTEGER NOT NULL,
                used_at     TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id               TEXT PRIMARY KEY,
                user_id          TEXT,
                created_at       TEXT NOT NULL DEFAULT (datetime('now')),
                feature          TEXT NOT NULL,
                succeeded        TEXT NOT NULL,
                accuracy         INTEGER,
                speed            INTEGER,
                ease             INTEGER,
                issues           TEXT,
                comment          TEXT,
                company          TEXT,
                query            TEXT,
                response_time_ms INTEGER,
                had_error        INTEGER NOT NULL DEFAULT 0
            );
        """)

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS guest_sessions (
                guest_id     TEXT PRIMARY KEY,
                credits_used INTEGER NOT NULL DEFAULT 0,
                first_seen   TEXT NOT NULL DEFAULT (datetime('now')),
                last_seen    TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)

    # Migration: add is_verified to existing installs (no-op if already exists)
    try:
        with _lock, _get_conn() as conn:
            conn.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass


# ─── Users ────────────────────────────────────────────────────────────────────

def create_user(email: str, password_hash: str, role: str = "trial", api_key: Optional[str] = None) -> dict:
    uid = str(ULID())
    # Admin users are auto-verified
    is_verified = 1 if role == "admin" else 0
    with _lock, _get_conn() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, role, api_key, is_verified) VALUES (?, ?, ?, ?, ?, ?)",
            (uid, email.lower().strip(), password_hash, role, api_key, is_verified),
        )
    return get_user_by_id(uid)


def get_user_by_email(email: str) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? AND is_active = 1",
            (email.lower().strip(),),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_api_key(api_key: str) -> Optional[dict]:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE api_key = ? AND is_active = 1", (api_key,)
        ).fetchone()
    return dict(row) if row else None


def user_exists(email: str) -> bool:
    with _get_conn() as conn:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
    return row is not None


def verify_user(user_id: str) -> None:
    """Mark user as verified."""
    with _lock, _get_conn() as conn:
        conn.execute("UPDATE users SET is_verified = 1 WHERE id = ?", (user_id,))


# ─── Verification tokens ───────────────────────────────────────────────────────

def create_verification_token(user_id: str) -> str:
    """Generate a 24-hour verification token."""
    import secrets
    from datetime import timedelta
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    with _lock, _get_conn() as conn:
        # Invalidate any existing unused tokens for this user
        conn.execute(
            "UPDATE verification_tokens SET used = 1 WHERE user_id = ? AND used = 0",
            (user_id,),
        )
        conn.execute(
            "INSERT INTO verification_tokens (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at),
        )
    return token


def consume_verification_token(token: str) -> Optional[str]:
    """
    Validate and consume a verification token.
    Returns user_id if valid, None if invalid/expired/used.
    """
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT user_id, expires_at, used FROM verification_tokens WHERE token = ?",
            (token,),
        ).fetchone()

    if not row:
        return None
    if row["used"]:
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        return None

    with _lock, _get_conn() as conn:
        conn.execute("UPDATE verification_tokens SET used = 1 WHERE token = ?", (token,))

    return row["user_id"]


# ─── Admin ─────────────────────────────────────────────────────────────────────

def list_all_users() -> list[dict]:
    """Return all users with credit summary — admin only."""
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT u.id, u.email, u.role, u.is_verified, u.is_active, u.created_at,
                      COALESCE(dc.credits_used, 0) as credits_used_today,
                      COALESCE(cl.total_credits, 0) as credits_used_total
               FROM users u
               LEFT JOIN daily_credits dc
                 ON u.id = dc.user_id AND dc.date = date('now')
               LEFT JOIN (SELECT user_id, SUM(credits) as total_credits FROM credit_log GROUP BY user_id) cl
                 ON u.id = cl.user_id
               ORDER BY u.created_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def get_admin_stats() -> dict:
    """Return aggregated platform stats — admin only."""
    with _get_conn() as conn:
        # Signups per day (last 30 days)
        signups = conn.execute(
            """SELECT date(created_at) as day, COUNT(*) as count
               FROM users WHERE created_at >= date('now', '-30 days')
               GROUP BY day ORDER BY day"""
        ).fetchall()

        # Daily active users (last 30 days)
        dau = conn.execute(
            """SELECT date, COUNT(DISTINCT user_id) as count
               FROM daily_credits WHERE date >= date('now', '-30 days')
               GROUP BY date ORDER BY date"""
        ).fetchall()

        # Endpoint usage totals
        endpoint_usage = conn.execute(
            """SELECT endpoint, COUNT(*) as count, SUM(credits) as credits
               FROM credit_log GROUP BY endpoint ORDER BY count DESC"""
        ).fetchall()

        # Total platform stats
        totals = conn.execute(
            """SELECT
               (SELECT COUNT(*) FROM users) as total_users,
               (SELECT COUNT(*) FROM users WHERE is_verified=1) as verified_users,
               (SELECT COUNT(DISTINCT user_id) FROM daily_credits WHERE date=date('now')) as active_today,
               (SELECT COUNT(*) FROM credit_log) as total_actions,
               (SELECT COUNT(*) FROM credit_log WHERE endpoint='/forecast/event') as total_forecasts,
               (SELECT COUNT(*) FROM credit_log WHERE endpoint IN ('/query','/query/stream')) as total_queries,
               (SELECT COUNT(*) FROM credit_log WHERE endpoint='/companies/load') as total_loads"""
        ).fetchone()

    return {
        "totals": dict(totals),
        "signups_by_day": [dict(r) for r in signups],
        "dau_by_day": [dict(r) for r in dau],
        "endpoint_usage": [dict(r) for r in endpoint_usage],
    }


# ─── Credits ──────────────────────────────────────────────────────────────────

def get_credits_used_today(user_id: str) -> int:
    today = date.today().isoformat()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT credits_used FROM daily_credits WHERE user_id = ? AND date = ?",
            (user_id, today),
        ).fetchone()
    return row["credits_used"] if row else 0


def consume_credits(user_id: str, endpoint: str, credits: int) -> None:
    today = date.today().isoformat()
    with _lock, _get_conn() as conn:
        conn.execute(
            """INSERT INTO daily_credits (user_id, date, credits_used)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, date) DO UPDATE SET credits_used = credits_used + ?""",
            (user_id, today, credits, credits),
        )
        conn.execute(
            "INSERT INTO credit_log (user_id, endpoint, credits) VALUES (?, ?, ?)",
            (user_id, endpoint, credits),
        )


def check_and_consume(user_id: str, role: str, endpoint: str) -> tuple[bool, int, int]:
    """
    Returns (allowed, credits_used_today, daily_limit).
    Admins always allowed. Trial users checked against DAILY_LIMIT_TRIAL.
    Does NOT consume — call consume_credits() after successful response.
    """
    if role == "admin":
        return True, 0, -1  # -1 = unlimited

    cost = CREDIT_COSTS.get(endpoint, 0)
    used = get_credits_used_today(user_id)
    allowed = (used + cost) <= DAILY_LIMIT_TRIAL
    return allowed, used, DAILY_LIMIT_TRIAL


def get_credit_summary(user_id: str, role: str) -> dict:
    if role == "admin":
        return {"used": 0, "limit": -1, "remaining": -1, "role": "admin"}
    used = get_credits_used_today(user_id)
    remaining = max(0, DAILY_LIMIT_TRIAL - used)
    return {"used": used, "limit": DAILY_LIMIT_TRIAL, "remaining": remaining, "role": "trial"}


# ─── Guest sessions ───────────────────────────────────────────────────────────

def get_guest_credits_used(guest_id: str) -> int:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT credits_used FROM guest_sessions WHERE guest_id = ?", (guest_id,)
        ).fetchone()
    return row["credits_used"] if row else 0


def check_and_consume_guest(guest_id: str) -> tuple[bool, int, int]:
    """Returns (allowed, credits_used, limit). Does NOT consume — call consume_guest_credit after success."""
    used = get_guest_credits_used(guest_id)
    return (used < GUEST_CREDIT_LIMIT), used, GUEST_CREDIT_LIMIT


def consume_guest_credit(guest_id: str) -> None:
    with _lock, _get_conn() as conn:
        conn.execute(
            """INSERT INTO guest_sessions (guest_id, credits_used)
               VALUES (?, 1)
               ON CONFLICT(guest_id) DO UPDATE SET
                 credits_used = credits_used + 1,
                 last_seen = datetime('now')""",
            (guest_id,),
        )


# ─── Feedback ─────────────────────────────────────────────────────────────────

def save_feedback(
    user_id: Optional[str],
    feature: str,
    succeeded: str,
    accuracy: Optional[int],
    speed: Optional[int],
    ease: Optional[int],
    issues: Optional[str],
    comment: Optional[str],
    company: Optional[str],
    query: Optional[str],
    response_time_ms: Optional[int],
    had_error: int,
) -> None:
    fid = str(ULID())
    with _lock, _get_conn() as conn:
        conn.execute(
            """INSERT INTO feedback
               (id, user_id, feature, succeeded, accuracy, speed, ease,
                issues, comment, company, query, response_time_ms, had_error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (fid, user_id, feature, succeeded, accuracy, speed, ease,
             issues, comment, company, query, response_time_ms, had_error),
        )
