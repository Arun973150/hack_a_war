"use client";

import { useState } from "react";
import { RegulationItem } from "./FeedMonitor";
import { sendSlackAlert, sendEmailAlert, PipelineResult } from "../lib/api";

interface Alert {
  id: string;
  time: string;
  channel: "slack" | "email";
  regulation: string;
  message: string;
  riskScore: number;
  demoMode?: boolean;
}

const INITIAL_ALERTS: Alert[] = [
  { id: "ALT-001", time: "2 hours ago", channel: "slack", regulation: "DPDP Act 2023", message: "CRITICAL: 72-hour breach notification obligation. DPO appointment absent.", riskScore: 9 },
  { id: "ALT-002", time: "4 hours ago", channel: "email", regulation: "DORA", message: "HIGH: TLPT testing requirement not covered. Deadline: Dec 31.", riskScore: 8 },
  { id: "ALT-003", time: "Yesterday", channel: "slack", regulation: "EU AI Act", message: "CRITICAL: Human oversight gap detected. No controls map to Art. 14.", riskScore: 10 },
];

interface Props {
  regulation: RegulationItem | null;
  analysisComplete: boolean;
  pipelineResult: PipelineResult | null;
}

export default function AlertsPanel({ regulation, analysisComplete, pipelineResult }: Props) {
  const [sendingSlack, setSendingSlack] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [slackSent, setSlackSent] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>(INITIAL_ALERTS);

  const canSend = !!(regulation && analysisComplete);
  const riskScore = pipelineResult?.overall_risk_score ?? (regulation?.severity === "Critical" ? 9 : 7);
  const gapsCount = pipelineResult?.gaps?.length ?? 4;
  const impactSummary = pipelineResult?.impact_summary ?? `${regulation?.severity ?? "High"} risk regulatory obligation detected in ${regulation?.jurisdiction}.`;

  const handleSlack = async () => {
    if (!regulation || !analysisComplete) return;
    setSendingSlack(true);
    const result = await sendSlackAlert({
      regulation_title: regulation.title,
      regulation_id: regulation.id,
      jurisdiction: regulation.jurisdiction,
      risk_score: riskScore,
      severity: regulation.severity,
      impact_summary: impactSummary,
      gaps_count: gapsCount,
    });
    const newAlert: Alert = {
      id: `ALT-${Date.now()}`,
      time: "Just now",
      channel: "slack",
      regulation: regulation.title.split("—")[0].trim(),
      message: `${regulation.severity.toUpperCase()}: ${impactSummary.slice(0, 120)}`,
      riskScore,
      demoMode: result?.demo_mode,
    };
    setAlerts((prev) => [newAlert, ...prev]);
    setSendingSlack(false);
    setSlackSent(true);
  };

  const handleEmail = async () => {
    if (!regulation || !analysisComplete) return;
    setSendingEmail(true);
    const result = await sendEmailAlert({
      regulation_title: regulation.title,
      regulation_id: regulation.id,
      jurisdiction: regulation.jurisdiction,
      risk_score: riskScore,
      severity: regulation.severity,
      impact_summary: impactSummary,
      recipient_email: process.env.NEXT_PUBLIC_ALERT_EMAIL || "compliance@redforge.ai",
    });
    const newAlert: Alert = {
      id: `ALT-${Date.now()}`,
      time: "Just now",
      channel: "email",
      regulation: regulation.title.split("—")[0].trim(),
      message: `${regulation.severity.toUpperCase()}: ${gapsCount} action items generated. Immediate review required.`,
      riskScore,
      demoMode: result?.demo_mode,
    };
    setAlerts((prev) => [newAlert, ...prev]);
    setSendingEmail(false);
    setEmailSent(true);
  };

  return (
    <div style={{ background: "#0D0D12", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, overflow: "hidden" }}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: "#EDEDEF" }}>Alert Notifications</span>
      </div>

      <div style={{ padding: "20px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 20 }}>
          <SendButton label="Slack Alert" icon={<SlackIcon />} sending={sendingSlack} sent={slackSent} disabled={!canSend} onClick={handleSlack} />
          <SendButton label="Email Alert" icon={<EmailIcon />} sending={sendingEmail} sent={emailSent} disabled={!canSend} onClick={handleEmail} />
        </div>

        {!canSend && (
          <div style={{ padding: "10px 14px", borderRadius: 8, background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: "#4A4C57", textAlign: "center" }}>Analyze a regulation to enable alert sending</div>
          </div>
        )}

        <div>
          <div style={{ fontSize: 11, color: "#4A4C57", textTransform: "uppercase", letterSpacing: "0.04em", fontWeight: 600, marginBottom: 10 }}>Recent Alerts</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {alerts.slice(0, 5).map((alert) => (
              <AlertRow key={alert.id} alert={alert} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function SendButton({ label, icon, sending, sent, disabled, onClick }: {
  label: string; icon: React.ReactNode; sending: boolean; sent: boolean; disabled: boolean; onClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      onClick={onClick}
      disabled={disabled || sending || sent}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
        padding: "14px 12px", borderRadius: 10, cursor: disabled ? "not-allowed" : "pointer",
        background: sent ? "rgba(34,197,94,0.06)" : disabled ? "rgba(255,255,255,0.02)" : hovered ? "rgba(255,255,255,0.05)" : "rgba(255,255,255,0.03)",
        border: sent ? "1px solid rgba(34,197,94,0.25)" : disabled ? "1px solid rgba(255,255,255,0.05)" : "1px solid rgba(255,255,255,0.1)",
        transition: "all .15s", outline: "none",
      }}
    >
      {sending ? (
        <div style={{ width: 18, height: 18, borderRadius: "50%", border: "2px solid rgba(255,255,255,0.2)", borderTopColor: "#EDEDEF", animation: "spin 0.8s linear infinite" }} />
      ) : sent ? <div style={{ width: 18, height: 18, borderRadius: "50%", background: "rgba(34,197,94,0.2)", border: "1px solid rgba(34,197,94,0.4)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, color: "#22C55E" }}>+</div> : (
        <div style={{ opacity: disabled ? 0.3 : 1 }}>{icon}</div>
      )}
      <span style={{ fontSize: 12, fontWeight: 500, color: sent ? "#22C55E" : disabled ? "#4A4C57" : "#8B8D97" }}>
        {sending ? "Sending..." : sent ? "Sent!" : label}
      </span>
      <style>{`@keyframes spin { to{transform:rotate(360deg)} }`}</style>
    </button>
  );
}

function AlertRow({ alert }: { alert: Alert }) {
  const riskColor = alert.riskScore >= 9 ? "#E5484D" : alert.riskScore >= 7 ? "#F59E0B" : "#8B5CF6";
  return (
    <div style={{ padding: "10px 14px", background: "rgba(0,0,0,0.2)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 8 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 10, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: "#4A4C57", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)", padding: "1px 5px", borderRadius: 3 }}>{alert.channel === "slack" ? "SLK" : "EML"}</span>
        <span style={{ fontSize: 12, fontWeight: 600, color: "#C4C6D0" }}>{alert.regulation}</span>
        <span style={{ fontSize: 10, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: riskColor, background: `${riskColor}15`, border: `1px solid ${riskColor}30`, padding: "1px 6px", borderRadius: 4 }}>R{alert.riskScore}</span>
        {alert.demoMode && <span style={{ fontSize: 9, color: "#4A4C57", border: "1px solid rgba(255,255,255,0.07)", padding: "1px 5px", borderRadius: 3 }}>demo</span>}
        <span style={{ fontSize: 10, color: "#4A4C57", marginLeft: "auto" }}>{alert.time}</span>
      </div>
      <div style={{ fontSize: 11, color: "#4A4C57", lineHeight: 1.5 }}>{alert.message}</div>
    </div>
  );
}

function SlackIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
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
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <rect x="2" y="4" width="20" height="16" rx="3" stroke="#E5484D" strokeWidth="1.5"/>
      <path d="M2 8l10 6 10-6" stroke="#E5484D" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  );
}
