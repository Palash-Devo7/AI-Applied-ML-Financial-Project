# Finance AI RAG System

A production-oriented Finance AI Assistant built with hybrid RAG (Retrieval-Augmented Generation), FinBERT embeddings, ChromaDB, and Claude. Designed to answer questions from SEC filings, earnings reports, and financial statements with cited, factual responses.

## Architecture

```
POST /documents/upload
  → PDF Parser (pypdf / pdfplumber fallback)
  → Metadata Extractor (company, ticker, year, section_type)
  → FinancialChunker (section-boundary + recursive split)
  → EmbeddingService (FinBERT CLS, L2-normalized)
  → ChromaDB (persistent cosine similarity index)

POST /query
  → MCPService.classify_query()        → RISK | REVENUE | MACRO | COMPARATIVE | HISTORICAL | GENERAL
  → MCPService.build_metadata_filters() → ChromaDB where-clause
  → EmbeddingService.embed_texts()      → query vector
  → RetrievalService.hybrid_query()     → vector + BM25 + RRF fusion
  → MCPService.assemble_context()       → dedup, sort, cite
  → GenerationService.generate()        → Claude API answer
  → { answer, sources, query_type, latency_ms, tokens_used }
```

## Stack

| Component | Technology |
|-----------|-----------|
| Embeddings | ProsusAI/finbert (CLS token, L2-normalized) |
| LLM | Claude claude-sonnet-4-6 via Anthropic SDK |
| Vector DB | ChromaDB (persistent, cosine similarity) |
| Hybrid Retrieval | ChromaDB + BM25 (rank-bm25) + RRF fusion |
| Backend | FastAPI (async) + Uvicorn |
| Container | Docker multi-stage + docker-compose |
| Monitoring | structlog (JSON) + Prometheus + Grafana |

## Quick Start

### 1. Prerequisites

- Docker & Docker Compose
- Anthropic API key

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Start with Docker Compose

```bash
cd docker
docker-compose up -d

# Wait for FinBERT model download (~1 min on first run)
docker-compose logs -f api
```

Services:
- API: http://localhost:8000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/changeme)

### 4. Verify health

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "services": {"chroma": "ok", "finbert": "ok", "claude": "ok"}}
```

### 5. Ingest a document

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@data/sample_docs/apple_10k_2023.pdf" \
  -F "ticker=AAPL" \
  -F "report_type=10-K" \
  -F "year=2023"

# Response: {"document_id": "...", "chunk_count": 247, "status": "ingested"}
```

### 6. Query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are Apple'\''s main risk factors for fiscal 2023?",
    "filters": {"ticker": "AAPL", "year": 2023}
  }'
