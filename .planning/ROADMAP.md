# Roadmap: QuantCortex — Nifty 50 Graph Completion + Impact Visualization

**Milestone:** v2.0
**Goal:** Complete Nifty 50 graph seed data across all sectors and deliver animated propagation visualization — making cross-sector impact analysis the clear differentiator of QuantCortex.
**Defined:** 2026-04-02

---

## Phase 1 — Seed Data: Metals & Energy (High Priority) 🔴

**Goal:** Collect and load the two highest-value missing sector batches — Metals/Mining and Energy/Conglomerates — enabling cross-sector propagation for crude oil shocks, coal supply chain events, and conglomerate group cascades.

**Why first:** COALINDIA → NTPC, ONGC → BPCL, ADANIENT → group are the most-queried macro chains after RBI/banking. Without these, energy and commodity event propagation shows empty results.

**Requirements:** SEED-01, SEED-02, SEED-03, SEED-04

**Deliverables:**
- Batch 3 JSON: JSWSTEEL, HINDALCO, COALINDIA, VEDL — ≥6 edges each, v2 prompt quality
- Batch 4 JSON: RELIANCE, ONGC, BPCL, NTPC, POWERGRID, ADANIENT, ADANIPORTS, ADANIGREEN
- Both batches loaded into graph DB via POST /graph/seed
- Smoke test: crude oil shock propagation shows ONGC → BPCL → RELIANCE chain

**Status:** Pending

---

## Phase 2 — Seed Data: Auto, FMCG, Pharma & Stub Fixes (Medium Priority) 🟡

**Goal:** Complete remaining sector batches and fix all critical stub nodes — ensuring every Nifty 50 company has meaningful graph presence.

**Why second:** Fixes the most embarrassing gaps (TITAN with 2 edges, ITC with 1 edge). Auto and FMCG complete the consumer-facing sector coverage needed for RBI rate impact chains (rates → banks → auto loans → TATAMOTORS/MARUTI).

**Requirements:** SEED-05, SEED-06, SEED-07, SEED-08, SEED-09, SEED-10

**Deliverables:**
- Batch 5 JSON: BAJAJ-AUTO, EICHERMOT, HEROMOTOCO + upgraded TATAMOTORS, MARUTI, M&M, TATASTEEL
- Batch 6 JSON: ITC (full), HINDUNILVR (full), NESTLEIND, BRITANNIA, TATACONSUM, ASIANPAINT
- Critical stubs fixed: TITAN ≥8 edges, JSWSTEEL ≥8 edges, ITC ≥8 edges
- Batch 7 JSON: LT, ULTRACEMCO, GRASIM, BHARTIARTL, SHREECEM
- Pharma JSON: SUNPHARMA, DRREDDY, CIPLA, DIVISLAB, APOLLOHOSP
- All batches loaded and spot-checked

**Status:** Pending

---

## Phase 3 — Master Merge, Validation & Reload 🟡

**Goal:** Merge all batch files into a single authoritative nifty50_relationships.json, run full validation, reload the graph, and confirm end-to-end propagation chains work correctly.

**Why third:** All data work converges here. The graph isn't production-ready until validation passes and the demo-critical chains (RBI, crude oil, FMCG) produce meaningful multi-hop output.

**Requirements:** SEED-11, SEED-12, SEED-13

**Deliverables:**
- Master nifty50_relationships.json: banking_it_clean as base, v2 batches override v1 placeholders
- Validation script passes: all 50 companies ≥6 edges, zero stub nodes, no vague source_reference
- Graph reloaded via POST /graph/seed
- Smoke tests pass:
  - RBI rate change: Banking → Real Estate → Auto chain visible
  - Crude oil shock: ONGC → BPCL → RELIANCE → downstream chain visible
  - IT sector: USD/INR exposure chain visible (already works, regression check)
- PHASE_C_DATA_TRACKER.md updated to reflect completion

**Status:** Pending

---

## Phase 4 — Graph Engine Improvements 🔵

**Goal:** Fix the BFS path-weighting limitation, add cross-sector bridging edges, and expose MIN_IMPACT as a configurable parameter — making the propagation engine more accurate and flexible.

**Why fourth:** Data is now complete. Engine improvements are most valuable after the graph is fully populated (more paths = more cases where the first-visit limitation matters).

**Requirements:** GRAPH-01, GRAPH-02, GRAPH-03

**Deliverables:**
- BFS updated: track highest cumulative weight per node (not first-visited). Nodes may be updated in-place if a higher-weight path is found.
- Cross-sector bridging edges added to seed: HDFCBANK/ICICIBANK → real_estate_sector (lends_to), BAJFINANCE → auto_sector (lends_to, auto loans segment)
- PropagationRequest model: add optional `min_impact` field (default 0.2)
- Frontend depth selector: add "Sensitivity" control (min_impact 0.1 / 0.2 / 0.3)
- Regression tests: Banking/IT propagation output unchanged or improved

**Status:** Pending

---

## Phase 5 — Animated Propagation Visualization 🟣

**Goal:** Build the React Flow animated graph in the Impact tab — showing impact spreading outward depth-by-depth as a wave animation, with nodes colored by impact level and edges labeled by relationship type.

**Why fifth:** This is the visual differentiator. The data and engine are now solid, so the visualization will have real content to display. Building viz on incomplete data earlier would have shown empty/thin graphs.

**Requirements:** VIZ-01 through VIZ-07

**Deliverables:**
- @xyflow/react installed in finance-ui
- PropagationGraph component: directed graph, trigger node at center, BFS wave animation (300ms / 700ms / 1200ms per depth level)
- Node styles: red (≥70% impact), orange (≥50%), yellow (≥30%), grey (<30%)
- Edge thickness proportional to impact_score; edge label = relationship type
- Sector grouping: nodes visually clustered (Banking cluster, Energy cluster, etc.)
- Node click → navigate to /company/[ticker] for company nodes
- Panel appears below LLM analysis; existing table view toggled via "Table / Graph" switch
- Empty state: clear message when total_affected === 0

**Status:** Pending

---

## Phase 6 — UX Polish & Code Quality 🔧

**Goal:** Close the three known UX gaps and eliminate the code duplication that creates maintenance risk in the query pipeline.

**Why last:** Lower urgency than the graph/viz work, but important for code health before the v2.0 milestone is closed.

**Requirements:** UX-01, UX-02, CODE-01

**Deliverables:**
- Impact tab: affected company tickers are `<Link href="/company/[ticker]">` — clickable
- Chat tab: when opened from /company/[ticker] page, company field pre-populated with ticker
- Shared `_build_context(company_name, context_str)` helper extracted to `app/services/query_service.py`
- Both query.py stream endpoint and query_service.py use the shared helper
- Existing tests pass, no behaviour regression

**Status:** Pending

---

## Summary

| Phase | Name | Requirements | Priority |
|-------|------|-------------|----------|
| 1 | Seed Data: Metals & Energy | SEED-01–04 | 🔴 High |
| 2 | Seed Data: Auto, FMCG, Pharma & Stubs | SEED-05–10 | 🟡 Medium |
| 3 | Master Merge, Validation & Reload | SEED-11–13 | 🟡 Medium |
| 4 | Graph Engine Improvements | GRAPH-01–03 | 🔵 Engine |
| 5 | Animated Propagation Visualization | VIZ-01–07 | 🟣 Feature |
| 6 | UX Polish & Code Quality | UX-01–02, CODE-01 | 🔧 Polish |

**Total requirements:** 26 v1
**Estimated phases:** 6
