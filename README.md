# Finance AI RAG System

A production-oriented Finance AI Assistant for BSE-listed Indian companies. Type a ticker, the system auto-fetches financials and filings from BSE India, and you can ask natural language questions or get multi-agent event forecasts — no manual document uploads needed.

**Stack:** Python 3.14 · FastAPI · FinBERT · ChromaDB · Groq (LLaMA 3.3 70B) · SQLite · BSE India · Streamlit

---

## What it does

- **Auto-ingests company data** — enter a BSE ticker (e.g. `TATASTEEL`), the system resolves the scrip code, fetches financials to SQLite, downloads recent filings (Annual Reports, Results, Board Meeting PDFs) from BSE India, and ingests them into the vector store automatically
- **Answers financial questions** — hybrid RAG (FinBERT vector search + BM25 + Reciprocal Rank Fusion) over ingested documents, enriched with structured financial tables from SQLite
- **Multi-agent forecasting** — Bull, Bear, and Macro analyst agents run in parallel and a Synthesizer combines their views into a structured event forecast
- **Streaming responses** — answers stream token-by-token via SSE, sources appear after completion
- **Pluggable LLMs** — switch between Groq (free, default), DeepSeek, or Claude via a single env var

---

## Architecture

### Query flow
```
POST /query  or  POST /query/stream (SSE)
  → MCPService: classify query → RISK | REVENUE | MACRO | COMPARATIVE | HISTORICAL | GENERAL
  → MCPService: build ChromaDB metadata filter
  → SQLite: fetch structured financials → prepend to context
  → EmbeddingService: FinBERT CLS embed
  → RetrievalService: vector search + BM25 + RRF fusion (α=0.7)
  → MCPService: assemble context (dedup, sort, cite)
  → GenerationService: LLM answer
```

### Company auto-load flow
```
POST /companies/load {"ticker": "TATASTEEL"}
  → Background task: CompanyLoader
    → BSEProvider: ticker → scrip_code
    → BSEProvider: fetch financials → SQLite
    → BSEProvider: fetch live price → SQLite
    → BSEProvider: get announcements → filter (Results, Annual Report, Board Meeting)
    → BSEProvider: download PDFs [session warmup required]
    → IngestionService: parse → chunk → embed → ChromaDB
    → company_registry: status = ready
```

### Forecast flow
```
POST /forecast/event {"company": "Tata Steel", "event_type": "...", "event_description": "..."}
  → asyncio.gather: Bull agent | Bear agent | Macro agent  (parallel LLM calls)
  → Synthesizer agent: combines views → base / bull / bear case + risks + catalysts
```

---

## Stack

| Component | Technology |
|---|---|
| Embeddings | ProsusAI/finbert (CLS pooler_output, L2-normalized, dim=768) |
| LLM | Groq llama-3.3-70b (default) · DeepSeek · Claude — switchable via env var |
| Vector DB | ChromaDB (persistent, cosine similarity, metadata filtering) |
| Hybrid Retrieval | ChromaDB vector + BM25 (rank-bm25) + Reciprocal Rank Fusion |
| Structured DB | SQLite — financials, stock prices, events, ticker map, company registry |
| Market Data | BSE India (`bse` package) for auto-ingest · yfinance for historical prices |
| Backend | FastAPI async + Uvicorn |
| Frontend | Streamlit (CHAT / FORECAST / DOCUMENTS / KNOWLEDGE BASE tabs) |
| Monitoring | structlog (JSON) + Prometheus + Grafana |
| OCR | pypdf → pdfplumber → Tesseract (3-layer fallback) |

---

## Quick Start

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` — at minimum set your LLM API key:

```env
LLM_PROVIDER=groq           # groq | deepseek | claude
GROQ_API_KEY=gsk_...        # free at console.groq.com
```

### 3. Run the backend

```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 4. Run the UI (separate terminal)

```bash
streamlit run ui/app.py
```

Open http://localhost:8501

### 5. Load a company and query

In the **FORECAST** tab, open "LOAD COMPANY DATA", enter a BSE ticker (e.g. `TATASTEEL`), click Fetch & Ingest. Poll status until ready, then switch to **CHAT** and ask questions.

Or via API:

```bash
# Load a company
curl -X POST http://localhost:8000/companies/load \
  -H "Content-Type: application/json" \
  -d '{"ticker": "TATASTEEL"}'

# Poll until ready
curl http://localhost:8000/companies/status/TATASTEEL

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What was Tata Steel revenue in FY2024?", "company": "Tata Steel"}'
```

---

## API Reference

