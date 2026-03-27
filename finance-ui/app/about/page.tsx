"use client";

import { useRouter } from "next/navigation";
import { Navbar } from "@/components/home/Navbar";
import { Footer } from "@/components/home/Footer";


const pillars = [
  {
    num: "01",
    title: "Research that was out of reach",
    desc: "Serious AI research tools should not be limited to a handful of institutions. QuantCortex makes that depth accessible to every investor, analyst, and student in India.",
  },
  {
    num: "02",
    title: "Filings as the ground truth",
    desc: "Every answer is grounded in actual BSE filings and structured financials. Not summaries. Not opinions. Primary sources, every time.",
  },
  {
    num: "03",
    title: "AI that explains itself",
    desc: "Multi-agent forecasting shows you the bull case, the bear case, and the macro picture side by side. The reasoning is visible. You decide.",
  },
];

const roadmap = [
  {
    num: "01",
    tag: "Coming next",
    title: "GraphRAG — Company Relationship Mapping",
    desc: "Graph-based intelligence built on NetworkX. Understand how companies in a sector influence each other, who supplies whom, and where contagion risk hides before it surfaces in prices.",
  },
  {
    num: "02",
    tag: "Coming next",
    title: "Zerodha Kite Integration",
    desc: "Research and execute in one place. Place orders directly from your analysis without switching platforms or losing context mid-decision.",
  },
  {
    num: "03",
    tag: "Coming next",
    title: "Portfolio-level AI Analysis",
    desc: "Cross-company intelligence across your full holdings. Spot concentration risk, sector overlap, and hidden correlations that single-ticker analysis misses.",
  },
  {
    num: "04",
    tag: "Coming next",
    title: "Sector Intelligence",
    desc: "Macro signals mapped to BSE sectors in real time. Know which sectors are exposed to rate moves, currency shifts, and global events before the market reprices.",
  },
];

