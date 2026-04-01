"use client";

import { useState, useEffect } from "react";
import { getConflicts } from "../lib/api";

interface Conflict {
  id: string;
  title: string;
  severity: "Critical" | "High" | "Medium";
  left: { jurisdiction: string; regulation: string; requirement: string; color: string };
  right: { jurisdiction: string; regulation: string; requirement: string; color: string };
  description: string;
  recommendation: string;
}

const CONFLICTS: Conflict[] = [
  {
    id: "CNFL-001",
    title: "Data Retention vs Right to Erasure",
    severity: "Critical",
    left: {
      jurisdiction: "US",
      regulation: "SEC Rule 17a-4",
      requirement: "Retain all business communications for minimum 7 years. Immutable storage required. Deletion is prohibited.",
      color: "#3B82F6",
    },
    right: {
      jurisdiction: "EU",
      regulation: "GDPR Art. 17",
      requirement: "Data subjects have the right to erasure. Controller must delete personal data upon request without undue delay.",
      color: "#6366F1",
    },
    description: "US SEC rules mandate 7-year immutable retention of communications while EU GDPR grants users the absolute right to erasure — these are directly irreconcilable for EU citizen data.",
    recommendation: "Implement jurisdiction-aware data segmentation. Apply pseudonymization for EU data to satisfy erasure requests without violating US retention obligations.",
  },
  {
    id: "CNFL-002",
    title: "AI System Oversight Requirements",
    severity: "High",
    left: {
      jurisdiction: "EU",
      regulation: "EU AI Act Art. 14",
      requirement: "High-risk AI systems must allow human oversight and intervention at all times. Full auditability required.",
      color: "#6366F1",
    },
    right: {
      jurisdiction: "India",
      regulation: "SEBI CSCRF 2024",
      requirement: "Automated risk management systems must operate continuously with minimal human delay. Real-time response mandated.",
      color: "#F59E0B",
    },
    description: "EU AI Act requires human-in-the-loop for high-risk AI decisions, while SEBI requires automated real-time response in capital markets — creating a conflict for AI-driven trading systems.",
    recommendation: "Deploy tiered human oversight: human approval for high-value decisions (>₹10L), automated response for low-risk with comprehensive logging for SEBI audit trails.",
  },
  {
    id: "CNFL-003",
    title: "Breach Notification Timelines",
    severity: "High",
    left: {
      jurisdiction: "India",
      regulation: "DPDP Act 2023",
      requirement: "Report personal data breaches to Data Protection Board within 72 hours of becoming aware.",
      color: "#F59E0B",
    },
    right: {
      jurisdiction: "US",
      regulation: "SEC Cybersecurity Rules",
      requirement: "Disclose material cybersecurity incidents in Form 8-K within 4 business days of determining materiality.",
      color: "#3B82F6",
    },
    description: "DPDP requires 72-hour reporting from awareness while SEC requires 4 business days from materiality determination — 'materiality' assessment could extend effective window beyond DPDP deadline.",
    recommendation: "Adopt the most stringent timeline (72 hours) as universal SLA. Use parallel notification workflows with jurisdiction-specific templates triggered simultaneously.",
  },
];

const SEV_COLORS = {
  Critical: { bg: "rgba(229,72,77,0.1)", text: "#E5484D", border: "rgba(229,72,77,0.3)" },
  High: { bg: "rgba(245,158,11,0.1)", text: "#F59E0B", border: "rgba(245,158,11,0.3)" },
  Medium: { bg: "rgba(139,92,246,0.1)", text: "#8B5CF6", border: "rgba(139,92,246,0.3)" },
};

