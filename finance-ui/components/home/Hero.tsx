"use client";

import { useRouter } from "next/navigation";
import { DotCanvas } from "./DotCanvas";

export function Hero() {
  const router = useRouter();
  return (
    <div className="home-hero" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", minHeight: 580 }}>
      <div className="home-hero-text" style={{ padding: "72px 56px", display: "flex", flexDirection: "column", justifyContent: "center", borderRight: "1px solid var(--home-border)" }}>
        <div style={{ fontSize: 11, letterSpacing: 3, textTransform: "uppercase", color: "var(--home-purple)", marginBottom: 24, fontFamily: "var(--font-mono)", display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ width: 20, height: 1, background: "var(--home-purple)", display: "inline-block" }} />
          Indian Equity Research Platform
        </div>
        <h1 style={{ fontSize: "clamp(30px,3.8vw,52px)", fontWeight: 800, lineHeight: 1.05, letterSpacing: "-1.2px", marginBottom: 22 }}>
          Research any BSE stock.<br />Powered by <em style={{ color: "var(--home-purple)", fontStyle: "normal" }}>AI.</em>
        </h1>
        <p style={{ fontSize: 15, color: "var(--home-muted)", lineHeight: 1.8, maxWidth: 400, marginBottom: 40, fontWeight: 300 }}>
          QuantCortex is a single platform to research every BSE listed company. Search a ticker, ask questions in plain language, and get AI powered insights backed by actual filings.
        </p>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <button onClick={() => router.push("/auth/login")} style={{
            background: "var(--home-purple)", color: "#1a0a3a", border: "none", borderRadius: 10,
            padding: "14px 28px", fontSize: 14, fontWeight: 700, cursor: "pointer",
            fontFamily: "var(--font-sans)", transition: "all .2s",
          }}
            onMouseEnter={e => { e.currentTarget.style.background = "#c4b5fd"; e.currentTarget.style.transform = "translateY(-1px)"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "var(--home-purple)"; e.currentTarget.style.transform = "none"; }}
          >Try free</button>
          <button onClick={() => document.getElementById("features")?.scrollIntoView({ behavior: "smooth" })} style={{
            fontSize: 13, color: "var(--home-muted)", background: "none", border: "none", cursor: "pointer",
            fontFamily: "var(--font-sans)", fontWeight: 500, padding: "14px 4px",
            textDecoration: "underline", textUnderlineOffset: 3, transition: "color .2s",
          }}
            onMouseEnter={e => (e.currentTarget.style.color = "var(--home-text)")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--home-muted)")}
          >See how it works</button>
        </div>
      </div>
      <div className="home-hero-canvas" style={{ position: "relative", overflow: "hidden", background: "var(--home-bg)", minHeight: 580 }}>
        <DotCanvas />
      </div>
    </div>
  );
}
