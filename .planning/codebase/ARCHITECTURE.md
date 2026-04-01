# Architecture

**Analysis Date:** 2026-04-01

## System Overview

Finance AI RAG — a backend API + Next.js frontend for researching BSE-listed Indian companies. Users load a company ticker; the system auto-fetches financials and PDFs from BSE India, embeds them with FinBERT, and stores them in ChromaDB. Users then ask natural language questions (RAG pipeline) or request multi-agent event forecasts. A GraphRAG layer (NetworkX + SQLite) models inter-company relationships and propagates event impact across supply chains.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  finance-ui (Next.js, port 3000)                                │
│  app/page.tsx  app/company/[ticker]/  app/admin/               │
│  lib/api.ts — REST + SSE fetch client                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / SSE  (NEXT_PUBLIC_API_URL)
┌──────────────────────────▼──────────────────────────────────────┐
│  FastAPI  (Uvicorn, port 8000)   app/main.py                   │
│  Middleware: CORS · RateLimit · RequestLogging · SecurityHdrs  │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────────┐  │
│  │  /auth   │  /query  │/forecast │/companies│  /graph      │  │
│  │  /docs   │  /stream │ /event   │  /load   │  /propagate  │  │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴──────┬───────┘  │
│       │          │          │          │            │           │
│  ┌────▼──────────▼──────────▼──────────▼────────────▼───────┐  │
│  │         Services  (app/services/)                         │  │
│  │  QueryService · ForecastService · ImpactService          │  │
│  │  CompanyLoader · IngestionService · MCPService           │  │
│  │  EmbeddingService · RetrievalService · GenerationService │  │
│  └────┬──────────┬──────────┬──────────┬────────────────────┘  │
│       │          │          │          │                        │
│  ┌────▼──┐  ┌────▼──┐  ┌───▼───┐  ┌───▼──────────────────┐   │
│  │ChromaDB│  │SQLite │  │FinBERT│  │  NetworkX GraphStore  │   │
│  │vector  │  │fin_db │  │ CPU   │  │  + PropagationEngine  │   │
│  │ store  │  │auth_db│  │thread │  │  (app/graph/)         │   │
│  └────────┘  └───────┘  └───────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │  External Services      │
              │  BSE India (bse pkg)    │
              │  Groq / DeepSeek /      │
              │  Anthropic Claude LLM   │
              └─────────────────────────┘
