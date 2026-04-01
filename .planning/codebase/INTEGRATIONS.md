# External Integrations

**Analysis Date:** 2026-04-01

## LLM Providers

All three backends implement the `ModelBackend` Protocol in `app/services/generation_service.py`.
The active backend is selected at startup via the `LLM_PROVIDER` environment variable.

**Groq (default):**
- SDK: `openai.AsyncOpenAI` pointed at `https://api.groq.com/openai/v1`
- Default model: `llama-3.3-70b-versatile`
- Auth env var: `GROQ_API_KEY`
- Model env var: `GROQ_MODEL`
- Streaming: supported via `stream_generate()` async generator

**DeepSeek (optional):**
- SDK: `openai.AsyncOpenAI` pointed at `https://api.deepseek.com`
- Default model: `deepseek-chat`
- Auth env var: `DEEPSEEK_API_KEY`
- Model env var: `DEEPSEEK_MODEL`
- Activate: set `LLM_PROVIDER=deepseek`
- Streaming: supported

**Claude / Anthropic (optional):**
- SDK: `anthropic.AsyncAnthropic` (native SDK, not OpenAI-compatible wrapper)
- Default model: `claude-sonnet-4-6`
- Auth env var: `ANTHROPIC_API_KEY`
- Model env var: `CLAUDE_MODEL`
- Activate: set `LLM_PROVIDER=claude`
- Streaming: not implemented (falls back to full response then single yield)
- Package: `anthropic==0.43.0` (only imported if `LLM_PROVIDER=claude`)

**Retry policy (all backends):**
- tenacity: exponential backoff, min=2s max=30s, 3 attempts, re-raises on failure
- Rate limit errors from Groq/Claude raise HTTP 429 with user-facing message

**Token metering:**
- Prometheus counters `LLM_INPUT_TOKENS_TOTAL` and `LLM_OUTPUT_TOKENS_TOTAL` labeled by model
- Latency histogram `LLM_LATENCY_SECONDS` labeled by model
- Metrics emitted in `app/monitoring/metrics.py`

## Market Data

**BSE India (`bse>=3.2.0`):**
- Unofficial Python package wrapping BSE's undocumented APIs
- Implementation: `app/services/providers/bse_provider.py`
- Key operations:
  - `getScripCode(ticker)` — resolve BSE scrip code from ticker symbol
  - `listSecurities(group=...)` — bulk securities list (loaded into in-memory cache at startup)
  - `resultsSnapshot(scrip_code)` — quarterly + annual financials
  - `quote(scrip_code)` — live price
  - `announcements(scripcode, from_date, to_date)` — corporate filings list
- PDF download: direct HTTP GET to `https://www.bseindia.com/xml-data/corpfiling/AttachLive/{filename}`
- Auth: none (public endpoint, but protected by Akamai Bot Manager)
- Session warmup required: `GET https://www.bseindia.com/` must be called first to set cookies;
  cold requests are blocked. Done in `BSEProvider._warmup()` and before every PDF download.
- Known bug: `bse.lookup()` throws `IndexError` — always use `bse.getScripCode()` instead

**Yahoo Finance (`yfinance>=0.2.54`):**
- Implementation: `app/services/market_data_service.py`
- Used for: historical stock prices, annual/quarterly income statements, balance sheet, cash flow
- No API key required
- Ticker format: `TATASTEEL.NS` (NSE) or `TATASTEEL.BO` (BSE)
- ISIN-to-ticker resolution: `GET https://query2.finance.yahoo.com/v1/finance/search?q={isin}`
  via `BSEProvider.resolve_yfinance_ticker()` — no auth required
- Always run sync `yfinance` calls in `asyncio.to_thread()` (blocking I/O)

## Embedding Model

**ProsusAI/finbert (HuggingFace):**
- Implementation: `app/services/embedding_service.py`
- Downloaded from HuggingFace Hub at startup (or pre-baked into Docker image)
- Strategy: CLS token pooler_output, L2-normalized, dimension=768
- Env vars: `EMBEDDING_MODEL`, `EMBEDDING_STRATEGY`, `EMBEDDING_BATCH_SIZE`, `EMBEDDING_DEVICE`
- Always run in `ThreadPoolExecutor(max_workers=1)` — CPU-bound, not safe for async context
- No external API call at query time; fully local inference

## Data Storage

**ChromaDB (Vector Database):**
- Package: `chromadb==1.5.5`
- Persistence: local filesystem at `./data/chroma_db` (configurable via `CHROMA_PERSIST_DIR`)
- Collection: `finance_docs` (configurable via `CHROMA_COLLECTION_NAME`)
- Distance: cosine similarity (`CHROMA_DISTANCE_FUNCTION=cosine`)
- Wrapper: `app/core/vector_store.py`
- Threading: ChromaDB client is sync-only; all calls must be wrapped in `run_in_threadpool()`
- Concurrent writes protected by `asyncio.Lock` in vector_store wrapper

