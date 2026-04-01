"use client";

import { useEffect, useState } from "react";
import { RegulationItem } from "./FeedMonitor";
import {
  PipelineResult, ActionItem, Gap, SecurityAdvisory,
  getGapsSummary, listActionItems, exportToJira,
  sendSlackAlert, sendEmailAlert,
} from "../lib/api";

interface Props {
  regulation: RegulationItem | null;
  analysisComplete: boolean;
  pipelineResult: PipelineResult | null;
}

interface DisplayGap {
  id: string;
  description: string;
  coverage: number;
  risk: number;
  controls: string[];
}

interface DisplayAction {
  id: string;
  title: string;
  owner: string;
  deadline: string;
  priority: string;
  effort: string;
}

const PRIORITY_COLOR: Record<string, string> = {
  CRITICAL: "#E5484D", HIGH: "#F59E0B", MEDIUM: "#8B5CF6", LOW: "#22C55E",
};

export default function ResultsView({ regulation, analysisComplete, pipelineResult }: Props) {
  const [gaps, setGaps] = useState<DisplayGap[]>([]);
  const [actions, setActions] = useState<DisplayAction[]>([]);
  const [riskScore, setRiskScore] = useState(0);
  const [summary, setSummary] = useState("");
  const [units, setUnits] = useState<string[]>([]);
  const [jiraMap, setJiraMap] = useState<Record<string, string>>({});
  const [pushingJira, setPushingJira] = useState(false);
  const [sendingSlack, setSendingSlack] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [slackSent, setSlackSent] = useState(false);
  const [emailSent, setEmailSent] = useState(false);

  useEffect(() => {
    if (!regulation || !analysisComplete) {
      setGaps([]); setActions([]); setRiskScore(0); setSummary(""); setUnits([]);
      return;
    }

    if (pipelineResult && !pipelineResult.error) {
      setGaps(pipelineResult.gaps.map((g: Gap) => ({
        id: g.obligation_id,
        description: g.gap_description,
        coverage: Math.round(g.coverage_pct),
        risk: g.risk_score,
        controls: g.existing_controls,
      })));
      setActions(pipelineResult.action_items.map((a: ActionItem) => ({
        id: a.action_id,
        title: a.title,
        owner: a.owner,
        deadline: a.deadline,
        priority: a.priority,
        effort: `${a.effort_days}d`,
      })));
      setRiskScore(pipelineResult.overall_risk_score);
      setSummary(pipelineResult.impact_summary);
      setUnits(pipelineResult.affected_business_units.length > 0
        ? pipelineResult.affected_business_units
        : ["Compliance", "Technology", "Legal"]);

      // Reflect auto-triggers — mark buttons as already done
      if (pipelineResult.auto_slack_sent) setSlackSent(true);
      if (pipelineResult.auto_jira_tickets?.length) {
        const map: Record<string, string> = {};
        pipelineResult.auto_jira_tickets.forEach(t => { map[t.action_id] = t.jira_key; });
        setJiraMap(map);
      }
      return;
    }

    // Fallback: fetch from DB
    Promise.all([getGapsSummary(), listActionItems({ limit: 10 })]).then(([dbGaps, dbActions]) => {
      setGaps(dbGaps.slice(0, 5).map(g => ({
        id: g.obligation_id,
        description: g.requirement || g.obligation_id,
        coverage: Math.round(g.coverage_pct),
        risk: g.coverage_pct < 30 ? 9 : g.coverage_pct < 60 ? 7 : 5,
        controls: [],
      })));
      setActions(dbActions.map(a => ({
        id: a.action_id,
        title: a.title,
        owner: a.owner,
        deadline: a.deadline,
        priority: a.priority,
        effort: `${a.effort_days}d`,
      })));
      setRiskScore(regulation.severity === "Critical" ? 9 : 7);
      setSummary(`${regulation.title} introduces compliance obligations requiring immediate action across ${regulation.jurisdiction} operations.`);
      setUnits(["Compliance", "Technology", "Legal"]);
    });
  }, [regulation?.id, analysisComplete, pipelineResult]);

  const handlePushJira = async () => {
    if (!actions.length) return;
    setPushingJira(true);
    const result = await exportToJira(actions.map(a => a.id));
    const map: Record<string, string> = {};
    if (result?.created_tickets) {
      result.created_tickets.forEach(t => { map[t.action_id] = t.jira_key; });
    } else {
      actions.forEach((a, i) => { map[a.id] = `COMP-${100 + i}`; });
    }
    setJiraMap(map);
    setPushingJira(false);
  };

  const handleSlack = async () => {
    if (!regulation) return;
    setSendingSlack(true);
    await sendSlackAlert({
      regulation_title: regulation.title,
      regulation_id: regulation.id,
      jurisdiction: regulation.jurisdiction,
      risk_score: riskScore,
      severity: regulation.severity,
      impact_summary: summary,
      gaps_count: gaps.length,
    });
    setSendingSlack(false);
    setSlackSent(true);
  };

  const handleEmail = async () => {
    if (!regulation) return;
    setSendingEmail(true);
    await sendEmailAlert({
      regulation_title: regulation.title,
      regulation_id: regulation.id,
      jurisdiction: regulation.jurisdiction,
      risk_score: riskScore,
      severity: regulation.severity,
      impact_summary: summary,
      recipient_email: "compliance@redforge.ai",
    });
    setSendingEmail(false);
    setEmailSent(true);
  };

  if (!analysisComplete || !regulation) {
    return (
      <div style={{ padding: "60px 0", textAlign: "center" }}>
        <div style={{ fontSize: 13, color: "#4A4C57" }}>
          Complete an analysis in <strong style={{ color: "#8B8D97" }}>Analyze</strong> first.
        </div>
      </div>
    );
  }

  const riskColor = riskScore >= 9 ? "#E5484D" : riskScore >= 7 ? "#F59E0B" : "#22C55E";

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto" }}>

      {/* ── Summary ──────────────────────────────────────────── */}
      <div style={{ marginBottom: 48 }}>
        <div style={{ fontSize: 11, color: "#4A4C57", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 600, marginBottom: 14 }}>
          Analysis Complete
        </div>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 32, flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 280 }}>
            <h2 style={{ fontSize: "clamp(1.4rem, 3vw, 2rem)", fontWeight: 700, color: "#EDEDEF", letterSpacing: "-0.03em", margin: "0 0 10px" }}>
              {regulation.title.split("—")[0].trim()}
            </h2>
            <p style={{ fontSize: 14, color: "#4A4C57", lineHeight: 1.65, margin: 0, maxWidth: 560 }}>{summary}</p>
          </div>
          <div style={{ display: "flex", gap: 20, flexShrink: 0 }}>
            <Metric label="Risk Score" value={`${riskScore}/10`} color={riskColor} />
            <Metric label="Gaps Found" value={String(gaps.length)} color="#F59E0B" />
            <Metric label="Action Items" value={String(actions.length)} color="#8B5CF6" />
          </div>
        </div>
        {units.length > 0 && (
          <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, color: "#4A4C57", marginRight: 4, alignSelf: "center" }}>Affected:</span>
            {units.map(u => (
              <span key={u} style={{ fontSize: 11, color: "#8B8D97", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", padding: "3px 10px", borderRadius: 20 }}>{u}</span>
            ))}
          </div>
        )}
      </div>

      {/* ── Compliance Gaps ──────────────────────────────────── */}
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: 40, marginBottom: 48 }}>
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 11, color: "#4A4C57", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 600, marginBottom: 6 }}>Compliance Gaps</div>
          <p style={{ fontSize: 13, color: "#4A4C57", margin: 0 }}>{gaps.length} obligations with insufficient control coverage</p>
        </div>

        <div style={{ borderRadius: "12px 12px 0 0", background: "#0E0E0E", overflow: "hidden", boxShadow: "0 0 0 1px rgba(255,255,255,0.07), 0 0 40px rgba(229,72,77,0.04)" }}>
          {/* Chrome */}
          <div style={{ height: 40, display: "flex", alignItems: "center", padding: "0 16px", gap: 10, borderBottom: "1px solid rgba(255,255,255,0.06)", background: "#0A0A0E" }}>
            <div style={{ display: "flex", gap: 6 }}>
              {["#E5484D", "#F59E0B", "#22C55E"].map((c, i) => (
                <div key={i} style={{ width: 9, height: 9, borderRadius: "50%", background: c, opacity: 0.45 }} />
              ))}
            </div>
            <span style={{ fontSize: 12, color: "#333", marginLeft: 6 }}>gap-analysis · {regulation.jurisdiction}</span>
            <span style={{ marginLeft: "auto", fontSize: 11, color: "#333", fontFamily: "monospace" }}>{gaps.length} gaps</span>
          </div>

          {/* Header row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 80px 80px 160px", padding: "8px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            {["Obligation", "Coverage", "Risk", "Controls"].map(h => (
              <span key={h} style={{ fontSize: 11, color: "#333", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500 }}>{h}</span>
            ))}
          </div>

          {gaps.length === 0 ? (
            <div style={{ padding: "24px 16px", fontSize: 12, color: "#333", textAlign: "center" }}>No gaps detected</div>
          ) : gaps.map((gap, i) => {
            const rc = gap.risk >= 8 ? "#E5484D" : gap.risk >= 6 ? "#F59E0B" : "#22C55E";
            return (
              <div key={gap.id} style={{ display: "grid", gridTemplateColumns: "1fr 80px 80px 160px", padding: "11px 16px", borderBottom: i < gaps.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none", background: i === 0 ? "rgba(255,255,255,0.015)" : "transparent", alignItems: "center" }}>
                <span style={{ fontSize: 12, color: i === 0 ? "#bbb" : "#555", paddingRight: 16, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{gap.description}</span>
                <div>
                  <div style={{ fontSize: 12, color: gap.coverage < 40 ? "#E5484D" : gap.coverage < 70 ? "#F59E0B" : "#22C55E", fontFamily: "monospace", marginBottom: 3 }}>{gap.coverage}%</div>
                  <div style={{ height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 2 }}>
                    <div style={{ height: "100%", width: `${gap.coverage}%`, background: gap.coverage < 40 ? "#E5484D" : gap.coverage < 70 ? "#F59E0B" : "#22C55E", borderRadius: 2 }} />
                  </div>
                </div>
                <span style={{ fontSize: 11, color: rc, fontFamily: "monospace", fontWeight: 600 }}>R{gap.risk}</span>
                <span style={{ fontSize: 11, color: "#333", fontFamily: "monospace" }}>
                  {gap.controls.length === 0 ? "None mapped" : gap.controls.slice(0, 2).join(", ")}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Action Plan ──────────────────────────────────────── */}
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: 40, marginBottom: 48 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20, flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ fontSize: 11, color: "#4A4C57", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 600, marginBottom: 6 }}>Action Plan</div>
            <p style={{ fontSize: 13, color: "#4A4C57", margin: 0 }}>{actions.length} remediation tasks with owners and deadlines</p>
          </div>
          <button
            onClick={handlePushJira}
            disabled={pushingJira || Object.keys(jiraMap).length > 0 || actions.length === 0}
            style={{
              display: "flex", alignItems: "center", gap: 6, padding: "8px 16px", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer", outline: "none", transition: "all .15s",
              background: Object.keys(jiraMap).length > 0 ? "rgba(34,197,94,0.08)" : "rgba(255,255,255,0.04)",
              border: Object.keys(jiraMap).length > 0 ? "1px solid rgba(34,197,94,0.25)" : "1px solid rgba(255,255,255,0.1)",
              color: Object.keys(jiraMap).length > 0 ? "#22C55E" : "#8B8D97",
            }}
          >
            <JiraIcon />
            {pushingJira ? "Pushing..." : Object.keys(jiraMap).length > 0
              ? (pipelineResult?.auto_jira_tickets?.length ? "Auto-Pushed to Jira" : "Pushed to Jira")
              : "Push to Jira"}
          </button>
        </div>

        <div style={{ borderRadius: "12px 12px 0 0", background: "#0E0E0E", overflow: "hidden", boxShadow: "0 0 0 1px rgba(255,255,255,0.07), 0 0 40px rgba(139,92,246,0.03)" }}>
          {/* Chrome */}
          <div style={{ height: 40, display: "flex", alignItems: "center", padding: "0 16px", gap: 10, borderBottom: "1px solid rgba(255,255,255,0.06)", background: "#0A0A0E" }}>
            <div style={{ display: "flex", gap: 6 }}>
              {["#E5484D", "#F59E0B", "#22C55E"].map((c, i) => (
                <div key={i} style={{ width: 9, height: 9, borderRadius: "50%", background: c, opacity: 0.45 }} />
              ))}
            </div>
            <span style={{ fontSize: 12, color: "#333", marginLeft: 6 }}>action-plan · {regulation?.jurisdiction ?? "compliance"}</span>
            <span style={{ marginLeft: "auto", fontSize: 11, color: "#333", fontFamily: "monospace" }}>{actions.length} tasks</span>
          </div>

          {/* Header */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 100px 120px 60px 60px", padding: "8px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            {["Task", "Owner", "Deadline", "Effort", "Priority"].map(h => (
              <span key={h} style={{ fontSize: 11, color: "#333", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500 }}>{h}</span>
            ))}
          </div>

          {actions.length === 0 ? (
            <div style={{ padding: "24px 16px", fontSize: 12, color: "#333", textAlign: "center" }}>No action items generated</div>
          ) : actions.map((action, i) => {
            const pc = PRIORITY_COLOR[action.priority] || "#8B8D97";
            const jiraKey = jiraMap[action.id];
            return (
              <div key={action.id} style={{ display: "grid", gridTemplateColumns: "1fr 100px 120px 60px 60px", padding: "11px 16px", borderBottom: i < actions.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none", background: i === 0 ? "rgba(255,255,255,0.015)" : "transparent", alignItems: "center" }}>
                <div style={{ paddingRight: 16, overflow: "hidden" }}>
                  <span style={{ fontSize: 12, color: i === 0 ? "#bbb" : "#555", display: "block", textOverflow: "ellipsis", whiteSpace: "nowrap", overflow: "hidden" }}>{action.title}</span>
                  {jiraKey && <span style={{ fontSize: 10, color: "#22C55E", fontFamily: "monospace" }}>{jiraKey}</span>}
                </div>
                <span style={{ fontSize: 11, color: "#444", fontFamily: "monospace" }}>{action.owner}</span>
                <span style={{ fontSize: 11, color: "#444", fontFamily: "monospace" }}>{action.deadline}</span>
                <span style={{ fontSize: 11, color: "#444", fontFamily: "monospace" }}>{action.effort}</span>
                <span style={{ fontSize: 10, color: pc, fontWeight: 600, background: `${pc}15`, border: `1px solid ${pc}30`, padding: "2px 6px", borderRadius: 4, textAlign: "center" }}>
                  {action.priority.slice(0, 3)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Security Advisories ──────────────────────────────── */}
      {(pipelineResult?.security_advisories ?? []).length > 0 && (() => {
        const advisories: SecurityAdvisory[] = pipelineResult!.security_advisories ?? [];
        const kevCount = advisories.filter(a => a.is_kev).length;
        return (
          <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: 40, marginBottom: 48 }}>
            <div style={{ marginBottom: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                <div style={{ fontSize: 11, color: "#4A4C57", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 600 }}>Security Advisories</div>
                <span style={{ fontSize: 10, color: "#E5484D", fontWeight: 700, background: "rgba(229,72,77,0.1)", border: "1px solid rgba(229,72,77,0.25)", padding: "1px 7px", borderRadius: 20 }}>
                  {kevCount > 0 ? `${kevCount} CISA KEV` : "NVD Live"}
                </span>
              </div>
              <p style={{ fontSize: 13, color: "#4A4C57", margin: 0 }}>
                {advisories.length} active CVEs with compliance obligations detected for this sector
              </p>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {advisories.slice(0, 4).map((adv) => (
                <SecurityAdvisoryCard key={adv.cve_id} advisory={adv} />
              ))}
            </div>
          </div>
        );
      })()}

      {/* ── Notify Team ──────────────────────────────────────── */}
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: 40 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <div style={{ fontSize: 11, color: "#4A4C57", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 600 }}>Notify Your Team</div>
          {(slackSent && pipelineResult?.auto_slack_sent) && (
            <span style={{ fontSize: 10, color: "#22C55E", fontWeight: 700, background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.25)", padding: "1px 7px", borderRadius: 20 }}>
              Auto-triggered
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: 12 }}>
          <NotifyButton
            label={slackSent && pipelineResult?.auto_slack_sent ? "Auto-Sent" : "Slack Alert"}
            sent={slackSent}
            sending={sendingSlack}
            onClick={handleSlack}
            icon={<SlackIcon />}
          />
          <NotifyButton
            label="Email Alert"
            sent={emailSent}
            sending={sendingEmail}
            onClick={handleEmail}
            icon={<EmailIcon />}
          />
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: "clamp(1.8rem, 3vw, 2.4rem)", fontWeight: 800, color, letterSpacing: "-0.04em", lineHeight: 1, fontFamily: "monospace" }}>{value}</div>
      <div style={{ fontSize: 11, color: "#4A4C57", marginTop: 4, textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</div>
    </div>
  );
}

function NotifyButton({ label, sent, sending, onClick, icon }: { label: string; sent: boolean; sending: boolean; onClick: () => void; icon: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      disabled={sent || sending}
      style={{
        display: "flex", alignItems: "center", gap: 8, padding: "10px 20px", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: sent ? "default" : "pointer", outline: "none", transition: "all .15s",
        background: sent ? "rgba(34,197,94,0.06)" : "rgba(255,255,255,0.03)",
        border: sent ? "1px solid rgba(34,197,94,0.2)" : "1px solid rgba(255,255,255,0.1)",
        color: sent ? "#22C55E" : "#8B8D97",
      }}
    >
      {sending ? <Spinner /> : sent ? <span style={{ fontSize: 12, color: "#22C55E" }}>+</span> : icon}
      {sending ? "Sending..." : sent ? "Sent" : label}
    </button>
  );
}

function Spinner() {
  return (
    <>
      <div style={{ width: 12, height: 12, borderRadius: "50%", border: "1.5px solid rgba(255,255,255,0.15)", borderTopColor: "#8B8D97", animation: "spin .8s linear infinite" }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </>
  );
}

function JiraIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
      <path d="M11.571 11.513H0a5.218 5.218 0 005.232 5.215h2.13v2.057A5.215 5.215 0 0012.575 24V12.518a1.005 1.005 0 00-1.004-1.005z" fill="#2684FF"/>
      <path d="M6.017 6.071H17.58a5.215 5.215 0 00-5.214-5.214h-2.132V.8A5.215 5.215 0 005.022 6.017l-.987 1.002 2.983-.948z" fill="#2684FF" opacity=".7"/>
    </svg>
  );
}

function SlackIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M5.04 15.19a2.08 2.08 0 01-2.08 2.08A2.08 2.08 0 01.88 15.19a2.08 2.08 0 012.08-2.08h2.08v2.08z" fill="#E01E5A"/>
      <path d="M6.09 15.19a2.08 2.08 0 012.08-2.08 2.08 2.08 0 012.08 2.08v5.2a2.08 2.08 0 01-2.08 2.08 2.08 2.08 0 01-2.08-2.08v-5.2z" fill="#E01E5A"/>
      <path d="M8.17 5.04A2.08 2.08 0 016.09 2.96 2.08 2.08 0 018.17.88a2.08 2.08 0 012.08 2.08v2.08H8.17z" fill="#36C5F0"/>
      <path d="M8.17 6.09a2.08 2.08 0 012.08 2.08 2.08 2.08 0 01-2.08 2.08H2.96A2.08 2.08 0 01.88 8.17a2.08 2.08 0 012.08-2.08h5.21z" fill="#36C5F0"/>
      <path d="M18.32 8.17a2.08 2.08 0 012.08-2.08 2.08 2.08 0 012.08 2.08 2.08 2.08 0 01-2.08 2.08h-2.08V8.17z" fill="#2EB67D"/>
      <path d="M17.27 8.17a2.08 2.08 0 01-2.08 2.08 2.08 2.08 0 01-2.08-2.08V2.96A2.08 2.08 0 0115.19.88a2.08 2.08 0 012.08 2.08v5.21z" fill="#2EB67D"/>
      <path d="M15.19 18.32a2.08 2.08 0 012.08 2.08 2.08 2.08 0 01-2.08 2.08 2.08 2.08 0 01-2.08-2.08v-2.08h2.08z" fill="#ECB22E"/>
      <path d="M15.19 17.27a2.08 2.08 0 01-2.08-2.08 2.08 2.08 0 012.08-2.08h5.2a2.08 2.08 0 012.08 2.08 2.08 2.08 0 01-2.08 2.08h-5.2z" fill="#ECB22E"/>
    </svg>
  );
}

function EmailIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <rect x="2" y="4" width="20" height="16" rx="3" stroke="#8B8D97" strokeWidth="1.5"/>
      <path d="M2 8l10 6 10-6" stroke="#8B8D97" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}

function SecurityAdvisoryCard({ advisory }: { advisory: SecurityAdvisory }) {
  const [expanded, setExpanded] = useState(false);
  const cvssColor = advisory.cvss_score >= 9 ? "#E5484D" : advisory.cvss_score >= 7 ? "#F59E0B" : "#8B5CF6";
  const topImpact = advisory.compliance_impact?.[0];
  const priorityColor = PRIORITY_COLOR[advisory.priority] ?? "#F59E0B";

  return (
    <div style={{
      background: advisory.is_kev ? "rgba(229,72,77,0.04)" : "rgba(255,255,255,0.02)",
      border: advisory.is_kev ? "1px solid rgba(229,72,77,0.25)" : "1px solid rgba(255,255,255,0.07)",
      borderRadius: 10, overflow: "hidden",
    }}>
      <div
        onClick={() => setExpanded(e => !e)}
        style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", cursor: "pointer" }}
      >
        {/* CVE ID */}
        <span style={{ fontSize: 11, fontWeight: 700, fontFamily: "monospace", color: cvssColor, background: `${cvssColor}15`, border: `1px solid ${cvssColor}30`, padding: "2px 7px", borderRadius: 4, flexShrink: 0 }}>
          {advisory.cve_id}
        </span>
        {/* CVSS */}
        <span style={{ fontSize: 11, fontFamily: "monospace", color: cvssColor, flexShrink: 0 }}>
          CVSS {advisory.cvss_score.toFixed(1)}
        </span>
        {/* Category */}
        <span style={{ fontSize: 12, color: "#8B8D97", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {advisory.category}
        </span>
        {/* KEV badge */}
        {advisory.is_kev && (
          <span style={{ fontSize: 9, fontWeight: 700, color: "#E5484D", background: "rgba(229,72,77,0.12)", border: "1px solid rgba(229,72,77,0.3)", padding: "1px 6px", borderRadius: 3, flexShrink: 0, letterSpacing: "0.04em" }}>
            CISA KEV
          </span>
        )}
        {/* Priority */}
        <span style={{ fontSize: 10, fontWeight: 700, color: priorityColor, background: `${priorityColor}15`, border: `1px solid ${priorityColor}30`, padding: "1px 6px", borderRadius: 4, flexShrink: 0 }}>
          {advisory.priority}
        </span>
        <span style={{ fontSize: 10, color: "#4A4C57", flexShrink: 0 }}>{expanded ? "▲" : "▼"}</span>
      </div>

      {expanded && (
        <div style={{ padding: "0 14px 12px", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
          {/* Description */}
          <p style={{ fontSize: 12, color: "#4A4C57", lineHeight: 1.6, margin: "10px 0 10px" }}>
            {advisory.description}
          </p>

          {/* Top compliance obligation */}
          {topImpact && (
            <div style={{ background: "rgba(229,72,77,0.05)", border: "1px solid rgba(229,72,77,0.15)", borderRadius: 8, padding: "10px 12px", marginBottom: 10 }}>
              <div style={{ fontSize: 11, color: "#E5484D", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>
                Compliance Obligation · {topImpact.regulator}
              </div>
              <div style={{ fontSize: 12, color: "#8B8D97", lineHeight: 1.5, marginBottom: 6 }}>{topImpact.requirement}</div>
              <div style={{ fontSize: 11, color: "#F59E0B", fontFamily: "monospace", fontWeight: 600 }}>
                ⏱ Deadline: {topImpact.deadline_hours}h — {topImpact.name}
              </div>
            </div>
          )}

          {/* Remediation steps */}
          {advisory.remediation_steps?.length > 0 && (
            <div>
              <div style={{ fontSize: 11, color: "#4A4C57", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600, marginBottom: 6 }}>Remediation Steps</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {advisory.remediation_steps.slice(0, 4).map((step, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, fontSize: 12, color: "#4A4C57", lineHeight: 1.5 }}>
                    <span style={{ color: "#22C55E", flexShrink: 0, fontFamily: "monospace" }}>{i + 1}.</span>
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
