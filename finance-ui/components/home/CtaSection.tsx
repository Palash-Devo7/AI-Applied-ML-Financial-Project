"use client";

import { useRouter } from "next/navigation";

export function CtaSection() {
  const router = useRouter();
  return (
    <section className="home-section" style={{
      padding: "96px 56px",
      background: "radial-gradient(ellipse 70% 60% at 50% 50%, rgba(167,139,250,0.12) 0%, var(--home-bg) 70%)",
      borderTop: "1px solid var(--home-border)",
    }}>
      <div style={{ maxWidth: 640, margin: "0 auto", textAlign: "center" }}>
        <span style={{ fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 3, textTransform: "uppercase" }}>
          Get started today
        </span>
        <h2 style={{ fontSize: "clamp(28px,3.4vw,50px)", fontWeight: 800, lineHeight: 1.08, letterSpacing: "-1.2px", marginTop: 16, whiteSpace: "pre-line" }}>
          {"Research smarter.\nStart free."}
        </h2>
        <p style={{ fontSize: 15, color: "var(--home-muted)", marginTop: 16, marginBottom: 40, fontWeight: 300 }}>
          10 credit points per day. No credit card required.
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", alignItems: "center" }}>
          <button onClick={() => router.push("/auth/register")} style={{
            background: "var(--home-purple)", color: "#1a0a3a", border: "none", borderRadius: 10,
            padding: "14px 32px", fontSize: 14, fontWeight: 700, cursor: "pointer",
            fontFamily: "var(--font-sans)", transition: "all .2s",
          }}
            onMouseEnter={e => { e.currentTarget.style.background = "#c4b5fd"; e.currentTarget.style.transform = "translateY(-1px)"; }}
            onMouseLeave={e => { e.currentTarget.style.background = "var(--home-purple)"; e.currentTarget.style.transform = "none"; }}
          >Create free account</button>
          <button onClick={() => router.push("/auth/login")} style={{
            background: "none", color: "var(--home-text)", border: "1px solid var(--home-border2)",
            borderRadius: 10, padding: "14px 28px", fontSize: 14, fontWeight: 500, cursor: "pointer",
            fontFamily: "var(--font-sans)", transition: "all .2s",
          }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--home-purple)"; e.currentTarget.style.color = "var(--home-purple)"; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--home-border2)"; e.currentTarget.style.color = "var(--home-text)"; }}
          >Sign in</button>
        </div>
      </div>
    </section>
  );
}
