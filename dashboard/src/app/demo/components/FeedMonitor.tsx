"use client";

import { useState, useEffect, useCallback } from "react";
import { Jurisdiction } from "./JurisdictionFilter";
import { fetchLiveFeed, searchRegulations, SearchResult, LiveFeedItem } from "../lib/api";

export interface RegulationItem {
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
}

// Fallback mock data used when Qdrant is empty or backend is down
const MOCK_REGULATIONS: RegulationItem[] = [
  {
    id: "REG-2024-001", title: "EU AI Act — High-Risk System Obligations",
    body: "Providers of high-risk AI systems must implement conformity assessment procedures and maintain technical documentation for 10 years post-market.",
    jurisdiction: "EU", regulator: "European Commission", date: "2024-08-01",
    severity: "Critical", sector: "Technology", docType: "Regulation",
    rawText: "EU AI Act Article 9: Providers of high-risk AI systems shall establish, implement, document and maintain a risk management system for 10 years. Human oversight measures must allow overseers to intervene. Conformity assessment mandatory before market placement.",
  },
  {
    id: "REG-2024-002", title: "SEC Cybersecurity Disclosure Rules",
    body: "Public companies must disclose material cybersecurity incidents within 4 business days and annually report cybersecurity risk management strategy.",
    jurisdiction: "US", regulator: "SEC", date: "2024-09-05",
    severity: "High", sector: "Financial Services", docType: "Rule",
    rawText: "SEC Rule 17a-4 amendment: Registrants must disclose material cybersecurity incidents on Form 8-K within four business days of determination. Annual disclosure of cybersecurity risk management, strategy, and governance required on Form 10-K.",
  },
  {
    id: "REG-2024-003", title: "DPDP Act — Data Fiduciary Obligations",
    body: "Data fiduciaries must appoint a Data Protection Officer, implement consent mechanisms, and report data breaches within 72 hours.",
    jurisdiction: "India", regulator: "MeitY", date: "2024-07-15",
    severity: "Critical", sector: "All Sectors", docType: "Act",
    rawText: "Digital Personal Data Protection Act 2023: Every significant data fiduciary shall appoint a Data Protection Officer. Personal data breaches must be reported to the Data Protection Board within 72 hours. Consent mechanisms must be granular and revocable.",
  },
  {
    id: "REG-2024-004", title: "DORA — ICT Risk Management Framework",
    body: "Financial entities must establish ICT risk management frameworks, conduct TLPT testing annually, and report major ICT incidents within 4 hours.",
    jurisdiction: "EU", regulator: "EBA / ESMA", date: "2024-01-17",
    severity: "Critical", sector: "Financial Services", docType: "Regulation",
    rawText: "Digital Operational Resilience Act: Financial entities must implement comprehensive ICT risk management frameworks. Threat-led penetration testing (TLPT) required annually for significant entities. Major ICT incidents reported to competent authority within 4 hours of classification.",
  },
  {
    id: "REG-2024-005", title: "RBI Digital Lending Guidelines Update",
    body: "Regulated entities must ensure all loan disbursals and repayments flow directly between borrower bank accounts and lenders.",
    jurisdiction: "India", regulator: "RBI", date: "2024-06-20",
    severity: "High", sector: "Banking", docType: "Circular",
    rawText: "RBI Circular DOR.CRE.REC.66/21.07.001/2022-23: All loan disbursals and repayments shall be executed only between the bank accounts of borrower and the Regulated Entity. Lending Service Providers prohibited from handling loan funds.",
  },
  {
    id: "REG-2024-006", title: "FTC Safeguards Rule — Expanded Scope",
    body: "Non-banking financial institutions must implement comprehensive information security programs covering encryption, access controls, and incident response.",
    jurisdiction: "US", regulator: "FTC", date: "2024-10-12",
    severity: "High", sector: "Financial Services", docType: "Rule",
    rawText: "FTC Safeguards Rule 16 CFR Part 314 amendment: Non-banking financial institutions covered under Gramm-Leach-Bliley Act must implement encryption of customer information, multi-factor authentication, and incident response plans within 180 days.",
  },
  {
    id: "REG-2024-007", title: "NIS2 Directive — Essential Entity Requirements",
    body: "Essential entities must implement risk management measures including supply chain security, encryption, and multi-factor authentication.",
    jurisdiction: "EU", regulator: "ENISA", date: "2024-10-17",
    severity: "High", sector: "Critical Infrastructure", docType: "Directive",
    rawText: "NIS2 Directive 2022/2555: Essential entities must implement measures on risk analysis, incident handling, business continuity, supply chain security, encryption, and multi-factor authentication. Significant incidents reported within 24 hours.",
  },
  {
    id: "REG-2024-008", title: "SEBI Cybersecurity & Cyber Resilience Framework",
    body: "Market infrastructure institutions must achieve CSCRF compliance and establish 24/7 SOC capabilities by Q1 2025.",
    jurisdiction: "India", regulator: "SEBI", date: "2024-08-20",
    severity: "Medium", sector: "Capital Markets", docType: "Circular",
    rawText: "SEBI Circular SEBI/HO/ITD/ITD-PoD-2/P/CIR/2023/193: All Market Infrastructure Institutions and Registered Intermediaries must comply with Cybersecurity and Cyber Resilience Framework. Quarterly vulnerability assessments and 24x7 SOC mandatory by Q1 2025.",
  },
];

