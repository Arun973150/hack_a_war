/**
 * Red Forge API client for the demo dashboard.
 * All calls go to the FastAPI backend at API_BASE.
 * Each function gracefully returns null/empty on error — components fall back to mock data.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "rf-dev-key-2025";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    const finalHeaders = new Headers(init?.headers);
    finalHeaders.set("Content-Type", "application/json");
    finalHeaders.set("X-API-Key", API_KEY);
    
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: finalHeaders,
    });
    if (!res.ok) return null;
    return res.json() as Promise<T>;
  } catch {
    return null;
  }
}

// ─── Regulations ────────────────────────────────────────────────────────────

export interface SearchResult {
  score: number;
  text: string;
  section_title: string;
  jurisdiction?: string;
  regulatory_body?: string;
  document_type?: string;
  source_id?: string;
  published_date?: number;
}

export interface LiveFeedItem {
  id: string;
  title: string;
  body: string;
  jurisdiction: string;
  regulator: string;
  date: string;
  severity: "Critical" | "High" | "Medium" | "Low";
  sector: string;
  docType: string;
  rawText: string;
  sourceUrl?: string;
}

export async function fetchLiveFeed(jurisdiction?: string): Promise<LiveFeedItem[]> {
  const qs = jurisdiction && jurisdiction !== "All" ? `?jurisdiction=${encodeURIComponent(jurisdiction)}` : "";
  const data = await apiFetch<{ items: LiveFeedItem[]; total: number; live: boolean }>(
    `/api/v1/regulations/feed${qs}`,
  );
  return data?.items ?? [];
}

export async function searchRegulations(
  query: string,
  jurisdiction?: string,
  limit = 20,
): Promise<SearchResult[]> {
  const data = await apiFetch<{ results: SearchResult[]; total: number }>(
    "/api/v1/regulations/search",
    {
      method: "POST",
      body: JSON.stringify({ query, jurisdiction: jurisdiction || undefined, limit }),
    },
  );
  return data?.results ?? [];
}

export async function triggerPipeline(payload: {
  document_id: string;
  raw_text: string;
  source_url: string;
  jurisdiction: string;
  regulatory_body: string;
  document_type: string;
  published_date: string;
}): Promise<{ status: string; document_id: string } | null> {
  return apiFetch("/api/v1/regulations/process", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ─── SSE Streaming ──────────────────────────────────────────────────────────

export interface AgentEvent {
  type: "connected" | "agent_done" | "complete" | "error" | "timeout";
  node?: string;
  step?: number;
  logs?: string[];
  result?: PipelineResult;
  message?: string;
}

export interface SecurityAdvisory {
  cve_id: string;
  cvss_score: number;
  severity: string;
  description: string;
  category: string;
  cwes: string[];
  compliance_controls: string[];
  compliance_impact: { name: string; regulator: string; requirement: string; deadline_hours: number; action: string }[];
  remediation_steps: string[];
  priority: string;
  is_kev: boolean;
}

export interface PipelineResult {
  document_id: string;
  is_relevant: boolean;
  relevance_score: number;
  sector: string;
  obligations: Obligation[];
  affected_business_units: string[];
  gaps: Gap[];
  overall_risk_score: number;
  jurisdiction_conflicts: string[];
  impact_summary: string;
  action_items: ActionItem[];
  security_advisories: SecurityAdvisory[];
  validation: { valid: boolean; confidence: number; issues: string[] } | null;
  error?: string;
  auto_slack_sent?: boolean;
  auto_jira_tickets?: { action_id: string; jira_key: string; jira_url: string }[];
}

export interface Obligation {
  obligation_id: string;
  text: string;
  who_must_comply: string;
  what: string;
  deadline: string | null;
  penalty: string | null;
}

export interface Gap {
  obligation_id: string;
  gap_description: string;
  existing_controls: string[];
  coverage_pct: number;
  risk_score: number;
}

export interface ActionItem {
  action_id: string;
  title: string;
  description: string;
  owner: string;
  deadline: string;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  effort_days: number;
  compliance_risk_score: number;
  source_obligation_ids: string[];
}

export function streamPipeline(
  documentId: string,
  onEvent: (event: AgentEvent) => void,
): () => void {
  const es = new EventSource(`${API_BASE}/api/v1/stream/${documentId}`);
  es.onmessage = (e) => {
    try {
      const data: AgentEvent = JSON.parse(e.data);
      onEvent(data);
      if (data.type === "complete" || data.type === "timeout" || data.type === "error") {
        es.close();
      }
    } catch {}
  };
  es.onerror = () => {
    onEvent({ type: "error", message: "SSE connection lost" });
    es.close();
  };
  return () => es.close();
}

// ─── Actions ────────────────────────────────────────────────────────────────

export interface DBActionItem {
  action_id: string;
  title: string;
  description: string;
  owner: string;
  deadline: string;
  priority: string;
  effort_days: number;
  compliance_risk_score: number;
  status: string;
  jira_ticket_id: string | null;
  source_obligation_ids: string[];
  created_at: string | null;
}

export async function listActionItems(params?: {
  priority?: string;
  status?: string;
  owner?: string;
  limit?: number;
}): Promise<DBActionItem[]> {
  const qs = new URLSearchParams();
  if (params?.priority) qs.set("priority", params.priority);
  if (params?.status) qs.set("status", params.status);
  if (params?.owner) qs.set("owner", params.owner);
  if (params?.limit) qs.set("limit", String(params.limit));
  const data = await apiFetch<{ action_items: DBActionItem[] }>(
    `/api/v1/actions/?${qs.toString()}`,
  );
  return data?.action_items ?? [];
}

export async function exportToJira(
  actionIds: string[],
  projectKey?: string,
): Promise<{ created_tickets: { action_id: string; jira_key: string; jira_url: string }[] } | null> {
  return apiFetch("/api/v1/actions/export/jira", {
    method: "POST",
    body: JSON.stringify({ action_ids: actionIds, project_key: projectKey }),
  });
}

// ─── Controls & Gaps ────────────────────────────────────────────────────────

export interface GapSummaryItem {
  obligation_id: string;
  requirement: string;
  coverage_pct: number;
}

export async function getGapsSummary(): Promise<GapSummaryItem[]> {
  const data = await apiFetch<{ gaps: GapSummaryItem[] }>("/api/v1/controls/gaps/summary");
  return data?.gaps ?? [];
}

export interface DriftData {
  months: number[];
  current: number;
  total_controls: number;
  high_coverage_controls: number;
  jurisdiction: string;
}

export async function getComplianceDrift(jurisdiction?: string): Promise<DriftData | null> {
  const qs = jurisdiction && jurisdiction !== "All" ? `?jurisdiction=${jurisdiction}` : "";
  return apiFetch<DriftData>(`/api/v1/controls/drift${qs}`);
}

export interface ConflictData {
  conflicts: object[];
  total: number;
  from_graph?: boolean;
}

export async function getConflicts(): Promise<ConflictData | null> {
  return apiFetch<ConflictData>("/api/v1/controls/conflicts");
}

// ─── Org Profile ────────────────────────────────────────────────────────────

export interface OrgProfile {
  exists: boolean;
  company_name: string;
  sectors: string[];
  countries: string[];
  regulators: string[];
  company_size: string;
  annual_revenue_usd: number | null;
  description: string;
}

export async function fetchOrgProfile(): Promise<OrgProfile | null> {
  return apiFetch<OrgProfile>("/api/v1/org/profile");
}

export async function saveOrgProfile(profile: {
  company_name: string;
  sectors: string[];
  countries: string[];
  regulators: string[];
  company_size?: string;
  annual_revenue_usd?: number | null;
  description?: string;
}): Promise<{ status: string } | null> {
  return apiFetch("/api/v1/org/profile", {
    method: "POST",
    body: JSON.stringify(profile),
  });
}

// ─── File Upload ─────────────────────────────────────────────────────────────

export interface UploadedControl {
  control_id: string;
  name: string;
  framework: string;
  status: "registered" | "error";
  error?: string;
}

export async function uploadControlFile(file: File): Promise<{
  registered: UploadedControl[];
  total: number;
  method: string;
  filename: string;
  error?: string;
} | null> {
  try {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/v1/org/import-controls`, {
      method: "POST",
      headers: { "X-API-Key": API_KEY },
      body: form,
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => res.statusText);
      return { registered: [], total: 0, method: "error", filename: file.name, error: `Upload error ${res.status}: ${detail}` };
    }
    return res.json();
  } catch (e: any) {
    return { registered: [], total: 0, method: "error", filename: file.name, error: `fetch error: ${e.message}` };
  }
}

// ─── Alerts ──────────────────────────────────────────────────────────────────

export async function sendSlackAlert(payload: {
  regulation_title: string;
  regulation_id: string;
  jurisdiction: string;
  risk_score: number;
  severity: string;
  impact_summary: string;
  gaps_count: number;
}): Promise<{ sent: boolean; demo_mode?: boolean } | null> {
  return apiFetch("/api/v1/alerts/slack", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function sendEmailAlert(payload: {
  regulation_title: string;
  regulation_id: string;
  jurisdiction: string;
  risk_score: number;
  severity: string;
  impact_summary: string;
  recipient_email: string;
}): Promise<{ sent: boolean; demo_mode?: boolean } | null> {
  return apiFetch("/api/v1/alerts/email", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ─── CVE Intelligence API ─────────────────────────────────────────────────────

export interface BlastRadiusBreakdown {
  framework: string;
  full_name: string;
  jurisdiction: string;
  regulator: string;
  fine_native_currency: string;
  fine_native_amount: number;
  fine_usd: number;
  fine_label: string;
  deadline_hours: number;
  regulations_triggered: string[];
}

export interface BlastRadius {
  cve_id: string;
  total_exposure_usd: number;
  worst_single_fine_usd: number;
  obligations_triggered: number;
  jurisdictions_triggered: string[];
  jurisdictions_count: number;
  earliest_deadline_hours: number;
  revenue_based: boolean;
  breakdown: BlastRadiusBreakdown[];
  summary: string;
}

export interface CveAlert {
  cve_id: string;
  severity: string;
  cvss_score: number;
  category: string;
  description: string;
  affected_packages: { name: string; version: string; ecosystem: string; fixed_version?: string }[];
  compliance_impact: { name: string; regulator: string; requirement: string; deadline_hours: number; action: string }[];
  blast_radius: BlastRadius;
  remediation_steps: string[];
  is_kev: boolean;
  slack_sent: boolean;
  jira_key: string | null;
  first_seen: string | null;
}

export interface RegulationDiff {
  source_id: string;
  has_changes: boolean;
  severity: "none" | "minor" | "major" | "critical";
  summary: string;
  new_obligations: { obligation_id: string; text: string; deadline: string; penalty: string }[];
  removed_obligations: { obligation_id: string; text: string }[];
  changed_obligations: { obligation_id: string; changes: Record<string, { from: string; to: string }> }[];
  title?: string;
  jurisdiction?: string;
  current_version?: string;
  previous_version?: string;
  current_date?: string;
  previous_date?: string;
  obligations_count?: number;
}

export interface SuggestFixResult {
  cve_id: string;
  priority: string;
  severity: string;
  cvss_score: number;
  category: string;
  description: string;
  cwes: string[];
  patch: {
    action: string;
    command?: string;
    fixed_version?: string;
    current_version?: string;
    message?: string;
  };
  remediation_steps: string[];
  compliance_obligations: { name: string; regulator: string; requirement: string; deadline_hours: number; action: string }[];
  compliance_controls_affected: string[];
  blast_radius: BlastRadius;
  is_kev: boolean;
}

export async function fetchCveAlerts(params?: {
  severity?: string;
  unnotified_only?: boolean;
  limit?: number;
}): Promise<CveAlert[]> {
  const qs = new URLSearchParams();
  if (params?.severity) qs.set("severity", params.severity);
  if (params?.unnotified_only) qs.set("unnotified_only", "true");
  if (params?.limit) qs.set("limit", String(params.limit));
  const data = await apiFetch<{ alerts: CveAlert[]; total: number }>(
    `/api/v1/cve/alerts?${qs.toString()}`,
  );
  return data?.alerts ?? [];
}

export async function triggerScanNow(): Promise<{
  status: string;
  scanned_packages: number;
  new_cves: number;
  cves: CveAlert[];
} | null> {
  return apiFetch("/api/v1/cve/scan-now", { method: "POST" });
}

export async function fetchRegulationDiffs(limit = 20): Promise<RegulationDiff[]> {
  const data = await apiFetch<{ diffs: RegulationDiff[]; total: number; sources_tracked: number }>(
    `/api/v1/cve/regulation-diffs?limit=${limit}`,
  );
  return data?.diffs ?? [];
}

export async function fetchRegulationDiff(sourceId: string): Promise<RegulationDiff | null> {
  return apiFetch<RegulationDiff>(`/api/v1/cve/regulation-diff/${encodeURIComponent(sourceId)}`);
}

export async function suggestFix(payload: {
  cve_id: string;
  package_name?: string;
  package_version?: string;
  ecosystem?: string;
  jurisdiction?: string;
  org_annual_revenue_usd?: number;
}): Promise<SuggestFixResult | null> {
  return apiFetch("/api/v1/cve/suggest-fix", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function calculateBlastRadius(payload: {
  cve_id: string;
  cwes?: string[];
  description?: string;
  cvss_score?: number;
  org_annual_revenue_usd?: number;
}): Promise<BlastRadius | null> {
  return apiFetch("/api/v1/cve/blast-radius", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function uploadStackFile(file: File, replaceExisting = false): Promise<{
  filename: string;
  parsed_packages: number;
  newly_registered: number;
  total_monitored: number;
  error?: string;
} | null> {
  try {
    const form = new FormData();
    form.append("file", file);
    const headers = new Headers();
    headers.set("X-API-Key", API_KEY);
    
    const res = await fetch(
      `${API_BASE}/api/v1/cve/upload-stack?replace_existing=${replaceExisting}`,
      { method: "POST", headers, body: form },
    );
    if (!res.ok) {
      return { filename: "", parsed_packages: 0, newly_registered: 0, total_monitored: 0, error: `backend error: ${res.status} ${res.statusText}` };
    }
    return res.json();
  } catch (e: any) {
    return { filename: "", parsed_packages: 0, newly_registered: 0, total_monitored: 0, error: `fetch error: ${e.message}` };
  }
}

export async function askQuestion(
  question: string,
  jurisdiction?: string,
): Promise<{ answer: string; sources: any[]; controls_referenced: string[] } | null> {
  const data = await apiFetch<{ answer: string; sources: any[]; controls_referenced: string[] }>("/api/v1/ask", {
    method: "POST",
    body: JSON.stringify({ question, jurisdiction: jurisdiction && jurisdiction !== "All" ? jurisdiction : undefined }),
  });
  return data;
}
