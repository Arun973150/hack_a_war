const figs = [
  {
    id: "FIG 0.2",
    label: "Built for precision",
    description: "Red Forge is shaped by the practices of compliance teams that cannot afford to miss anything.",
    svg: (
      <svg viewBox="0 0 280 260" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Isometric stacked document layers */}
        <g stroke="rgba(255,255,255,0.16)" strokeWidth="1" strokeLinejoin="round">
          {/* Layer 5 - bottom */}
          <polygon points="140,228 210,187 140,146 70,187" fill="rgba(255,255,255,0.02)"/>
          <line x1="70" y1="187" x2="70" y2="204" stroke="rgba(255,255,255,0.08)"/>
          <line x1="210" y1="187" x2="210" y2="204" stroke="rgba(255,255,255,0.08)"/>
          <polygon points="140,245 210,204 140,163 70,204" fill="none" stroke="rgba(255,255,255,0.06)"/>

          {/* Layer 4 */}
          <polygon points="140,204 210,163 140,122 70,163" fill="rgba(255,255,255,0.025)"/>
          <line x1="70" y1="163" x2="70" y2="187" stroke="rgba(255,255,255,0.06)"/>
          <line x1="210" y1="163" x2="210" y2="187" stroke="rgba(255,255,255,0.06)"/>

          {/* Layer 3 */}
          <polygon points="140,180 210,139 140,98 70,139" fill="rgba(255,255,255,0.03)"/>
          <line x1="70" y1="139" x2="70" y2="163" stroke="rgba(255,255,255,0.08)"/>
          <line x1="210" y1="139" x2="210" y2="163" stroke="rgba(255,255,255,0.08)"/>

          {/* Layer 2 */}
          <polygon points="140,156 210,115 140,74 70,115" fill="rgba(255,255,255,0.035)"/>
          <line x1="70" y1="115" x2="70" y2="139" stroke="rgba(255,255,255,0.1)"/>
          <line x1="210" y1="115" x2="210" y2="139" stroke="rgba(255,255,255,0.1)"/>

          {/* Top layer */}
          <polygon points="140,132 210,91 140,50 70,91" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.22)"/>
          <line x1="70" y1="91" x2="70" y2="115" stroke="rgba(255,255,255,0.12)"/>
          <line x1="210" y1="91" x2="210" y2="115" stroke="rgba(255,255,255,0.12)"/>

          {/* Text lines on top layer */}
          <line x1="108" y1="73" x2="172" y2="73" stroke="rgba(255,255,255,0.25)" strokeWidth="1.5"/>
          <line x1="100" y1="82" x2="165" y2="82" stroke="rgba(255,255,255,0.15)"/>
          <line x1="105" y1="91" x2="155" y2="91" stroke="rgba(255,255,255,0.12)"/>
          <line x1="108" y1="100" x2="160" y2="100" stroke="rgba(255,255,255,0.1)"/>

          {/* Scanning arc on top */}
          <circle cx="140" cy="80" r="28" stroke="rgba(229,72,77,0.25)" strokeDasharray="5 4" strokeWidth="1"/>
          <circle cx="140" cy="80" r="40" stroke="rgba(229,72,77,0.12)" strokeDasharray="5 6" strokeWidth="1"/>
        </g>
      </svg>
    ),
  },
  {
    id: "FIG 0.3",
    label: "Powered by AI agents",
    description: "Designed for workflows handled by humans and agents. From reading regulatory PDFs to generating Jira tickets.",
    svg: (
      <svg viewBox="0 0 280 260" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Isometric cubes representing 5 agents */}
        <g stroke="rgba(255,255,255,0.16)" strokeWidth="1" strokeLinejoin="round">
          {/* Cube 1 - top center (Scanner) */}
          <polygon points="140,62 175,82 140,102 105,82" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.22)"/>
          <polygon points="105,82 105,112 140,132 140,102" fill="rgba(255,255,255,0.02)"/>
          <polygon points="175,82 175,112 140,132 140,102" fill="rgba(255,255,255,0.015)"/>

          {/* Cube 2 - left (Extractor) */}
          <polygon points="90,118 125,138 90,158 55,138" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.18)"/>
          <polygon points="55,138 55,168 90,188 90,158" fill="rgba(255,255,255,0.02)"/>
          <polygon points="125,138 125,168 90,188 90,158" fill="rgba(255,255,255,0.015)"/>

          {/* Cube 3 - right (Impact Analyst) */}
          <polygon points="190,118 225,138 190,158 155,138" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.18)"/>
          <polygon points="155,138 155,168 190,188 190,158" fill="rgba(255,255,255,0.02)"/>
          <polygon points="225,138 225,168 190,188 190,158" fill="rgba(255,255,255,0.015)"/>

          {/* Cube 4 - bottom left (Planner) */}
          <polygon points="90,194 125,214 90,234 55,214" fill="rgba(255,255,255,0.035)" stroke="rgba(255,255,255,0.14)"/>
          <polygon points="55,214 55,234 90,254 90,234" fill="rgba(255,255,255,0.015)"/>
          <polygon points="125,214 125,234 90,254 90,234" fill="rgba(255,255,255,0.01)"/>

          {/* Cube 5 - bottom right (Validator) */}
          <polygon points="190,194 225,214 190,234 155,214" fill="rgba(255,255,255,0.035)" stroke="rgba(255,255,255,0.14)"/>
          <polygon points="155,214 155,234 190,254 190,234" fill="rgba(255,255,255,0.015)"/>
          <polygon points="225,214 225,234 190,254 190,234" fill="rgba(255,255,255,0.01)"/>

          {/* Connectors */}
          <line x1="110" y1="120" x2="127" y2="110" stroke="rgba(255,255,255,0.12)" strokeDasharray="3 3"/>
          <line x1="170" y1="120" x2="153" y2="110" stroke="rgba(255,255,255,0.12)" strokeDasharray="3 3"/>
          <line x1="90" y1="158" x2="90" y2="194" stroke="rgba(255,255,255,0.1)" strokeDasharray="3 3"/>
          <line x1="190" y1="158" x2="190" y2="194" stroke="rgba(255,255,255,0.1)" strokeDasharray="3 3"/>
        </g>
      </svg>
    ),
  },
  {
    id: "FIG 0.4",
    label: "Designed for action",
    description: "Reduces compliance noise and restores focus. Every output is a concrete task with an owner, deadline, and priority.",
    svg: (
      <svg viewBox="0 0 280 260" fill="none" xmlns="http://www.w3.org/2000/svg">
        {/* Stacked output cards, slight perspective fan */}
        <g stroke="rgba(255,255,255,0.12)" strokeLinejoin="round">
          {/* Card 4 - back */}
          <rect x="55" y="80" width="170" height="36" rx="4" fill="rgba(255,255,255,0.015)" stroke="rgba(255,255,255,0.08)"/>
          {/* Card 3 */}
          <rect x="52" y="122" width="176" height="36" rx="4" fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.10)"/>
          {/* Card 2 */}
          <rect x="49" y="164" width="182" height="36" rx="4" fill="rgba(255,255,255,0.025)" stroke="rgba(255,255,255,0.13)"/>
          {/* Card 1 - front */}
          <rect x="46" y="206" width="188" height="38" rx="4" fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.20)"/>

          {/* Content in front card */}
          <circle cx="68" cy="225" r="6" stroke="rgba(229,72,77,0.5)" fill="rgba(229,72,77,0.1)"/>
          <line x1="84" y1="221" x2="180" y2="221" stroke="rgba(255,255,255,0.25)" strokeWidth="1.4"/>
          <line x1="84" y1="229" x2="155" y2="229" stroke="rgba(255,255,255,0.12)"/>

          {/* Content in card 2 */}
          <circle cx="66" cy="182" r="5" stroke="rgba(245,158,11,0.4)" fill="rgba(245,158,11,0.08)"/>
          <line x1="80" y1="179" x2="185" y2="179" stroke="rgba(255,255,255,0.2)" strokeWidth="1.2"/>
          <line x1="80" y1="186" x2="165" y2="186" stroke="rgba(255,255,255,0.1)"/>

          {/* Content in card 3 */}
          <circle cx="69" cy="140" r="5" stroke="rgba(34,197,94,0.4)" fill="rgba(34,197,94,0.08)"/>
          <line x1="82" y1="137" x2="188" y2="137" stroke="rgba(255,255,255,0.16)" strokeWidth="1.2"/>
          <line x1="82" y1="144" x2="160" y2="144" stroke="rgba(255,255,255,0.08)"/>

          {/* Content in card 4 */}
          <circle cx="72" cy="98" r="4" stroke="rgba(139,92,246,0.4)" fill="rgba(139,92,246,0.08)"/>
          <line x1="84" y1="95" x2="190" y2="95" stroke="rgba(255,255,255,0.12)" strokeWidth="1"/>
          <line x1="84" y1="102" x2="168" y2="102" stroke="rgba(255,255,255,0.06)"/>

          {/* Arrow on front card */}
          <path d="M210 225 L222 225 M216 220 L222 225 L216 230" stroke="rgba(255,255,255,0.2)" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
        </g>
      </svg>
    ),
  },
];