**SQLite (Structured Data — two databases):**

`data/financial_data.db` — financial and market data:
- Managed by: `app/data/financial_db.py`
- Tables: `company_financials`, `stock_prices`, `events`, `ticker_map`, `company_registry`, `graph_edges`
- Connection: thread-local via `threading.local()`, WAL mode enabled
- No external connection; embedded file-based DB

`data/auth.db` — user authentication and credits:
- Managed by: `app/data/auth_db.py`
- Tables: `users`, `verification_tokens`, credit tracking tables
- Connection: direct `sqlite3.connect()` with WAL + foreign keys enabled
- User IDs: ULID format via `python-ulid`

## Authentication & Identity

**JWT-based auth:**
- Library: `python-jose[cryptography]==3.3.0`
- Secret env var: `JWT_SECRET` (default placeholder — must override in production)
- Token expiry: `JWT_EXPIRE_HOURS=24` (default)
- Password hashing: `passlib[bcrypt]` + `bcrypt==4.0.1`

**User roles:** `guest`, `trial`, `admin`
- Credit system: costs per endpoint defined in `app/data/auth_db.py` (`CREDIT_COSTS` dict)
- Trial users: 10 credits/day; guest sessions: 3 lifetime credits
- Admin auto-created at startup if `ADMIN_EMAIL` + `ADMIN_PASSWORD` set and user not found

**API key auth:** generated via `app/core/security.generate_api_key()`, stored per user

## Email

**Resend:**
- Package: `resend==2.10.0`
- Auth env var: `RESEND_API_KEY`
- From address: `EMAIL_FROM` (default: `noreply@quantcortex.in`)
- Used for: email verification tokens, transactional notifications
- Frontend URL for links: `FRONTEND_URL` (default: `https://quantcortex.in`)

## Monitoring & Observability

**Prometheus:**
- Package: `prometheus-client==0.21.1` + `prometheus-fastapi-instrumentator==7.0.0`
- Enabled via: `PROMETHEUS_ENABLED=true`
- Metrics prefix: `METRICS_PREFIX=finance_rag`
- Auto-instruments all FastAPI routes; custom LLM token and latency metrics in `app/monitoring/metrics.py`

**Grafana:**
- Configured in `docker/docker-compose.yml` (docker-compose only)
- Credentials: `GRAFANA_USER` / `GRAFANA_PASSWORD` env vars
- Prometheus config: `docker/prometheus.yml`

**Structured Logging:**
- Package: `structlog==24.4.0`
- Format: JSON structured logs
- Level: `LOG_LEVEL` env var (default: `INFO`)
- Configured in `app/monitoring/logger.py`

## Real-Time / Streaming

**Server-Sent Events (SSE):**
- Endpoint: `POST /query/stream`
- Implementation: FastAPI `StreamingResponse` in `app/routers/query.py`
- Event sequence: `meta` event (sources + query_type) → repeated `token` events → `done` event
- All three LLM backends support streaming; Claude backend falls back to single yield

## CORS

- Allowed origins: comma-separated list in `ALLOWED_ORIGINS` env var (default: `http://localhost:3000`)
- Methods: `GET`, `POST`, `DELETE`, `OPTIONS`
- Headers: `Authorization`, `Content-Type`
- Credentials: disabled (`allow_credentials=False`)

## Rate Limiting

- Library: `slowapi==0.1.9` (wraps `limits` library)
- Limiter singleton: `app/core/limiter.py`
- Per-endpoint rates defined in `app/config.py`:
  - `RATE_LIMIT_QUERY=5/minute` (applies to `/query` and `/query/stream`)
  - `RATE_LIMIT_UPLOAD=5/minute`
  - `RATE_LIMIT_GLOBAL=60/minute`

## Environment Variables Summary

| Variable | Purpose | Default |
|---|---|---|
| `LLM_PROVIDER` | Active LLM backend | `groq` |
| `GROQ_API_KEY` | Groq authentication | — |
| `DEEPSEEK_API_KEY` | DeepSeek authentication | — |
| `ANTHROPIC_API_KEY` | Anthropic/Claude authentication | — |
| `JWT_SECRET` | JWT signing secret | insecure placeholder |
| `ADMIN_EMAIL` | Auto-created admin email | `admin@financerag.com` |
| `ADMIN_PASSWORD` | Auto-created admin password | — (empty disables) |
| `RESEND_API_KEY` | Resend email service | — |
| `CHROMA_PERSIST_DIR` | ChromaDB storage path | `./data/chroma_db` |
| `ALLOWED_ORIGINS` | CORS allowed origins | `http://localhost:3000` |
| `PROMETHEUS_ENABLED` | Enable metrics endpoint | `true` |
| `EMBEDDING_DEVICE` | CPU or CUDA for FinBERT | `cpu` |

Full reference: `app/config.py` and `.env.example`

---

*Integration audit: 2026-04-01*
