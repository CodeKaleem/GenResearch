"use client";

import { useState } from "react";
import { supabase } from "../../lib/supabase";

// ── Design tokens (mirrored from theme.ts) ─────────────────────
const C = {
  cream: "#f5f0e8",
  creamLight: "#faf8f2",
  creamDark: "#efe8d8",
  inkDark: "#2c1f0e",
  inkMid: "#5a3e20",
  inkLight: "#7a6040",
  gold: "#8b6914",
  goldLight: "#c8971e",
  goldFaint: "rgba(139,105,20,0.09)",
  sienna: "#a0522d",
  umber: "#6b5c38",
  white: "#fffef9",
  border: "rgba(180,160,120,0.22)",
  borderGold: "rgba(139,105,20,0.4)",
  green: "#5a8a3c",
  shadow: "rgba(120,100,60,0.10)",
} as const;

// ── Floating paper card decoration ────────────────────────────
function MiniPaper({ style, delay }: { style?: React.CSSProperties; delay?: string }) {
  return (
    <div style={{
      background: "rgba(255,254,249,0.06)",
      border: "1px solid rgba(200,151,30,0.15)",
      borderRadius: 3,
      padding: "12px 14px",
      animation: "floatPaper 7s ease-in-out infinite",
      animationDelay: delay ?? "0s",
      ...style,
    }}>
      {[80, 60, 90, 50].map((w, i) => (
        <div key={i} style={{
          height: 4,
          background: i === 0 ? "rgba(200,151,30,0.4)" : "rgba(200,151,30,0.12)",
          borderRadius: 2,
          width: `${w}%`,
          marginBottom: 5,
        }} />
      ))}
    </div>
  );
}

// ── Logo mark ─────────────────────────────────────────────────
function LogoMark({ dark = false }: { dark?: boolean }) {
  const color = dark ? C.inkDark : C.goldLight;
  const textColor = dark ? C.inkDark : C.goldLight;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ width: 32, height: 32, position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: 28, height: 28, border: `2px solid ${color}`, transform: "rotate(45deg)", position: "absolute" }} />
        <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 13, fontWeight: 700, color: textColor, position: "relative", zIndex: 1 }}>G</span>
      </div>
      <div>
        <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 17, fontWeight: 800, color: dark ? C.inkDark : C.white, letterSpacing: "-0.01em", lineHeight: 1 }}>GenResearch</div>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 9.5, color: dark ? C.gold : C.goldLight, letterSpacing: "0.18em", textTransform: "uppercase" }}>Academic AI Platform</div>
      </div>
    </div>
  );
}

// ── Input field ───────────────────────────────────────────────
function FormInput({
  id, label, type = "text", placeholder, value, onChange, icon,
}: {
  id: string; label: string; type?: string; placeholder: string;
  value: string; onChange: (v: string) => void; icon: string;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ marginBottom: 20 }}>
      <label htmlFor={id} style={{
        display: "block",
        fontFamily: "'Crimson Pro', Georgia, serif",
        fontSize: 12, fontWeight: 600, color: C.gold,
        letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 7,
      }}>{label}</label>
      <div style={{ position: "relative" }}>
        <span style={{
          position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)",
          fontSize: 15, color: focused ? C.gold : C.inkLight,
          transition: "color .2s", pointerEvents: "none",
        }}>{icon}</span>
        <input
          id={id}
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={e => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={{
            width: "100%",
            padding: "13px 14px 13px 40px",
            border: `1.5px solid ${focused ? C.gold : C.border}`,
            borderRadius: 3,
            background: focused ? C.white : C.creamLight,
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 15, color: C.inkDark,
            outline: "none",
            transition: "all .25s",
            boxShadow: focused ? `0 0 0 3px rgba(139,105,20,0.08)` : "none",
          }}
        />
      </div>
    </div>
  );
}

// ── Main Login Component ───────────────────────────────────────

