"use client";

import { useState, useEffect } from "react";

const C = {
  cream: "#f5f0e8", creamLight: "#faf8f2", creamDark: "#efe8d8",
  inkDark: "#2c1f0e", inkMid: "#5a3e20", inkLight: "#7a6040",
  gold: "#8b6914", goldLight: "#c8971e", goldFaint: "rgba(139,105,20,0.09)",
  sienna: "#a0522d", umber: "#6b5c38", white: "#fffef9",
  border: "rgba(180,160,120,0.22)", green: "#5a8a3c",
  shadow: "rgba(120,100,60,0.10)",
  borderGold: "rgba(139,105,20,0.4)",
};

// ── Animated number ───────────────────────────────────────────
function Num({ to, duration = 1400 }: { to: number; duration?: number }) {
  const [v, setV] = useState(0);
  useEffect(() => {
    const t0 = performance.now();
    const tick = (n: number) => {
      const p = Math.min((n - t0) / duration, 1);
      setV(Math.round((1 - Math.pow(1 - p, 3)) * to));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [to, duration]);
  return <>{v.toLocaleString()}</>;
}

// ── Mini progress bar ─────────────────────────────────────────
function MiniBar({ value, color = C.gold }: { value: number; color?: string }) {
  return (
    <div style={{ height: 4, background: C.creamDark, border: `1px solid ${C.border}`, borderRadius: 2, overflow: "hidden" }}>
      <div style={{
        height: "100%", width: `${value}%`,
        background: `linear-gradient(90deg, ${color}, ${color}bb)`,
        borderRadius: 2, transition: "width 1.2s cubic-bezier(.4,0,.2,1)",
      }} />
    </div>
  );
}

// ── Sidebar nav item ──────────────────────────────────────────
function SideItem({ icon, label, active, badge, onClick }: {
  icon: string; label: string; active?: boolean; badge?: number; onClick?: () => void;
}) {
  const [hov, setHov] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        width: "100%", textAlign: "left",
        display: "flex", alignItems: "center", gap: 10,
        padding: "10px 16px", margin: "1px 0",
        background: active ? C.inkDark : hov ? "rgba(139,105,20,0.07)" : "transparent",
        border: "none", borderRadius: 3, cursor: "pointer",
        transition: "all .2s",
      }}
    >
      <span style={{ fontSize: 14, flexShrink: 0, opacity: active ? 1 : 0.75 }}>{icon}</span>
      <span style={{
        flex: 1,
        fontFamily: "'Crimson Pro', Georgia, serif",
        fontSize: 14, fontWeight: active ? 600 : 400,
        color: active ? C.cream : hov ? C.gold : C.inkLight,
        letterSpacing: "0.02em",
      }}>{label}</span>
      {badge !== undefined && badge > 0 && (
        <span style={{
          fontSize: 10, fontWeight: 700,
          background: active ? C.goldLight : C.gold,
          color: active ? C.inkDark : C.cream,
          borderRadius: 10, padding: "1px 7px",
          fontFamily: "'Crimson Pro', Georgia, serif",
        }}>{badge}</span>
      )}
    </button>
  );
}

// ── Task card ─────────────────────────────────────────────────
type TaskStatus = "completed" | "processing" | "failed";
interface Task {
  id: string; title: string; agent: string; papers: number;
  status: TaskStatus; time: string; score?: number;
}

