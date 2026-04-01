"use client";

export default function CTA() {
  return (
    <section style={{ borderTop: "1px solid rgba(255,255,255,0.07)", padding: "112px 0" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "48px 80px", alignItems: "start" }}>
          {/* Left */}
          <div>
            <h2 style={{ fontSize: "clamp(2rem,4vw,3.2rem)", fontWeight: 700, letterSpacing: "-0.04em", lineHeight: 1.08, color: "#fff", marginBottom: 16 }}>
              Stop finding out about regulations after the fact.
            </h2>
            <p style={{ fontSize: 14, color: "#333", maxWidth: 400 }}>
              No credit card. No sales call. We'll reach out within 24 hours.
            </p>
          </div>

          {/* Right */}
          <div style={{ paddingTop: 8 }}>
            <p style={{ fontSize: "1.2rem", color: "#555", lineHeight: 1.65, marginBottom: 36 }}>
              Join the early access program. You get the full pipeline, all integrations, and
              direct access to the team to shape what we build next.
            </p>

            <form
              onSubmit={e => e.preventDefault()}
              style={{ display: "flex", gap: 8, maxWidth: 440 }}
            >
              <input
                type="email"
                placeholder="you@yourcompany.com"
                style={{
                  flex: 1, padding: "10px 14px",
                  background: "#0E0E0E",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 8, fontSize: 14, color: "#ddd",
                  outline: "none",
                }}
                onFocus={e => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.25)")}
                onBlur={e => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)")}
              />
              <button
                type="submit"
                style={{
                  padding: "10px 20px", borderRadius: 8,
                  fontSize: 14, fontWeight: 500, color: "#fff",
                  background: "linear-gradient(135deg,#E5484D,#C73E3E)",
                  border: "none", cursor: "pointer", whiteSpace: "nowrap",
                  boxShadow: "0 4px 20px rgba(229,72,77,0.25)",
                }}
              >
                Request access
              </button>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}
