"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import Nav from "@/components/nav";
import JurisdictionFilter, { Jurisdiction } from "./components/JurisdictionFilter";
import FeedMonitor, { RegulationItem } from "./components/FeedMonitor";
import AgentTrace from "./components/AgentTrace";
import ResultsView from "./components/ResultsView";
import ConflictDetection from "./components/ConflictDetection";
import DriftScore from "./components/DriftScore";
import OnboardUpload from "./components/OnboardUpload";
import ProactiveAlerts from "./components/ProactiveAlerts";
import { triggerPipeline, streamPipeline, AgentEvent, PipelineResult } from "./lib/api";

const SIMULATED_STEP_MS = 1800;
const AGENT_COUNT = 5;

// Step 1 → 2 → 3 → 4  (linear demo flow)
type Tab = "setup" | "analyze" | "results" | "monitoring";

const TABS: { id: Tab; step: number; label: string }[] = [
  { id: "setup",      step: 1, label: "Setup" },
  { id: "analyze",    step: 2, label: "Analyze" },
  { id: "results",    step: 3, label: "Results" },
  { id: "monitoring", step: 4, label: "Monitoring" },
];

export default function DemoPage() {
  const [jurisdiction, setJurisdiction] = useState<Jurisdiction>("All");
  const [selectedReg, setSelectedReg] = useState<RegulationItem | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("setup");

  const [sseEvents, setSseEvents] = useState<AgentEvent[]>([]);
  const [activeStep, setActiveStep] = useState(-1);
  const [isRunning, setIsRunning] = useState(false);
  const [isRealMode, setIsRealMode] = useState(false);

  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [pipelineResult, setPipelineResult] = useState<PipelineResult | null>(null);

  // Auto-advance to Results when pipeline finishes
  useEffect(() => {
    if (analysisComplete) setActiveTab("results");
  }, [analysisComplete]);

  const sseCleanup = useRef<(() => void) | null>(null);
  const simInterval = useRef<NodeJS.Timeout | null>(null);

  const stopAll = useCallback(() => {
    sseCleanup.current?.();
    sseCleanup.current = null;
    if (simInterval.current) clearInterval(simInterval.current);
    simInterval.current = null;
  }, []);

  const runSimulated = useCallback(() => {
    setIsRealMode(false);
    let step = 0;
    setActiveStep(0);
    simInterval.current = setInterval(() => {
      step++;
      if (step < AGENT_COUNT) {
        setActiveStep(step);
      } else {
        clearInterval(simInterval.current!);
        simInterval.current = null;
        setActiveStep(AGENT_COUNT);
        setIsRunning(false);
        setAnalysisComplete(true);
      }
    }, SIMULATED_STEP_MS);
  }, []);

  const handleSelectReg = useCallback(async (reg: RegulationItem) => {
    if (isRunning) return;

    stopAll();
    setSelectedReg(reg);
    setSseEvents([]);
    setActiveStep(-1);
    setAnalysisComplete(false);
    setPipelineResult(null);
    setIsRunning(true);
    setActiveTab("analyze");

    const triggered = await triggerPipeline({
      document_id: reg.id,
      raw_text: reg.rawText || reg.body,
      source_url: reg.id,
      jurisdiction: reg.jurisdiction,
      regulatory_body: reg.regulator,
      document_type: reg.docType,
      published_date: reg.date,
    });

    if (!triggered) {
      runSimulated();
      return;
    }

    setIsRealMode(true);
    setActiveStep(0);

    const cleanup = streamPipeline(reg.id, (event: AgentEvent) => {
      if (event.type === "agent_done") {
        setSseEvents((prev) => [...prev, event]);
        setActiveStep((event.step ?? 0) + 1);
      } else if (event.type === "complete") {
        setSseEvents((prev) => [...prev, event]);
        setActiveStep(AGENT_COUNT);
        setIsRunning(false);
        setAnalysisComplete(true);
        if (event.result) setPipelineResult(event.result);
      } else if (event.type === "error" || event.type === "timeout") {
        setIsRunning(false);
        setAnalysisComplete(true);
      }
    });

    sseCleanup.current = cleanup;
  }, [isRunning, stopAll, runSimulated]);

  return (
    <div style={{ minHeight: "100vh", background: "#08080C", color: "#EDEDEF" }}>
      <Nav />

      <div style={{ paddingTop: 52 }}>
        <div style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
          <div style={{ maxWidth: 1400, margin: "0 auto", padding: "18px 24px 0" }}>

            {/* Header */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#22C55E", boxShadow: "0 0 8px rgba(34,197,94,0.5)", animation: "pulse 2s infinite" }} />
                <span style={{ fontSize: 15, fontWeight: 700, color: "#EDEDEF", letterSpacing: "-0.01em" }}>Red Forge</span>
                <span style={{ fontSize: 12, color: "#4A4C57" }}>/ Compliance Intelligence</span>
              </div>
              <JurisdictionFilter value={jurisdiction} onChange={setJurisdiction} />
            </div>

            {/* Step tabs */}
            <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
              {TABS.map((tab, i) => {
                const active = tab.id === activeTab;
                const completed =
                  (tab.id === "setup") ||
                  (tab.id === "analyze" && (isRunning || analysisComplete)) ||
                  (tab.id === "results" && analysisComplete);
                const running = tab.id === "analyze" && isRunning;

                return (
                  <div key={tab.id} style={{ display: "flex", alignItems: "center" }}>
                    <button
                      onClick={() => setActiveTab(tab.id)}
                      style={{
                        display: "flex", alignItems: "center", gap: 7,
                        padding: "8px 16px", fontSize: 13,
                        fontWeight: active ? 600 : 400,
                        color: active ? "#EDEDEF" : completed ? "#8B8D97" : "#4A4C57",
                        background: "none", border: "none",
                        borderBottom: active ? "2px solid #E5484D" : "2px solid transparent",
                        cursor: "pointer", outline: "none", transition: "color .15s",
                      }}
                    >
                      <span style={{
                        width: 18, height: 18, borderRadius: "50%", fontSize: 10, fontWeight: 700,
                        display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                        background: running ? "rgba(245,158,11,0.15)" :
                                    active ? "rgba(229,72,77,0.15)" :
                                    completed ? "rgba(34,197,94,0.1)" : "rgba(255,255,255,0.05)",
                        color: running ? "#F59E0B" :
                               active ? "#E5484D" :
                               completed ? "#22C55E" : "#4A4C57",
                        border: running ? "1px solid rgba(245,158,11,0.3)" :
                                active ? "1px solid rgba(229,72,77,0.3)" :
                                completed ? "1px solid rgba(34,197,94,0.2)" : "1px solid rgba(255,255,255,0.07)",
                        animation: running ? "pulse 1s infinite" : "none",
                      }}>
                        {tab.step}
                      </span>
                      {tab.label}
                    </button>
                    {i < TABS.length - 1 && (
                      <span style={{ fontSize: 11, color: "#2A2C37", padding: "0 2px" }}>›</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Content */}
        <div style={{ maxWidth: 1400, margin: "0 auto", padding: "20px 24px 40px" }}>

          {/* Step 1: Setup — upload controls */}
          {activeTab === "setup" && (
            <div style={{ maxWidth: 680 }}>
              <OnboardUpload onAnalyze={() => setActiveTab("analyze")} />
            </div>
          )}

          {/* Step 2: Analyze — pick regulation, watch agents */}
          {activeTab === "analyze" && (
            <div>
              {!selectedReg && !isRunning && (
                <div style={{ marginBottom: 14, padding: "10px 16px", borderRadius: 8, background: "rgba(229,72,77,0.04)", border: "1px solid rgba(229,72,77,0.15)", display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#E5484D", flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: "#8B8D97" }}>Select a regulation from the feed to run the analysis pipeline.</span>
                </div>
              )}
              <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 16, height: 580 }}>
                <FeedMonitor filter={jurisdiction} selectedId={selectedReg?.id || null} onSelect={handleSelectReg} />
                <AgentTrace
                  regulation={selectedReg}
                  sseEvents={sseEvents}
                  activeStep={activeStep}
                  isRunning={isRunning}
                  isRealMode={isRealMode}
                />
              </div>
            </div>
          )}

          {/* Step 3: Results — report style */}
          {activeTab === "results" && (
            <ResultsView regulation={selectedReg} analysisComplete={analysisComplete} pipelineResult={pipelineResult} />
          )}

          {/* Step 4: Monitoring — always-on health */}
          {activeTab === "monitoring" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                <DriftScore jurisdiction={jurisdiction} />
                <ConflictDetection />
              </div>
              <ProactiveAlerts />
            </div>
          )}

        </div>
      </div>

      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }`}</style>
    </div>
  );
}