```

### 7. Bulk seed documents

```bash
# Place PDFs in data/sample_docs/ with naming convention: TICKER_REPORTTYPE_YEAR.pdf
python scripts/seed_documents.py --dir data/sample_docs --url http://localhost:8000
```

## Local Development (without Docker)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Set environment variables
cp .env.example .env && edit .env

# Run API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (ChromaDB, FinBERT, Claude) |
| `GET` | `/metrics` | Prometheus metrics |
| `POST` | `/documents/upload` | Ingest a PDF document |
| `POST` | `/query` | Submit a financial question |
| `GET` | `/collections` | List collections |
| `DELETE` | `/collections/{name}` | Delete a collection |

### POST /query

```json
{
  "question": "What were Apple's revenue drivers in Q4 2023?",
  "filters": {
    "ticker": "AAPL",
    "year": 2023,
    "quarter": "Q4",
    "report_type": "10-K"
  },
  "top_k": 5,
  "include_sources": true
}
```

Response:
```json
{
  "query_id": "01HXK...",
  "question": "...",
  "answer": "Apple's Q4 2023 revenue drivers... [Source 1]...",
  "sources": [{"chunk_id": "...", "text": "...", "score": 0.91, ...}],
  "query_type": "REVENUE",
  "latency_ms": 3240.5,
  "tokens_used": {"input_tokens": 1842, "output_tokens": 312, "total_tokens": 2154},
  "chunk_count": 4
}
```

## Monitoring

### Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `finance_rag_http_requests_total` | Counter | Requests by method/endpoint/status |
| `finance_rag_http_request_duration_seconds` | Histogram | Request latency |
| `finance_rag_queries_total` | Counter | Queries by type/status |
| `finance_rag_query_duration_seconds` | Histogram | Query end-to-end latency |
| `finance_rag_llm_input_tokens_total` | Counter | LLM input tokens consumed |
| `finance_rag_llm_output_tokens_total` | Counter | LLM output tokens generated |
| `finance_rag_llm_latency_seconds` | Histogram | LLM API call latency |
| `finance_rag_documents_ingested_total` | Counter | Documents ingested |
| `finance_rag_chunks_created_total` | Counter | Chunks created by section type |
| `finance_rag_chroma_collection_size` | Gauge | Vectors in ChromaDB |

### Grafana

Access at http://localhost:3000. Pre-provisioned dashboard shows:
- Request rate and latency (p50/p95/p99)
- Query rate by type
- LLM token usage and latency
- Document ingestion rate
- ChromaDB collection size

## Configuration Reference

See `.env.example` for all configuration options. Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic API key |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Claude model version |
| `EMBEDDING_MODEL` | `ProsusAI/finbert` | HuggingFace model ID |
| `EMBEDDING_STRATEGY` | `cls` | `cls` (pooler_output) or `mean` pooling |
| `RETRIEVAL_TOP_K` | `5` | Chunks returned per query |
| `RETRIEVAL_RRF_ALPHA` | `0.7` | Vector weight in RRF fusion (0-1) |
| `MAX_CONTEXT_TOKENS` | `6000` | Max tokens sent to Claude |
| `CHUNK_SIZE_TOKENS` | `480` | Max tokens per chunk |
| `COLLECT_TRAINING_DATA` | `false` | Log QA pairs for Phase 2 fine-tuning |

## Testing

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/ -m unit

# Integration tests
pytest tests/integration/ -m integration

# With coverage
pytest --cov=app --cov-report=html
```

## Benchmarking

```bash
# Benchmark FinBERT embedding throughput
python scripts/benchmark_embeddings.py --batch-sizes 1 4 8 16 --samples 64
```

## Phase 2: Fine-tuning Roadmap

The system includes design hooks for LoRA fine-tuning (see `app/phase2/`):

1. **Data collection**: Set `COLLECT_TRAINING_DATA=true` — GenerationService logs `(question, context, answer)` JSONL
2. **Dataset building**: `DatasetBuilder` cleans, deduplicates, formats for instruction tuning
3. **LoRA training**: `LoRATrainer` fine-tunes a base LLM with PEFT on finance QA data
4. **Model registry**: `ModelRegistry` versions and promotes adapter checkpoints
5. **Evaluation**: `RAGEvaluator` measures faithfulness, relevance, retrieval quality
6. **Deployment**: Set `USE_FINETUNED_MODEL=true` + `FINETUNED_MODEL_PATH=...` to swap backends

## Project Structure

```
finance-rag/
├── app/
│   ├── main.py                    # FastAPI app factory, lifespan
│   ├── config.py                  # Pydantic BaseSettings
│   ├── dependencies.py            # DI providers (singletons)
│   ├── routers/                   # HTTP route handlers
│   ├── services/                  # Business logic
│   │   ├── embedding_service.py   # FinBERT async embeddings
│   │   ├── retrieval_service.py   # Hybrid vector + BM25 + RRF
│   │   ├── generation_service.py  # Claude API + ModelBackend protocol
│   │   ├── ingestion_service.py   # parse → chunk → embed → store
│   │   ├── query_service.py       # classify → filter → retrieve → generate
│   │   └── mcp_service.py         # MCP orchestration layer
│   ├── core/                      # Domain logic
│   │   ├── chunker.py             # Section-aware + recursive chunking
│   │   ├── document_parser.py     # PDF parsing
│   │   ├── metadata_extractor.py  # Regex-based metadata extraction
│   │   ├── vector_store.py        # ChromaDB async wrapper
│   │   └── prompts.py             # System/user prompt templates
│   ├── monitoring/                # Observability
│   └── phase2/                    # Fine-tuning hooks (stubs)
├── tests/                         # Unit + integration tests
├── scripts/                       # Seed and benchmark utilities
├── docker/                        # Dockerfile + docker-compose
└── monitoring/                    # Prometheus + Grafana config
```