```

## Singleton Pattern via `dependencies.py`

All stateful services are created exactly once per process via `@lru_cache(maxsize=1)` in `app/dependencies.py`. FastAPI `Depends()` calls the async wrapper which delegates to the cached singleton.

```
_get_embedding_service_singleton()   → EmbeddingService   (FinBERT, ThreadPoolExecutor)
_get_vector_store_singleton()        → VectorStoreClient  (ChromaDB)
_get_retrieval_service_singleton()   → RetrievalService   (depends on vector_store)
_get_generation_service_singleton()  → GenerationService  (Groq/DeepSeek/Claude backend)
_get_mcp_service_singleton()         → MCPService         (classifier, entity extractor)
_get_graph_store_singleton()         → GraphStore         (NetworkX DiGraph)
```

Rule: never instantiate services outside `app/dependencies.py` except in tests.

## Layers

**Routers (`app/routers/`):**
- Purpose: HTTP request validation, auth/credit gating, background task dispatch
- Delegates all business logic to Services; never touches DB or models directly
- Uses `Depends(require_credits)` + `consume_after_success()` for credit checks
- Returns 202 + `BackgroundTasks` for long-running operations (load, ingest)

**Services (`app/services/`):**
- Purpose: Business logic — query pipeline, forecasting, ingestion, market data
- Stateless; receive singletons via constructor injection from routers
- ChromaDB/BSE/FinBERT calls always wrapped: `run_in_threadpool()` or `asyncio.to_thread()`

**Core (`app/core/`):**
- Purpose: Infrastructure primitives — vector store wrapper, document parser, chunker, prompts, security, rate limiter, email
- No business logic; no external API calls at this layer

**Data (`app/data/`):**
- Purpose: SQLite persistence — `financial_db.py` (financials, prices, events, graph tables) and `auth_db.py` (users, credits, feedback)
- Raw SQL via `sqlite3`; thread safety via `threading.Lock()`

**Graph (`app/graph/`):**
- Purpose: NetworkX in-memory graph backed by SQLite; impact propagation
- `GraphStore` — SQLite ↔ NetworkX bridge; seeded from JSON at startup
- `PropagationEngine` — pure weighted BFS, no I/O; scores affected nodes
- `GraphRetriever` — builds relationship summary string for LLM context injection

**Models (`app/models/`):**
- Purpose: Pydantic request/response schemas shared across routers and services
- Files: `queries.py`, `forecast.py`, `impact.py`, `documents.py`, `monitoring.py`

## Key Data Flows

### Query Pipeline (`POST /query` and `POST /query/stream`)

```
Client request
  → auth_deps.require_credits()              [gate: 1 credit]
  → MCPService.classify_query()              → query_type (RISK|REVENUE|MACRO|…)
  → MCPService.extract_entities()            → {company, ticker, year, …}
  → MCPService.build_metadata_filters()      → ChromaDB where-clause
  → EmbeddingService.embed_texts([question]) → 768-dim FinBERT vector
  → RetrievalService.hybrid_query()          → top-K chunks (vector + BM25 + RRF)
  → MCPService.assemble_context()            → deduped, citation-formatted string
  → financial_db.build_financial_context()   → SQLite financials prepended
  → GraphRetriever.build_graph_context()     → relationship graph prepended
  → GenerationService.generate()             → LLM answer
  → consume_after_success()                  [debit credit]
```

`/query/stream` runs the same pipeline inline in `query.py` and emits SSE events:
`meta` (sources, query_type) → `token` (repeated) → `done`.

**Known issue:** The stream endpoint duplicates enrichment logic from `query_service.py`. Both must be kept in sync until a shared `_build_context()` helper is extracted.

### Company Load Pipeline (`POST /companies/load`)

```
Client POST {ticker}
  → BackgroundTasks.add_task(_run)           [returns 202 immediately]
  → CompanyLoader.load(ticker)
      → BSEProvider.get_scrip_code()         → scrip_code
      → BSEProvider.get_company_name()
      → financial_db.register_company()      status = "loading"
      → BSEProvider.get_financials()         → SQLite upsert
      → BSEProvider.get_price()              → stock_prices upsert
      → BSEProvider.get_announcements()      → filter PDF list
      → BSEProvider.download_pdf()           [requires session warmup!]
      → IngestionService.ingest()
          → DocumentParser.parse()           → text (3-layer: pypdf→pdfplumber→OCR)
          → Chunker.chunk()                  → 512-token sections, 64-token overlap
          → MetadataExtractor.extract()      → company/year/quarter/section
          → EmbeddingService.embed_texts()   → FinBERT vectors (thread pool)
          → VectorStoreClient.add()          → ChromaDB (asyncio.Lock for writes)
      → financial_db.update_company_status() status = "ready"
Client polls GET /companies/status/{ticker}
```

### Forecast Pipeline (`POST /forecast/event`)

```
Client POST {company, event_type, event_description, horizon_days}
  → ForecastService.forecast()
      → financial_db.build_financial_context()  [SQLite structured data]
      → financial_db.search_similar_events()    [historical events lookup]
      → EmbeddingService + RetrievalService     [top-5 PDF chunks for company]
      → asyncio.gather(                         [3 agents in parallel]
            run_agent("bull", BULL_SYSTEM),
            run_agent("bear", BEAR_SYSTEM),
            run_agent("macro", MACRO_SYSTEM),
        )  → each: GenerationService.raw_generate()
      → GenerationService.raw_generate(SYNTHESIZER_SYSTEM, all_views)
      → parse + return ForecastResponse