export default function Statement() {
  return (
    <section className="spotlight" style={{ padding: "112px 0 96px", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>

        {/* Big headline - white fades to gray */}
        <h2 style={{
          fontSize: "clamp(2.2rem, 5vw, 4rem)",
          fontWeight: 700,
          letterSpacing: "-0.04em",
          lineHeight: 1.08,
          marginBottom: 80,
          maxWidth: 900,
        }}>
          <span style={{ color: "#fff" }}>A new species of compliance tool. </span>
          <span style={{ color: "#333" }}>Purpose-built for modern teams with AI workflows at its core, Red Forge sets a new standard for regulatory intelligence.</span>
        </h2>

        {/* Three figure cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 1, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, overflow: "hidden" }}>
          {figs.map((fig) => (
            <div key={fig.id} style={{ background: "#0A0A0A", padding: "0 0 32px", display: "flex", flexDirection: "column" }}>
              {/* Fig label */}
              <div style={{ padding: "20px 24px 0", marginBottom: 8 }}>
                <span style={{ fontSize: 11, color: "#333", fontFamily: "monospace", letterSpacing: "0.08em" }}>{fig.id}</span>
              </div>

              {/* Illustration */}
              <div style={{ padding: "0 16px", flex: 1, display: "flex", alignItems: "center", justifyContent: "center", minHeight: 240 }}>
                {fig.svg}
              </div>

              {/* Text */}
              <div style={{ padding: "0 24px" }}>
                <p style={{ fontSize: 14, fontWeight: 600, color: "#ddd", marginBottom: 6, letterSpacing: "-0.01em" }}>{fig.label}</p>
                <p style={{ fontSize: 13, color: "#444", lineHeight: 1.6 }}>{fig.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
