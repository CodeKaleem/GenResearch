"use client";
import { useState, useEffect, useRef } from "react";

// ═══════════════════════════════════════════════════════════════
//  DESIGN TOKENS
// ═══════════════════════════════════════════════════════════════
export const C = {
  cream:       "#f5f0e8",
  creamLight:  "#faf8f2",
  creamDark:   "#efe8d8",
  parchment:   "#e8dfc8",
  inkDark:     "#2c1f0e",
  inkMid:      "#5a3e20",
  inkLight:    "#7a6040",
  inkFaint:    "rgba(80,60,30,0.45)",
  gold:        "#8b6914",
  goldLight:   "#c8971e",
  goldFaint:   "rgba(139,105,20,0.10)",
  sienna:      "#a0522d",
  siennaFaint: "rgba(160,82,45,0.10)",
  umber:       "#6b5c38",
  white:       "#fffef9",
  border:      "rgba(180,160,120,0.22)",
  borderGold:  "rgba(139,105,20,0.30)",
  shadow:      "rgba(120,100,60,0.10)",
  shadowMd:    "rgba(120,100,60,0.18)",
  green:       "#5a8a3c",
  greenFaint:  "rgba(90,138,60,0.10)",
  red:         "#a0352d",
  redFaint:    "rgba(160,53,45,0.10)",
  blue:        "#2c5f8a",
  blueFaint:   "rgba(44,95,138,0.10)",
};

