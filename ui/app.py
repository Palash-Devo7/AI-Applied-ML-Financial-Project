"""Finance AI RAG — Streamlit UI (Industrial/Utilitarian v2)."""
import json
import time
from datetime import datetime

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="FINANCE AI · RAG",
    page_icon="⬛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design System CSS ──────────────────────────────────────────────────────────

STYLES = """
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

:root {
  --bg-base:       #0B0B0F;
  --bg-panel:      #111116;
  --bg-elevated:   #18181F;
  --bg-hover:      #1E1E27;
  --border:        #232330;
  --border-active: #3A3A50;
  --text-primary:  #E2E2EE;
  --text-secondary:#7C7C99;
  --text-muted:    #3D3D55;
  --accent:        #2962FF;
  --accent-dim:    rgba(41,98,255,0.12);
  --accent-glow:   rgba(41,98,255,0.25);
  --success:       #26A69A;
  --danger:        #EF5350;
  --warning:       #F59E0B;
  --font-mono: 'JetBrains Mono', 'Courier New', monospace;
  --font-ui:   'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* ── Resets ── */
html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg-base) !important;
  color: var(--text-primary) !important;
}
* { box-sizing: border-box; }
[data-testid="stHeader"]   { display: none !important; }
[data-testid="stToolbar"]  { display: none !important; }
footer, #MainMenu          { display: none !important; }
.main .block-container     { padding: 0 !important; max-width: 100% !important; }

/* ── Global typography ── */
p, span, div, label, li, a {
  font-family: var(--font-ui) !important;
  color: var(--text-primary);
}
h1,h2,h3,h4,h5,h6 {
  color: var(--text-primary) !important;
  font-family: var(--font-ui) !important;
}
.stMarkdown p { color: var(--text-primary) !important; }
.stMarkdown code {
  font-family: var(--font-mono) !important;
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border) !important;
  border-radius: 2px !important;
  color: var(--accent) !important;
  padding: 1px 5px !important;
  font-size: 12px !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: var(--bg-panel) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding: 0 !important; }
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }
[data-testid="stSidebar"] .stMarkdown p { color: var(--text-secondary) !important; }
[data-testid="stSidebar"] hr { border-color: var(--border) !important; margin: 6px 0 !important; }

/* Sidebar radio as nav list */
[data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: 0 !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label {
  display: flex !important; align-items: center !important;
  padding: 7px 14px !important; margin: 0 !important;
  font-family: var(--font-mono) !important;
  font-size: 11px !important; letter-spacing: 0.1em !important;
  color: var(--text-secondary) !important;
  border-left: 2px solid transparent !important;
  border-radius: 0 !important; cursor: pointer !important;
  transition: all 0.12s !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
  background: var(--bg-hover) !important;
  color: var(--text-primary) !important;
  border-left-color: var(--border-active) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"],
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
  color: var(--text-primary) !important;
  border-left-color: var(--accent) !important;
  background: var(--accent-dim) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] input { display: none !important; }

/* ── Inputs ── */
.stTextInput input, .stNumberInput input, [data-testid="stTextInput"] input {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border) !important;
  color: var(--text-primary) !important;
  border-radius: 2px !important;
  font-family: var(--font-mono) !important;
  font-size: 12px !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--accent-glow) !important;
  outline: none !important;
}
.stSelectbox [data-baseweb="select"] > div {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border) !important;
  border-radius: 2px !important;
}
.stSelectbox [data-baseweb="select"] *,
[data-baseweb="popover"] * {
  color: var(--text-primary) !important;
  font-family: var(--font-mono) !important;
  font-size: 12px !important;
  background: var(--bg-elevated) !important;
}
[data-baseweb="menu"] { background: var(--bg-elevated) !important; border: 1px solid var(--border-active) !important; }
[data-baseweb="menu"] li:hover { background: var(--bg-hover) !important; }
.stSlider [data-baseweb="slider"] div { background: var(--accent) !important; }

/* ── Buttons ── */
.stButton > button {
  background: var(--accent) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 2px !important;
  font-family: var(--font-mono) !important;
  font-size: 11px !important;
  letter-spacing: 0.1em !important;
  font-weight: 600 !important;
  padding: 7px 16px !important;
  transition: opacity 0.15s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* ── Tabs (page navigation) ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: var(--bg-panel) !important;
  border-bottom: 1px solid var(--border) !important;
  gap: 0 !important; padding: 0 20px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--text-secondary) !important;
  font-family: var(--font-mono) !important;
  font-size: 11px !important;
  letter-spacing: 0.12em !important;
  padding: 14px 20px !important;
  border-radius: 0 !important;
  border-bottom: 2px solid transparent !important;
  text-transform: uppercase !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
  color: var(--text-primary) !important;
  border-bottom: 2px solid var(--accent) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none !important; }
[data-testid="stTabPanel"] { padding: 0 !important; background: var(--bg-base) !important; }

/* ── Chat input ── */
[data-testid="stChatInput"] {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border) !important;
  border-radius: 2px !important;
  margin: 0 0 0 0 !important;
}
[data-testid="stChatInput"]:focus-within {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px var(--accent-glow) !important;
}
[data-testid="stChatInput"] textarea {
  background: transparent !important;
  color: var(--text-primary) !important;
  font-family: var(--font-ui) !important;
  font-size: 14px !important;
}
[data-testid="stChatInput"] button {
  background: var(--accent) !important;
  border-radius: 2px !important;
  width: 40px !important;
  height: 40px !important;
}

/* ── Chat messages (remove default styling) ── */
[data-testid="stChatMessage"] {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  box-shadow: none !important;
}
[data-testid="stChatMessage"] > div { background: transparent !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  background: var(--bg-panel) !important;
  border: 1px dashed var(--border-active) !important;
  border-radius: 2px !important;
  padding: 8px !important;
}
[data-testid="stFileUploader"] * { color: var(--text-secondary) !important; }

/* ── Metrics ── */
[data-testid="stMetric"] {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border) !important;
  border-radius: 2px !important;
  padding: 16px !important;
}
[data-testid="stMetricValue"] {
  color: var(--accent) !important;
  font-family: var(--font-mono) !important;
  font-size: 1.8rem !important;
}
[data-testid="stMetricLabel"] {
  color: var(--text-muted) !important;
  font-family: var(--font-mono) !important;
  font-size: 10px !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
}
[data-testid="stMetricDelta"] { display: none; }

/* ── Expander ── */
[data-testid="stExpander"] {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border) !important;
  border-radius: 2px !important;
}
[data-testid="stExpander"] summary {
  color: var(--text-muted) !important;
  font-family: var(--font-mono) !important;
  font-size: 11px !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
}

/* ── Alerts ── */
[data-testid="stNotification"] { border-radius: 2px !important; }
[data-testid="stSuccess"]  { background: rgba(38,166,154,0.08) !important; border: 1px solid rgba(38,166,154,0.4) !important; border-radius: 2px !important; }
[data-testid="stError"]    { background: rgba(239,83,80,0.08)  !important; border: 1px solid rgba(239,83,80,0.4)  !important; border-radius: 2px !important; }
[data-testid="stInfo"]     { background: rgba(41,98,255,0.08)  !important; border: 1px solid rgba(41,98,255,0.4)  !important; border-radius: 2px !important; }
[data-testid="stWarning"]  { background: rgba(245,158,11,0.08) !important; border: 1px solid rgba(245,158,11,0.4) !important; border-radius: 2px !important; }
.stSuccess p, .stError p, .stInfo p, .stWarning p { font-size: 13px !important; }

/* ── Container / border wrapper ── */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border) !important;
  border-radius: 2px !important;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; margin: 8px 0 !important; }

/* ── Toggle ── */
[data-testid="stToggle"] span { background: var(--accent) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-active); border-radius: 2px; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: var(--accent) !important; }

/* ── Animations ── */
@keyframes pulse-dot {
  0%,100% { opacity:1; box-shadow:0 0 0 0 rgba(38,166,154,0.5); }
  50%      { opacity:.8; box-shadow:0 0 0 5px rgba(38,166,154,0); }
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
@keyframes spin-badge { from{transform:rotate(0)} to{transform:rotate(360deg)} }

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Custom Component Classes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

/* Topbar */
.topbar {
  display:flex; align-items:center; justify-content:space-between;
  height:48px; padding:0 24px;
  background: var(--bg-panel);
  border-bottom:1px solid var(--border);
  margin-bottom:0;
}
.topbar-logo { display:flex; align-items:baseline; gap:3px; }
.logo-finance {
  font-family:var(--font-mono) !important;
  font-size:14px; font-weight:600;
  color:var(--accent) !important; letter-spacing:0.12em;
}
.logo-ai {
  font-family:var(--font-mono) !important;
  font-size:14px; font-weight:600;
  color:var(--text-primary) !important;
}
.logo-rag {
  font-family:var(--font-mono) !important;
  font-size:9px; color:var(--text-muted) !important;
  letter-spacing:0.1em; margin-left:4px;
  border:1px solid var(--border); border-radius:2px;
  padding:1px 4px;
}
.topbar-right { display:flex; align-items:center; gap:10px; }
.model-pill {
  font-family:var(--font-mono) !important;
  font-size:11px; color:var(--text-muted) !important;
  border:1px solid var(--border); border-radius:2px; padding:3px 8px;
  letter-spacing:0.06em;
}
.health-dot { width:8px; height:8px; border-radius:50%; display:inline-block; }
.health-dot.on  { background:var(--success); animation:pulse-dot 2s ease-in-out infinite; }
.health-dot.off { background:var(--danger); }

/* Sidebar section label */
.sidebar-label {
  font-family:var(--font-mono) !important;
  font-size:10px; color:var(--text-muted) !important;
  letter-spacing:0.12em; text-transform:uppercase;
  padding:14px 14px 6px;
  display:block;
}

/* Stat pair */
.stat-row {
  display:flex; align-items:center; justify-content:space-between;
  padding:3px 14px;
}
.stat-label { font-family:var(--font-mono) !important; font-size:10px; color:var(--text-muted) !important; letter-spacing:0.08em; }
.stat-value { font-family:var(--font-mono) !important; font-size:13px; color:var(--accent) !important; font-weight:600; }

/* Recent query row */
.rq-row {
  display:flex; align-items:center; justify-content:space-between;
  padding:5px 14px; border-left:2px solid transparent;
  cursor:pointer; transition:all 0.1s;
}
.rq-row:hover { background:var(--bg-hover); border-left-color:var(--accent); }
.rq-text {
  font-family:var(--font-mono) !important; font-size:11px;
  color:var(--text-secondary) !important;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:155px;
}
.rq-time {
  font-family:var(--font-mono) !important; font-size:10px;
  color:var(--text-muted) !important;
  white-space:nowrap; margin-left:6px;
}

/* User bubble */
.user-row { display:flex; justify-content:flex-end; margin:18px 0 6px; }
.user-bubble {
  max-width:70%;
  background:var(--bg-elevated);
  border-right:2px solid var(--accent);
  border-radius:2px 0 0 2px;
  padding:12px 16px;
  font-size:14px; line-height:1.55;
  color:var(--text-primary) !important;
}
.bubble-time {
  font-family:var(--font-mono) !important;
  font-size:10px; color:var(--text-muted) !important;
  text-align:right; margin-top:6px;
}

/* AI response card */
.ai-card {
  background:var(--bg-panel);
  border-left:2px solid var(--border-active);
  padding:16px 20px; margin:6px 0;
  border-radius:0 2px 2px 0;
  font-size:14px; line-height:1.65;
  color:var(--text-primary) !important;
}
.ai-card p { color:var(--text-primary) !important; margin:0 0 8px; }
.ai-card ul,ol { color:var(--text-primary) !important; padding-left:20px; }
.ai-card li { color:var(--text-primary) !important; margin-bottom:4px; }
.ai-card strong { color:var(--text-primary) !important; }

/* Response meta footer */
.resp-meta {
  display:flex; align-items:center; gap:8px;
  margin-top:10px; padding-top:8px;
  border-top:1px solid var(--border);
  flex-wrap:wrap;
}
.meta-chip {
  font-family:var(--font-mono) !important;
  font-size:10px; color:var(--text-muted) !important;
  background:var(--bg-elevated);
  border:1px solid var(--border); border-radius:2px;
  padding:2px 7px; letter-spacing:0.08em;
}
.meta-chip.hl { color:var(--accent) !important; border-color:rgba(41,98,255,0.35); }

/* Source card */
.src-card {
  background:var(--bg-elevated);
  border-left:3px solid var(--border-active);
  padding:10px 12px; margin:5px 0;
  border-radius:0 2px 2px 0;
}
.src-card.hi { border-left-color:var(--success) !important; }
.src-card.md { border-left-color:var(--warning) !important; }
.src-card.lo { border-left-color:var(--danger)  !important; }

.pill-row { display:flex; flex-wrap:wrap; gap:4px; margin-bottom:6px; }
.pill {
  font-family:var(--font-mono) !important;
  font-size:10px; font-weight:600;
  padding:2px 6px; border-radius:2px; letter-spacing:0.06em;
}
.pill-co  { background:var(--accent-dim); color:var(--accent) !important; border:1px solid rgba(41,98,255,0.3); }
.pill-sec { background:var(--bg-hover); color:var(--text-secondary) !important; border:1px solid var(--border); }
.pill-yr  { background:var(--bg-hover); color:var(--text-muted) !important; border:1px solid var(--border); }

.score-track { height:2px; background:var(--border); border-radius:1px; margin:5px 0; }
.score-fill  { height:2px; border-radius:1px; }
.score-fill.hi { background:var(--success); }
.score-fill.md { background:var(--warning); }
.score-fill.lo { background:var(--danger);  }

.src-preview {
  font-size:12px; color:var(--text-secondary) !important;
  line-height:1.45;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
}
.src-page { font-family:var(--font-mono) !important; font-size:10px; color:var(--text-muted) !important; margin-top:4px; }

/* Context panel */
.ctx-header {
  font-family:var(--font-mono) !important;
  font-size:10px; color:var(--text-muted) !important;
  letter-spacing:0.12em; text-transform:uppercase;
  padding:16px 0 10px; border-bottom:1px solid var(--border); margin-bottom:10px;
}
.ctx-empty {
  font-family:var(--font-mono) !important;
  font-size:11px; color:var(--text-muted) !important;
  text-align:center; padding:48px 0; line-height:2;
}

/* Empty state */
.empty-state {
  display:flex; flex-direction:column; align-items:center;
  justify-content:center; padding:80px 20px; gap:20px;
}
.empty-title {
  font-family:var(--font-mono) !important;
  font-size:30px; font-weight:600; letter-spacing:0.14em;
  color:var(--text-muted) !important;
}
.chip-row { display:flex; flex-direction:column; gap:8px; width:100%; max-width:480px; }

/* Company filter indicator */
.filter-indicator {
  display:inline-flex; align-items:center; gap:5px;
  font-family:var(--font-mono) !important;
  font-size:11px; color:var(--text-muted) !important;
  margin-bottom:4px;
}
.fdot { width:6px; height:6px; border-radius:50%; flex-shrink:0; }
.fdot.on  { background:var(--accent); }
.fdot.off { background:var(--text-muted); }

/* Jobs table */
.jobs-table { width:100%; border-collapse:collapse; }
.jobs-table th {
  font-family:var(--font-mono) !important; font-size:10px;
  color:var(--text-muted) !important; letter-spacing:0.1em; text-transform:uppercase;
  text-align:left; padding:8px 10px;
  border-bottom:1px solid var(--border);
}
.jobs-table td {
  font-family:var(--font-mono) !important; font-size:12px;
  color:var(--text-primary) !important;
  padding:8px 10px; border-bottom:1px solid var(--border);
  vertical-align:top;
}
.jobs-table tr:hover td { background:var(--bg-hover); }
.badge {
  font-family:var(--font-mono) !important; font-size:10px; font-weight:600;
  padding:2px 7px; border-radius:2px; letter-spacing:0.08em; white-space:nowrap;
}
.badge-proc { background:rgba(41,98,255,0.15); color:var(--accent) !important; border:1px solid rgba(41,98,255,0.4); }
.badge-done { background:rgba(38,166,154,0.15); color:var(--success) !important; border:1px solid rgba(38,166,154,0.4); }
.badge-fail { background:rgba(239,83,80,0.15);  color:var(--danger)  !important; border:1px solid rgba(239,83,80,0.4);  }

/* Knowledge base company card */
.co-card {
  background:var(--bg-panel); border:1px solid var(--border);
  border-radius:2px; padding:14px 16px; margin-bottom:8px;
  cursor:pointer; transition:all 0.12s;
}
.co-card:hover { background:var(--bg-hover); border-color:var(--border-active); }
.co-name {
  font-size:14px; font-weight:600; color:var(--text-primary) !important;
  margin-bottom:8px;
}
.co-stats { display:flex; gap:16px; flex-wrap:wrap; }
.co-stat { font-family:var(--font-mono) !important; font-size:11px; color:var(--text-muted) !important; }
.co-stat b { color:var(--accent) !important; font-weight:600; }

/* Danger zone */
.danger-zone {
  border:1px solid rgba(239,83,80,0.35); border-radius:2px;
  padding:16px; background:rgba(239,83,80,0.04);
  margin-top:24px;
}
.danger-label {
  font-family:var(--font-mono) !important; font-size:10px; font-weight:600;
  color:var(--danger) !important; letter-spacing:0.14em; text-transform:uppercase;
  margin-bottom:8px;
}
.danger-zone .stButton > button {
  background:transparent !important;
  color:var(--danger) !important;
  border:1px solid rgba(239,83,80,0.6) !important;
}
.danger-zone .stButton > button:hover {
  background:rgba(239,83,80,0.1) !important;
}

/* Upload zone label */
.field-label {
  font-family:var(--font-mono) !important; font-size:10px;
  color:var(--text-muted) !important; letter-spacing:0.1em; text-transform:uppercase;
  margin-bottom:4px;
}
.field-req { color:var(--danger) !important; }

/* Content wrapper with padding */
.content-pad { padding:20px 24px; }
.content-pad-r { padding:20px 16px; border-left:1px solid var(--border); }
"""

