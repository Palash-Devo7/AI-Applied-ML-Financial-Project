"use client";

import { useRouter } from "next/navigation";

export function Navbar() {
  const router = useRouter();

  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <nav className="home-navbar" style={{
      position: "sticky", top: 0, zIndex: 100,
      background: "rgba(7,7,10,0.92)", backdropFilter: "blur(16px)",
      borderBottom: "1px solid var(--home-border)",
      padding: "0 48px", display: "flex", alignItems: "center",
      justifyContent: "space-between", height: 60,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{
          width: 30, height: 30, background: "var(--home-purple)", borderRadius: 8,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 14, fontWeight: 800, color: "#1a0a3a",
        }}>Q</div>
        <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.3px" }}>
          Quant<em style={{ color: "var(--home-purple)", fontStyle: "normal" }}>Cortex</em>
        </span>
      </div>

      <div className="home-navbar-links" style={{ display: "flex", gap: 28 }}>
        {[["Platform", "value"], ["Features", "features"], ["Roadmap", "roadmap"]].map(([label, id]) => (
          <span key={id} onClick={() => scrollTo(id)} style={{
            fontSize: 13, color: "var(--home-muted)", cursor: "pointer", transition: "color .2s",
          }}
            onMouseEnter={e => (e.currentTarget.style.color = "var(--home-text)")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--home-muted)")}
          >{label}</span>
        ))}
      </div>

      <button onClick={() => router.push("/auth/login")} style={{
        fontSize: 13, color: "var(--home-text)", background: "none",
        border: "1px solid var(--home-border2)", borderRadius: 8, padding: "8px 18px",
        cursor: "pointer", fontFamily: "var(--font-sans)", fontWeight: 500, transition: "all .2s",
      }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--home-purple)"; e.currentTarget.style.color = "var(--home-purple)"; }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--home-border2)"; e.currentTarget.style.color = "var(--home-text)"; }}
      >Sign in</button>
    </nav>
  );
}
