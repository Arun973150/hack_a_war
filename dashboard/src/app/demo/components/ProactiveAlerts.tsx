"use client";

import { useState, useEffect, useCallback } from "react";
import {
  fetchCveAlerts,
  triggerScanNow,
  fetchRegulationDiffs,
  uploadStackFile,
  CveAlert,
  RegulationDiff,
} from "../lib/api";

// ─── Severity colour map ──────────────────────────────────────────────────────
const SEV: Record<string, { bg: string; text: string; border: string }> = {
  CRITICAL: { bg: "rgba(229,72,77,0.1)", text: "#E5484D", border: "rgba(229,72,77,0.3)" },
  HIGH:     { bg: "rgba(245,158,11,0.1)", text: "#F59E0B", border: "rgba(245,158,11,0.3)" },
  MEDIUM:   { bg: "rgba(139,92,246,0.1)", text: "#8B5CF6", border: "rgba(139,92,246,0.3)" },
  LOW:      { bg: "rgba(34,197,94,0.1)",  text: "#22C55E", border: "rgba(34,197,94,0.3)"  },
};

const DIFF_SEV: Record<string, { text: string; label: string }> = {
  critical: { text: "#E5484D", label: "CRITICAL CHANGE" },
  major:    { text: "#F59E0B", label: "MAJOR CHANGE" },
  minor:    { text: "#8B5CF6", label: "MINOR UPDATE" },
  none:     { text: "#6B6C74", label: "UNCHANGED" },
};

// ─── Tab ─────────────────────────────────────────────────────────────────────
type Tab = "cve" | "diffs";

