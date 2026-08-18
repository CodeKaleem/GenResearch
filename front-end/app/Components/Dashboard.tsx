"use client";
import { useState, useEffect } from "react";
import UploadPapers from "./UploadPapers";
import MyPapers from "./MyPapers";
import Chat from "./Chat";
import Agents from "./Agents";
import Results from "./Results";
import Citations from "./Citations";
import Library from "./Library";
import Settings from "./Settings";
import { supabase } from "../../lib/supabase";
import { 
  getProfile, 
  getCurrentUserId, 
  subscribeToPapers, 
  subscribeToTasks, 
  subscribeToResults,
  type Paper as DBPaper, 
  type Task as DBTask,
  type TaskResult as DBResult
} from "../../lib/db";

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
        height: "100%", width: `${Math.min(value, 100)}%`,
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
        flex: 1, fontFamily: "'Crimson Pro', Georgia, serif",
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
type TaskStatus = "completed" | "processing" | "pending" | "failed";
interface Task {
  id: string; title: string; agent: string; papers: number;
  status: TaskStatus; time: string; score?: number;
}

function TaskCard({ task, onOpen }: { task: Task; onOpen: () => void }) {
  const [hov, setHov] = useState(false);
  const statusStyle: Record<TaskStatus, { label: string; color: string; bg: string }> = {
    completed:  { label: "Completed",  color: C.green,   bg: "rgba(90,138,60,0.09)" },
    processing: { label: "Processing", color: C.gold,    bg: C.goldFaint },
    pending:    { label: "Pending",    color: C.inkLight,bg: "rgba(122,96,64,0.09)" },
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
          <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 15, fontWeight: 700, color: C.inkDark, marginBottom: 4, lineHeight: 1.3 }}>{task.title}</div>
          <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.inkLight, letterSpacing: "0.04em" }}>{task.agent} · {task.papers} paper{task.papers > 1 ? "s" : ""}</div>
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
          <div style={{ display: "flex", alignItems: "center", gap: 5, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.gold }}>
            <span style={{ animation: "spin 1.2s linear infinite", display: "inline-block" }}>⟳</span>
            In progress…
          </div>
        )}
      </div>
    </div>
  );
}

// ── Activity item ─────────────────────────────────────────────
function ActivityItem({ icon, text, time, color }: { icon: string; text: string; time: string; color: string; }) {
  return (
    <div style={{ display: "flex", gap: 12, paddingBottom: 14, marginBottom: 2 }}>
      <div style={{
        width: 30, height: 30, borderRadius: "50%", flexShrink: 0,
        background: `${color}18`, border: `1px solid ${color}33`,
        display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13,
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
    <div style={{ background: C.creamLight, border: `1px solid ${C.border}`, borderRadius: 4, padding: "22px 22px", transition: "all .3s", cursor: "default" }}
      onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = C.borderGold; (e.currentTarget as HTMLDivElement).style.transform = "translateY(-3px)"; (e.currentTarget as HTMLDivElement).style.boxShadow = `0 8px 24px ${C.shadow}`; }}
      onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = C.border; (e.currentTarget as HTMLDivElement).style.transform = "none"; (e.currentTarget as HTMLDivElement).style.boxShadow = "none"; }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <div style={{ width: 38, height: 38, borderRadius: 4, background: `${color}18`, border: `1px solid ${color}33`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>{icon}</div>
        {trend && <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, color: trend.startsWith("+") ? C.green : C.sienna, fontWeight: 600 }}>{trend}</span>}
      </div>
      <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 32, fontWeight: 900, color: C.inkDark, lineHeight: 1, marginBottom: 4 }}><Num to={value} /></div>
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

