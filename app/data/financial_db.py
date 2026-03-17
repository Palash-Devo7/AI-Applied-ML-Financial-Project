"""SQLite database for structured financial data — financials, stock prices, events."""
import sqlite3
import threading
from pathlib import Path
from typing import Optional

DB_PATH = Path("./data/financial_data.db")

# One connection per thread (sqlite3 is not thread-safe across threads)
_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        _local.conn = conn
    return _local.conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS company_financials (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            company          TEXT    NOT NULL,
            ticker           TEXT,
            fiscal_year      INTEGER NOT NULL,
            fiscal_quarter   TEXT    DEFAULT 'Annual',
            period_end_date  TEXT,
            revenue          REAL,
            net_income       REAL,
            ebitda           REAL,
            eps              REAL,
            total_assets     REAL,
            total_debt       REAL,
            cash             REAL,
            operating_cash_flow REAL,
            gross_margin     REAL,
            net_margin       REAL,
            created_at       TEXT    DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company, fiscal_year, fiscal_quarter)
        );

        CREATE TABLE IF NOT EXISTS stock_prices (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            company  TEXT    NOT NULL,
            ticker   TEXT    NOT NULL,
            date     TEXT    NOT NULL,
            open     REAL,
            high     REAL,
            low      REAL,
            close    REAL,
            volume   INTEGER,
            UNIQUE(ticker, date)
        );

        CREATE TABLE IF NOT EXISTS events (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            company      TEXT    NOT NULL,
            ticker       TEXT,
            event_date   TEXT    NOT NULL,
            event_type   TEXT    NOT NULL,
            title        TEXT    NOT NULL,
            description  TEXT,
            impact_score REAL    DEFAULT 0.0,
            source       TEXT,
            created_at   TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ticker_map (
            company  TEXT PRIMARY KEY,
            ticker   TEXT NOT NULL,
            exchange TEXT DEFAULT 'NSE'
        );

        CREATE TABLE IF NOT EXISTS company_registry (
            company          TEXT PRIMARY KEY,
            ticker           TEXT NOT NULL,
            scrip_code       TEXT,
            exchange         TEXT DEFAULT 'BSE',
            status           TEXT DEFAULT 'pending',
            loaded_at        TEXT,
            docs_synced_at   TEXT,
            prices_synced_at TEXT,
            doc_count        INTEGER DEFAULT 0,
            error_msg        TEXT,
            created_at       TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_fin_company    ON company_financials(company);
        CREATE INDEX IF NOT EXISTS idx_price_ticker   ON stock_prices(ticker, date);
        CREATE INDEX IF NOT EXISTS idx_event_company  ON events(company, event_date);
        CREATE INDEX IF NOT EXISTS idx_registry_ticker ON company_registry(ticker);
    """)
    conn.commit()


# ── Ticker map ────────────────────────────────────────────────────────────────

def upsert_ticker(company: str, ticker: str, exchange: str = "NSE") -> None:
    conn = _get_conn()
    conn.execute(
        "INSERT INTO ticker_map(company,ticker,exchange) VALUES(?,?,?) "
        "ON CONFLICT(company) DO UPDATE SET ticker=excluded.ticker, exchange=excluded.exchange",
        (company, ticker, exchange),
    )
    conn.commit()


def get_ticker(company: str) -> Optional[str]:
    row = _get_conn().execute(
        "SELECT ticker FROM ticker_map WHERE company=?", (company,)
    ).fetchone()
    return row["ticker"] if row else None


def list_tickers() -> list:
    rows = _get_conn().execute("SELECT company, ticker, exchange FROM ticker_map").fetchall()
    return [dict(r) for r in rows]


# ── Company financials ─────────────────────────────────────────────────────────

def upsert_financials(records: list[dict]) -> int:
    """Insert or replace a list of financial records. Returns rows affected."""
    conn = _get_conn()
    cursor = conn.executemany(
        """INSERT INTO company_financials
           (company, ticker, fiscal_year, fiscal_quarter, period_end_date,
            revenue, net_income, ebitda, eps, total_assets, total_debt,
            cash, operating_cash_flow, gross_margin, net_margin)
           VALUES
           (:company,:ticker,:fiscal_year,:fiscal_quarter,:period_end_date,
            :revenue,:net_income,:ebitda,:eps,:total_assets,:total_debt,
            :cash,:operating_cash_flow,:gross_margin,:net_margin)
           ON CONFLICT(company, fiscal_year, fiscal_quarter)
           DO UPDATE SET
             revenue=excluded.revenue, net_income=excluded.net_income,
             ebitda=excluded.ebitda, eps=excluded.eps,
             total_assets=excluded.total_assets, total_debt=excluded.total_debt,
             cash=excluded.cash, operating_cash_flow=excluded.operating_cash_flow,
             gross_margin=excluded.gross_margin, net_margin=excluded.net_margin,
             ticker=excluded.ticker
        """,
        records,
    )
    conn.commit()
    return cursor.rowcount


def get_financials(company: str, years: int = 5) -> list[dict]:
    rows = _get_conn().execute(
        """SELECT * FROM company_financials
           WHERE company=? AND fiscal_quarter='Annual'
           ORDER BY fiscal_year DESC LIMIT ?""",
        (company, years),
    ).fetchall()
    return [dict(r) for r in rows]


def get_quarterly_financials(company: str, limit: int = 8) -> list[dict]:
    rows = _get_conn().execute(
        """SELECT * FROM company_financials
           WHERE company=? AND fiscal_quarter != 'Annual'
           ORDER BY fiscal_year DESC, fiscal_quarter DESC LIMIT ?""",
        (company, limit),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Stock prices ───────────────────────────────────────────────────────────────

def upsert_stock_prices(records: list[dict]) -> int:
    conn = _get_conn()
    cursor = conn.executemany(
        """INSERT INTO stock_prices(company,ticker,date,open,high,low,close,volume)
           VALUES(:company,:ticker,:date,:open,:high,:low,:close,:volume)
           ON CONFLICT(ticker,date) DO UPDATE SET
             open=excluded.open, high=excluded.high,
             low=excluded.low, close=excluded.close, volume=excluded.volume""",
        records,
    )
    conn.commit()
    return cursor.rowcount


def get_stock_prices(ticker: str, limit: int = 365) -> list[dict]:
    rows = _get_conn().execute(
        "SELECT * FROM stock_prices WHERE ticker=? ORDER BY date DESC LIMIT ?",
        (ticker, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_stock_summary(ticker: str) -> Optional[dict]:
    """Latest price + 52-week high/low + YTD change."""
    row = _get_conn().execute(
        """SELECT
             MAX(CASE WHEN date = (SELECT MAX(date) FROM stock_prices WHERE ticker=?) THEN close END) as latest_close,
             MAX(CASE WHEN date = (SELECT MAX(date) FROM stock_prices WHERE ticker=?) THEN date  END) as latest_date,
             MAX(high)  as week52_high,
             MIN(low)   as week52_low,
             AVG(close) as avg_close,
             MAX(volume) as max_volume
           FROM stock_prices
           WHERE ticker=? AND date >= date('now','-365 days')""",
        (ticker, ticker, ticker),
    ).fetchone()
    return dict(row) if row and row["latest_close"] else None


# ── Events ────────────────────────────────────────────────────────────────────

def insert_event(event: dict) -> int:
    conn = _get_conn()
    cursor = conn.execute(
        """INSERT INTO events(company,ticker,event_date,event_type,title,description,impact_score,source)
           VALUES(:company,:ticker,:event_date,:event_type,:title,:description,:impact_score,:source)""",
        event,
    )
    conn.commit()
    return cursor.lastrowid


def get_events(company: str, limit: int = 20) -> list[dict]:
    rows = _get_conn().execute(
        "SELECT * FROM events WHERE company=? ORDER BY event_date DESC LIMIT ?",
        (company, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_events_by_type(event_type: str, limit: int = 20) -> list[dict]:
    rows = _get_conn().execute(
        "SELECT * FROM events WHERE event_type=? ORDER BY event_date DESC LIMIT ?",
        (event_type, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def search_similar_events(event_type: str, company: str = None, limit: int = 5) -> list[dict]:
    """Find historical events of the same type — used for analogical forecasting."""
    if company:
        rows = _get_conn().execute(
            """SELECT * FROM events
               WHERE event_type=? AND company != ?
               ORDER BY event_date DESC LIMIT ?""",
            (event_type, company, limit),
        ).fetchall()
    else:
        rows = _get_conn().execute(
            "SELECT * FROM events WHERE event_type=? ORDER BY event_date DESC LIMIT ?",
            (event_type, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Company registry ──────────────────────────────────────────────────────────

def register_company(company: str, ticker: str, scrip_code: str = "") -> None:
    conn = _get_conn()
    conn.execute(
        """INSERT INTO company_registry(company, ticker, scrip_code)
           VALUES(?,?,?)
           ON CONFLICT(company) DO UPDATE SET
             ticker=excluded.ticker, scrip_code=excluded.scrip_code""",
        (company, ticker, scrip_code),
    )
    conn.commit()


def update_company_status(company: str, status: str, error_msg: str = "") -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    if status == "ready":
        conn.execute(
            "UPDATE company_registry SET status=?, loaded_at=?, error_msg=? WHERE company=?",
            (status, now, error_msg, company),
        )
    else:
        conn.execute(
            "UPDATE company_registry SET status=?, error_msg=? WHERE company=?",
            (status, error_msg, company),
        )
    conn.commit()


def update_docs_synced(company: str, doc_count: int) -> None:
    from datetime import datetime, timezone
    conn = _get_conn()
    conn.execute(
        "UPDATE company_registry SET docs_synced_at=?, doc_count=? WHERE company=?",
        (datetime.now(timezone.utc).isoformat(), doc_count, company),
    )
    conn.commit()


def get_company_registry(company: str) -> Optional[dict]:
    row = _get_conn().execute(
        "SELECT * FROM company_registry WHERE company=?", (company,)
    ).fetchone()
    return dict(row) if row else None


def get_registry_by_ticker(ticker: str) -> Optional[dict]:
    row = _get_conn().execute(
        "SELECT * FROM company_registry WHERE ticker=?", (ticker,)
    ).fetchone()
    return dict(row) if row else None


def list_registered_companies() -> list[dict]:
    rows = _get_conn().execute(
        "SELECT * FROM company_registry ORDER BY loaded_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


# ── Context builder ────────────────────────────────────────────────────────────

def build_financial_context(company: str) -> str:
    """Build a concise financial summary string to inject into LLM context."""
    fins = get_financials(company, years=5)
    ticker = get_ticker(company)
    stock_summary = get_stock_summary(ticker) if ticker else None
    events = get_events(company, limit=10)

    if not fins and not events:
        return ""

    lines = [f"\n=== STRUCTURED FINANCIAL DATA: {company.upper()} ==="]

    # Annual financials table
    if fins:
        lines.append("\nANNUAL FINANCIALS (in Crores INR or as reported):")
        lines.append(f"{'Year':<8} {'Revenue':>14} {'Net Income':>12} {'EBITDA':>12} {'EPS':>8} {'Total Assets':>14} {'Net Margin':>11}")
        lines.append("-" * 82)
        for f in fins:
            rev  = f"{f['revenue']/1e7:.0f}Cr"  if f.get("revenue")      else "N/A"
            ni   = f"{f['net_income']/1e7:.0f}Cr" if f.get("net_income")  else "N/A"
            ebit = f"{f['ebitda']/1e7:.0f}Cr"   if f.get("ebitda")       else "N/A"
            eps  = f"{f['eps']:.2f}"             if f.get("eps")          else "N/A"
            ta   = f"{f['total_assets']/1e7:.0f}Cr" if f.get("total_assets") else "N/A"
            nm   = f"{f['net_margin']:.1f}%"     if f.get("net_margin")   else "N/A"
            lines.append(f"{f['fiscal_year']:<8} {rev:>14} {ni:>12} {ebit:>12} {eps:>8} {ta:>14} {nm:>11}")

    # Stock summary
    if stock_summary and stock_summary.get("latest_close"):
        lines.append(f"\nSTOCK ({ticker}):")
        lines.append(f"  Latest close : ₹{stock_summary['latest_close']:.2f} ({stock_summary['latest_date']})")
        lines.append(f"  52-week range: ₹{stock_summary['week52_low']:.2f} – ₹{stock_summary['week52_high']:.2f}")

    # Recent events
    if events:
        lines.append("\nKEY EVENTS (most recent first):")
        for e in events[:8]:
            impact = f"[impact: {e['impact_score']:+.1f}]" if e.get("impact_score") else ""
            lines.append(f"  {e['event_date']}  {e['event_type']:<18} {e['title']} {impact}")

    lines.append("=== END STRUCTURED DATA ===\n")
    return "\n".join(lines)
