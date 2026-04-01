# Codebase Structure

**Analysis Date:** 2026-04-01

## Directory Layout

```
finance-rag/
├── app/                          # FastAPI backend application
│   ├── main.py                   # App factory, lifespan, middleware, router registration
│   ├── config.py                 # Pydantic BaseSettings (reads .env)
│   ├── dependencies.py           # @lru_cache singletons — the only place services are created
│   ├── core/                     # Infrastructure primitives (no business logic)
│   │   ├── auth_deps.py          # FastAPI Depends: get_current_user, require_credits
│   │   ├── chunker.py            # Section-aware → recursive char split (512 tok / 64 overlap)
│   │   ├── document_parser.py    # pypdf → pdfplumber → Tesseract OCR (3-layer fallback)
│   │   ├── email.py              # Verification/welcome email sending
│   │   ├── limiter.py            # SlowAPI rate limiter instance
│   │   ├── metadata_extractor.py # Regex: company, year, quarter, section_type from text
│   │   ├── prompts.py            # Finance system prompt + user prompt templates
│   │   ├── security.py           # JWT (HS256), password hashing, API key generation
│   │   └── vector_store.py       # Async-safe ChromaDB wrapper (asyncio.Lock for writes)
│   ├── data/                     # SQLite persistence layer
│   │   ├── auth_db.py            # Users, verification tokens, credits, guest sessions, feedback
│   │   └── financial_db.py       # Financials, stock_prices, events, ticker_map, graph tables
│   ├── graph/                    # GraphRAG layer
│   │   ├── graph_store.py        # NetworkX DiGraph ↔ SQLite bridge; seeding + loading
│   │   ├── graph_builder.py      # Graph construction helpers
│   │   ├── graph_retriever.py    # BFS neighbor traversal; builds context string for LLM
│   │   └── propagation_engine.py # Pure weighted BFS from trigger ticker; no I/O
│   ├── models/                   # Pydantic schemas (request/response)
│   │   ├── documents.py          # Ingestion request/response
│   │   ├── forecast.py           # ForecastRequest, ForecastResponse, AgentView
│   │   ├── impact.py             # PropagationRequest, PropagationResponse, AffectedNode
│   │   ├── monitoring.py         # Health check response
│   │   └── queries.py            # QueryRequest, QueryResponse, TokenUsageDetail
│   ├── monitoring/               # Observability
│   │   ├── logger.py             # structlog JSON config
│   │   ├── metrics.py            # Prometheus counters + histograms
│   │   └── middleware.py         # RequestLoggingMiddleware (per-request structlog)
│   ├── routers/                  # FastAPI routers (one file per resource)
│   │   ├── auth.py               # POST /auth/register|login, GET /auth/me|verify|admin/*
│   │   ├── collections.py        # GET/DELETE /collections (ChromaDB collection mgmt)
│   │   ├── companies.py          # POST /companies/load, GET /companies/status|list|search
│   │   ├── feedback.py           # POST /feedback
│   │   ├── forecast.py           # POST /forecast/event, POST /forecast/preview (guest)
│   │   ├── graph.py              # GET /graph/{ticker}, POST /graph/propagate|seed
│   │   ├── health.py             # GET /health
│   │   ├── ingestion.py          # POST /documents/upload (202 + background OCR)
│   │   ├── market_data.py        # POST /market/fetch/sync, GET /market/financials|stock
│   │   ├── preview.py            # Guest-mode preview endpoints (no auth, 3-credit limit)
│   │   └── query.py              # POST /query (sync), POST /query/stream (SSE)
│   └── services/                 # Business logic
│       ├── company_loader.py     # BSE auto-ingest orchestrator (scrip → financials → PDFs)
│       ├── embedding_service.py  # FinBERT CLS extraction; runs in ThreadPoolExecutor(max_workers=1)
│       ├── forecast_service.py   # Bull/Bear/Macro agents + Synthesizer via asyncio.gather
│       ├── generation_service.py # LLM backends: generate() + raw_generate() + stream_generate()
│       ├── impact_service.py     # Graph propagation + LLM answer grounded in graph data
│       ├── ingestion_service.py  # parse → chunk → embed → store pipeline
│       ├── market_data_service.py# yfinance integration
│       ├── mcp_service.py        # Query classification, entity extract, filter build, context assembly
│       ├── query_service.py      # QueryService: classify → filter → retrieve → enrich → generate
│       ├── retrieval_service.py  # ChromaDB + BM25 + RRF hybrid retrieval
│       └── providers/
│           ├── base.py           # MarketDataProvider Protocol (interface)
│           └── bse_provider.py   # BSE India implementation (session warmup required for PDFs)
├── finance-ui/                   # Next.js 15 frontend
│   ├── app/                      # App Router pages
│   │   ├── layout.tsx            # Root layout, font, metadata
│   │   ├── page.tsx              # Landing / home page
│   │   ├── providers.tsx         # React context providers (auth, etc.)
│   │   ├── about/                # Static about page
│   │   ├── admin/                # Admin dashboard page (role-gated)
│   │   ├── auth/
│   │   │   ├── login/            # Login + register page
│   │   │   └── verify/           # Email verification landing
│   │   ├── company/
│   │   │   └── [ticker]/         # Company detail page (chat + forecast + graph)
│   │   └── preview/              # Guest preview page (unauthenticated)
│   ├── components/               # Shared React components
│   │   ├── auth-guard.tsx        # Redirect unauthenticated users
│   │   ├── ConditionalHeader.tsx # Header shown/hidden based on route
│   │   ├── feedback-modal.tsx    # Post-session feedback form
│   │   ├── header.tsx            # Top navigation bar
│   │   ├── search-bar.tsx        # Company search input
│   │   ├── home/                 # Landing page sections
│   │   │   ├── Hero.tsx
│   │   │   ├── FeaturesSection.tsx
│   │   │   ├── ValueSection.tsx
│   │   │   ├── CtaSection.tsx
│   │   │   ├── RoadmapSection.tsx
│   │   │   ├── PlatformStrip.tsx
│   │   │   ├── DotCanvas.tsx
│   │   │   ├── Navbar.tsx
│   │   │   └── Footer.tsx
│   │   └── ui/                   # Generic UI primitives (shadcn-style)
│   │       ├── badge.tsx
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── input.tsx
│   │       ├── separator.tsx
│   │       └── tabs.tsx
│   └── lib/
│       ├── api.ts                # Single HTTP client module; all fetch calls go through here
│       ├── auth.tsx              # Auth context + useAuth hook
│       └── utils.ts              # Shared utilities (cn, etc.)
├── data/                         # Runtime data (not committed except seed)
│   ├── chroma_db/                # ChromaDB persistent store (generated)
│   ├── sample_docs/              # Sample PDFs for manual testing
│   └── seed/
│       └── nifty50_banking_it_relationships_clean.json  # Graph seed data (committed)
├── tests/
│   ├── unit/                     # Unit tests (pytest)
│   └── integration/              # Integration tests (pytest)
├── scripts/
│   ├── benchmark_embeddings.py   # Embedding throughput benchmarking
│   └── seed_documents.py         # Seed ChromaDB with sample docs
├── monitoring/
│   └── grafana/
│       ├── dashboards/           # Grafana dashboard JSON
│       ├── dashboards-provisioning/
│       └── datasources/          # Prometheus datasource config
├── docker/                       # Docker build assets
├── docker-compose.yml            # Backend + Prometheus + Grafana stack
├── Dockerfile                    # FastAPI app container
├── requirements.txt              # Production Python dependencies
├── requirements-dev.txt          # Dev/test Python dependencies
├── pytest.ini                    # pytest config
├── CLAUDE.md                     # Claude Code context (rules, key files, flows)
└── README.md                     # Project overview
```

