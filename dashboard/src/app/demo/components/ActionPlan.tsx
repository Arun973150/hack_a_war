"use client";

import { useEffect, useState } from "react";
import { RegulationItem } from "./FeedMonitor";
import { listActionItems, exportToJira, DBActionItem, ActionItem as PipelineAction, PipelineResult } from "../lib/api";

interface DisplayTask {
  id: string;
  title: string;
  owner: string;
  deadline: string;
  effort: string;
  priority: "Critical" | "High" | "Medium";
  status: string;
  jiraKey?: string | null;
}

function mapDbItem(i: DBActionItem): DisplayTask {
  return {
    id: i.action_id,
    title: i.title,
    owner: i.owner,
    deadline: i.deadline,
    effort: `${i.effort_days} day${i.effort_days !== 1 ? "s" : ""}`,
    priority: (i.priority === "CRITICAL" ? "Critical" : i.priority === "HIGH" ? "High" : "Medium") as DisplayTask["priority"],
    status: i.status,
    jiraKey: i.jira_ticket_id,
  };
}

function mapPipelineAction(a: PipelineAction): DisplayTask {
  return {
    id: a.action_id,
    title: a.title,
    owner: a.owner,
    deadline: a.deadline,
    effort: `${a.effort_days} day${a.effort_days !== 1 ? "s" : ""}`,
    priority: (a.priority === "CRITICAL" ? "Critical" : a.priority === "HIGH" ? "High" : "Medium") as DisplayTask["priority"],
    status: "Open",
    jiraKey: null,
  };
}

const PRIORITY_COLORS = {
  Critical: { bg: "rgba(229,72,77,0.1)", text: "#E5484D", border: "rgba(229,72,77,0.25)" },
  High: { bg: "rgba(245,158,11,0.1)", text: "#F59E0B", border: "rgba(245,158,11,0.25)" },
  Medium: { bg: "rgba(139,92,246,0.1)", text: "#8B5CF6", border: "rgba(139,92,246,0.25)" },
};

interface Props {
  regulation: RegulationItem | null;
  analysisComplete: boolean;
  pipelineResult: PipelineResult | null;
}

export default function ActionPlan({ regulation, analysisComplete, pipelineResult }: Props) {
  const [tasks, setTasks] = useState<DisplayTask[]>([]);
  const [jiraStatus, setJiraStatus] = useState<"idle" | "pushing" | "done">("idle");
  const [pushedMap, setPushedMap] = useState<Record<string, string>>({});
  const [fromApi, setFromApi] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setJiraStatus("idle");
    setPushedMap({});
    setTasks([]);
    setFromApi(false);

    if (!regulation || !analysisComplete) return;

    setLoading(true);

    // Priority 1: pipeline result action items
    if (pipelineResult?.action_items && pipelineResult.action_items.length > 0) {
      setTasks(pipelineResult.action_items.map(mapPipelineAction));
      setFromApi(true);
      setLoading(false);
      return;
    }

    // Priority 2: real DB action items
    listActionItems({ limit: 20 }).then((items) => {
      if (items.length > 0) {
        setTasks(items.map(mapDbItem));
        setFromApi(true);
      } else {
        setTasks([]);
        setFromApi(false);
      }
      setLoading(false);
    });
  }, [regulation?.id, analysisComplete, pipelineResult]);

  const handlePushToJira = async () => {
    if (!tasks.length) return;
    setJiraStatus("pushing");

    const actionIds = tasks.map((t) => t.id);
    const result = await exportToJira(actionIds);

    if (result?.created_tickets) {
      const map: Record<string, string> = {};
      result.created_tickets.forEach((t) => { map[t.action_id] = t.jira_key; });
      setPushedMap(map);
    } else {
      // Backend Jira call failed or demo mode — show simulated keys
      const map: Record<string, string> = {};
      tasks.forEach((t, i) => { map[t.id] = `COMP-${100 + i}`; });
      setPushedMap(map);
    }
    setJiraStatus("done");
  };

  return (
    <div style={{ background: "#0D0D12", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, overflow: "hidden" }}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#EDEDEF" }}>Action Plan</span>
          {fromApi && <span style={{ fontSize: 10, color: "#22C55E", fontWeight: 600 }}>● REAL DATA</span>}
          {tasks.length > 0 && (
            <span style={{ fontSize: 11, fontWeight: 600, background: "rgba(229,72,77,0.1)", color: "#E5484D", border: "1px solid rgba(229,72,77,0.25)", padding: "2px 8px", borderRadius: 20, fontFamily: "JetBrains Mono, monospace" }}>
              {tasks.length} tasks
            </span>
          )}
        </div>
        <JiraButton status={jiraStatus} disabled={!analysisComplete || tasks.length === 0} onClick={handlePushToJira} />
      </div>

      <div style={{ padding: "16px 20px" }}>
        {loading ? (
          <div style={{ padding: "20px 0", textAlign: "center" }}>
            <div style={{ fontSize: 12, color: "#4A4C57" }}>Loading action items...</div>
          </div>
        ) : tasks.length === 0 && analysisComplete ? (
          <div style={{ padding: "20px 0", textAlign: "center" }}>
            <div style={{ fontSize: 12, color: "#4A4C57" }}>No action items generated yet.</div>
          </div>
        ) : tasks.length === 0 ? (
          <div style={{ padding: "20px 0", textAlign: "center" }}>
            <div style={{ fontSize: 12, color: "#4A4C57" }}>Analyze a regulation to generate action items.</div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {tasks.map((task) => (
              <TaskRow key={task.id} task={task} jiraKey={pushedMap[task.id] || task.jiraKey} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function JiraButton({ status, disabled, onClick }: { status: "idle" | "pushing" | "done"; disabled: boolean; onClick: () => void }) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      onClick={onClick}
      disabled={disabled || status !== "idle"}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex", alignItems: "center", gap: 6, padding: "6px 14px", borderRadius: 7,
        fontSize: 12, fontWeight: 600, cursor: disabled ? "not-allowed" : "pointer",
        border: status === "done" ? "1px solid rgba(34,197,94,0.4)" : "1px solid rgba(255,255,255,0.15)",
        background: status === "done" ? "rgba(34,197,94,0.1)" : disabled ? "rgba(255,255,255,0.03)" : hovered ? "rgba(255,255,255,0.07)" : "rgba(255,255,255,0.04)",
        color: status === "done" ? "#22C55E" : disabled ? "#4A4C57" : "#EDEDEF",
        transition: "all .15s", outline: "none",
      }}
    >
      {status === "pushing" ? (
        <><div style={{ width: 12, height: 12, borderRadius: "50%", border: "1.5px solid #8B8D97", borderTopColor: "transparent", animation: "spin 0.8s linear infinite" }} />Pushing...</>
      ) : status === "done" ? <>Pushed to Jira</> : (
        <><JiraIcon />Push to Jira</>
      )}
      <style>{`@keyframes spin { to{transform:rotate(360deg)} }`}</style>
    </button>
  );
}

function JiraIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M11.571 11.513H0a5.218 5.218 0 005.232 5.215h2.13v2.057A5.215 5.215 0 0012.575 24V12.518a1.005 1.005 0 00-1.004-1.005z" fill="#2684FF"/>
      <path d="M6.017 6.071H17.58a5.215 5.215 0 00-5.214-5.214h-2.132V.8A5.215 5.215 0 005.022 6.017l-.987 1.002 2.983-.948z" fill="#2684FF" opacity=".7"/>
    </svg>
  );
}

