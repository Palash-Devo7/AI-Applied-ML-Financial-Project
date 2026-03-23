export function FeaturesSection() {
  const features = [
    { num: "01", title: "Instant Company Research", desc: "Search any BSE ticker and get full AI analysis in seconds. Financials, filings, and insights fetched on first search." },
    { num: "02", title: "AI Powered Q and A", desc: "Ask anything about a company in plain English. QuantCortex retrieves and reasons over actual filings to give you precise answers." },
    { num: "03", title: "Multi Agent Forecasting", desc: "Three specialized agents (Bull, Bear, Macro) independently analyze scenarios and a Synthesizer weighs the evidence." },
    { num: "04", title: "Precise Financial Data", desc: "Revenue, EBITDA, margins, and more pulled directly from BSE. Structured data enriches every AI answer." },
    { num: "05", title: "Real Time Streaming", desc: "Answers stream token by token, so you see results immediately without staring at a loading spinner." },
    { num: "06", title: "Any Filing Quality", desc: "FinBERT-powered ingestion handles scanned PDFs, image-only filings, and messy reports with 3-layer OCR fallback." },
  ];

  return (
    <section id="features" style={{ padding: "96px 56px", background: "var(--home-bg2)", borderTop: "1px solid var(--home-border)" }}>
      <div style={{ maxWidth: 960, margin: "0 auto" }}>
        <div style={{ marginBottom: 56 }}>
          <span style={{ fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 3, textTransform: "uppercase" }}>
            Features
          </span>
          <h2 style={{ fontSize: "clamp(26px,2.8vw,42px)", fontWeight: 800, lineHeight: 1.1, letterSpacing: "-1px", marginTop: 16 }}>
            Everything you need to research smarter.
          </h2>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, border: "1px solid var(--home-border)", borderRadius: 16, overflow: "hidden" }}>
          {features.map((f) => (
            <div key={f.num} style={{
              padding: "36px 28px", background: "var(--home-bg2)",
              borderRight: "1px solid var(--home-border)", borderBottom: "1px solid var(--home-border)",
              transition: "background .2s",
            }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--home-bg3)")}
              onMouseLeave={e => (e.currentTarget.style.background = "var(--home-bg2)")}
            >
              <div style={{ fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 2, marginBottom: 18 }}>{f.num}</div>
              <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 10, lineHeight: 1.3 }}>{f.title}</div>
              <div style={{ fontSize: 13, color: "var(--home-muted)", lineHeight: 1.7, fontWeight: 300 }}>{f.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