st.markdown(f"<style>{STYLES}</style>", unsafe_allow_html=True)


# ── API Helpers ────────────────────────────────────────────────────────────────

def check_server() -> bool:
    try:
        return requests.get(f"{API_BASE}/health", timeout=3).status_code == 200
    except Exception:
        return False


@st.cache_data(ttl=30)
def fetch_companies() -> list:
    try:
        r = requests.get(f"{API_BASE}/collections/companies", timeout=5)
        return r.json().get("companies", []) if r.ok else []
    except Exception:
        return []


@st.cache_data(ttl=30)
def fetch_collection_info() -> dict:
    try:
        r = requests.get(f"{API_BASE}/collections", timeout=5)
        cols = r.json().get("collections", [{}]) if r.ok else [{}]
        return cols[0] if cols else {}
    except Exception:
        return {}


def fetch_jobs() -> list:
    try:
        r = requests.get(f"{API_BASE}/documents/jobs", timeout=5)
        return r.json() if r.ok and isinstance(r.json(), list) else []
    except Exception:
        return []


def stream_query(payload: dict):
    """SSE generator: yields (token, meta_or_None)."""
    with requests.post(
        f"{API_BASE}/query/stream",
        json=payload, stream=True, timeout=120,
        headers={"Accept": "text/event-stream"},
    ) as resp:
        resp.raise_for_status()
        meta = None
        for raw in resp.iter_lines():
            if not raw:
                continue
            line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            if not line.startswith("data: "):
                continue
            data = json.loads(line[6:])
            if data["type"] == "meta":
                meta = data
            elif data["type"] == "token":
                yield data["text"], meta
                meta = None
            elif data["type"] == "done":
                break
            elif data["type"] == "error":
                raise RuntimeError(data.get("text", "Stream error"))