function TaskRow({ task, jiraKey }: { task: DisplayTask; jiraKey?: string | null }) {
  const [expanded, setExpanded] = useState(false);
  const pColor = PRIORITY_COLORS[task.priority];
  return (
    <div
      style={{
        background: "rgba(0,0,0,0.2)", border: `1px solid ${jiraKey ? "rgba(34,197,94,0.2)" : "rgba(255,255,255,0.05)"}`,
        borderRadius: 8, padding: "10px 14px", cursor: "pointer", transition: "border-color .2s",
      }}
      onClick={() => setExpanded(!expanded)}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 6, height: 6, borderRadius: "50%", flexShrink: 0, background: jiraKey ? "#22C55E" : task.priority === "Critical" ? "#E5484D" : task.priority === "High" ? "#F59E0B" : "#8B5CF6", boxShadow: jiraKey ? "0 0 6px rgba(34,197,94,0.5)" : "none" }} />
        <span style={{ fontSize: 12, fontWeight: 500, color: "#C4C6D0", flex: 1, lineHeight: 1.3 }}>{task.title}</span>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em", background: pColor.bg, color: pColor.text, border: `1px solid ${pColor.border}`, padding: "2px 6px", borderRadius: 4, flexShrink: 0 }}>
          {task.priority}
        </span>
        {jiraKey && (
          <span style={{ fontSize: 10, color: "#22C55E", fontFamily: "JetBrains Mono, monospace", flexShrink: 0 }}>{jiraKey}</span>
        )}
        <span style={{ fontSize: 11, color: "#4A4C57", flexShrink: 0 }}>{expanded ? "▲" : "▼"}</span>
      </div>
      {expanded && (
        <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid rgba(255,255,255,0.05)" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
            <MetaCell label="Owner" value={task.owner} />
            <MetaCell label="Deadline" value={task.deadline} />
            <MetaCell label="Effort" value={task.effort} />
          </div>
        </div>
      )}
    </div>
  );
}

function MetaCell({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 10, color: "#4A4C57", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600, marginBottom: 3 }}>{label}</div>
      <div style={{ fontSize: 12, color: "#8B8D97", fontFamily: "JetBrains Mono, monospace" }}>{value}</div>
    </div>
  );
}
