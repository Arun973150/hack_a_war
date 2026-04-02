"use client";

import { useState, useRef, useEffect } from "react";
import { askQuestion } from "../lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: any[];
}

export default function AskReforge() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hi! I'm Reforge, your compliance intelligence assistant. You can ask me about regulations, internal policies, or existing controls." }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const query = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: query }]);
    setIsLoading(true);

    const res = await askQuestion(query);

    setIsLoading(false);
    if (!res) {
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, I had trouble connecting to the backend. Please try again." }]);
      return;
    }

    setMessages(prev => [...prev, { 
      role: "assistant", 
      content: res.answer || "I couldn't find an answer.",
      sources: res.sources 
    }]);
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: "fixed",
          bottom: 24,
          right: 24,
          zIndex: 9999,
          width: 50,
          height: 50,
          borderRadius: 25,
          background: "linear-gradient(135deg, #E5484D 0%, #B83E42 100%)",
          boxShadow: "0 4px 14px rgba(229,72,77,0.4)",
          border: "none",
          color: "white",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          transition: "transform 0.2s",
          transform: isOpen ? "scale(0.9)" : "scale(1)",
        }}
      >
        {isOpen ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        ) : (
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        )}
      </button>

      {isOpen && (
        <div style={{
          position: "fixed",
          bottom: 84,
          right: 24,
          width: 360,
          height: 500,
          background: "#111118",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: 12,
          boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
          zIndex: 9999,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden"
        }}>
          {/* Header */}
          <div style={{ padding: "16px", borderBottom: "1px solid rgba(255,255,255,0.1)", display: "flex", alignItems: "center", gap: 10, background: "rgba(255,255,255,0.02)" }}>
            <div style={{
              width: 28, height: 28, borderRadius: 8,
              background: "linear-gradient(135deg,#E5484D,#B83E42)",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 2px 8px rgba(229,72,77,0.4)"
            }}>
              <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
                <path d="M2 12L5.5 5.5L9 9L11.5 2" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#EDEDEF" }}>Ask Reforge</div>
              <div style={{ fontSize: 11, color: "#22C55E", display: "flex", alignItems: "center", gap: 4 }}>
                <span style={{ width: 6, height: 6, borderRadius: 3, background: "#22C55E" }}></span> AI Assistant
              </div>
            </div>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
            {messages.map((m, i) => (
              <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: m.role === "user" ? "flex-end" : "flex-start" }}>
                <div style={{
                  maxWidth: "85%",
                  padding: "10px 14px",
                  borderRadius: 12,
                  background: m.role === "user" ? "rgba(229,72,77,0.15)" : "rgba(255,255,255,0.05)",
                  border: `1px solid ${m.role === "user" ? "rgba(229,72,77,0.3)" : "rgba(255,255,255,0.1)"}`,
                  color: "#EDEDEF",
                  fontSize: 13,
                  lineHeight: 1.5,
                  whiteSpace: "pre-wrap"
                }}>
                  {m.content}
                </div>
                {m.sources && m.sources.length > 0 && (
                  <div style={{ marginTop: 6, display: "flex", gap: 4, flexWrap: "wrap", maxWidth: "85%" }}>
                    {m.sources.map((s, idx) => (
                      <div key={idx} style={{ fontSize: 10, color: "#8B8D97", background: "rgba(255,255,255,0.03)", padding: "2px 6px", borderRadius: 4, border: "1px solid rgba(255,255,255,0.05)" }}>
                        Source: {s.source_id.split("-")[0]}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
                <div style={{
                  padding: "10px 14px", borderRadius: 12, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)",
                  display: "flex", gap: 4
                }}>
                  <span style={{ width: 6, height: 6, borderRadius: 3, background: "#8B8D97", animation: "bounce 1.4s infinite ease-in-out both" }} />
                  <span style={{ width: 6, height: 6, borderRadius: 3, background: "#8B8D97", animation: "bounce 1.4s infinite ease-in-out both", animationDelay: "0.16s" }} />
                  <span style={{ width: 6, height: 6, borderRadius: 3, background: "#8B8D97", animation: "bounce 1.4s infinite ease-in-out both", animationDelay: "0.32s" }} />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Input */}
          <div style={{ padding: "12px", borderTop: "1px solid rgba(255,255,255,0.1)" }}>
            <form onSubmit={handleSubmit} style={{ display: "flex", gap: 8 }}>
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask about compliance..."
                style={{
                  flex: 1,
                  background: "rgba(0,0,0,0.3)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 20,
                  padding: "8px 14px",
                  color: "#EDEDEF",
                  fontSize: 13,
                  outline: "none"
                }}
              />
              <button
                type="submit"
                disabled={!input.trim() || isLoading}
                style={{
                  width: 34, height: 34, borderRadius: 17,
                  background: input.trim() && !isLoading ? "#E5484D" : "rgba(255,255,255,0.1)",
                  color: "white", border: "none",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  cursor: input.trim() && !isLoading ? "pointer" : "default",
                  transition: "background 0.2s"
                }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
              </button>
            </form>
          </div>
        </div>
      )}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }
      `}</style>
    </>
  );
}
