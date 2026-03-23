import { FileText, MessageSquare, Network } from "lucide-react";

const ICONS = [
  <div key="ft" className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: "rgba(167,139,250,0.08)", border: "1px solid rgba(167,139,250,0.2)" }}><FileText size={22} stroke="#a78bfa" strokeWidth={1.5} /></div>,
  <div key="ms" className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: "rgba(167,139,250,0.08)", border: "1px solid rgba(167,139,250,0.2)" }}><MessageSquare size={22} stroke="#a78bfa" strokeWidth={1.5} /></div>,
  <div key="nw" className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: "rgba(167,139,250,0.08)", border: "1px solid rgba(167,139,250,0.2)" }}><Network size={22} stroke="#a78bfa" strokeWidth={1.5} /></div>,
];

export function ValueSection() {
  const cards = [
    { icon: ICONS[0], title: "Zero setup research", desc: "Search any BSE ticker and get instant AI analysis. No uploads, no config, no waiting." },
    { icon: ICONS[1], title: "Ask in plain language", desc: "Ask revenue, margins, risk, or anything else in plain English. QuantCortex reads the filings so you don't have to." },
    { icon: ICONS[2], title: "Multi agent forecasting", desc: "Bull, Bear, and Macro agents debate each scenario. A synthesizer delivers a final probability-weighted outlook." },
  ];

  return (
    <section className="home-section" style={{ padding: "96px 56px", background: "var(--home-bg)" }}>
      <div style={{ maxWidth: 960, margin: "0 auto" }}>
        <div style={{ marginBottom: 56 }}>
          <span style={{ fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 3, textTransform: "uppercase" }}>
            What we do
          </span>
          <h2 style={{ fontSize: "clamp(28px,3.2vw,46px)", fontWeight: 800, lineHeight: 1.1, letterSpacing: "-1px", marginTop: 16, whiteSpace: "pre-line" }}>
            {"One platform.\nAny listed company."}
          </h2>
          <p style={{ fontSize: 15, color: "var(--home-muted)", lineHeight: 1.8, maxWidth: 520, marginTop: 16, fontWeight: 300 }}>
            Indian equity research is fragmented and slow. QuantCortex changes that. One platform, every BSE listed company, instant AI-powered insights.
          </p>
        </div>

        <div className="home-grid-3" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 24 }}>
          {cards.map((card) => (
            <div key={card.title} style={{
              background: "var(--home-bg2)", border: "1px solid var(--home-border)",
              borderRadius: 16, padding: "32px 28px",
              transition: "border-color .2s",
            }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = "var(--home-purple-border)")}
              onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--home-border)")}
            >
              <div style={{ marginBottom: 16 }}>{card.icon}</div>
              <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 10 }}>{card.title}</div>
              <div style={{ fontSize: 13, color: "var(--home-muted)", lineHeight: 1.7, fontWeight: 300 }}>{card.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
