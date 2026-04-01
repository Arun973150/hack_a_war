"use client";
/* eslint-disable react/no-unescaped-entities */

// ─── Mockup components ────────────────────────────────────────────────────────

function MonitorMockup() {
  const feeds = [
    { source: "Federal Register", id: "FR-2024-8821", title: "CFPB amends Regulation Z — open-end credit provisions updated", risk: "HIGH", riskColor: "#E5484D", time: "2m ago", status: "Analyzing" },
    { source: "EUR-Lex", id: "EU-DORA-0041", title: "DORA RTS on ICT risk management published — 23 new obligations", risk: "CRITICAL", riskColor: "#F59E0B", time: "1h ago", status: "Done" },
    { source: "SEBI", id: "SEBI-CIR-2024", title: "Circular on research analyst regulations — updated disclosure norms", risk: "MEDIUM", riskColor: "#8B5CF6", time: "3h ago", status: "Done" },
    { source: "RBI", id: "RBI-MAS-110", title: "Master directions on KYC — updated digital onboarding requirements", risk: "HIGH", riskColor: "#E5484D", time: "5h ago", status: "Done" },
    { source: "Federal Register", id: "FR-2024-8799", title: "HHS HIPAA Security Rule proposed rulemaking — encryption mandate", risk: "CRITICAL", riskColor: "#F59E0B", time: "8h ago", status: "Done" },
    { source: "EUR-Lex", id: "EU-NIS2-0112", title: "NIS2 implementing acts on incident reporting thresholds", risk: "HIGH", riskColor: "#E5484D", time: "12h ago", status: "Done" },
  ];

  return (
    <div style={{ borderRadius: "12px 12px 0 0", border: "none", background: "#111", overflow: "hidden", boxShadow: "0 0 0 1px rgba(255,255,255,0.07), 0 0 60px rgba(229,72,77,0.05)" }}>
      {/* Toolbar */}
      <div style={{ height: 42, display: "flex", alignItems: "center", padding: "0 16px", gap: 12, borderBottom: "1px solid rgba(255,255,255,0.07)", background: "#0E0E0E" }}>
        <div style={{ display: "flex", gap: 6 }}>
          {["#E5484D","#F59E0B","#22C55E"].map((c,i) => <div key={i} style={{ width: 10, height: 10, borderRadius: "50%", background: c, opacity: i===0?0.7:i===1?0.5:0.4 }} />)}
        </div>
        <span style={{ fontSize: 13, fontWeight: 500, color: "#555", marginLeft: 8 }}>Ingestion feed · Last 24 hours</span>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#22C55E" }} className="blink" />
          <span style={{ fontSize: 11, color: "#333" }}>Live · 6 sources active</span>
        </div>
      </div>

      {/* Column headers */}
      <div style={{ display: "grid", gridTemplateColumns: "140px 1fr 80px 90px 80px", gap: 0, padding: "8px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
        {["Source","Document","Risk","Status","Time"].map(h => (
          <span key={h} style={{ fontSize: 11, color: "#333", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</span>
        ))}
      </div>

      {/* Rows */}
      {feeds.map((f, i) => (
        <div key={i} style={{
          display: "grid", gridTemplateColumns: "140px 1fr 80px 90px 80px",
          gap: 0, padding: "10px 16px",
          borderBottom: "1px solid rgba(255,255,255,0.04)",
          background: i === 0 ? "rgba(255,255,255,0.02)" : "transparent",
        }}>
          <span style={{ fontSize: 12, color: "#444", fontFamily: "monospace" }}>{f.source}</span>
          <span style={{ fontSize: 12, color: i === 0 ? "#bbb" : "#555", paddingRight: 16, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{f.title}</span>
          <span style={{ fontSize: 11, color: f.riskColor, fontWeight: 600 }}>{f.risk}</span>
          <span style={{ fontSize: 11, color: f.status === "Analyzing" ? "#F59E0B" : "#333" }}>
            {f.status === "Analyzing" ? "⟳ Analyzing" : "✓ Done"}
          </span>
          <span style={{ fontSize: 11, color: "#333" }}>{f.time}</span>
        </div>
      ))}
    </div>
  );
}

function ExtractMockup() {
  return (
    <div style={{ borderRadius: "12px 12px 0 0", border: "none", background: "#111", overflow: "hidden", display: "flex", boxShadow: "0 0 0 1px rgba(255,255,255,0.07), 0 0 60px rgba(229,72,77,0.05)" }}>
      {/* Left - document viewer */}
      <div style={{ flex: 1, borderRight: "1px solid rgba(255,255,255,0.07)" }}>
        <div style={{ height: 42, display: "flex", alignItems: "center", padding: "0 16px", borderBottom: "1px solid rgba(255,255,255,0.07)", background: "#0E0E0E", gap: 8 }}>
          <div style={{ display: "flex", gap: 6 }}>
            {["#E5484D","#F59E0B","#22C55E"].map((c,i) => <div key={i} style={{ width: 10, height: 10, borderRadius: "50%", background: c, opacity: i===0?0.7:0.4 }} />)}
          </div>
          <span style={{ fontSize: 12, color: "#555", marginLeft: 8, fontFamily: "monospace" }}>DORA-RTS-ICT-2024.pdf</span>
        </div>
        <div style={{ padding: "20px 20px", fontFamily: "monospace", fontSize: 12, lineHeight: 1.7, color: "#444" }}>
          <p style={{ marginBottom: 8, color: "#666" }}>Article 5 — ICT risk management framework</p>
          <p style={{ marginBottom: 12 }}>
            <span style={{ color: "#777" }}>1. Financial entities shall have in place </span>
            <span style={{ background: "rgba(229,72,77,0.15)", color: "#E5484D", padding: "1px 4px", borderRadius: 3 }}>
              a sound, comprehensive and well-documented ICT risk management framework
            </span>
            <span style={{ color: "#777" }}> as part of their overall risk management system.</span>
          </p>
          <p style={{ marginBottom: 12 }}>
            <span style={{ color: "#777" }}>2. The ICT risk management framework shall enable </span>
            <span style={{ background: "rgba(245,158,11,0.12)", color: "#F59E0B", padding: "1px 4px", borderRadius: 3 }}>
              financial entities to address ICT risk quickly, efficiently and comprehensively
            </span>
            <span style={{ color: "#777" }}> and to ensure a high level of digital operational resilience.</span>
          </p>
          <p style={{ color: "#333" }}>3. The ICT risk management framework shall include at least the strategies, policies, protocols and tools necessary...</p>
        </div>
      </div>

      {/* Right - extracted obligations */}
      <div style={{ width: 340, flexShrink: 0 }}>
        <div style={{ height: 42, display: "flex", alignItems: "center", padding: "0 16px", borderBottom: "1px solid rgba(255,255,255,0.07)", background: "#0E0E0E" }}>
          <span style={{ fontSize: 12, fontWeight: 500, color: "#555" }}>Extracted · 2 of 23</span>
        </div>
        <div style={{ padding: "12px", display: "flex", flexDirection: "column", gap: 8 }}>
          {[
            { id: "OBL-001", who: "Financial entities", what: "Implement ICT risk management framework", when: "12 months", risk: "CRITICAL", riskColor: "#F59E0B" },
            { id: "OBL-002", who: "All entities", what: "Ensure high-level digital operational resilience", when: "Ongoing", risk: "HIGH", riskColor: "#E5484D" },
          ].map(o => (
            <div key={o.id} style={{ padding: "12px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.08)", background: "#131313" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontSize: 10, color: "#333", fontFamily: "monospace" }}>{o.id}</span>
                <span style={{ fontSize: 10, color: o.riskColor, fontWeight: 600, background: `${o.riskColor}15`, padding: "2px 6px", borderRadius: 4 }}>{o.risk}</span>
              </div>
              <p style={{ fontSize: 12, color: "#aaa", lineHeight: 1.5, marginBottom: 8 }}>{o.what}</p>
              <div style={{ display: "flex", gap: 12 }}>
                <span style={{ fontSize: 10, color: "#333" }}>WHO: <span style={{ color: "#555" }}>{o.who}</span></span>
                <span style={{ fontSize: 10, color: "#333" }}>BY: <span style={{ color: "#555" }}>{o.when}</span></span>
              </div>
            </div>
          ))}
          <div style={{ padding: "10px 12px", borderRadius: 8, border: "1px dashed rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
            <span style={{ fontSize: 11, color: "#2A2A2A" }}>+ 21 more obligations being extracted...</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function AnalyzeMockup() {
  const controls = [
    { id: "CTL-014", name: "ICT Risk Management Policy", framework: "DORA", coverage: 82, obligations: 4, status: "covered" },
    { id: "CTL-027", name: "Digital Resilience Testing", framework: "DORA", coverage: 34, obligations: 7, status: "gap" },
    { id: "CTL-031", name: "Third-party Risk Assessment", framework: "DORA", coverage: 0, obligations: 5, status: "missing" },
    { id: "CTL-008", name: "Incident Classification Procedure", framework: "DORA", coverage: 61, obligations: 3, status: "gap" },
    { id: "CTL-042", name: "Audit Rights & Exit Clauses", framework: "DORA", coverage: 0, obligations: 2, status: "missing" },
  ];

  return (
    <div style={{ borderRadius: "12px 12px 0 0", border: "none", background: "#111", overflow: "hidden", boxShadow: "0 0 0 1px rgba(255,255,255,0.07), 0 0 60px rgba(229,72,77,0.05)" }}>
      <div style={{ height: 42, display: "flex", alignItems: "center", padding: "0 16px", gap: 8, borderBottom: "1px solid rgba(255,255,255,0.07)", background: "#0E0E0E" }}>
        <div style={{ display: "flex", gap: 6 }}>
          {["#E5484D","#F59E0B","#22C55E"].map((c,i) => <div key={i} style={{ width: 10, height: 10, borderRadius: "50%", background: c, opacity: i===0?0.7:0.4 }} />)}
        </div>
        <span style={{ fontSize: 13, fontWeight: 500, color: "#555", marginLeft: 8 }}>Gap analysis · DORA RTS · 23 obligations · 11 controls checked</span>
        <div style={{ marginLeft: "auto", fontSize: 12, color: "#E5484D", fontWeight: 600 }}>41% coverage</div>
      </div>

      {/* Summary bar */}
      <div style={{ padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", gap: 20 }}>
        {[
          { label: "Covered", count: 3, color: "#22C55E" },
          { label: "Partial gap", count: 5, color: "#F59E0B" },
          { label: "Missing control", count: 3, color: "#E5484D" },
        ].map(s => (
          <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 8, height: 8, borderRadius: 2, background: s.color }} />
            <span style={{ fontSize: 12, color: "#555" }}>{s.count} {s.label}</span>
          </div>
        ))}
        {/* Coverage bar */}
        <div style={{ flex: 1, height: 4, borderRadius: 2, background: "rgba(255,255,255,0.06)", overflow: "hidden", alignSelf: "center", marginLeft: 8 }}>
          <div style={{ width: "41%", height: "100%", background: "linear-gradient(90deg,#E5484D,#F59E0B)", borderRadius: 2 }} />
        </div>
      </div>

      {/* Table headers */}
      <div style={{ display: "grid", gridTemplateColumns: "80px 1fr 80px 100px 80px", padding: "8px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
        {["Control","Name","Coverage","Obligations","Status"].map(h => (
          <span key={h} style={{ fontSize: 11, color: "#333", textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</span>
        ))}
      </div>

      {controls.map((c, i) => (
        <div key={c.id} style={{
          display: "grid", gridTemplateColumns: "80px 1fr 80px 100px 80px",
          padding: "10px 16px", borderBottom: "1px solid rgba(255,255,255,0.04)",
          background: c.status === "missing" ? "rgba(229,72,77,0.03)" : "transparent",
        }}>
          <span style={{ fontSize: 11, color: "#333", fontFamily: "monospace" }}>{c.id}</span>
          <span style={{ fontSize: 12, color: "#777" }}>{c.name}</span>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ flex: 1, height: 3, borderRadius: 2, background: "rgba(255,255,255,0.06)", overflow: "hidden" }}>
              <div style={{
                width: `${c.coverage}%`, height: "100%", borderRadius: 2,
                background: c.coverage >= 80 ? "#22C55E" : c.coverage > 0 ? "#F59E0B" : "#E5484D"
              }} />
            </div>
            <span style={{ fontSize: 10, color: "#444", width: 26, textAlign: "right" }}>{c.coverage}%</span>
          </div>
          <span style={{ fontSize: 12, color: "#555" }}>{c.obligations} obligations</span>
          <span style={{ fontSize: 11, fontWeight: 600, color: c.status === "covered" ? "#22C55E" : c.status === "gap" ? "#F59E0B" : "#E5484D" }}>
            {c.status === "covered" ? "✓ Covered" : c.status === "gap" ? "⚠ Gap" : "✗ Missing"}
          </span>
        </div>
      ))}
    </div>
  );
}

function ActMockup() {
  const items = [
    { id: "ACT-001", title: "Implement ICT risk management framework documentation", owner: "Compliance", deadline: "90 days", effort: "21d", priority: "CRITICAL", priorityColor: "#F59E0B", status: "open", jira: null },
    { id: "ACT-002", title: "Establish digital resilience testing programme (TLPT)", owner: "IT Security", deadline: "60 days", effort: "14d", priority: "HIGH", priorityColor: "#E5484D", status: "open", jira: null },
    { id: "ACT-003", title: "Update third-party contracts with audit rights clauses", owner: "Legal", deadline: "30 days", effort: "7d", priority: "HIGH", priorityColor: "#E5484D", status: "in_progress", jira: "COMP-214" },
    { id: "ACT-004", title: "Define ICT incident classification taxonomy", owner: "IT Security", deadline: "45 days", effort: "5d", priority: "MEDIUM", priorityColor: "#8B5CF6", status: "open", jira: null },
    { id: "ACT-005", title: "Create exit strategy documentation for critical ICT providers", owner: "Procurement", deadline: "120 days", effort: "10d", priority: "MEDIUM", priorityColor: "#8B5CF6", status: "open", jira: null },
  ];

  return (
    <div style={{ borderRadius: "12px 12px 0 0", border: "none", background: "#111", overflow: "hidden", boxShadow: "0 0 0 1px rgba(255,255,255,0.07), 0 0 60px rgba(229,72,77,0.05)" }}>
      <div style={{ height: 42, display: "flex", alignItems: "center", padding: "0 16px", gap: 8, borderBottom: "1px solid rgba(255,255,255,0.07)", background: "#0E0E0E" }}>
        <div style={{ display: "flex", gap: 6 }}>
          {["#E5484D","#F59E0B","#22C55E"].map((c,i) => <div key={i} style={{ width: 10, height: 10, borderRadius: "50%", background: c, opacity: i===0?0.7:0.4 }} />)}
        </div>
        <span style={{ fontSize: 13, fontWeight: 500, color: "#555", marginLeft: 8 }}>Action items · DORA RTS · 5 generated</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <button style={{ fontSize: 11, color: "#555", border: "1px solid rgba(255,255,255,0.08)", background: "none", padding: "3px 10px", borderRadius: 5, cursor: "pointer" }}>Filter</button>
          <button style={{ fontSize: 11, color: "#fff", background: "#E5484D", border: "none", padding: "3px 10px", borderRadius: 5, cursor: "pointer" }}>Export to Jira</button>
        </div>
      </div>

      {/* Column headers */}
      <div style={{ display: "grid", gridTemplateColumns: "70px 1fr 90px 70px 60px 80px 80px", padding: "8px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
        {["ID","Action","Owner","Deadline","Effort","Priority","Status"].map(h => (
          <span key={h} style={{ fontSize: 11, color: "#333", textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</span>
        ))}
      </div>

      {items.map((item, i) => (
        <div key={item.id} style={{
          display: "grid", gridTemplateColumns: "70px 1fr 90px 70px 60px 80px 80px",
          padding: "10px 16px", borderBottom: "1px solid rgba(255,255,255,0.04)",
          alignItems: "center",
          background: item.status === "in_progress" ? "rgba(255,255,255,0.015)" : "transparent",
        }}>
          <span style={{ fontSize: 11, color: "#333", fontFamily: "monospace" }}>{item.id}</span>
          <span style={{ fontSize: 12, color: "#777", paddingRight: 12, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.title}</span>
          <span style={{ fontSize: 12, color: "#555" }}>{item.owner}</span>
          <span style={{ fontSize: 11, color: "#444" }}>{item.deadline}</span>
          <span style={{ fontSize: 11, color: "#444", fontFamily: "monospace" }}>{item.effort}</span>
          <span style={{ fontSize: 11, fontWeight: 600, color: item.priorityColor }}>{item.priority}</span>
          <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
            {item.jira
              ? <span style={{ fontSize: 10, color: "#2684FF", fontFamily: "monospace" }}>{item.jira}</span>
              : <span style={{ fontSize: 11, color: item.status === "in_progress" ? "#F59E0B" : "#333" }}>
                  {item.status === "in_progress" ? "In progress" : "Open"}
                </span>
            }
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Section layout ───────────────────────────────────────────────────────────

type Section = {
  version: string;
  versionLabel: string;
  headline: string;
  description: string;
  mockup: React.ReactNode;
};

const sections: Section[] = [
  {
    version: "1.0",
    versionLabel: "Monitor",
    headline: "Make regulatory monitoring automatic",
    description: "Red Forge connects to Federal Register, EUR-Lex, SEBI, RBI, and a dozen more sources. Every new document is fetched, parsed, and queued for AI analysis — no manual checking, no RSS feeds, no missed filings.",
    mockup: <MonitorMockup />,
  },
  {
    version: "2.0",
    versionLabel: "Extract",
    headline: "Extract every obligation that matters",
    description: "A dedicated AI agent reads every clause and pulls out structured obligations: who must do what, by when, under what conditions, and what the penalty is. Output is structured JSON with direct citations — not a summary, not a guess.",
    mockup: <ExtractMockup />,
  },
  {
    version: "3.0",
    versionLabel: "Analyze",
    headline: "Find the gaps before auditors do",
    description: "Red Forge cross-references every new obligation against your existing control library using Qdrant for semantic similarity and Neo4j for knowledge graph traversal. It tells you exactly what's covered, what's partially addressed, and what has no control at all.",
    mockup: <AnalyzeMockup />,
  },
  {
    version: "4.0",
    versionLabel: "Act",
    headline: "Turn every gap into a concrete action",
    description: "Every identified gap becomes a prioritized action item with an owner, a deadline, an effort estimate, and a risk score. One click exports them all to Jira. Your team just executes — the hard thinking is already done.",
    mockup: <ActMockup />,
  },
];

export default function FeatureSections() {
  return (
    <div>
      {sections.map((section, i) => (
        <section
          key={section.version}
          id={`feature-${section.version}`}
          className="spotlight"
          style={{ borderTop: "1px solid rgba(255,255,255,0.07)", padding: "96px 0 0" }}
        >
          <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>

            {/* Two-column header */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "48px 80px", marginBottom: 72, alignItems: "start" }}>
              {/* Left — bold headline */}
              <h2 style={{
                fontSize: "clamp(2rem,4vw,3rem)",
                fontWeight: 700,
                letterSpacing: "-0.035em",
                lineHeight: 1.1,
                color: "#fff",
              }}>
                {section.headline}
              </h2>

              {/* Right — description + version link */}
              <div>
                <p style={{ fontSize: "clamp(1.05rem,1.8vw,1.35rem)", color: "#777", lineHeight: 1.6, marginBottom: 32 }}>
                  {section.description}
                </p>
                <a
                  href="#"
                  style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 14, color: "#444", textDecoration: "none", transition: "color .15s" }}
                  onMouseEnter={e => (e.currentTarget.style.color = "#888")}
                  onMouseLeave={e => (e.currentTarget.style.color = "#444")}
                >
                  <span style={{ color: "#2A2A2A" }}>{section.version}</span>
                  {"  "}{section.versionLabel}
                  <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                    <path d="M2 6.5h9M7.5 3L11 6.5 7.5 10" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </a>
              </div>
            </div>

            {/* Full-width mockup — extends to edge */}
            {section.mockup}
          </div>
        </section>
      ))}
    </div>
  );
}
