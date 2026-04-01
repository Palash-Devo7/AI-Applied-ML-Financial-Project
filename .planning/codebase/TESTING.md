# Testing Patterns

**Analysis Date:** 2026-04-01

## Test Framework

**Runner:** `pytest==8.3.4`
Config: `finance-rag/pytest.ini`

**Key pytest settings:**
```ini
[pytest]
asyncio_mode = auto          # all async tests run automatically
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests (no external dependencies)
    integration: Integration tests (may require services)
    slow: Tests marked as slow
```

**Additional libraries:**
- `pytest-asyncio==0.25.2` — async test support (mode: auto)
- `pytest-cov==6.0.0` — coverage reporting
- `httpx==0.28.1` — `AsyncClient` for endpoint tests

**Run commands:**
```bash
# Run all tests
cd "D:/AI finance project/finance-rag"
pytest

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# With coverage
pytest --cov=app --cov-report=term-missing

# Single file
pytest tests/unit/test_chunker.py -v
```

---

## Test File Organization

**Location:** `tests/` at project root, split into `unit/` and `integration/` subdirectories.

```
tests/
  conftest.py                    # shared fixtures (session-scoped event loop, mocks)
  unit/
    __init__.py
    test_chunker.py              # FinancialChunker — pure logic, no I/O
    test_metadata_extractor.py   # MetadataExtractor — pure logic, no I/O
    test_mcp_service.py          # MCPService — pure logic, no I/O
  integration/
    __init__.py
    test_ingestion_pipeline.py   # IngestionService with mocked embed + vector store
    test_query_pipeline.py       # QueryService with mocked embed + vector store + generation
```

**Naming:** `test_<module_name>.py`. Test functions named `test_<what>_<expected_outcome>`.

---

## Test Structure

**Fixture-per-class pattern** (no `Test*` classes in current tests — all module-level functions):
```python
@pytest.fixture
def chunker():
    return FinancialChunker(chunk_size_tokens=480, chunk_overlap_tokens=64)

def test_chunk_empty_text(chunker):
    chunks = chunker.chunk_document("")
    assert chunks == []
```

**Async tests** use plain `async def` — `asyncio_mode = auto` handles the event loop:
```python
@pytest.mark.asyncio
async def test_ingestion_returns_upload_response(ingestion_service, sample_pdf_bytes, ...):
    result = await ingestion_service.ingest(...)
    assert result.status == "ingested"
```

---

## Shared Fixtures (`tests/conftest.py`)

All shared fixtures live in `tests/conftest.py` with no scope specified (function-scoped by default), except `event_loop` which is `scope="session"`.

**Available shared fixtures:**

| Fixture | Returns | Notes |
|---------|---------|-------|
| `mock_settings` | None | `monkeypatch` sets env vars including `CHROMA_PERSIST_DIR=/tmp/test_chroma` |
| `mock_embedding_service` | `MagicMock` | `embed_texts` returns `AsyncMock` → `[[0.1]*768, [0.2]*768]` |
| `mock_vector_store` | `MagicMock` | `count`, `upsert_chunks`, `query`, `get_collection_info`, `delete_collection` all `AsyncMock` |
| `mock_generation_service` | `MagicMock` | `generate` returns `AsyncMock` → `(answer_str, TokenUsageDetail)` |
| `sample_pdf_bytes` | `bytes` | Minimal valid PDF binary for parse/ingest tests |

---

## Mocking Approach

**What is mocked:**
- `EmbeddingService` — FinBERT loading is slow and requires model weights; mock returns fixed `[0.1]*768` vectors
- `VectorStoreClient` — ChromaDB persistence requires disk; mock returns fixed query results
- `GenerationService` — LLM calls require API keys and network; mock returns a fixed answer string
- `DocumentParser.parse` — patched via `unittest.mock.patch` inside specific integration tests to return a `ParsedDocument` directly without PDF parsing

**What is NOT mocked:**
- `FinancialChunker` — tested against real logic with real text inputs
- `MetadataExtractor` — tested against real regex patterns
- `MCPService` — tested against real classification and entity extraction logic
- `RetrievalService` — instantiated with the mock vector store but its BM25 + RRF logic runs for real

**Mocking tools used:** `unittest.mock.MagicMock`, `unittest.mock.AsyncMock`, `unittest.mock.patch` (context manager form). `pytest-mock` is not used.

**Service construction in integration tests:** Services are constructed directly by passing mock dependencies as constructor arguments — not via the `app/dependencies.py` singletons. This is the correct pattern for tests.

---

## What Is Tested

**Unit tests (`tests/unit/`):**
- `test_chunker.py` — empty input, short text, content preservation, section detection, token count estimation, multi-chunk splitting, sequential chunk indices
- `test_metadata_extractor.py` — ticker/company extraction, year extraction, report type (10-K/10-Q), quarter, sector, override precedence, filename year fallback, section type classification
- `test_mcp_service.py` — query classification (RISK/REVENUE/MACRO/COMPARATIVE/HISTORICAL/GENERAL), entity extraction (ticker, year, quarter), filter construction (single, multi, empty, explicit override), context assembly (sort by score, deduplication, citation format, empty input)

**Integration tests (`tests/integration/`):**
- `test_ingestion_pipeline.py` — full ingest returns valid `UploadResponse`; vector store `upsert_chunks` called with correct args; empty content raises `ValueError`
- `test_query_pipeline.py` — full query returns structured `QueryResponse`; filters passed through; graceful handling when no results; `include_sources=False` suppresses sources; query type classification end-to-end

---

## Coverage Gaps

The following areas have **no test coverage** and represent risk:

- **`app/routers/*.py`** — No HTTP-level endpoint tests exist. `httpx.AsyncClient` is installed but no `TestClient` or `AsyncClient` test suite is present.
- **`app/core/vector_store.py`** — The `asyncio.Lock` write-guard and `run_in_threadpool` wrapping are not tested.
- **`app/services/company_loader.py`** — The full BSE auto-ingest flow (`POST /companies/load`) is explicitly noted as untested in `CLAUDE.md`.
- **`app/services/forecast_service.py`** — Bull/Bear/Macro agent parallelism and Synthesizer are not tested.
- **`app/services/generation_service.py`** — LLM backends (Groq, DeepSeek, Claude) and streaming are not tested.
- **`app/data/financial_db.py`** — SQLite operations (upsert, query, registry) are not tested.
- **`app/core/document_parser.py`** — The 3-layer PDF fallback (pypdf → pdfplumber → Tesseract OCR) is not tested.
- **Streaming SSE endpoint** (`POST /query/stream`) — noted in `app/routers/CLAUDE.md` as having duplicated enrichment logic; not tested.
- **Auth flows** — `app/core/auth_deps.py` dependency chain not tested.

---

## CI/CD

No `.github/` directory exists — there is no CI pipeline configured. Tests are run manually only.

**Pre-push checklist** (from `CLAUDE.md`) is a manual human process, not automated.