# ── Session state init ─────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "recent_queries" not in st.session_state:
    st.session_state.recent_queries = []   # [{"text":..,"ts":..}]
if "last_context" not in st.session_state:
    st.session_state.last_context = []     # source list for right panel


# ── Server health (cached for topbar) ─────────────────────────────────────────

server_ok = check_server()
companies  = fetch_companies() if server_ok else []
info       = fetch_collection_info() if server_ok else {}


# ── Topbar ─────────────────────────────────────────────────────────────────────

health_cls   = "on" if server_ok else "off"
provider_env = "LLaMA 3.3 · Groq"    # update if you change provider

topbar_html = f"""
<div class="topbar">
  <div class="topbar-logo">
    <span class="logo-finance">FINANCE</span>
    <span class="logo-ai">AI</span>
    <span class="logo-rag">RAG</span>
  </div>
  <div class="topbar-right">
    <span class="model-pill">{provider_env}</span>
    <span class="health-dot {health_cls}" title="{'API Online' if server_ok else 'API Offline'}"></span>
  </div>
</div>
"""


# ── Sidebar ─────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(topbar_html, unsafe_allow_html=True)
    st.markdown('<div style="border-top:1px solid var(--border); margin:4px 0 0;"></div>', unsafe_allow_html=True)
    st.markdown('<span class="sidebar-label">Filters</span>', unsafe_allow_html=True)

    company_options = ["ALL COMPANIES"] + companies
    selected_company = st.selectbox("company", company_options, label_visibility="collapsed")

    top_k = st.number_input(
        "top_k", min_value=1, max_value=50, value=10, step=1,
        label_visibility="collapsed",
        help="Number of chunks to retrieve",
    )

    # Recent queries
    if st.session_state.recent_queries:
        st.markdown('<div style="border-top:1px solid var(--border); margin:8px 0;"></div>', unsafe_allow_html=True)
        st.markdown('<span class="sidebar-label">Recent Queries</span>', unsafe_allow_html=True)
        recent = st.session_state.recent_queries[-8:][::-1]
        rq_html = ""
        for q in recent:
            ts = q.get("ts", "")
            txt = q.get("text", "")[:50]
            rq_html += f'<div class="rq-row"><span class="rq-text">{txt}</span><span class="rq-time">{ts}</span></div>'
        st.markdown(rq_html, unsafe_allow_html=True)

    # System stats
    st.markdown('<div style="border-top:1px solid var(--border); margin:8px 0;"></div>', unsafe_allow_html=True)
    st.markdown('<span class="sidebar-label">System</span>', unsafe_allow_html=True)

    jobs_all  = fetch_jobs() if server_ok else []
    ingested  = [j for j in jobs_all if j.get("status") == "ingested"]
    total_chunks  = info.get("count", 0)
    total_cos     = len(companies)
    total_docs    = len(ingested)

    stats_html = f"""
    <div class="stat-row"><span class="stat-label">CHUNKS</span><span class="stat-value">{total_chunks:,}</span></div>
    <div class="stat-row"><span class="stat-label">COMPANIES</span><span class="stat-value">{total_cos}</span></div>
    <div class="stat-row"><span class="stat-label">DOCUMENTS</span><span class="stat-value">{total_docs}</span></div>
    """
    st.markdown(stats_html, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "What is the total revenue for FY2025?",
    "Summarise the key risk factors mentioned in the report.",
    "What are the total assets on the balance sheet?",
]

