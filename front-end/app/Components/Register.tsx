"use client";

import { useState } from "react";
import { supabase } from "../../lib/supabase";

const C = {
  cream: "#f5f0e8", creamLight: "#faf8f2", creamDark: "#efe8d8",
  inkDark: "#2c1f0e", inkMid: "#5a3e20", inkLight: "#7a6040",
  gold: "#8b6914", goldLight: "#c8971e", goldFaint: "rgba(139,105,20,0.09)",
  sienna: "#a0522d", umber: "#6b5c38", white: "#fffef9",
  border: "rgba(180,160,120,0.22)", borderGold: "rgba(139,105,20,0.4)",
  green: "#5a8a3c", shadow: "rgba(120,100,60,0.10)",
} as const;

function MiniPaper({ style, delay }: { style?: React.CSSProperties; delay?: string }) {
  return (
    <div style={{
      background: "rgba(255,254,249,0.06)",
      border: "1px solid rgba(200,151,30,0.15)",
      borderRadius: 3, padding: "12px 14px",
      animation: "floatPaper 7s ease-in-out infinite",
      animationDelay: delay ?? "0s", ...style,
    }}>
      {[75, 55, 85, 45].map((w, i) => (
        <div key={i} style={{
          height: 4,
          background: i === 0 ? "rgba(200,151,30,0.4)" : "rgba(200,151,30,0.12)",
          borderRadius: 2, width: `${w}%`, marginBottom: 5,
        }} />
      ))}
    </div>
  );
}

function FormInput({ id, label, type = "text", placeholder, value, onChange, icon }: {
  id: string; label: string; type?: string; placeholder: string;
  value: string; onChange: (v: string) => void; icon: string;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ marginBottom: 18 }}>
      <label htmlFor={id} style={{
        display: "block", fontFamily: "'Crimson Pro', Georgia, serif",
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
          id={id} type={type} placeholder={placeholder} value={value}
          onChange={e => onChange(e.target.value)}
          onFocus={() => setFocused(true)} onBlur={() => setFocused(false)}
          style={{
            width: "100%", padding: "12px 14px 12px 40px",
            border: `1.5px solid ${focused ? C.gold : C.border}`,
            borderRadius: 3, background: focused ? C.white : C.creamLight,
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 15, color: C.inkDark, outline: "none", transition: "all .25s",
            boxShadow: focused ? `0 0 0 3px rgba(139,105,20,0.08)` : "none",
          }}
        />
      </div>
    </div>
  );
}

function StrengthBar({ password }: { password: string }) {
  const score = [/[a-z]/, /[A-Z]/, /[0-9]/, /[^a-zA-Z0-9]/, /.{8,}/].filter(r => r.test(password)).length;
  const labels = ["", "Weak", "Fair", "Good", "Strong", "Excellent"];
  const colors = ["", C.sienna, "#c97820", C.umber, C.green, "#2a7a3c"];
  if (!password) return null;
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: "flex", gap: 4, marginBottom: 5 }}>
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} style={{
            flex: 1, height: 3, borderRadius: 2, transition: "background .3s",
            background: i <= score ? colors[score] : C.border,
          }} />
        ))}
      </div>
      <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, color: colors[score] }}>
        {labels[score]} password
      </span>
    </div>
  );
}

