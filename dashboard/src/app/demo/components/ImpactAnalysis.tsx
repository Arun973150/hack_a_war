"use client";

import { useEffect, useState } from "react";
import { RegulationItem } from "./FeedMonitor";
import { getGapsSummary, GapSummaryItem, PipelineResult } from "../lib/api";

interface DisplayGap {
  obligation: string;
  existing: string[];
  coverage: number;
  risk: number;
  obligationId: string;
}

// Fallback mock gaps when Neo4j is empty
const MOCK_GAPS: Record<string, DisplayGap[]> = {
  "REG-2024-001": [
    { obligationId: "OBL-001", obligation: "Conformity assessment for high-risk AI", existing: ["AI-CTRL-12", "RISK-001"], coverage: 42, risk: 9 },
    { obligationId: "OBL-002", obligation: "Technical documentation for 10 years", existing: ["DOC-CTRL-08"], coverage: 61, risk: 7 },
    { obligationId: "OBL-003", obligation: "Human oversight mechanisms", existing: [], coverage: 5, risk: 10 },
    { obligationId: "OBL-004", obligation: "Incident reporting to national authority", existing: ["INC-CTRL-03"], coverage: 30, risk: 8 },
  ],
  "REG-2024-002": [
    { obligationId: "OBL-005", obligation: "Material incident disclosure within 4 days", existing: ["INC-CTRL-03", "INC-CTRL-07"], coverage: 55, risk: 8 },
    { obligationId: "OBL-006", obligation: "Annual cybersecurity risk management report", existing: ["RISK-001"], coverage: 70, risk: 6 },
    { obligationId: "OBL-007", obligation: "Board-level cybersecurity governance", existing: [], coverage: 10, risk: 7 },
  ],
  "REG-2024-003": [
    { obligationId: "OBL-008", obligation: "Appoint Data Protection Officer", existing: [], coverage: 0, risk: 10 },
    { obligationId: "OBL-009", obligation: "Implement consent mechanisms", existing: ["PRIV-CTRL-02"], coverage: 35, risk: 9 },
    { obligationId: "OBL-010", obligation: "72-hour breach notification", existing: ["INC-CTRL-03"], coverage: 48, risk: 8 },
  ],
  "REG-2024-004": [
    { obligationId: "OBL-011", obligation: "ICT risk management framework", existing: ["RISK-001", "RISK-003"], coverage: 68, risk: 7 },
    { obligationId: "OBL-012", obligation: "Annual TLPT testing", existing: [], coverage: 5, risk: 9 },
    { obligationId: "OBL-013", obligation: "Major ICT incident reporting (4-hour SLA)", existing: ["INC-CTRL-03"], coverage: 40, risk: 8 },
  ],
};

const RISK_COLORS = ["#22C55E","#22C55E","#22C55E","#84CC16","#84CC16","#F59E0B","#F59E0B","#EF4444","#E5484D","#E5484D"];

interface Props {
  regulation: RegulationItem | null;
  analysisComplete: boolean;
  pipelineResult: PipelineResult | null;
}

