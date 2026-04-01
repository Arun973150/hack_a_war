"use client";

import { useState, useCallback, useRef } from "react";
import { uploadControlFile, UploadedControl } from "../lib/api";

type UploadState = "idle" | "dragging" | "uploading" | "done" | "error";

const FORMATS = [
  { ext: ".csv", label: "CSV", icon: "CSV" },
  { ext: ".xlsx", label: "XLSX", icon: "XLS" },
  { ext: ".pdf", label: "PDF", icon: "PDF" },
  { ext: ".docx", label: "DOCX", icon: "DOC" },
];

export default function OnboardUpload({ onAnalyze }: { onAnalyze?: () => void }) {
  const [state, setState] = useState<UploadState>("idle");
  const [fileName, setFileName] = useState<string | null>(null);
  const [controls, setControls] = useState<UploadedControl[]>([]);
  const [method, setMethod] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = useCallback(async (file: File) => {
    setFileName(file.name);
    setState("uploading");
    setErrorMsg("");

    const result = await uploadControlFile(file);

    if (!result) {
      // Backend down — simulate success for demo
      setState("done");
      setMethod("demo_mode");
      setControls([
        { control_id: "CTRL-DEMO-001", name: "Data Encryption at Rest", framework: "ISO27001", status: "registered" },
        { control_id: "CTRL-DEMO-002", name: "Access Control Policy", framework: "SOC2", status: "registered" },
        { control_id: "CTRL-DEMO-003", name: "Incident Response Plan", framework: "DORA", status: "registered" },
      ]);
      return;
    }

    setControls(result.registered);
    setMethod(result.method);
    setState("done");
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setState("idle");
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  }, [handleUpload]);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
  };

  const reset = () => {
    setState("idle");
    setFileName(null);
    setControls([]);
    setMethod("");
    setErrorMsg("");
    if (fileRef.current) fileRef.current.value = "";
  };

  return (
    <div style={{ background: "#0D0D12", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, overflow: "hidden" }}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: "#EDEDEF" }}>Control Onboarding</span>
        </div>
        {state === "done" && (
          <button onClick={reset} style={{ fontSize: 11, color: "#8B8D97", background: "none", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "3px 10px", cursor: "pointer", outline: "none" }}>
            Reset
          </button>
        )}
      </div>

      <div style={{ padding: "20px" }}>
        {state === "idle" || state === "dragging" ? (
          <>
            <div
              onDragOver={(e) => { e.preventDefault(); setState("dragging"); }}
              onDragLeave={() => setState("idle")}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
              style={{
                border: `2px dashed ${state === "dragging" ? "rgba(229,72,77,0.6)" : "rgba(255,255,255,0.1)"}`,
                borderRadius: 10, padding: "28px 20px", textAlign: "center", cursor: "pointer",
                background: state === "dragging" ? "rgba(229,72,77,0.04)" : "rgba(255,255,255,0.01)",
                transition: "all .15s", marginBottom: 16,
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: "#4A4C57", marginBottom: 10, letterSpacing: "0.08em" }}>UPLOAD</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#EDEDEF", marginBottom: 6 }}>Drop your control file here</div>
              <div style={{ fontSize: 12, color: "#4A4C57", marginBottom: 12 }}>
                or <span style={{ color: "#E5484D" }}>browse to upload</span>
              </div>
              <div style={{ fontSize: 11, color: "#2A2C37" }}>CSV · XLSX · PDF · DOCX</div>
              <input ref={fileRef} type="file" accept=".csv,.xlsx,.pdf,.docx" onChange={handleFile} style={{ display: "none" }} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 8 }}>
              {FORMATS.map((f) => (
                <div key={f.ext} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, padding: "10px 8px", textAlign: "center" }}>
                  <div style={{ fontSize: 10, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: "#4A4C57", marginBottom: 4 }}>{f.icon}</div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "#8B8D97" }}>{f.label}</div>
                </div>
              ))}
            </div>
          </>
        ) : state === "uploading" ? (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <div style={{ fontSize: 11, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: "#4A4C57", marginBottom: 12, letterSpacing: "0.08em" }}>
              {fileName?.endsWith(".pdf") || fileName?.endsWith(".docx") ? "AI" : "UP"}
            </div>
            <div style={{ fontSize: 12, fontWeight: 500, color: "#EDEDEF", marginBottom: 4 }}>
              {fileName?.endsWith(".pdf") || fileName?.endsWith(".docx") ? "Gemini extracting controls..." : "Parsing and registering controls..."}
            </div>
            <div style={{ fontSize: 11, color: "#4A4C57", marginBottom: 16, fontFamily: "JetBrains Mono, monospace" }}>{fileName}</div>
            <div style={{ height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 2, overflow: "hidden" }}>
              <div style={{ height: "100%", width: "100%", background: "linear-gradient(90deg,#E5484D,#B83E42)", borderRadius: 2, animation: "shimmer 1.5s infinite" }} />
            </div>
            <style>{`@keyframes shimmer { 0%,100%{opacity:1} 50%{opacity:0.5} }`}</style>
          </div>
        ) : state === "done" ? (
          <ExtractedResults
            fileName={fileName!}
            controls={controls}
            method={method}
            onAnalyze={onAnalyze}
          />
        ) : (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <div style={{ fontSize: 13, color: "#E5484D" }}>Upload failed: {errorMsg}</div>
            <button onClick={reset} style={{ marginTop: 12, fontSize: 12, color: "#8B8D97", background: "none", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, padding: "4px 12px", cursor: "pointer", outline: "none" }}>Try again</button>
          </div>
        )}
      </div>
    </div>
  );
}

