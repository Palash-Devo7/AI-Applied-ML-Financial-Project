export function RoadmapSection() {
  const live = [
    { title: "Full BSE coverage with AI research", desc: "Any BSE-listed company, loaded on demand. Search a ticker and get instant AI analysis." },
    { title: "Multi agent event forecasting", desc: "Bull, Bear, and Macro agents + Synthesizer delivering probability-weighted event forecasts." },
  ];

  const coming = [
    { title: "Deeper market intelligence", desc: "Cross-company comparisons, sector analysis, and portfolio-level AI insights." },
    { title: "Predictive signals", desc: "Early-warning signals derived from filing patterns, sentiment shifts, and macro triggers." },
    { title: "Direct investment workflow", desc: "Connect your broker. Go from research to trade without leaving the platform." },
    { title: "Global market expansion", desc: "NSE, SGX, and international markets with the same AI research layer and broader coverage." },
  ];

  return (
    <section id="roadmap" style={{ padding: "96px 56px", background: "var(--home-bg)", borderTop: "1px solid var(--home-border)" }}>
      <div style={{ maxWidth: 960, margin: "0 auto" }}>
        <div style={{ marginBottom: 56 }}>
          <span style={{ fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 3, textTransform: "uppercase" }}>
            Roadmap
          </span>
          <h2 style={{ fontSize: "clamp(26px,2.8vw,42px)", fontWeight: 800, lineHeight: 1.1, letterSpacing: "-1px", marginTop: 16 }}>
            Where we are. Where we&apos;re going.
          </h2>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
          {live.map((item) => (
            <div key={item.title} style={{
              background: "var(--home-bg2)", border: "1px solid rgba(16,185,129,0.2)",
              borderRadius: 16, padding: "28px 24px",
            }}>
              <div style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                fontSize: 10, fontFamily: "var(--font-mono)", letterSpacing: 1.5, textTransform: "uppercase",
                color: "var(--home-green)", background: "rgba(16,185,129,0.08)",
                border: "1px solid rgba(16,185,129,0.2)", borderRadius: 20, padding: "4px 10px", marginBottom: 16,
              }}>
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--home-green)", display: "inline-block" }} />
                Live now
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, lineHeight: 1.4 }}>{item.title}</div>
              <div style={{ fontSize: 12, color: "var(--home-muted)", lineHeight: 1.7, fontWeight: 300 }}>{item.desc}</div>
            </div>
          ))}

          {coming.map((item) => (
            <div key={item.title} style={{
              background: "var(--home-bg2)", border: "1px solid var(--home-border)",
              borderRadius: 16, padding: "28px 24px",
            }}>
              <div style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                fontSize: 10, fontFamily: "var(--font-mono)", letterSpacing: 1.5, textTransform: "uppercase",
                color: "var(--home-purple)", background: "var(--home-purple-dim)",
                border: "1px solid var(--home-purple-border)", borderRadius: 20, padding: "4px 10px", marginBottom: 16,
              }}>
                <span style={{
                  width: 6, height: 6, borderRadius: "50%", background: "var(--home-purple)",
                  display: "inline-block", animation: "softpulse 2s ease-in-out infinite",
                }} />
                Coming soon
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8, lineHeight: 1.4 }}>{item.title}</div>
              <div style={{ fontSize: 12, color: "var(--home-muted)", lineHeight: 1.7, fontWeight: 300 }}>{item.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