export default function ConflictDetection() {
  const [selected, setSelected] = useState<string>(CONFLICTS[0].id);
  const [liveCount, setLiveCount] = useState<number | null>(null);
  const [fromGraph, setFromGraph] = useState(false);

  useEffect(() => {
    getConflicts().then((data) => {
      if (data && data.total > 0) {
        setLiveCount(data.total);
        setFromGraph(!!data.from_graph);
      }
    });
  }, []);

  const conflict = CONFLICTS.find((c) => c.id === selected) || CONFLICTS[0];
  const sev = SEV_COLORS[conflict.severity];

  return (
    <div style={{
      background: "#0D0D12",
      border: "1px solid rgba(255,255,255,0.07)",
      borderRadius: 12,
      overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        padding: "16px 20px",
        borderBottom: "1px solid rgba(255,255,255,0.07)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 20, height: 20, borderRadius: 4, background: "rgba(245,158,11,0.15)", border: "1px solid rgba(245,158,11,0.3)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "#F59E0B" }}>!</div>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#EDEDEF" }}>Cross-Jurisdiction Conflicts</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {fromGraph && <span style={{ fontSize: 10, color: "#22C55E", fontWeight: 600 }}>● Neo4j</span>}
          <span style={{
            fontSize: 11, fontWeight: 700,
            background: "rgba(229,72,77,0.1)", color: "#E5484D",
            border: "1px solid rgba(229,72,77,0.25)",
            padding: "2px 8px", borderRadius: 20,
          }}>
            {liveCount ?? CONFLICTS.length} detected
          </span>
        </div>
      </div>

      <div style={{ padding: "20px" }}>
        {/* Conflict selector */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 20 }}>
          {CONFLICTS.map((c) => {
            const cs = SEV_COLORS[c.severity];
            const active = c.id === selected;
            return (
              <button
                key={c.id}
                onClick={() => setSelected(c.id)}
                style={{
                  display: "flex", alignItems: "center", gap: 10,
                  padding: "8px 12px", borderRadius: 8, cursor: "pointer",
                  background: active ? "rgba(229,72,77,0.06)" : "rgba(255,255,255,0.02)",
                  border: active ? "1px solid rgba(229,72,77,0.3)" : "1px solid rgba(255,255,255,0.06)",
                  textAlign: "left", outline: "none", transition: "all .15s ease",
                }}
              >
                <div style={{
                  width: 6, height: 6, borderRadius: "50%",
                  background: cs.text, flexShrink: 0,
                }} />
                <span style={{ fontSize: 12, fontWeight: 500, color: active ? "#EDEDEF" : "#8B8D97", flex: 1 }}>
                  {c.title}
                </span>
                <span style={{
                  fontSize: 10, fontWeight: 700,
                  background: cs.bg, color: cs.text, border: `1px solid ${cs.border}`,
                  padding: "1px 6px", borderRadius: 4,
                }}>
                  {c.severity}
                </span>
              </button>
            );
          })}
        </div>

        {/* Side-by-side comparison */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", gap: 12, alignItems: "stretch", marginBottom: 16 }}>
          <JurisdictionCard
            jurisdiction={conflict.left.jurisdiction}
            regulation={conflict.left.regulation}
            requirement={conflict.left.requirement}
            color={conflict.left.color}
          />

          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <div style={{
              width: 32, height: 32, borderRadius: "50%",
              background: sev.bg, border: `1px solid ${sev.border}`,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 11, color: sev.text, fontWeight: 700,
            }}>
              VS
            </div>
          </div>

          <JurisdictionCard
            jurisdiction={conflict.right.jurisdiction}
            regulation={conflict.right.regulation}
            requirement={conflict.right.requirement}
            color={conflict.right.color}
          />
        </div>

        {/* Description */}
        <div style={{
          padding: "12px 14px",
          background: `${sev.bg}`,
          border: `1px solid ${sev.border}`,
          borderRadius: 8,
          marginBottom: 12,
        }}>
          <div style={{ fontSize: 11, color: sev.text, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>
            Conflict Analysis
          </div>
          <div style={{ fontSize: 12, color: "#8B8D97", lineHeight: 1.6 }}>{conflict.description}</div>
        </div>

        {/* Recommendation */}
        <div style={{
          padding: "12px 14px",
          background: "rgba(34,197,94,0.05)",
          border: "1px solid rgba(34,197,94,0.2)",
          borderRadius: 8,
        }}>
          <div style={{ fontSize: 11, color: "#22C55E", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>
            Recommended Resolution
          </div>
          <div style={{ fontSize: 12, color: "#8B8D97", lineHeight: 1.6 }}>{conflict.recommendation}</div>
        </div>
      </div>
    </div>
  );
}

function JurisdictionCard({
  jurisdiction, regulation, requirement, color,
}: {
  jurisdiction: string;
  regulation: string;
  requirement: string;
  color: string;
}) {
  return (
    <div style={{
      background: `${color}08`,
      border: `1px solid ${color}25`,
      borderRadius: 8,
      padding: "12px 14px",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
        <div style={{ width: 3, height: 32, background: color, borderRadius: 2, flexShrink: 0 }} />
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color, textTransform: "uppercase", letterSpacing: "0.04em" }}>
            {jurisdiction}
          </div>
          <div style={{ fontSize: 11, color: "#8B8D97", fontWeight: 500 }}>{regulation}</div>
        </div>
      </div>
      <div style={{ fontSize: 12, color: "#8B8D97", lineHeight: 1.6 }}>{requirement}</div>
    </div>
  );
}
