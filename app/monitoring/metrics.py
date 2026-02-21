"""Prometheus metrics definitions."""
from prometheus_client import Counter, Gauge, Histogram

# ── HTTP request metrics ──────────────────────────────────────────────────────
HTTP_REQUESTS_TOTAL = Counter(
    "finance_rag_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "finance_rag_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# ── Ingestion metrics ─────────────────────────────────────────────────────────
DOCUMENTS_INGESTED_TOTAL = Counter(
    "finance_rag_documents_ingested_total",
    "Total documents ingested",
    ["report_type", "status"],
)

CHUNKS_CREATED_TOTAL = Counter(
    "finance_rag_chunks_created_total",
    "Total document chunks created",
    ["section_type"],
)

INGESTION_DURATION_SECONDS = Histogram(
    "finance_rag_ingestion_duration_seconds",
    "Document ingestion duration in seconds",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# ── Query metrics ─────────────────────────────────────────────────────────────
QUERIES_TOTAL = Counter(
    "finance_rag_queries_total",
    "Total queries processed",
    ["query_type", "status"],
)

QUERY_DURATION_SECONDS = Histogram(
    "finance_rag_query_duration_seconds",
    "Query end-to-end duration in seconds",
    ["query_type"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

RETRIEVAL_CHUNK_COUNT = Histogram(
    "finance_rag_retrieval_chunk_count",
    "Number of chunks retrieved per query",
    buckets=[1, 2, 3, 5, 8, 10, 15, 20],
)

# ── Token usage metrics ───────────────────────────────────────────────────────
LLM_INPUT_TOKENS_TOTAL = Counter(
    "finance_rag_llm_input_tokens_total",
    "Total LLM input tokens consumed",
    ["model"],
)

LLM_OUTPUT_TOKENS_TOTAL = Counter(
    "finance_rag_llm_output_tokens_total",
    "Total LLM output tokens generated",
    ["model"],
)

LLM_LATENCY_SECONDS = Histogram(
    "finance_rag_llm_latency_seconds",
    "LLM API call duration in seconds",
    ["model"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 20.0, 60.0],
)

# ── Embedding metrics ─────────────────────────────────────────────────────────
EMBEDDING_DURATION_SECONDS = Histogram(
    "finance_rag_embedding_duration_seconds",
    "Embedding generation duration in seconds",
    ["batch_size"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 5.0],
)

# ── System metrics ────────────────────────────────────────────────────────────
CHROMA_COLLECTION_SIZE = Gauge(
    "finance_rag_chroma_collection_size",
    "Number of vectors in ChromaDB collection",
    ["collection_name"],
)

ACTIVE_REQUESTS = Gauge(
    "finance_rag_active_requests",
    "Number of currently active requests",
)
