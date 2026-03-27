"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  getGuestCredits,
  streamPreviewQuery,
  previewForecast,
  type ForecastResult,
  type AgentView,
  type PreviewForecastRequest,
} from "@/lib/api";
import { ArrowLeft, Loader2, Send, TrendingUp, TrendingDown, Minus, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function generateUUID(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

const POPULAR_TICKERS = ["TATASTEEL", "HDFCBANK", "RELIANCE", "INFY", "WIPRO"];

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
  const pct = (remaining / limit) * 100;
  const color = remaining === 0 ? "text-red-400 border-red-400/30 bg-red-400/10"
    : remaining === 1 ? "text-yellow-400 border-yellow-400/30 bg-yellow-400/10"
    : "text-green-400 border-green-400/30 bg-green-400/10";
  return (
    <span className={cn("text-xs font-mono px-3 py-1 rounded-full border", color)}>
      {remaining}/{limit} credits
    </span>
  );
}

// ─── Signup nudge ─────────────────────────────────────────────────────────────

function SignupNudge({ router }: { router: ReturnType<typeof useRouter> }) {
  return (
    <div className="rounded-xl border border-primary/30 bg-primary/5 p-8 text-center space-y-4 mt-6">
      <p className="text-foreground font-semibold text-lg">You&apos;ve used all 3 free credits.</p>
      <p className="text-muted-foreground text-sm leading-relaxed">
        Create a free account to get <span className="text-foreground font-medium">10 credits per day</span> — no card required.
      </p>
      <button
        onClick={() => router.push("/auth/login")}
        className="px-6 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary/90 transition-colors"
      >
        Create free account
      </button>
      <div className="text-xs text-muted-foreground">
        Already have an account?{" "}
        <button onClick={() => router.push("/auth/login")} className="text-primary underline underline-offset-2 bg-transparent border-none cursor-pointer p-0 text-xs">
          Sign in
        </button>
      </div>
    </div>
  );
}

// ─── Chat tab ─────────────────────────────────────────────────────────────────

function ChatTab({
  company,
  guestToken,
  creditsRemaining,
  onCreditUpdate,
  onGuestLimit,
}: {
  company: string;
  guestToken: string;
  creditsRemaining: number;
  onCreditUpdate: (n: number) => void;
  onGuestLimit: () => void;
}) {
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
      company,
      guestToken,
      (chunk) => {
        setAnswer((p) => p + chunk);
        bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      },
      (remaining) => {
        onCreditUpdate(remaining);
        setStreaming(false);
        if (remaining === 0) onGuestLimit();
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
          Ask anything about <span className="text-foreground font-medium">{company}</span> — financials, risks, strategy, or filings.
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
        <div className="rounded-xl border border-border bg-card p-5">
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
    </div>
  );
}

// ─── Forecast tab ─────────────────────────────────────────────────────────────

function ForecastTab({
  company,
  guestToken,
  creditsRemaining,
  onCreditUpdate,
  onGuestLimit,
}: {
  company: string;
  guestToken: string;
  creditsRemaining: number;
  onCreditUpdate: (n: number) => void;
  onGuestLimit: () => void;
}) {
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
        company,
        event_type: eventType,
        event_description: description.trim(),
        horizon_days: horizon,
        guest_token: guestToken,
      };
      const r = await previewForecast(payload);
      setResult(r);
      // Forecast costs 2 credits
      const newRemaining = Math.max(0, creditsRemaining - 2);
      onCreditUpdate(newRemaining);
      if (newRemaining === 0) onGuestLimit();
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
            Describe a hypothetical event for <span className="text-foreground">{company}</span> — get a Bull / Bear / Macro multi-agent analysis.
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
        {creditsRemaining < 2 && creditsRemaining > 0 && (
          <p className="text-yellow-400 text-xs">You have {creditsRemaining} credit left — not enough for a forecast (costs 2). Use it for a query instead.</p>
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
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PreviewPage() {
  const router = useRouter();
  const [guestToken, setGuestToken] = useState("");
  const [creditsRemaining, setCreditsRemaining] = useState(3);
  const [creditsLoaded, setCreditsLoaded] = useState(false);
  const [company, setCompany] = useState("");
  const [activeCompany, setActiveCompany] = useState(""); // confirmed selection
  const [tab, setTab] = useState<"chat" | "forecast">("chat");
  const [guestLimitHit, setGuestLimitHit] = useState(false);

  useEffect(() => {
    let token = localStorage.getItem("guest_token");
    if (!token) {
      token = generateUUID();
      localStorage.setItem("guest_token", token);
    }
    setGuestToken(token);
  }, []);

  useEffect(() => {
    if (!guestToken) return;
    getGuestCredits(guestToken)
      .then((c) => {
        setCreditsRemaining(c.remaining);
        if (c.remaining === 0) setGuestLimitHit(true);
      })
      .catch(() => {})
      .finally(() => setCreditsLoaded(true));
  }, [guestToken]);

  function selectCompany() {
    const t = company.trim().toUpperCase();
    if (t) setActiveCompany(t);
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Top bar */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-border">
        <button
          onClick={() => router.push("/")}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors text-sm"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
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
        {/* Company picker */}
        {!activeCompany ? (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold mb-1">Select a BSE stock to research</h1>
              <p className="text-muted-foreground text-sm">
                No login needed. You get 3 free credits — use them for queries (1 each) or forecasts (2 each).
              </p>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") selectCompany(); }}
                placeholder="Enter ticker, e.g. TATASTEEL"
                className="flex-1 h-11 px-4 rounded-lg bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary font-mono uppercase"
              />
              <button
                onClick={selectCompany}
                disabled={!company.trim()}
                className="px-5 py-2 rounded-lg bg-primary text-primary-foreground font-semibold text-sm disabled:opacity-40 hover:bg-primary/90 transition-colors"
              >
                Research
              </button>
            </div>

            <div>
              <p className="text-muted-foreground text-xs uppercase tracking-wider mb-3">Popular stocks</p>
              <div className="flex flex-wrap gap-2">
                {POPULAR_TICKERS.map((t) => (
                  <button
                    key={t}
                    onClick={() => { setCompany(t); setActiveCompany(t); }}
                    className="px-4 py-2 rounded-lg border border-border bg-card text-foreground text-sm font-mono hover:border-primary/50 hover:bg-primary/5 transition-colors"
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Company header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => { setActiveCompany(""); setCompany(""); }}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ArrowLeft className="h-4 w-4" />
                </button>
                <div>
                  <h1 className="text-xl font-bold font-mono">{activeCompany}</h1>
                  <p className="text-muted-foreground text-xs">Preview mode · data from loaded filings</p>
                </div>
              </div>
              <div className="text-muted-foreground text-xs text-right">
                <span className="text-primary">1 credit</span> per query &nbsp;·&nbsp; <span className="text-primary">2 credits</span> per forecast
              </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-border gap-0">
              {(["chat", "forecast"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={cn(
                    "px-5 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors capitalize",
                    tab === t
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  )}
                >
                  {t === "chat" ? "Ask a Question" : "Event Forecast"}
                </button>
              ))}
            </div>

            {/* Guest limit hit */}
            {guestLimitHit ? (
              <SignupNudge router={router} />
            ) : (
              <>
                {tab === "chat" && (
                  <ChatTab
                    company={activeCompany}
                    guestToken={guestToken}
                    creditsRemaining={creditsRemaining}
                    onCreditUpdate={setCreditsRemaining}
                    onGuestLimit={() => setGuestLimitHit(true)}
                  />
                )}
                {tab === "forecast" && (
                  <ForecastTab
                    company={activeCompany}
                    guestToken={guestToken}
                    creditsRemaining={creditsRemaining}
                    onCreditUpdate={setCreditsRemaining}
                    onGuestLimit={() => setGuestLimitHit(true)}
                  />
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
