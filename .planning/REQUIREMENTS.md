# Requirements: QuantCortex — Nifty 50 Graph Completion + Impact Visualization

**Defined:** 2026-04-02
**Core Value:** Cross-sector impact propagation across all Nifty 50 companies with animated visualization

## v1 Requirements

### Seed Data — High Priority Batches

- [ ] **SEED-01**: Metals & Mining batch (JSWSTEEL, HINDALCO, COALINDIA, VEDL) collected with v2 prompt, ≥6 edges each, passes validation script
- [ ] **SEED-02**: Energy & Conglomerates batch (RELIANCE, ONGC, BPCL, NTPC, POWERGRID, ADANIENT, ADANIPORTS, ADANIGREEN) collected, ≥6 edges each, passes validation
- [ ] **SEED-03**: COALINDIA → supplies_to → NTPC/BPCL edges captured (flagship power sector chain)
- [ ] **SEED-04**: RELIANCE group edges captured: JIO telecom, O2C refining, competes_with BHARTIARTL

### Seed Data — Medium Priority Batches

- [ ] **SEED-05**: Auto remainder batch (BAJAJ-AUTO, EICHERMOT, HEROMOTOCO) collected, ≥6 edges each
- [ ] **SEED-06**: FMCG stubs upgraded: ITC (1→≥8 edges), HINDUNILVR (4→≥8 edges), NESTLEIND, BRITANNIA, TATACONSUM, ASIANPAINT collected
- [ ] **SEED-07**: Partially covered auto companies upgraded: TATAMOTORS (JLR exports_to UK/Europe), MARUTI (Suzuki Group), M&M (Ministry of Agriculture tractor), TATASTEEL (CBAM exposure)
- [ ] **SEED-08**: Critical stubs fixed: TITAN (2→≥8 edges with gold import duty regulated_by), JSWSTEEL (1→≥8 edges full set)
- [ ] **SEED-09**: Pharma batch (SUNPHARMA, DRREDDY, CIPLA, DIVISLAB, APOLLOHOSP) collected — DIVISLAB supplies_to chain captured
- [ ] **SEED-10**: Industrials batch (LT, ULTRACEMCO, GRASIM, BHARTIARTL, SHREECEM) collected — GRASIM parent_of ULTRACEMCO

### Seed Data — Merge & Validation

- [ ] **SEED-11**: Master nifty50_relationships.json merged from all batches (banking_it_clean as base, v2 batches override v1 placeholders)
- [ ] **SEED-12**: Validation script passes on master file: all 50 companies ≥6 edges, zero stub nodes, no vague source_reference values
- [ ] **SEED-13**: Graph reloaded in DB via POST /graph/seed, propagation smoke test passes for: RBI rate change (Banking → Real Estate → Auto chain), crude oil shock (ONGC → BPCL → RELIANCE chain)

### Graph Engine

- [ ] **GRAPH-01**: BFS propagation engine updated to track and use highest-weight path to each node (not first-visited path) — improves impact score accuracy
- [ ] **GRAPH-02**: Cross-sector bridging edges added to seed data: banks' lending book exposure to Real Estate (HDFCBANK/ICICIBANK → real_estate_sector), auto financing (BAJFINANCE → Auto sector)
- [ ] **GRAPH-03**: MIN_IMPACT configurable via PropagationRequest (currently hardcoded 0.2), exposed in frontend depth selector

### Visualization

- [ ] **VIZ-01**: React Flow (@xyflow/react) installed in finance-ui
- [ ] **VIZ-02**: Propagation graph component renders trigger node + affected nodes as a directed graph (node color = impact level: red/orange/yellow/grey)
- [ ] **VIZ-03**: BFS wave animation: depth-1 nodes appear at 300ms, depth-2 at 700ms, depth-3 at 1200ms — shows propagation spreading outward
- [ ] **VIZ-04**: Edge thickness proportional to impact score; edge label shows relationship type
- [ ] **VIZ-05**: Node click navigates to /company/[ticker] for company nodes
- [ ] **VIZ-06**: Sector grouping: nodes visually clustered by sector (Banking, Energy, Auto, etc.)
- [ ] **VIZ-07**: Visualization panel appears below LLM analysis in Impact tab — existing table view remains as toggle

### UX & Code Quality

- [ ] **UX-01**: Affected company tickers in Impact tab table are clickable links to /company/[ticker]
- [ ] **UX-02**: Chat tab pre-fills company field when opened from a company page
- [ ] **CODE-01**: Shared _build_context() helper extracted — eliminates duplicate enrichment logic in query.py (stream endpoint) and query_service.py

## v2 Requirements

### News Trigger (Phase C3 — deferred)

- **NEWS-01**: GET /graph/news endpoint returns latest BSE announcements + NewsAPI macro events
- **NEWS-02**: Entity extraction from news headlines to trigger graph propagation automatically
- **NEWS-03**: News feed UI in frontend with click-to-propagate

### Extended Coverage

- **EXT-01**: Mid-cap companies beyond Nifty 50 get Tier 1 (yfinance sector) edges automatically on load
- **EXT-02**: Tier 3 LLM extraction fires on Annual Report PDF ingestion to auto-expand graph

### Zerodha Integration (Phase D)

- **KITE-01**: Zerodha Kite Connect brokerage auth flow
- **KITE-02**: Portfolio positions fetched and overlaid on impact analysis

## Out of Scope

| Feature | Reason |
|---------|--------|
| All 5000+ BSE companies in seed data | Solo dev, no data team. Nifty 50 covers 65% market cap |
| Real-time news feed v1 | NewsAPI free tier 100 req/day — insufficient for prod. Defer to v2 |
| Fine-tuned model | RAG performance sufficient. Phase 2 stubs remain stubs |
| Mobile app | Web-first |
| 3D graph visualization | Complexity vs value — React Flow 2D is sufficient |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SEED-01 | Phase 1 | Pending |
| SEED-02 | Phase 1 | Pending |
| SEED-03 | Phase 1 | Pending |
| SEED-04 | Phase 1 | Pending |
| SEED-05 | Phase 2 | Pending |
| SEED-06 | Phase 2 | Pending |
| SEED-07 | Phase 2 | Pending |
| SEED-08 | Phase 2 | Pending |
| SEED-09 | Phase 2 | Pending |
| SEED-10 | Phase 2 | Pending |
| SEED-11 | Phase 3 | Pending |
| SEED-12 | Phase 3 | Pending |
| SEED-13 | Phase 3 | Pending |
| GRAPH-01 | Phase 4 | Pending |
| GRAPH-02 | Phase 4 | Pending |
| GRAPH-03 | Phase 4 | Pending |
| VIZ-01 | Phase 5 | Pending |
| VIZ-02 | Phase 5 | Pending |
| VIZ-03 | Phase 5 | Pending |
| VIZ-04 | Phase 5 | Pending |
| VIZ-05 | Phase 5 | Pending |
| VIZ-06 | Phase 5 | Pending |
| VIZ-07 | Phase 5 | Pending |
| UX-01 | Phase 6 | Pending |
| UX-02 | Phase 6 | Pending |
| CODE-01 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-02*
*Last updated: 2026-04-02 after initial definition*
