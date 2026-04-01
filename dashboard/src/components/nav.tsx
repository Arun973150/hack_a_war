"use client";

import { useState, useEffect } from "react";

const links = ["Product", "Resources", "Customers", "Pricing", "Now", "Contact"];
const DEMO_HREF = "/demo";

export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);

  return (
    <header
      style={{
        position: "fixed",
        top: 0, left: 0, right: 0,
        zIndex: 50,
        background: scrolled
          ? "rgba(10,10,10,0.88)"
          : "linear-gradient(180deg, rgba(10,10,10,0.6) 0%, transparent 100%)",
        backdropFilter: scrolled ? "blur(16px)" : "none",
        borderBottom: scrolled ? "1px solid rgba(255,255,255,0.07)" : "1px solid transparent",
        boxShadow: scrolled ? "0 1px 0 rgba(229,72,77,0.06), inset 0 1px 0 rgba(255,255,255,0.04)" : "none",
        transition: "all 0.2s ease",
      }}
    >
      <div style={{
        maxWidth: 1200,
        margin: "0 auto",
        padding: "0 24px",
        height: 52,
        display: "flex",
        alignItems: "center",
        gap: 0,
      }}>
        {/* Logo */}
        <a href="/" style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none", marginRight: 32 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 8,
            background: "linear-gradient(135deg,#E5484D,#B83E42)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 2px 8px rgba(229,72,77,0.4)",
            flexShrink: 0,
          }}>
            <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
              <path d="M2 12L5.5 5.5L9 9L11.5 2" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span style={{ fontSize: 15, fontWeight: 600, color: "#fff", letterSpacing: "-0.01em" }}>Red Forge</span>
        </a>

        {/* Desktop links */}
        <nav style={{ display: "flex", alignItems: "center", gap: 2, flex: 1 }} className="hidden-mobile">
          {links.map(l => (
            <a key={l} href="#"
              style={{ padding: "6px 12px", fontSize: 13.5, color: "#888", textDecoration: "none", borderRadius: 6, transition: "color .15s" }}
              onMouseEnter={e => (e.currentTarget.style.color = "#fff")}
              onMouseLeave={e => (e.currentTarget.style.color = "#888")}
            >{l}</a>
          ))}
          <a href={DEMO_HREF}
            style={{
              padding: "5px 12px", fontSize: 13.5, textDecoration: "none", borderRadius: 6,
              color: "#E5484D", fontWeight: 600,
              background: "rgba(229,72,77,0.08)",
              border: "1px solid rgba(229,72,77,0.2)",
              display: "flex", alignItems: "center", gap: 6,
              transition: "all .15s ease",
              marginLeft: 4,
            }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLElement).style.background = "rgba(229,72,77,0.14)";
              (e.currentTarget as HTMLElement).style.borderColor = "rgba(229,72,77,0.4)";
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.background = "rgba(229,72,77,0.08)";
              (e.currentTarget as HTMLElement).style.borderColor = "rgba(229,72,77,0.2)";
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#E5484D", boxShadow: "0 0 6px rgba(229,72,77,0.6)" }} />
            Live Demo
          </a>
        </nav>

        {/* Divider + actions */}
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginLeft: "auto" }} className="hidden-mobile">
          <div style={{ width: 1, height: 16, background: "rgba(255,255,255,0.12)" }} />
          <a href="#" style={{ fontSize: 13.5, color: "#888", textDecoration: "none", transition: "color .15s" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#fff")}
            onMouseLeave={e => (e.currentTarget.style.color = "#888")}
          >Log in</a>
          <a href="#" style={{
            fontSize: 13.5, fontWeight: 500, color: "#fff",
            border: "1px solid rgba(255,255,255,0.25)",
            padding: "5px 14px", borderRadius: 7,
            textDecoration: "none",
            transition: "background .15s, border-color .15s",
            background: "transparent",
          }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.07)";
              (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.4)";
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLElement).style.background = "transparent";
              (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.25)";
            }}
          >Sign up</a>
        </div>

        {/* Mobile toggle */}
        <button onClick={() => setOpen(!open)} className="show-mobile"
          style={{ marginLeft: "auto", background: "none", border: "none", color: "#888", cursor: "pointer", padding: 6 }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            {open
              ? <path d="M4 4l10 10M14 4L4 14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
              : <path d="M2 5h14M2 9h14M2 13h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>}
          </svg>
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div style={{
          background: "rgba(10,10,10,0.97)", backdropFilter: "blur(20px)",
          borderTop: "1px solid rgba(255,255,255,0.07)",
          padding: "12px 24px 20px",
        }} className="show-mobile">
          {links.map(l => (
            <a key={l} href="#" style={{ display: "block", padding: "10px 0", fontSize: 14, color: "#888", textDecoration: "none" }}
              onClick={() => setOpen(false)}>{l}</a>
          ))}
          <a href={DEMO_HREF} style={{ display: "block", padding: "10px 0", fontSize: 14, color: "#E5484D", textDecoration: "none", fontWeight: 600 }}
            onClick={() => setOpen(false)}>⬤ Live Demo</a>
          <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.07)", display: "flex", gap: 12 }}>
            <a href="#" style={{ fontSize: 14, color: "#888", textDecoration: "none" }}>Log in</a>
            <a href="#" style={{ fontSize: 14, color: "#fff", border: "1px solid rgba(255,255,255,0.25)", padding: "5px 14px", borderRadius: 7, textDecoration: "none" }}>Sign up</a>
          </div>
        </div>
      )}

      <style>{`
        @media (max-width: 768px) { .hidden-mobile { display: none !important; } }
        @media (min-width: 769px) { .show-mobile { display: none !important; } }
      `}</style>
    </header>
  );
}
