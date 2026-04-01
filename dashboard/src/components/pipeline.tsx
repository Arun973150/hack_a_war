const steps = [
  {
    n: "01",
    title: "Document fetched",
    sub: "Ingestion layer",
    body: "Prefect workers pull new filings from Federal Register, EUR-Lex, SEBI, and RBI hourly. PDFs, HTML, and APIs — all handled. Raw bytes go to Supabase storage, text is chunked for analysis.",
    detail: "Docling · pdfplumber · Tesseract · Prefect",
  },
  {
    n: "02",
    title: "Scanner decides relevance",
    sub: "Agent 1 · Gemini 2.0 Flash-Lite",
    body: "A fast triage agent reads the document and classifies it — jurisdiction, sector, document type, and a relevance score against your org profile. Irrelevant documents are filtered out here.",
    detail: "< 2s per document · 0.1¢ average cost",
  },
  {
    n: "03",
    title: "Obligations extracted",
    sub: "Agent 2 · Gemini 2.0 Flash",
    body: "Long documents are split into clause-aware chunks. Each chunk is analyzed to extract WHO / WHAT / WHEN / CONDITIONS / PENALTY. Output is structured JSON with source citations.",
    detail: "Chunk-parallel · Citation-grounded",
  },
  {
    n: "04",
    title: "Gaps identified against your controls",
    sub: "Agent 3 · Gemini 2.5 Pro",
    body: "Uses Qdrant for semantic search across similar past regulations, and Neo4j for knowledge graph traversal. Finds every gap between new obligations and your existing control library.",
    detail: "Dual-channel RAG · KG traversal",
  },
  {
    n: "05",
    title: "Action plan generated & validated",
    sub: "Agents 4 + 5 · Gemini 2.0 Flash",
    body: "Agent 4 generates prioritized action items with owners, deadlines, and effort estimates. Agent 5 cross-checks every obligation claim against the original document — nothing ships unverified.",
    detail: "Self-correcting loop · Jira-ready output",
  },
];

export default function Pipeline() {
  return (
    <section id="pipeline" style={{ padding: "96px 0", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>

        {/* Header */}
        <div style={{ marginBottom: 56 }}>
          <h2 style={{ fontSize: "clamp(2rem,4vw,3rem)", fontWeight: 700, letterSpacing: "-0.035em", lineHeight: 1.1, color: "#fff", marginBottom: 16, maxWidth: 560 }}>
            Five agents.
            <br /><span style={{ color: "#444" }}>One decision.</span>
          </h2>
          <p style={{ fontSize: 15, color: "#555", maxWidth: 460, lineHeight: 1.6 }}>
            Every regulatory document runs through a deterministic graph of specialized agents.
            Each has one job. Together they replace weeks of manual review.
          </p>
        </div>

        {/* Steps */}
        <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {steps.map((step, i) => (
            <div key={step.n} style={{
              display: "flex", gap: 0,
              border: "1px solid rgba(255,255,255,0.07)",
              borderRadius: i === 0 ? "10px 10px 0 0" : i === steps.length-1 ? "0 0 10px 10px" : 0,
              marginTop: i > 0 ? -1 : 0,
              background: "#0D0D0D",
              overflow: "hidden",
            }}>
              {/* Number */}
              <div style={{
                width: 56, flexShrink: 0, display: "flex", alignItems: "flex-start", justifyContent: "center",
                paddingTop: 24, paddingBottom: 24,
                borderRight: "1px solid rgba(255,255,255,0.07)",
                background: "#0A0A0A",
              }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: "#333", fontFamily: "monospace" }}>{step.n}</span>
              </div>

              {/* Content */}
              <div style={{ padding: "22px 24px 22px", flex: 1 }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 8, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 14, fontWeight: 600, color: "#ddd" }}>{step.title}</span>
                  <span style={{ fontSize: 12, color: "#444", fontFamily: "monospace" }}>{step.sub}</span>
                </div>
                <p style={{ fontSize: 13, color: "#555", lineHeight: 1.65, marginBottom: 10 }}>{step.body}</p>
                <span style={{ fontSize: 11, color: "#333", fontFamily: "monospace" }}>{step.detail}</span>
              </div>
            </div>
          ))}
        </div>

        {/* LangGraph note */}
        <div style={{
          marginTop: 16, padding: "18px 20px", borderRadius: 10,
          border: "1px solid rgba(255,255,255,0.07)", background: "#0D0D0D",
          display: "flex", gap: 14, alignItems: "flex-start",
        }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8, flexShrink: 0,
            border: "1px solid rgba(139,92,246,0.2)", background: "rgba(139,92,246,0.08)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="3" cy="7" r="2" stroke="#8B5CF6" strokeWidth="1.2"/>
              <circle cx="11" cy="3" r="2" stroke="#8B5CF6" strokeWidth="1.2"/>
              <circle cx="11" cy="11" r="2" stroke="#8B5CF6" strokeWidth="1.2"/>
              <path d="M5 7h2M9 4.5L6 6.5M9 9.5L6 7.5" stroke="#8B5CF6" strokeWidth="1" strokeLinecap="round"/>
            </svg>
          </div>
          <div>
            <p style={{ fontSize: 13, fontWeight: 600, color: "#ddd", marginBottom: 4 }}>Built on LangGraph + LangChain</p>
            <p style={{ fontSize: 13, color: "#555", lineHeight: 1.6 }}>
              The agent graph uses LangGraph StateGraph with conditional routing — if Agent 5 flags a hallucination,
              the pipeline loops back to Agent 2 for re-extraction. Self-correcting, not just self-reporting.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
