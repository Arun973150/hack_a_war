const quotes = [
  {
    body: "We went from monthly manual regulatory review cycles to hourly automated monitoring. The action items come out in a format our team can actually use — not a 40-page PDF.",
    name: "Head of Compliance",
    role: "Series C Fintech",
  },
  {
    body: "The knowledge graph alone is worth it. Being able to ask which controls address a DORA obligation and get an answer in seconds changed how we do pre-audit prep.",
    name: "GRC Lead",
    role: "Enterprise SaaS",
  },
  {
    body: "Our legal team was skeptical of AI-generated analysis. The hallucination validator was the thing that got them over the line — every claim traces to the source text.",
    name: "VP Legal & Compliance",
    role: "Healthtech scale-up",
  },
];

export default function SocialProof() {
  return (
    <section style={{ padding: "96px 0", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>
        <p style={{ fontSize: 12, color: "#333", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 500, marginBottom: 40 }}>
          From teams using Red Forge
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
          {quotes.map((q, i) => (
            <div key={i} style={{
              padding: "24px",
              border: "1px solid rgba(255,255,255,0.07)",
              borderRadius: 10,
              background: "#0D0D0D",
              display: "flex", flexDirection: "column", gap: 20,
            }}>
              <p style={{ fontSize: 14, color: "#777", lineHeight: 1.7, flex: 1 }}>{q.body}</p>
              <div style={{ display: "flex", alignItems: "center", gap: 10, borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 16 }}>
                <div style={{ width: 28, height: 28, borderRadius: "50%", background: "#1A1A1A", border: "1px solid rgba(255,255,255,0.08)" }} />
                <div>
                  <p style={{ fontSize: 12, fontWeight: 600, color: "#ddd" }}>{q.name}</p>
                  <p style={{ fontSize: 11, color: "#444" }}>{q.role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
