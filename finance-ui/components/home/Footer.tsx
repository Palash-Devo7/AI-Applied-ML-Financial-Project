export function Footer() {
  const linkStyle: React.CSSProperties = {
    fontSize: 13, color: "var(--home-muted)", textDecoration: "none", transition: "color .2s", display: "block", marginBottom: 10,
  };

  return (
    <footer className="home-footer" style={{
      borderTop: "1px solid var(--home-border)",
      background: "var(--home-bg2)",
      padding: "48px 56px 32px",
    }}>
      {/* Three columns */}
      <div className="home-footer-grid" style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 40, marginBottom: 40 }}>

        {/* Brand */}
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
            <div style={{
              width: 24, height: 24, background: "var(--home-purple)", borderRadius: 6,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 12, fontWeight: 800, color: "#1a0a3a",
            }}>Q</div>
            <span style={{ fontSize: 14, fontWeight: 700, letterSpacing: "-0.3px" }}>
              Quant<em style={{ color: "var(--home-purple)", fontStyle: "normal" }}>Cortex</em>
            </span>
          </div>
          <p style={{ fontSize: 13, color: "var(--home-muted)", fontWeight: 300, lineHeight: 1.6 }}>
            AI research platform
          </p>
        </div>

        {/* Links */}
        <div>
          <div style={{ fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 2, textTransform: "uppercase", marginBottom: 16 }}>Links</div>
          {[
            { label: "GitHub", href: "https://github.com/Palash-Devo7/AI-Applied-ML-Financial-Project" },
            { label: "LinkedIn", href: "https://www.linkedin.com/in/palash-joshi-901656286/" },
          ].map(({ label, href }) => (
            <a key={label} href={href} target="_blank" rel="noopener noreferrer" style={linkStyle}
              onMouseEnter={e => (e.currentTarget.style.color = "var(--home-text)")}
              onMouseLeave={e => (e.currentTarget.style.color = "var(--home-muted)")}
            >{label}</a>
          ))}
        </div>

        {/* Contact */}
        <div>
          <div style={{ fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 2, textTransform: "uppercase", marginBottom: 16 }}>Contact</div>
          <p style={{ fontSize: 13, color: "var(--home-muted)", marginBottom: 4 }}>Palash Joshi</p>
          <p style={{ fontSize: 13, color: "var(--home-muted)", fontFamily: "var(--font-mono)" }}>palash@quantcortex.in</p>
        </div>
      </div>

      {/* Bottom bar */}
      <div style={{ borderTop: "1px solid var(--home-border)", paddingTop: 24, fontSize: 12, color: "var(--home-muted2)", fontFamily: "var(--font-mono)" }}>
        © 2026 QuantCortex. All rights reserved.
      </div>
    </footer>
  );
}