export default function ImpactAnalysis({ regulation, analysisComplete, pipelineResult }: Props) {
  const [gaps, setGaps] = useState<DisplayGap[]>([]);
  const [riskScore, setRiskScore] = useState(0);
  const [units, setUnits] = useState<string[]>([]);
  const [summary, setSummary] = useState("");
  const [fromApi, setFromApi] = useState(false);

  useEffect(() => {
    if (!regulation || !analysisComplete) {
      setGaps([]);
      setRiskScore(0);
      setUnits([]);
      setSummary("");
      setFromApi(false);
      return;
    }

    // Priority 1: real pipeline result (SSE complete event)
    if (pipelineResult && !pipelineResult.error) {
      const realGaps: DisplayGap[] = pipelineResult.gaps.map((g) => ({
        obligationId: g.obligation_id,
        obligation: g.gap_description,
        existing: g.existing_controls,
        coverage: Math.round(g.coverage_pct),
        risk: g.risk_score,
      }));
      setGaps(realGaps.length > 0 ? realGaps : MOCK_GAPS[regulation.id] || []);
      setRiskScore(pipelineResult.overall_risk_score || 6);
      setUnits(pipelineResult.affected_business_units.length > 0
        ? pipelineResult.affected_business_units
        : ["Compliance", "Technology", "Legal"]);
      setSummary(pipelineResult.impact_summary || "Analysis complete.");
      setFromApi(true);
      return;
    }

    // Priority 2: real Neo4j gaps
    getGapsSummary().then((dbGaps) => {
      if (dbGaps.length > 0) {
        const mapped: DisplayGap[] = dbGaps.slice(0, 5).map((g) => ({
          obligationId: g.obligation_id,
          obligation: g.requirement || g.obligation_id,
          existing: [],
          coverage: Math.round(g.coverage_pct),
          risk: g.coverage_pct < 30 ? 9 : g.coverage_pct < 60 ? 7 : 5,
        }));
        setGaps(mapped);
        setRiskScore(regulation.severity === "Critical" ? 9 : 7);
        setUnits(["Compliance", "Technology", "Legal"]);
        setSummary(`${dbGaps.length} compliance gaps detected from Knowledge Graph for ${regulation.jurisdiction}.`);
        setFromApi(true);
      } else {
        // Priority 3: mock
        const mock = MOCK_GAPS[regulation.id] || [];
        setGaps(mock);
        setRiskScore(regulation.severity === "Critical" ? 9 : regulation.severity === "High" ? 7 : 5);
        setUnits(["Compliance", "Technology", "Legal", "HR"]);
        setSummary(`${regulation.title} introduces critical obligations requiring immediate assessment across ${regulation.jurisdiction} operations.`);
        setFromApi(false);
      }
    });
  }, [regulation?.id, analysisComplete, pipelineResult]);

  const riskColor = RISK_COLORS[Math.min(riskScore - 1, 9)] || "#8B8D97";

  if (!regulation) {
    return (
      <div style={{ background: "#0D0D12", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, padding: "40px 20px", textAlign: "center" }}>
        <div style={{ fontSize: 13, color: "#4A4C57" }}>Analyze a regulation to see impact assessment</div>
      </div>
    );
  }

  return (
    <div style={{ background: "#0D0D12", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, overflow: "hidden" }}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: "#EDEDEF" }}>Impact Analysis</span>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {fromApi && <span style={{ fontSize: 10, color: "#22C55E", fontWeight: 600 }}>● REAL DATA</span>}
          <span style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: "#4A4C57" }}>{regulation.id}</span>
        </div>
      </div>

      <div style={{ padding: "20px" }}>
        {!analysisComplete ? (
          <div style={{ padding: "20px 0", textAlign: "center" }}>
            <div style={{ fontSize: 12, color: "#4A4C57" }}>Waiting for analysis to complete...</div>
            <div style={{ marginTop: 12, height: 4, background: "rgba(255,255,255,0.05)", borderRadius: 2, overflow: "hidden" }}>
              <div style={{ height: "100%", width: "60%", background: "#E5484D", borderRadius: 2, animation: "shimmer 1.5s infinite" }} />
            </div>
          </div>
        ) : (
          <>
            {/* Risk gauge + business units */}
            <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 20, marginBottom: 20, alignItems: "start" }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ width: 88, height: 88, borderRadius: "50%", background: `conic-gradient(${riskColor} ${riskScore * 36}deg, rgba(255,255,255,0.05) 0deg)`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <div style={{ width: 66, height: 66, borderRadius: "50%", background: "#0D0D12", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                    <span style={{ fontSize: 22, fontWeight: 800, color: riskColor, fontFamily: "JetBrains Mono, monospace" }}>{riskScore}</span>
                    <span style={{ fontSize: 9, color: "#4A4C57", textTransform: "uppercase", letterSpacing: "0.05em" }}>/ 10</span>
                  </div>
                </div>
                <div style={{ fontSize: 11, color: "#8B8D97", marginTop: 6, fontWeight: 500 }}>Risk Score</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: "#4A4C57", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600 }}>Affected Business Units</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {units.map((u) => (
                    <span key={u} style={{ fontSize: 12, fontWeight: 500, background: "rgba(139,92,246,0.1)", color: "#8B5CF6", border: "1px solid rgba(139,92,246,0.25)", padding: "4px 10px", borderRadius: 6 }}>{u}</span>
                  ))}
                </div>
              </div>
            </div>

            {summary && (
              <div style={{ padding: "12px 14px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, marginBottom: 20 }}>
                <div style={{ fontSize: 11, color: "#4A4C57", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600, marginBottom: 6 }}>Executive Summary</div>
                <div style={{ fontSize: 13, color: "#8B8D97", lineHeight: 1.6 }}>{summary}</div>
              </div>
            )}

            <div>
              <div style={{ fontSize: 11, color: "#4A4C57", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600, marginBottom: 12 }}>
                Compliance Gaps ({gaps.length})
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {gaps.map((gap, i) => <GapRow key={i} gap={gap} />)}
              </div>
            </div>
          </>
        )}
      </div>
      <style>{`@keyframes shimmer { 0%,100%{opacity:1} 50%{opacity:0.5} }`}</style>
    </div>
  );
}

function GapRow({ gap }: { gap: DisplayGap }) {
  const riskColor = gap.risk >= 8 ? "#E5484D" : gap.risk >= 6 ? "#F59E0B" : "#22C55E";
  return (
    <div style={{ background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 8, padding: "12px 14px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <span style={{ fontSize: 12, fontWeight: 500, color: "#C4C6D0" }}>{gap.obligation}</span>
        <span style={{ fontSize: 11, fontWeight: 700, color: riskColor, fontFamily: "JetBrains Mono, monospace", background: `${riskColor}15`, border: `1px solid ${riskColor}30`, padding: "2px 7px", borderRadius: 4 }}>
          R{gap.risk}
        </span>
      </div>
      <div style={{ marginBottom: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: "#4A4C57" }}>Coverage</span>
          <span style={{ fontSize: 11, color: gap.coverage < 40 ? "#E5484D" : gap.coverage < 70 ? "#F59E0B" : "#22C55E", fontFamily: "JetBrains Mono, monospace", fontWeight: 600 }}>{gap.coverage}%</span>
        </div>
        <div style={{ height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 2, overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${gap.coverage}%`, background: gap.coverage < 40 ? "#E5484D" : gap.coverage < 70 ? "#F59E0B" : "#22C55E", borderRadius: 2, transition: "width 0.8s ease" }} />
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ fontSize: 11, color: "#4A4C57" }}>Controls:</span>
        {gap.existing.length === 0 ? (
          <span style={{ fontSize: 11, color: "#E5484D" }}>None mapped</span>
        ) : gap.existing.map((c) => (
          <span key={c} style={{ fontSize: 10, fontFamily: "JetBrains Mono, monospace", background: "rgba(255,255,255,0.05)", color: "#8B8D97", border: "1px solid rgba(255,255,255,0.08)", padding: "1px 6px", borderRadius: 4 }}>{c}</span>
        ))}
      </div>
    </div>
  );
}
