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
    const detail = body?.detail;
    const message = typeof detail === "string"
      ? detail
      : detail?.message ?? `${res.status} ${res.statusText}`;
    throw new Error(message);
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
  financials_synced_at?: string | null;
  progress_msg?: string | null;
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
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail = body?.detail;
        const message = typeof detail === "string"
          ? detail
          : detail?.message ?? `${res.status} ${res.statusText}`;
        throw new Error(message);
      }
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

// ─── Feedback API ─────────────────────────────────────────────────────────────

export interface FeedbackPayload {
  feature: "forecast" | "chat" | "both";
  succeeded: "yes" | "partially" | "no";
  accuracy?: number;
  speed?: number;
  ease?: number;
  issues?: string[];
  comment?: string;
  company?: string;
  query?: string;
  response_time_ms?: number;
  had_error?: boolean;
}

export function submitFeedback(payload: FeedbackPayload): Promise<{ status: string }> {
  return request("/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// ─── Guest preview ────────────────────────────────────────────────────────────

export interface GuestCredits {
  used: number;
  limit: number;
  remaining: number;
}

export interface CompanySearchResult {
  scrip_code: string;
  ticker: string;
  name: string;
  industry?: string;
}

export async function previewSearchCompanies(q: string): Promise<CompanySearchResult[]> {
  if (!q || q.trim().length < 2) return [];
  const res = await fetch(`${API}/preview/search?q=${encodeURIComponent(q.trim())}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.results ?? [];
}

export async function previewCompanyStatus(ticker: string): Promise<{ status: string; company?: string }> {
  const res = await fetch(`${API}/preview/company-status/${encodeURIComponent(ticker)}`);
  if (!res.ok) return { status: "unknown" };
  return res.json();
}

export async function getGuestCredits(guestToken: string): Promise<GuestCredits> {
  const res = await fetch(`${API}/preview/credits?guest_token=${encodeURIComponent(guestToken)}`);
  if (!res.ok) throw new Error("Failed to fetch guest credits");
  return res.json();
}

export function streamPreviewQuery(
  question: string,
  company: string | undefined,
  guestToken: string,
  onChunk: (text: string) => void,
  onDone: (creditsRemaining: number) => void,
  onError: (err: Error, isGuestLimit?: boolean) => void
): AbortController {
  const ctrl = new AbortController();
  fetch(`${API}/query/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, company: company || undefined, guest_token: guestToken }),
    signal: ctrl.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        const detail = body?.detail;
        const isGuestLimit = detail?.error === "guest_limit_reached";
        const message = typeof detail === "string"
          ? detail
          : detail?.message ?? `${res.status} ${res.statusText}`;
        onError(new Error(message), isGuestLimit);
        return;
      }
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
            else if (event.type === "done") onDone(event.credits_remaining ?? 0);
            else if (event.type === "error") onError(new Error(event.text));
          } catch {
            // ignore malformed lines
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") onError(err);
    });
  return ctrl;
}

export interface PreviewForecastRequest {
  company: string;
  event_type: string;
  event_description: string;
  horizon_days?: number;
  guest_token: string;
}

export async function previewForecast(payload: PreviewForecastRequest): Promise<ForecastResult> {
  const res = await fetch(`${API}/forecast/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body?.detail;
    const isGuestLimit = detail?.error === "guest_limit_reached";
    const message = typeof detail === "string"
      ? detail
      : detail?.message ?? `${res.status} ${res.statusText}`;
    const err = new Error(message) as Error & { isGuestLimit?: boolean };
    err.isGuestLimit = isGuestLimit;
    throw err;
  }
  return res.json();
}

// ─── Admin API ────────────────────────────────────────────────────────────────

export interface AdminUser {
  id: string;
  email: string;
  role: string;
  is_verified: number;
  is_active: number;
  created_at: string;
  credits_used_today: number;
}

export async function adminListUsers(): Promise<AdminUser[]> {
  const data = await request<{ users: AdminUser[] }>("/auth/admin/users");
  return data.users;
}

export interface AdminStats {
  totals: {
    total_users: number;
    verified_users: number;
    active_today: number;
    total_actions: number;
    total_forecasts: number;
    total_queries: number;
    total_loads: number;
  };
  signups_by_day: { day: string; count: number }[];
  dau_by_day: { date: string; count: number }[];
  endpoint_usage: { endpoint: string; count: number; credits: number }[];
  loaded_companies: { company: string; ticker: string; status: string; loaded_at: string }[];
}

export async function adminGetStats(): Promise<AdminStats> {
  return request<AdminStats>("/auth/admin/stats");
}
