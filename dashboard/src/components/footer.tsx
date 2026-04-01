"use client";

const cols = [
  { title: "Product", links: ["How it works","Features","Integrations","Changelog","Roadmap"] },
  { title: "Frameworks", links: ["GDPR","HIPAA","EU AI Act","DORA","SEBI / RBI"] },
  { title: "Developers", links: ["API docs","GitHub","LangSmith traces","Self-hosted","Webhooks"] },
  { title: "Company", links: ["About","Blog","Privacy","Terms","Contact"] },
];

export default function Footer() {
  return (
    <footer style={{ borderTop: "1px solid rgba(255,255,255,0.07)", background: "#0A0A0A", padding: "64px 0 40px" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr 1fr 1fr", gap: 40, marginBottom: 64 }}>

          {/* Brand */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
              <div style={{ width: 24, height: 24, borderRadius: 6, background: "linear-gradient(135deg,#E5484D,#B83E42)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <svg width="10" height="10" viewBox="0 0 14 14" fill="none">
                  <path d="M2 12L5.5 5.5L9 9L11.5 2" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <span style={{ fontSize: 14, fontWeight: 600, color: "#fff" }}>Red Forge</span>
            </div>
            <p style={{ fontSize: 13, color: "#333", lineHeight: 1.65, maxWidth: 200 }}>
              AI-powered regulatory compliance monitoring for modern teams.
            </p>
          </div>

          {/* Link columns */}
          {cols.map(col => (
            <div key={col.title}>
              <p style={{ fontSize: 12, color: "#555", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 16 }}>{col.title}</p>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {col.links.map(link => (
                  <a key={link} href="#" style={{ fontSize: 13, color: "#333", textDecoration: "none", transition: "color .15s" }}
                    onMouseEnter={e => (e.currentTarget.style.color = "#777")}
                    onMouseLeave={e => (e.currentTarget.style.color = "#333")}
                  >{link}</a>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: 24, borderTop: "1px solid rgba(255,255,255,0.05)" }}>
          <p style={{ fontSize: 12, color: "#222" }}>© {new Date().getFullYear()} Red Forge. All rights reserved.</p>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#22C55E" }} className="blink" />
            <span style={{ fontSize: 12, color: "#222" }}>All systems operational</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
