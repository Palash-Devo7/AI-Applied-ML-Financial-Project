# QuantCortex — Project Journey

**Author:** Palash Joshi
**Live Product:** [quantcortex.in](https://quantcortex.in)
**GitHub:** https://github.com/Palash-Devo7/AI-Applied-ML-Financial-Project
**Duration:** March 2026 (ongoing)
**Stack:** Python 3.12 · FastAPI · FinBERT · ChromaDB · Groq (LLaMA 3.3 70B) · Tesseract OCR · Next.js 15 · SQLite · BSE India

---

## Table of Contents

1. [Project Goal](#1-project-goal)
2. [Initial Strategy & Architecture Decisions](#2-initial-strategy--architecture-decisions)
3. [System Architecture](#3-system-architecture)
4. [Phase-by-Phase Build Log](#4-phase-by-phase-build-log)
5. [Challenges & Solutions](#5-challenges--solutions)
6. [LLM Provider Journey](#6-llm-provider-journey)
7. [OCR Journey](#7-ocr-journey)
8. [Retrieval Quality Issues & Fixes](#8-retrieval-quality-issues--fixes)
9. [Streamlit UI Layer](#9-streamlit-ui-layer)
10. [Financial Forecasting Vision](#10-financial-forecasting-vision)
11. [Phase A: Historical Data Layer](#11-phase-a-historical-data-layer)
12. [Production Readiness Checklist](#12-production-readiness-checklist)
13. [Current System Capabilities](#13-current-system-capabilities)
14. [File Structure](#14-file-structure)
15. [Key Design Patterns](#15-key-design-patterns)
16. [Lessons Learned](#16-lessons-learned)
17. [Next.js Frontend — Full Rebuild](#17-nextjs-frontend--full-rebuild)
18. [Security Layer — Production Auth](#18-security-layer--production-auth)
19. [Production Deployment](#19-production-deployment)
20. [Vision: Market Impact Propagation System](#20-vision-market-impact-propagation-system)
21. [Email Verification & Auth Hardening](#21-email-verification--auth-hardening)

---

## 1. Project Goal

Build a **Finance AI RAG (Retrieval-Augmented Generation) system** that:

- Accepts financial PDF documents (annual reports, 10-Ks, balance sheets, earnings reports)
- Extracts, chunks, and embeds them using a finance-specialized model (FinBERT)
- Answers natural language questions about those documents using an LLM
- Supports multiple companies in a single knowledge base with company-level filtering
- Is production-observable (structured logs, Prometheus metrics, Grafana dashboards)
- Is extensible to fine-tuned models in Phase 2

**Target users:** Financial analysts, investors, students analyzing company performance without reading hundreds of pages manually.

---

## 2. Initial Strategy & Architecture Decisions

### Why RAG instead of fine-tuning?

Fine-tuning bakes knowledge into model weights — it's expensive, slow, and goes stale. RAG retrieves live data from documents at query time. For financial documents that change every quarter, RAG is the right choice.

### Key architecture decisions made upfront:

| Decision | Choice | Reason |
|---|---|---|
| Embedding model | ProsusAI/finbert | Finance-domain-specific BERT. Better semantic understanding of terms like "EBITDA", "amortization", "diluted EPS" than generic embeddings |
| Vector DB | ChromaDB (persistent) | Local-first, no external service, cosine similarity, metadata filtering support |
| Retrieval strategy | Hybrid (Vector + BM25 + RRF) | Pure vector misses exact financial terms. BM25 catches keyword matches. RRF (Reciprocal Rank Fusion) combines both scores |
| LLM | Pluggable via Protocol | Don't lock into one provider — swap Claude / DeepSeek / Groq / fine-tuned model via config |
| Async safety | run_in_threadpool + asyncio.Lock | ChromaDB and FinBERT are synchronous. Wrapping prevents event loop blocking |
| Chunking | Section-aware + recursive | Financial docs have logical sections (Balance Sheet, Risk Factors). Keep related text together |
| Monitoring | structlog + Prometheus + Grafana | JSON logs for parsing, metrics for alerting, dashboards for visibility |

### Retrieval pipeline design (RRF explained):

```
Query
  │
  ├── FinBERT embed → ChromaDB vector search → top-N by cosine similarity
  │
  └── BM25 sparse search → keyword scoring over stored documents

Both results → Reciprocal Rank Fusion (alpha=0.7 vector weight)
             → Re-ranked unified list
             → Top-K chunks sent to LLM
```

RRF formula: `score = alpha * (1/(rank_vector + 60)) + (1-alpha) * (1/(rank_bm25 + 60))`

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI (port 8000)                         │
│                                                                     │
│  POST /documents/upload    POST /query    GET /collections/*        │
│          │                      │                                   │
│          ▼                      ▼                                   │
│  IngestionService         QueryService                              │
│          │                      │                                   │
│    ┌─────▼─────┐         ┌──────▼──────────────────┐               │
│    │DocumentParser│      │MCPService                │               │
│    │ pypdf      │        │ - classify_query()       │               │
│    │ pdfplumber │        │ - extract_entities()     │               │
│    │ Tesseract  │        │ - build_metadata_filter()│               │
│    │   OCR      │        │ - assemble_context()     │               │
│    └─────┬─────┘        └──────┬───────────────────┘               │
│          │                     │                                    │
│    FinancialChunker      EmbeddingService (FinBERT)                 │
│    (section-aware)       (ThreadPoolExecutor)                       │
│          │                     │                                    │
│    EmbeddingService            │                                    │
│    (FinBERT)                   ▼                                    │
│          │              RetrievalService                            │
│          │              (Vector + BM25 + RRF)                      │
│          ▼                     │                                    │
│    ChromaDB (persistent)◄──────┘                                   │
│    ./data/chroma_db/            │                                   │
│                                 ▼                                   │
│                         GenerationService                           │
│                         ┌──────────────┐                           │
│                         │ GroqBackend  │ ← default (free)          │
│                         │ DeepSeekBknd │ ← optional                │
│                         │ ClaudeBackend│ ← optional                │
│                         │ FineTunedBknd│ ← Phase 2 stub            │
│                         └──────────────┘                           │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
  Monitoring Stack
  structlog (JSON) → stdout
  Prometheus → /metrics
  Grafana → dashboards
```

---

## 4. Phase-by-Phase Build Log

### Phase 1: Core Infrastructure (Session 1)

Built all 58 files from scratch:

**Config & DI:**
- `app/config.py` — Pydantic BaseSettings reading from `.env`, `@lru_cache` singleton
- `app/dependencies.py` — FastAPI dependency injection, all singletons via `@lru_cache`

**Core processing:**
- `app/core/document_parser.py` — PDF text extraction (pypdf → pdfplumber fallback)
- `app/core/chunker.py` — Section-aware chunking (SEC headers) + recursive 480-token splits
- `app/core/metadata_extractor.py` — Auto-extract company, year, report type from text/filename
- `app/core/vector_store.py` — Async-safe ChromaDB wrapper
- `app/core/prompts.py` — System prompt + per-query-type user prompts

**Services:**
- `app/services/embedding_service.py` — FinBERT inference, lazy torch imports, ThreadPoolExecutor
- `app/services/ingestion_service.py` — Full pipeline: parse → chunk → embed → upsert
- `app/services/retrieval_service.py` — Hybrid vector + BM25 + RRF retrieval
- `app/services/mcp_service.py` — Query classification, entity extraction, context assembly
- `app/services/generation_service.py` — ModelBackend Protocol, Claude/DeepSeek/Groq backends
- `app/services/query_service.py` — End-to-end query orchestration

**API:**
- `app/routers/health.py`, `ingestion.py`, `query.py`, `collections.py`

**Monitoring:**
- `app/monitoring/logger.py` — structlog JSON configuration
- `app/monitoring/metrics.py` — 11 Prometheus custom metrics
- `app/monitoring/middleware.py` — Request logging middleware with request_id

**Models:**
- `app/models/documents.py`, `queries.py`, `monitoring.py` — Pydantic response models

**Phase 2 stubs (not yet implemented):**
- `app/phase2/fine_tuning/lora_trainer.py`
- `app/phase2/fine_tuning/dataset_builder.py`
- `app/phase2/fine_tuning/model_registry.py`
- `app/phase2/evaluation/rag_evaluator.py`

**Infrastructure:**
- `docker/Dockerfile` — Multi-stage build (builder + slim runtime, non-root user)
- `docker/docker-compose.yml` — API + Prometheus + Grafana services
- `monitoring/prometheus.yml`, Grafana dashboard JSON
- `requirements.txt`, `requirements-dev.txt`, `.env.example`, `README.md`

**Tests:** 43/43 passing (unit + integration)

---

### Phase 2: Testing & Bug Fixes (Session 1 continued)

Ran full test suite, found and fixed 5 bugs:

| Bug | Root Cause | Fix |
|---|---|---|
| `test_classify_historical_query` failed | "trend in revenue" scored tie 1-1 between HISTORICAL and REVENUE types; REVENUE won due to dict ordering | Added stronger HISTORICAL keywords: "over the last", "over the past", "last 3 years", "multi-year", "long-term trend" |
| `test_filename_year_fallback` failed | `\b` word boundary in regex fails on underscores — `report_2021.pdf` has no boundary between `_` and `2` | Used plain `re.search(r"(20[0-2]\d)", filename)` in `_year_from_filename()` |
| Integration tests wouldn't collect | `import torch` at module level in `embedding_service.py` — crashed import without torch installed | Moved torch/numpy imports inside method bodies (lazy imports) |
| `ModuleNotFoundError: python_ulid` | Package `python-ulid` imports as `ulid`, not `python_ulid` | Changed `from python_ulid import ULID` → `from ulid import ULID` everywhere |
| `test_ingestion_returns_upload_response` failed | Mock text was 60 chars; ingestion guard requires `total_chars > 100` | Increased mock text to 156 chars |

---

### Phase 3: GitHub Push (Session 1 continued)

First-time GitHub push for the user. Steps taken:
1. `git init` in project directory
2. `git config user.name / user.email`
3. `git remote add origin https://github.com/Palash-Devo7/AI-Applied-ML-Financial-Project.git`
4. `git pull --allow-unrelated-histories` — GitHub had auto-generated README, caused conflict
5. Resolved conflict: `git checkout --ours README.md` (kept our detailed README)
6. `git add . && git commit && git push`

---

### Phase 4: Local Testing Setup (Session 2)

First attempt to run the server revealed two issues:

**Issue 1: ChromaDB incompatible with Python 3.14**
- Error: `unable to infer type for attribute "chroma_server_nofile"`
- Root cause: ChromaDB 0.6.3 uses `pydantic.v1` internally, which doesn't support Python 3.14
- Fix: Upgraded to `chromadb==1.5.5` which uses native Pydantic V2

**Issue 2: `/docs` returning 404**
- Root cause: `docs_url="/docs" if settings.debug else None` — docs disabled because `DEBUG=false` in `.env`
- Fix: Set `DEBUG=true` in `.env`

---

### Phase 5: OCR Support (Session 2)

The test PDF (Tata Steel FY25 Integrated Report) was **image-based** — scanned pages with no text layer. Both pypdf and pdfplumber returned 0 chars.

**Solution:** Added Tesseract OCR as third fallback in `document_parser.py`:

```
pypdf → pdfplumber → Tesseract OCR (via pymupdf page rendering)
```

Flow for image PDFs:
1. `fitz` (PyMuPDF) renders each page as an image at 2x zoom
2. `pytesseract` runs OCR on each image
3. Text assembled back into `ParsedPage` objects
4. Normal chunking + embedding pipeline continues

**Packages added:** `pymupdf`, `pytesseract`, `pillow`
**System dependency:** Tesseract OCR v5.5.0 (Windows installer)

**Performance issue discovered:** OCR on a 200-page PDF takes 10-15 minutes. Browser/Swagger UI timed out, making uploads appear to fail.

**Fix:** Converted ingestion to **async background task**:
- `POST /documents/upload` returns immediately with `{document_id, status: "processing"}`
- Actual OCR + embedding runs in background via FastAPI `BackgroundTasks`
- New endpoints: `GET /documents/{document_id}/status`, `GET /documents/jobs`

---

### Phase 6: LLM Provider Switches (Sessions 1-3)

Three LLM providers used in sequence:

| Provider | Reason for switch | Cost |
|---|---|---|
| Claude (Anthropic) | Initial provider | Expensive |
| DeepSeek | Cost savings (~40x cheaper) | Low paid |
| Groq | DeepSeek subscription issues | **Free tier** |

See [Section 6](#6-llm-provider-journey) for full technical details.

---

### Phase 7: Multi-Company Retrieval Fix (Session 3)

**Problem:** Uploaded two companies' documents. Querying company A returned data from company B.

**Root cause:** The entity extraction (`mcp_service.py`) only recognized a hardcoded list of US companies (Apple, Microsoft, Google, etc.). "Tata Steel" was not in the list, so no metadata filter was applied — ChromaDB returned chunks from all companies mixed together.

**Fixes applied:**
1. Added top-level `company` field to `QueryRequest` model (visible in Swagger UI)
2. Query service uses this field as an explicit metadata filter bypassing entity extraction
3. Added `GET /collections/companies` endpoint to see exact stored company names
4. Company filter applied as `{"company": {"$eq": "Tata Steel"}}` in ChromaDB where-clause

**Usage:** In `POST /query`, pass `"company": "Tata Steel"` alongside your question.

---

### Phase 8: Streamlit UI Layer (Session 4)

**Motivation:** The system was API-only (Swagger UI). A proper interface was needed to make the tool usable by non-technical analysts.

**Choice:** Streamlit over React/Next.js — pure Python, no HTML/CSS/JS, built-in file uploader and chat interface, deployable in hours.

**Initial build:** Three-page dark-themed app:
- 💬 Chat — natural language Q&A with company filter and source citations
- 📁 Upload — PDF drag & drop with metadata form and job status tracker
- 🏢 Knowledge Base — company/document browser with stats and danger zone

**Problems found immediately after first launch:**
1. **Bland white UI** — default Streamlit theme looked unprofessional
2. **Laggy** — API calls (`fetch_companies`, `fetch_collection_info`) ran on every page re-render
3. **3+ second response delay** — LLM generated the full answer server-side before sending anything to UI

**Fix 1 — Dark professional theme:** Full CSS override injected via `st.markdown()` — dark navy background (`#0f1117`), blue accent (`#3b82f6`), styled chat bubbles, source cards, metric tiles.

**Fix 2 — Caching API calls:** Wrapped `fetch_companies()` and `fetch_collection_info()` with `@st.cache_data(ttl=30)` — eliminates repeated network calls on every render cycle.

**Fix 3 — Streaming responses (biggest change):**

Backend changes:
- Added `stream_generate()` async generator to `GroqBackend` and `DeepSeekBackend` using `stream=True` in the OpenAI client
- Added `stream_generate()` to `GenerationService` with graceful fallback for backends that don't support streaming
- Added `POST /query/stream` FastAPI endpoint using `StreamingResponse` with Server-Sent Events (SSE) format

SSE event format:
```
data: {"type": "meta", "query_type": "REVENUE", "chunk_count": 5, "sources": [...]}
data: {"type": "token", "text": "Tata"}
data: {"type": "token", "text": " Steel"}
...
data: {"type": "done"}
```

The `meta` event carries sources and query metadata and is sent **before** tokens start — so the UI knows context before the answer arrives.

Frontend changes:
- `stream_query()` generator in `ui/app.py` — opens SSE connection with `requests.post(..., stream=True)` and yields `(token, meta)` tuples
- `st.write_stream()` consumes the generator and renders tokens as they arrive — identical UX to ChatGPT/Claude

**Python 3.14 bug:** `nonlocal` inside a nested function within an `if` block is illegal in Python 3.14. Used a mutable `state = {}` dict instead to share data between the generator closure and outer scope.

**Result:** First token appears in ~1 second (retrieval time). Answer streams word by word. Sources appear after streaming completes.

---

## 5. Challenges & Solutions

### Challenge 1: Python 3.14 Compatibility

Python 3.14 is very new (2025). Several packages broke:

| Package | Issue | Resolution |
|---|---|---|
| ChromaDB 0.6.3 | Uses `pydantic.v1` — not compatible with Python 3.14 | Upgraded to chromadb 1.5.5 |
| torch | CPU wheels available | Installed CPU-only torch 2.5.1 |
| transformers | Worked with minor warnings | Used as-is |

**Lesson:** When using bleeding-edge Python, always verify all key dependencies have updated wheels.

---

### Challenge 2: Image-Based PDFs

Most real-world financial reports (especially scanned or older reports) have no text layer. This made the entire system unusable for real documents.

**Three-layer parsing strategy:**
```
Layer 1: pypdf — fast, handles text-layer PDFs
Layer 2: pdfplumber — better layout handling, tables
Layer 3: Tesseract OCR — for pure image PDFs (slow, CPU-intensive)
```

Each layer runs only if the previous extracted < 50 chars/page.

**Remaining gap:** Tesseract struggles with complex financial tables. Numbers in multi-column layouts often get merged. Cloud OCR (Google Document AI, AWS Textract) would handle this better for production.

---

### Challenge 3: Synchronous OCR Blocking Async Server

FastAPI is async-first. OCR with Tesseract is CPU-bound and takes minutes. Running it in the async event loop would block all other requests.

**Solution:**
- OCR runs in FastAPI `BackgroundTasks` (separate thread, non-blocking)
- Endpoint returns `202 Accepted` immediately
- Client polls `GET /documents/{id}/status` for completion

---

### Challenge 4: Company Isolation in Shared Collection

All documents live in one ChromaDB collection. Without filtering, a query for Company A retrieves chunks from Company B.

**Design choice:** One collection with metadata filtering (not one collection per company).

**Why:** ChromaDB's metadata `where` clause (`{"company": {"$eq": "..."}}`) is efficient. Separate collections would require routing logic and make cross-company comparison impossible.

**Remaining gap:** Company name must match exactly. "Tata Steel" ≠ "TATA STEEL". Future fix: normalize company names to lowercase at ingest time.

---

### Challenge 5: Retrieval Missing Data That Exists in Documents

The 44-page Tata Steel report contained assets data but the system said "no data available."

**Root causes identified:**
1. `top_k=5` was too low — asset data was ranked 8th-10th due to vector similarity competition
2. Section boundary patterns were US-centric (SEC format) — Indian report sections like "Balance Sheet", "Statement of Assets" weren't recognized as section boundaries, so they weren't chunked as separate sections
3. Table data from OCR is noisy — numbers lose context when column structure is lost

**Fixes:**
1. Increased default `top_k` from 5 to 10, max from 20 to 50
2. Added Indian/general financial report section patterns: Balance Sheet, Statement of Profit and Loss, Cash Flow Statement, Directors Report, Auditors Report, EBITDA, Financial Summary, etc.
3. Improved chunk separators to prefer paragraph/sentence boundaries over word boundaries

---

## 6. LLM Provider Journey

### ModelBackend Protocol Design

From the start, the LLM was abstracted behind a Protocol:

```python
@runtime_checkable
class ModelBackend(Protocol):
    async def generate(
        self, question: str, context: str, query_type: str
    ) -> tuple[str, TokenUsageDetail]: ...
```

This meant swapping providers required zero changes to the query pipeline — only `GenerationService.__init__` needed updating.

### Provider 1: Claude (Anthropic)

- Used `anthropic` SDK
- `claude-sonnet-4-6` model
- Expensive for development — not sustainable for testing

### Provider 2: DeepSeek

- Uses `openai` SDK with `base_url="https://api.deepseek.com"`
- Model: `deepseek-chat`
- ~40x cheaper than Claude
- Subscription issues encountered during testing

### Provider 3: Groq (current default)

- Uses `openai` SDK with `base_url="https://api.groq.com/openai/v1"`
- Model: `llama-3.3-70b-versatile`
- **Free tier** — no cost for development
- Very fast inference (one of the fastest providers)
- Excellent for financial Q&A

### Switching providers

Edit `.env`:
```env
LLM_PROVIDER=groq        # or deepseek, claude
GROQ_API_KEY=gsk_...
```
Restart server. No code changes needed.

---

## 7. OCR Journey

### Why OCR was needed

Real financial PDFs are often scanned documents or reports exported from presentation software — they contain images of text, not actual text characters.

### Implementation

```python
def _try_ocr(self, content: bytes):
    import fitz           # PyMuPDF: renders PDF pages as images
    import pytesseract    # Tesseract OCR wrapper

    pdf = fitz.open(stream=content, filetype="pdf")
    for page in pdf:
        mat = fitz.Matrix(2.0, 2.0)      # 2x zoom for better accuracy
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text = pytesseract.image_to_string(img, lang="eng")
```

### Performance characteristics

| PDF type | Parser used | Time (44 pages) |
|---|---|---|
| Text-layer PDF | pypdf | < 1 second |
| Complex layout | pdfplumber | 2-5 seconds |
| Image/scanned | Tesseract OCR | 10-20 minutes |

### Known OCR limitations

- **Tables**: Column structure is lost — "45,230 | 41,100" becomes "45,230 41,100" or worse
- **Headers/footers**: Repetitive boilerplate appears in every chunk
- **Multi-column layouts**: Text from adjacent columns gets merged
- **Low resolution scans**: Accuracy drops significantly

### Production recommendation

For production scale, replace/supplement Tesseract with:
- **Google Document AI** — best table extraction, form understanding
- **AWS Textract** — strong for financial forms, structured data
- **Azure Document Intelligence** — good for mixed content

---

## 8. Retrieval Quality Issues & Fixes

### How retrieval works

```
Question → FinBERT embed → ChromaDB cosine search → top-N×2 candidates
                                                            │
Question (raw text) → BM25 score over stored documents ───┘
                                                            │
                              Reciprocal Rank Fusion (α=0.7)
                                                            │
                              Top-K chunks → LLM context
```

### Issues encountered

**Issue 1: Wrong company data returned**
- Cause: No company filter applied (entity extraction didn't know Tata Steel)
- Fix: Added explicit `company` field to query API

**Issue 2: Asset data not found in 44-page report**
- Cause: top_k=5, Indian section headers not recognized, OCR table noise
- Fix: top_k=10 default, added 20+ Indian financial section patterns

**Issue 3: Context window overflow**
- Protection: Context trimmed at 6000 tokens (configurable via `MAX_CONTEXT_TOKENS`)
- Chunks sorted by score DESC then year DESC before trimming

**Issue 4: Duplicate chunks**
- Protection: Jaccard similarity deduplication (threshold 0.8) before context assembly

---

## 9. Streamlit UI Layer

### Architecture

```
Browser (http://localhost:8501)
        │
   Streamlit UI (ui/app.py)
        │  HTTP requests (requests library)
        │  SSE stream (requests stream=True)
        ▼
FastAPI Backend (http://localhost:8000)
```

Two processes run independently. The UI is a thin client — all intelligence stays in the FastAPI backend.

### Pages

**💬 Chat**
- Company filter dropdown (auto-populated from `/collections/companies`)
- Top K slider (1-50, default 10)
- Sources toggle
- Chat history with message persistence via `st.session_state`
- Streaming responses via `st.write_stream()`
- Source cards shown after streaming with score, company, section, page number
- Query metadata footer (query type, chunk count, latency)

**📁 Upload**
- PDF drag & drop via `st.file_uploader`
- Metadata form: company (required), year, ticker, report type, sector
- Calls `POST /documents/upload` → returns immediately (background task)
- Job status panel showing all uploads with live status (🔄/✅/❌)
- Refresh button to poll job completion

**🏢 Knowledge Base**
- Three metrics: total chunks, companies, documents (ingested/total)
- Company cards with chunk counts
- Document list with full metadata
- Danger zone: delete entire collection (requires typing "DELETE")

### Streaming Implementation

```python
# Backend: SSE endpoint (query.py)
async def event_generator():
    # 1. Retrieve (fast) — happens before first token
    chunks = await retrieval.hybrid_query(...)
    context, used_chunks = mcp.assemble_context(chunks)

    # 2. Send metadata event first
    yield f"data: {json.dumps({'type': 'meta', 'sources': [...], ...})}\n\n"

    # 3. Stream tokens
    async for token in generation.stream_generate(...):
        yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"

# Frontend: consume stream (app.py)
def stream_query(payload):
    with requests.post("/query/stream", json=payload, stream=True) as resp:
        for line in resp.iter_lines():
            data = json.loads(line[6:])          # strip "data: "
            if data["type"] == "token":
                yield data["text"], meta

st.write_stream(token_generator())               # renders tokens live
```

### Performance improvements

| Metric | Before | After |
|---|---|---|
| Time to first token | 3-5 seconds | ~1 second |
| Full answer display | 3-5 seconds | Streams progressively |
| Page render API calls | Every render (laggy) | Cached 30s TTL |
| Theme | Default white | Dark navy professional |

### Known Streamlit limitations

- **No WebSocket** — SSE over HTTP polling, minor overhead vs native WebSocket
- **Session state** — Chat history lives in browser session, lost on refresh
- **Single thread** — Streamlit re-runs entire script on interaction; state management via `st.session_state`
- **`nonlocal` in Python 3.14** — Can't use `nonlocal` in nested functions inside `if` blocks; workaround: mutable `state = {}` dict

---

## 10. Financial Forecasting Vision

### Inspiration: MiroFish

During Session 5, we studied [MiroFish](https://github.com/666ghj/MiroFish) — a swarm intelligence prediction engine with 26,500+ GitHub stars. It spawns thousands of autonomous agents with persistent memory to simulate outcomes from seed data (news, financial signals, policy docs).

**Key insight:** MiroFish uses the same underlying ingredients we can use — OASIS (Apache 2.0), Zep Cloud (free tier), OpenAI-compatible SDK. MiroFish itself is AGPL-3.0 (cannot be used in a product without open-sourcing everything), but we can build the same architecture independently.

### Our Forecasting Roadmap

Rather than generic simulation, we build a **financially-tuned forecasting engine** in three phases:

```
Phase A — Historical Data Layer (COMPLETE ✅)
  Real quantitative data (revenue, EPS, stock prices) from yfinance
  Structured SQLite DB alongside ChromaDB vector store
  Auto-injected into every RAG query as grounding context

Phase B — Multi-Agent Forecasting (NEXT)
  4-5 specialist analyst agents (bull, bear, macro, sector, quant)
  Each sees the same context, produces independent forecast
  Synthesis agent combines views into final structured report
  New endpoint: POST /forecast/event

Phase C — GraphRAG (FUTURE)
  Knowledge graph of company relationships (competitors, suppliers, sectors)
  Graph traversal for richer, more precise context assembly
  Libraries: NetworkX (local) or Neo4j (scale)
```

### Why Sequential Phases Matter

```
Without Phase A:
  Agent: "Historically, steel dumping causes margin compression"
  (generic, no numbers)

With Phase A:
  Agent: "In FY2024 Tata Steel posted a net loss of ₹4,437 Cr.
          FY2022 was the peak at ₹40,154 Cr net income.
          Stock fell from ₹216 to ₹122 over the past year."
  (specific, credible, useful for forecasting)
```

---

## 11. Phase A: Historical Data Layer

**Completed:** Session 5 (March 2026)

### What was built

3 new files, 3 modified files:

| File | Purpose |
|---|---|
| `app/data/financial_db.py` | SQLite manager — 4 tables: financials, stock prices, events, ticker map |
| `app/services/market_data_service.py` | yfinance integration — fetch annual/quarterly financials + OHLCV prices |
| `app/routers/market_data.py` | REST API — fetch, query, and manage market data + events |

**Modified:**
- `app/services/query_service.py` — enriches RAG context with structured financial table
- `app/routers/query.py` — same enrichment added to streaming endpoint
- `app/main.py` — initialises SQLite DB on startup, registers market_data router

### Database Schema

```sql
company_financials  — revenue, net_income, ebitda, eps, assets, debt per year/quarter
stock_prices        — OHLCV daily prices per ticker
events              — manually logged financial events with impact scores (-1 to +1)
ticker_map          — company name → exchange ticker (e.g. "Tata Steel" → "TATASTEEL.NS")
```

### How context enrichment works

```
User query: "What was Tata Steel's revenue trend?"

Step 1: ChromaDB retrieves PDF chunks (qualitative — management commentary, risks)
Step 2: SQLite looks up "Tata Steel" → fetches 5 years of financials + stock summary
Step 3: Structured table prepended to LLM context:

=== STRUCTURED FINANCIAL DATA: TATA STEEL ===
ANNUAL FINANCIALS:
Year     Revenue         Net Income      EBITDA          EPS     Net Margin
2025     216840Cr        3420Cr          ...             ...     1.6%
2024     227296Cr        -4437Cr (LOSS)  ...             ...     -1.9%
2023     241636Cr        8760Cr          ...             ...     3.6%
2022     242326Cr        40154Cr         ...             ...     16.6%

STOCK (TATASTEEL.NS):
  Latest close : ₹183.01 (2026-03-13)
  52-week range: ₹122.44 – ₹216.45
=== END STRUCTURED DATA ===

Step 4: LLM answers with real numbers, not just PDF text
```

### New API endpoints

```
POST /market/fetch/sync    — fetch financials + prices for a ticker (waits for completion)
POST /market/fetch         — same but background (returns immediately)
GET  /market/financials/{company}       — get annual history
GET  /market/financials/{company}/quarterly
GET  /market/stock/{ticker}             — OHLCV history
GET  /market/stock/{ticker}/summary     — 52-week range + latest close
POST /market/events                     — manually log a financial event
GET  /market/events/{company}           — get event history
GET  /market/events/similar/{type}      — find analogous events across companies
GET  /market/tickers                    — list all registered company→ticker mappings
```

### Tata Steel data loaded (verified)

```
Annual records: 5
2025  Revenue: ₹2.17L Cr   Net Income: ₹3,420 Cr
2024  Revenue: ₹2.27L Cr   Net Income: -₹4,437 Cr  ← Net loss year
2023  Revenue: ₹2.42L Cr   Net Income: ₹8,760 Cr
2022  Revenue: ₹2.42L Cr   Net Income: ₹40,154 Cr  ← Peak profit year
2021  No data (yfinance gap)

Stock: ₹183 latest · 52-week ₹122–₹216
```

### Bug found and fixed

The streaming endpoint (`POST /query/stream`) had its own inline pipeline that bypassed `query_service.py`. The structured context enrichment was added to `query_service.py` but the UI uses the stream endpoint — so the fix had to be applied to `query.py` as well.

**Lesson:** When you have two code paths doing the same thing (query vs stream), both must be updated. Consider refactoring into a shared `_build_context()` helper in Phase B.

---



### Must-have before launch

- [ ] **API Authentication** — API keys or JWT on every endpoint
- [ ] **Rate limiting** — max requests/min per user to prevent abuse
- [ ] **Set DEBUG=false** — disables `/docs` exposure in production
- [ ] **Persistent storage** — ChromaDB on a proper volume (not local disk)
- [ ] **OCR job queue** — Replace BackgroundTasks with Celery + Redis for reliability
- [ ] **Error alerting** — Prometheus alerts on error rates, LLM failures

### Nice-to-have

- [ ] **Query caching** — Redis cache for repeated identical questions
- [ ] **Multi-worker** — `API_WORKERS=4` for concurrent requests
- [ ] **GPU for embeddings** — `EMBEDDING_DEVICE=cuda` for 10x faster FinBERT
- [ ] **Cloud OCR** — Replace Tesseract with Google Document AI for tables
- [ ] **Company name normalization** — Lowercase all company names at ingest + query time
- [ ] **Document versioning** — Track when documents are updated/re-ingested

### Scalability numbers

| Metric | Current (dev) | Production target |
|---|---|---|
| Documents | Unlimited | Unlimited |
| Chunks stored | ~1M comfortable | 10M+ with RAM |
| RAM per 1M chunks | ~3 GB | Scale horizontally |
| Concurrent queries | 1 worker | 4-8 workers |
| Embedding speed | ~50 chunks/sec (CPU) | ~500/sec (GPU) |
| OCR speed | 1 page/5 sec | Use cloud API |

---

## 11. Current System Capabilities

### What works today

✅ Upload any financial PDF (text or image/scanned)
✅ Automatic OCR fallback for image PDFs
✅ Async background ingestion (no timeout for large files)
✅ Query ingestion job status
✅ Natural language Q&A over financial documents
✅ Streaming responses — token-by-token like ChatGPT
✅ Company-level filtering (ask about specific company only)
✅ Hybrid retrieval (vector + BM25 + RRF)
✅ 6 query types: RISK, REVENUE, MACRO, COMPARATIVE, HISTORICAL, GENERAL
✅ Source citations in every answer with score + page reference
✅ Multiple LLM backends (Groq/DeepSeek/Claude) switchable via `.env`
✅ Streamlit UI — industrial dark theme, three pages, streaming chat
✅ Prometheus metrics + Grafana dashboards
✅ JSON structured logging
✅ Historical financials from yfinance (revenue, EPS, net income, assets)
✅ Stock price history + 52-week summary per ticker
✅ Structured financial data auto-injected into every RAG query
✅ Manual event logging (earnings, macro events, regulatory changes)
✅ Analogous event lookup across companies for forecasting

### What doesn't work yet

❌ Table data extraction is unreliable (OCR noise)
❌ Company name matching is case-sensitive and exact
❌ No authentication — anyone can access the API
❌ No rate limiting
❌ OCR jobs lost on server restart (in-memory job tracker)
❌ Chat history lost on Streamlit page refresh
❌ Multi-agent forecasting not yet built (Phase B)
❌ GraphRAG not yet built (Phase C)
❌ Phase 2 fine-tuning not implemented

---

## 11. File Structure

```
finance-rag/
├── app/
│   ├── config.py                   # Pydantic settings, @lru_cache singleton
│   ├── dependencies.py             # FastAPI DI providers, all singletons
│   ├── main.py                     # App factory, lifespan, routers, middleware
│   ├── core/
│   │   ├── chunker.py              # Section-aware + recursive chunking
│   │   ├── document_parser.py      # pypdf → pdfplumber → Tesseract OCR
│   │   ├── metadata_extractor.py   # Auto-extract company, year, report type
│   │   ├── prompts.py              # SYSTEM_PROMPT, per-query-type prompts
│   │   └── vector_store.py         # Async-safe ChromaDB wrapper
│   ├── models/
│   │   ├── documents.py            # UploadResponse, DocumentMetadata
│   │   ├── queries.py              # QueryRequest, QueryResponse, RetrievedChunk
│   │   └── monitoring.py           # Health check models
│   ├── monitoring/
│   │   ├── logger.py               # structlog JSON configuration
│   │   ├── metrics.py              # 11 Prometheus custom metrics
│   │   └── middleware.py           # Request logging, request_id binding
│   ├── phase2/
│   │   ├── fine_tuning/
│   │   │   ├── lora_trainer.py     # Stub: LoRA fine-tuning trainer
│   │   │   ├── dataset_builder.py  # Stub: JSONL → training dataset
│   │   │   └── model_registry.py   # Stub: model versioning
│   │   └── evaluation/
│   │       └── rag_evaluator.py    # Stub: RAGAS metrics evaluation
│   ├── data/
│   │   └── financial_db.py         # SQLite manager — financials, prices, events, ticker map
│   ├── routers/
│   │   ├── health.py               # GET /health
│   │   ├── ingestion.py            # POST /documents/upload, GET /documents/{id}/status
│   │   ├── query.py                # POST /query, POST /query/stream (SSE)
│   │   ├── collections.py          # GET /collections, /collections/companies
│   │   └── market_data.py          # GET/POST /market/* — financials, stock, events
│   └── services/
│       ├── embedding_service.py    # FinBERT inference, ThreadPoolExecutor
│       ├── generation_service.py   # ModelBackend Protocol, Groq/DeepSeek/Claude
│       ├── ingestion_service.py    # parse → chunk → embed → upsert pipeline
│       ├── market_data_service.py  # yfinance integration, async wrappers
│       ├── mcp_service.py          # Classify, extract entities, build filters, assemble context
│       ├── query_service.py        # End-to-end query orchestration + structured context enrichment
│       └── retrieval_service.py    # Hybrid vector + BM25 + RRF
├── tests/
│   ├── conftest.py                 # Shared fixtures, mocks
│   ├── unit/                       # Pure Python, no external services (43 tests)
│   └── integration/                # Mock embedding/vector/LLM
├── docker/
│   ├── Dockerfile                  # Multi-stage: builder + slim runtime
│   └── docker-compose.yml          # API + Prometheus + Grafana
├── monitoring/
│   ├── prometheus.yml              # Scrape config
│   └── grafana_dashboard.json      # Pre-built dashboard
├── ui/
│   ├── app.py                      # Streamlit UI — Chat, Upload, Knowledge Base pages
│   └── .streamlit/
│       └── config.toml             # Dark theme, port 8501, no telemetry
├── data/
│   └── chroma_db/                  # Persistent vector store (gitignored)
├── .env                            # Active config (gitignored)
├── .env.example                    # Template for new setups
├── requirements.txt                # Production dependencies
├── requirements-dev.txt            # pytest, coverage, etc.
├── PROJECT_JOURNEY.md              # This document
└── README.md                       # Setup and usage guide
```

---

## 12. Key Design Patterns

### 1. ModelBackend Protocol (runtime swappable LLM)

```python
@runtime_checkable
class ModelBackend(Protocol):
    async def generate(self, question, context, query_type) -> tuple[str, TokenUsageDetail]: ...

# GenerationService picks backend at init time based on config
if llm_provider == "groq":
    self._backend = GroqBackend(...)
elif llm_provider == "claude":
    self._backend = ClaudeBackend(...)
else:
    self._backend = DeepSeekBackend(...)
```

New backends (fine-tuned models, other APIs) slot in without touching the query pipeline.

### 2. Async-safe ChromaDB

ChromaDB is synchronous. All calls wrapped in `run_in_threadpool()`. Write operations additionally protected with `asyncio.Lock()` to prevent concurrent write corruption.

### 3. Lazy imports for heavy dependencies

```python
def _load_model(self):
    import torch                          # Only imported when actually needed
    from transformers import AutoModel    # Prevents test collection failures
```

### 4. @lru_cache singletons

FinBERT loads once at startup (~440MB). All services are singletons — not re-created per request.

### 5. Three-layer PDF parsing

```
pypdf (fast) → pdfplumber (better layout) → Tesseract OCR (images)
```
Each layer only activates if the previous returned insufficient text.

### 6. MCP (Model Context Protocol) layer

Sits between retrieval and generation:
- **classify_query()** → one of 6 types (RISK, REVENUE, MACRO, COMPARATIVE, HISTORICAL, GENERAL)
- **extract_entities()** → company, ticker, year, quarter from question text
- **build_metadata_filters()** → ChromaDB where-clause from entities
- **assemble_context()** → deduplicate chunks (Jaccard), trim to token limit, format citations

---

## 13. Lessons Learned

1. **Python version matters** — Python 3.14 broke ChromaDB, which required an upgrade to 1.5.5. Always check package compatibility matrices before choosing runtime versions.

2. **Real-world PDFs are messy** — Every financial document encountered was image-based. Building only text-layer PDF support would have made the system useless in practice.

3. **Synchronous ops in async servers need care** — OCR + embedding are both CPU-bound. Without `run_in_threadpool` and `BackgroundTasks`, the server would freeze on every upload.

4. **Hardcoded entity lists don't scale** — Building a company name extractor with a fixed list of US companies was a design mistake. It worked for demos but broke immediately on real data (Tata Steel).

5. **Retrieval quality > LLM quality** — The LLM can only answer from what retrieval gives it. If relevant chunks aren't retrieved, no amount of model quality helps. Investing in top_k, section boundaries, and hybrid retrieval paid off more than switching LLMs.

6. **Cheap/free LLMs are viable** — Groq's free tier with LLaMA 3.3 70B produces answers indistinguishable from Claude for financial Q&A. Don't over-invest in expensive APIs during development.

7. **Test with real documents early** — The 43 tests all passed with mock data, but real documents immediately exposed OCR gaps, section boundary mismatches, and retrieval ranking issues.

---

## 17. What's Next (Phase B onwards)

### Phase B — Multi-Agent Forecasting

The next major feature. Instead of one LLM answering, 4-5 specialist agents each analyze the same context independently, then a synthesis agent combines their views.

**Agents planned:**

| Agent | Role | Focus |
|---|---|---|
| Bull Analyst | Optimistic equity analyst | Upside scenarios, growth catalysts |
| Bear Analyst | Risk-focused analyst | Downside risks, margin pressure |
| Macro Analyst | Macroeconomist | Sector/economy impact, FX effects |
| Sector Analyst | Industry specialist | Competitive dynamics, peers |
| Quant Analyst | Quantitative analyst | Historical patterns, statistical analogies |

**New endpoint:** `POST /forecast/event`
```json
{
  "company": "Tata Steel",
  "event": "China increases steel export quota by 30%",
  "horizon": "12 months"
}
```

**Output:**
```
Bull View:    Domestic demand shields revenue, anti-dumping duties likely... +5-8% upside
Bear View:    Global price war, EBITDA margin compression of 300-400bps...
Macro View:   USD/INR movement amplifies raw material cost...
Synthesis:    High probability of short-term pressure (6-12 months).
              Historical analog: 2015 steel crisis — recovery took 18 months.
```

**New Streamlit tab:** FORECAST — event input → animated agent thinking → structured report

---

### Phase C — GraphRAG

Replace flat vector search with a knowledge graph so the system understands **relationships between companies, sectors, and events**.

```
"Tata Steel"
  ├── competes_with → JSW Steel, SAIL, ArcelorMittal
  ├── supplies_to   → Auto sector, Infrastructure
  ├── exposed_to    → Iron ore prices, Coking coal, EU carbon tax
  └── parent_of     → Tata Steel UK, Tata Steel Netherlands
```

When event = "EU Carbon Border Tax increases":
- Graph finds: Tata Steel UK is most exposed
- Retrieves: UK operations financial data specifically
- Much more precise than flat cosine search

**Library:** NetworkX (pure Python, no extra infra) → Neo4j for production scale

---

### Phase D — Brokerage Integration

Connect users' brokerage accounts to automatically load their portfolio into the RAG system.

**Target brokers (India):**

| Broker | API | Priority |
|---|---|---|
| Zerodha | Kite Connect API | First — most mature, best docs |
| Upstox | Upstox API v2 | Second |
| Angel One | SmartAPI | Third |

**User flow:**
```
User clicks "Connect Zerodha"
        │
        └── OAuth redirect → Zerodha login
                │
                └── Access token returned
                        │
                        └── System auto-fetches:
                            - Portfolio holdings (TATASTEEL, RELIANCE, etc.)
                            - 5 years of financials for each via yfinance
                            - Ingests available annual reports
                            - Ready to answer cross-portfolio questions
```

**Key capability unlocked:**
> "Which of my holdings is most at risk from rising interest rates?"
> System answers using data from ALL holdings simultaneously.

**Prerequisites before building:**
- User authentication system (JWT/API keys)
- Secure token storage (encrypted, never in plain text)
- API approval from Zerodha (Kite Connect costs ₹2,000/month for dev)

**Planned endpoints:**
```
POST /auth/brokerage/zerodha/connect   — initiate OAuth flow
GET  /auth/brokerage/zerodha/callback  — handle OAuth callback
GET  /portfolio/holdings               — fetch user's holdings
POST /portfolio/sync                   — auto-ingest all holding companies
GET  /portfolio/ask                    — query across entire portfolio
```

**Difficulty:** Medium-High
**Dependencies:** Phase B complete, user auth system in place

---

### Immediate priorities (pre-production)

1. **API authentication** — Bearer token or API key middleware
2. **Company name normalization** — Store and query in lowercase
3. **Persistent job tracking** — Replace in-memory dict with SQLite (already have it now)
4. **Cloud OCR integration** — Google Document AI for financial tables
5. **Shared context builder** — Refactor query vs stream endpoints to share `_build_context()` helper

### Phase 2: Fine-tuning (stubs ready)

The infrastructure for fine-tuning is stubbed in `app/phase2/`:

1. **Data collection** — Set `COLLECT_TRAINING_DATA=true` to log (question, context, answer) triples to JSONL
2. **Dataset building** — `DatasetBuilder` converts JSONL to training format
3. **LoRA training** — `LoRATrainer` fine-tunes a base model on collected financial Q&A pairs
4. **Model registry** — `ModelRegistry` versions and serves fine-tuned models
5. **Evaluation** — `RAGEvaluator` measures faithfulness, relevance, correctness using RAGAS metrics

---

*Document last updated: March 2026*
*System version: 1.2.0 (added historical data layer, yfinance, structured context enrichment)*

---

## 18. Phase B: Multi-Agent Forecasting

**Completed: March 2026 | Version: 1.3.0**

### What was built

A parallel multi-agent forecasting engine triggered by a specific company event. Three analyst agents (Bull, Bear, Macro) run simultaneously via `asyncio.gather`, then a Synthesizer agent combines their views into a structured forecast.

**Pipeline:**
```
POST /forecast/event
        │
        ├── Build context (SQLite financials + similar events + PDF chunks)
        │
        ├── asyncio.gather:
        │     ├── Bull Agent   (optimistic, upside catalysts)
        │     ├── Bear Agent   (pessimistic, downside risks)
        │     └── Macro Agent  (macro/sector forces)
        │
        └── Synthesizer Agent
              ├── BASE_CASE (most likely)
              ├── BULL_CASE (optimistic)
              ├── BEAR_CASE (pessimistic)
              ├── CONFIDENCE (HIGH/MEDIUM/LOW)
              ├── KEY_RISKS
              └── KEY_CATALYSTS
```

**New files:**
- `app/models/forecast.py` — ForecastRequest, ForecastResponse, AgentView models
- `app/services/forecast_service.py` — multi-agent engine with regex-based output parsing
- `app/routers/forecast.py` — POST /forecast/event endpoint

**Modified files:**
- `app/services/generation_service.py` — added `raw_generate(system, user)` to all backends (DeepSeek, Groq, Claude) enabling custom system prompts for agents
- `app/main.py` — registered forecast router
- `ui/app.py` — added FORECAST tab (4 tabs total: CHAT, FORECAST, DOCUMENTS, KNOWLEDGE BASE)

**Cost design:** DeepSeek/Groq for agents (cheap), Claude only if configured. 4 LLM calls per forecast (3 parallel + 1 synthesis).

---

## 19. Phase B (cont): BSE Auto-Ingest + Provider Pattern

**Completed: March 2026 | Version: 1.4.0**

### The manual upload problem

Every company required manual PDF uploads. Not scalable — 200 companies × 4 quarters = 800 PDFs/year.

### Solution: BSE India package + provider abstraction

Used `pip install bse` (unofficial BSE India API wrapper) to auto-fetch filings and financial data for any BSE-listed company.

**Key discovery during research:**
- PDF download requires session warmup: first GET `https://www.bseindia.com/` to get Akamai cookies, then download from `AttachLive/` URL
- Without warmup: 403 Forbidden
- With warmup: 200 OK, valid PDF

**Provider pattern (future-proof):**
```python
class MarketDataProvider(Protocol):
    def get_scrip_code(self, ticker) -> str
    def get_financials(self, scrip_code) -> dict
    def get_price(self, scrip_code) -> dict
    def get_announcements(self, scrip_code, days_back) -> list[dict]
    def download_pdf(self, attachment_name) -> bytes

# Swap provider: change ONE file (bse_provider.py → stockinsights_provider.py)
# Rest of codebase is untouched
```

**If BSE package breaks:** change `MARKET_DATA_PROVIDER=bse` to another provider in `.env`. Recovery time: ~2 hours.

**Full auto-ingest flow:**
```
User types "TATASTEEL" in UI
        ↓
POST /companies/load (background task)
        ↓
BSEProvider.get_scrip_code("TATASTEEL") → "500470"
        ↓
Fetch financials → parse → upsert SQLite (revenue, margins, EPS)
Fetch live price → upsert SQLite
        ↓
Fetch announcements (last 365 days) → filter:
  - PDFFLAG == 1 (has PDF)
  - CATEGORYNAME in [Results, Board Meeting, Annual Report, Investor Presentation]
  - File size > 50KB (excludes tiny notice PDFs)
  - Take most recent 6
        ↓
Download each PDF (session warmup → AttachLive URL)
        ↓
ingest_service.ingest(pdf_bytes, overrides={company, ticker, year}) → ChromaDB
        ↓
company_registry: status = "ready"
```

**New files:**
- `app/services/providers/base.py` — MarketDataProvider Protocol
- `app/services/providers/bse_provider.py` — BSE implementation
- `app/services/company_loader.py` — orchestrates full company load
- `app/routers/companies.py` — POST /companies/load, GET /companies/status/{ticker}, GET /companies/list

**Modified files:**
- `app/data/financial_db.py` — added company_registry table + 6 registry functions
- `app/main.py` — registered companies router
- `ui/app.py` — FORECAST tab now has "LOAD COMPANY DATA" expander with status table
- `requirements.txt` — added `bse>=3.2.0`

**BSE API test results:**
| Feature | Status |
|---|---|
| getScripCode() | ✅ Working |
| quote() — live price | ✅ Working |
| resultsSnapshot() — financials | ✅ Working |
| announcements() — filing metadata | ✅ Working |
| PDF download (with session warmup) | ✅ Working |
| resultCalendar() | ✅ Working |
| lookup() | ❌ Bug in v3.2.0 — use getScripCode() instead |

**Why not StockInsights API?**
Evaluated StockInsights AI API (₹6,000/month for 5,000 calls). BSE package provides equivalent data for free. StockInsights only advantage is AI-generated summaries — not needed since the system generates its own analysis.

---

---

## 17. Next.js Frontend — Full Rebuild

### Why we replaced Streamlit

Streamlit was fast to prototype but hit hard limits in production:
- No real routing — every page is a re-run of the full script
- No persistent auth — session state lost on refresh
- No streaming UI control — `st.write_stream` has no customisation
- Looks like an internal tool, not a product

**Decision:** Replace with Next.js 15 (App Router) + Tailwind v4 + shadcn/ui. Build a real product UI.

### Design system

Dark, finance-terminal aesthetic inspired by Stripe's dashboard:

```css
--background: #06060A      /* near-black base */
--card: #0F0F17            /* surface */
--border: #1A1A2E          /* subtle borders */
--primary: #4F46E5         /* indigo accent */
--muted-foreground: #6B7280
```

### Key engineering decisions

**SSE streaming in React:**
The backend sends typed JSON events over SSE:
```
data: {"type": "meta", "chunk_count": 8, "sources": [...]}
data: {"type": "token", "text": "Tata Steel"}
data: {"type": "token", "text": " reported..."}
data: {"type": "done"}
```

Frontend parses each line, extracts `.text` only when `type === "token"`, appends to message state. This was non-trivial — initial implementation was displaying raw JSON.

**Fire-and-forget company load:**
Company loading takes 5–10 minutes (PDF download + OCR + embedding). UX pattern:
1. User selects company → `loadCompany()` called without await
2. Immediately navigate to `/company/[ticker]`
3. Page shows ingestion progress banner with live polling (5s interval)
4. When status changes (doc_count increases, prices_synced_at set) — auto-refresh data
5. User never waits on a loading screen

**Markdown in chat:**
Backend prompt explicitly requests structured markdown. Frontend renders with `react-markdown` + `remark-gfm` — handles tables, headers, bold, code blocks, blockquotes.

### Bugs fixed during frontend build

| Bug | Root cause | Fix |
|-----|-----------|-----|
| Search dropdown not showing | Backend returns `{results: [...]}` not plain array | `data.results ?? []` |
| Forecast crash — `agents undefined` | Response uses `agent_views[]` with `stance`, not `agents[]` with `signal` | Rewrote AgentView type |
| Chat showing raw JSON | SSE events not parsed | Parse JSON, filter `type === "token"` |
| Overview never updates | Financials fetched once on mount | Polling loop re-fetches on state change |
| Port 8000 blocked | Windows system process reserved port | Switched to 8080 |
| TypeScript error on `sector` | Backend has `group` field, not `sector` | Changed to `r.group` |

---

## 18. Security Layer — Production Auth

### What was built

When preparing for production, a full security layer was added from scratch:

**Authentication:**
- JWT tokens (python-jose, HS256) — stateless, no server-side session storage
- bcrypt password hashing (passlib) — cost factor 12, salt auto-generated
- API keys with `fr_` prefix — alternative auth for programmatic access
- ULID for user IDs — time-sortable, URL-safe, no UUID collision concerns

**Credit system:**
- Trial users: 10 credits/day, resets midnight UTC
- Admin users: unlimited (role-based bypass)
- Credit costs: `/query` = 1, `/forecast/event` = 2, `/documents/upload` = 2
- `check_and_consume()` → gate before request, `consume_after_success()` → deduct after success
- This prevents charging users for failed requests

**Rate limiting:**
- slowapi (per-IP, Redis-compatible) — 20/min queries, 10/min forecasts, 5/min uploads
- Extracted to `app/core/limiter.py` to avoid circular imports (main.py ↔ query.py)

**CORS & headers:**
- Origins restricted to known domains via env var `ALLOWED_ORIGINS`
- `allow_credentials=False` (avoids cookie CSRF vectors)
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- HSTS added in production environment only

**Frontend auth:**
- JWT stored in `sessionStorage` (survives tab refresh, cleared on tab close)
- Module-level `_token` in `api.ts` — all requests automatically include Bearer header
- `AuthProvider` restores token from sessionStorage on mount, validates with `/auth/me`
- `AuthGuard` component redirects to `/auth/login` if no valid token
- Credit counter in header refreshes after each credit-bearing operation

### Key lesson

The circular import problem: `query.py` imported `limiter` from `main.py`, which imports `query.py`. Fixed by creating `app/core/limiter.py` as a standalone module — a pattern applicable to any shared FastAPI dependency.

---

## 19. Production Deployment

### Infrastructure

```
quantcortex.in (Vercel — Next.js)
       ↓ HTTPS
api.quantcortex.in (Hostinger VPS — FastAPI)
       ↓
  Nginx (reverse proxy, SSL termination)
       ↓
  uvicorn (127.0.0.1:8080)
       ↓
  systemd (auto-restart, runs as non-root user)
```

**VPS specs:** Ubuntu 24.04, 2 vCPU, 4GB RAM, 50GB NVMe (Hostinger KVM)

**Why not serverless?**
- ChromaDB requires persistent disk (file-based vector store)
- SQLite requires persistent disk
- FinBERT is 438MB loaded into RAM — cold starts would be unacceptable
- Background tasks (PDF ingest, OCR) run for minutes — Lambda timeout = 15min max

### Deployment steps (documented for reproducibility)
1. Ubuntu 24.04, Python 3.12, Nginx, Certbot, Tesseract installed via apt
2. Non-root `financerag` user — app never runs as root
3. `.env` with production secrets — never committed to git
4. `systemd` service with `Restart=always` — survives crashes and reboots
5. `certbot --nginx` — automatic SSL, auto-renews via cron
6. UFW firewall — only ports 22 (SSH), 80 (HTTP), 443 (HTTPS) open
7. Vercel — GitHub push triggers automatic frontend deploy

### Issues encountered
- **bcrypt version conflict:** passlib 1.7.4 + bcrypt 4.x has `__about__` AttributeError on Python 3.12. Fixed: `pip install bcrypt==4.0.1`
- **app/models/ in .gitignore:** `models/` pattern matched `app/models/`. Fixed: changed to `/models/` (anchored to root)
- **Port 8000 blocked:** Windows system process held port 8000. Production uses 8080.
- **BSE timeout on startup:** BSE securities cache times out for some stock groups (A, F). Non-fatal — loads partial cache (1800 securities) and continues.
- **DNS propagation:** `api.quantcortex.in` A record took ~15 min to propagate before Certbot could verify domain ownership.

---

## 20. Vision: Market Impact Propagation System

### The insight

Current financial AI tools (Screener, Tickertape, Moneycontrol, even ChatGPT) show you data about a company in isolation. None of them answer:

> *"Reliance Industries announced a refinery shutdown — which companies are affected, by how much, and over what timeframe?"*

This requires understanding the **relationship graph** between companies — who supplies whom, who competes, which sectors are interdependent.

### The system we're building

```
Event/News arrives
       ↓
Sentiment → Price Impact Model
(quantify event severity and direction)
       ↓
GraphRAG — Company Relationship Graph (Phase C)
(who is directly affected? supply chain? competitors? sector peers?)
       ↓
Anomaly Detector (Phase E)
(are affected companies already showing financial stress?)
       ↓
Volatility Forecaster (Phase E)
(predict high-volatility windows for each affected company)
       ↓
Earnings Surprise Predictor (Phase E)
(will upcoming earnings be impacted?)
       ↓
Multi-Agent Synthesis (already built)
(Bull/Bear/Macro → final propagation-aware forecast)
```

### Why this is genuinely novel

No retail platform does impact propagation. It requires:
1. A knowledge graph of company relationships (not just price data)
2. ML models trained on Indian market data (not US-market models)
3. Integration of unstructured (filings, news) + structured (financials, prices) data
4. A retrieval system that can traverse the graph (GraphRAG)

### Build order

| Phase | What | Depends on |
|-------|------|-----------|
| C | GraphRAG — company relationship graph | Core RAG (done) |
| D | Sentiment → Price Impact model | Graph (Phase C) |
| E | Volatility Forecaster + Anomaly Detector | Historical data (done) + Graph |
| F | Earnings Surprise Predictor | All of above as features |
| G | Full propagation pipeline | All phases |

---

## 21. Email Verification & Auth Hardening

### The problem

After shipping JWT auth and the Next.js frontend, the system had a gap: anyone could register with a fake email and consume credits. There was also no way to distinguish verified real users from throwaway accounts — important for trust, spam prevention, and future paid tiers.

### What we built

**Backend — transactional email verification via Resend:**

```
POST /auth/register
  → create user (is_verified=0)
  → generate secrets.token_urlsafe(32) → store in verification_tokens table (24h expiry)
  → send_verification_email() via Resend API from noreply@quantcortex.in
  → return JWT (user can browse but not consume credits)

GET /auth/verify?token=xxx
  → validate token: not used, not expired
  → mark token used=1, user is_verified=1
  → send_welcome_email()

POST /auth/resend-verification   — invalidates old token, sends fresh one
GET /auth/admin/users            — admin-only, returns all users + credit usage stats
```

**Database additions:**

```sql
ALTER TABLE users ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0;

CREATE TABLE verification_tokens (
    token       TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    used        INTEGER NOT NULL DEFAULT 0
);
```

**Auth dependency chain tightened:**

```python
get_current_user      # validates JWT / API key
    ↓
require_verified      # 403 if email not verified (admin exempt)
    ↓
require_credits       # checks daily limit
    ↓
consume_after_success # deducts credit only on successful response
```

### Key bugs hit and fixed

**structlog `event=` keyword conflict:**

```python
# BROKEN — structlog uses 'event' as its positional arg internally
logger.warning("resend_api_key_not_set", event="email_skipped")
# → TypeError: BoundLogger.warning() got multiple values for argument 'event'

# FIXED
logger.warning("resend_api_key_not_set_email_skipped")
```

Every register call was returning 500 until this was caught.

**`ALTER TABLE` inside `executescript`:** SQLite's `executescript()` commits pending transactions and doesn't mix DDL + DML. Had to split into separate `executescript` (for `CREATE TABLE`) and a `try/except` block (for `ALTER TABLE`).

### Frontend verification UX — three iterations

**Iteration 1 (broken):** On successful verification, always redirected to `/auth/login` — even when the user was already logged in. Forced an unnecessary second login.

**Iteration 2 (broken):** Checked `sessionStorage` for an existing token, attempted `window.close()` if logged in. Two problems:
1. `sessionStorage` is tab-scoped — the verify tab (opened from email) always has an empty session, so the check always returned false
2. Browsers block `window.close()` on tabs not opened via `window.open()` — email clients open tabs manually, so the call silently failed, leaving the user back on Gmail

**Iteration 3 (working):**

*Switch `sessionStorage` → `localStorage`* across the entire auth layer. `localStorage` is shared across all tabs of the same origin, so the verify tab correctly reads the existing login.

*Redirect instead of close, + BroadcastChannel for instant cross-tab sync:*

```typescript
// verify/page.tsx — after successful verification:
try { new BroadcastChannel("auth").postMessage("verified"); } catch {}
setTimeout(() => router.replace(alreadyLoggedIn ? "/" : "/auth/login"), 2000);

// lib/auth.tsx — AuthProvider:
channel = new BroadcastChannel("auth");
channel.onmessage = (e) => { if (e.data === "verified") refresh(); };
```

The verify tab navigates to `/` (user stays in the app). Any other open app tabs receive the signal and immediately call `/auth/me` — the unverified banner disappears without user action.

A `visibilitychange` listener provides a fallback for cross-device scenarios (verify on phone, app open on desktop) — the banner clears the next time the desktop tab is focused.

### Final verified UX flow

```
Register → JWT issued, yellow "Please verify your email" banner appears
     ↓
User clicks verify link in email → new tab opens
     ↓
"Email verified! Taking you back to the app..." (2 sec)
     ↓
Verify tab redirects to /
Original tab receives BroadcastChannel signal → calls /auth/me
     ↓
is_verified: true → banner gone, full access unlocked
```

---

*Document last updated: March 2026*
*System version: 2.1.0 (Email verification + auth hardening + localStorage + BroadcastChannel UX)*
