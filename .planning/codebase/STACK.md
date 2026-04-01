# Technology Stack

**Analysis Date:** 2026-04-01

## Languages

**Primary:**
- Python 3.11 — all backend application code (`app/`, `ui/`)
- TypeScript 5.x — Next.js frontend (`finance-ui/`)

**Secondary:**
- SQL — SQLite schema in `app/data/financial_db.py` and `app/data/auth_db.py`

## Runtime

**Backend Environment:**
- Python 3.11 (pinned in `docker/Dockerfile` via `python:3.11-slim`)
- Uvicorn ASGI server with standard extras: `uvicorn[standard]==0.34.0`

**Frontend Environment:**
- Node.js (version managed by Next.js 16.2.0 requirement)

**Package Managers:**
- Backend: `pip` with `requirements.txt` and `requirements-dev.txt`
- Frontend: npm (lockfile: `finance-ui/package-lock.json`)

## Frameworks

**Backend Web:**
- FastAPI `0.115.6` — async REST API, dependency injection, OpenAPI docs
- Pydantic v2 `2.10.6` — request/response validation
- `pydantic-settings 2.7.1` — `.env` configuration management (`app/config.py`)

**Frontend:**
- Next.js `16.2.0` — React app server (`finance-ui/`)
- React `19.2.4` — UI rendering
- Tailwind CSS v4 — utility-first styling
- shadcn `4.0.8` — component library built on Base UI
- Recharts `3.8.0` — financial data charts

**Alternative UI (Legacy/Dev):**
- Streamlit `>=1.40.0` — thin client at `ui/app.py`, calls FastAPI backend directly

**Testing:**
- pytest `8.3.4` with `pytest-asyncio 0.25.2` and `pytest-cov 6.0.0`
- Config: `pytest.ini`

**Linting / Formatting:**
- Ruff `0.9.1` — linting and formatting (replaces flake8 + black)
- mypy `1.14.1` — static type checking

## Key Dependencies

**Machine Learning / Embeddings:**
- `transformers==4.48.0` — HuggingFace Transformers (loads ProsusAI/finbert)
- `torch==2.5.1` — CPU-only build; override with `torch==2.5.1+cu121` for GPU
- `numpy==1.26.4` — numerical operations

**LLM Clients:**
- `openai==1.82.0` — used by both DeepSeek and Groq backends (OpenAI-compatible API)
- `anthropic==0.43.0` — used only when `LLM_PROVIDER=claude`
- `groq>=0.9.0` — Groq SDK (currently loaded via openai-compatible client)

**Vector Database:**
- `chromadb==1.5.5` — persistent vector store at `./data/chroma_db`

**Retrieval:**
- `rank-bm25==0.2.2` — BM25 keyword retrieval for hybrid search
- `langchain-text-splitters==0.3.4` — recursive character text splitting
- `tiktoken==0.8.0` — token counting for chunking and context limits

**PDF Parsing (3-layer fallback):**
- `pypdf==5.1.0` — primary parser
- `pdfplumber==0.11.4` — secondary parser
- `pymupdf>=1.24.0` — OCR fallback (renders pages as images)
- `pytesseract>=0.3.10` — Tesseract wrapper (requires Tesseract binary installed)
- `pillow>=10.0.0` — image handling for OCR

**Graph:**
- `networkx>=3.0` — company relationship graph (Phase C)

**Market Data:**
- `yfinance>=0.2.54` — Yahoo Finance historical prices/financials
- `bse>=3.2.0` — unofficial BSE India Python client

**Auth / Security:**
- `python-jose[cryptography]==3.3.0` — JWT encoding/decoding
- `passlib[bcrypt]==1.7.4` + `bcrypt==4.0.1` — password hashing
- `slowapi==0.1.9` — rate limiting middleware for FastAPI

**HTTP / Async Utilities:**
- `httpx==0.28.1` — async HTTP client
- `tenacity==9.0.0` — retry logic (LLM calls use exponential backoff, 3 attempts)
- `python-ulid==3.1.0` — ULID generation for user IDs

**Monitoring:**
- `structlog==24.4.0` — structured JSON logging
- `prometheus-client==0.21.1` — metrics exposition
- `prometheus-fastapi-instrumentator==7.0.0` — auto-instrument FastAPI endpoints

**Email:**
- `resend==2.10.0` — transactional email via Resend API

**Frontend Key Libraries:**
- `lucide-react ^0.577.0` — icon set
- `react-markdown ^10.1.0` + `remark-gfm ^4.0.1` — render LLM markdown responses
- `@vercel/analytics ^2.0.1` — Vercel analytics tracking
- `class-variance-authority ^0.7.1` + `clsx ^2.1.1` — conditional class composition

## Configuration

**Backend:**
- `app/config.py` — Pydantic `BaseSettings` class reads from `.env` (case-insensitive)
- `.env.example` present; `.env` must be created locally
- All settings accessible via `get_settings()` singleton (`@lru_cache`)

**Frontend:**
- `finance-ui/next.config.ts` — minimal Next.js config (no custom settings currently)
- `finance-ui/.env.local` — frontend environment overrides

**Build:**
- Backend: no build step; run directly with `uvicorn app.main:app`
- Frontend: `next build` / `next dev`
- Docker: multi-stage build in `docker/Dockerfile` (builder + runtime stages)

## Platform Requirements

**Development:**
- Python 3.11+
- Tesseract OCR binary (for PDF fallback parsing)
- poppler-utils (for PDF rendering in Docker)

**Production:**
- Docker via `docker/docker-compose.yml`
- Prometheus + Grafana monitoring stack included in compose
- Backend exposed on port `8000`, frontend on port `3000`
- FinBERT model downloaded from HuggingFace at startup (or pre-baked into image)

---

*Stack analysis: 2026-04-01*
