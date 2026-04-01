# QuantCortex

## What This Is

QuantCortex is a Finance AI RAG system for BSE-listed Indian companies. Users load a company ticker, the system auto-fetches financials and PDFs from BSE India, and they can ask natural language questions, run multi-agent forecasts, or trigger an impact propagation analysis that shows how an event ripples through the market graph. Live at quantcortex.in.

## Core Value

Cross-sector impact propagation — show users exactly which companies and macro factors get hit when any event touches a Nifty 50 company, in a way no retail Indian finance platform does today.

## Requirements

### Validated (already shipped)

- ✓ Full RAG pipeline: FinBERT embed → ChromaDB → BM25+RRF hybrid → LLM answer — Phase A
- ✓ Historical data layer: SQLite financials, stock prices, events, ticker_map — Phase A
- ✓ BSE auto-ingest: POST /companies/load → scrip_code → PDFs → ChromaDB — Phase B
- ✓ Multi-agent forecasting: Bull/Bear/Macro + Synthesizer — Phase B
- ✓ Streaming responses: SSE via POST /query/stream — Phase B
- ✓ Graph foundation: NetworkX in-memory graph, SQLite nodes/edges, seed loader — Phase C
- ✓ Impact propagation engine: BFS traversal, weighted edges, propagate() — Phase C
- ✓ Impact propagation endpoint: POST /graph/propagate — Phase C
- ✓ Impact tab in frontend with LLM analysis + affected companies/factors table — Phase C
- ✓ Next.js frontend: company view, chat, forecast, impact tabs — Phase C
- ✓ Auth + credit system, rate limiting, production deployment

### Active

- [ ] Complete Nifty 50 graph seed data: Batches 3–7 (Metals, Energy, Auto, FMCG, Pharma, Industrials)
- [ ] Fix stub nodes: TITAN (2 edges), ITC (1 edge), JSWSTEEL (1 edge) — minimum 6 edges each
- [ ] Master seed merge + validation: single nifty50_relationships.json, no stub nodes, all ≥6 edges
- [ ] Cross-sector bridging edges: bank lending books → Real Estate / Auto financing segments
- [ ] Graph engine: BFS revisits nodes via higher-weight paths (currently first-visit wins)
- [ ] Animated propagation visualization: React Flow wave animation in Impact tab
- [ ] Shared _build_context() helper: eliminate duplicate enrichment in query.py + query_service.py
- [ ] Impact tab UX: affected company tickers clickable to /company/[ticker]
- [ ] Chat tab: pre-fill company when opened from company page

### Out of Scope

- All 5000+ BSE companies — solo developer, no data team. Nifty 50 is the right scope for v1.
- Phase D Zerodha Kite Connect integration — deferred, needs brokerage auth flow
- Real-time news feed (C3) — deferred to v2, NewsAPI free tier is 100 req/day
- Fine-tuned model (phase2/ stubs) — deferred, RAG performance is sufficient for now
- Mobile app — web-first

## Context

- **Stack:** Python 3.12 · FastAPI · FinBERT · ChromaDB · Groq LLaMA 3.3 70B (default) · NetworkX · SQLite · Next.js 15 · BSE India package
- **Graph data today:** 12 companies (Banking + IT), 141 high-quality edges. 8 companies partially covered (v1 prompt quality). 30 companies not covered.
- **Propagation engine works correctly** — the gap is missing seed data, not broken code. BFS traversal is sound but visits nodes first-come-first-served (misses higher-weight alternative paths).
- **Solo developer** — all seed data must be researchable by one person using the v2 research prompt + LLM assistance.
- **Live product** — changes to query pipeline or graph must not break existing RAG behaviour.

## Constraints

- **Tech stack:** No new backend frameworks. Extensions only — additive changes preferred.
- **ChromaDB:** Sync-only — always wrap in run_in_threadpool(). Writes need asyncio.Lock.
- **FinBERT:** CPU-bound — always run in ThreadPoolExecutor(max_workers=1).
- **BSE:** Sync calls — always wrap in asyncio.to_thread().
- **Graph propagation:** Changes to BFS must not regress existing impact output for Banking/IT companies.
- **Seed data quality:** All batches must pass the validation script (≥6 edges, no stub nodes, specific source_reference). Use v2 research prompt only.
- **Frontend:** React Flow for graph viz — TypeScript-native, handles directed graphs, animated edges.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Nifty 50 as graph scope for v1 | 65% of BSE market cap, all major supply chains represented. Solo dev can't maintain 5000+ companies. | — Pending |
| React Flow for propagation viz | TypeScript-native, animated edges built-in, BFS wave animation achievable, good DX | — Pending |
| Seed data collected batch-by-batch | Allows incremental graph quality improvement without blocking the visualization work | ✓ Good |
| BFS with visited set (current) | Prevents cycles, fast. Known limitation: misses higher-weight alternative paths | ⚠️ Revisit in Phase 4 |
| SQLite for graph storage | Queryable without loading NetworkX, row-level inserts on LLM extraction | ✓ Good |

---
*Last updated: 2026-04-02 after project initialization*
