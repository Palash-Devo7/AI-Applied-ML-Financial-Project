"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  getCompanyStatus,
  getFinancials,
  getStockSummary,
  forecastEvent,
  streamQuery,
  type CompanyStatus,
  type AnnualFinancial,
  type StockSummary,
  type ForecastResult,
  type AgentView,
  type ForecastRequest,
  type ChatMessage,
} from "@/lib/api";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { ArrowLeft, TrendingUp, TrendingDown, Minus, Send, Loader2, FileText } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

// ─── Hero bar ────────────────────────────────────────────────────────────────

function fmt(n: number | undefined | null, prefix = "", suffix = "") {
  if (n === undefined || n === null) return "—";
  return `${prefix}${n.toLocaleString("en-IN")}${suffix}`;
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-muted-foreground text-xs uppercase tracking-wider">{label}</span>
      <span className="text-foreground font-semibold">{value}</span>
    </div>
  );
}

function HeroBar({
  ticker,
  status,
  stock,
}: {
  ticker: string;
  status: CompanyStatus | null;
  stock: StockSummary | null;
}) {
  const price = stock?.summary?.latest_close;
  const high52 = stock?.summary?.week52_high;
  const low52 = stock?.summary?.week52_low;

  return (
    <div className="flex flex-wrap items-center gap-x-8 gap-y-2 py-5 border-b border-border">
      <div>
        <h1 className="text-2xl font-bold text-foreground">
          {status?.company ?? ticker}
        </h1>
        <span className="text-muted-foreground text-sm font-mono">{ticker}</span>
      </div>
      {price !== undefined && (
        <div className="flex items-center gap-2">
          <span className="text-3xl font-bold text-foreground">
            ₹{price.toLocaleString("en-IN")}
          </span>
        </div>
      )}
      <div className="flex flex-wrap gap-x-6 gap-y-2 ml-auto">
        <StatItem label="52W High" value={fmt(high52, "₹")} />
        <StatItem label="52W Low" value={fmt(low52, "₹")} />
        <StatItem
          label="Status"
          value={status?.status ?? "—"}
        />
      </div>
    </div>
  );
}

// ─── Overview tab ────────────────────────────────────────────────────────────