export default function Register({
  onRegisterSuccess,
  onNavigateLogin,
  onNavigateHome,
}: {
  onRegisterSuccess?: () => void;
  onNavigateLogin?: () => void;
  onNavigateHome?: () => void;
}) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [institution, setInstitution] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!fullName || !email || !password || !confirmPassword) { setError("Please fill in all required fields."); return; }
    if (password !== confirmPassword) { setError("Passwords do not match."); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters."); return; }
    if (!agreed) { setError("Please accept the terms to continue."); return; }
    
    setLoading(true);
    try {
      const { error: authError } = await supabase.auth.signUp({
        email: email.trim(),
        password,
        options: {
          data: {
            full_name: fullName.trim(),
            institution: institution.trim(),
            role: "student", // Default role for front-end
          },
        },
      });

      if (authError) {
        setError(authError.message);
      } else {
        onRegisterSuccess?.();
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
        body { background: ${C.cream}; color: ${C.inkDark}; font-family: 'Crimson Pro', Georgia, serif; overflow-x: hidden; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: ${C.cream}; }
        ::-webkit-scrollbar-thumb { background: rgba(139,105,20,0.3); border-radius: 3px; }
        @keyframes fadeUp    { from{opacity:0;transform:translateY(22px)} to{opacity:1;transform:translateY(0)} }
        @keyframes floatPaper { 0%,100%{transform:translateY(0) rotate(-1.5deg)} 50%{transform:translateY(-12px) rotate(1deg)} }
        @keyframes spin      { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        .r-fade-1 { animation: fadeUp .65s .08s both; }
        .r-fade-2 { animation: fadeUp .65s .18s both; }
        .r-fade-3 { animation: fadeUp .65s .30s both; }
        .r-fade-4 { animation: fadeUp .65s .44s both; }
        .r-fade-5 { animation: fadeUp .65s .58s both; }
        .reg-submit {
          width:100%; padding:14px 24px; background:${C.inkDark}; color:${C.cream};
          border:none; border-radius:3px; font-family:'Crimson Pro',Georgia,serif;
          font-size:13.5px; font-weight:600; letter-spacing:.1em; text-transform:uppercase;
          cursor:pointer; transition:all .3s;
        }
        .reg-submit:hover:not(:disabled) { background:${C.gold}; transform:translateY(-2px); box-shadow:0 8px 28px rgba(139,105,20,0.32); }
        .reg-submit:disabled { opacity:.7; cursor:not-allowed; }
        .back-link { display:inline-flex; align-items:center; gap:6px; font-family:'Crimson Pro',Georgia,serif; font-size:13px; color:rgba(200,151,30,0.6); cursor:pointer; border:none; background:transparent; transition:color .2s; padding:0; }
        .back-link:hover { color:${C.goldLight}; }
        .auth-text-link { font-family:'Crimson Pro',Georgia,serif; font-size:14px; color:${C.gold}; background:none; border:none; cursor:pointer; text-decoration:underline; text-underline-offset:2px; transition:color .2s; padding:0; }
        .auth-text-link:hover { color:${C.goldLight}; }
        .checkbox-wrap { display:flex; align-items:flex-start; gap:10px; cursor:pointer; }
        .checkbox-wrap input[type="checkbox"] { accent-color:${C.gold}; width:15px; height:15px; margin-top:3px; cursor:pointer; flex-shrink:0; }
      `}</style>

      <div style={{ display: "flex", minHeight: "100vh" }}>

        {/* ── LEFT PANEL ── */}
        <div style={{
          width: "42%", background: C.inkDark, position: "relative",
          overflow: "hidden", display: "flex", flexDirection: "column",
          justifyContent: "space-between", padding: "44px 52px", flexShrink: 0,
        }}>
          <div style={{
            position: "absolute", inset: 0, pointerEvents: "none",
            backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 79px, rgba(200,151,30,0.04) 80px)",
          }} />
          <div style={{
            position: "absolute", left: "-60px", top: "-60px",
            width: 320, height: 320, borderRadius: "50%",
            border: "1px solid rgba(200,151,30,0.07)", pointerEvents: "none",
          }} />
          <div style={{
            position: "absolute", right: "-80px", bottom: "-80px",
            width: 380, height: 380, borderRadius: "50%",
            border: "1px solid rgba(200,151,30,0.08)", pointerEvents: "none",
          }} />

          <MiniPaper style={{ position: "absolute", right: 36, top: "22%", width: 120 }} delay="0s" />
          <MiniPaper style={{ position: "absolute", right: 72, bottom: "28%", width: 95 }} delay="2.5s" />

          {/* Logo + back */}
          <div style={{ position: "relative", zIndex: 10 }}>
            <button className="back-link" onClick={onNavigateHome} style={{ marginBottom: 56 }}>
              ← Back to home
            </button>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 32, height: 32, position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ width: 28, height: 28, border: `2px solid ${C.goldLight}`, transform: "rotate(45deg)", position: "absolute" }} />
                <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 13, fontWeight: 700, color: C.goldLight, position: "relative", zIndex: 1 }}>G</span>
              </div>
              <div>
                <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 17, fontWeight: 800, color: C.white, letterSpacing: "-0.01em", lineHeight: 1 }}>GenResearch</div>
                <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 9.5, color: C.goldLight, letterSpacing: "0.18em", textTransform: "uppercase" }}>Academic AI Platform</div>
              </div>
            </div>
          </div>

          {/* Centre copy */}
          <div style={{ position: "relative", zIndex: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
              <div style={{ height: 1, width: 36, background: C.gold }} />
              <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, fontWeight: 600, color: C.gold, letterSpacing: "0.2em", textTransform: "uppercase" }}>Join Today</span>
            </div>
            <h1 style={{
              fontFamily: "'Playfair Display', serif",
              fontSize: "clamp(26px, 3vw, 42px)",
              fontWeight: 900, color: C.white,
              lineHeight: 1.1, letterSpacing: "-0.02em", marginBottom: 18,
            }}>
              Begin Your<br />
              <em style={{ color: C.goldLight }}>Research Journey.</em>
            </h1>
            <p style={{
              fontFamily: "'Crimson Pro', Georgia, serif",
              fontSize: 15, color: "rgba(245,240,232,0.60)",
              lineHeight: 1.8, maxWidth: 320,
            }}>
              Create your free account and unlock the full power of multi-agent
              AI for academic research — summaries, reviews, and citations in seconds.
            </p>
          </div>

          {/* Feature checklist */}
          <div style={{ position: "relative", zIndex: 10 }}>
            {[
              { icon: "✓", text: "Upload unlimited research papers" },
              { icon: "✓", text: "Run 4 specialized AI agents" },
              { icon: "✓", text: "Export citations in any format" },
              { icon: "✓", text: "Persistent research library" },
            ].map(item => (
              <div key={item.text} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <span style={{
                  width: 18, height: 18, borderRadius: "50%",
                  background: "rgba(90,138,60,0.25)", border: "1px solid rgba(90,138,60,0.4)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 10, color: "#7ecf5a", flexShrink: 0,
                }}>{item.icon}</span>
                <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: "rgba(245,240,232,0.55)" }}>
                  {item.text}
                </span>
              </div>
            ))}
            <div style={{ marginTop: 22, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: "rgba(200,151,30,0.35)", letterSpacing: "0.06em" }}>
              Ali Ahmed · Kaleem-Ullah Abbasi · COMSATS WAH · FYP 2025
            </div>
          </div>
        </div>

        {/* ── RIGHT PANEL — form ── */}
        <div style={{
          flex: 1, background: C.cream,
          display: "flex", flexDirection: "column",
          justifyContent: "center", alignItems: "center",
          padding: "48px 40px", position: "relative", overflowY: "auto",
        }}>
          <div style={{
            position: "absolute", inset: 0, pointerEvents: "none",
            backgroundImage: "repeating-linear-gradient(90deg, transparent, transparent 79px, rgba(139,105,20,0.025) 80px)",
          }} />

          <div style={{ width: "100%", maxWidth: 440, position: "relative", zIndex: 10 }}>

            {/* Header */}
            <div className="r-fade-1" style={{ marginBottom: 28, textAlign: "center" }}>
              <div style={{ display: "inline-flex", alignItems: "center", gap: 10, marginBottom: 18 }}>
                <div style={{ height: 1, width: 28, background: C.borderGold }} />
                <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, fontWeight: 600, color: C.gold, letterSpacing: "0.2em", textTransform: "uppercase" }}>New Account</span>
                <div style={{ height: 1, width: 28, background: C.borderGold }} />
              </div>
              <h2 style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: "clamp(24px, 2.8vw, 34px)",
                fontWeight: 900, color: C.inkDark,
                letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: 10,
              }}>Create Your<br /><em style={{ color: C.gold }}>Free Account</em></h2>
              <p style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14.5, color: C.inkLight, lineHeight: 1.7 }}>
                Already have an account?{" "}
                <button className="auth-text-link" onClick={onNavigateLogin}>Sign in here</button>
              </p>
            </div>

            <div className="r-fade-2" style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 26 }}>
              <div style={{ flex: 1, height: 1, background: C.border }} />
              <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 16, color: C.gold }}>✦</span>
              <div style={{ flex: 1, height: 1, background: C.border }} />
            </div>

            {error && (
              <div style={{
                marginBottom: 18, padding: "12px 16px",
                background: "rgba(160,82,45,0.08)",
                border: "1px solid rgba(160,82,45,0.25)", borderRadius: 3,
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 14, color: C.sienna,
                display: "flex", alignItems: "center", gap: 8,
              }}>
                <span>⚠</span> {error}
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
              <div className="r-fade-3">
                {/* Row: name + institution */}
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                  <FormInput id="reg-name" label="Full Name" placeholder="Ali Ahmed" value={fullName} onChange={setFullName} icon="👤" />
                  <FormInput id="reg-institution" label="Institution" placeholder="COMSATS University" value={institution} onChange={setInstitution} icon="🏛" />
                </div>
                <FormInput id="reg-email" label="Email Address" type="email" placeholder="you@university.edu" value={email} onChange={setEmail} icon="✉" />
                <FormInput id="reg-password" label="Password" type="password" placeholder="Min. 8 characters" value={password} onChange={setPassword} icon="🔒" />
                {password && <StrengthBar password={password} />}
                <div style={{ marginTop: password ? 14 : 0 }}>
                  <FormInput id="reg-confirm" label="Confirm Password" type="password" placeholder="Repeat your password" value={confirmPassword} onChange={setConfirmPassword} icon="🔒" />
                </div>
                {confirmPassword && password !== confirmPassword && (
                  <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.sienna, marginTop: -10, marginBottom: 14 }}>
                    ⚠ Passwords do not match
                  </div>
                )}
              </div>

              {/* Terms checkbox */}
              <div className="r-fade-4" style={{ marginBottom: 24, marginTop: 4 }}>
                <label className="checkbox-wrap">
                  <input type="checkbox" checked={agreed} onChange={e => setAgreed(e.target.checked)} />
                  <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkLight, lineHeight: 1.6 }}>
                    I agree to the{" "}
                    <span style={{ color: C.gold, textDecoration: "underline", cursor: "pointer" }}>Terms of Service</span>
                    {" "}and{" "}
                    <span style={{ color: C.gold, textDecoration: "underline", cursor: "pointer" }}>Privacy Policy</span>
                  </span>
                </label>
              </div>

              <div className="r-fade-5">
                <button
                  id="register-submit-btn"
                  type="submit"
                  className="reg-submit"
                  disabled={loading}
                >
                  {loading ? (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                      <span style={{ animation: "spin 1s linear infinite", display: "inline-block" }}>⟳</span>
                      Creating Account…
                    </span>
                  ) : "Create Account →"}
                </button>
              </div>
            </form>

            <div className="r-fade-5" style={{
              textAlign: "center", marginTop: 24,
              padding: "18px 0 0", borderTop: `1px solid ${C.border}`,
            }}>
              <p style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, color: C.inkLight }}>
                Already a researcher?{" "}
                <button id="go-to-login-btn" className="auth-text-link" onClick={onNavigateLogin}>
                  Sign in to your account
                </button>
              </p>
            </div>

          </div>
        </div>
      </div>
    </>
  );
}