export default function AboutPage() {
  const router = useRouter();

  return (
    <div style={{ background: "var(--home-bg)", color: "var(--home-text)", fontFamily: "var(--font-sans)", minHeight: "100vh" }}>
      <Navbar />

      {/* Hero */}
      <section style={{ padding: "100px 56px 72px", maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ fontSize: 11, letterSpacing: 3, textTransform: "uppercase", color: "var(--home-purple)", marginBottom: 24, fontFamily: "var(--font-mono)", display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 20, height: 1, background: "var(--home-purple)", display: "inline-block" }} />
          What is QuantCortex
        </div>
        <h1 style={{ fontSize: "clamp(32px,4vw,58px)", fontWeight: 800, lineHeight: 1.05, letterSpacing: "-1.5px", maxWidth: 740, marginBottom: 20 }}>
          AI-powered equity research for{" "}
          <em style={{ color: "var(--home-purple)", fontStyle: "normal" }}>every BSE-listed company</em>{" "}
          in India.
        </h1>
        <p style={{ fontSize: 16, color: "var(--home-text)", lineHeight: 1.8, maxWidth: 580, fontWeight: 300 }}>
          Search any ticker, ask questions in plain language, and get answers grounded in actual filings. Multi-agent forecasting. Real-time stock data. Zero manual uploads. Built for investors who want to understand a business before committing to it.
        </p>
      </section>

      {/* Builder profile */}
      <section style={{ borderTop: "1px solid var(--home-border)", borderBottom: "1px solid var(--home-border)", background: "var(--home-bg2)" }}>
        <div className="about-profile-grid" style={{ maxWidth: 1100, margin: "0 auto", padding: "80px 56px", display: "grid", gridTemplateColumns: "320px 1fr", gap: 72, alignItems: "center" }}>

          {/* Photo frame */}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20 }}>
            <div style={{
              width: 220, height: 220, borderRadius: "50%",
              border: "2px solid var(--home-purple-border)",
              padding: 4,
              background: "linear-gradient(135deg, rgba(167,139,250,0.12), rgba(167,139,250,0.04))",
              boxShadow: "0 0 60px rgba(167,139,250,0.12)",
              display: "flex", alignItems: "center", justifyContent: "center",
              overflow: "hidden",
            }}>
              <img
                src="/fc.jpeg"
                alt="Palash Joshi"
                style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover", display: "block" }}
                onError={e => {
                  const el = e.currentTarget as HTMLImageElement;
                  el.style.display = "none";
                  const parent = el.parentElement!;
                  parent.innerHTML = `<span style="font-size:56px;font-weight:800;color:#a78bfa;letter-spacing:-2px">PJ</span>`;
                }}
              />
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: "-0.3px", marginBottom: 6 }}>Palash Joshi</div>
              <div style={{ fontSize: 12, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 2, textTransform: "uppercase" }}>Founder and Engineer</div>
            </div>
            <div style={{ display: "flex", gap: 12 }}>
              <a href="https://github.com/Palash-Devo7/AI-Applied-ML-Financial-Project" target="_blank" rel="noopener noreferrer" style={{
                fontSize: 12, color: "var(--home-muted)", border: "1px solid var(--home-border2)",
                borderRadius: 8, padding: "8px 16px", textDecoration: "none",
                fontFamily: "var(--font-mono)", transition: "all .2s",
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--home-purple)"; e.currentTarget.style.color = "var(--home-purple)"; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--home-border2)"; e.currentTarget.style.color = "var(--home-muted)"; }}
              >GitHub</a>
              <a href="https://www.linkedin.com/in/palash-joshi-901656286/" target="_blank" rel="noopener noreferrer" style={{
                fontSize: 12, color: "var(--home-muted)", border: "1px solid var(--home-border2)",
                borderRadius: 8, padding: "8px 16px", textDecoration: "none",
                fontFamily: "var(--font-mono)", transition: "all .2s",
              }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--home-purple)"; e.currentTarget.style.color = "var(--home-purple)"; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--home-border2)"; e.currentTarget.style.color = "var(--home-muted)"; }}
              >LinkedIn</a>
            </div>
          </div>

          {/* Bio */}
          <div>
            <div style={{ fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 3, textTransform: "uppercase", marginBottom: 28 }}>
              The Team
            </div>
            <p style={{ fontSize: 16, lineHeight: 1.85, color: "var(--home-text)", marginBottom: 22, fontWeight: 300 }}>
              I am a software engineer with over 80 production systems delivered across AI pipelines, backend APIs, cloud infrastructure, and automation at scale. Every project I touch goes to production. That is the standard I hold myself to.
            </p>
            <p style={{ fontSize: 16, lineHeight: 1.85, color: "var(--home-text)", marginBottom: 22, fontWeight: 300 }}>
              I have built LLM-driven automation systems that moved outbound response rates from 4 percent to 13 percent. I have designed RAG platforms that aggregate data across more than 10 internal systems with role-based access and MCP-driven retrieval routing. I have delivered automation workflows that cut manual processing time by 60 to 80 percent. I have built and backtested algorithmic trading strategies across live market data.
            </p>

            <p style={{ fontSize: 16, lineHeight: 1.85, color: "var(--home-text)", marginBottom: 28, fontWeight: 300 }}>
              QuantCortex is where all of that converges. Every system I have built has sharpened what is inside this platform.
            </p>
            <p style={{ fontSize: 14, color: "var(--home-muted)", fontWeight: 300 }}>
              <a href="mailto:palash@quantcortex.in" style={{ color: "var(--home-purple)", textDecoration: "none" }}>palash@quantcortex.in</a>
            </p>
          </div>
        </div>
      </section>

      {/* Mission — current + roadmap merged */}
      <section style={{ padding: "96px 56px 80px", maxWidth: 1100, margin: "0 auto" }}>

        {/* Mission header */}
        <div style={{ fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 3, textTransform: "uppercase", marginBottom: 28, display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 20, height: 1, background: "var(--home-purple)", display: "inline-block" }} />
          Our mission
        </div>
        <h2 style={{ fontSize: "clamp(28px,3.2vw,50px)", fontWeight: 800, lineHeight: 1.1, letterSpacing: "-1.2px", maxWidth: 820, marginBottom: 20 }}>
          Institutional-grade research for{" "}
          <em style={{ color: "var(--home-purple)", fontStyle: "normal" }}>every investor</em>{" "}
          in India.
        </h2>
        <p style={{ fontSize: 16, color: "var(--home-text)", lineHeight: 1.8, maxWidth: 600, fontWeight: 300, marginBottom: 56 }}>
          The depth of analysis that was previously locked behind expensive subscriptions and specialized terminals is now available to anyone with a browser. That is not a feature. That is the whole point.
        </p>

        {/* Current pillars */}
        <div className="home-grid-3" style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 1, border: "1px solid var(--home-border)", borderRadius: 16, overflow: "hidden", marginBottom: 72 }}>
          {pillars.map(p => (
            <div key={p.num} style={{ padding: "36px 28px", background: "var(--home-bg2)", borderRight: "1px solid var(--home-border)", transition: "background .2s" }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--home-bg3)")}
              onMouseLeave={e => (e.currentTarget.style.background = "var(--home-bg2)")}
            >
              <div style={{ fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 2, marginBottom: 18 }}>{p.num}</div>
              <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 10, lineHeight: 1.3 }}>{p.title}</div>
              <div style={{ fontSize: 13, color: "var(--home-text)", lineHeight: 1.7, fontWeight: 300 }}>{p.desc}</div>
            </div>
          ))}
        </div>

        {/* What's coming divider */}
        <div style={{ display: "flex", alignItems: "center", gap: 20, marginBottom: 48 }}>
          <div style={{ flex: 1, height: 1, background: "var(--home-border)" }} />
          <div style={{ fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 3, textTransform: "uppercase", whiteSpace: "nowrap" }}>
            What is coming next
          </div>
          <div style={{ flex: 1, height: 1, background: "var(--home-border)" }} />
        </div>

        <p style={{ fontSize: 16, color: "var(--home-text)", lineHeight: 1.8, maxWidth: 600, fontWeight: 300, marginBottom: 48 }}>
          This is version one. The platform is already live and growing. Here is what is already planned and in development.
        </p>

        {/* Roadmap grid */}
        <div className="about-roadmap-grid" style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 1, border: "1px solid var(--home-border)", borderRadius: 16, overflow: "hidden", marginBottom: 72 }}>
          {roadmap.map(r => (
            <div key={r.num} style={{ padding: "36px 32px", background: "var(--home-bg2)", borderRight: "1px solid var(--home-border)", borderBottom: "1px solid var(--home-border)", transition: "background .2s" }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--home-bg3)")}
              onMouseLeave={e => (e.currentTarget.style.background = "var(--home-bg2)")}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18 }}>
                <span style={{ fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 2 }}>{r.num}</span>
                <span style={{ fontSize: 10, color: "var(--home-green)", fontFamily: "var(--font-mono)", letterSpacing: 2, textTransform: "uppercase", border: "1px solid rgba(16,185,129,0.3)", borderRadius: 4, padding: "2px 8px" }}>{r.tag}</span>
              </div>
              <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 12, lineHeight: 1.3 }}>{r.title}</div>
              <div style={{ fontSize: 13, color: "var(--home-text)", lineHeight: 1.7, fontWeight: 300 }}>{r.desc}</div>
            </div>
          ))}
        </div>

        {/* Closing statement */}
        <div style={{ borderLeft: "2px solid var(--home-purple)", paddingLeft: 28, marginBottom: 56 }}>
          <p style={{ fontSize: "clamp(18px,2vw,26px)", fontWeight: 700, lineHeight: 1.3, letterSpacing: "-0.5px", color: "var(--home-text)" }}>
            We are building the research platform Indian investors deserve.
          </p>
          <p style={{ fontSize: 15, color: "var(--home-text)", fontWeight: 300, marginTop: 10, lineHeight: 1.7 }}>
            QuantCortex is not a demo project. Every feature ships to production. Every user gets the real thing.
          </p>
        </div>

        {/* CTA */}
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <button onClick={() => router.push("/preview")} style={{
            background: "var(--home-purple)", color: "#1a0a3a", border: "none", borderRadius: 10,
            padding: "14px 28px", fontSize: 14, fontWeight: 700, cursor: "pointer",
            fontFamily: "var(--font-sans)", transition: "all .2s",
          }}
            onMouseEnter={e => { e.currentTarget.style.background = "#c4b5fd"; e.currentTarget.style.transform = "translateY(-1px)"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "var(--home-purple)"; e.currentTarget.style.transform = "none"; }}
          >Try it free</button>
          <button onClick={() => router.push("/")} style={{
            fontSize: 13, color: "var(--home-muted)", background: "none", border: "none", cursor: "pointer",
            fontFamily: "var(--font-sans)", fontWeight: 500, padding: "14px 4px",
            textDecoration: "underline", textUnderlineOffset: 3, transition: "color .2s",
          }}
            onMouseEnter={e => (e.currentTarget.style.color = "var(--home-text)")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--home-muted)")}
          >Back to home</button>
        </div>
      </section>

      <Footer />
    </div>
  );
}
