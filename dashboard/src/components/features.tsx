"use client";

const features = [
  {
    title: "Real-time regulatory radar",
    description: "Connects to Federal Register, EUR-Lex, SEBI, RBI, and more. New documents are fetched hourly, parsed, and queued for analysis — no manual checking required.",
    tag: "Ingestion · Layer 1",
  },
  {
    title: "Structured obligation extraction",
    description: "Every clause is analyzed to pull out WHO must do WHAT, by WHEN, under what CONDITIONS, with what PENALTY. Output is structured — not a summary.",
    tag: "Agent 2 · Gemini Flash",
  },
  {
    title: "Gap analysis against your controls",
    description: "Cross-references every obligation against your control library using dual-channel RAG: Qdrant for semantic similarity and Neo4j for graph traversal.",
    tag: "Agent 3 · Gemini 2.5 Pro",
  },
  {
    title: "Prioritized action planning",
    description: "Every gap becomes a concrete action item with owner, deadline, effort estimate, and risk score. Sorted by impact. One click to Jira.",
    tag: "Agent 4 · Gemini Flash",
  },
  {
    title: "Regulatory knowledge graph",
    description: "All regulations, obligations, and controls live as a connected graph in Neo4j. Ask in plain English — the system generates Cypher and answers instantly.",
    tag: "Neo4j · LangChain",
  },
  {
    title: "Hallucination-checked outputs",
    description: "A fifth validator agent cross-checks every extracted obligation against the original source text. Nothing ships unless it's grounded in the document.",
    tag: "Agent 5 · Self-correcting",
  },
];

export default function Features() {
  return (
    <section id="features" style={{ padding: "96px 0" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>

        {/* Header */}
        <div style={{ marginBottom: 56 }}>
          <h2 style={{ fontSize: "clamp(2rem,4vw,3rem)", fontWeight: 700, letterSpacing: "-0.035em", lineHeight: 1.1, color: "#fff", marginBottom: 16, maxWidth: 600 }}>
            Not a dashboard.
            <br /><span style={{ color: "#444" }}>An agent.</span>
          </h2>
          <p style={{ fontSize: 15, color: "#555", maxWidth: 480, lineHeight: 1.6 }}>
            Documents go in one end, prioritized action items come out the other.
            Your team just executes.
          </p>
        </div>

        {/* Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 1, background: "rgba(255,255,255,0.07)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, overflow: "hidden" }}>
          {features.map((f) => (
            <div key={f.title} style={{ background: "#0A0A0A", padding: "28px 24px", display: "flex", flexDirection: "column", gap: 12, transition: "background .15s", cursor: "default" }}
              onMouseEnter={e => (e.currentTarget.style.background = "#111")}
              onMouseLeave={e => (e.currentTarget.style.background = "#0A0A0A")}
            >
              <h3 style={{ fontSize: 14, fontWeight: 600, color: "#ddd", letterSpacing: "-0.01em", lineHeight: 1.3 }}>{f.title}</h3>
              <p style={{ fontSize: 13, color: "#555", lineHeight: 1.65, flex: 1 }}>{f.description}</p>
              <span style={{ fontSize: 11, color: "#333", fontFamily: "monospace", borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 10, marginTop: 4 }}>
                {f.tag}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