def score_class(s: float) -> str:
    if s >= 0.7: return "hi"
    if s >= 0.4: return "md"
    return "lo"

def fmt_source_card(src: dict, idx: int) -> str:
    sc  = src.get("score", 0)
    cls = score_class(sc)
    pct = int(sc * 100)
    co  = src.get("company") or src.get("ticker") or ""
    yr  = str(src["year"]) if src.get("year") else ""
    sec = src.get("section_type") or src.get("report_type") or ""
    pg  = src.get("page_num")
    txt = src.get("text", "")[:300]

    pills = ""
    if co:  pills += f'<span class="pill pill-co">{co}</span>'
    if yr:  pills += f'<span class="pill pill-yr">{yr}</span>'
    if sec: pills += f'<span class="pill pill-sec">{sec[:24]}</span>'

    page_ref = f'<div class="src-page">p.{pg}</div>' if pg else ""

    return f"""
    <div class="src-card {cls}">
      <div class="pill-row">{pills}</div>
      <div class="score-track"><div class="score-fill {cls}" style="width:{pct}%"></div></div>
      <div class="src-preview">{txt}</div>
      {page_ref}
    </div>
    """

def fmt_user_bubble(text: str, ts: str) -> str:
    return f"""
    <div class="user-row">
      <div class="user-bubble">
        {text}
        <div class="bubble-time">{ts}</div>
      </div>
    </div>
    """