export default function Login({
  onLoginSuccess,
  onNavigateRegister,
  onNavigateHome,
}: {
  onLoginSuccess?: () => void;
  onNavigateRegister?: () => void;
  onNavigateHome?: () => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!email || !password) { setError("Please fill in all fields."); return; }
    
    setLoading(true);
    try {
      const { error: authError } = await supabase.auth.signInWithPassword({
        email: email.trim(),
        password,
      });

      if (authError) {
        setError(authError.message);
      } else {
        onLoginSuccess?.();
      }
    } catch (err) {
      setError("An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,800;0,900;1,700&family=Crimson+Pro:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { height: 100%; }
        body { background: ${C.cream}; color: ${C.inkDark}; font-family: 'Crimson Pro', Georgia, serif; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: ${C.cream}; }
        ::-webkit-scrollbar-thumb { background: rgba(139,105,20,0.3); border-radius: 3px; }

        @keyframes fadeUp    { from{opacity:0;transform:translateY(22px)} to{opacity:1;transform:translateY(0)} }
        @keyframes floatPaper { 0%,100%{transform:translateY(0) rotate(-1.5deg)} 50%{transform:translateY(-12px) rotate(1deg)} }
        @keyframes spin      { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        @keyframes shimmer   { 0%{background-position:200% center} 100%{background-position:-200% center} }
        @keyframes pulse     { 0%,100%{opacity:1} 50%{opacity:.45} }

        .auth-fade-1 { animation: fadeUp .65s .08s both; }
        .auth-fade-2 { animation: fadeUp .65s .18s both; }
        .auth-fade-3 { animation: fadeUp .65s .30s both; }
        .auth-fade-4 { animation: fadeUp .65s .44s both; }
        .auth-fade-5 { animation: fadeUp .65s .58s both; }

        .login-submit {
          width: 100%;
          padding: 14px 24px;
          background: ${C.inkDark};
          color: ${C.cream};
          border: none; border-radius: 3px;
          font-family: 'Crimson Pro', Georgia, serif;
          font-size: 13.5px; font-weight: 600;
          letter-spacing: .1em; text-transform: uppercase;
          cursor: pointer; transition: all .3s;
          position: relative; overflow: hidden;
        }
        .login-submit:hover:not(:disabled) {
          background: ${C.gold};
          transform: translateY(-2px);
          box-shadow: 0 8px 28px rgba(139,105,20,0.32);
        }
        .login-submit:disabled { opacity: .7; cursor: not-allowed; }

        .back-link {
          display: inline-flex; align-items: center; gap: 6px;
          font-family: 'Crimson Pro', Georgia, serif;
          font-size: 13px; color: rgba(200,151,30,0.6);
          text-decoration: none; cursor: pointer; border: none; background: transparent;
          transition: color .2s; padding: 0;
        }
        .back-link:hover { color: ${C.goldLight}; }

        .auth-text-link {
          font-family: 'Crimson Pro', Georgia, serif;
          font-size: 14px; color: ${C.gold};
          background: none; border: none; cursor: pointer;
          text-decoration: underline; text-underline-offset: 2px;
          transition: color .2s; padding: 0;
        }
        .auth-text-link:hover { color: ${C.goldLight}; }

        .checkbox-wrap { display: flex; align-items: center; gap: 9px; cursor: pointer; }
        .checkbox-wrap input[type="checkbox"] { accent-color: ${C.gold}; width: 15px; height: 15px; cursor: pointer; }
      `}</style>

      <div style={{ display: "flex", minHeight: "100vh" }}>

        {/* ── LEFT PANEL — brand dark ── */}
        <div style={{
          width: "45%",
          background: C.inkDark,
          position: "relative",
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "44px 52px",
          flexShrink: 0,
        }}>
          {/* Background texture lines */}
          <div style={{
            position: "absolute", inset: 0, pointerEvents: "none",
            backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 79px, rgba(200,151,30,0.04) 80px)",
          }} />
          {/* Decorative circles */}
          <div style={{
            position: "absolute", right: "-80px", bottom: "-80px",
            width: 380, height: 380, borderRadius: "50%",
            border: "1px solid rgba(200,151,30,0.08)", pointerEvents: "none",
          }} />
          <div style={{
            position: "absolute", right: "-40px", bottom: "-40px",
            width: 260, height: 260, borderRadius: "50%",
            border: "1px solid rgba(200,151,30,0.12)", pointerEvents: "none",
          }} />

          {/* Floating mini papers */}
          <MiniPaper style={{ position: "absolute", right: 40, top: "18%", width: 130 }} delay="0s" />
          <MiniPaper style={{ position: "absolute", right: 80, top: "42%", width: 100 }} delay="2s" />

          {/* Logo */}
          <div style={{ position: "relative", zIndex: 10 }}>
            <button className="back-link" onClick={onNavigateHome} style={{ marginBottom: 60 }}>
              ← Back to home
            </button>
            <LogoMark dark={false} />
          </div>

          {/* Centre copy */}
          <div style={{ position: "relative", zIndex: 10 }}>
            <div style={{
              display: "flex", alignItems: "center", gap: 12, marginBottom: 24,
            }}>
              <div style={{ height: 1, width: 36, background: C.gold }} />
              <span style={{
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 10, fontWeight: 600, color: C.gold,
                letterSpacing: "0.2em", textTransform: "uppercase",
              }}>Welcome back</span>
            </div>
            <h1 style={{
              fontFamily: "'Playfair Display', serif",
              fontSize: "clamp(28px, 3.5vw, 44px)",
              fontWeight: 900, color: C.white,
              lineHeight: 1.1, letterSpacing: "-0.02em", marginBottom: 18,
            }}>
              Your Research<br />
              <em style={{ color: C.goldLight }}>Awaits You.</em>
            </h1>
            <p style={{
              fontFamily: "'Crimson Pro', Georgia, serif",
              fontSize: 15.5, color: "rgba(245,240,232,0.62)",
              lineHeight: 1.8, maxWidth: 340,
            }}>
              Sign in to continue your academic journey. Access your uploaded
              papers, agent results, and research library.
            </p>
          </div>

          {/* Bottom features list */}
          <div style={{ position: "relative", zIndex: 10 }}>
            {[
              { icon: "◈", text: "Multi-agent AI research pipeline" },
              { icon: "◉", text: "Automated literature reviews" },
              { icon: "◎", text: "APA · MLA · IEEE citations" },
            ].map((item) => (
              <div key={item.icon} style={{
                display: "flex", alignItems: "center", gap: 12,
                marginBottom: 12,
              }}>
                <span style={{ color: C.goldLight, fontSize: 13 }}>{item.icon}</span>
                <span style={{
                  fontFamily: "'Crimson Pro', Georgia, serif",
                  fontSize: 13.5, color: "rgba(245,240,232,0.55)",
                }}>{item.text}</span>
              </div>
            ))}
            <div style={{
              marginTop: 24,
              fontFamily: "'Crimson Pro', Georgia, serif",
              fontSize: 11, color: "rgba(200,151,30,0.4)",
              letterSpacing: "0.06em",
            }}>
              Ali Ahmed · Kaleem-Ullah Abbasi · COMSATS WAH · FYP 2025
            </div>
          </div>
        </div>

        {/* ── RIGHT PANEL — form ── */}
        <div style={{
          flex: 1,
          background: C.cream,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: "60px 40px",
          position: "relative",
          overflowY: "auto",
        }}>
          {/* Subtle bg texture */}
          <div style={{
            position: "absolute", inset: 0, pointerEvents: "none",
            backgroundImage: "repeating-linear-gradient(90deg, transparent, transparent 79px, rgba(139,105,20,0.025) 80px)",
          }} />

          <div style={{
            width: "100%", maxWidth: 420, position: "relative", zIndex: 10,
          }}>

            {/* Header */}
            <div className="auth-fade-1" style={{ marginBottom: 36, textAlign: "center" }}>
              <div style={{
                display: "inline-flex", alignItems: "center", gap: 10,
                marginBottom: 20,
              }}>
                <div style={{ height: 1, width: 28, background: C.borderGold }} />
                <span style={{
                  fontFamily: "'Crimson Pro', Georgia, serif",
                  fontSize: 10, fontWeight: 600, color: C.gold,
                  letterSpacing: "0.2em", textTransform: "uppercase",
                }}>Researcher Login</span>
                <div style={{ height: 1, width: 28, background: C.borderGold }} />
              </div>
              <h2 style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: "clamp(26px, 3vw, 36px)",
                fontWeight: 900, color: C.inkDark,
                letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: 10,
              }}>Sign In to<br /><em style={{ color: C.gold }}>GenResearch</em></h2>
              <p style={{
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 15, color: C.inkLight, lineHeight: 1.7,
              }}>
                Don&apos;t have an account?{" "}
                <button className="auth-text-link" onClick={onNavigateRegister}>
                  Create one free
                </button>
              </p>
            </div>

            {/* Ornamental rule */}
            <div className="auth-fade-2" style={{
              display: "flex", alignItems: "center", gap: 14, marginBottom: 32,
            }}>
              <div style={{ flex: 1, height: 1, background: C.border }} />
              <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 16, color: C.gold }}>✦</span>
              <div style={{ flex: 1, height: 1, background: C.border }} />
            </div>

            {/* Error message */}
            {error && (
              <div style={{
                marginBottom: 20,
                padding: "12px 16px",
                background: "rgba(160,82,45,0.08)",
                border: "1px solid rgba(160,82,45,0.25)",
                borderRadius: 3,
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 14, color: C.sienna,
                display: "flex", alignItems: "center", gap: 8,
              }}>
                <span>⚠</span> {error}
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} noValidate>
              <div className="auth-fade-3">
                <FormInput
                  id="login-email"
                  label="Email Address"
                  type="email"
                  placeholder="you@university.edu"
                  value={email}
                  onChange={setEmail}
                  icon="✉"
                />
                <FormInput
                  id="login-password"
                  label="Password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={setPassword}
                  icon="🔒"
                />
              </div>

              {/* Remember + Forgot */}
              <div className="auth-fade-4" style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                marginBottom: 28,
              }}>
                <label className="checkbox-wrap">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={e => setRemember(e.target.checked)}
                  />
                  <span style={{
                    fontFamily: "'Crimson Pro', Georgia, serif",
                    fontSize: 14, color: C.inkLight,
                  }}>Remember me</span>
                </label>
                <button
                  type="button"
                  className="auth-text-link"
                  style={{ fontSize: 13 }}
                  onClick={() => { /* TODO: Forgot password flow */ }}
                >
                  Forgot password?
                </button>
              </div>

              {/* Submit */}
              <div className="auth-fade-5">
                <button
                  id="login-submit-btn"
                  type="submit"
                  className="login-submit"
                  disabled={loading}
                >
                  {loading ? (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                      <span style={{ animation: "spin 1s linear infinite", display: "inline-block" }}>⟳</span>
                      Signing In…
                    </span>
                  ) : "Sign In →"}
                </button>
              </div>
            </form>

            {/* Divider */}
            <div className="auth-fade-5" style={{
              display: "flex", alignItems: "center", gap: 14,
              margin: "28px 0",
            }}>
              <div style={{ flex: 1, height: 1, background: C.border }} />
              <span style={{
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 11.5, color: C.inkLight, letterSpacing: "0.06em",
              }}>or continue with</span>
              <div style={{ flex: 1, height: 1, background: C.border }} />
            </div>

            {/* Social buttons placeholder row */}
            <div className="auth-fade-5" style={{ display: "flex", gap: 12, marginBottom: 32 }}>
              {[
                { label: "Google", icon: "G" },
                { label: "GitHub", icon: "⌥" },
                { label: "ORCID", icon: "◎" },
              ].map(s => (
                <button
                  key={s.label}
                  id={`login-social-${s.label.toLowerCase()}`}
                  type="button"
                  style={{
                    flex: 1, padding: "11px 8px",
                    background: C.creamLight,
                    border: `1.5px solid ${C.border}`,
                    borderRadius: 3, cursor: "pointer",
                    fontFamily: "'Crimson Pro', Georgia, serif",
                    fontSize: 13, color: C.inkMid,
                    display: "flex", alignItems: "center", justifyContent: "center", gap: 7,
                    transition: "all .2s",
                  }}
                  onMouseEnter={e => { e.currentTarget.style.borderColor = C.borderGold; e.currentTarget.style.background = C.white; }}
                  onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.background = C.creamLight; }}
                >
                  <span style={{ fontWeight: 700, color: C.gold }}>{s.icon}</span>
                  {s.label}
                </button>
              ))}
            </div>

            {/* Register CTA */}
            <div className="auth-fade-5" style={{
              textAlign: "center",
              padding: "20px 0 0",
              borderTop: `1px solid ${C.border}`,
            }}>
              <p style={{
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 14.5, color: C.inkLight, lineHeight: 1.65,
              }}>
                New to GenResearch?{" "}
                <button
                  id="go-to-register-btn"
                  className="auth-text-link"
                  onClick={onNavigateRegister}
                >
                  Create your free account
                </button>
              </p>
            </div>

          </div>
        </div>
      </div>
    </>
  );
}
