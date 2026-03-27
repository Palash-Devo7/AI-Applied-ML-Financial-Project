# QuantCortex — AI Research Platform for Indian Equities

> **Live at [quantcortex.in](https://quantcortex.in)**

An end-to-end AI-powered financial research platform built specifically for BSE-listed Indian companies. Search any BSE ticker — the system auto-fetches filings, financials, and announcements, then lets you ask natural language questions or run multi-agent event forecasts. No manual uploads needed.

---

## Demo

**[quantcortex.in](https://quantcortex.in)** — try 3 free queries with no sign-up required, or register for 10 credit points/day

Try: Go to [quantcortex.in/preview](https://quantcortex.in/preview) → type `TATASTEEL` → ask a question → see full AI analysis instantly

About: [quantcortex.in/about](https://quantcortex.in/about) — the platform and the team behind it

---

## What Makes This Different

| Feature | QuantCortex | Generic RAG / ChatGPT |
|---------|------------|----------------------|
| BSE-specific data pipeline | Auto-fetches filings from BSE India | Manual copy-paste |
| Finance-tuned embeddings | FinBERT (domain-specific, 768-dim) | General-purpose embeddings |
| Hybrid retrieval | Vector + BM25 + RRF fusion | Vector-only |
| Multi-agent forecasting | Bull + Bear + Macro → Synthesis | Single LLM response |
| Structured financial context | SQLite financials injected into RAG context | No structured data |
| India-specific | BSE scrip codes, INR, Indian fiscal year | US-market focused |

---

## Architecture

### Query Flow
```
User question
  → MCPService: classify query type (RISK / REVENUE / MACRO / COMPARATIVE / HISTORICAL)
  → MCPService: build ChromaDB metadata filter (company, year, report type)
  → SQLite: fetch structured financials → prepend to context
  → EmbeddingService: FinBERT CLS embed (768-dim, L2-normalized)
  → RetrievalService: ChromaDB vector search + BM25 + Reciprocal Rank Fusion (α=0.7)
  → MCPService: assemble context (dedup, sort by score, cite sources)
  → GenerationService: LLM answer (streaming SSE)
```

### Company Auto-Load Flow
```
POST /companies/load {"ticker": "TATASTEEL"}
  → Background task: CompanyLoader
    → BSEProvider: ticker → scrip_code (BSE India API)
    → BSEProvider: fetch financials → SQLite upsert
    → BSEProvider: fetch live price → stock_prices upsert
    → BSEProvider: get announcements → filter relevant PDFs
    → BSEProvider: download PDFs (with session warmup for Akamai bypass)
    → IngestionService: pypdf → pdfplumber → Tesseract OCR (3-layer fallback)
    → Chunker: section-aware → recursive char split (480 tok / 64 overlap)
    → EmbeddingService: FinBERT embed in batches
    → ChromaDB: upsert with rich metadata
    → company_registry: status = ready
```

### Multi-Agent Forecast Flow
```
POST /forecast/event {"company": "Tata Steel", "event_type": "capacity_expansion", ...}
  → asyncio.gather (parallel):
      Bull Agent    → optimistic analysis with key catalysts
      Bear Agent    → risk analysis with downside scenarios
      Macro Agent   → sector + macro environment assessment
  → Synthesizer Agent → base / bull / bear case + key risks + key catalysts
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Embeddings** | ProsusAI/FinBERT (CLS pooler, dim=768) | Finance-domain pre-trained, outperforms general embeddings on financial text |
| **LLM** | Groq LLaMA-3.3-70B (default) · Claude · DeepSeek | Switchable via env var — no vendor lock-in |
| **Vector DB** | ChromaDB (persistent, cosine similarity) | Metadata filtering for company/year/report type |
| **Hybrid Retrieval** | ChromaDB + BM25 + Reciprocal Rank Fusion | Combines semantic and keyword search, significantly improves recall |
| **Structured DB** | SQLite — financials, stock prices, events, company registry | Fast structured financial context injection |
| **Market Data** | BSE India (`bse` package) + yfinance | BSE filings auto-ingest + historical prices |
| **Backend** | FastAPI (async) + Uvicorn | High-performance async API |
| **Frontend** | Next.js 15 (App Router) + Tailwind v4 + shadcn/ui | Modern React, streaming SSE support |
| **Auth** | JWT (python-jose) + bcrypt (passlib) | Stateless auth, secure password hashing |
| **Rate Limiting** | slowapi (per-IP) | Abuse prevention |
| **OCR** | pypdf → pdfplumber → Tesseract (3-layer fallback) | Handles scanned PDFs, image-heavy annual reports |
| **Monitoring** | structlog (JSON) + Prometheus + Grafana | Production observability |
| **Deployment** | Vercel (frontend) + Hostinger VPS + Nginx + Certbot | Full production stack |

---

## Features

### Core RAG
- Hybrid retrieval: FinBERT vector search + BM25 keyword + RRF fusion
- Query classification — routes to appropriate retrieval strategy
- Structured financial data injection from SQLite into RAG context
- Streaming responses via Server-Sent Events (SSE)
- Source citations with page numbers, section types, relevance scores

### BSE Auto-Ingest
- Type a ticker → system resolves BSE scrip code automatically
- Fetches Annual Reports, Quarterly Results, Board Meeting PDFs from BSE
- 3-layer OCR fallback handles any PDF quality
- Background processing with real-time status polling

### Multi-Agent Forecasting
- Three analyst agents run in parallel (asyncio.gather)
- Bull Agent, Bear Agent, Macro Agent each produce independent analysis
- Synthesizer combines into structured forecast with base/bull/bear cases
- Returns key risks, key catalysts, confidence assessment

### Guest Preview
- `/preview` page — no login required, full-capability AI responses
- 3 lifetime credits per guest tracked in isolated `guest_sessions` SQLite table
- Guest identity: `SHA256(IP + localStorage_token)[:32]` — no PII stored
- slowapi `3/day` per IP as hard server-side abuse cap
- After 3 credits: signup nudge card with "Create free account" → `/auth/login`

### Security & Auth
- JWT-based authentication with bcrypt password hashing
- Email verification via Resend (unverified users cannot consume credits)
- Admin role with unlimited access + dashboard
- CORS restricted to known origins
- Security headers (X-Content-Type-Options, X-Frame-Options, HSTS in production)

### Rate Limiting — Three Layers

**Layer 1 — slowapi (per-IP, before auth):**

| Endpoint | Limit |
|---|---|
| `POST /query` or `/query/stream` | 5 req/min |
| `POST /forecast/event` | 10 req/min |
| `POST /companies/load` | 10 req/min |
| `POST /documents/upload` | 5 req/min |

**Layer 2 — Credit system (per-user, per-day):**
- 10 credits/day for trial users, resets midnight UTC. Admin: unlimited.
- `/query` costs 1 credit, `/forecast/event` and `/documents/upload` cost 2.
- Credits deducted only on success — failed requests are free.
- HTTP 429: `{ error: "daily_credit_limit_reached", used, limit }`

**Layer 3 — Groq API quota protection:**
- Groq free tier: 30 RPM shared across all users.
- `RateLimitError` caught explicitly in `GroqBackend.generate()`, `raw_generate()`, and `stream_generate()` before the tenacity retry loop fires (retrying on rate limit burns more quota).
- Returns HTTP 429 with a user-facing message. At 5 req/min per user, the system handles ~6 concurrent active users within Groq's 30 RPM cap.

### Production
- Deployed on Hostinger VPS (Ubuntu 24.04) + Nginx reverse proxy
- SSL via Let's Encrypt (auto-renews)
- systemd service with auto-restart on crash
- UFW firewall (SSH + HTTP/HTTPS only)
- Frontend on Vercel with auto-deploy from GitHub

---

## API Reference

All endpoints require `Authorization: Bearer <token>` (except `/health` and `/auth/*`).

### Auth
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/register` | Create trial account → JWT + API key |
| `POST` | `/auth/login` | Login → JWT + API key |
| `GET` | `/auth/me` | User info + credit summary |

### Query
| Method | Path | Credits | Description |
|--------|------|---------|-------------|
| `POST` | `/query` | 1 | Financial question → answer + sources |
| `POST` | `/query/stream` | 1 | Same but token-by-token SSE streaming |

### Companies
| Method | Path | Credits | Description |
|--------|------|---------|-------------|
| `POST` | `/companies/load` | 1 | Auto-fetch + ingest BSE ticker (background) |
| `GET` | `/companies/status/{ticker}` | 0 | Load status: pending / loading / ready |
| `GET` | `/companies/search?q=` | 0 | Search BSE companies by name or ticker |
| `GET` | `/companies/list` | 0 | All registered companies |

### Forecast
| Method | Path | Credits | Description |
|--------|------|---------|-------------|
| `POST` | `/forecast/event` | 2 | Multi-agent event impact forecast |

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/market/financials/{company}` | Annual financials history |
| `GET` | `/market/stock/{ticker}/summary` | 52-week range + latest close |

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- Tesseract OCR (`brew install tesseract` / `apt install tesseract-ocr`)

### Backend
```bash
git clone https://github.com/YOUR_USERNAME/AI-Applied-ML-Financial-Project
cd AI-Applied-ML-Financial-Project

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env — set GROQ_API_KEY at minimum

python -m uvicorn app.main:app --reload --port 8080
# API docs at http://localhost:8080/docs
```

### Frontend
```bash
cd finance-ui
npm install

# Create finance-ui/.env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8080" > .env.local

npm run dev
# Open http://localhost:3000
```

### Quick API test
```bash
# Register
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Use the token from above
TOKEN="your_token_here"

# Load a company
curl -X POST http://localhost:8080/companies/load \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ticker": "TATASTEEL"}'

# Ask a question
curl -X POST http://localhost:8080/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What was Tata Steel revenue in FY2024?", "company": "Tata Steel"}'
```

---

## Project Structure

```
finance-rag/
├── app/
│   ├── main.py                    # FastAPI factory, lifespan, middleware
│   ├── config.py                  # Pydantic BaseSettings (.env)
│   ├── dependencies.py            # @lru_cache singletons
│   ├── core/
│   │   ├── auth_deps.py           # get_current_user, require_credits, consume_after_success
│   │   ├── security.py            # JWT create/decode, bcrypt hash/verify, API key gen
│   │   ├── limiter.py             # Shared slowapi Limiter instance
│   │   ├── chunker.py             # Section-aware + recursive chunking
│   │   ├── document_parser.py     # 3-layer OCR: pypdf → pdfplumber → Tesseract
│   │   ├── metadata_extractor.py  # Regex: company, year, quarter, section_type
│   │   ├── vector_store.py        # ChromaDB async-safe wrapper
│   │   └── prompts.py             # Structured markdown prompt templates
│   ├── data/
│   │   ├── financial_db.py        # SQLite: financials, stock_prices, company_registry
│   │   └── auth_db.py             # SQLite: users, daily_credits, credit_log
│   ├── routers/
│   │   ├── auth.py                # POST /auth/register, /auth/login, GET /auth/me
│   │   ├── query.py               # POST /query + /query/stream (SSE)
│   │   ├── forecast.py            # POST /forecast/event
│   │   ├── companies.py           # Company auto-load endpoints
│   │   ├── ingestion.py           # POST /documents/upload
│   │   ├── market_data.py         # Market data endpoints
│   │   ├── collections.py         # ChromaDB collection management
│   │   └── health.py              # GET /health
│   ├── services/
│   │   ├── embedding_service.py   # FinBERT async (ThreadPoolExecutor, CPU-bound)
│   │   ├── retrieval_service.py   # Hybrid vector + BM25 + RRF
│   │   ├── generation_service.py  # LLM backends (Protocol pattern — Groq/DeepSeek/Claude)
│   │   ├── ingestion_service.py   # parse → chunk → embed → store pipeline
│   │   ├── query_service.py       # Full query pipeline
│   │   ├── mcp_service.py         # Query classification + context assembly
│   │   ├── forecast_service.py    # Multi-agent forecasting engine
│   │   ├── company_loader.py      # BSE auto-ingest orchestrator
│   │   └── providers/
│   │       ├── base.py            # MarketDataProvider Protocol
│   │       └── bse_provider.py    # BSE India implementation
│   ├── models/                    # Pydantic request/response models
│   └── monitoring/                # structlog + Prometheus middleware
├── finance-ui/                    # Next.js 15 frontend
│   ├── app/
│   │   ├── auth/login/page.tsx    # Login + Register (tabbed)
│   │   ├── company/[ticker]/      # Company research page
│   │   └── page.tsx               # Home + search
│   ├── components/
│   │   ├── header.tsx             # Credit counter + logout
│   │   ├── auth-guard.tsx         # Route protection
│   │   ├── search-bar.tsx         # Debounced BSE company search
│   │   ├── ConditionalHeader.tsx  # Hides header on homepage
│   │   ├── feedback-modal.tsx     # Post-interaction feedback (30s delay)
│   │   └── home/                  # Homepage sections (Hero, DotCanvas, Features…)
│   └── lib/
│       ├── api.ts                 # API client (Bearer token, SSE streaming)
│       └── auth.tsx               # Auth context + sessionStorage persistence
├── monitoring/                    # Prometheus + Grafana config
├── docker/                        # Dockerfile + docker-compose
└── requirements.txt
```

---

## Roadmap

### Completed
- [x] Core RAG pipeline — FinBERT + ChromaDB + BM25/RRF hybrid retrieval
- [x] BSE auto-ingest — ticker → scrip code → filings → PDFs → vector store
- [x] Historical data layer — SQLite financials, stock prices, events
- [x] Multi-agent forecasting — Bull/Bear/Macro parallel agents + Synthesizer
- [x] Next.js frontend — dark UI, streaming chat, forecast UI, financial charts
- [x] JWT auth + credit system + rate limiting
- [x] Production deployment — quantcortex.in (Vercel + VPS + SSL)
- [x] Email verification with Resend + BroadcastChannel cross-tab sync
- [x] Full homepage redesign — landing page with animated DotCanvas, feature sections, roadmap
- [x] Progressive load UX — real-time step messages, early-ready signal, background indexing banner
- [x] Live stock pricing — BSE price fetched on every summary request, falls back to cache
- [x] Feedback modal — 30s delayed trigger, 7-day cooldown

### In Progress / Planned
- [ ] **Phase C — GraphRAG:** NetworkX company relationship graph (suppliers, competitors, sectors) — enables impact propagation analysis
- [ ] **Phase D — Market Impact Propagation:** Track how news/events ripple through connected companies and sectors
- [ ] **Phase E — ML Models:** Earnings surprise predictor, volatility forecaster, sentiment → price impact model trained on BSE historical data
- [ ] **Phase F — Brokerage Integration:** Zerodha Kite Connect for portfolio-aware research

---

## Key Design Decisions

**Why FinBERT over OpenAI embeddings?**
Financial text has domain-specific vocabulary (EBITDA, scrip codes, BSE-specific terms). FinBERT was pre-trained on financial corpora and produces significantly better semantic similarity for financial document retrieval.

**Why hybrid retrieval (vector + BM25 + RRF)?**
Pure vector search misses exact term matches (ticker symbols, specific financial ratios). Pure BM25 misses semantic similarity. RRF fusion gets the best of both — tested on financial Q&A, it consistently outperforms either alone.

**Why SQLite for structured data?**
Financial statements have structured, predictable schemas. Putting them in SQLite and injecting them directly into the LLM context is more reliable than embedding them — the LLM gets exact numbers, not approximations from chunked text.

**Why the Protocol pattern for LLM backends?**
`GenerationService` depends on a `ModelBackend` Protocol, not a concrete class. Switching between Groq, DeepSeek, and Claude requires zero changes to the query pipeline — just an env var.

---

## License

MIT
