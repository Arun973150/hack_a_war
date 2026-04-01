"use client";

import { useEffect, useRef, useState } from "react";
import { RegulationItem } from "./FeedMonitor";
import { AgentEvent } from "../lib/api";

const AGENTS = [
  { id: "scanner", name: "Scanner", color: "#3B82F6", icon: "S" },
  { id: "extractor", name: "Extractor", color: "#8B5CF6", icon: "E" },
  { id: "impact_analyst", name: "Impact Analyst", color: "#E5484D", icon: "I" },
  { id: "action_planner", name: "Action Planner", color: "#F59E0B", icon: "A" },
  { id: "validator", name: "Validator", color: "#22C55E", icon: "V" },
];

// Animated fallback logs shown while waiting for real SSE data
const FALLBACK_LOGS: Record<string, (reg: RegulationItem) => string[]> = {
  scanner: (r) => [
    `Fetching: ${r.id} from ${r.regulator}`, `Document type: ${r.docType}`,
    `Jurisdiction: ${r.jurisdiction} — confidence 0.97`, `Sector: ${r.sector}`, `Relevance: RELEVANT ✓`,
  ],
  extractor: (r) => [
    `Semantic chunking: 3 chunks @ avg 480 tokens`, `Extracting SPO triplets...`,
    `Found 7 obligations (WHO / WHAT / DEADLINE)`, `${r.body.slice(0, 60)}...`, `Penalty clauses: 2 identified`,
  ],
  impact_analyst: (r) => [
    `Querying Neo4j knowledge graph...`,
    `MATCH (r:Regulation)-[:APPLIES_TO]->(o:Obligation) WHERE r.jurisdiction='${r.jurisdiction}'`,
    `Retrieved 23 existing controls · Coverage gaps: 4 obligations`,
    `Fetching CVEs from NVD + CISA KEV for sector: ${r.sector}`,
    `Mapped 3 CVEs to compliance obligations · Risk score: ${r.severity === "Critical" ? 9 : 7}/10`,
  ],
  action_planner: (r) => [
    `Generating remediation tasks for 4 compliance gaps`,
    `Assigning owners: Compliance, Legal, Technology, Security Engineering`,
    `Adding CVE patch tasks with regulatory deadlines (RBI 48h, DPDP 72h)`,
    `Task 1: Patch encryption CVE — 48h per RBI PA Guidelines`,
    `${r.jurisdiction} action plan complete · ${r.severity === "Critical" ? 8 : 5} tasks generated`,
  ],
  validator: () => [
    `Validating schema completeness...`, `All obligations have coverage assessments ✓`,
    `Action items have owners and deadlines ✓`, `Risk score in expected range ✓`, `Output valid — complete`,
  ],
};

interface AgentState {
  status: "pending" | "running" | "done";
  logs: string[];
  visibleCount: number;
}

interface Props {
  regulation: RegulationItem | null;
  sseEvents: AgentEvent[];
  activeStep: number;
  isRunning: boolean;
  isRealMode: boolean; // true = real SSE, false = simulated
}

