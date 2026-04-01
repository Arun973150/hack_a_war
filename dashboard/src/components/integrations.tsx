"use client";

const integrations = [
  { name: "Jira", desc: "Push action items as tasks with priority and owner pre-filled.", color: "#2684FF" },
  { name: "Slack", desc: "Get notified the moment a high-risk regulation drops.", color: "#E01E5A" },
  { name: "GitHub", desc: "Create compliance issues and PRs to update policy docs.", color: "#aaa" },
  { name: "ServiceNow", desc: "Sync action items to GRC workflows and your risk register.", color: "#81B5A1" },
  { name: "LangSmith", desc: "Full trace logging for every agent run — debug and audit.", color: "#F59E0B" },
  { name: "Grafana", desc: "Pipeline health, ingestion rates, and agent latency on one board.", color: "#F46800" },
];

export default function Integrations() {
  return (
    <section id="integrations" style={{ borderTop: "1px solid rgba(255,255,255,0.07)", padding: "96px 0" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "48px 80px", alignItems: "start", marginBottom: 56 }}>
          <h2 style={{ fontSize: "clamp(2rem,4vw,3rem)", fontWeight: 700, letterSpacing: "-0.035em", lineHeight: 1.1, color: "#fff" }}>
            Fits where your<br />team already works
          </h2>
          <p style={{ fontSize: "1.15rem", color: "#555", lineHeight: 1.65, paddingTop: 8 }}>
            Red Forge slots into your existing compliance and engineering stack.
            No new portal. No new login. Just results where you already look.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 1, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, overflow: "hidden" }}>
          {integrations.map((int) => (
            <div key={int.name} style={{ background: "#0A0A0A", padding: "24px", display: "flex", flexDirection: "column", gap: 10, transition: "background .15s" }}
              onMouseEnter={e => (e.currentTarget.style.background = "#111")}
              onMouseLeave={e => (e.currentTarget.style.background = "#0A0A0A")}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: int.color }} />
                <span style={{ fontSize: 14, fontWeight: 600, color: "#ddd" }}>{int.name}</span>
              </div>
              <p style={{ fontSize: 13, color: "#444", lineHeight: 1.6 }}>{int.desc}</p>
            </div>
          ))}
        </div>

        <p style={{ marginTop: 20, fontSize: 13, color: "#333" }}>
          Everything available via REST API.{" "}
          <a href="#" style={{ color: "#555", textDecoration: "underline", textUnderlineOffset: 3 }}>Read the docs →</a>
        </p>
      </div>
    </section>
  );
}