```

### Impact Propagation Pipeline (`POST /graph/propagate`)

```
Client POST {ticker, event_description, depth}
  → ImpactService.propagate()
      → propagation_engine.propagate()          [BFS, pure in-memory, no I/O]
          → weighted BFS up to depth hops
          → prune edges below MIN_IMPACT (0.2)
          → returns {companies: [...], factors: [...]} sorted by impact_score
      → graph_retriever.build_graph_context()   [direct edges → LLM context string]
      → GenerationService.raw_generate()        [LLM answer grounded in graph]
      → return PropagationResponse
```

## GraphRAG Layer

`app/graph/graph_store.py` — `GraphStore` holds a `nx.DiGraph` in memory. At startup, edges are loaded from SQLite `graph_nodes` + `graph_edges` tables (or seeded from `data/seed/nifty50_banking_it_relationships_clean.json` if the table is empty). Relationships carry pre-computed weights (e.g., `supplies_to=0.9`, `belongs_to_sector=0.3`) multiplied by a per-edge confidence score.

Node types: `company`, `macro`, `regulator`, `group`, `geography`, `sector`.

`app/graph/propagation_engine.py` — `propagate()` is a pure function: no I/O, no LLM. Weighted BFS from trigger ticker; cumulative weight = product of edge weights along path. Nodes below `MIN_IMPACT=0.2` are pruned. Returns two lists: affected companies and activated macro factors.

`app/graph/graph_retriever.py` — `build_graph_context()` formats direct edges of a ticker as a structured text block injected into every query/stream context window.

## Frontend ↔ Backend Communication

`finance-ui/lib/api.ts` is the single HTTP client module. It reads `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8080`). All authenticated requests attach `Authorization: Bearer <JWT or API key>`. On 401, the client clears the token and redirects to `/auth/login`.

SSE streaming: `streamQuery()` and `streamPreviewQuery()` open a `fetch()` to `/query/stream` (or `/query/preview`), read the response body with a `ReadableStream` reader, and parse `data: {...}` lines. Event types: `meta`, `token`, `done`, `error`.

## Auth and Credit System

**Auth:** JWT (HS256 via `app/core/security.py`) or API key (prefix `fr_`). Both are accepted in the `Authorization: Bearer` header by `app/core/auth_deps.get_current_user()`. Email verification required before using gated endpoints (`require_verified`). Admin users bypass verification and daily credit limits.

**Credits:** Defined in `app/data/auth_db.py` as `CREDIT_COSTS` dict keyed by exact path:
- `/query`, `/query/stream` → 1 credit
- `/forecast/event`, `/documents/upload` → 2 credits
- `/companies/load` → 1 credit

Trial users: 10 credits/day (resets at midnight UTC). Admins: unlimited. Guest users (unauthenticated preview): 3 lifetime credits. Credit check happens at request entry (`check_and_consume`); debit happens post-success (`consume_after_success`).

## Error Handling

**Strategy:** Fail-open on non-critical enrichments; fail-closed on core pipeline.

- Graph context, structured financial context, and BSE cache failures are logged as warnings and skipped — the query still proceeds.
- Agent failures in forecast fall back to a neutral stub response.
- Uncaught exceptions in routers return a generic 500 JSON response (no stack traces in production).
- BSE PDF ingestion runs in background; failures are recorded in company registry status, not surfaced to client as HTTP errors.

## Monitoring

`app/monitoring/metrics.py` — Prometheus counters/histograms (`QUERIES_TOTAL`, `QUERY_DURATION_SECONDS`).
`app/monitoring/middleware.py` — `RequestLoggingMiddleware` logs every request with structlog.
`app/monitoring/logger.py` — JSON structured logging via structlog.
Grafana dashboards in `monitoring/grafana/`.

---

*Architecture analysis: 2026-04-01*
