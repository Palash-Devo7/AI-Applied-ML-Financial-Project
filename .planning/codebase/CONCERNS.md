# Codebase Concerns

**Analysis Date:** 2026-04-01

---

## Tech Debt

**[HIGH] Duplicate enrichment pipeline in query router and query service:**
- Issue: `POST /query/stream` in `app/routers/query.py` (lines 82–144) contains a full inline copy of the classify → filter → embed → retrieve → structured-enrich → graph-enrich pipeline. The identical logic lives in `app/services/query_service.py` `QueryService.query()`. Any change to enrichment (e.g. adding a new context source) must be made in both places manually.
- Files: `app/routers/query.py`, `app/services/query_service.py`
- Impact: Divergence bugs. The stream path has already drifted: it lacks per-query Prometheus metrics and ULID tracking present in `QueryService.query()`.
- Fix approach: Extract a shared `async def _build_context(request, services) -> tuple[str, list, str]` helper. Both the non-streaming and streaming paths call it; the stream path wraps the result in SSE.

**[MED] Rate limit strings are hardcoded in decorator literals, not read from config:**
- Issue: `@limiter.limit("5/minute")` is repeated verbatim across `app/routers/query.py` (lines 38, 65) and `app/routers/ingestion.py` (line 82). `config.py` defines `rate_limit_query` and `rate_limit_upload` settings that are never consumed by the decorators.
- Files: `app/routers/query.py`, `app/routers/ingestion.py`, `app/config.py`
- Impact: Changing the rate limit in `.env` has no effect; the hardcoded literals take precedence.
- Fix approach: Pass the settings value into `limiter.limit(get_settings().rate_limit_query)` or use a factory function.

**[MED] Credit limit constants not in config:**
- Issue: `DAILY_LIMIT_TRIAL = 10` and `GUEST_CREDIT_LIMIT = 3` are module-level constants in `app/data/auth_db.py` (lines 22–23). They cannot be adjusted via environment variables without a code change.
- Files: `app/data/auth_db.py`
- Fix approach: Move to `Settings` (e.g. `trial_daily_credits: int = 10`) and read from `get_settings()`.

**[MED] `forecast_service.py` hardcodes `top_k=5` for PDF context retrieval:**
- Issue: Line 229 of `app/services/forecast_service.py` passes `top_k=5` directly rather than reading from `settings.retrieval_top_k`.
- Files: `app/services/forecast_service.py`
- Impact: Tuning retrieval depth for forecast quality requires a code change, not a config change.
- Fix approach: Inject settings or read `get_settings().retrieval_top_k`.

---

## Architectural Risks

**[HIGH] BFS propagation visits each node only once — misses higher-weight alternative paths:**
- Issue: `app/graph/propagation_engine.py` adds a neighbor to `visited` the first time it is reached (line 64 check, line 73 `visited.add`). If a node is reachable via two paths and the first-encountered path carries a lower cumulative weight than a later path, the node's `impact_score` is understated. For a directed graph with multiple supply-chain paths this is a correctness problem, not just precision.
- Files: `app/graph/propagation_engine.py`
- Impact: Affected companies may receive lower impact scores than they deserve, causing them to be pruned by `MIN_IMPACT = 0.2`.
- Fix approach: Switch to a relaxation approach (like Dijkstra/Bellman-Ford) that updates scores when a higher-weight path is found, or accumulate scores per node and sort at the end.

**[MED] Graph store loads fully into memory with no refresh path for live mutations:**
- Issue: `GraphStore.load_from_db()` in `app/graph/graph_store.py` (line 51) rebuilds the NetworkX DiGraph once at startup. If edges are added at runtime (e.g. via the graph builder or future seed endpoints), the in-memory graph goes stale until the next process restart.
- Files: `app/graph/graph_store.py`
- Impact: New relationships seeded after startup are invisible to propagation and chat context without a restart.
- Fix approach: Add a `reload()` method and call it from the graph mutation endpoints, or expose a `POST /graph/reload` admin endpoint.

**[LOW] Phase C (GraphRAG) is partially live but not gated by a feature flag:**
- Issue: Graph context is silently prepended to all LLM queries in both `query_service.py` (line 91) and `query.py` stream path (line 111) when `company_name` is set. If the graph is empty the code falls back gracefully, but if the graph contains stale or incorrect relationships they will silently contaminate every answer.
- Files: `app/services/query_service.py`, `app/routers/query.py`
- Fix approach: Add a `GRAPH_RAG_ENABLED` settings flag so graph context can be toggled off without a code change.

---

## Performance Bottlenecks

