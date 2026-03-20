const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

// ─── Token management (module-level, set by AuthProvider) ────────────────────

let _token: string | null = null;

export function setAuthToken(t: string) {
  _token = t;
}

export function clearAuthToken() {
  _token = null;
}

// ─── Core request helper ──────────────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string>),
  };
  if (_token) headers["Authorization"] = `Bearer ${_token}`;

  const res = await fetch(`${API}${path}`, { ...init, headers });

  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined") {
      clearAuthToken();
      localStorage.removeItem("auth_token");
      window.location.href = "/auth/login";
    }
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json();
}

// ─── Auth API ─────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: string;
  email: string;
  role: string;
  api_key?: string;
  is_verified?: boolean;
}

export interface Credits {
  used: number;
  limit: number;
  remaining: number;
  role: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  api_key: string;
}

export async function authLogin(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export async function authRegister(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export interface MeResponse extends AuthUser {
  credits: Credits;
}

export async function authMe(): Promise<MeResponse> {
  return request<MeResponse>("/auth/me");
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface CompanyResult {
  scrip_code: string;
  ticker: string;
  name: string;
  isin?: string;
  group?: string;
  market_cap?: string;
}

export interface CompanyStatus {
  ticker: string;
  company: string;          // full name, e.g. "Tata Consultancy Services Ltd"
  scrip_code?: string;
  exchange?: string;
  status: string;
  loaded_at?: string | null;
  doc_count?: number;
  prices_synced_at?: string | null;
}

export interface AnnualFinancial {
  fiscal_year: number;
  revenue?: number;
  net_income?: number;
  ebitda?: number;
  eps?: number;
  gross_margin?: number;
  net_margin?: number;
}

export interface FinancialsResponse {
  company: string;
  ticker: string | null;
  annual_financials: AnnualFinancial[];
}

export interface StockSummary {
  ticker: string;
  summary: {
    latest_close: number;
    latest_date: string;
    week52_high: number;
    week52_low: number;
    avg_close: number;
    max_volume: number | null;
  };
}

export interface ForecastRequest {
  company: string;           // must match company name in KB
  event_type: string;        // e.g. "earnings_beat"
  event_description: string; // 10–1000 chars
  horizon_days?: number;     // 30–365, default 90
}

export interface AgentView {
  agent: string;
  stance: "BULLISH" | "BEARISH" | "NEUTRAL";
  estimated_impact: string;
  key_points: string[];
  reasoning: string;
}

export interface ForecastResult {
  forecast_id: string;
  company: string;
  event_type: string;
  agent_views: AgentView[];
  base_case: string;
  bull_case: string;
  bear_case: string;
  confidence: string;
  key_risks: string[];
  key_catalysts: string[];
  latency_ms: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

// ─── Company endpoints ────────────────────────────────────────────────────────

export async function searchCompanies(q: string): Promise<CompanyResult[]> {
  if (!q.trim()) return [];
  const data = await request<{ results: CompanyResult[]; query: string }>(
    `/companies/search?q=${encodeURIComponent(q)}`
  );
  return data.results ?? [];
}

export async function loadCompany(ticker: string): Promise<{ status: string; message?: string }> {
  return request(`/companies/load`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
}

export async function getCompanyStatus(ticker: string): Promise<CompanyStatus> {
  return request<CompanyStatus>(`/companies/status/${ticker}`);
}

// ─── Market data endpoints ────────────────────────────────────────────────────

export async function getFinancials(ticker: string): Promise<FinancialsResponse> {
  return request<FinancialsResponse>(`/market/financials/${ticker}`);
}

export async function getStockSummary(ticker: string): Promise<StockSummary> {
  return request<StockSummary>(`/market/stock/${ticker}/summary`);
}

// ─── Forecast ─────────────────────────────────────────────────────────────────

export async function forecastEvent(payload: ForecastRequest): Promise<ForecastResult> {
  return request<ForecastResult>(`/forecast/event`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// ─── Query / Chat ─────────────────────────────────────────────────────────────

export async function queryChat(
  question: string,
  company?: string
): Promise<{ answer: string; sources: string[] }> {
  return request(`/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, company }),
  });
}

export function streamQuery(
  question: string,
  company: string | undefined,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: Error) => void
): AbortController {
  const ctrl = new AbortController();
  const streamHeaders: Record<string, string> = { "Content-Type": "application/json" };
  if (_token) streamHeaders["Authorization"] = `Bearer ${_token}`;
  fetch(`${API}/query/stream`, {
    method: "POST",
    headers: streamHeaders,
    body: JSON.stringify({ question, company }),
    signal: ctrl.signal,
  })
    .then(async (res) => {
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response body");
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === "token" && event.text) onChunk(event.text);
          } catch {
            // ignore malformed lines
          }
        }
      }
      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") onError(err);
    });
  return ctrl;
}