def fmt_resp_meta(meta: dict) -> str:
    qt = meta.get("query_type", "GENERAL")
    cc = meta.get("chunk_count", 0)
    return f"""
    <div class="resp-meta">
      <span class="meta-chip hl">{qt}</span>
      <span class="meta-chip">{cc} SOURCES</span>
    </div>
    """

def render_history_message(msg: dict, show_sources: bool):
    ts = msg.get("ts", "")
    if msg["role"] == "user":
        st.markdown(fmt_user_bubble(msg["content"], ts), unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="ai-card">{msg["content"]}</div>', unsafe_allow_html=True)
        if msg.get("meta"):
            st.markdown(fmt_resp_meta(msg["meta"]), unsafe_allow_html=True)
        if msg.get("sources") and show_sources:
            with st.expander(f"▶ {len(msg['sources'])} SOURCES"):
                cards = "".join(fmt_source_card(s, i) for i, s in enumerate(msg["sources"], 1))
                st.markdown(cards, unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pages
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tab_chat, tab_docs, tab_kb = st.tabs(["CHAT", "DOCUMENTS", "KNOWLEDGE BASE"])


# ── CHAT ──────────────────────────────────────────────────────────────────────

with tab_chat:
    col_main, col_ctx = st.columns([3, 1])

    # ── Right context panel ──
    with col_ctx:
        st.markdown('<div class="content-pad-r">', unsafe_allow_html=True)
        st.markdown('<div class="ctx-header">RETRIEVED CONTEXT</div>', unsafe_allow_html=True)

        ctx_sources = st.session_state.last_context
        if ctx_sources:
            for src in ctx_sources:
                sc  = src.get("score", 0)
                cls = score_class(sc)
                co  = src.get("company") or src.get("ticker") or "—"
                sec = src.get("section_type") or src.get("report_type") or "—"
                yr  = str(src.get("year", "")) if src.get("year") else ""
                pct = int(sc * 100)
                txt = src.get("text", "")[:200]

                ctx_card = f"""
                <div class="src-card {cls}" style="margin-bottom:8px;">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
                    <span style="font-size:12px;font-weight:600;color:var(--text-primary)">{co}</span>
                    <span class="mono-val" style="font-family:var(--font-mono);font-size:11px;color:var(--accent)">{sc:.3f}</span>
                  </div>
                  <div style="font-family:var(--font-mono);font-size:10px;color:var(--text-muted);margin-bottom:4px;">{sec} {yr}</div>
                  <div class="score-track"><div class="score-fill {cls}" style="width:{pct}%"></div></div>
                  <div style="font-size:11px;color:var(--text-secondary);line-height:1.4;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">{txt}</div>
                </div>
                """
                st.markdown(ctx_card, unsafe_allow_html=True)
        else:
            st.markdown('<div class="ctx-empty">Context will appear<br>after a query</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Main chat area ──
    with col_main:
        st.markdown('<div class="content-pad">', unsafe_allow_html=True)

        # Filter bar
        fi_dot   = "on" if selected_company != "ALL COMPANIES" else "off"
        fi_label = selected_company if selected_company != "ALL COMPANIES" else "ALL COMPANIES"
        col_fi, col_src, col_clr = st.columns([3, 1, 1])
        with col_fi:
            st.markdown(
                f'<div class="filter-indicator"><span class="fdot {fi_dot}"></span>{fi_label} · TOP {top_k}</div>',
                unsafe_allow_html=True,
            )
        with col_src:
            show_sources = st.toggle("Sources", value=True)
        with col_clr:
            if st.session_state.messages and st.button("CLEAR", use_container_width=True):
                st.session_state.messages = []
                st.session_state.last_context = []
                st.rerun()

        st.markdown('<div style="border-top:1px solid var(--border);margin:6px 0 16px;"></div>', unsafe_allow_html=True)

        # Offline banner
        if not server_ok:
            st.error("API offline — start the server: `uvicorn app.main:app --reload --port 8000`")

        # Empty state
        if not st.session_state.messages:
            empty_html = '<div class="empty-state"><div class="empty-title">ASK ANYTHING</div>'
            st.markdown(empty_html, unsafe_allow_html=True)
            for ex in EXAMPLE_QUERIES:
                if st.button(ex, use_container_width=False, key=f"ex_{ex[:20]}"):
                    st.session_state._prefill = ex
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            # Render history
            for msg in st.session_state.messages:
                render_history_message(msg, show_sources)

        # Chat input
        prompt = st.chat_input("Ask about financials…")

        # Handle prefill from example chips
        if hasattr(st.session_state, "_prefill") and st.session_state._prefill:
            prompt = st.session_state._prefill
            del st.session_state._prefill

        if prompt and server_ok:
            ts = datetime.now().strftime("%H:%M")
            st.session_state.messages.append({"role": "user", "content": prompt, "ts": ts})
            st.session_state.recent_queries.append({"text": prompt, "ts": ts})

            # Render user bubble immediately
            st.markdown(fmt_user_bubble(prompt, ts), unsafe_allow_html=True)

            payload = {"question": prompt, "top_k": int(top_k), "include_sources": show_sources}
            if selected_company != "ALL COMPANIES":
                payload["company"] = selected_company

            state = {"meta": {}, "sources": [], "tokens": []}

            try:
                def token_generator():
                    for token, meta in stream_query(payload):
                        if meta:
                            state["meta"]    = meta
                            state["sources"] = meta.get("sources", [])
                        state["tokens"].append(token)
                        yield token

                # Stream into Streamlit — it renders inside the current context
                st.write_stream(token_generator())

                full_text = "".join(state["tokens"])
                collected_meta    = state["meta"]
                collected_sources = state["sources"]

                # Update right panel
                st.session_state.last_context = collected_sources

                # Meta footer
                if collected_meta:
                    st.markdown(fmt_resp_meta(collected_meta), unsafe_allow_html=True)

                # Sources expander
                if collected_sources and show_sources:
                    with st.expander(f"▶ {len(collected_sources)} SOURCES"):
                        cards = "".join(fmt_source_card(s, i) for i, s in enumerate(collected_sources, 1))
                        st.markdown(cards, unsafe_allow_html=True)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_text,
                    "sources": collected_sources,
                    "meta": collected_meta,
                    "ts": ts,
                })

            except Exception as e:
                st.error(f"Stream error: {e}")

        st.markdown('</div>', unsafe_allow_html=True)


# ── DOCUMENTS ─────────────────────────────────────────────────────────────────

with tab_docs:
    st.markdown('<div class="content-pad">', unsafe_allow_html=True)

    if not server_ok:
        st.error("API offline.")
    else:
        col_up, col_jobs = st.columns([1.2, 1])

        with col_up:
            st.markdown('<div class="field-label">Upload PDF <span class="field-req">*</span></div>', unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "PDF",
                type=["pdf"],
                label_visibility="collapsed",
            )

            if uploaded_file:
                st.info(f"`{uploaded_file.name}` — {uploaded_file.size / 1024:.1f} KB")

                with st.form("upload_form"):
                    r1c1, r1c2 = st.columns(2)
                    with r1c1:
                        st.markdown('<div class="field-label">Company <span class="field-req">*</span></div>', unsafe_allow_html=True)
                        company = st.text_input("company", placeholder="e.g. Tata Steel", label_visibility="collapsed")
                    with r1c2:
                        st.markdown('<div class="field-label">Report Type</div>', unsafe_allow_html=True)
                        report_type = st.selectbox(
                            "report_type",
                            ["Annual Report", "Integrated Report", "10-K", "10-Q", "Balance Sheet", "Earnings Report", "Other"],
                            label_visibility="collapsed",
                        )

                    r2c1, r2c2 = st.columns(2)
                    with r2c1:
                        st.markdown('<div class="field-label">Fiscal Year</div>', unsafe_allow_html=True)
                        year = st.number_input("year", 2000, 2030, 2024, step=1, label_visibility="collapsed")
                    with r2c2:
                        st.markdown('<div class="field-label">Ticker</div>', unsafe_allow_html=True)
                        ticker = st.text_input("ticker", placeholder="e.g. TATASTEEL", label_visibility="collapsed")

                    st.markdown('<div class="field-label">Sector (optional)</div>', unsafe_allow_html=True)
                    sector = st.text_input("sector", placeholder="e.g. Steel", label_visibility="collapsed")

                    submitted = st.form_submit_button("UPLOAD & INGEST", type="primary", use_container_width=True)

                if submitted:
                    if not company.strip():
                        st.error("Company name is required.")
                    else:
                        with st.spinner("Uploading…"):
                            result = requests.post(
                                f"{API_BASE}/documents/upload",
                                files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")},
                                data={k: v for k, v in {
                                    "company": company, "year": str(year),
                                    "report_type": report_type,
                                    "ticker": ticker, "sector": sector,
                                }.items() if v},
                                timeout=30,
                            )
                        if result.ok:
                            doc_id = result.json().get("document_id", "")[:22]
                            st.success(f"Queued — `{doc_id}…`  |  Processing in background.")
                            st.cache_data.clear()
                        else:
                            st.error(f"Upload failed: {result.text}")

        with col_jobs:
            col_jh, col_jr = st.columns([2, 1])
            with col_jh:
                st.markdown('<div class="field-label" style="padding-top:6px;">Ingestion Jobs</div>', unsafe_allow_html=True)
            with col_jr:
                if st.button("REFRESH", use_container_width=True):
                    st.rerun()

            jobs = fetch_jobs()
            any_proc = any(j.get("status") == "processing" for j in jobs)

            if not jobs:
                st.markdown('<div class="ctx-empty">No uploads yet.</div>', unsafe_allow_html=True)
            else:
                rows = ""
                for job in reversed(jobs):
                    s = job.get("status", "")
                    badge_cls = {"processing": "badge-proc", "ingested": "badge-done", "failed": "badge-fail"}.get(s, "badge-proc")
                    badge_txt = {"processing": "⟳ PROCESSING", "ingested": "✓ COMPLETE", "failed": "✗ FAILED"}.get(s, s.upper())
                    fn     = job.get("filename", "—")[:30]
                    co     = job.get("company", "—")
                    chunks = f'{job["chunk_count"]:,}' if job.get("chunk_count") else "—"
                    rows += f"""
                    <tr>
                      <td style="max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{fn}</td>
                      <td>{co}</td>
                      <td><span class="badge {badge_cls}">{badge_txt}</span></td>
                      <td style="color:var(--accent)">{chunks}</td>
                    </tr>
                    """
                table = f"""
                <table class="jobs-table" style="margin-top:8px;">
                  <thead><tr>
                    <th>FILE</th><th>COMPANY</th><th>STATUS</th><th>CHUNKS</th>
                  </tr></thead>
                  <tbody>{rows}</tbody>
                </table>
                """
                st.markdown(table, unsafe_allow_html=True)

            # Auto-refresh while processing
            if any_proc:
                time.sleep(3)
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ── KNOWLEDGE BASE ─────────────────────────────────────────────────────────────

with tab_kb:
    st.markdown('<div class="content-pad">', unsafe_allow_html=True)

    if not server_ok:
        st.error("API offline.")
    else:
        jobs_kb   = fetch_jobs()
        ing_jobs  = [j for j in jobs_kb if j.get("status") == "ingested"]
        cos_kb    = fetch_companies()

        # Metric cards
        m1, m2, m3 = st.columns(3)
        m1.metric("TOTAL CHUNKS",  f"{info.get('count', 0):,}")
        m2.metric("COMPANIES",     str(len(cos_kb)))
        m3.metric("DOCUMENTS",     f"{len(ing_jobs)} / {len(jobs_kb)}")

        st.markdown('<div style="border-top:1px solid var(--border);margin:20px 0 16px;"></div>', unsafe_allow_html=True)

        col_cos, col_docs = st.columns(2)

        with col_cos:
            st.markdown('<div class="field-label">Companies</div>', unsafe_allow_html=True)
            if not cos_kb:
                st.markdown('<div class="ctx-empty">No companies yet.<br>Upload a document.</div>', unsafe_allow_html=True)
            else:
                for co in cos_kb:
                    co_chunks = sum(j.get("chunk_count", 0) for j in ing_jobs if j.get("company") == co)
                    co_docs   = sum(1 for j in ing_jobs if j.get("company") == co)
                    card_html = f"""
                    <div class="co-card">
                      <div class="co-name">{co}</div>
                      <div class="co-stats">
                        <span class="co-stat"><b>{co_chunks:,}</b> chunks</span>
                        <span class="co-stat"><b>{co_docs}</b> docs</span>
                      </div>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)

        with col_docs:
            st.markdown('<div class="field-label">Documents</div>', unsafe_allow_html=True)
            if not jobs_kb:
                st.markdown('<div class="ctx-empty">No documents.</div>', unsafe_allow_html=True)
            else:
                for job in reversed(jobs_kb):
                    s     = job.get("status", "")
                    bcls  = {"processing": "badge-proc", "ingested": "badge-done", "failed": "badge-fail"}.get(s, "")
                    btxt  = {"processing": "PROCESSING", "ingested": "COMPLETE", "failed": "FAILED"}.get(s, s.upper())
                    fn    = job.get("filename", "—")
                    co    = job.get("company", "")
                    rt    = job.get("report_type", "")
                    yr    = str(job.get("year", "")) if job.get("year") else ""
                    ck    = f'{job["chunk_count"]:,}' if job.get("chunk_count") else ""

                    meta_bits = " · ".join(filter(None, [co, rt, yr]))
                    chunk_bit = f'<span style="font-family:var(--font-mono);font-size:11px;color:var(--accent)">{ck}</span>' if ck else ""

                    doc_card = f"""
                    <div class="co-card">
                      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
                        <span style="font-size:13px;font-weight:600;color:var(--text-primary);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{fn}</span>
                        <span class="badge {bcls}">{btxt}</span>
                      </div>
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted)">{meta_bits}</span>
                        {chunk_bit}
                      </div>
                    </div>
                    """
                    st.markdown(doc_card, unsafe_allow_html=True)

        # Danger zone
        st.markdown('<div class="danger-zone">', unsafe_allow_html=True)
        st.markdown('<div class="danger-label">⚠ Danger Zone</div>', unsafe_allow_html=True)
        st.markdown('<p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px;">Permanently deletes ALL documents and vectors from the knowledge base.</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        confirm = st.text_input("Type DELETE to confirm", label_visibility="visible", placeholder="DELETE")
        if st.button("DELETE COLLECTION", use_container_width=True):
            if confirm == "DELETE":
                r = requests.delete(f"{API_BASE}/collections/finance_docs", timeout=30)
                if r.ok:
                    st.success("Collection deleted.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(r.text)
            else:
                st.error("Type DELETE to confirm.")

    st.markdown('</div>', unsafe_allow_html=True)