function OverviewTab({ financials }: { financials: AnnualFinancial[] | null }) {
  if (!financials) {
    return (
      <div className="flex items-center gap-3 py-12 text-muted-foreground justify-center">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading financials…
      </div>
    );
  }

  if (financials.length === 0) {
    return (
      <p className="text-muted-foreground text-center py-12 text-sm">
        No financial data yet. Data loads in the background — check back shortly.
      </p>
    );
  }

  const sorted = [...financials].sort((a, b) => a.fiscal_year - b.fiscal_year);
  const chartData = sorted.map((f) => ({
    year: String(f.fiscal_year),
    Revenue: f.revenue ? Math.round(f.revenue) : 0,
    Profit: f.net_income ? Math.round(f.net_income) : 0,
  }));

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-foreground font-semibold mb-4">Revenue vs Net Profit (₹ Cr)</h3>
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="gRevenue" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gProfit" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="year" stroke="#6B7280" tick={{ fontSize: 12 }} />
            <YAxis stroke="#6B7280" tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                background: "#0F0F17",
                border: "1px solid #1A1A2E",
                borderRadius: 8,
                color: "#F1F1F3",
              }}
            />
            <Area
              type="monotone"
              dataKey="Revenue"
              stroke="#4F46E5"
              fill="url(#gRevenue)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="Profit"
              stroke="#10B981"
              fill="url(#gProfit)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Key metrics table */}
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
                  {f.net_margin !== undefined && f.net_margin !== null
                    ? `${f.net_margin.toFixed(1)}%`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Forecast tab ─────────────────────────────────────────────────────────────

const EVENT_TYPES = [
  "earnings_beat",
  "earnings_miss",
  "management_change",
  "regulatory_action",
  "acquisition",
  "macro_shock",
  "capacity_expansion",
  "debt_restructuring",
  "sector_disruption",
  "geopolitical",
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

function ForecastTab({ companyName }: { companyName: string }) {
  const { refreshCredits } = useAuth();
  const [eventType, setEventType] = useState("earnings_beat");
  const [description, setDescription] = useState("");
  const [horizon, setHorizon] = useState(90);
  const [result, setResult] = useState<ForecastResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!description.trim() || description.trim().length < 10) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const payload: ForecastRequest = {
        company: companyName,
        event_type: eventType,
        event_description: description.trim(),
        horizon_days: horizon,
      };
      const r = await forecastEvent(payload);
      setResult(r);
      refreshCredits().catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Forecast failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Input form */}
      <div className="rounded-xl border border-border bg-card p-6 space-y-4">
        <h3 className="text-foreground font-semibold">Run Event Forecast</h3>
        <p className="text-muted-foreground text-sm">
          Describe a hypothetical event for <span className="text-foreground">{companyName}</span> and get
          a multi-agent bull/bear/macro analysis.
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="text-muted-foreground text-xs uppercase tracking-wider block mb-1.5">
              Event Type
            </label>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {EVENT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/_/g, " ")}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-muted-foreground text-xs uppercase tracking-wider block mb-1.5">
              Horizon (days)
            </label>
            <input
              type="number"
              min={30}
              max={365}
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
              className="w-full h-10 px-3 rounded-lg bg-background border border-border text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>

        <div>
          <label className="text-muted-foreground text-xs uppercase tracking-wider block mb-1.5">
            Event Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. Q4 FY2026 earnings beat estimates by 15%, strong guidance on margins…"
            rows={3}
            className="w-full px-3 py-2 rounded-lg bg-background border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          />
          <p className="text-muted-foreground text-xs mt-1">
            {description.trim().length}/1000 chars (min 10)
          </p>
        </div>

        <button
          onClick={run}
          disabled={loading || description.trim().length < 10}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm disabled:opacity-40 hover:bg-primary/90 transition-colors"
        >
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          {loading ? "Running agents…" : "Run Forecast"}
        </button>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Confidence badge */}
          <div className="flex items-center gap-3">
            <span className="text-muted-foreground text-sm">Overall confidence:</span>
            <span className={cn(
              "text-xs font-semibold px-2.5 py-1 rounded-full border",
              result.confidence === "HIGH"
                ? "text-green-400 bg-green-400/10 border-green-400/20"
                : result.confidence === "LOW"
                ? "text-red-400 bg-red-400/10 border-red-400/20"
                : "text-yellow-400 bg-yellow-400/10 border-yellow-400/20"
            )}>
              {result.confidence}
            </span>
          </div>

          {/* Agent cards */}
          <div className="grid gap-4 sm:grid-cols-3">
            {result.agent_views.map((view: AgentView) => {
              const Icon = STANCE_ICON[view.stance] ?? Minus;
              return (
                <div
                  key={view.agent}
                  className="rounded-xl border border-border bg-card p-5 flex flex-col gap-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-foreground text-sm font-semibold capitalize">
                      {view.agent} view
                    </span>
                    <span
                      className={cn(
                        "flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full border",
                        STANCE_STYLES[view.stance] ?? STANCE_STYLES.NEUTRAL
                      )}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      {view.stance}
                    </span>
                  </div>
                  <ul className="space-y-1.5">
                    {view.key_points.map((pt, i) => (
                      <li key={i} className="text-foreground text-xs leading-relaxed flex gap-2">
                        <span className="text-primary mt-0.5 shrink-0">•</span>
                        {pt}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
          </div>

          {/* Cases */}
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

          {/* Risks & Catalysts */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-border bg-card p-5">
              <h4 className="text-red-400 text-sm font-semibold mb-3">Key Risks</h4>
              <ul className="space-y-2">
                {result.key_risks.map((r, i) => (
                  <li key={i} className="text-muted-foreground text-sm flex gap-2">
                    <span className="text-red-400 shrink-0">↓</span>{r}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-border bg-card p-5">
              <h4 className="text-green-400 text-sm font-semibold mb-3">Key Catalysts</h4>
              <ul className="space-y-2">
                {result.key_catalysts.map((c, i) => (
                  <li key={i} className="text-muted-foreground text-sm flex gap-2">
                    <span className="text-green-400 shrink-0">↑</span>{c}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Chat tab ─────────────────────────────────────────────────────────────────

function ChatTab({ companyName }: { companyName: string }) {
  const { refreshCredits } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const ctrlRef = useRef<AbortController | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function send() {
    const q = input.trim();
    if (!q || streaming) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setStreaming(true);

    let buf = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    ctrlRef.current = streamQuery(
      q,
      companyName || undefined,
      (chunk) => {
        buf += chunk;
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: buf };
          return updated;
        });
      },
      () => { setStreaming(false); refreshCredits().catch(() => {}); },
      () => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: buf || "Sorry, something went wrong.",
          };
          return updated;
        });
        setStreaming(false);
      }
    );
  }

  return (
    <div className="flex flex-col h-[520px]">
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <p className="text-muted-foreground text-center py-12 text-sm">
            Ask anything about {companyName} — filings, financials, risks, guidance…
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={cn(
              "rounded-2xl px-4 py-3 text-sm leading-relaxed",
              m.role === "user"
                ? "ml-auto max-w-[80%] bg-primary text-primary-foreground"
                : "w-full bg-card border border-border text-foreground prose-chat"
            )}
          >
            {!m.content ? (
              <span className="flex gap-1">
                <span className="animate-bounce">.</span>
                <span className="animate-bounce" style={{ animationDelay: "0.1s" }}>.</span>
                <span className="animate-bounce" style={{ animationDelay: "0.2s" }}>.</span>
              </span>
            ) : m.role === "user" ? (
              m.content
            ) : (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ children }) => <h1 className="text-lg font-bold text-foreground mt-4 mb-2 first:mt-0">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-base font-bold text-foreground mt-4 mb-2 first:mt-0">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-semibold text-foreground mt-3 mb-1.5 first:mt-0">{children}</h3>,
                  p: ({ children }) => <p className="text-foreground mb-2 last:mb-0 leading-relaxed">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc list-outside ml-4 mb-2 space-y-1">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal list-outside ml-4 mb-2 space-y-1">{children}</ol>,
                  li: ({ children }) => <li className="text-foreground leading-relaxed">{children}</li>,
                  strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                  em: ({ children }) => <em className="italic text-muted-foreground">{children}</em>,
                  code: ({ children }) => <code className="bg-muted px-1.5 py-0.5 rounded text-xs font-mono text-foreground">{children}</code>,
                  blockquote: ({ children }) => <blockquote className="border-l-2 border-primary pl-3 my-2 text-muted-foreground italic">{children}</blockquote>,
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-3">
                      <table className="w-full text-xs border-collapse">{children}</table>
                    </div>
                  ),
                  th: ({ children }) => <th className="text-left px-3 py-2 bg-muted text-muted-foreground font-medium border border-border">{children}</th>,
                  td: ({ children }) => <td className="px-3 py-2 border border-border text-foreground">{children}</td>,
                  hr: () => <hr className="border-border my-3" />,
                }}
              >
                {m.content}
              </ReactMarkdown>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-3 border-t border-border pt-4">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask a question…"
          className="flex-1 h-11 px-4 rounded-xl bg-card border border-border text-foreground placeholder:text-muted-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <button
          onClick={send}
          disabled={streaming || !input.trim()}
          className="h-11 px-4 rounded-xl bg-primary text-primary-foreground disabled:opacity-40 hover:bg-primary/90 transition-colors flex items-center gap-2"
        >
          {streaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

export default function CompanyView({ ticker }: { ticker: string }) {
  const router = useRouter();
  const [status, setStatus] = useState<CompanyStatus | null>(null);
  const [financials, setFinancials] = useState<AnnualFinancial[] | null>(null);
  const [stock, setStock] = useState<StockSummary | null>(null);

  // Poll status + re-fetch financials/stock whenever data arrives
  useEffect(() => {
    let stopped = false;
    let hasPrices = false;
    let hasFinancials = false;

    async function fetchMarketData() {
      getStockSummary(ticker).then(setStock).catch(() => null);
      getFinancials(ticker)
        .then((d) => { if (d.annual_financials.length > 0) setFinancials(d.annual_financials); })
        .catch(() => null);
    }

    // Initial fetch
    fetchMarketData();

    async function poll() {
      while (!stopped) {
        try {
          const s = await getCompanyStatus(ticker);
          setStatus(s);

          // Re-fetch market data when prices or financials become available for the first time
          const newPrices = !!s.prices_synced_at;
          const newFinancials = (s.doc_count ?? 0) > 0;
          if ((newPrices && !hasPrices) || (newFinancials && !hasFinancials)) {
            fetchMarketData();
            hasPrices = newPrices;
            hasFinancials = newFinancials;
          }

          if (s.status === "ready") {
            fetchMarketData(); // final refresh on ready
            break;
          }
        } catch { /* ignore */ }
        await new Promise((r) => setTimeout(r, 5000));
      }
    }
    poll();
    return () => { stopped = true; };
  }, [ticker]);

  const companyName = status?.company ?? ticker;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6 text-sm"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>

        <HeroBar ticker={ticker} status={status} stock={stock} />

        {/* Ingestion progress banner */}
        {status && status.status !== "ready" && (
          <div className="mt-4 flex items-center gap-3 px-4 py-3 rounded-xl border border-primary/20 bg-primary/5 text-sm">
            <Loader2 className="h-4 w-4 text-primary animate-spin shrink-0" />
            <div className="flex-1">
              <span className="text-foreground font-medium">Loading company data in background</span>
              <span className="text-muted-foreground ml-2">
                — financials ready, ingesting filings
                {status.doc_count ? ` (${status.doc_count} docs so far)` : ""}
              </span>
            </div>
            <span className="text-muted-foreground flex items-center gap-1 text-xs">
              <FileText className="h-3.5 w-3.5" />
              Chat available once docs are indexed
            </span>
          </div>
        )}

        {status?.status === "ready" && (status.doc_count ?? 0) > 0 && (
          <div className="mt-4 flex items-center gap-2 px-4 py-2.5 rounded-xl border border-green-500/20 bg-green-500/5 text-sm text-green-400">
            <FileText className="h-4 w-4 shrink-0" />
            {status.doc_count} documents indexed — all features available
          </div>
        )}

        <Tabs defaultValue="overview" className="mt-6">
          <TabsList className="bg-card border border-border">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="forecast">Forecast</TabsTrigger>
            <TabsTrigger value="chat">Chat</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="mt-6">
            <OverviewTab financials={financials} />
          </TabsContent>

          <TabsContent value="forecast" className="mt-6">
            <ForecastTab companyName={companyName} />
          </TabsContent>

          <TabsContent value="chat" className="mt-6">
            <ChatTab companyName={companyName} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