## Key File Locations

**Entry Points:**
- `app/main.py` — `create_app()` factory; `lifespan()` handles startup singleton init and graph seeding
- `finance-ui/app/layout.tsx` — Next.js root layout

**Configuration:**
- `app/config.py` — Pydantic `BaseSettings`; reads from `.env`. Keys: `LLM_PROVIDER`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `CHROMA_PERSIST_DIR`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ALLOWED_ORIGINS`
- `docker-compose.yml` — service orchestration with env var injection
- `finance-ui/lib/api.ts` — reads `NEXT_PUBLIC_API_URL` (build-time env var)

**Core Business Logic:**
- `app/services/query_service.py` — canonical query pipeline (sync endpoint)
- `app/routers/query.py` — streaming endpoint (inline duplicate of query pipeline, see known issues)
- `app/services/forecast_service.py` — multi-agent forecast orchestration
- `app/services/company_loader.py` — BSE auto-ingest; single source of truth for load order
- `app/graph/propagation_engine.py` — pure BFS impact propagation; no side effects

**Persistence:**
- `app/data/financial_db.py` — all financial data + graph edge/node tables + company registry
- `app/data/auth_db.py` — user accounts, credits, guest sessions, feedback
- `data/chroma_db/` — ChromaDB vector store (persisted on disk)

**Testing:**
- `tests/unit/` — unit tests
- `tests/integration/` — integration tests
- `pytest.ini` — test configuration

## Frontend Page Map

| Route | File | Purpose |
|---|---|---|
| `/` | `app/page.tsx` | Landing page with hero + feature sections |
| `/preview` | `app/preview/page.tsx` | Guest query/forecast (3 lifetime credits, no auth) |
| `/auth/login` | `app/auth/login/page.tsx` | Login + register form |
| `/auth/verify` | `app/auth/verify/page.tsx` | Email verification token handler |
| `/company/[ticker]` | `app/company/[ticker]/page.tsx` | Company chat, forecast, graph UI |
| `/admin` | `app/admin/page.tsx` | Admin analytics dashboard (role=admin only) |
| `/about` | `app/about/page.tsx` | Static about page |

## Backend Router → Service Map

| Router file | Prefix | Service(s) used |
|---|---|---|
| `routers/query.py` | `/query` | `QueryService`, `EmbeddingService`, `RetrievalService`, `GenerationService`, `MCPService`, `GraphStore` |
| `routers/forecast.py` | `/forecast` | `ForecastService` |
| `routers/companies.py` | `/companies` | `CompanyLoader`, `IngestionService` |
| `routers/ingestion.py` | `/documents` | `IngestionService` |
| `routers/graph.py` | `/graph` | `GraphStore`, `ImpactService`, `GenerationService` |
| `routers/market_data.py` | `/market` | `MarketDataService` |
| `routers/auth.py` | `/auth` | `auth_db` directly |
| `routers/preview.py` | `/preview` | `QueryService`, `ForecastService` (guest credit path) |

## Naming Conventions

**Files:** `snake_case.py` for Python; `kebab-case.tsx` or `PascalCase.tsx` for React components.

**Python classes:** `PascalCase` (e.g., `QueryService`, `GraphStore`, `VectorStoreClient`).

**Router prefixes:** Plural nouns matching the resource (`/companies`, `/documents`, `/collections`).

**Singleton privates:** `_get_*_singleton()` functions in `dependencies.py` are prefixed with underscore to signal they should not be called outside startup/dependency injection.

## Where to Add New Code

**New API endpoint:**
- Add router file to `app/routers/`
- Register router in `app/main.py` `create_app()`
- Add request/response Pydantic models in `app/models/`
- Add frontend API calls in `finance-ui/lib/api.ts`

**New service:**
- Implement in `app/services/`
- Add `@lru_cache` singleton factory in `app/dependencies.py`
- Inject into routers via `Depends(get_your_service)`

**New LLM backend:**
- Implement `ModelBackend` Protocol from `app/services/generation_service.py`
- Register backend choice in `_get_generation_service_singleton()` in `app/dependencies.py`

**New market data provider:**
- Implement `MarketDataProvider` Protocol from `app/services/providers/base.py`
- Swap provider by changing `_get_provider()` in `app/services/company_loader.py`

**New frontend page:**
- Add directory under `finance-ui/app/`
- Wrap with `<AuthGuard>` from `components/auth-guard.tsx` if login required
- Use `finance-ui/lib/api.ts` functions for all backend calls

**New graph relationship type:**
- Add to `EDGE_WEIGHTS` in `app/graph/graph_store.py`
- Add to `_TARGET_NODE_TYPES` in `app/graph/graph_store.py`
- Add to `_REL_LABELS` in `app/graph/graph_retriever.py`

## Special Directories

**`data/chroma_db/`:**
- Generated at runtime by ChromaDB
- Not committed to git
- Path configured by `CHROMA_PERSIST_DIR` env var

**`data/seed/`:**
- Committed JSON seed files for graph initialization
- Loaded automatically at startup if `graph_edges` table is empty

**`app/phase2/`:**
- Contains evaluation and fine-tuning scripts (not part of the live request pipeline)
- `evaluation/` and `fine_tuning/` subdirectories

**`.planning/codebase/`:**
- Architecture and convention documents for Claude Code context
- Generated; committed

---

*Structure analysis: 2026-04-01*
