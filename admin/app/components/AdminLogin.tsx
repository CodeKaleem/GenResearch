"use client";
import { useState } from "react";
import { supabase } from "../../lib/supabase";
import { C, globalStyles } from "./shared";

function FormField({ id, label, type = "text", placeholder, value, onChange, icon, error }: {
  id: string; label: string; type?: string; placeholder: string;
  value: string; onChange: (v: string) => void; icon: string; error?: string;
}) {
  const [f, setF] = useState(false);
  return (
    <div style={{ marginBottom: 20 }}>
      <label htmlFor={id} style={{ display: "block", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, fontWeight: 600, color: C.gold, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 7 }}>{label}</label>
      <div style={{ position: "relative" }}>
        <span style={{ position: "absolute", left: 13, top: "50%", transform: "translateY(-50%)", fontSize: 15, color: f ? C.gold : C.inkLight, transition: "color .2s", pointerEvents: "none" }}>{icon}</span>
        <input id={id} type={type} placeholder={placeholder} value={value}
          onChange={e => onChange(e.target.value)} onFocus={() => setF(true)} onBlur={() => setF(false)}
          style={{ width: "100%", padding: "13px 14px 13px 40px", border: `1.5px solid ${error ? C.red : f ? C.gold : C.border}`, borderRadius: 3, background: f ? C.white : C.creamLight, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 15, color: C.inkDark, outline: "none", transition: "all .25s", boxShadow: f ? "0 0 0 3px rgba(139,105,20,0.08)" : "none" }} />
      </div>
      {error && <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.red, marginTop: 5 }}>⚠ {error}</div>}
    </div>
  );
}

const extraCSS = `
  ${globalStyles}
  @keyframes floatPaper { 0%,100%{transform:translateY(0) rotate(-1.5deg)} 50%{transform:translateY(-12px) rotate(1deg)} }
  .af1{animation:fadeUp .65s .08s both} .af2{animation:fadeUp .65s .18s both}
  .af3{animation:fadeUp .65s .30s both} .af4{animation:fadeUp .65s .44s both} .af5{animation:fadeUp .65s .58s both}
  .al-submit{width:100%;padding:14px 24px;background:${C.inkDark};color:${C.cream};border:none;border-radius:3px;font-family:'Crimson Pro',Georgia,serif;font-size:13.5px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;cursor:pointer;transition:all .3s}
  .al-submit:hover:not(:disabled){background:${C.gold};transform:translateY(-2px);box-shadow:0 8px 28px rgba(139,105,20,0.32)}
  .al-submit:disabled{opacity:.7;cursor:not-allowed}
  .al-link{font-family:'Crimson Pro',Georgia,serif;font-size:14px;color:${C.gold};background:none;border:none;cursor:pointer;text-decoration:underline;text-underline-offset:2px;transition:color .2s;padding:0}
  .al-link:hover{color:${C.goldLight}}
  .chk-wrap{display:flex;align-items:center;gap:9px;cursor:pointer}
  .chk-wrap input[type="checkbox"]{accent-color:${C.gold};width:15px;height:15px;cursor:pointer}
`;

