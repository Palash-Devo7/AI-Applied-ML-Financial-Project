"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { adminListUsers, adminGetStats, AdminUser, AdminStats } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const S = {
  page: { minHeight: "100vh", background: "var(--home-bg)", padding: "48px 40px", fontFamily: "var(--font-sans)" } as React.CSSProperties,
  inner: { maxWidth: 1100, margin: "0 auto" } as React.CSSProperties,
  label: { fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 3, textTransform: "uppercase" as const, marginBottom: 10 },
  card: { background: "var(--home-bg2)", border: "1px solid var(--home-border)", borderRadius: 12, padding: "20px 24px" } as React.CSSProperties,
  section: { marginBottom: 40 } as React.CSSProperties,
  th: { padding: "12px 16px", textAlign: "left" as const, fontSize: 11, fontFamily: "var(--font-mono)", letterSpacing: 1.5, textTransform: "uppercase" as const, color: "var(--home-muted)", fontWeight: 500, borderBottom: "1px solid var(--home-border)" },
  td: { padding: "12px 16px", fontSize: 13, borderBottom: "1px solid var(--home-border)" } as React.CSSProperties,
};

function StatCard({ label, value, sub }: { label: string; value: number | string; sub?: string }) {
  return (
    <div style={S.card}>
      <div style={S.label}>{label}</div>
      <div style={{ fontSize: 32, fontWeight: 800, color: "var(--home-purple)", lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: "var(--home-muted)", marginTop: 6, fontFamily: "var(--font-mono)" }}>{sub}</div>}
    </div>
  );
}

function MiniBar({ data, keyField, valueField, max }: { data: Record<string, unknown>[]; keyField: string; valueField: string; max: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {data.map((row, i) => {
        const val = row[valueField] as number;
        const pct = max > 0 ? (val / max) * 100 : 0;
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 90, fontSize: 11, color: "var(--home-muted)", fontFamily: "var(--font-mono)", flexShrink: 0, textAlign: "right" }}>
              {String(row[keyField]).slice(5)}
            </div>
            <div style={{ flex: 1, background: "var(--home-bg3)", borderRadius: 4, height: 8, overflow: "hidden" }}>
              <div style={{ width: `${pct}%`, background: "var(--home-purple)", height: "100%", borderRadius: 4, transition: "width .4s ease" }} />
            </div>
            <div style={{ fontSize: 12, color: "var(--home-text)", fontFamily: "var(--font-mono)", width: 24, flexShrink: 0 }}>{val}</div>
          </div>
        );
      })}
    </div>
  );
}

const ENDPOINT_LABELS: Record<string, string> = {
  "/companies/load": "Company loads",
  "/forecast/event": "Forecasts",
  "/query/stream": "Chat queries",
  "/query": "Queries",
  "/documents/upload": "Doc uploads",
};