const SEVERITY_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  Critical: { bg: "rgba(229,72,77,0.12)", text: "#E5484D", dot: "#E5484D" },
  High: { bg: "rgba(245,158,11,0.12)", text: "#F59E0B", dot: "#F59E0B" },
  Medium: { bg: "rgba(139,92,246,0.12)", text: "#8B5CF6", dot: "#8B5CF6" },
  Low: { bg: "rgba(34,197,94,0.12)", text: "#22C55E", dot: "#22C55E" },
};

const JURISDICTION_COLORS: Record<string, string> = {
  US: "#3B82F6", EU: "#6366F1", India: "#F59E0B",
};

function mapSearchResultToRegItem(r: SearchResult, idx: number): RegulationItem {
  // Map Qdrant search result to RegulationItem shape
  const jur = (r.jurisdiction || "US") as string;
  const riskScore = r.score ?? 0.5;
  const severity: RegulationItem["severity"] =
    riskScore > 0.85 ? "Critical" : riskScore > 0.7 ? "High" : riskScore > 0.5 ? "Medium" : "Low";

  return {
    id: r.source_id || `LIVE-${idx + 1}`,
    title: r.section_title || "Untitled Regulation",
    body: r.text?.slice(0, 200) || "",
    jurisdiction: jur,
    regulator: r.regulatory_body || "Unknown",
    date: (() => { try { const d = new Date((r.published_date || 0) * 1000); return isNaN(d.getTime()) || d.getFullYear() < 2000 ? "2024" : d.toISOString().slice(0, 10); } catch { return "2024"; } })(),
    severity,
    sector: "Financial Services",
    docType: r.document_type || "Regulation",
    rawText: r.text || "",
  };
}

interface Props {
  filter: Jurisdiction;
  selectedId: string | null;
  onSelect: (reg: RegulationItem) => void;
}

