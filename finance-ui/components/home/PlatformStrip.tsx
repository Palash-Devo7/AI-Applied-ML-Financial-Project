export function PlatformStrip() {
  const items = ["AI powered Q and A", "Instant filing ingestion", "Multi agent forecasting", "Streaming answers", "Cited sources"];
  return (
    <div id="value" style={{ borderTop: "1px solid var(--home-border)", borderBottom: "1px solid var(--home-border)", padding: "20px 56px", display: "flex", alignItems: "center", gap: 48, background: "var(--home-bg2)" }}>
      <span style={{ fontSize: 11, color: "var(--home-muted2)", textTransform: "uppercase", letterSpacing: 2, whiteSpace: "nowrap", fontFamily: "var(--font-mono)" }}>What we do</span>
      <div style={{ display: "flex", gap: 36, alignItems: "center", flexWrap: "wrap" }}>
        {items.map(item => (
          <span key={item} style={{ fontSize: 12, color: "var(--home-muted)", display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--home-purple)", opacity: 0.5, display: "inline-block" }} />
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