export default function ProactiveAlerts() {
  const [tab, setTab] = useState<Tab>("cve");
  const [alerts, setAlerts] = useState<CveAlert[]>([]);
  const [diffs, setDiffs] = useState<RegulationDiff[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<{ new_cves: number; scanned_packages: number } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [loadingAlerts, setLoadingAlerts] = useState(true);

  const loadData = useCallback(async () => {
    setLoadingAlerts(true);
    const [cveData, diffData] = await Promise.all([
      fetchCveAlerts({ limit: 30 }),
      fetchRegulationDiffs(15),
    ]);
    setAlerts(cveData);
    setDiffs(diffData);
    setLoadingAlerts(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  async function handleScanNow() {
    setScanning(true);
    setScanResult(null);
    const res = await triggerScanNow();
    if (res) setScanResult({ new_cves: res.new_cves, scanned_packages: res.scanned_packages });
    await loadData();
    setScanning(false);
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg("");
    const res = await uploadStackFile(file, false);
    if (res) {
      setUploadMsg(`Registered ${res.newly_registered} new packages (${res.total_monitored} total monitored)`);
      await loadData();
    } else {
      setUploadMsg("Upload failed. Check file format.");
    }
    setUploading(false);
    e.target.value = "";
  }

  return (
    <div style={{ background: "#0D0D12", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, overflow: "hidden" }}>
      {/* Header */}
      <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 20, height: 20, borderRadius: 4, background: "rgba(229,72,77,0.15)", border: "1px solid rgba(229,72,77,0.3)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "#E5484D" }}>
            ⚡
          </div>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#EDEDEF" }}>Proactive Monitoring</span>
          <span style={{ fontSize: 10, color: "#22C55E", fontWeight: 600 }}>● LIVE</span>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {/* Upload stack file */}
          <label style={{
            fontSize: 11, fontWeight: 600, color: "#8B8D97",
            background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: 6, padding: "4px 10px", cursor: "pointer",
          }}>
            {uploading ? "Uploading…" : "Upload Stack File"}
            <input type="file" accept=".txt,.json" style={{ display: "none" }} onChange={handleUpload} />
          </label>
          <button
            onClick={handleScanNow}
            disabled={scanning}
            style={{
              fontSize: 11, fontWeight: 600,
              background: scanning ? "rgba(255,255,255,0.04)" : "rgba(34,197,94,0.1)",
              color: scanning ? "#6B6C74" : "#22C55E",
              border: `1px solid ${scanning ? "rgba(255,255,255,0.1)" : "rgba(34,197,94,0.3)"}`,
              borderRadius: 6, padding: "4px 12px", cursor: scanning ? "default" : "pointer",
            }}
          >
            {scanning ? "Scanning…" : "Scan Now"}
          </button>
        </div>
      </div>

      {/* Upload / scan feedback */}
      {(uploadMsg || scanResult) && (
        <div style={{ padding: "8px 20px", background: "rgba(34,197,94,0.05)", borderBottom: "1px solid rgba(34,197,94,0.15)", fontSize: 11, color: "#22C55E" }}>
          {uploadMsg && <span>{uploadMsg}</span>}
          {scanResult && (
            <span>Scan complete — {scanResult.scanned_packages} packages checked, {scanResult.new_cves} new CVE{scanResult.new_cves !== 1 ? "s" : ""} found</span>
          )}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
        {(["cve", "diffs"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{
            flex: 1, padding: "10px 16px", fontSize: 12, fontWeight: 600, cursor: "pointer", outline: "none",
            background: tab === t ? "rgba(255,255,255,0.04)" : "transparent",
            color: tab === t ? "#EDEDEF" : "#6B6C74",
            borderBottom: tab === t ? "2px solid #E5484D" : "2px solid transparent",
            border: "none", borderBottomColor: tab === t ? "#E5484D" : "transparent",
            transition: "all .15s",
          }}>
            {t === "cve"
              ? `CVE Alerts ${alerts.length > 0 ? `(${alerts.length})` : ""}`
              : `Regulation Diffs ${diffs.length > 0 ? `(${diffs.length})` : ""}`
            }
          </button>
        ))}
      </div>

      <div style={{ padding: 20 }}>
        {loadingAlerts ? (
          <div style={{ textAlign: "center", padding: "32px 0", color: "#6B6C74", fontSize: 12 }}>Loading…</div>
        ) : tab === "cve" ? (
          <CveAlertsTab alerts={alerts} expanded={expanded} setExpanded={setExpanded} />
        ) : (
          <RegDiffsTab diffs={diffs} expanded={expanded} setExpanded={setExpanded} />
        )}
      </div>
    </div>
  );
}

// ─── CVE Alerts Tab ──────────────────────────────────────────────────────────

function CveAlertsTab({
  alerts, expanded, setExpanded,
}: { alerts: CveAlert[]; expanded: string | null; setExpanded: (id: string | null) => void }) {
  if (alerts.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "32px 0", color: "#6B6C74", fontSize: 12 }}>
        No CVE alerts yet. Upload a requirements.txt and click "Scan Now" to start proactive monitoring.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {alerts.map((alert) => {
        const sev = SEV[alert.severity] || SEV.MEDIUM;
        const isExpanded = expanded === alert.cve_id;
        const blast = alert.blast_radius;

        return (
          <div key={alert.cve_id} style={{ border: `1px solid ${isExpanded ? sev.border : "rgba(255,255,255,0.07)"}`, borderRadius: 8, overflow: "hidden", background: isExpanded ? sev.bg : "transparent" }}>
            {/* Row */}
            <button
              onClick={() => setExpanded(isExpanded ? null : alert.cve_id)}
              style={{ width: "100%", padding: "10px 14px", display: "flex", alignItems: "center", gap: 10, background: "transparent", border: "none", cursor: "pointer", textAlign: "left" }}
            >
              {/* KEV badge */}
              {alert.is_kev && (
                <span style={{ fontSize: 9, fontWeight: 700, background: "rgba(229,72,77,0.2)", color: "#E5484D", border: "1px solid rgba(229,72,77,0.4)", borderRadius: 3, padding: "1px 4px", flexShrink: 0 }}>KEV</span>
              )}
              {/* CVE ID */}
              <span style={{ fontSize: 12, fontWeight: 700, color: sev.text, flexShrink: 0, fontFamily: "monospace" }}>{alert.cve_id}</span>
              {/* Severity badge */}
              <span style={{ fontSize: 10, fontWeight: 700, background: sev.bg, color: sev.text, border: `1px solid ${sev.border}`, borderRadius: 4, padding: "1px 6px", flexShrink: 0 }}>
                CVSS {alert.cvss_score.toFixed(1)}
              </span>
              {/* Category */}
              <span style={{ fontSize: 11, color: "#8B8D97", flex: 1 }}>{alert.category}</span>
              {/* Blast radius teaser */}
              {blast && (
                <span style={{ fontSize: 11, fontWeight: 600, color: "#F59E0B", flexShrink: 0 }}>
                  ${(blast.total_exposure_usd / 1000).toFixed(0)}K exposure
                </span>
              )}
              {/* Notified status */}
              {alert.slack_sent && (
                <span style={{ fontSize: 10, color: "#22C55E", flexShrink: 0 }}>✓ Notified</span>
              )}
              <span style={{ color: "#6B6C74", fontSize: 12, flexShrink: 0 }}>{isExpanded ? "▲" : "▼"}</span>
            </button>

            {/* Expanded detail */}
            {isExpanded && (
              <div style={{ padding: "0 14px 14px", display: "flex", flexDirection: "column", gap: 10 }}>
                {/* Description */}
                <p style={{ fontSize: 12, color: "#8B8D97", lineHeight: 1.6, margin: 0 }}>{alert.description}</p>

                {/* Affected packages */}
                {alert.affected_packages?.length > 0 && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: sev.text, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>Affected Packages</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                      {alert.affected_packages.map((p, i) => (
                        <span key={i} style={{ fontSize: 11, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 4, padding: "2px 8px", color: "#EDEDEF", fontFamily: "monospace" }}>
                          {p.name}@{p.version}
                          {p.fixed_version && <span style={{ color: "#22C55E" }}> → {p.fixed_version}</span>}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Blast radius */}
                {blast && (
                  <BlastRadiusCard blast={blast} />
                )}

                {/* Compliance obligations */}
                {alert.compliance_impact?.length > 0 && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: sev.text, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>Compliance Obligations Triggered</div>
                    {alert.compliance_impact.map((ob, i) => (
                      <div key={i} style={{ padding: "8px 10px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 6, marginBottom: 4 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                          <span style={{ fontSize: 11, fontWeight: 600, color: "#EDEDEF" }}>{ob.name}</span>
                          <span style={{ fontSize: 10, fontWeight: 700, color: ob.deadline_hours <= 24 ? "#E5484D" : "#F59E0B", background: ob.deadline_hours <= 24 ? "rgba(229,72,77,0.1)" : "rgba(245,158,11,0.1)", borderRadius: 4, padding: "1px 6px" }}>
                            ⏰ {ob.deadline_hours}h
                          </span>
                        </div>
                        <div style={{ fontSize: 11, color: "#6B6C74" }}>{ob.action}</div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Remediation steps */}
                {alert.remediation_steps?.length > 0 && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#22C55E", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>Remediation Steps</div>
                    <ol style={{ margin: 0, padding: "0 0 0 16px" }}>
                      {alert.remediation_steps.map((step, i) => (
                        <li key={i} style={{ fontSize: 12, color: "#8B8D97", lineHeight: 1.7 }}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {/* Jira link */}
                {alert.jira_key && (
                  <div style={{ fontSize: 11, color: "#6B6C74" }}>
                    Jira: <span style={{ color: "#EDEDEF", fontFamily: "monospace" }}>{alert.jira_key}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Blast Radius Card ───────────────────────────────────────────────────────

function BlastRadiusCard({ blast }: { blast: ReturnType<typeof fetchCveAlerts> extends Promise<(infer T)[]> ? T extends { blast_radius: infer B } ? B : never : never }) {
  const [showBreakdown, setShowBreakdown] = useState(false);
  // Use a simpler type since we can't easily infer it above
  const b = blast as any;
  if (!b) return null;

  return (
    <div style={{ border: "1px solid rgba(245,158,11,0.25)", borderRadius: 8, overflow: "hidden" }}>
      <button
        onClick={() => setShowBreakdown(!showBreakdown)}
        style={{ width: "100%", padding: "10px 14px", background: "rgba(245,158,11,0.05)", border: "none", cursor: "pointer", textAlign: "left", display: "flex", alignItems: "center", justifyContent: "space-between" }}
      >
        <div>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#F59E0B", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 2 }}>
            Cross-CVE Blast Radius
          </div>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#EDEDEF" }}>
            ${b.total_exposure_usd?.toLocaleString()} USD
            <span style={{ fontSize: 11, fontWeight: 400, color: "#8B8D97", marginLeft: 8 }}>
              {b.jurisdictions_count} jurisdiction{b.jurisdictions_count !== 1 ? "s" : ""} · {b.obligations_triggered} obligation{b.obligations_triggered !== 1 ? "s" : ""} · ⏰ {b.earliest_deadline_hours}h
            </span>
          </div>
        </div>
        <span style={{ color: "#6B6C74", fontSize: 12 }}>{showBreakdown ? "▲" : "▼"}</span>
      </button>

      {showBreakdown && b.breakdown?.length > 0 && (
        <div style={{ padding: "0 14px 12px" }}>
          <p style={{ fontSize: 11, color: "#8B8D97", margin: "8px 0 10px", lineHeight: 1.6 }}>{b.summary}</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {b.breakdown.map((row: any, i: number) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 10px", background: "rgba(255,255,255,0.02)", borderRadius: 6 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: "#EDEDEF" }}>{row.framework}</div>
                  <div style={{ fontSize: 10, color: "#6B6C74" }}>{row.jurisdiction} · {row.regulator}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "#F59E0B" }}>${row.fine_usd?.toLocaleString()}</div>
                  <div style={{ fontSize: 10, color: "#6B6C74" }}>⏰ {row.deadline_hours}h</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Regulation Diffs Tab ────────────────────────────────────────────────────

function RegDiffsTab({
  diffs, expanded, setExpanded,
}: { diffs: RegulationDiff[]; expanded: string | null; setExpanded: (id: string | null) => void }) {
  if (diffs.length === 0) {
    return (
      <div style={{ textAlign: "center", padding: "32px 0", color: "#6B6C74", fontSize: 12 }}>
        No regulation diffs yet. Process regulations through the pipeline to start tracking changes.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {diffs.map((diff) => {
        const ds = DIFF_SEV[diff.severity] || DIFF_SEV.minor;
        const isExpanded = expanded === diff.source_id;

        return (
          <div key={diff.source_id} style={{ border: `1px solid ${isExpanded ? "rgba(245,158,11,0.3)" : "rgba(255,255,255,0.07)"}`, borderRadius: 8, overflow: "hidden" }}>
            <button
              onClick={() => setExpanded(isExpanded ? null : diff.source_id)}
              style={{ width: "100%", padding: "10px 14px", display: "flex", alignItems: "center", gap: 10, background: "transparent", border: "none", cursor: "pointer", textAlign: "left" }}
            >
              <span style={{ fontSize: 10, fontWeight: 700, color: ds.text, textTransform: "uppercase", flexShrink: 0 }}>{ds.label}</span>
              <span style={{ fontSize: 12, fontWeight: 500, color: "#EDEDEF", flex: 1 }}>
                {diff.title || diff.source_id.split("/").pop() || diff.source_id}
              </span>
              {diff.jurisdiction && (
                <span style={{ fontSize: 10, color: "#8B8D97", flexShrink: 0 }}>{diff.jurisdiction}</span>
              )}
              <span style={{ fontSize: 11, color: "#8B8D97", flexShrink: 0 }}>{diff.summary}</span>
              <span style={{ color: "#6B6C74", fontSize: 12 }}>{isExpanded ? "▲" : "▼"}</span>
            </button>

            {isExpanded && (
              <div style={{ padding: "0 14px 14px", display: "flex", flexDirection: "column", gap: 10 }}>
                {/* Metadata */}
                <div style={{ display: "flex", gap: 16, fontSize: 11, color: "#6B6C74" }}>
                  {diff.current_date && <span>Latest: {new Date(diff.current_date).toLocaleDateString()}</span>}
                  {diff.previous_date && <span>Previous: {new Date(diff.previous_date).toLocaleDateString()}</span>}
                  {diff.obligations_count !== undefined && <span>{diff.obligations_count} obligations tracked</span>}
                </div>

                {/* New obligations */}
                {diff.new_obligations?.length > 0 && (
                  <DiffSection label="New Obligations Added" color="#22C55E" items={diff.new_obligations.map(o => ({
                    id: o.obligation_id,
                    text: o.text,
                    meta: o.deadline ? `Deadline: ${o.deadline}` : undefined,
                  }))} />
                )}

                {/* Removed obligations */}
                {diff.removed_obligations?.length > 0 && (
                  <DiffSection label="Obligations Removed" color="#E5484D" items={diff.removed_obligations.map(o => ({
                    id: o.obligation_id,
                    text: o.text,
                  }))} />
                )}

                {/* Changed obligations */}
                {diff.changed_obligations?.length > 0 && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#F59E0B", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>
                      Changed Obligations ({diff.changed_obligations.length})
                    </div>
                    {diff.changed_obligations.map((ch, i) => (
                      <div key={i} style={{ padding: "8px 10px", background: "rgba(245,158,11,0.04)", border: "1px solid rgba(245,158,11,0.15)", borderRadius: 6, marginBottom: 4 }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color: "#EDEDEF", marginBottom: 4, fontFamily: "monospace" }}>{ch.obligation_id}</div>
                        {Object.entries(ch.changes).map(([field, change]) => (
                          <div key={field} style={{ marginBottom: 3 }}>
                            <span style={{ fontSize: 10, color: "#F59E0B", fontWeight: 600, textTransform: "capitalize" }}>{field}: </span>
                            <span style={{ fontSize: 11, color: "#E5484D", textDecoration: "line-through" }}>{change.from || "(empty)"}</span>
                            <span style={{ fontSize: 11, color: "#6B6C74" }}> → </span>
                            <span style={{ fontSize: 11, color: "#22C55E" }}>{change.to || "(empty)"}</span>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function DiffSection({ label, color, items }: {
  label: string;
  color: string;
  items: { id: string; text: string; meta?: string }[];
}) {
  return (
    <div>
      <div style={{ fontSize: 10, fontWeight: 700, color, textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 6 }}>
        {label} ({items.length})
      </div>
      {items.map((item, i) => (
        <div key={i} style={{ padding: "6px 10px", background: `${color}08`, border: `1px solid ${color}20`, borderRadius: 6, marginBottom: 3 }}>
          <div style={{ fontSize: 10, fontFamily: "monospace", color, marginBottom: 2 }}>{item.id}</div>
          <div style={{ fontSize: 11, color: "#8B8D97", lineHeight: 1.5 }}>{item.text}</div>
          {item.meta && <div style={{ fontSize: 10, color, marginTop: 2 }}>{item.meta}</div>}
        </div>
      ))}
    </div>
  );
}