export default function FeedMonitor({ filter, selectedId, onSelect }: Props) {
  const [regulations, setRegulations] = useState<RegulationItem[]>(MOCK_REGULATIONS);
  const [loading, setLoading] = useState(false);
  const [isLive, setIsLive] = useState(false);

  const fetchFeed = useCallback(async () => {
    setLoading(true);

    // Try live feed first (Federal Register + EUR-Lex + SEBI)
    const jurisdiction = filter === "All" ? undefined : filter;
    const liveItems = await fetchLiveFeed(jurisdiction);

    if (liveItems.length > 0) {
      const mapped: RegulationItem[] = liveItems.map((item: LiveFeedItem) => ({
        id: item.id,
        title: item.title,
        body: item.body,
        jurisdiction: item.jurisdiction,
        regulator: item.regulator,
        date: item.date,
        severity: item.severity,
        sector: item.sector,
        docType: item.docType,
        rawText: item.rawText,
      }));
      setRegulations(mapped);
      setIsLive(true);
      setLoading(false);
      return;
    }

    // Fallback: try Qdrant semantic search
    const query = filter === "All"
      ? "regulatory compliance obligations financial services technology"
      : `${filter} regulatory compliance obligations`;
    const results = await searchRegulations(query, filter !== "All" ? filter : undefined, 20);

    if (results.length > 0) {
      setRegulations(results.map(mapSearchResultToRegItem));
      setIsLive(true);
    } else {
      // Last resort: mock data
      const filtered = filter === "All"
        ? MOCK_REGULATIONS
        : MOCK_REGULATIONS.filter((r) => r.jurisdiction === filter);
      setRegulations(filtered);
      setIsLive(false);
    }
    setLoading(false);
  }, [filter]);

  useEffect(() => {
    fetchFeed();
  }, [fetchFeed]);

  const displayed = filter === "All" || isLive
    ? regulations
    : regulations.filter((r) => r.jurisdiction === filter);

  return (
    <div style={{
      background: "#0D0D12",
      border: "1px solid rgba(255,255,255,0.07)",
      borderRadius: 12,
      overflow: "hidden",
      display: "flex",
      flexDirection: "column",
      height: "100%",
    }}>
      {/* Header */}
      <div style={{
        padding: "16px 20px",
        borderBottom: "1px solid rgba(255,255,255,0.07)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: isLive ? "#22C55E" : "#F59E0B",
            boxShadow: `0 0 8px ${isLive ? "rgba(34,197,94,0.6)" : "rgba(245,158,11,0.5)"}`,
            animation: "feedpulse 2s infinite",
          }} />
          <span style={{ fontSize: 13, fontWeight: 600, color: "#EDEDEF" }}>Regulatory Feed</span>
          {isLive && (
            <span style={{ fontSize: 10, color: "#22C55E", fontWeight: 600 }}>LIVE · FR / EUR-Lex / SEBI</span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {loading && (
            <div style={{
              width: 12, height: 12, borderRadius: "50%",
              border: "1.5px solid rgba(255,255,255,0.2)", borderTopColor: "#E5484D",
              animation: "spin 0.8s linear infinite",
            }} />
          )}
          <span style={{
            fontSize: 11, fontWeight: 600,
            background: "rgba(229,72,77,0.1)", color: "#E5484D",
            border: "1px solid rgba(229,72,77,0.25)",
            padding: "2px 8px", borderRadius: 20,
            fontFamily: "JetBrains Mono, monospace",
          }}>
            {displayed.length} active
          </span>
        </div>
      </div>

      {/* Feed list */}
      <div style={{ overflowY: "auto", flex: 1 }}>
        {displayed.map((reg) => (
          <FeedItem
            key={reg.id}
            reg={reg}
            sev={SEVERITY_COLORS[reg.severity] || SEVERITY_COLORS.Medium}
            jColor={JURISDICTION_COLORS[reg.jurisdiction] || "#8B8D97"}
            isSelected={selectedId === reg.id}
            onSelect={onSelect}
          />
        ))}
      </div>

      <style>{`
        @keyframes feedpulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes spin { to{transform:rotate(360deg)} }
      `}</style>
    </div>
  );
}

function FeedItem({
  reg, sev, jColor, isSelected, onSelect,
}: {
  reg: RegulationItem;
  sev: { bg: string; text: string; dot: string };
  jColor: string;
  isSelected: boolean;
  onSelect: (r: RegulationItem) => void;
}) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onClick={() => onSelect(reg)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding: "14px 20px",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
        cursor: "pointer",
        background: isSelected ? "rgba(229,72,77,0.06)" : hovered ? "rgba(255,255,255,0.02)" : "transparent",
        borderLeft: isSelected ? "2px solid #E5484D" : "2px solid transparent",
        transition: "all .15s ease",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
        <span style={{
          fontSize: 10, fontWeight: 700, letterSpacing: "0.05em",
          background: sev.bg, color: sev.text, border: `1px solid ${sev.dot}33`,
          padding: "2px 7px", borderRadius: 20, textTransform: "uppercase",
        }}>{reg.severity}</span>
        <span style={{
          fontSize: 10, fontWeight: 600,
          background: `${jColor}15`, color: jColor, border: `1px solid ${jColor}30`,
          padding: "2px 7px", borderRadius: 20,
        }}>{reg.jurisdiction}</span>
        <span style={{ fontSize: 10, color: "#4A4C57", marginLeft: "auto", fontFamily: "JetBrains Mono, monospace" }}>
          {reg.date}
        </span>
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color: isSelected ? "#EDEDEF" : "#C4C6D0", marginBottom: 4, lineHeight: 1.4 }}>
        {reg.title}
      </div>
      <div style={{ fontSize: 12, color: "#4A4C57", lineHeight: 1.5, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
        {reg.body}
      </div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 8 }}>
        <span style={{ fontSize: 11, color: "#4A4C57" }}>{reg.regulator} · {reg.sector}</span>
        <button
          onClick={(e) => { e.stopPropagation(); onSelect(reg); }}
          style={{
            fontSize: 11, fontWeight: 600, color: isSelected ? "#E5484D" : "#8B8D97",
            background: "none", border: "none", cursor: "pointer", padding: 0,
          }}
        >
          {isSelected ? "Analyzing →" : "Analyze →"}
        </button>
      </div>
    </div>
  );
}
