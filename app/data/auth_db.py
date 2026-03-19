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

DAILY_LIMIT_TRIAL = 10  # credits per day for trial users


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_auth_db() -> None:
    """Create tables and default admin user."""
    with _lock, _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                email       TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'trial',
                api_key     TEXT UNIQUE,
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS daily_credits (
                user_id     TEXT NOT NULL,
                date        TEXT NOT NULL,
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
        """)


# ─── Users ────────────────────────────────────────────────────────────────────

def create_user(email: str, password_hash: str, role: str = "trial", api_key: Optional[str] = None) -> dict:
    uid = str(ULID())
    with _lock, _get_conn() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, role, api_key) VALUES (?, ?, ?, ?, ?)",
            (uid, email.lower().strip(), password_hash, role, api_key),
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