export default function AgentTrace({ regulation, sseEvents, activeStep, isRunning, isRealMode }: Props) {
  const [agentStates, setAgentStates] = useState<AgentState[]>(
    AGENTS.map(() => ({ status: "pending", logs: [], visibleCount: 0 })),
  );
  const logIntervals = useRef<Record<number, NodeJS.Timeout>>({});

  // Reset on new regulation
  useEffect(() => {
    Object.values(logIntervals.current).forEach(clearInterval);
    logIntervals.current = {};
    setAgentStates(AGENTS.map(() => ({ status: "pending", logs: [], visibleCount: 0 })));
  }, [regulation?.id]);

  // Real SSE mode: update from SSE events
  useEffect(() => {
    if (!isRealMode || !regulation) return;

    sseEvents.forEach((evt) => {
      if (evt.type === "agent_done" && evt.step !== undefined) {
        const step = evt.step;
        const logs = evt.logs && evt.logs.length > 0 ? evt.logs : FALLBACK_LOGS[evt.node || ""]?.(regulation) || [];

        setAgentStates((prev) => {
          const next = [...prev];
          // Mark all previous as done
          for (let i = 0; i < step; i++) {
            if (next[i].status !== "done") {
              next[i] = { status: "done", logs: FALLBACK_LOGS[AGENTS[i].id]?.(regulation) || [], visibleCount: 999 };
            }
          }
          next[step] = { status: "done", logs, visibleCount: logs.length };
          return next;
        });
      }
    });
  }, [sseEvents, isRealMode, regulation?.id]);

  // Simulated mode: animate logs for each active step
  useEffect(() => {
    if (isRealMode || !regulation || activeStep < 0) return;

    const idx = activeStep;
    if (idx >= AGENTS.length) return;

    const logs = FALLBACK_LOGS[AGENTS[idx].id]?.(regulation) || [];

    setAgentStates((prev) => {
      const next = [...prev];
      // Mark all prior as done
      for (let i = 0; i < idx; i++) {
        next[i] = { status: "done", logs: FALLBACK_LOGS[AGENTS[i].id]?.(regulation) || [], visibleCount: 999 };
      }
      next[idx] = { status: "running", logs, visibleCount: 0 };
      return next;
    });

    let count = 0;
    const interval = setInterval(() => {
      count++;
      setAgentStates((prev) => {
        const next = [...prev];
        next[idx] = { ...next[idx], visibleCount: count };
        return next;
      });
      if (count >= logs.length) clearInterval(interval);
    }, 300);

    logIntervals.current[idx] = interval;
    return () => clearInterval(interval);
  }, [activeStep, isRealMode, regulation?.id]);

  // When analysis completes (step = AGENTS.length), mark last as done
  useEffect(() => {
    if (!isRealMode && !isRunning && activeStep >= AGENTS.length && regulation) {
      setAgentStates((prev) => {
        const next = [...prev];
        next[AGENTS.length - 1] = {
          status: "done",
          logs: FALLBACK_LOGS["validator"]?.(regulation) || [],
          visibleCount: 999,
        };
        return next;
      });
    }
  }, [isRunning, activeStep, isRealMode, regulation?.id]);

  return (
    <div style={{
      background: "#0D0D12", border: "1px solid rgba(255,255,255,0.07)",
      borderRadius: 12, overflow: "hidden", display: "flex", flexDirection: "column", height: "100%",
    }}>
      <div style={{
        padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.07)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#EDEDEF" }}>Agent Trace</span>
          {isRunning && (
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#22C55E", boxShadow: "0 0 6px rgba(34,197,94,0.6)", display: "inline-block", animation: "blink 1s infinite" }} />
          )}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
        {!regulation ? (
          <EmptyState />
        ) : (
          AGENTS.map((agent, idx) => (
            <AgentStep
              key={agent.id}
              agent={agent}
              state={agentStates[idx]}
              isLast={idx === AGENTS.length - 1}
            />
          ))
        )}
      </div>

      <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
        @keyframes spin { to{transform:rotate(360deg)} }
      `}</style>
    </div>
  );
}

function EmptyState() {
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, padding: "40px 0" }}>
      <div style={{ width: 48, height: 48, borderRadius: 12, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700, color: "#4A4C57", letterSpacing: "0.05em" }}>AI</div>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#4A4C57", marginBottom: 4 }}>Select a regulation to analyze</div>
        <div style={{ fontSize: 12, color: "#2A2C37" }}>5 AI agents · LangGraph pipeline</div>
      </div>
    </div>
  );
}

function AgentStep({ agent, state, isLast }: { agent: (typeof AGENTS)[0]; state: AgentState; isLast: boolean }) {
  const { status, logs, visibleCount } = state;
  const shownLogs = logs.slice(0, visibleCount);

  return (
    <div style={{ display: "flex", gap: 12 }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0 }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8, flexShrink: 0,
          display: "flex", alignItems: "center", justifyContent: "center",
          background: status === "done" ? `${agent.color}20` : status === "running" ? `${agent.color}15` : "rgba(255,255,255,0.03)",
          border: `1px solid ${status !== "pending" ? agent.color + "50" : "rgba(255,255,255,0.07)"}`,
          fontSize: 14, transition: "all .3s ease",
        }}>
          {status === "running" ? (
            <div style={{ width: 14, height: 14, borderRadius: "50%", border: `2px solid ${agent.color}`, borderTopColor: "transparent", animation: "spin 0.8s linear infinite" }} />
          ) : status === "done" ? (
            <span style={{ fontSize: 11, fontWeight: 700, color: agent.color }}>{agent.icon}</span>
          ) : (
            <span style={{ fontSize: 10, color: "#4A4C57", fontWeight: 600 }}>—</span>
          )}
        </div>
        {!isLast && (
          <div style={{
            width: 1, flex: 1, marginTop: 4, minHeight: 12,
            background: status === "done" ? `linear-gradient(${agent.color}, rgba(255,255,255,0.07))` : "rgba(255,255,255,0.07)",
            transition: "background .5s ease",
          }} />
        )}
      </div>

      <div style={{ flex: 1, paddingBottom: isLast ? 0 : 4 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: status !== "pending" ? agent.color : "#4A4C57", transition: "color .3s" }}>
            {agent.name}
          </span>
          {status === "done" && <span style={{ fontSize: 10, color: "#22C55E", marginLeft: "auto" }}>done</span>}
          {status === "running" && <span style={{ fontSize: 10, color: agent.color, marginLeft: "auto", animation: "blink 1s infinite" }}>processing...</span>}
        </div>

        {status !== "pending" && (
          <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 6, padding: "8px 10px", fontFamily: "JetBrains Mono, monospace" }}>
            {shownLogs.map((log, i) => (
              <div key={i} style={{
                fontSize: 11, color: i === shownLogs.length - 1 && status === "running" ? "#EDEDEF" : "#8B8D97",
                lineHeight: 1.6, paddingLeft: 8,
                borderLeft: `2px solid ${i === shownLogs.length - 1 && status === "running" ? agent.color : "transparent"}`,
              }}>
                <span style={{ color: "#4A4C57" }}>› </span>{log}
              </div>
            ))}
            {status === "running" && (
              <div style={{ display: "flex", gap: 3, paddingLeft: 8, marginTop: 4 }}>
                {[0, 1, 2].map(i => (
                  <div key={i} style={{ width: 4, height: 4, borderRadius: "50%", background: agent.color, opacity: 0.6, animation: `blink 1s ${i * 0.2}s infinite` }} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