// ═══════════════════════════════════════════════════════════════
//  GLOBAL STYLES
// ═══════════════════════════════════════════════════════════════
export const globalStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,800;0,900;1,700&family=Crimson+Pro:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }
  body { background: ${C.cream}; color: ${C.inkDark}; font-family: 'Crimson Pro', Georgia, serif; overflow-x: hidden; }
  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: ${C.cream}; }
  ::-webkit-scrollbar-thumb { background: rgba(139,105,20,0.28); border-radius: 3px; }
  @keyframes fadeUp   { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:translateY(0)} }
  @keyframes fadeIn   { from{opacity:0} to{opacity:1} }
  @keyframes adminPulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(1.3)} }
  @keyframes spin     { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
  @keyframes shimmer  { 0%{background-position:-400px 0} 100%{background-position:400px 0} }
  @keyframes slideIn  { from{opacity:0;transform:translateX(-12px)} to{opacity:1;transform:translateX(0)} }
  .a1{animation:fadeUp .6s .04s both}
  .a2{animation:fadeUp .6s .10s both}
  .a3{animation:fadeUp .6s .18s both}
  .a4{animation:fadeUp .6s .27s both}
  .a5{animation:fadeUp .6s .38s both}
  .a6{animation:fadeUp .6s .50s both}
  .btn-ink  { background:${C.inkDark};color:${C.cream};border:none;border-radius:3px;padding:9px 20px;font-size:12px;font-family:'Crimson Pro',Georgia,serif;font-weight:600;cursor:pointer;letter-spacing:.08em;text-transform:uppercase;transition:all .22s; }
  .btn-ink:hover  { background:${C.gold};transform:translateY(-1px);box-shadow:0 5px 16px rgba(139,105,20,.28); }
  .btn-gold { background:${C.gold};color:${C.white};border:none;border-radius:3px;padding:9px 20px;font-size:12px;font-family:'Crimson Pro',Georgia,serif;font-weight:600;cursor:pointer;letter-spacing:.08em;text-transform:uppercase;transition:all .22s; }
  .btn-gold:hover { background:#6b5010;transform:translateY(-1px);box-shadow:0 5px 16px rgba(139,105,20,.32); }
  .btn-ghost{ background:transparent;color:${C.inkDark};border:1.5px solid rgba(44,31,14,.22);border-radius:3px;padding:8px 16px;font-size:12px;font-family:'Crimson Pro',Georgia,serif;font-weight:500;cursor:pointer;transition:all .22s; }
  .btn-ghost:hover{ border-color:${C.gold};color:${C.gold}; }
  .btn-red  { background:${C.red};color:#fff;border:none;border-radius:3px;padding:7px 14px;font-size:11px;font-family:'Crimson Pro',Georgia,serif;font-weight:600;cursor:pointer;letter-spacing:.06em;transition:all .22s; }
  .btn-red:hover { background:#7a1f1a;transform:translateY(-1px); }
  .btn-green{ background:${C.green};color:#fff;border:none;border-radius:3px;padding:7px 14px;font-size:11px;font-family:'Crimson Pro',Georgia,serif;font-weight:600;cursor:pointer;letter-spacing:.06em;transition:all .22s; }
  .btn-green:hover{ background:#3d6128;transform:translateY(-1px); }
  .card { background:${C.creamLight};border:1px solid ${C.border};border-radius:4px; }
  .divider { height:1px;background:${C.border};margin:0; }
`;

// ═══════════════════════════════════════════════════════════════
//  ANIMATED COUNTER
// ═══════════════════════════════════════════════════════════════
export function Num({ to, prefix = "", suffix = "", duration = 1600 }: {
  to: number; prefix?: string; suffix?: string; duration?: number;
}) {
  const [v, setV] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const started = useRef(false);
  useEffect(() => {
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && !started.current) {
        started.current = true;
        const t0 = performance.now();
        const tick = (n: number) => {
          const p = Math.min((n - t0) / duration, 1);
          setV(Math.round((1 - Math.pow(1 - p, 3)) * to));
          if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      }
    }, { threshold: 0.4 });
    if (ref.current) io.observe(ref.current);
    return () => io.disconnect();
  }, [to, duration]);
  return <span ref={ref}>{prefix}{v.toLocaleString()}{suffix}</span>;
}

// ═══════════════════════════════════════════════════════════════
//  PROGRESS BAR
// ═══════════════════════════════════════════════════════════════
export function Bar({ value, color = C.gold, animate = true }: {
  value: number; color?: string; animate?: boolean;
}) {
  const [w, setW] = useState(0);
  useEffect(() => { const t = setTimeout(() => setW(value), 300); return () => clearTimeout(t); }, [value]);
  return (
    <div style={{ height: 5, background: C.creamDark, border: `1px solid ${C.border}`, borderRadius: 2, overflow: "hidden" }}>
      <div style={{ height: "100%", width: `${animate ? w : value}%`, background: `linear-gradient(90deg, ${color}, ${color}cc)`, borderRadius: 2, transition: animate ? "width 1.4s cubic-bezier(.4,0,.2,1)" : "none" }} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
//  SPARKLINE
// ═══════════════════════════════════════════════════════════════
export function Sparkline({ data, color = C.gold, h = 32 }: { data: number[]; color?: string; h?: number }) {
  const w = 80;
  const max = Math.max(...data); const min = Math.min(...data); const range = max - min || 1;
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(" ");
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
      <polyline points={`0,${h} ${pts} ${w},${h}`} fill={`${color}22`} stroke="none" />
    </svg>
  );
}

// ═══════════════════════════════════════════════════════════════
//  STATUS BADGE
// ═══════════════════════════════════════════════════════════════
export function Badge({ label, color, pulse = false }: { label: string; color: string; pulse?: boolean }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "3px 10px", background: `${color}18`, border: `1px solid ${color}44`, borderRadius: 2, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10.5, fontWeight: 600, color, letterSpacing: "0.08em", textTransform: "uppercase" }}>
      {pulse && <span style={{ width: 6, height: 6, borderRadius: "50%", background: color, animation: "adminPulse 1.6s ease infinite", flexShrink: 0 }} />}
      {label}
    </span>
  );
}

// ═══════════════════════════════════════════════════════════════
//  SECTION HEADER
// ═══════════════════════════════════════════════════════════════
export function SectionHead({ label, action, onAction }: { label: string; action?: string; onAction?: () => void }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ height: 1, width: 22, background: C.gold }} />
        <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10.5, fontWeight: 600, color: C.gold, letterSpacing: "0.18em", textTransform: "uppercase" }}>{label}</span>
      </div>
      {action && (
        <button onClick={onAction} style={{ background: "transparent", border: `1px solid ${C.border}`, borderRadius: 3, padding: "5px 13px", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.inkLight, cursor: "pointer", letterSpacing: "0.04em", transition: "all .2s" }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = C.gold; e.currentTarget.style.color = C.gold; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.color = C.inkLight; }}
        >{action}</button>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
//  PAGE WRAPPER
// ═══════════════════════════════════════════════════════════════
export function PageTitle({ title, sub, actions }: { title: string; sub?: string; actions?: React.ReactNode }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 14, marginBottom: 28 }}>
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ height: 1, width: 24, background: C.gold }} />
          <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10.5, fontWeight: 600, color: C.gold, letterSpacing: "0.18em", textTransform: "uppercase" }}>{sub || "Admin Console"}</span>
        </div>
        <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: "clamp(22px,2.8vw,34px)", fontWeight: 900, color: C.inkDark, letterSpacing: "-0.02em", lineHeight: 1.1 }}>{title}</h1>
      </div>
      {actions && <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>{actions}</div>}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
//  MODAL
// ═══════════════════════════════════════════════════════════════
export function Modal({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(44,31,14,0.38)", backdropFilter: "blur(4px)" }} onClick={onClose}>
      <div style={{ background: C.creamLight, border: `1px solid ${C.borderGold}`, borderRadius: 6, padding: "28px 32px", minWidth: 440, maxWidth: 600, width: "90%", boxShadow: `0 24px 64px ${C.shadowMd}`, animation: "fadeUp .3s both" }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 22 }}>
          <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 800, color: C.inkDark }}>{title}</span>
          <button onClick={onClose} style={{ background: "transparent", border: "none", cursor: "pointer", color: C.inkLight, fontSize: 18, lineHeight: 1 }}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
//  FORM FIELD
// ═══════════════════════════════════════════════════════════════
export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <label style={{ display: "block", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.gold, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>{label}</label>
      {children}
    </div>
  );
}

export const inputStyle: React.CSSProperties = {
  width: "100%", padding: "9px 12px",
  border: `1.5px solid ${C.border}`, borderRadius: 3,
  background: C.white, fontFamily: "'Crimson Pro', Georgia, serif",
  fontSize: 13.5, color: C.inkDark, outline: "none",
};

export const selectStyle: React.CSSProperties = {
  ...({ width: "100%", padding: "9px 12px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: C.white, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkDark, outline: "none", cursor: "pointer" } as React.CSSProperties),
};

// ═══════════════════════════════════════════════════════════════
//  USER ROW (user management table row)
// ═══════════════════════════════════════════════════════════════
export interface UserRow {
  id: string; name: string; email: string; role: string;
  papers: number; tasks: number; status: "active" | "inactive" | "suspended";
  joined: string;
}
export function UserTableRow({ user }: { user: UserRow }) {
  const [hov, setHov] = useState(false);
  const statusColor = { active: C.green, inactive: C.inkLight, suspended: C.red }[user.status];
  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{
        display: "grid",
        gridTemplateColumns: "2fr 2fr 1fr 60px 60px 90px 90px",
        gap: 0,
        padding: "13px 16px",
        background: hov ? C.white : "transparent",
        borderBottom: `1px solid ${C.border}`,
        transition: "background .2s", cursor: "default",
        alignItems: "center",
      }}>
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: C.inkDark, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Playfair Display', serif", fontSize: 11, fontWeight: 700, color: C.cream, flexShrink: 0 }}>{user.name.charAt(0)}</div>
          <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, fontWeight: 500, color: C.inkDark }}>{user.name}</span>
        </div>
      </div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight }}>{user.email}</div>
      <div>
        <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.umber, background: `${C.umber}14`, border: `1px solid ${C.umber}33`, borderRadius: 2, padding: "2px 8px", letterSpacing: "0.06em", textTransform: "uppercase" }}>{user.role}</span>
      </div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight, textAlign: "center" }}>{user.papers}</div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight, textAlign: "center" }}>{user.tasks}</div>
      <div><Badge label={user.status} color={statusColor} pulse={user.status === "active"} /></div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, color: C.inkLight }}>{user.joined}</div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
//  AGENT HEALTH ROW
// ═══════════════════════════════════════════════════════════════
export interface AgentHealth {
  name: string; status: "online" | "degraded" | "offline";
  requests: number; avgTime: string; errorRate: number; uptime: number;
}
export function AgentHealthRow({ agent }: { agent: AgentHealth }) {
  const [hov, setHov] = useState(false);
  const statusColor = { online: C.green, degraded: C.goldLight, offline: C.red }[agent.status];
  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{ display: "grid", gridTemplateColumns: "2fr 90px 80px 80px 120px 120px", padding: "13px 16px", background: hov ? C.white : "transparent", borderBottom: `1px solid ${C.border}`, transition: "background .2s", cursor: "default", alignItems: "center", gap: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: statusColor, boxShadow: agent.status === "online" ? `0 0 8px ${statusColor}` : "none", animation: agent.status === "online" ? "adminPulse 2s ease infinite" : "none", flexShrink: 0 }} />
        <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, fontWeight: 500, color: C.inkDark }}>{agent.name}</span>
      </div>
      <div><Badge label={agent.status} color={statusColor} /></div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight, textAlign: "right" }}>{agent.requests.toLocaleString()}</div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight, textAlign: "right" }}>{agent.avgTime}</div>
      <div style={{ paddingRight: 12 }}><Bar value={agent.errorRate} color={agent.errorRate > 5 ? C.red : C.green} /></div>
      <div><Bar value={agent.uptime} color={C.gold} /></div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
//  LOG ROW
// ═══════════════════════════════════════════════════════════════
export interface LogEntry { id: string; level: "info" | "warn" | "error" | "success"; message: string; time: string; agent?: string; }
export function LogRow({ entry }: { entry: LogEntry }) {
  const levelColor = { info: C.blue, warn: C.goldLight, error: C.red, success: C.green }[entry.level];
  const levelIcon = { info: "ℹ", warn: "⚠", error: "✕", success: "✓" }[entry.level];
  return (
    <div style={{ display: "flex", gap: 12, alignItems: "flex-start", padding: "9px 16px", borderBottom: `1px solid ${C.border}`, fontFamily: "'Crimson Pro', Georgia, serif" }}>
      <span style={{ fontSize: 12, color: levelColor, flexShrink: 0, marginTop: 1 }}>{levelIcon}</span>
      <div style={{ flex: 1 }}>
        <span style={{ fontSize: 13, color: C.inkDark }}>{entry.message}</span>
        {entry.agent && <span style={{ fontSize: 11, color: C.gold, marginLeft: 8, background: C.goldFaint, border: `1px solid ${C.borderGold}`, borderRadius: 2, padding: "0px 6px" }}>{entry.agent}</span>}
      </div>
      <span style={{ fontSize: 11, color: C.inkLight, flexShrink: 0 }}>{entry.time}</span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
//  COST ROW
// ═══════════════════════════════════════════════════════════════
export function CostRow({ label, tokens, cost, pct, color }: { label: string; tokens: string; cost: string; pct: number; color: string; }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
        <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkDark }}>{label}</span>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.inkLight }}>{tokens}</span>
          <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, fontWeight: 700, color }}>{cost}</span>
        </div>
      </div>
      <Bar value={pct} color={color} />
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
//  STAT CARD
// ═══════════════════════════════════════════════════════════════
export interface StatCardProps { icon: string; label: string; value: number; prefix?: string; suffix?: string; sub: string; trend?: string; trendUp?: boolean; color?: string; sparkData?: number[]; }
export function StatCard({ icon, label, value, prefix="", suffix="", sub, trend, trendUp, color=C.gold, sparkData }: StatCardProps) {
  const [hov, setHov] = useState(false);
  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{ background: C.creamLight, border: `1px solid ${hov ? C.borderGold : C.border}`, borderRadius: 4, padding: "22px 20px", transition: "all .28s ease", transform: hov ? "translateY(-3px)" : "none", boxShadow: hov ? `0 8px 28px ${C.shadow}` : "none", cursor: "default", position: "relative", overflow: "hidden" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <div style={{ width: 38, height: 38, borderRadius: 4, background: `${color}18`, border: `1px solid ${color}33`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>{icon}</div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
          {trend && <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, fontWeight: 600, color: trendUp ? C.green : C.red }}>{trend}</span>}
          {sparkData && <Sparkline data={sparkData} color={color} />}
        </div>
      </div>
      <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 34, fontWeight: 900, color: C.inkDark, lineHeight: 1, marginBottom: 4 }}><Num to={value} prefix={prefix} suffix={suffix} /></div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color, letterSpacing: "0.10em", textTransform: "uppercase", marginBottom: 2 }}>{label}</div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight }}>{sub}</div>
    </div>
  );
}