function TaskCard({ task, onOpen }: { task: Task; onOpen: () => void }) {
  const [hov, setHov] = useState(false);
  const statusStyle: Record<TaskStatus, { label: string; color: string; bg: string }> = {
    completed:  { label: "Completed",  color: C.green,   bg: "rgba(90,138,60,0.09)" },
    processing: { label: "Processing", color: C.gold,    bg: C.goldFaint },
    failed:     { label: "Failed",     color: C.sienna,  bg: "rgba(160,82,45,0.09)" },
  };
  const s = statusStyle[task.status];

  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: "18px 20px",
        background: hov ? C.white : C.creamLight,
        border: `1px solid ${hov ? C.borderGold : C.border}`,
        borderRadius: 4, cursor: "pointer", transition: "all .25s",
        transform: hov ? "translateY(-2px)" : "none",
        boxShadow: hov ? `0 6px 20px ${C.shadow}` : "none",
      }}
      onClick={onOpen}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div style={{ flex: 1, paddingRight: 12 }}>
          <div style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: 15, fontWeight: 700, color: C.inkDark,
            marginBottom: 4, lineHeight: 1.3,
          }}>{task.title}</div>
          <div style={{
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 12, color: C.inkLight, letterSpacing: "0.04em",
          }}>{task.agent} · {task.papers} paper{task.papers > 1 ? "s" : ""}</div>
        </div>
        <div style={{
          padding: "4px 10px", borderRadius: 2, flexShrink: 0,
          background: s.bg, border: `1px solid ${s.color}33`,
          fontFamily: "'Crimson Pro', Georgia, serif",
          fontSize: 11, fontWeight: 600, color: s.color,
          letterSpacing: "0.08em", textTransform: "uppercase",
        }}>{s.label}</div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.inkLight }}>{task.time}</span>
        {task.score !== undefined && (
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.inkLight }}>Quality</span>
            <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, fontWeight: 700, color: C.gold }}>{task.score}</span>
            <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.inkLight }}>/100</span>
          </div>
        )}
        {task.status === "processing" && (
          <div style={{
            display: "flex", alignItems: "center", gap: 5,
            fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.gold,
          }}>
            <span style={{ animation: "spin 1.2s linear infinite", display: "inline-block" }}>⟳</span>
            In progress…
          </div>
        )}
      </div>
    </div>
  );
}

// ── Activity item ─────────────────────────────────────────────
function ActivityItem({ icon, text, time, color }: {
  icon: string; text: string; time: string; color: string;
}) {
  return (
    <div style={{ display: "flex", gap: 12, paddingBottom: 14, marginBottom: 2 }}>
      <div style={{
        width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
        background: `${color}18`, border: `1px solid ${color}33`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 13,
      }}>{icon}</div>
      <div style={{ flex: 1 }}>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkDark, lineHeight: 1.55 }}
          dangerouslySetInnerHTML={{ __html: text.replace(/\*\*(.*?)\*\*/g, `<strong style="color:${C.inkMid}">$1</strong>`) }} />
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.inkLight, marginTop: 2 }}>{time}</div>
      </div>
    </div>
  );
}

// ── Stat card ─────────────────────────────────────────────────
function StatCard({ icon, label, value, sub, trend, color = C.gold }: {
  icon: string; label: string; value: number; sub: string; trend?: string; color?: string;
}) {
  return (
    <div style={{
      background: C.creamLight, border: `1px solid ${C.border}`,
      borderRadius: 4, padding: "22px 22px",
      transition: "all .3s", cursor: "default",
    }}
      onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = C.borderGold; (e.currentTarget as HTMLDivElement).style.transform = "translateY(-3px)"; (e.currentTarget as HTMLDivElement).style.boxShadow = `0 8px 24px ${C.shadow}`; }}
      onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = C.border; (e.currentTarget as HTMLDivElement).style.transform = "none"; (e.currentTarget as HTMLDivElement).style.boxShadow = "none"; }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <div style={{
          width: 38, height: 38, borderRadius: 4,
          background: `${color}18`, border: `1px solid ${color}33`,
          display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16,
        }}>{icon}</div>
        {trend && (
          <span style={{
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 11.5, color: trend.startsWith("+") ? C.green : C.sienna,
            fontWeight: 600,
          }}>{trend}</span>
        )}
      </div>
      <div style={{
        fontFamily: "'Playfair Display', serif",
        fontSize: 32, fontWeight: 900, color: C.inkDark,
        lineHeight: 1, marginBottom: 4,
      }}>
        <Num to={value} />
      </div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.gold, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 2 }}>{label}</div>
      <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight }}>{sub}</div>
    </div>
  );
}

