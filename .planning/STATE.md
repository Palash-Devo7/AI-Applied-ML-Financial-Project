# Project State — QuantCortex

**Last updated:** 2026-04-02 after project initialization

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-02)

**Core value:** Cross-sector impact propagation across all Nifty 50 companies with animated visualization
**Current milestone:** v2.0 — Nifty 50 Graph Completion + Impact Visualization
**Current phase:** Not started — run `/gsd:plan-phase 1` to begin

## Current Position

```
Phase 1 [ ] Seed Data: Metals & Energy          ← START HERE
Phase 2 [ ] Seed Data: Auto, FMCG, Pharma & Stubs
Phase 3 [ ] Master Merge, Validation & Reload
Phase 4 [ ] Graph Engine Improvements
Phase 5 [ ] Animated Propagation Visualization
Phase 6 [ ] UX Polish & Code Quality
```

## What's Already Built (do not re-implement)

- Full RAG pipeline: FinBERT → ChromaDB → BM25+RRF → Groq LLM
- Phase A: SQLite historical data (financials, stock prices, events, ticker_map)
- Phase B: Multi-agent forecasting (Bull/Bear/Macro + Synthesizer), BSE auto-ingest
- Phase C: GraphRAG — NetworkX graph, BFS propagation engine, POST /graph/propagate, Impact tab UI
- Auth + credit system, rate limiting, Next.js frontend with company/chat/forecast/impact tabs

## Graph Data Status

| Batch | Companies | Edges | Quality | Status |
|-------|-----------|-------|---------|--------|
| Banking + IT (done) | 12 | 141 | High (v2) | ✅ Active |
| Auto + partial (v1) | 8 | ~29 | Low (v1) | ⚠️ Needs upgrade |
| Metals & Mining | 4 | 0 | — | ❌ Batch 3 |
| Energy & Conglomerates | 8 | 0 | — | ❌ Batch 4 |
| Auto remainder + FMCG | 8 | 0 | — | ❌ Batch 5+6 |
| Pharma | 5 | 0 | — | ❌ Batch 6 |
| Industrials | 5 | 0 | — | ❌ Batch 7 |

## Key File Locations

- Seed data: `data/seed/nifty50_relationships.json` (master), `data/seed/nifty50_banking_it_relationships_clean.json` (batch 1)
- Research prompt: `data/seed/research_prompt_v2.md` — use this for all new batches
- Propagation engine: `app/graph/propagation_engine.py`
- Impact service: `app/services/impact_service.py`
- Graph router: `app/routers/graph.py`
- Impact tab UI: `finance-ui/app/company/[ticker]/company-view.tsx` (ImpactTab component, line ~587)
- Validation script: `data/seed/PHASE_C_DATA_TRACKER.md` (bottom of file)

## Architecture Rules (never break)

1. ChromaDB is sync-only → always wrap in `run_in_threadpool()`, writes need `asyncio.Lock`
2. FinBERT is CPU-bound → always run in `ThreadPoolExecutor(max_workers=1)` via `run_in_executor`
3. BSE calls are sync → always wrap in `asyncio.to_thread()` inside async functions
4. Singletons via `@lru_cache` in `dependencies.py` — never instantiate services per-request
5. Graph augmentation is additive — flat vector search always runs, graph context prepended if available

## Open Issues / Tech Debt

- **HIGH:** BFS visits nodes first-come-first-served — misses higher-weight alternative paths (fix in Phase 4)
- **HIGH:** Duplicate enrichment code in `query.py` stream endpoint and `query_service.py` (fix in Phase 6)
- **MED:** Impact tab company tickers not clickable (fix in Phase 6)
- **MED:** Chat tab has no company pre-fill from company page (fix in Phase 6)
- **LOW:** MIN_IMPACT=0.2 hardcoded in propagation_engine.py — should be configurable (fix in Phase 4)

## Next Action

Run `/gsd:plan-phase 1` to create the execution plan for Seed Data: Metals & Energy.

Note: Phase 1 is primarily data research work, not coding. The researcher agent will help structure the approach for collecting batch data using the v2 research prompt.
