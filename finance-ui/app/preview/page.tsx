"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  getGuestCredits,
  getFinancials,
  getStockSummary,
  streamPreviewQuery,
  previewForecast,
  previewSearchCompanies,
  previewCompanyStatus,
  type ForecastResult,
  type AgentView,
  type AnnualFinancial,
  type StockSummary,
  type PreviewForecastRequest,
  type CompanySearchResult,
} from "@/lib/api";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  ArrowLeft, Loader2, Send, TrendingUp, TrendingDown,
  Minus, Sparkles, Search, Lock,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function generateUUID(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

function fmt(n: number | undefined | null, prefix = "", suffix = "") {
  if (n === undefined || n === null) return "—";
  return `${prefix}${n.toLocaleString("en-IN")}${suffix}`;
}

const EVENT_TYPES = [
  "earnings_beat", "earnings_miss", "management_change",
  "regulatory_action", "acquisition", "macro_shock",
  "capacity_expansion", "debt_restructuring", "sector_disruption", "geopolitical",
];

const STANCE_STYLES: Record<string, string> = {
  BULLISH: "text-green-400 bg-green-400/10 border-green-400/20",
  BEARISH: "text-red-400 bg-red-400/10 border-red-400/20",
  NEUTRAL: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
};

const STANCE_ICON: Record<string, typeof TrendingUp> = {
  BULLISH: TrendingUp,
  BEARISH: TrendingDown,
  NEUTRAL: Minus,
};

// ─── Credit badge ─────────────────────────────────────────────────────────────

function CreditBadge({ remaining, limit }: { remaining: number; limit: number }) {
  const color = remaining === 0
    ? "text-red-400 border-red-400/30 bg-red-400/10"
    : remaining === 1
    ? "text-yellow-400 border-yellow-400/30 bg-yellow-400/10"
    : "text-green-400 border-green-400/30 bg-green-400/10";
  return (
    <span className={cn("text-xs font-mono px-3 py-1 rounded-full border", color)}>
      {remaining}/{limit} credits
    </span>
  );
}

// ─── Company search autocomplete ─────────────────────────────────────────────

function CompanySearch({ onSelect }: { onSelect: (ticker: string, name: string) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CompanySearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const search = useCallback((q: string) => {
    if (q.trim().length < 2) { setResults([]); setOpen(false); return; }
    setSearching(true);
    previewSearchCompanies(q)
      .then((r) => { setResults(r); setOpen(r.length > 0); })
      .catch(() => setResults([]))
      .finally(() => setSearching(false));
  }, []);

  function handleInput(e: React.ChangeEvent<HTMLInputElement>) {
    const v = e.target.value;
    setQuery(v);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => search(v), 280);
  }

  function pick(r: CompanySearchResult) {
    setQuery(r.name);
    setOpen(false);
    onSelect(r.ticker, r.name);
  }

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={wrapperRef} className="relative w-full max-w-lg">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          value={query}
          onChange={handleInput}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder="Search — e.g. Tata, HDFC, Reliance"
          className="w-full h-12 pl-10 pr-4 rounded-xl bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          autoComplete="off"
        />
        {searching && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground animate-spin" />
        )}
      </div>

      {open && results.length > 0 && (
        <div className="absolute top-full mt-1 w-full z-50 rounded-xl border border-border bg-card shadow-xl overflow-hidden max-h-72 overflow-y-auto">
          {results.map((r) => (
            <button
              key={r.scrip_code}
              onMouseDown={() => pick(r)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-primary/10 transition-colors text-left border-b border-border last:border-0"
            >
              <div className="flex flex-col gap-0.5">
                <span className="text-foreground text-sm font-medium">{r.name}</span>
                {r.industry && <span className="text-muted-foreground text-xs">{r.industry}</span>}
              </div>
              <span className="text-primary text-xs font-mono ml-4 shrink-0">{r.ticker}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Not-loaded nudge ─────────────────────────────────────────────────────────

function NotLoadedNudge({
  companyName,
  ticker,
  router,
}: {
  companyName: string;
  ticker: string;
  router: ReturnType<typeof useRouter>;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-10 text-center space-y-5 mt-2">
      <div className="flex justify-center">
        <div className="h-14 w-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
          <Lock className="h-6 w-6 text-primary" />
        </div>
      </div>
      <div>
        <p className="text-foreground font-semibold text-lg">{companyName}</p>
        <p className="text-muted-foreground text-xs font-mono mt-0.5">{ticker}</p>
      </div>
      <p className="text-muted-foreground text-sm leading-relaxed max-w-sm mx-auto">
        This company&apos;s data hasn&apos;t been loaded yet. Sign up free to load it — the system will auto-fetch filings, financials, and stock data from BSE.
      </p>
      <button
        onClick={() => router.push("/auth/login")}
        className="px-6 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/90 transition-colors"
      >
        Sign up free to load this company
      </button>
      <p className="text-muted-foreground text-xs">
        Or try a pre-loaded stock:{" "}
        {["TATASTEEL", "HDFCBANK", "RELIANCE"].map((t, i) => (
          <span key={t}>
            {i > 0 && " · "}
            <button
              onClick={() => router.push(`/preview?q=${t}`)}
              className="text-primary underline underline-offset-2 bg-transparent border-none cursor-pointer p-0 text-xs"
            >
              {t}
            </button>
          </span>
        ))}
      </p>
    </div>
  );
}

// ─── Signup nudge (credits exhausted) ────────────────────────────────────────

function SignupNudge({ router }: { router: ReturnType<typeof useRouter> }) {
  return (
    <div className="rounded-xl border border-primary/30 bg-primary/5 p-8 text-center space-y-4 mt-6">
      <p className="text-foreground font-semibold text-lg">You&apos;ve used all 3 free credits.</p>
      <p className="text-muted-foreground text-sm leading-relaxed">
        Create a free account to get{" "}
        <span className="text-foreground font-medium">10 credits per day</span> — no card required.
      </p>
      <button
        onClick={() => router.push("/auth/login")}
        className="px-6 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/90 transition-colors"
      >
        Create free account
      </button>
      <p className="text-xs text-muted-foreground">
        Already have an account?{" "}
        <button
          onClick={() => router.push("/auth/login")}
          className="text-primary underline underline-offset-2 bg-transparent border-none cursor-pointer p-0 text-xs"
        >
          Sign in
        </button>
      </p>
    </div>
  );
}

// ─── Overview tab ─────────────────────────────────────────────────────────────

function OverviewTab({ dbCompanyName, ticker }: { dbCompanyName: string; ticker: string }) {
  const [financials, setFinancials] = useState<AnnualFinancial[] | null>(null);
  const [stock, setStock] = useState<StockSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.allSettled([
      getFinancials(dbCompanyName),
      getStockSummary(ticker),
    ]).then(([finRes, stockRes]) => {
      if (finRes.status === "fulfilled") setFinancials(finRes.value.annual_financials);
      if (stockRes.status === "fulfilled") setStock(stockRes.value);
    }).finally(() => setLoading(false));
  }, [dbCompanyName, ticker]);

  if (loading) {
    return (
      <div className="flex items-center gap-3 py-16 text-muted-foreground justify-center">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading data…
      </div>
    );
  }

  const sorted = financials ? [...financials].sort((a, b) => a.fiscal_year - b.fiscal_year) : [];
  const chartData = sorted.map((f) => ({
    year: `FY${f.fiscal_year}`,
    Revenue: f.revenue ? Math.round(f.revenue) : 0,
    Profit: f.net_income ? Math.round(f.net_income) : 0,
  }));

  return (
    <div className="space-y-6">
      {/* Stock price summary */}
      {stock?.summary && (
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="flex flex-wrap items-end gap-6">
            <div>
              <p className="text-muted-foreground text-xs uppercase tracking-wider mb-1">Latest Price</p>
              <p className="text-3xl font-bold text-foreground">
                {stock.summary.latest_close ? `₹${stock.summary.latest_close.toLocaleString("en-IN")}` : "—"}
              </p>
              {stock.summary.latest_date && (
                <p className="text-muted-foreground text-xs mt-0.5">{stock.summary.latest_date}</p>
              )}
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              {[
                { label: "52W High", value: fmt(stock.summary.week52_high, "₹") },
                { label: "52W Low", value: fmt(stock.summary.week52_low, "₹") },
                { label: "Avg Close", value: fmt(stock.summary.avg_close, "₹") },
              ].map(({ label, value }) => (
                <div key={label} className="flex flex-col gap-0.5">
                  <span className="text-muted-foreground text-xs uppercase tracking-wider">{label}</span>
                  <span className="text-foreground font-semibold text-sm">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Revenue chart */}
      {chartData.length > 0 ? (
        <div className="rounded-xl border border-border bg-card p-5">
          <h3 className="text-foreground font-semibold mb-4 text-sm">Revenue vs Net Profit (₹ Cr)</h3>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="gRevenue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gProfit" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="year" stroke="#6B7280" tick={{ fontSize: 11 }} />
              <YAxis stroke="#6B7280" tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  background: "#0f0f14",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: 8,
                  color: "#f0f0f5",
                  fontSize: 12,
                }}
              />
              <Area type="monotone" dataKey="Revenue" stroke="#a78bfa" fill="url(#gRevenue)" strokeWidth={2} />
              <Area type="monotone" dataKey="Profit" stroke="#10B981" fill="url(#gProfit)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="text-muted-foreground text-sm text-center py-8">No financial data available yet.</p>
      )}

      {/* Financial table */}
      {sorted.length > 0 && (
        <div className="rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left px-4 py-3 text-muted-foreground font-medium">Year</th>
                <th className="text-right px-4 py-3 text-muted-foreground font-medium">Revenue</th>
                <th className="text-right px-4 py-3 text-muted-foreground font-medium">Net Income</th>
                <th className="text-right px-4 py-3 text-muted-foreground font-medium">EPS</th>
                <th className="text-right px-4 py-3 text-muted-foreground font-medium">Net Margin</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((f) => (
                <tr key={f.fiscal_year} className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors">
                  <td className="px-4 py-3 text-foreground font-medium">FY{f.fiscal_year}</td>
                  <td className="px-4 py-3 text-right text-foreground">{fmt(f.revenue, "₹", " Cr")}</td>
                  <td className="px-4 py-3 text-right text-foreground">{fmt(f.net_income, "₹", " Cr")}</td>
                  <td className="px-4 py-3 text-right text-foreground">{fmt(f.eps, "₹")}</td>
                  <td className="px-4 py-3 text-right text-foreground">
                    {f.net_margin != null ? `${f.net_margin.toFixed(1)}%` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Chat tab ─────────────────────────────────────────────────────────────────

function ChatTab({
  dbCompanyName,
  guestToken,
  creditsRemaining,
  onCreditUpdate,
  onGuestLimit,
}: {
  dbCompanyName: string;
  guestToken: string;
  creditsRemaining: number;
  onCreditUpdate: (n: number) => void;
  onGuestLimit: () => void;
}) {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [hasQueried, setHasQueried] = useState(false);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  function submit() {
    if (!question.trim() || streaming || creditsRemaining < 1) return;
    setStreaming(true);
    setAnswer("");
    setError("");
    setHasQueried(true);

    abortRef.current = streamPreviewQuery(
      question.trim(),
      dbCompanyName,
      guestToken,
      (chunk) => {
        setAnswer((p) => p + chunk);
        bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      },
      (remaining) => {
        onCreditUpdate(remaining);
        setStreaming(false);
        // Don't call onGuestLimit() here — let the user read the answer first.
        // The nudge appears below the answer when creditsRemaining === 0.
      },
      (err, isGuestLimit) => {
        setStreaming(false);
        if (isGuestLimit) { onGuestLimit(); onCreditUpdate(0); }
        else setError(err.message || "Something went wrong.");
      }
    );
  }

  const canSubmit = question.trim().length > 0 && !streaming && creditsRemaining >= 1;

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-card p-5 space-y-3">
        <p className="text-muted-foreground text-sm">
          Ask anything about <span className="text-foreground font-medium">{dbCompanyName}</span> — financials, risks, strategy, or filings.
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
            placeholder="e.g. What is the revenue trend for the last 3 years?"
            disabled={creditsRemaining < 1}
            className="flex-1 h-10 px-3 rounded-lg bg-background border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-40"
          />
          <button
            onClick={submit}
            disabled={!canSubmit}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium text-sm disabled:opacity-40 hover:bg-primary/90 transition-colors"
          >
            {streaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            {streaming ? "Thinking…" : "Ask"}
          </button>
        </div>
        <p className="text-muted-foreground text-xs">1 credit per query</p>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {hasQueried && (
        <div className="rounded-xl border border-border bg-card p-5 min-h-[80px]">
          {streaming && !answer && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="h-4 w-4 animate-spin" /> Analysing filings…
            </div>
          )}
          {answer && (
            <div className="prose prose-sm prose-invert max-w-none text-sm leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {creditsRemaining === 0 && hasQueried && !streaming && (
        <SignupNudge router={router} />
      )}
    </div>
  );
}

// ─── Forecast tab ─────────────────────────────────────────────────────────────

function ForecastTab({
  dbCompanyName,
  guestToken,
  creditsRemaining,
  onCreditUpdate,
  onGuestLimit,
}: {
  dbCompanyName: string;
  guestToken: string;
  creditsRemaining: number;
  onCreditUpdate: (n: number) => void;
  onGuestLimit: () => void;
}) {
  const router = useRouter();
  const [eventType, setEventType] = useState("earnings_beat");
  const [description, setDescription] = useState("");
  const [horizon, setHorizon] = useState(90);
  const [result, setResult] = useState<ForecastResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    if (!description.trim() || description.trim().length < 10 || loading || creditsRemaining < 2) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const payload: PreviewForecastRequest = {
        company: dbCompanyName,
        event_type: eventType,
        event_description: description.trim(),
        horizon_days: horizon,
        guest_token: guestToken,
      };
      const r = await previewForecast(payload);
      setResult(r);
      const newRemaining = Math.max(0, creditsRemaining - 2);
      onCreditUpdate(newRemaining);
      // Don't call onGuestLimit() — let the user read the result first.
    } catch (e) {
      const err = e as Error & { isGuestLimit?: boolean };
      if (err.isGuestLimit) { onGuestLimit(); onCreditUpdate(0); }
      else setError(err.message || "Forecast failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-card p-6 space-y-4">
        <div>
          <h3 className="text-foreground font-semibold">Run Event Forecast</h3>
          <p className="text-muted-foreground text-sm mt-1">
            Describe a hypothetical event for <span className="text-foreground">{dbCompanyName}</span> — get a Bull / Bear / Macro multi-agent analysis.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="text-muted-foreground text-xs uppercase tracking-wider block mb-1.5">Event Type</label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {EVENT_TYPES.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-muted-foreground text-xs uppercase tracking-wider block mb-1.5">Horizon (days)</label>
            <input
              type="number" min={30} max={365} value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
              className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        <div>
          <label className="text-muted-foreground text-xs uppercase tracking-wider block mb-1.5">Event Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. Q4 FY2026 earnings beat estimates by 15%, strong margin guidance…"
            rows={3}
            className="w-full px-3 py-2 rounded-lg bg-background border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          />
          <p className="text-muted-foreground text-xs mt-1">{description.trim().length}/1000 chars (min 10)</p>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={run}
            disabled={loading || description.trim().length < 10 || creditsRemaining < 2}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm disabled:opacity-40 hover:bg-primary/90 transition-colors"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? "Running agents…" : "Run Forecast"}
          </button>
          <span className="text-muted-foreground text-xs">2 credits per forecast</span>
        </div>

        {creditsRemaining === 1 && (
          <p className="text-yellow-400 text-xs">
            1 credit left — not enough for a forecast (costs 2). Use the Ask tab instead.
          </p>
        )}
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {result && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="text-muted-foreground text-sm">Overall confidence:</span>
            <span className={cn(
              "text-xs font-semibold px-2.5 py-1 rounded-full border",
              result.confidence === "HIGH" ? "text-green-400 bg-green-400/10 border-green-400/20"
                : result.confidence === "LOW" ? "text-red-400 bg-red-400/10 border-red-400/20"
                : "text-yellow-400 bg-yellow-400/10 border-yellow-400/20"
            )}>
              {result.confidence}
            </span>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            {result.agent_views.map((view: AgentView) => {
              const Icon = STANCE_ICON[view.stance] ?? Minus;
              return (
                <div key={view.agent} className="rounded-xl border border-border bg-card p-5 flex flex-col gap-3">
                  <div className="flex items-center justify-between">
                    <span className="text-foreground text-sm font-semibold capitalize">{view.agent} view</span>
                    <span className={cn("flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full border", STANCE_STYLES[view.stance] ?? STANCE_STYLES.NEUTRAL)}>
                      <Icon className="h-3.5 w-3.5" />{view.stance}
                    </span>
                  </div>
                  <ul className="space-y-1.5">
                    {view.key_points.map((pt, i) => (
                      <li key={i} className="text-foreground text-xs leading-relaxed flex gap-2">
                        <span className="text-primary mt-0.5 shrink-0">•</span>{pt}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            {[
              { label: "Base Case", text: result.base_case, color: "text-blue-400" },
              { label: "Bull Case", text: result.bull_case, color: "text-green-400" },
              { label: "Bear Case", text: result.bear_case, color: "text-red-400" },
            ].map(({ label, text, color }) => (
              <div key={label} className="rounded-xl border border-border bg-card p-5">
                <h4 className={cn("text-sm font-semibold mb-2", color)}>{label}</h4>
                <p className="text-muted-foreground text-sm leading-relaxed">{text}</p>
              </div>
            ))}
          </div>

          {(result.key_risks.length > 0 || result.key_catalysts.length > 0) && (
            <div className="grid gap-4 sm:grid-cols-2">
              {result.key_risks.length > 0 && (
                <div className="rounded-xl border border-border bg-card p-5">
                  <h4 className="text-red-400 text-sm font-semibold mb-3">Key Risks</h4>
                  <ul className="space-y-1.5">
                    {result.key_risks.map((r, i) => (
                      <li key={i} className="text-foreground text-xs leading-relaxed flex gap-2">
                        <span className="text-red-400 shrink-0">•</span>{r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {result.key_catalysts.length > 0 && (
                <div className="rounded-xl border border-border bg-card p-5">
                  <h4 className="text-green-400 text-sm font-semibold mb-3">Key Catalysts</h4>
                  <ul className="space-y-1.5">
                    {result.key_catalysts.map((c, i) => (
                      <li key={i} className="text-foreground text-xs leading-relaxed flex gap-2">
                        <span className="text-green-400 shrink-0">•</span>{c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {creditsRemaining === 0 && result && !loading && (
        <SignupNudge router={router} />
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

type CompanyStatus = "checking" | "ready" | "not_loaded";
type Tab = "overview" | "chat" | "forecast";

export default function PreviewPage() {
  const router = useRouter();

  // Guest token + credits
  const [guestToken, setGuestToken] = useState("");
  const [creditsRemaining, setCreditsRemaining] = useState(3);
  const [creditsLoaded, setCreditsLoaded] = useState(false);
  const [guestLimitHit, setGuestLimitHit] = useState(false);

  // Selected company
  const [displayName, setDisplayName] = useState("");   // from BSE search
  const [ticker, setTicker] = useState("");
  const [dbCompanyName, setDbCompanyName] = useState(""); // exact name from registry
  const [companyStatus, setCompanyStatus] = useState<CompanyStatus>("checking");
  const [tab, setTab] = useState<Tab>("overview");

  // Init guest token
  useEffect(() => {
    let token = localStorage.getItem("guest_token");
    if (!token) { token = generateUUID(); localStorage.setItem("guest_token", token); }
    setGuestToken(token);
  }, []);

  // Fetch credits
  useEffect(() => {
    if (!guestToken) return;
    getGuestCredits(guestToken)
      .then((c) => { setCreditsRemaining(c.remaining); if (c.remaining === 0) setGuestLimitHit(true); })
      .catch(() => {})
      .finally(() => setCreditsLoaded(true));
  }, [guestToken]);

  async function handleCompanySelect(t: string, name: string) {
    setTicker(t);
    setDisplayName(name);
    setDbCompanyName("");
    setCompanyStatus("checking");
    setTab("overview");
    try {
      const s = await previewCompanyStatus(t);
      if (s.status === "ready") {
        setDbCompanyName(s.company ?? name);
        setCompanyStatus("ready");
      } else {
        setCompanyStatus("not_loaded");
      }
    } catch {
      setCompanyStatus("not_loaded");
    }
  }

  const TABS: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "chat", label: "Ask a Question" },
    { key: "forecast", label: "Event Forecast" },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-border">
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors text-sm"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <span className="font-bold text-sm">QuantCortex Preview</span>
        </div>
        <div className="flex items-center gap-3">
          {creditsLoaded && <CreditBadge remaining={creditsRemaining} limit={3} />}
          <button
            onClick={() => router.push("/auth/login")}
            className="px-4 py-1.5 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/90 transition-colors"
          >
            Sign up free
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Company search — always visible */}
        <div className="space-y-4">
          {!displayName && (
            <>
              <div>
                <h1 className="text-2xl font-bold mb-1">Search any BSE listed company</h1>
                <p className="text-muted-foreground text-sm">
                  No sign-up needed. 3 free credits — 1 per query, 2 per forecast.
                </p>
              </div>
            </>
          )}

          <CompanySearch onSelect={handleCompanySelect} />

          {!displayName && (
            <div>
              <p className="text-muted-foreground text-xs uppercase tracking-wider mb-3">Popular stocks</p>
              <div className="flex flex-wrap gap-2">
                {[
                  { ticker: "TATASTEEL", name: "Tata Steel Ltd" },
                  { ticker: "HDFCBANK", name: "HDFC Bank Ltd" },
                  { ticker: "RELIANCE", name: "Reliance Industries Ltd" },
                  { ticker: "INFY", name: "Infosys Ltd" },
                  { ticker: "WIPRO", name: "Wipro Ltd" },
                ].map((s) => (
                  <button
                    key={s.ticker}
                    onClick={() => handleCompanySelect(s.ticker, s.name)}
                    className="px-4 py-2 rounded-lg border border-border bg-card text-sm hover:border-primary/50 hover:bg-primary/5 transition-colors"
                  >
                    <span className="font-mono text-primary text-xs mr-2">{s.ticker}</span>
                    <span className="text-foreground">{s.name}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Company view */}
        {displayName && (
          <div className="space-y-6">
            {/* Company header */}
            <div className="flex items-start justify-between gap-4 py-2 border-b border-border">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => { setDisplayName(""); setTicker(""); setDbCompanyName(""); }}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ArrowLeft className="h-4 w-4" />
                </button>
                <div>
                  <h2 className="text-xl font-bold">{displayName}</h2>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-primary text-xs font-mono">{ticker}</span>
                    {companyStatus === "checking" && (
                      <span className="text-muted-foreground text-xs flex items-center gap-1">
                        <Loader2 className="h-3 w-3 animate-spin" /> checking…
                      </span>
                    )}
                    {companyStatus === "ready" && (
                      <span className="text-green-400 text-xs">data ready</span>
                    )}
                  </div>
                </div>
              </div>
              {companyStatus === "ready" && (
                <div className="text-muted-foreground text-xs text-right shrink-0">
                  <span className="text-primary">1 credit</span> per query &nbsp;·&nbsp;
                  <span className="text-primary">2 credits</span> per forecast
                </div>
              )}
            </div>

            {/* Not loaded */}
            {companyStatus === "not_loaded" && (
              <NotLoadedNudge companyName={displayName} ticker={ticker} router={router} />
            )}

            {/* Checking */}
            {companyStatus === "checking" && (
              <div className="flex items-center gap-3 py-12 justify-center text-muted-foreground text-sm">
                <Loader2 className="h-4 w-4 animate-spin" /> Checking data availability…
              </div>
            )}

            {/* Loaded — tabs */}
            {companyStatus === "ready" && (
              <>
                <div className="flex border-b border-border">
                  {TABS.map((t) => (
                    <button
                      key={t.key}
                      onClick={() => setTab(t.key)}
                      className={cn(
                        "px-5 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors",
                        tab === t.key
                          ? "border-primary text-foreground"
                          : "border-transparent text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>

                {guestLimitHit ? (
                  <SignupNudge router={router} />
                ) : (
                  <>
                    {tab === "overview" && (
                      <OverviewTab dbCompanyName={dbCompanyName} ticker={ticker} />
                    )}
                    {tab === "chat" && (
                      <ChatTab
                        dbCompanyName={dbCompanyName}
                        guestToken={guestToken}
                        creditsRemaining={creditsRemaining}
                        onCreditUpdate={setCreditsRemaining}
                        onGuestLimit={() => setGuestLimitHit(true)}
                      />
                    )}
                    {tab === "forecast" && (
                      <ForecastTab
                        dbCompanyName={dbCompanyName}
                        guestToken={guestToken}
                        creditsRemaining={creditsRemaining}
                        onCreditUpdate={setCreditsRemaining}
                        onGuestLimit={() => setGuestLimitHit(true)}
                      />
                    )}
                  </>
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