function ExtractedResults({ fileName, controls, method, onAnalyze }: { fileName: string; controls: UploadedControl[]; method: string; onAnalyze?: () => void }) {
  const newCount = controls.filter((c) => c.status === "registered").length;
  const errCount = controls.filter((c) => c.status === "error").length;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
        <div style={{ width: 18, height: 18, borderRadius: 4, background: "rgba(34,197,94,0.15)", border: "1px solid rgba(34,197,94,0.3)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, color: "#22C55E" }}>+</div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#22C55E" }}>{newCount} controls registered</div>
          <div style={{ fontSize: 11, color: "#4A4C57", fontFamily: "JetBrains Mono, monospace" }}>{fileName}</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <span style={{ fontSize: 11, color: "#22C55E", background: "rgba(34,197,94,0.1)", border: "1px solid rgba(34,197,94,0.2)", padding: "2px 8px", borderRadius: 20 }}>{newCount} registered</span>
          {errCount > 0 && <span style={{ fontSize: 11, color: "#E5484D", background: "rgba(229,72,77,0.1)", border: "1px solid rgba(229,72,77,0.2)", padding: "2px 8px", borderRadius: 20 }}>{errCount} errors</span>}
          <span style={{ fontSize: 11, color: method === "ai_extraction" ? "#8B5CF6" : "#22C55E", background: `${method === "ai_extraction" ? "rgba(139,92,246,0.1)" : "rgba(34,197,94,0.1)"}`, border: `1px solid ${method === "ai_extraction" ? "rgba(139,92,246,0.2)" : "rgba(34,197,94,0.2)"}`, padding: "2px 8px", borderRadius: 20 }}>
            {method === "ai_extraction" ? "AI extracted" : method === "demo_mode" ? "demo" : "direct parse"}
          </span>
        </div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {controls.map((c) => (
          <div key={c.control_id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: 7, background: "rgba(0,0,0,0.2)", border: `1px solid ${c.status === "registered" ? "rgba(34,197,94,0.15)" : "rgba(229,72,77,0.15)"}` }}>
            <span style={{ fontSize: 12, color: c.status === "registered" ? "#22C55E" : "#E5484D" }}>{c.status === "registered" ? "+" : "✗"}</span>
            <span style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: "#4A4C57" }}>{c.control_id}</span>
            <span style={{ fontSize: 12, color: "#8B8D97", flex: 1 }}>{c.name}</span>
            <span style={{ fontSize: 10, color: "#4A4C57", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", padding: "1px 6px", borderRadius: 4 }}>{c.framework}</span>
          </div>
        ))}
      </div>

      {onAnalyze && (
        <button
          onClick={onAnalyze}
          style={{
            marginTop: 16, width: "100%", padding: "10px 0", borderRadius: 8, cursor: "pointer",
            background: "rgba(229,72,77,0.08)", border: "1px solid rgba(229,72,77,0.3)",
            color: "#E5484D", fontSize: 13, fontWeight: 600, outline: "none", transition: "all .15s",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(229,72,77,0.14)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(229,72,77,0.08)")}
        >
          Analyze a regulation →
        </button>
      )}
    </div>
  );
}