export default function AdminLogin({ onLoginSuccess }: {
  onLoginSuccess?: () => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fErr, setFErr] = useState<{ email?: string; password?: string }>({});

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const eErr = !email.trim() ? "Email is required." : !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? "Enter a valid email." : undefined;
    const pErr = !password ? "Password is required." : password.length < 6 ? "Min 6 characters." : undefined;
    setFErr({ email: eErr, password: pErr });
    if (eErr || pErr) return;

    setLoading(true);
    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
      if (authError) { setError(authError.message); setLoading(false); return; }

      // Verify admin role — reject non-admin users
      const role = data.user?.user_metadata?.role;
      if (role !== "admin") {
        await supabase.auth.signOut();
        setError("Access denied. This console is restricted to administrators.");
        setLoading(false);
        return;
      }

      onLoginSuccess?.();
    } catch { setError("An unexpected error occurred."); }
    finally { setLoading(false); }
  };

  return (
    <>
      <style>{extraCSS}</style>
      <div style={{ display: "flex", minHeight: "100vh" }}>
        {/* LEFT PANEL */}
        <div style={{ width: "45%", background: C.inkDark, position: "relative", overflow: "hidden", display: "flex", flexDirection: "column", justifyContent: "space-between", padding: "44px 52px", flexShrink: 0 }}>
          <div style={{ position: "absolute", inset: 0, pointerEvents: "none", backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 79px, rgba(200,151,30,0.04) 80px)" }} />
          <div style={{ position: "absolute", right: -80, bottom: -80, width: 380, height: 380, borderRadius: "50%", border: "1px solid rgba(200,151,30,0.08)", pointerEvents: "none" }} />
          <div style={{ position: "absolute", right: -40, bottom: -40, width: 260, height: 260, borderRadius: "50%", border: "1px solid rgba(200,151,30,0.12)", pointerEvents: "none" }} />
          {/* Floating papers */}
          {[{ r: 40, t: "18%", w: 130, d: "0s" }, { r: 80, t: "42%", w: 100, d: "2s" }].map((p, i) => (
            <div key={i} style={{ position: "absolute", right: p.r, top: p.t, width: p.w, background: "rgba(255,254,249,0.06)", border: "1px solid rgba(200,151,30,0.15)", borderRadius: 3, padding: "12px 14px", animation: "floatPaper 7s ease-in-out infinite", animationDelay: p.d }}>
              {[80, 60, 90, 50].map((w2, j) => <div key={j} style={{ height: 4, background: j === 0 ? "rgba(200,151,30,0.4)" : "rgba(200,151,30,0.12)", borderRadius: 2, width: `${w2}%`, marginBottom: 5 }} />)}
            </div>
          ))}
          {/* Logo */}
          <div style={{ position: "relative", zIndex: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 32, height: 32, position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ width: 28, height: 28, border: `2px solid ${C.goldLight}`, transform: "rotate(45deg)", position: "absolute" }} />
                <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 13, fontWeight: 700, color: C.goldLight, position: "relative", zIndex: 1 }}>G</span>
              </div>
              <div>
                <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 17, fontWeight: 800, color: C.white, lineHeight: 1 }}>GenResearch</div>
                <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 9.5, color: C.red, letterSpacing: "0.18em", textTransform: "uppercase", fontWeight: 600 }}>Admin Console</div>
              </div>
            </div>
          </div>
          {/* Copy */}
          <div style={{ position: "relative", zIndex: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
              <div style={{ height: 1, width: 36, background: C.gold }} />
              <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, fontWeight: 600, color: C.gold, letterSpacing: "0.2em", textTransform: "uppercase" }}>Administrator Access</span>
            </div>
            <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: "clamp(28px,3.5vw,44px)", fontWeight: 900, color: C.white, lineHeight: 1.1, letterSpacing: "-0.02em", marginBottom: 18 }}>
              System<br /><em style={{ color: C.goldLight }}>Control Center.</em>
            </h1>
            <p style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 15.5, color: "rgba(245,240,232,0.62)", lineHeight: 1.8, maxWidth: 340 }}>
              Sign in to manage users, monitor agents, track costs, and configure the GenResearch platform.
            </p>
          </div>
          {/* Features */}
          <div style={{ position: "relative", zIndex: 10 }}>
            {[{ i: "◈", t: "User & role management" }, { i: "◉", t: "Real-time agent monitoring" }, { i: "◎", t: "API cost tracking & analytics" }].map(f => (
              <div key={f.i} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                <span style={{ color: C.goldLight, fontSize: 13 }}>{f.i}</span>
                <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: "rgba(245,240,232,0.55)" }}>{f.t}</span>
              </div>
            ))}
            <div style={{ marginTop: 24, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: "rgba(200,151,30,0.4)", letterSpacing: "0.06em" }}>Ali Ahmed · Kaleem-Ullah Abbasi · COMSATS WAH · FYP 2025</div>
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div style={{ flex: 1, background: C.cream, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "60px 40px", position: "relative", overflowY: "auto" }}>
          <div style={{ position: "absolute", inset: 0, pointerEvents: "none", backgroundImage: "repeating-linear-gradient(90deg, transparent, transparent 79px, rgba(139,105,20,0.025) 80px)" }} />
          <div style={{ width: "100%", maxWidth: 420, position: "relative", zIndex: 10 }}>
            {/* Header */}
            <div className="af1" style={{ marginBottom: 36, textAlign: "center" }}>
              <div style={{ display: "inline-flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
                <div style={{ height: 1, width: 28, background: C.borderGold }} />
                <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, fontWeight: 600, color: C.gold, letterSpacing: "0.2em", textTransform: "uppercase" }}>Admin Login</span>
                <div style={{ height: 1, width: 28, background: C.borderGold }} />
              </div>
              <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: "clamp(26px,3vw,36px)", fontWeight: 900, color: C.inkDark, letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: 10 }}>
                Sign In to<br /><em style={{ color: C.gold }}>Admin Console</em>
              </h2>
              <p style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 15, color: C.inkLight, lineHeight: 1.7 }}>
                Authorized personnel only. Access is monitored and logged.
              </p>
            </div>
            {/* Rule */}
            <div className="af2" style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 32 }}>
              <div style={{ flex: 1, height: 1, background: C.border }} />
              <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 16, color: C.gold }}>✦</span>
              <div style={{ flex: 1, height: 1, background: C.border }} />
            </div>
            {/* Error */}
            {error && (
              <div style={{ marginBottom: 20, padding: "12px 16px", background: C.redFaint, border: `1px solid ${C.red}44`, borderRadius: 3, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, color: C.red, display: "flex", alignItems: "center", gap: 8 }}>
                <span>⚠</span> {error}
              </div>
            )}
            {/* Form */}
            <form onSubmit={handleSubmit} noValidate>
              <div className="af3">
                <FormField id="admin-login-email" label="Email Address" type="email" placeholder="admin@genresearch.ai" value={email} onChange={v => { setEmail(v); setFErr(p => ({ ...p, email: undefined })); }} icon="✉" error={fErr.email} />
                <FormField id="admin-login-password" label="Password" type="password" placeholder="Enter your password" value={password} onChange={v => { setPassword(v); setFErr(p => ({ ...p, password: undefined })); }} icon="🔒" error={fErr.password} />
              </div>
              <div className="af4" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 28 }}>
                <label className="chk-wrap">
                  <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />
                  <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, color: C.inkLight }}>Remember me</span>
                </label>
                <button type="button" className="al-link" style={{ fontSize: 13 }}>Forgot password?</button>
              </div>
              <div className="af5">
                <button id="admin-login-submit-btn" type="submit" className="al-submit" disabled={loading}>
                  {loading ? <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}><span style={{ animation: "spin 1s linear infinite", display: "inline-block" }}>⟳</span> Signing In…</span> : "Sign In →"}
                </button>
              </div>
            </form>
            {/* Footer */}
            <div className="af5" style={{ textAlign: "center", marginTop: 32, paddingTop: 18, borderTop: `1px solid ${C.border}` }}>
              <div style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "8px 16px", background: C.goldFaint, border: `1px solid ${C.borderGold}`, borderRadius: 3 }}>
                <span style={{ fontSize: 14 }}>🔐</span>
                <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight }}>Protected by Supabase Auth · TLS encrypted</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