**[HIGH] FinBERT is CPU-bound and single-threaded:**
- Issue: `app/services/embedding_service.py` creates `ThreadPoolExecutor(max_workers=1)` (line 15). Every embedding call — per query, per forecasted chunk, per ingested document — queues behind a single CPU thread. Concurrent requests will serialize on FinBERT inference.
- Files: `app/services/embedding_service.py`
- Impact: Under moderate load (>2 concurrent users) latency spikes significantly.
- Fix approach: This is constrained by GIL + model thread-safety. Short-term: add GPU support via `embedding_device: str = "cpu"` already in config. Long-term: move to a dedicated embedding microservice or use Groq/OpenAI embeddings for production scale.

**[HIGH] OCR ingestion blocks for 10–20 minutes per large PDF:**
- Issue: `app/core/document_parser.py` falls back to Tesseract OCR when pypdf and pdfplumber fail. A 44-page scanned PDF takes 10–20 minutes in this fallback path. The `POST /documents/upload` endpoint returns 202 and runs OCR in a `BackgroundTask`, but there is no timeout, no progress granularity beyond a status string, and no failure recovery if the background worker crashes mid-PDF.
- Files: `app/core/document_parser.py`, `app/routers/ingestion.py`
- Impact: Server resources are consumed for tens of minutes per PDF; if the process restarts the ingestion is silently lost.
- Fix approach: Add a per-document OCR timeout (e.g. 15 min), page-level checkpointing, and persist partially-ingested chunks rather than discarding on failure.

**[MED] Company status polling in the frontend re-fetches financials on every 2-second tick:**
- Issue: `finance-ui/app/company/[ticker]/company-view.tsx` `poll()` loop (lines 815–838) calls `fetchFinancials()` unconditionally on every iteration until `status === "ready"`, regardless of whether `financials_synced_at` has changed. For a company with a long load time this is dozens of redundant API calls.
- Files: `finance-ui/app/company/[ticker]/company-view.tsx`
- Fix approach: Gate the `fetchFinancials()` call on a changed `financials_synced_at` timestamp, similar to how `prices_synced_at` is handled on line 826.

---

## Security Concerns

**[HIGH] JWT secret has a weak default in config:**
- Issue: `app/config.py` line 76 sets `jwt_secret: str = Field(default="change-me-in-production-use-openssl-rand-hex-32")`. If `.env` is absent or the variable is unset, the application starts with a known, publicly documented secret, making all JWTs forgeable.
- Files: `app/config.py`, `app/core/security.py`
- Impact: Full authentication bypass in any deployment that omits `.env`.
- Fix approach: Raise `ValueError` at startup if `jwt_secret` is the default value and `environment == "production"`.

**[MED] Rate limiter keys on IP address only — trivially bypassable behind proxy:**
- Issue: `app/core/limiter.py` uses `get_remote_address` as the key function. Behind a reverse proxy (Nginx, Cloudflare) all requests share the proxy's IP, making the per-IP limit useless. There is no fallback to user ID or API key keying.
- Files: `app/core/limiter.py`
- Impact: Rate limiting provides no protection in production deployments behind a proxy.
- Fix approach: Use a composite key: `X-Forwarded-For` header (with validation) for anonymous requests, user ID for authenticated ones.

**[LOW] `check_and_consume` in `auth_db.py` has a TOCTOU race under concurrent requests:**
- Issue: Credit check (`check_and_consume`) and consumption (`consume_credits`) are two separate SQLite calls separated by the HTTP handler. A user sending two simultaneous requests could pass both credit checks before either consumption is recorded.
- Files: `app/data/auth_db.py`, `app/core/auth_deps.py`
- Fix approach: Perform check and insert in a single atomic `INSERT ... WHERE remaining > 0` SQLite statement inside the same transaction.

---

## Known Bugs

**[HIGH] `bse.lookup()` raises `IndexError` in bse v3.2.0:**
- Issue: Documented in `CLAUDE.md` (line 122). The `bse.lookup()` method has an index-out-of-bounds bug. The correct call is `bse.getScripCode(ticker)`.
- Files: `app/services/providers/bse_provider.py`
- Impact: Any code path that accidentally calls `bse.lookup()` will raise an uncaught exception, failing the company load silently.
- Fix approach: Never call `bse.lookup()`. The fix is already applied in `bse_provider.py`; risk is regression if new code is added.

**[MED] `nonlocal` inside `if` blocks is illegal in Python 3.14:**
- Issue: Documented in `CLAUDE.md` (line 124). Any nested function that uses `nonlocal` conditionally will fail at parse time under Python 3.14+. The prescribed workaround is the `state = {}` dict pattern.
- Files: Any file using `nonlocal` inside conditional blocks (grep needed before upgrading Python).
- Impact: Breaks on Python 3.14 upgrade.
- Fix approach: Audit `nonlocal` usages before any Python version bump.

---

## Fragile Areas

