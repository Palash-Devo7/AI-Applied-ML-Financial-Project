export function Footer() {
  return (
    <footer className="home-footer" style={{
      borderTop: "1px solid var(--home-border)",
      padding: "32px 56px",
      background: "var(--home-bg2)",
      display: "flex", alignItems: "center", justifyContent: "space-between",
    }}>
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <div style={{
            width: 24, height: 24, background: "var(--home-purple)", borderRadius: 6,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, fontWeight: 800, color: "#1a0a3a",
          }}>Q</div>
          <span style={{ fontSize: 14, fontWeight: 700, letterSpacing: "-0.3px" }}>
            Quant<em style={{ color: "var(--home-purple)", fontStyle: "normal" }}>Cortex</em>
          </span>
        </div>
        <p style={{ fontSize: 12, color: "var(--home-muted)", fontWeight: 300 }}>
          AI research platform for Indian equities
        </p>
      </div>

      <div style={{ display: "flex", gap: 28 }}>
        {[
          { label: "GitHub", href: "https://github.com" },
          { label: "API Docs", href: "/docs" },
          { label: "Contact", href: "mailto:palash@quantcortex.in" },
        ].map(({ label, href }) => (
          <a key={label} href={href} style={{
            fontSize: 13, color: "var(--home-muted)", textDecoration: "none", transition: "color .2s",
          }}
            onMouseEnter={e => (e.currentTarget.style.color = "var(--home-text)")}
            onMouseLeave={e => (e.currentTarget.style.color = "var(--home-muted)")}
          >{label}</a>
        ))}
      </div>
    </footer>
  );
}