// ── Agent usage bar ───────────────────────────────────────────
function AgentUsageRow({ label, pct, color, count }: { label: string; pct: number; color: string; count: number }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
        <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkDark }}>{label}</span>
        <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight }}>{count} tasks · {pct}%</span>
      </div>
      <MiniBar value={pct} color={color} />
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────
export default function Dashboard({ onNavigateHome }: { onNavigateHome?: () => void }) {
  const [activeNav, setActiveNav] = useState("Dashboard");
  const [greeting, setGreeting] = useState("Good morning");

  useEffect(() => {
    const h = new Date().getHours();
    if (h < 12) setGreeting("Good morning");
    else if (h < 17) setGreeting("Good afternoon");
    else setGreeting("Good evening");
  }, []);

  const tasks: Task[] = [
    { id: "1", title: "Transformer Architectures in NLP", agent: "Summarization Agent", papers: 3, status: "completed", time: "Today, 2:14 PM", score: 87 },
    { id: "2", title: "BERT vs GPT Comparative Study", agent: "Literature Review Agent", papers: 5, status: "processing", time: "Today, 3:01 PM" },
    { id: "3", title: "Federated Learning Survey", agent: "Summarization Agent", papers: 4, status: "completed", time: "Yesterday", score: 92 },
    { id: "4", title: "Computer Vision Benchmarks", agent: "Citation Agent", papers: 2, status: "failed", time: "2 days ago" },
    { id: "5", title: "Reinforcement Learning in Robotics", agent: "Proposal Drafting Agent", papers: 6, status: "completed", time: "3 days ago", score: 79 },
  ];

  const navItems = [
    { icon: "⌂", label: "Dashboard" },
    { icon: "↑", label: "Upload Papers" },
    { icon: "⬡", label: "My Papers", badge: 12 },
    { icon: "⚙", label: "Agents" },
    { icon: "◈", label: "Results", badge: 3 },
    { icon: "◎", label: "Citations" },
    { icon: "⊞", label: "Library" },
    { icon: "◌", label: "Settings" },
  ];

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,800;0,900;1,700&family=Crimson+Pro:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { height: 100%; }
        body { background: #f5f0e8; color: #2c1f0e; font-family: 'Crimson Pro', Georgia, serif; overflow-x: hidden; }
        ::-webkit-scrollbar { width: 4px; } ::-webkit-scrollbar-track { background: #f5f0e8; } ::-webkit-scrollbar-thumb { background: rgba(139,105,20,0.28); border-radius: 3px; }
        @keyframes fadeUp  { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        @keyframes spin    { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        @keyframes pulse   { 0%,100%{opacity:1} 50%{opacity:.4} }
        .btn-ink{background:#2c1f0e;color:#f5f0e8;border:none;border-radius:3px;padding:10px 22px;font-size:12.5px;font-family:'Crimson Pro',Georgia,serif;font-weight:600;cursor:pointer;letter-spacing:.08em;text-transform:uppercase;transition:all .25s}
        .btn-ink:hover{background:#8b6914;transform:translateY(-2px);box-shadow:0 6px 20px rgba(139,105,20,0.28)}
        .btn-gold{background:#8b6914;color:#fffef9;border:none;border-radius:3px;padding:10px 22px;font-size:12.5px;font-family:'Crimson Pro',Georgia,serif;font-weight:600;cursor:pointer;letter-spacing:.08em;text-transform:uppercase;transition:all .25s}
        .btn-gold:hover{background:#6b5010;transform:translateY(-2px);box-shadow:0 6px 20px rgba(139,105,20,0.35)}
        .btn-outline{background:transparent;color:#2c1f0e;border:1.5px solid rgba(44,31,14,0.25);border-radius:3px;padding:8px 18px;font-size:12px;font-family:'Crimson Pro',Georgia,serif;font-weight:500;cursor:pointer;transition:all .25s}
        .btn-outline:hover{border-color:#8b6914;color:#8b6914}
        .fade-1{animation:fadeUp .6s .05s both}
        .fade-2{animation:fadeUp .6s .12s both}
        .fade-3{animation:fadeUp .6s .2s both}
        .fade-4{animation:fadeUp .6s .3s both}
        .fade-5{animation:fadeUp .6s .42s both}
        .fade-6{animation:fadeUp .6s .55s both}
      `}</style>

      {/* ── Top nav ── */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 300,
        height: 64, display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 32px",
        background: "rgba(245,240,232,0.98)", backdropFilter: "blur(16px)",
        borderBottom: `1px solid ${C.border}`,
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }} onClick={onNavigateHome}>
          <div style={{ width: 30, height: 30, position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ width: 26, height: 26, border: `2px solid ${C.gold}`, transform: "rotate(45deg)", position: "absolute" }} />
            <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 12, fontWeight: 700, color: C.gold, position: "relative", zIndex: 1 }}>G</span>
          </div>
          <div>
            <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 15, fontWeight: 800, color: C.inkDark, lineHeight: 1 }}>GenResearch</div>
            <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 8.5, color: C.gold, letterSpacing: "0.18em", textTransform: "uppercase" }}>Academic AI Platform</div>
          </div>
        </div>

        {/* Search bar */}
        <div style={{ flex: 1, maxWidth: 420, margin: "0 40px", position: "relative" }}>
          <div style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: C.inkLight, fontSize: 14 }}>🔍</div>
          <input
            placeholder="Search papers, tasks, results…"
            style={{
              width: "100%", padding: "9px 14px 9px 36px",
              border: `1.5px solid ${C.border}`, borderRadius: 3,
              background: C.white, fontFamily: "'Crimson Pro', Georgia, serif",
              fontSize: 13.5, color: C.inkDark, outline: "none",
              transition: "border-color .2s",
            }}
            onFocus={e => (e.target.style.borderColor = C.gold)}
            onBlur={e => (e.target.style.borderColor = C.border)}
          />
        </div>

        {/* Right nav */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {/* Notification bell */}
          <div style={{ position: "relative", cursor: "pointer" }}>
            <span style={{ fontSize: 16, color: C.inkLight }}>🔔</span>
            <div style={{
              position: "absolute", top: -2, right: -2, width: 8, height: 8,
              borderRadius: "50%", background: C.sienna,
              animation: "pulse 2s ease infinite",
            }} />
          </div>

          <div style={{ width: 1, height: 20, background: C.border }} />

          {/* User pill */}
          <div style={{
            display: "flex", alignItems: "center", gap: 9,
            padding: "5px 12px 5px 5px",
            background: C.creamLight, border: `1px solid ${C.border}`,
            borderRadius: 20, cursor: "pointer",
            transition: "border-color .2s",
          }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = C.borderGold)}
            onMouseLeave={e => (e.currentTarget.style.borderColor = C.border)}
          >
            <div style={{
              width: 28, height: 28, borderRadius: "50%",
              background: C.inkDark,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontFamily: "'Playfair Display', serif", fontSize: 12, fontWeight: 700, color: C.cream,
            }}>A</div>
            <div>
              <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, fontWeight: 600, color: C.inkDark, lineHeight: 1 }}>Ali Ahmed</div>
              <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, color: C.inkLight }}>BSE-SP23</div>
            </div>
          </div>

          <button className="btn-gold" style={{ padding: "9px 20px" }}>
            + New Task
          </button>
        </div>
      </nav>

      {/* ── Sidebar ── */}
      <aside style={{
        position: "fixed", top: 64, left: 0, bottom: 0, width: 220,
        background: C.creamLight, borderRight: `1px solid ${C.border}`,
        overflowY: "auto", zIndex: 200, padding: "20px 12px",
      }}>
        {/* Navigation */}
        <div style={{ marginBottom: 28 }}>
          <div style={{
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 10, fontWeight: 600, color: C.gold,
            letterSpacing: "0.18em", textTransform: "uppercase",
            padding: "0 8px", marginBottom: 8,
          }}>Navigation</div>
          {navItems.map(item => (
            <SideItem
              key={item.label}
              icon={item.icon}
              label={item.label}
              badge={item.badge}
              active={activeNav === item.label}
              onClick={() => setActiveNav(item.label)}
            />
          ))}
        </div>

        {/* Ornamental divider */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "0 4px 20px" }}>
          <div style={{ flex: 1, height: 1, background: C.border }} />
          <span style={{ color: C.gold, fontSize: 10 }}>✦</span>
          <div style={{ flex: 1, height: 1, background: C.border }} />
        </div>

        {/* Active task widget */}
        <div style={{
          background: C.inkDark, borderRadius: 4, padding: "16px 14px", marginBottom: 20,
        }}>
          <div style={{
            fontFamily: "'Crimson Pro', Georgia, serif",
            fontSize: 9.5, fontWeight: 600, color: C.goldLight,
            letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 10,
          }}>Active Task</div>
          <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: "rgba(245,240,232,0.8)", lineHeight: 1.5, marginBottom: 10 }}>
            BERT vs GPT Comparative Study
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <span style={{ animation: "spin 1.5s linear infinite", display: "inline-block", color: C.goldLight, fontSize: 12 }}>⟳</span>
            <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, color: C.goldLight }}>Processing…</span>
          </div>
          <div style={{ height: 3, background: "rgba(245,240,232,0.12)", borderRadius: 2, overflow: "hidden" }}>
            <div style={{
              height: "100%", width: "62%",
              background: `linear-gradient(90deg, ${C.goldLight}, ${C.gold})`,
              borderRadius: 2,
              animation: "shimmerBar 2s linear infinite",
              backgroundSize: "300% 100%",
            }} />
          </div>
        </div>

        {/* Storage usage */}
        <div style={{ padding: "0 4px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.inkLight }}>Storage</span>
            <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.gold, fontWeight: 600 }}>1.2 GB</span>
          </div>
          <MiniBar value={24} color={C.gold} />
          <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.inkLight, marginTop: 4 }}>24% of 5 GB used</div>
        </div>
      </aside>

      {/* ── Main content ── */}
      <main style={{
        marginLeft: 220, marginTop: 64,
        minHeight: "calc(100vh - 64px)",
        padding: "36px 40px",
        background: C.cream,
      }}>

        {/* Greeting header */}
        <div className="fade-1" style={{ marginBottom: 36 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                <div style={{ height: 1, width: 28, background: C.gold }} />
                <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.gold, letterSpacing: "0.18em", textTransform: "uppercase" }}>
                  {new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
                </span>
              </div>
              <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: "clamp(24px, 3vw, 36px)", fontWeight: 900, color: C.inkDark, letterSpacing: "-0.02em", lineHeight: 1.1 }}>
                {greeting}, <em style={{ color: C.gold }}>Ali.</em>
              </h1>
              <p style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 15, color: C.inkLight, marginTop: 6, lineHeight: 1.6 }}>
                You have <strong style={{ color: C.inkDark }}>1 task in progress</strong> and <strong style={{ color: C.inkDark }}>3 new results</strong> ready to review.
              </p>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button className="btn-outline">View All Results</button>
              <button className="btn-gold">+ Begin Research</button>
            </div>
          </div>
        </div>

        {/* Stats row */}
        <div className="fade-2" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16, marginBottom: 32 }}>
          <StatCard icon="📄" label="Total Papers" value={12} sub="Across all tasks" trend="+3 this week" />
          <StatCard icon="✓" label="Tasks Done" value={8} sub="Since joining" trend="+2 this week" color={C.green} />
          <StatCard icon="⚙" label="Tasks Running" value={1} sub="In progress now" color={C.gold} />
          <StatCard icon="◈" label="Avg. Quality" value={87} sub="Out of 100" trend="+4 pts" color={C.sienna} />
        </div>

        {/* Main grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 24 }}>

          {/* Left: Recent tasks */}
          <div>
            <div className="fade-3">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{ height: 1, width: 22, background: C.gold }} />
                  <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.gold, letterSpacing: "0.15em", textTransform: "uppercase" }}>Recent Tasks</span>
                </div>
                <button className="btn-outline" style={{ padding: "5px 14px", fontSize: 11.5 }}>View All</button>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {tasks.map((t, i) => (
                  <div key={t.id} style={{ animation: `fadeUp .5s ${i * 0.07 + 0.2}s both` }}>
                    <TaskCard task={t} onOpen={() => {}} />
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

            {/* Quick actions */}
            <div className="fade-3" style={{ background: C.creamLight, border: `1px solid ${C.border}`, borderRadius: 4, padding: "22px 20px" }}>
              <div style={{
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 11, fontWeight: 600, color: C.gold,
                letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 16,
              }}>Quick Actions</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  { label: "Upload New Papers", icon: "↑", color: C.gold },
                  { label: "Run Summarization", icon: "◈", color: C.gold },
                  { label: "Generate Literature Review", icon: "◉", color: C.sienna },
                  { label: "Format Citations (APA)", icon: "◎", color: C.umber },
                  { label: "Draft Research Proposal", icon: "◐", color: C.inkMid },
                ].map(a => (
                  <button key={a.label} style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "11px 14px", width: "100%", textAlign: "left",
                    background: "transparent",
                    border: `1px solid ${C.border}`,
                    borderRadius: 3, cursor: "pointer",
                    fontFamily: "'Crimson Pro', Georgia, serif",
                    fontSize: 13.5, color: C.inkDark,
                    transition: "all .2s",
                  }}
                    onMouseEnter={e => { e.currentTarget.style.background = C.white; e.currentTarget.style.borderColor = C.borderGold; e.currentTarget.style.color = C.gold; }}
                    onMouseLeave={e => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.borderColor = C.border; e.currentTarget.style.color = C.inkDark; }}
                  >
                    <span style={{ color: a.color, fontSize: 14, flexShrink: 0 }}>{a.icon}</span>
                    {a.label}
                    <span style={{ marginLeft: "auto", color: C.inkLight, fontSize: 13 }}>→</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Agent usage */}
            <div className="fade-4" style={{ background: C.creamLight, border: `1px solid ${C.border}`, borderRadius: 4, padding: "22px 20px" }}>
              <div style={{
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 11, fontWeight: 600, color: C.gold,
                letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 18,
              }}>Agent Usage</div>
              <AgentUsageRow label="Summarization" pct={50} color={C.gold} count={4} />
              <AgentUsageRow label="Literature Review" pct={25} color={C.sienna} count={2} />
              <AgentUsageRow label="Citation" pct={12} color={C.umber} count={1} />
              <AgentUsageRow label="Proposal Draft" pct={13} color={C.inkMid} count={1} />
            </div>

            {/* Activity feed */}
            <div className="fade-5" style={{ background: C.creamLight, border: `1px solid ${C.border}`, borderRadius: 4, padding: "22px 20px" }}>
              <div style={{
                fontFamily: "'Crimson Pro', Georgia, serif",
                fontSize: 11, fontWeight: 600, color: C.gold,
                letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: 16,
              }}>Recent Activity</div>
              <ActivityItem icon="✓" text="**Transformer Architectures** summary completed · Score 87/100" time="Today, 2:14 PM" color={C.green} />
              <ActivityItem icon="↑" text="**3 papers** uploaded and indexed successfully" time="Today, 2:09 PM" color={C.gold} />
              <ActivityItem icon="◉" text="**Literature Review Agent** started for BERT vs GPT" time="Today, 3:01 PM" color={C.sienna} />
              <ActivityItem icon="◎" text="**4 citations** extracted and formatted (APA)" time="Yesterday, 4:22 PM" color={C.umber} />
              <ActivityItem icon="✓" text="**Federated Learning Survey** summary completed · Score 92/100" time="Yesterday, 11:15 AM" color={C.green} />
            </div>
          </div>
        </div>

        {/* Bottom: Tips + ornament */}
        <div className="fade-6" style={{
          marginTop: 32, padding: "24px 28px",
          background: C.inkDark, borderRadius: 4,
          display: "flex", gap: 32, alignItems: "center", flexWrap: "wrap",
        }}>
          <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 16, fontWeight: 700, color: C.goldLight, flexShrink: 0 }}>
            ✦ Pro tip
          </div>
          <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14.5, color: "rgba(245,240,232,0.72)", lineHeight: 1.65, flex: 1 }}>
            For richer literature reviews, upload <strong style={{ color: C.goldLight }}>5–10 papers</strong> on the same topic before running the Literature Review Agent.
            Cross-paper analysis produces significantly more insightful research gap identification.
          </div>
          <button className="btn-outline" style={{ color: C.goldLight, borderColor: "rgba(200,151,30,0.35)", flexShrink: 0 }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = C.goldLight; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = "rgba(200,151,30,0.35)"; }}
          >Learn More</button>
        </div>
      </main>
    </>
  );
}
