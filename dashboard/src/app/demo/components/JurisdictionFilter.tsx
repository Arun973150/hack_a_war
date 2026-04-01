"use client";

export type Jurisdiction = "All" | "US" | "EU" | "India";

const REGIONS: { key: Jurisdiction; label: string; code: string }[] = [
  { key: "All", label: "All Regions", code: "GL" },
  { key: "US", label: "United States", code: "US" },
  { key: "EU", label: "European Union", code: "EU" },
  { key: "India", label: "India", code: "IN" },
];

interface Props {
  value: Jurisdiction;
  onChange: (j: Jurisdiction) => void;
}

export default function JurisdictionFilter({ value, onChange }: Props) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ fontSize: 12, color: "#4A4C57", fontWeight: 500, marginRight: 4, letterSpacing: "0.04em", textTransform: "uppercase" }}>
        Region
      </span>
      {REGIONS.map((r) => {
        const active = value === r.key;
        return (
          <button
            key={r.key}
            onClick={() => onChange(r.key)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "5px 12px", borderRadius: 7, cursor: "pointer",
              fontSize: 13, fontWeight: active ? 600 : 400,
              border: active ? "1px solid rgba(229,72,77,0.5)" : "1px solid rgba(255,255,255,0.08)",
              background: active ? "rgba(229,72,77,0.1)" : "rgba(255,255,255,0.03)",
              color: active ? "#E5484D" : "#8B8D97",
              transition: "all .15s ease",
              outline: "none",
            }}
            onMouseEnter={e => {
              if (!active) {
                (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.18)";
                (e.currentTarget as HTMLElement).style.color = "#EDEDEF";
              }
            }}
            onMouseLeave={e => {
              if (!active) {
                (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.08)";
                (e.currentTarget as HTMLElement).style.color = "#8B8D97";
              }
            }}
          >
            <span style={{ fontSize: 10, fontFamily: "JetBrains Mono, monospace", opacity: 0.6 }}>{r.code}</span>
            <span>{r.label}</span>
            {active && (
              <span style={{
                width: 6, height: 6, borderRadius: "50%",
                background: "#E5484D",
                boxShadow: "0 0 6px rgba(229,72,77,0.6)",
                flexShrink: 0,
              }} />
            )}
          </button>
        );
      })}
    </div>
  );
}