export default function AdminPage() {
  const router = useRouter();
  const { token, user, loading: authLoading } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!token || user?.role !== "admin") { router.replace("/auth/login"); return; }
    Promise.all([adminListUsers(), adminGetStats()])
      .then(([u, s]) => { setUsers(u); setStats(s); })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [authLoading, token, user, router]);

  if (authLoading || loading) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--home-bg)", color: "var(--home-muted)" }}>
      Loading...
    </div>
  );

  if (error) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--home-bg)", color: "#ef4444" }}>
      {error}
    </div>
  );

  const t = stats?.totals;
  const maxSignup = Math.max(...(stats?.signups_by_day.map(r => r.count) ?? [1]));
  const maxDau = Math.max(...(stats?.dau_by_day.map(r => r.count) ?? [1]));

  return (
    <div style={S.page}>
      <div style={S.inner}>

        {/* Header */}
        <div style={{ marginBottom: 40 }}>
          <div style={S.label}>Admin</div>
          <h1 style={{ fontSize: 28, fontWeight: 800, letterSpacing: "-0.5px", margin: 0 }}>Platform Dashboard</h1>
        </div>

        {/* Top stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 40 }}>
          <StatCard label="Total Users" value={t?.total_users ?? 0} sub={`${t?.verified_users ?? 0} verified`} />
          <StatCard label="Active Today" value={t?.active_today ?? 0} sub="unique users" />
          <StatCard label="Total Queries" value={t?.total_queries ?? 0} sub="chat + stream" />
          <StatCard label="Forecasts Run" value={t?.total_forecasts ?? 0} sub="multi-agent" />
        </div>

        {/* Charts row */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 40 }}>
          <div style={S.card}>
            <div style={S.label}>Signups by Day</div>
            {stats?.signups_by_day.length ? (
              <MiniBar data={stats.signups_by_day as Record<string, unknown>[]} keyField="day" valueField="count" max={maxSignup} />
            ) : <div style={{ fontSize: 12, color: "var(--home-muted)" }}>No data yet</div>}
          </div>
          <div style={S.card}>
            <div style={S.label}>Daily Active Users</div>
            {stats?.dau_by_day.length ? (
              <MiniBar data={stats.dau_by_day as Record<string, unknown>[]} keyField="date" valueField="count" max={maxDau} />
            ) : <div style={{ fontSize: 12, color: "var(--home-muted)" }}>No data yet</div>}
          </div>
        </div>

        {/* Endpoint usage + Companies row */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 40 }}>
          <div style={S.card}>
            <div style={S.label}>Feature Usage</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
              {stats?.endpoint_usage.map(e => (
                <div key={e.endpoint} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 13, color: "var(--home-text)" }}>{ENDPOINT_LABELS[e.endpoint] ?? e.endpoint}</span>
                  <span style={{ fontSize: 12, fontFamily: "var(--font-mono)", color: "var(--home-purple)" }}>{e.count}×</span>
                </div>
              ))}
              {!stats?.endpoint_usage.length && <div style={{ fontSize: 12, color: "var(--home-muted)" }}>No activity yet</div>}
            </div>
          </div>

          <div style={S.card}>
            <div style={S.label}>Researched Companies</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8, maxHeight: 220, overflowY: "auto" }}>
              {stats?.loaded_companies.map(c => (
                <div key={c.ticker} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <span style={{ fontSize: 13, color: "var(--home-text)" }}>{c.company}</span>
                    <span style={{ fontSize: 11, color: "var(--home-muted)", marginLeft: 8, fontFamily: "var(--font-mono)" }}>{c.ticker}</span>
                  </div>
                  <span style={{
                    fontSize: 10, fontFamily: "var(--font-mono)", padding: "2px 7px", borderRadius: 6,
                    background: c.status === "ready" ? "rgba(16,185,129,0.1)" : "var(--home-purple-dim)",
                    color: c.status === "ready" ? "#10b981" : "var(--home-purple)",
                    border: `1px solid ${c.status === "ready" ? "rgba(16,185,129,0.2)" : "var(--home-purple-border)"}`,
                  }}>{c.status}</span>
                </div>
              ))}
              {!stats?.loaded_companies.length && <div style={{ fontSize: 12, color: "var(--home-muted)" }}>No companies loaded yet</div>}
            </div>
          </div>
        </div>

        {/* Users table */}
        <div style={S.section}>
          <div style={{ ...S.label, marginBottom: 16 }}>All Users</div>
          <div style={{ background: "var(--home-bg2)", border: "1px solid var(--home-border)", borderRadius: 12, overflow: "hidden" }}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {["Email", "Role", "Verified", "Credits Today", "Total Credits", "Joined"].map(h => (
                      <th key={h} style={S.th}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}
                      onMouseEnter={e => (e.currentTarget.style.background = "var(--home-bg3)")}
                      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                    >
                      <td style={S.td}>{u.email}</td>
                      <td style={S.td}>
                        <span style={{
                          fontSize: 11, fontFamily: "var(--font-mono)", padding: "3px 8px", borderRadius: 6,
                          background: u.role === "admin" ? "rgba(167,139,250,0.12)" : "rgba(255,255,255,0.04)",
                          color: u.role === "admin" ? "var(--home-purple)" : "var(--home-muted)",
                          border: `1px solid ${u.role === "admin" ? "rgba(167,139,250,0.2)" : "var(--home-border)"}`,
                        }}>{u.role}</span>
                      </td>
                      <td style={{ ...S.td, color: u.is_verified ? "#10b981" : "var(--home-muted)" }}>
                        {u.is_verified ? "Yes" : "No"}
                      </td>
                      <td style={{ ...S.td, fontFamily: "var(--font-mono)", fontSize: 12 }}>{u.credits_used_today} / 10</td>
                      <td style={{ ...S.td, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--home-muted)" }}>{(u as AdminUser & { credits_used_total: number }).credits_used_total ?? 0}</td>
                      <td style={{ ...S.td, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--home-muted)" }}>
                        {new Date(u.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <p style={{ marginTop: 10, fontSize: 11, color: "var(--home-muted2)", fontFamily: "var(--font-mono)" }}>
            {users.length} user{users.length !== 1 ? "s" : ""} total
          </p>
        </div>

      </div>
    </div>
  );
}
