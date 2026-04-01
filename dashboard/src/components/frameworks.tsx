"use client";

const frameworks = [
  "GDPR", "HIPAA", "SOC 2", "ISO 27001", "PCI DSS",
  "EU AI Act", "DORA", "NIS2", "SEBI", "RBI", "CCPA", "FTC Act",
];

export default function Frameworks() {
  return (
    <section style={{ borderTop: "1px solid rgba(255,255,255,0.07)", borderBottom: "1px solid rgba(255,255,255,0.07)", padding: "40px 0" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>
        <p style={{ fontSize: 12, color: "#333", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 500, marginBottom: 20 }}>
          Monitoring coverage across major frameworks
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {frameworks.map(fw => (
            <div key={fw} style={{
              padding: "5px 12px", borderRadius: 6, fontSize: 13, fontWeight: 500,
              color: "#999", border: "1px solid rgba(255,255,255,0.08)",
              background: "#111", cursor: "default", transition: "color .15s, border-color .15s",
            }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.color = "#fff";
                (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.18)";
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.color = "#999";
                (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.08)";
              }}
            >{fw}</div>
          ))}
        </div>
      </div>
    </section>
  );
}
