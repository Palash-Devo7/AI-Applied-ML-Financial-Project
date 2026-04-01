# Coding Conventions

**Analysis Date:** 2026-04-01

## Python Code Style

**Formatting & Linting:**
- `ruff==0.9.1` for linting and formatting (configured via CLI flags; no `pyproject.toml`)
- `mypy==1.14.1` for static type checking
- All service files begin with `from __future__ import annotations` to enable PEP 563 deferred evaluation

**Type Hints:**
- All public methods carry full return type annotations: `async def embed_texts(self, texts: list[str]) -> list[list[float]]:`
- Private helpers use leading underscore and are annotated: `def _encode_batch(self, texts: list[str]) -> list[list[float]]:`
- `Optional[T]` from `typing` is used for optional Pydantic fields; `T | None` is used elsewhere in service code
- Protocol classes use `@runtime_checkable` decorator — see `ModelBackend` in `app/services/generation_service.py`

**Import Organization:**
1. `from __future__ import annotations`
2. Standard library (`asyncio`, `time`, `typing`, etc.)
3. Third-party (`structlog`, `fastapi`, `pydantic`, etc.)
4. Internal app imports (`app.models.*`, `app.services.*`, etc.)

**Module-level constants:** Named in `UPPER_SNAKE_CASE` (e.g., `MAX_PDFS = 3`, `_EXECUTOR = ThreadPoolExecutor(...)`)

---

## Naming Conventions

**Files:** `snake_case.py` throughout — `embedding_service.py`, `vector_store.py`, `auth_deps.py`

**Classes:** `PascalCase` — `EmbeddingService`, `VectorStoreClient`, `QueryService`, `ModelBackend`

**Functions/methods:** `snake_case` — `embed_texts()`, `build_metadata_filters()`, `get_current_user()`

**Private internals:** Leading underscore — `_encode_batch()`, `_write_lock`, `_get_embedding_service_singleton()`

**Singleton factory functions** in `app/dependencies.py`: `_get_<name>_singleton()` (private) + `get_<name>()` (public async wrapper exposed to FastAPI `Depends`)

**structlog event keys:** `snake_case` string literals — `"query_started"`, `"finbert_model_loaded"`, `"chroma_collection_ready"`

---

## Logging Approach

**Framework:** `structlog` with JSON output via `logger = structlog.get_logger(__name__)` — declared once per module at module level.

**Log call pattern:**
```python
logger.info("event_key", field1=value1, field2=value2)
logger.error("event_key_failed", error=str(exc))
logger.debug("detail_event", query_id=query_id, entities=entities)
```
Event keys are snake_case verb-noun descriptors. Never use f-strings in log calls — pass structured fields instead.

---

## FastAPI Patterns

**Router structure:**
- Each router lives in `app/routers/<domain>.py`
- Routers declare `router = APIRouter(tags=["<tag>"])` at module level
- Routes use `response_model=`, `status_code=`, and `summary=` on every `@router.post`/`@router.get`
- Services are never instantiated in route functions — always injected via `Depends()`

**Dependency injection:**
```python
@router.post("/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def query_documents(
    request: Request,
    body: QueryRequest,
    user: dict = Depends(require_credits),
    embedding_service = Depends(get_embedding_service),
) -> QueryResponse:
```

**Auth dependency chain:** `get_current_user` → `require_verified` → `require_credits` (each `Depends` the previous). Always attach credit consumption _after_ success via `consume_after_success(request)`.

**Background tasks pattern:** Return `202 Accepted` immediately; add work to `BackgroundTasks`; client polls a status endpoint.

**Error handling in routes:** Catch broad `Exception`, log with `logger.error(...)`, re-raise as `HTTPException(status_code=500)`.

---

## Service Layer Patterns

**Singletons via `@lru_cache`** — all services are instantiated once in `app/dependencies.py`:
```python
@lru_cache(maxsize=1)
def _get_embedding_service_singleton():
    from app.services.embedding_service import EmbeddingService
    ...
    return EmbeddingService(...)
```
Never instantiate services outside `app/dependencies.py` (except in tests where they are injected directly).

**Stateless services:** Services hold no per-request state. All mutable state is in SQLite (`app/data/financial_db.py`) or ChromaDB.

**Services accept dependencies as constructor arguments** (not via global imports), enabling clean test injection.

---

## Threading Rules (Critical — Never Break)

**ChromaDB (sync-only):** Wrap all read and write calls in `run_in_threadpool()` from `starlette.concurrency`. Write operations additionally guarded by `asyncio.Lock()`:
```python
# app/core/vector_store.py
async def upsert_chunks(self, ...):
    async with self._write_lock:
        await run_in_threadpool(self._collection.upsert, ...)
```

**FinBERT (CPU-bound):** Run in module-level `ThreadPoolExecutor(max_workers=1)` via `loop.run_in_executor`:
```python
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="finbert")
embeddings = await loop.run_in_executor(_EXECUTOR, self._encode_batch, texts)
```

**BSE calls (sync I/O):** Wrap with `asyncio.to_thread()` inside async functions:
```python
scrip_code = await asyncio.to_thread(self._bse.get_scrip_code, ticker)
```

**Forecast agents:** Bull, Bear, Macro agents run concurrently via `asyncio.gather()` — each is an async `raw_generate()` call. Synthesizer runs after all three complete.

---

## Pydantic Model Conventions

- All models extend `pydantic.BaseModel`
- Use `Field(...)` for required fields with `description=` and validators: `Field(..., min_length=3, max_length=2000)`
- Use `Optional[T]` with `= None` default for optional fields
- `QueryFilters` is a flat model (no nesting) passed as `Optional[QueryFilters]` inside request models
- Response models (`QueryResponse`) contain nested models (`TokenUsageDetail`, `RetrievedChunk`)
- Models live in `app/models/<domain>.py`; do not define models inside service files

---

## Frontend Patterns (Next.js / TypeScript)

**TypeScript config:** `strict: true`, `target: ES2017`, `moduleResolution: bundler`, path alias `@/*` maps to project root.

**ESLint:** `eslint-config-next/core-web-vitals` + `eslint-config-next/typescript` (no custom rule overrides).

**Component conventions:**
- Client components declare `"use client"` as the first line
- Named exports for components used in layout/composition: `export function Header()`
- Default exports for page-level route components
- Components receive typed props interfaces declared inline or above the component

**React hooks:**
- Auth state is centralised in `AuthContext` (`lib/auth.tsx`) — consume via `useAuth()` hook
- `useEffect` for side effects (token restore, tab-focus refresh, SSE stream lifecycle)
- `useCallback` wraps event handlers that are passed to children or used in `useEffect` deps
- `useState` typed explicitly: `useState<AuthState>({...})`

**API calls:** All backend calls go through the `request<T>()` helper in `lib/api.ts`. It injects the Bearer token and handles 401 redirect automatically. Never call `fetch()` directly from components.

**Environment variable:** `NEXT_PUBLIC_API_URL` for backend base URL; defaults to `http://localhost:8080`.

---

## Error Handling

**Backend — services:** Raise domain-specific exceptions (`ValueError` for invalid input), log with `logger.error(...)`, let routers convert to `HTTPException`.

**Backend — routes:** Broad `except Exception` catch → `HTTPException(500)`. Auth errors raise `HTTPException(401/403/429)` directly from dependency functions.

**Frontend:** `request<T>()` throws `Error(message)` for non-OK responses. Components catch errors from `await` calls in event handlers; 401 responses trigger automatic redirect to `/auth/login`.