export default function Dashboard({ onNavigateHome }: { onNavigateHome?: () => void }) {
  const [activeNav, setActiveNav] = useState("Dashboard");
  const [greeting, setGreeting] = useState("Good morning");
  const [user, setUser] = useState<{ name: string; institution: string } | null>(null);
  const [dbTasks, setDbTasks] = useState<DBTask[]>([]);
  const [dbPapers, setDbPapers] = useState<DBPaper[]>([]);
  const [dbResults, setDbResults] = useState<DBResult[]>([]);
  const [notifications, setNotifications] = useState<{ id: string; message: string; type: "success" | "error" | "info" }[]>([]);

  const addNotification = (message: string, type: "success" | "error" | "info" = "info") => {
    const id = Math.random().toString(36).substr(2, 9);
    setNotifications(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  };

  useEffect(() => {
    let isMounted = true;
    let unsubs: (() => void)[] = [];

    const init = async () => {
      const userId = await getCurrentUserId();
      if (!userId || !isMounted) return;
      const { data } = await getProfile(userId);
      if (data && isMounted) setUser({ name: data.full_name || "Researcher", institution: data.institution || "GenResearch" });

      if (isMounted) {
        unsubs.push(subscribeToTasks(userId, (tasks) => {
          setDbTasks(prev => {
            if (prev.length > 0 && tasks.length > prev.length) {
              const newT = tasks[0];
              if (newT.status === "completed") addNotification(`Task "${newT.title}" completed successfully!`, "success");
              else if (newT.status === "failed") addNotification(`Task "${newT.title}" encountered an error.`, "error");
            }
            return tasks;
          });
        }));

        unsubs.push(subscribeToPapers(userId, (papers) => {
          setDbPapers(prev => {
            if (prev.length > 0 && papers.length > prev.length) {
              addNotification(`Paper "${papers[0].title}" processed & indexed!`, "success");
            }
            return papers;
          });
        }));

        unsubs.push(subscribeToResults(userId, setDbResults));
      }
    };
    init();

    const h = new Date().getHours();
    if (h < 12) setGreeting("Good morning");
    else if (h < 17) setGreeting("Good afternoon");
    else setGreeting("Good evening");

    return () => {
      isMounted = false;
      unsubs.forEach(u => u());
    };
  }, []);

  const handleSignOut = async () => { await supabase.auth.signOut(); };

  const agentLabelMap: Record<string, string> = {
    summarization: "Summarization Agent",
    literature_review: "Literature Review Agent",
    citation: "Citation Agent",
    proposal: "Proposal Drafting Agent",
  };

  const tasks: Task[] = dbTasks.slice(0, 5).map(t => ({
    id: t.id,
    title: t.title,
    agent: agentLabelMap[t.agent_type] || t.agent_type,
    papers: t.paper_count,
    status: t.status as Task["status"],
    time: new Date(t.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    score: t.quality_score ?? undefined,
  }));

  const navItems = [
    { icon: "⌂", label: "Dashboard" },
    { icon: "↑", label: "Upload Papers" },
    { icon: "⬡", label: "My Papers", badge: dbPapers.length || undefined },
    { icon: "💬", label: "Ask AI" },
    { icon: "⚙", label: "Agents" },
    { icon: "◈", label: "Results", badge: dbResults.length || undefined },
    { icon: "◎", label: "Citations" },
    { icon: "⊞", label: "Library" },
    { icon: "◌", label: "Settings" },
  ];

  // Calculate usage stats
  const totalTasks = dbTasks.length || 1;
  const usageStats = ["summarization", "literature_review", "citation", "proposal"].map(type => {
    const count = dbTasks.filter(t => t.agent_type === type).length;
    return { type, count, pct: Math.round((count / totalTasks) * 100) };
  });

  // Activity Feed Generator
  const activityFeed = [...dbTasks, ...dbResults]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5)
    .map(item => {
      const isResult = "task_id" in item;
      const time = new Date(item.created_at).toLocaleString("en-US", { hour: "numeric", minute: "numeric", hour12: true });
      if (isResult) {
        return { icon: "✓", text: `**${item.title}** completed · Score ${item.score}/100`, time: `Today, ${time}`, color: C.green };
      } else {
        const t = item as DBTask;
        if (t.status === "processing") return { icon: "◉", text: `**${t.agent_type}** agent started for ${t.title}`, time: `Today, ${time}`, color: C.gold };
        if (t.status === "failed") return { icon: "⚠", text: `Task **${t.title}** failed to process`, time: `Today, ${time}`, color: C.sienna };
        return { icon: "◈", text: `New task **${t.title}** created`, time: `Today, ${time}`, color: C.inkLight };
      }
    });

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,800;0,900;1,700&family=Crimson+Pro:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #f5f0e8; color: #2c1f0e; font-family: 'Crimson Pro', Georgia, serif; }
        ::-webkit-scrollbar { width: 4px; } ::-webkit-scrollbar-thumb { background: rgba(139,105,20,0.28); border-radius: 3px; }
        @keyframes fadeUp { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        @keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        .btn-gold{background:#8b6914;color:#fffef9;border:none;border-radius:3px;padding:10px 22px;font-size:12.5px;font-family:'Crimson Pro',Georgia,serif;font-weight:600;cursor:pointer;letter-spacing:.08em;text-transform:uppercase;transition:all .25s}
        .btn-ink{background:#2c1f0e;color:#fffef9;border:none;border-radius:3px;padding:10px 22px;font-size:12.5px;font-family:'Crimson Pro',Georgia,serif;font-weight:600;cursor:pointer;letter-spacing:.08em;text-transform:uppercase;transition:all .25s}
        .btn-outline{background:transparent;color:#2c1f0e;border:1.5px solid rgba(44,31,14,0.25);border-radius:3px;padding:8px 18px;font-size:12px;font-family:'Crimson Pro',Georgia,serif;font-weight:500;cursor:pointer;transition:all .25s}
        .fade-1{animation:fadeUp .6s .05s both} .fade-2{animation:fadeUp .6s .12s both}
      `}</style>

      <nav style={{ position: "fixed", top: 0, left: 0, right: 0, zIndex: 300, height: 64, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 32px", background: "rgba(245,240,232,0.98)", backdropFilter: "blur(16px)", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, cursor: "pointer" }} onClick={onNavigateHome}>
          <div style={{ width: 30, height: 30, position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ width: 26, height: 26, border: `2px solid ${C.gold}`, transform: "rotate(45deg)", position: "absolute" }} />
            <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 12, fontWeight: 700, color: C.gold, position: "relative", zIndex: 1 }}>G</span>
          </div>
          <div><div style={{ fontFamily: "'Playfair Display', serif", fontSize: 15, fontWeight: 800, color: C.inkDark, lineHeight: 1 }}>GenResearch</div><div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 8.5, color: C.gold, letterSpacing: "0.18em", textTransform: "uppercase" }}>Academic AI Platform</div></div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 9, padding: "5px 12px 5px 5px", background: C.creamLight, border: `1px solid ${C.border}`, borderRadius: 20, cursor: "pointer" }}>
            <div style={{ width: 28, height: 28, borderRadius: "50%", background: C.inkDark, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Playfair Display', serif", fontSize: 12, fontWeight: 700, color: C.cream }}>{user?.name.charAt(0) || "U"}</div>
            <div><div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, fontWeight: 600, color: C.inkDark, lineHeight: 1 }}>{user?.name || "Researcher"}</div><div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, color: C.inkLight }}>{user?.institution}</div></div>
          </div>
          <button className="btn-gold" onClick={() => setActiveNav("Upload Papers")}>+ New Task</button>
        </div>
      </nav>

      <aside style={{ position: "fixed", top: 64, left: 0, bottom: 0, width: 220, background: C.creamLight, borderRight: `1px solid ${C.border}`, padding: "20px 12px", display: "flex", flexDirection: "column", zIndex: 200 }}>
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, fontWeight: 600, color: C.gold, letterSpacing: "0.18em", textTransform: "uppercase", padding: "0 8px", marginBottom: 8 }}>Navigation</div>
          {navItems.map(item => <SideItem key={item.label} icon={item.icon} label={item.label} badge={item.badge} active={activeNav === item.label} onClick={() => setActiveNav(item.label)} />)}
        </div>
        <div style={{ marginTop: "auto", padding: "12px 4px 0", borderTop: `1px solid ${C.border}` }}>
          <button onClick={handleSignOut} style={{ width: "100%", textAlign: "left", display: "flex", alignItems: "center", gap: 10, padding: "10px 16px", background: "transparent", border: "none", borderRadius: 3, cursor: "pointer", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: "#a0522d" }}><span>⏻</span>Sign Out</button>
        </div>
      </aside>

      <main style={{ marginLeft: 220, marginTop: 64, padding: "36px 40px", minHeight: "calc(100vh - 64px)" }}>
        {activeNav === "Dashboard" ? (
          <>
            <div className="fade-1" style={{ marginBottom: 36 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                    <div style={{ height: 1, width: 28, background: C.gold }} />
                    <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.gold, textTransform: "uppercase" }}>{new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}</span>
                  </div>
                  <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 36, fontWeight: 900, color: C.inkDark }}>{greeting}, <em style={{ color: C.gold }}>{user?.name.split(" ")[0]}.</em></h1>
                </div>
                <div style={{ display: "flex", gap: 10 }}><button className="btn-outline" onClick={() => setActiveNav("Results")}>History</button><button className="btn-gold" onClick={() => setActiveNav("Upload Papers")}>Research</button></div>
              </div>
            </div>

            <div className="fade-2" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
              <StatCard icon="📄" label="Papers" value={dbPapers.length} sub="Library size" />
              <StatCard icon="✓" label="Completed" value={dbTasks.filter(t => t.status === "completed").length} sub="Tasks finished" color={C.green} />
              <StatCard icon="⚙" label="Running" value={dbTasks.filter(t => t.status === "processing").length} sub="Active agents" color={C.gold} />
              <StatCard icon="◈" label="Avg Score" value={dbResults.length ? Math.round(dbResults.reduce((a, b) => a + b.score, 0) / dbResults.length) : 0} sub="Quality avg" color={C.sienna} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 24 }}>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}><span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.gold, textTransform: "uppercase" }}>Recent Tasks</span><button className="btn-outline" onClick={() => setActiveNav("Results")}>View All</button></div>
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{tasks.map(t => <TaskCard key={t.id} task={t} onOpen={() => setActiveNav("Results")} />)}</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                <div style={{ background: C.creamLight, border: `1px solid ${C.border}`, borderRadius: 4, padding: "20px" }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: C.gold, textTransform: "uppercase", marginBottom: 18 }}>Agent Usage</div>
                  {usageStats.map(s => <AgentUsageRow key={s.type} label={agentLabelMap[s.type]} pct={s.pct} color={C.gold} count={s.count} />)}
                </div>
                <div style={{ background: C.creamLight, border: `1px solid ${C.border}`, borderRadius: 4, padding: "20px" }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: C.gold, textTransform: "uppercase", marginBottom: 16 }}>Live Activity</div>
                  {activityFeed.map((a, i) => <ActivityItem key={i} {...a} />)}
                </div>
              </div>
            </div>
          </>
        ) : (
          <>
            {activeNav === "Upload Papers" && <UploadPapers />}
            {activeNav === "My Papers" && <MyPapers />}
            {activeNav === "Ask AI" && <Chat />}
            {activeNav === "Agents" && <Agents />}
            {activeNav === "Results" && <Results />}
            {activeNav === "Citations" && <Citations />}
            {activeNav === "Library" && <Library />}
            {activeNav === "Settings" && <Settings />}
          </>
        )}
      </main>

      {/* Real-time Notification Toast Container */}
      <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 9999, display: "flex", flexDirection: "column", gap: 10, maxWidth: 360, pointerEvents: "none" }}>
        {notifications.map(n => (
          <div key={n.id} className="fade-1" style={{ pointerEvents: "auto", padding: "14px 18px", borderRadius: 4, background: n.type === "success" ? C.creamLight : n.type === "error" ? "rgba(160,82,45,0.95)" : C.inkDark, border: `1px solid ${n.type === "success" ? C.green : n.type === "error" ? C.sienna : C.gold}`, color: n.type === "error" ? C.white : n.type === "success" ? C.inkDark : C.cream, boxShadow: "0 8px 24px rgba(0,0,0,0.18)", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 16 }}>{n.type === "success" ? "✓" : n.type === "error" ? "⚠" : "ℹ"}</span>
            <span style={{ flex: 1 }}>{n.message}</span>
          </div>
        ))}
      </div>
    </>
  );
}
