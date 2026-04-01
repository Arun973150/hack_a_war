"use client";

import { useEffect, useState } from "react";
import { getComplianceDrift, DriftData } from "../lib/api";

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

const FALLBACK: Record<string, number[]> = {
  All: [71,68,70,67,64,62,65,63,59,57,54,51],
  US: [78,76,79,77,75,73,76,74,71,69,67,64],
  EU: [65,62,63,60,57,55,57,54,51,48,45,42],
  India: [70,68,69,65,61,58,62,59,55,54,50,47],
};

const EVENTS = [
  { month: 3, label: "EU AI Act published", jurisdiction: "EU" },
  { month: 6, label: "DORA in force", jurisdiction: "EU" },
  { month: 8, label: "DPDP notified", jurisdiction: "India" },
  { month: 9, label: "SEC rules effective", jurisdiction: "US" },
];

interface Props { jurisdiction: string }

export default function DriftScore({ jurisdiction }: Props) {
  const [data, setData] = useState<number[]>(FALLBACK[jurisdiction] || FALLBACK.All);
  const [meta, setMeta] = useState<{ total: number; high: number } | null>(null);
  const [fromApi, setFromApi] = useState(false);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  useEffect(() => {
    getComplianceDrift(jurisdiction !== "All" ? jurisdiction : undefined).then((result) => {
      if (result && result.months && result.months.length === 12) {
        setData(result.months);
        setMeta({ total: result.total_controls, high: result.high_coverage_controls });
        setFromApi(true);
      } else {
        setData(FALLBACK[jurisdiction] || FALLBACK.All);
        setFromApi(false);
        setMeta(null);
      }
    });
  }, [jurisdiction]);

  const W = 520; const H = 160;
  const PAD = { top: 20, right: 20, bottom: 28, left: 36 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;
  const minVal = 30; const maxVal = 90;

  const pts = data.map((v, i) => ({
    x: PAD.left + (i / (data.length - 1)) * chartW,
    y: PAD.top + chartH - ((v - minVal) / (maxVal - minVal)) * chartH,
    v,
  }));

  const pathD = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  const areaD = `${pathD} L ${pts[pts.length-1].x} ${H-PAD.bottom} L ${pts[0].x} ${H-PAD.bottom} Z`;

  const current = data[data.length - 1];
  const delta = Math.round((current - data[0]) * 10) / 10;
  const deltaColor = delta >= 0 ? "#22C55E" : "#E5484D";
  const relevantEvents = EVENTS.filter((e) => jurisdiction === "All" || e.jurisdiction === jurisdiction);

  return (
    <div style={{ background: "#0D0D12", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, overflow: "hidden" }}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#EDEDEF" }}>Compliance Drift Score</span>
          {fromApi && <span style={{ fontSize: 10, color: "#22C55E", fontWeight: 600 }}>● Neo4j</span>}
          <span style={{ fontSize: 11, color: "#4A4C57" }}>12-month trend</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 22, fontWeight: 800, fontFamily: "JetBrains Mono, monospace", color: current >= 70 ? "#22C55E" : current >= 55 ? "#F59E0B" : "#E5484D" }}>{current}%</span>
          <span style={{ fontSize: 11, fontWeight: 600, color: deltaColor, fontFamily: "JetBrains Mono, monospace" }}>{delta >= 0 ? "+" : ""}{delta}%</span>
        </div>
      </div>

      <div style={{ padding: "20px" }}>
        <div style={{ position: "relative" }}>
          <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet">
            <defs>
              <linearGradient id="driftGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#E5484D" stopOpacity="0.15" />
                <stop offset="100%" stopColor="#E5484D" stopOpacity="0" />
              </linearGradient>
            </defs>
            {[40,50,60,70,80].map((val) => {
              const y = PAD.top + chartH - ((val - minVal) / (maxVal - minVal)) * chartH;
              return (
                <g key={val}>
                  <line x1={PAD.left} y1={y} x2={W-PAD.right} y2={y} stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
                  <text x={PAD.left-6} y={y+4} textAnchor="end" fontSize="9" fill="#4A4C57" fontFamily="JetBrains Mono, monospace">{val}</text>
                </g>
              );
            })}
            <path d={areaD} fill="url(#driftGrad)" />
            <path d={pathD} fill="none" stroke="#E5484D" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            {relevantEvents.map((ev) => {
              const pt = pts[ev.month];
              if (!pt) return null;
              return (
                <g key={ev.label}>
                  <line x1={pt.x} y1={PAD.top} x2={pt.x} y2={H-PAD.bottom} stroke="rgba(245,158,11,0.3)" strokeWidth="1" strokeDasharray="3,3" />
                  <circle cx={pt.x} cy={pt.y} r="4" fill="#F59E0B" opacity="0.8" />
                </g>
              );
            })}
            {pts.map((pt, i) => (
              <circle key={i} cx={pt.x} cy={pt.y} r="3"
                fill={hoveredIdx === i ? "#E5484D" : "#0D0D12"}
                stroke={hoveredIdx === i ? "#E5484D" : "rgba(229,72,77,0.4)"}
                strokeWidth="1.5" style={{ cursor: "pointer" }}
                onMouseEnter={() => setHoveredIdx(i)}
                onMouseLeave={() => setHoveredIdx(null)}
              />
            ))}
            {hoveredIdx !== null && (() => {
              const pt = pts[hoveredIdx];
              const tx = hoveredIdx > 8 ? pt.x - 40 : pt.x + 8;
              return (
                <g>
                  <rect x={tx} y={pt.y-22} width={48} height={18} rx="4" fill="#121218" stroke="rgba(255,255,255,0.1)" />
                  <text x={tx+24} y={pt.y-10} textAnchor="middle" fontSize="10" fill="#EDEDEF" fontFamily="JetBrains Mono, monospace" fontWeight="600">{pt.v}%</text>
                </g>
              );
            })()}
            {pts.map((pt, i) => (
              <text key={i} x={pt.x} y={H-4} textAnchor="middle" fontSize="9" fill={hoveredIdx === i ? "#EDEDEF" : "#4A4C57"} fontFamily="JetBrains Mono, monospace">{MONTHS[i]}</text>
            ))}
          </svg>
        </div>

        {relevantEvents.length > 0 && (
          <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 8 }}>
            {relevantEvents.map((ev) => (
              <div key={ev.label} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#F59E0B" }} />
                <span style={{ fontSize: 11, color: "#4A4C57" }}>{ev.label}</span>
              </div>
            ))}
          </div>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 16, paddingTop: 16, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <StatCell label="Current" value={`${current}%`} sub={current >= 70 ? "Good" : current >= 55 ? "Fair" : "Poor"} color={current >= 70 ? "#22C55E" : current >= 55 ? "#F59E0B" : "#E5484D"} />
          <StatCell label="YTD Change" value={`${delta >= 0 ? "+" : ""}${delta}%`} sub="vs Jan 2024" color={deltaColor} />
          <StatCell label="Controls" value={meta ? String(meta.total) : "147"} sub={`${meta ? meta.high : 79} high-coverage`} color="#8B5CF6" />
        </div>
      </div>
    </div>
  );
}

function StatCell({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 11, color: "#4A4C57", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 800, color, fontFamily: "JetBrains Mono, monospace", marginBottom: 2 }}>{value}</div>
      <div style={{ fontSize: 10, color: "#4A4C57" }}>{sub}</div>
    </div>
  );
}
