"use client";

const sidebarItems = [
  { label: "Overview", icon: "○", active: true },
  { label: "Regulations", icon: "◈", active: false },
  { label: "Controls", icon: "◇", active: false },
  { label: "Actions", icon: "△", active: false },
  { label: "Graph", icon: "⬡", active: false },
  { label: "Alerts", icon: "◎", active: false },
];

const obligations = [
  { id: "OBL-001", text: "Entities must implement ICT risk management frameworks within 12 months", who: "Financial entities", deadline: "12 months", risk: "CRITICAL" },
  { id: "OBL-002", text: "All ICT-related incidents must be classified and reported to competent authorities within 4 hours of detection", who: "All entities", deadline: "4 hours", risk: "HIGH" },
  { id: "OBL-003", text: "Third-party ICT service provider contracts must include exit strategies and audit rights clauses", who: "Compliance", deadline: "6 months", risk: "HIGH" },
];

export default function Hero() {
  return (
    <section className="spotlight" style={{ minHeight: "100vh", paddingTop: 52, display: "flex", flexDirection: "column" }}>

      {/* ── Copy block ─────────────────────────── */}
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "80px 24px 0", width: "100%" }}>

        {/* Headline */}
        <h1
          className="anim"
          style={{
            animationDelay: "0ms",
            fontSize: "clamp(2.6rem, 6vw, 4.8rem)",
            fontWeight: 700,
            lineHeight: 1.06,
            letterSpacing: "-0.04em",
            color: "#fff",
            maxWidth: 820,
            marginBottom: 28,
          }}
        >
          The compliance monitoring
          <br />system for teams and agents
        </h1>

        {/* Subtitle row */}
        <div
          className="anim"
          style={{
            animationDelay: "80ms",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 24,
            flexWrap: "wrap",
            marginBottom: 48,
          }}
        >
          <p style={{ fontSize: 15, color: "#666", maxWidth: 500, lineHeight: 1.6 }}>
            Purpose-built for tracking regulatory change and closing compliance gaps.
            Designed for the AI era.
          </p>

          {/* Announcement pill */}
          <a
            href="#"
            style={{
              display: "flex", alignItems: "center", gap: 10,
              fontSize: 13, color: "#999", textDecoration: "none",
              whiteSpace: "nowrap",
            }}
            onMouseEnter={e => (e.currentTarget.style.color = "#fff")}
            onMouseLeave={e => (e.currentTarget.style.color = "#999")}
          >
            <span className="blink" style={{ width: 7, height: 7, borderRadius: "50%", background: "#E5484D", flexShrink: 0, display: "inline-block" }} />
            Manual compliance review is dead
            <span style={{ marginLeft: 4, display: "flex", alignItems: "center", gap: 4 }}>
              redforge.ai/next
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M2.5 6h7M6.5 3.5L9 6l-2.5 2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </span>
          </a>
        </div>

        {/* CTAs */}
        <div className="anim" style={{ animationDelay: "150ms", display: "flex", gap: 10, marginBottom: 72 }}>
          <a href="#" style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            padding: "9px 18px", borderRadius: 8, fontSize: 14, fontWeight: 500,
            color: "#fff", textDecoration: "none",
            background: "linear-gradient(135deg,#E5484D,#C73E3E)",
            boxShadow: "0 1px 0 rgba(255,255,255,0.1) inset",
          }}>
            Get early access
            <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
              <path d="M2 6.5h9M7.5 3L11 6.5 7.5 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </a>
          <a href="#pipeline" style={{
            display: "inline-flex", alignItems: "center", padding: "9px 18px",
            borderRadius: 8, fontSize: 14, fontWeight: 500, color: "#888",
            textDecoration: "none", border: "1px solid rgba(255,255,255,0.1)",
            transition: "color .15s, border-color .15s",
          }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLElement).style.color = "#fff";
              (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.22)";
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.color = "#888";
              (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.1)";
            }}
          >
            See how it works
          </a>
        </div>
      </div>

      {/* ── App mockup ─────────────────────────── */}
      <div
        className="anim"
        style={{
          animationDelay: "220ms",
          flex: 1,
          maxWidth: 1200,
          margin: "0 auto",
          width: "100%",
          padding: "0 24px",
          paddingBottom: 0,
        }}
      >
        <div className="gradient-border" style={{
          borderRadius: "14px 14px 0 0",
          border: "none",
          background: "#111111",
          overflow: "hidden",
          boxShadow: "0 0 0 1px rgba(255,255,255,0.06), 0 24px 80px rgba(0,0,0,0.9), 0 0 80px rgba(229,72,77,0.06)",
          display: "flex",
          flexDirection: "column",
          minHeight: 480,
        }}>

          {/* Window chrome */}
          <div style={{
            height: 42, display: "flex", alignItems: "center", padding: "0 16px", gap: 8,
            borderBottom: "1px solid rgba(255,255,255,0.07)",
            background: "#0E0E0E",
          }}>
            <div style={{ display: "flex", gap: 6 }}>
              {["#E5484D","#F59E0B","#22C55E"].map((c,i) => (
                <div key={i} style={{ width: 11, height: 11, borderRadius: "50%", background: c, opacity: i===0?0.8:i===1?0.5:0.4 }} />
              ))}
            </div>
            <div style={{
              flex:1, maxWidth: 260, margin: "0 auto",
              height: 22, borderRadius: 5,
              background: "rgba(255,255,255,0.05)",
              display: "flex", alignItems: "center", padding: "0 10px", gap: 5,
            }}>
              <svg width="9" height="9" viewBox="0 0 9 9" fill="none">
                <circle cx="4.5" cy="4.5" r="3.5" stroke="rgba(255,255,255,0.2)" strokeWidth="1"/>
              </svg>
              <span style={{ fontSize: 11, color: "#333" }}>app.redforge.ai</span>
            </div>
          </div>

          {/* Three-panel layout */}
          <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>

            {/* Left sidebar */}
            <div style={{
              width: 210, flexShrink: 0,
              borderRight: "1px solid rgba(255,255,255,0.07)",
              background: "#0E0E0E",
              padding: "14px 8px",
              display: "flex", flexDirection: "column",
            }}>
              {/* Workspace */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 8px 14px", borderBottom: "1px solid rgba(255,255,255,0.07)", marginBottom: 10 }}>
                <div style={{ width: 22, height: 22, borderRadius: 6, background: "#E5484D", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <svg width="10" height="10" viewBox="0 0 14 14" fill="none">
                    <path d="M2 12L5.5 5.5L9 9L11.5 2" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#ddd" }}>Red Forge</span>
                <svg style={{ marginLeft: "auto" }} width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <path d="M4 5.5l2.5 2.5L9 5.5" stroke="#444" strokeWidth="1.3" strokeLinecap="round"/>
                </svg>
              </div>

              {sidebarItems.map(item => (
                <div key={item.label} style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "6px 8px", borderRadius: 6,
                  background: item.active ? "rgba(255,255,255,0.06)" : "transparent",
                  color: item.active ? "#ddd" : "#555",
                  fontSize: 13, cursor: "pointer", marginBottom: 1,
                }}>
                  <span style={{ fontSize: 10, width: 14, textAlign: "center" }}>{item.icon}</span>
                  {item.label}
                </div>
              ))}

              <div style={{ marginTop: "auto", padding: "12px 8px 4px", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
                <div style={{ fontSize: 11, color: "#333", marginBottom: 6 }}>Pipeline health</div>
                <div style={{ height: 2, borderRadius: 2, background: "rgba(255,255,255,0.07)", overflow: "hidden" }}>
                  <div style={{ width: "84%", height: "100%", background: "#22C55E", borderRadius: 2 }} />
                </div>
                <div style={{ fontSize: 11, color: "#333", marginTop: 4 }}>84% uptime · 3 agents running</div>
              </div>
            </div>

            {/* Main panel */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
              {/* Toolbar */}
              <div style={{
                height: 40, display: "flex", alignItems: "center",
                padding: "0 16px", gap: 8,
                borderBottom: "1px solid rgba(255,255,255,0.07)",
                background: "#0F0F0F",
              }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: "#ddd" }}>DORA RTS — ICT risk management</span>
                <div style={{ display: "flex", alignItems: "center", gap: 4, marginLeft: "auto" }}>
                  <span style={{ fontSize: 11, color: "#444" }}>02 / 23 obligations</span>
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <path d="M5 3.5l2.5 2.5L5 8.5" stroke="#444" strokeWidth="1.3" strokeLinecap="round"/>
                  </svg>
                </div>
              </div>

              {/* Content */}
              <div style={{ padding: "20px 20px", overflow: "auto", flex: 1 }}>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: "#eee", marginBottom: 8 }}>
                  DORA RTS on ICT risk management
                </h3>
                <p style={{ fontSize: 13, color: "#555", marginBottom: 18, lineHeight: 1.6 }}>
                  Published by EUR-Lex · DORA · EU · 2024-01-17 ·{" "}
                  <span style={{ color: "#E5484D", fontWeight: 500 }}>23 obligations extracted</span>
                </p>

                {/* Obligations */}
                <div style={{ fontSize: 12, fontWeight: 500, color: "#444", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  Extracted obligations
                </div>
                {obligations.map((obl) => (
                  <div key={obl.id} style={{
                    border: "1px solid rgba(255,255,255,0.07)",
                    borderRadius: 8, padding: "12px 14px", marginBottom: 8,
                    background: "#131313",
                  }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                      <span style={{ fontSize: 11, color: "#444", fontFamily: "monospace" }}>{obl.id}</span>
                      <span style={{
                        fontSize: 10, padding: "2px 7px", borderRadius: 4, fontWeight: 600,
                        color: obl.risk === "CRITICAL" ? "#F59E0B" : "#E5484D",
                        background: obl.risk === "CRITICAL" ? "rgba(245,158,11,0.12)" : "rgba(229,72,77,0.12)",
                        border: `1px solid ${obl.risk === "CRITICAL" ? "rgba(245,158,11,0.25)" : "rgba(229,72,77,0.25)"}`,
                      }}>{obl.risk}</span>
                      <span style={{ fontSize: 11, color: "#444", marginLeft: "auto" }}>Deadline: {obl.deadline}</span>
                    </div>
                    <p style={{ fontSize: 13, color: "#aaa", lineHeight: 1.5 }}>{obl.text}</p>
                    <p style={{ fontSize: 11, color: "#444", marginTop: 5 }}>WHO: {obl.who}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Right detail panel */}
            <div style={{
              width: 240, flexShrink: 0,
              borderLeft: "1px solid rgba(255,255,255,0.07)",
              background: "#0E0E0E",
              padding: "14px 14px",
            }}>
              <div style={{ fontSize: 11, fontWeight: 500, color: "#444", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 14 }}>
                Properties
              </div>

              {[
                { label: "Risk", value: "HIGH", valueColor: "#E5484D" },
                { label: "Jurisdiction", value: "EU", valueColor: "#8B8D97" },
                { label: "Framework", value: "DORA", valueColor: "#8B8D97" },
                { label: "Published", value: "2024-01-17", valueColor: "#8B8D97" },
                { label: "Obligations", value: "23 extracted", valueColor: "#22C55E" },
                { label: "Gap coverage", value: "41%", valueColor: "#F59E0B" },
              ].map(row => (
                <div key={row.label} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.05)",
                }}>
                  <span style={{ fontSize: 12, color: "#444" }}>{row.label}</span>
                  <span style={{ fontSize: 12, fontWeight: 500, color: row.valueColor }}>{row.value}</span>
                </div>
              ))}

              {/* AI agent status */}
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 500, color: "#444", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>
                  Agent status
                </div>
                {[
                  { name: "Scanner", status: "Done", color: "#22C55E" },
                  { name: "Extractor", status: "Done", color: "#22C55E" },
                  { name: "Impact Analyst", status: "Running", color: "#F59E0B" },
                  { name: "Planner", status: "Queued", color: "#444" },
                  { name: "Validator", status: "Queued", color: "#444" },
                ].map(agent => (
                  <div key={agent.name} style={{
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    padding: "5px 0",
                  }}>
                    <span style={{ fontSize: 12, color: "#555" }}>{agent.name}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                      <div className={agent.status === "Running" ? "blink" : ""} style={{ width: 6, height: 6, borderRadius: "50%", background: agent.color }} />
                      <span style={{ fontSize: 11, color: agent.color }}>{agent.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
