# Finance AI RAG System — Project Journey

**Author:** Palash Joshi
**Project:** AI-Applied-ML-Financial-Project
**GitHub:** https://github.com/Palash-Devo7/AI-Applied-ML-Financial-Project
**Duration:** March 2026 (ongoing)
**Stack:** Python 3.14 · FastAPI · FinBERT · ChromaDB · Groq (LLaMA 3.3 70B) · Tesseract OCR · Streamlit

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
10. [Production Readiness Checklist](#10-production-readiness-checklist)
11. [Current System Capabilities](#11-current-system-capabilities)
12. [File Structure](#12-file-structure)
13. [Key Design Patterns](#13-key-design-patterns)
14. [Lessons Learned](#14-lessons-learned)
15. [What's Next (Phase 2)](#15-whats-next-phase-2)

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

## 10. Production Readiness Checklist

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
✅ Streamlit UI — dark themed, three pages, no frontend code required
✅ Prometheus metrics + Grafana dashboards
✅ JSON structured logging
✅ See stored companies via `/collections/companies`
✅ Check collection size via `/collections`

### What doesn't work yet

❌ Table data extraction is unreliable (OCR noise)
❌ Company name matching is case-sensitive and exact
❌ No authentication — anyone can access the API
❌ No rate limiting
❌ OCR jobs lost on server restart (in-memory job tracker)
❌ Chat history lost on Streamlit page refresh
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
│   ├── routers/
│   │   ├── health.py               # GET /health
│   │   ├── ingestion.py            # POST /documents/upload, GET /documents/{id}/status
│   │   ├── query.py                # POST /query
│   │   └── collections.py          # GET /collections, /collections/companies
│   └── services/
│       ├── embedding_service.py    # FinBERT inference, ThreadPoolExecutor
│       ├── generation_service.py   # ModelBackend Protocol, Groq/DeepSeek/Claude
│       ├── ingestion_service.py    # parse → chunk → embed → upsert pipeline
│       ├── mcp_service.py          # Classify, extract entities, build filters, assemble context
│       ├── query_service.py        # End-to-end query orchestration
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

## 14. What's Next (Phase 2)

### Immediate priorities (pre-production)

1. **API authentication** — Bearer token or API key middleware
2. **Company name normalization** — Store and query in lowercase
3. **Persistent job tracking** — Replace in-memory dict with Redis or SQLite
4. **Cloud OCR integration** — Google Document AI for financial tables

### Phase 2: Fine-tuning (stubs ready)

The infrastructure for fine-tuning is stubbed in `app/phase2/`:

1. **Data collection** — Set `COLLECT_TRAINING_DATA=true` to log (question, context, answer) triples to JSONL
2. **Dataset building** — `DatasetBuilder` converts JSONL to training format
3. **LoRA training** — `LoRATrainer` fine-tunes a base model on collected financial Q&A pairs
4. **Model registry** — `ModelRegistry` versions and serves fine-tuned models
5. **Evaluation** — `RAGEvaluator` measures faithfulness, relevance, correctness using RAGAS metrics

Once enough (question, answer) pairs are collected via production usage, fine-tuning would produce a model that understands Indian financial reporting conventions better than a general-purpose LLM.

---

*Document last updated: March 2026*
*System version: 1.1.0 (added Streamlit UI + streaming)*
