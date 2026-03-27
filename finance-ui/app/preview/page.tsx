"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getGuestCredits, streamPreviewQuery } from "@/lib/api";
import { Loader2, Send, Sparkles } from "lucide-react";

function generateUUID(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

const SUGGESTED = [
  { company: "TATASTEEL", question: "What is the revenue trend for the last 3 years?" },
  { company: "HDFCBANK", question: "What are the key risk factors mentioned in the annual report?" },
  { company: "RELIANCE", question: "Summarise the capital expenditure plans." },
];

export default function PreviewPage() {
  const router = useRouter();
  const [guestToken, setGuestToken] = useState<string>("");
  const [creditsRemaining, setCreditsRemaining] = useState<number>(3);
  const [creditsLoaded, setCreditsLoaded] = useState(false);
  const [company, setCompany] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [hasQueried, setHasQueried] = useState(false);
  const [guestLimitHit, setGuestLimitHit] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const answerRef = useRef<HTMLDivElement>(null);

  // Initialise guest token from localStorage
  useEffect(() => {
    let token = localStorage.getItem("guest_token");
    if (!token) {
      token = generateUUID();
      localStorage.setItem("guest_token", token);
    }
    setGuestToken(token);
  }, []);

  // Fetch credits once token is ready
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

  function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    if (!question.trim() || streaming || creditsRemaining <= 0 || !guestToken) return;

    setStreaming(true);
    setAnswer("");
    setErrorMsg("");
    setHasQueried(true);
    setGuestLimitHit(false);

    abortRef.current = streamPreviewQuery(
      question.trim(),
      company.trim() || undefined,
      guestToken,
      (chunk) => {
        setAnswer((prev) => prev + chunk);
        answerRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
      },
      (remaining) => {
        setCreditsRemaining(remaining);
        setStreaming(false);
        if (remaining === 0) setGuestLimitHit(true);
      },
      (err, isGuestLimit) => {
        setStreaming(false);
        if (isGuestLimit) {
          setGuestLimitHit(true);
          setCreditsRemaining(0);
        } else {
          setErrorMsg(err.message || "Something went wrong. Please try again.");
        }
      }
    );
  }

  function handleSuggestion(s: { company: string; question: string }) {
    setCompany(s.company);
    setQuestion(s.question);
  }

  const canSubmit = question.trim().length > 0 && !streaming && creditsRemaining > 0 && creditsLoaded;

  return (
    <div style={{
      minHeight: "100vh",
      background: "var(--home-bg, #0d0d1a)",
      color: "var(--home-text, #e8e3ff)",
      fontFamily: "var(--font-sans)",
      display: "flex",
      flexDirection: "column",
    }}>
      {/* Top bar */}
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "18px 32px", borderBottom: "1px solid var(--home-border, rgba(255,255,255,0.08))",
      }}>
        <button
          onClick={() => router.push("/")}
          style={{ background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}
        >
          <Sparkles size={18} color="var(--home-purple, #a78bfa)" />
          <span style={{ fontWeight: 700, fontSize: 15, color: "var(--home-text, #e8e3ff)" }}>QuantCortex</span>
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          {creditsLoaded && (
            <span style={{
              fontSize: 12, fontFamily: "var(--font-mono)", color: "var(--home-muted, #7c6fa0)",
              background: "rgba(167,139,250,0.08)", border: "1px solid rgba(167,139,250,0.2)",
              borderRadius: 20, padding: "4px 12px",
            }}>
              {creditsRemaining} / 3 free queries left
            </span>
          )}
          <button
            onClick={() => router.push("/auth/login")}
            style={{
              background: "var(--home-purple, #a78bfa)", color: "#1a0a3a",
              border: "none", borderRadius: 8, padding: "8px 18px",
              fontSize: 13, fontWeight: 700, cursor: "pointer", fontFamily: "var(--font-sans)",
            }}
          >
            Sign up free
          </button>
        </div>
      </header>

      {/* Main content */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", padding: "48px 24px 80px" }}>
        {/* Heading */}
        <div style={{ textAlign: "center", marginBottom: 48, maxWidth: 560 }}>
          <div style={{
            fontSize: 11, letterSpacing: 3, textTransform: "uppercase",
            color: "var(--home-purple, #a78bfa)", marginBottom: 16,
            fontFamily: "var(--font-mono)",
          }}>
            No login required
          </div>
          <h1 style={{ fontSize: "clamp(24px,3.5vw,42px)", fontWeight: 800, lineHeight: 1.1, letterSpacing: "-1px", marginBottom: 14 }}>
            Ask anything about<br />any BSE listed company.
          </h1>
          <p style={{ fontSize: 14, color: "var(--home-muted, #7c6fa0)", lineHeight: 1.7 }}>
            Full AI-powered analysis — no stripped results. Try 3 free queries, no account needed.
          </p>
        </div>

        {/* Query card */}
        <div style={{
          width: "100%", maxWidth: 680,
          background: "rgba(255,255,255,0.03)", border: "1px solid var(--home-border, rgba(255,255,255,0.08))",
          borderRadius: 16, padding: "28px 28px 24px",
        }}>
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <input
              type="text"
              placeholder="Company (e.g. TATASTEEL, HDFCBANK, RELIANCE)"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              style={{
                background: "rgba(255,255,255,0.04)", border: "1px solid var(--home-border, rgba(255,255,255,0.1))",
                borderRadius: 10, padding: "12px 16px", fontSize: 14,
                color: "var(--home-text, #e8e3ff)", fontFamily: "var(--font-mono)",
                outline: "none", width: "100%", boxSizing: "border-box",
              }}
            />
            <div style={{ display: "flex", gap: 10 }}>
              <input
                type="text"
                placeholder="Ask a question about this company..."
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
                disabled={guestLimitHit}
                style={{
                  flex: 1, background: "rgba(255,255,255,0.04)", border: "1px solid var(--home-border, rgba(255,255,255,0.1))",
                  borderRadius: 10, padding: "12px 16px", fontSize: 14,
                  color: "var(--home-text, #e8e3ff)", fontFamily: "var(--font-sans)",
                  outline: "none", boxSizing: "border-box",
                  opacity: guestLimitHit ? 0.4 : 1,
                }}
              />
              <button
                type="submit"
                disabled={!canSubmit}
                style={{
                  background: canSubmit ? "var(--home-purple, #a78bfa)" : "rgba(167,139,250,0.2)",
                  color: canSubmit ? "#1a0a3a" : "rgba(167,139,250,0.4)",
                  border: "none", borderRadius: 10, padding: "12px 18px",
                  cursor: canSubmit ? "pointer" : "not-allowed",
                  display: "flex", alignItems: "center", gap: 6, fontSize: 14, fontWeight: 700,
                  transition: "all .2s",
                }}
              >
                {streaming ? <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> : <Send size={16} />}
                {streaming ? "Thinking..." : "Ask"}
              </button>
            </div>
          </form>

          {/* Suggested queries */}
          {!hasQueried && (
            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: 11, color: "var(--home-muted, #7c6fa0)", marginBottom: 10, textTransform: "uppercase", letterSpacing: 1.5, fontFamily: "var(--font-mono)" }}>
                Try these
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {SUGGESTED.map((s) => (
                  <button
                    key={s.question}
                    onClick={() => handleSuggestion(s)}
                    style={{
                      background: "rgba(167,139,250,0.06)", border: "1px solid rgba(167,139,250,0.15)",
                      borderRadius: 8, padding: "10px 14px", cursor: "pointer", textAlign: "left",
                      color: "var(--home-text, #e8e3ff)", fontSize: 13, fontFamily: "var(--font-sans)",
                      transition: "all .15s",
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.borderColor = "rgba(167,139,250,0.4)"; e.currentTarget.style.background = "rgba(167,139,250,0.1)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.borderColor = "rgba(167,139,250,0.15)"; e.currentTarget.style.background = "rgba(167,139,250,0.06)"; }}
                  >
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--home-purple, #a78bfa)", marginRight: 8 }}>{s.company}</span>
                    {s.question}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Answer area */}
        {(hasQueried || errorMsg) && (
          <div style={{
            width: "100%", maxWidth: 680, marginTop: 24,
            background: "rgba(255,255,255,0.03)", border: "1px solid var(--home-border, rgba(255,255,255,0.08))",
            borderRadius: 16, padding: "24px 28px",
          }}>
            {errorMsg && (
              <p style={{ color: "#f87171", fontSize: 14, margin: 0 }}>{errorMsg}</p>
            )}
            {answer && (
              <div ref={answerRef} style={{ fontSize: 14, lineHeight: 1.85, color: "var(--home-text, #e8e3ff)" }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
              </div>
            )}
            {streaming && !answer && (
              <div style={{ display: "flex", gap: 8, alignItems: "center", color: "var(--home-muted, #7c6fa0)", fontSize: 13 }}>
                <Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} />
                Analysing filings...
              </div>
            )}
          </div>
        )}

        {/* Guest limit nudge */}
        {guestLimitHit && (
          <div style={{
            width: "100%", maxWidth: 680, marginTop: 24,
            background: "rgba(167,139,250,0.07)", border: "1px solid rgba(167,139,250,0.3)",
            borderRadius: 16, padding: "28px 32px", textAlign: "center",
          }}>
            <div style={{ fontSize: 22, marginBottom: 12 }}>You&apos;ve used all 3 free queries.</div>
            <p style={{ color: "var(--home-muted, #7c6fa0)", fontSize: 14, marginBottom: 24, lineHeight: 1.7 }}>
              Create a free account to get <strong style={{ color: "var(--home-text, #e8e3ff)" }}>10 queries per day</strong> — no credit card required.
            </p>
            <button
              onClick={() => router.push("/auth/login")}
              style={{
                background: "var(--home-purple, #a78bfa)", color: "#1a0a3a",
                border: "none", borderRadius: 10, padding: "14px 32px",
                fontSize: 15, fontWeight: 700, cursor: "pointer", fontFamily: "var(--font-sans)",
              }}
            >
              Create free account
            </button>
            <div style={{ marginTop: 16, fontSize: 12, color: "var(--home-muted, #7c6fa0)" }}>
              Already have an account?{" "}
              <button
                onClick={() => router.push("/auth/login")}
                style={{ background: "none", border: "none", color: "var(--home-purple, #a78bfa)", cursor: "pointer", fontSize: 12, padding: 0 }}
              >
                Sign in
              </button>
            </div>
          </div>
        )}
      </main>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        input:focus { border-color: rgba(167,139,250,0.5) !important; }
      `}</style>
    </div>
  );
}