### Core

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/metrics` | Prometheus metrics |
| `POST` | `/documents/upload` | Manually upload a PDF (202, background) |
| `POST` | `/query` | Financial question → answer + sources |
| `POST` | `/query/stream` | Same but SSE streaming |

### Company auto-load

| Method | Path | Description |
|---|---|---|
| `POST` | `/companies/load` | Auto-fetch + ingest a BSE ticker (202, background) |
| `GET` | `/companies/status/{ticker}` | Load status: pending / loading / ready / failed |
| `GET` | `/companies/list` | All registered companies |

### Market data

| Method | Path | Description |
|---|---|---|
| `POST` | `/market/fetch/sync` | Fetch financials + prices (waits) |
| `GET` | `/market/financials/{company}` | Annual financials history |
| `GET` | `/market/financials/{company}/quarterly` | Quarterly breakdown |
| `GET` | `/market/stock/{ticker}/summary` | 52-week range + latest close |
| `POST` | `/market/events` | Log a financial event |
| `GET` | `/market/events/similar/{type}` | Find analogous historical events |

### Forecasting

| Method | Path | Description |
|---|---|---|
| `POST` | `/forecast/event` | Multi-agent event impact forecast |

### Collections

| Method | Path | Description |
|---|---|---|
| `GET` | `/collections` | List ChromaDB collections |
| `DELETE` | `/collections/{name}` | Delete a collection |

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `groq` | `groq` \| `deepseek` \| `claude` |
| `GROQ_API_KEY` | — | Required if `LLM_PROVIDER=groq` |
| `DEEPSEEK_API_KEY` | — | Required if `LLM_PROVIDER=deepseek` |
| `ANTHROPIC_API_KEY` | — | Required if `LLM_PROVIDER=claude` |
| `EMBEDDING_MODEL` | `ProsusAI/finbert` | HuggingFace model ID |
| `RETRIEVAL_TOP_K` | `10` | Chunks returned per query |
| `RETRIEVAL_RRF_ALPHA` | `0.7` | Vector weight in RRF fusion |
| `MAX_CONTEXT_TOKENS` | `6000` | Max tokens sent to LLM |
| `CHUNK_SIZE_TOKENS` | `480` | Max tokens per chunk |
| `COLLECT_TRAINING_DATA` | `false` | Log QA pairs to JSONL for Phase 2 |

---

## Project Structure

```
finance-rag/
├── app/
│   ├── main.py                      # FastAPI factory, lifespan, router registration
│   ├── config.py                    # Pydantic BaseSettings (.env)
│   ├── dependencies.py              # @lru_cache singletons (embedding, vector, llm, etc.)
│   ├── data/
│   │   └── financial_db.py          # SQLite: financials, prices, events, company_registry
│   ├── routers/
│   │   ├── query.py                 # POST /query + /query/stream
│   │   ├── ingestion.py             # POST /documents/upload
│   │   ├── forecast.py              # POST /forecast/event
│   │   ├── companies.py             # Company auto-load endpoints
│   │   ├── market_data.py           # Market data endpoints
│   │   ├── collections.py           # ChromaDB collection management
│   │   └── health.py                # GET /health
│   ├── services/
│   │   ├── embedding_service.py     # FinBERT async (ThreadPoolExecutor)
│   │   ├── retrieval_service.py     # Hybrid vector + BM25 + RRF
│   │   ├── generation_service.py    # LLM backends (Groq/DeepSeek/Claude) + Protocol
│   │   ├── ingestion_service.py     # parse → chunk → embed → store
│   │   ├── query_service.py         # Full query pipeline
│   │   ├── mcp_service.py           # Query classification + context assembly
│   │   ├── forecast_service.py      # Multi-agent forecasting engine
│   │   ├── market_data_service.py   # yfinance integration
│   │   ├── company_loader.py        # BSE auto-ingest orchestrator
│   │   └── providers/
│   │       ├── base.py              # MarketDataProvider Protocol
│   │       └── bse_provider.py      # BSE India implementation
│   ├── core/
│   │   ├── chunker.py               # Section-aware + recursive chunking
│   │   ├── document_parser.py       # pypdf → pdfplumber → Tesseract OCR
│   │   ├── metadata_extractor.py    # Regex metadata extraction
│   │   ├── vector_store.py          # ChromaDB async-safe wrapper
│   │   └── prompts.py               # Prompt templates
│   ├── models/                      # Pydantic request/response models
│   ├── monitoring/                  # structlog + Prometheus middleware
│   └── phase2/                      # LoRA fine-tuning hooks (stubs)
├── ui/
│   └── app.py                       # Streamlit UI (4 tabs)
├── tests/
│   ├── unit/                        # Pure Python, no external services
│   └── integration/                 # Mocked embedding/vector/LLM
├── docker/                          # Dockerfile + docker-compose
├── monitoring/                      # Prometheus + Grafana config
├── scripts/                         # Seed and benchmark utilities
└── data/                            # chroma_db/, sample_docs/ (git-ignored)
```

---

## Monitoring (Docker)

```bash
cd docker && docker-compose up -d
```

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin / changeme)

Pre-built dashboard shows request latency, query rate by type, LLM token usage, ChromaDB collection size.

---

## Phase 2 Roadmap

- **Phase C — GraphRAG:** NetworkX knowledge graph of company relationships (competitors, suppliers, sectors) for richer context assembly
- **Phase D — Brokerage Integration:** Zerodha Kite Connect OAuth for real portfolio data
- **Fine-tuning hooks** (`app/phase2/`): Set `COLLECT_TRAINING_DATA=true` to log QA pairs → LoRA training pipeline ready to plug in