**[HIGH] BSE PDF download silently fails without session warmup:**
- Issue: Akamai Bot Manager on BSE India blocks cold `requests.Session` PDF downloads. `BSEProvider.__init__` calls `_warmup()` (line 53 of `app/services/providers/bse_provider.py`), but warmup swallows all exceptions (`except Exception: pass`). If warmup fails (e.g. BSE is temporarily down), subsequent PDF downloads will receive HTML error pages instead of PDF bytes, which are caught by the `content[:4] == b'%PDF'` validator and silently skipped.
- Files: `app/services/providers/bse_provider.py`
- Impact: Company load completes with `status=ready` but zero PDF documents indexed, leaving the chat and forecast features with no context.
- Fix approach: Log a WARNING with the warmup failure reason; retry warmup before the first PDF download attempt.

**[MED] ChromaDB is sync-only and requires explicit `asyncio.Lock` for writes:**
- Issue: `CLAUDE.md` rule 1. Any new write path that omits `run_in_threadpool()` or the lock will cause event-loop blocking or data corruption under concurrent ingestion.
- Files: `app/core/vector_store.py`, any future code writing to ChromaDB
- Impact: Silent data corruption or event loop stall under concurrent company loads.
- Fix approach: Enforce via a wrapper method that always acquires the lock; never expose raw ChromaDB client outside `vector_store.py`.

**[MED] Company name case-sensitivity in ChromaDB metadata filters:**
- Issue: Documented in `CLAUDE.md` (line 125). ChromaDB `where` filters use exact string matching. If a company is ingested as `"Tata Steel"` but queried as `"TATA STEEL"`, no chunks are returned.
- Files: `app/services/providers/bse_provider.py`, `app/core/metadata_extractor.py`
- Impact: Queries for a loaded company silently return no context, producing hallucinated answers.
- Fix approach: Normalize `company` metadata to Title Case at ingest and at query filter time in `MCPService.build_metadata_filters()`.

---

## Missing Features / Incomplete Implementations

**[HIGH] End-to-end test of company load flow is not done:**
- Issue: `CLAUDE.md` (line 31) notes that `POST /companies/load` with TATASTEEL has not been end-to-end tested. The integration tests in `tests/integration/` cover ingestion and query pipelines but not the company loader BSE path.
- Files: `tests/integration/`, `app/services/company_loader.py`
- Impact: Regressions in the BSE → SQLite → ChromaDB flow may go undetected.

**[HIGH] Phase D (Zerodha Kite Connect brokerage) is not implemented:**
- Issue: Noted in `CLAUDE.md` as pending. No brokerage integration exists. The feature is blocked on auth implementation.
- Impact: The product cannot place or track orders.

**[MED] No clickable company link from the Impact tab affected-companies table:**
- Issue: In `finance-ui/app/company/[ticker]/company-view.tsx` `ImpactTab` (lines 708–732), affected company tickers are rendered as plain `<span>` text. There is no link to `/company/[affected_ticker]`.
- Impact: Users who discover a downstream impact cannot navigate directly to that company's page; they must manually search.
- Fix approach: Wrap `node.ticker` in a Next.js `<Link href={/company/${node.ticker}}>` component.

**[MED] Chat tab has no pre-filled question suggestions:**
- Issue: The `ChatTab` empty state (lines 487–490 in `company-view.tsx`) shows only a static text prompt. There are no suggested questions (e.g. "What are the key risks?", "Summarise recent earnings") to guide new users.
- Impact: Cold-start friction for users who don't know what to ask.

**[LOW] `app/phase2/` directory contains evaluation and fine-tuning stubs that are not wired up:**
- Issue: `app/phase2/evaluation/` and `app/phase2/fine_tuning/` exist in the directory tree but are not imported or called from any service. `config.py` has `use_finetuned_model` and `finetuned_model_path` settings that always resolve to their defaults.
- Files: `app/phase2/`, `app/config.py`
- Impact: Dead code adds confusion about what is active.

---

## Test Coverage Gaps

**[HIGH] Graph propagation engine has no unit tests:**
- What's not tested: `propagate()` in `app/graph/propagation_engine.py` — specifically multi-hop scoring, `MIN_IMPACT` pruning, and the visited-once limitation.
- Files: `app/graph/propagation_engine.py`, `tests/unit/` (no corresponding test file)
- Risk: Scoring bugs go unnoticed. The visited-once issue (see Architectural Risks) cannot be caught without tests.
- Priority: High

**[MED] BSEProvider is not tested:**
- What's not tested: Warmup failure handling, PDF byte validation, scrip code resolution.
- Files: `app/services/providers/bse_provider.py`, `tests/` (no BSE provider test)
- Risk: BSE API changes or Akamai policy changes break silently.
- Priority: Medium

**[MED] Auth + credit system has no tests:**
- What's not tested: TOCTOU credit race, daily reset logic, API key auth path.
- Files: `app/data/auth_db.py`, `app/core/auth_deps.py`
- Priority: Medium

---

*Concerns audit: 2026-04-01*
