"use client";
import { useState, useEffect } from "react";
import { C, PageTitle, SectionHead, Num, StatCardProps, StatCard, Badge, UserTableRow, UserRow, AgentHealth, AgentHealthRow, LogEntry, LogRow, CostRow, Bar } from "./shared";
import { subscribeToProfiles, subscribeToPlatformStats, subscribeToAgentLogs, subscribeToSystemAlerts, subscribeToApiCosts, subscribeToTasks, type Profile, type PlatformStats, type AgentLog, type SystemAlert, type Task } from "../../lib/db";

export default function OverviewPage() {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [stats, setStats] = useState<PlatformStats>({ total_users: 0, total_papers: 0, total_tasks_completed: 0, active_tasks: 0, total_citations: 0 });
  const [alerts, setAlerts] = useState<SystemAlert[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [alertDismissed, setAlertDismissed] = useState(false);

  useEffect(() => {
    const unsubProfiles = subscribeToProfiles((data) => {
      setUsers(data.slice(0, 5).map(u => ({
        id: u.id,
        name: u.full_name,
        email: u.email,
        role: u.role,
        papers: 0,
        tasks: 0,
        status: u.status as any,
        joined: new Date(u.created_at).toLocaleDateString("en-US", { month: "short", year: "numeric" })
      })));
    });

    const unsubStats = subscribeToPlatformStats(setStats);
    
    const unsubLogs = subscribeToAgentLogs((data) => {
      setLogs(data.slice(0, 5).map(l => ({
        id: l.id,
        level: l.level as any,
        message: l.message,
        time: new Date(l.created_at).toLocaleTimeString("en-US", { hour12: false }),
        agent: l.agent || "System"
      })));
    });

    const unsubAlerts = subscribeToSystemAlerts(setAlerts);
    const unsubTasks = subscribeToTasks(setTasks);

    return () => {
      unsubProfiles();
      unsubStats();
      unsubLogs();
      unsubAlerts();
      unsubTasks();
    };
  }, []);

  const activeAlert = alerts.find(a => a.status === "active");

  const statCards: StatCardProps[] = [
    { icon: "👥", label: "Total Users", value: stats.total_users, suffix: "", sub: "Registered researchers", trend: "Live count", trendUp: true, color: C.gold, sparkData: [0, 0, 0, 0, 0, 0, 0, 0, 0, stats.total_users] },
    { icon: "📄", label: "Papers Indexed", value: stats.total_papers, suffix: "", sub: "Across all collections", trend: "Total items", trendUp: true, color: C.sienna, sparkData: [0, 0, 0, 0, 0, 0, 0, 0, 0, stats.total_papers] },
    { icon: "⚙", label: "Tasks Done", value: stats.total_tasks_completed, suffix: "", sub: "Successful outputs", trend: "Platform total", trendUp: true, color: C.umber, sparkData: [0, 0, 0, 0, 0, 0, 0, 0, 0, stats.total_tasks_completed] },
    { icon: "⚡", label: "Active Tasks", value: stats.active_tasks, suffix: "", sub: "Real-time queue", trend: "Pending load", trendUp: stats.active_tasks < 5, color: C.green, sparkData: [0, 0, 0, 0, 0, 0, 0, 0, 0, stats.active_tasks] },
  ];

  const agentTypes = ["Summarization", "Literature Review", "Citation", "Proposal"];
  const agents: AgentHealth[] = agentTypes.map(type => {
    const alert = alerts.find(a => a.agent?.startsWith(type) && a.status === "active");
    const agentTasks = tasks.filter(t => t.agent_type.replace(/_/g, " ").toLowerCase() === type.toLowerCase());
    return {
      name: `${type} Agent`,
      status: alert ? (alert.severity === "critical" ? "offline" : "degraded") : "online",
      requests: agentTasks.length,
      avgTime: agentTasks.length > 0 ? "Real-time" : "—",
      errorRate: alert ? 100 : 0,
      uptime: alert ? 0 : 100
    };
  });

  return (
    <div style={{ animation: "fadeUp .5s both" }}>
      <PageTitle title="System Overview" sub={new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })} actions={<><button className="btn-ghost">Export Report</button><button className="btn-gold">+ Invite User</button></>} />

      {activeAlert && !alertDismissed && (
        <div className="a1" style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 18px", marginBottom: 24, background: activeAlert.severity === "critical" ? C.redFaint : C.goldFaint, border: `1px solid ${activeAlert.severity === "critical" ? C.red : C.gold}44`, borderLeft: `3px solid ${activeAlert.severity === "critical" ? C.red : C.gold}`, borderRadius: 4 }}>
          <span style={{ color: activeAlert.severity === "critical" ? C.red : C.gold, fontSize: 15, flexShrink: 0 }}>{activeAlert.severity === "critical" ? "⚠" : "ℹ"}</span>
          <div style={{ flex: 1 }}>
            <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 13, fontWeight: 700, color: activeAlert.severity === "critical" ? C.red : C.gold }}>{activeAlert.title} — </span>
            <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkMid }}>{activeAlert.message}</span>
          </div>
          <button onClick={() => setAlertDismissed(true)} style={{ background: "transparent", border: "none", cursor: "pointer", color: activeAlert.severity === "critical" ? C.red : C.gold, fontSize: 16, lineHeight: 1, flexShrink: 0, padding: 2 }}>✕</button>
        </div>
      )}

      <div className="a2" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16, marginBottom: 28 }}>
        {statCards.map((card, i) => (
          <div key={i} style={{ animation: `fadeUp .6s ${i * 0.07 + 0.1}s both` }}>
            <StatCard {...card} />
          </div>
        ))}
      </div>

      <div className="a3" style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 22, marginBottom: 22 }}>
        <div className="card">
          <div style={{ padding: "18px 20px", borderBottom: `1px solid ${C.border}` }}>
            <SectionHead label="Recent Users" />
          </div>
          {users.length === 0 ? (
            <div style={{ padding: 40, textAlign: "center", color: C.inkLight }}>No users found.</div>
          ) : (
            users.map(u => <UserTableRow key={u.id} user={u} />)
          )}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div className="card" style={{ padding: "20px 18px" }}>
            <SectionHead label="Quick Actions" />
            {[
              { label: "Purge Stale Collections",  icon: "🗑", color: C.red },
              { label: "Reset Agent Rate Limits",  icon: "⟳", color: C.gold },
            ].map(a => (
              <button key={a.label} className="btn-ghost" style={{ width: "100%", textAlign: "left", display: "flex", alignItems: "center", gap: 9, padding: "10px 12px", marginBottom: 6, border: `1px solid ${C.border}`, borderRadius: 3 }}>
                <span style={{ color: a.color, fontSize: 14 }}>{a.icon}</span>
                {a.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="a4" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 22, marginBottom: 22 }}>
        <div className="card">
          <div style={{ padding: "16px 20px 0", borderBottom: `1px solid ${C.border}` }}>
            <SectionHead label="Agent Health Monitor" />
          </div>
          {agents.map((a, i) => <AgentHealthRow key={i} agent={a} />)}
        </div>
        <div className="card">
          <div style={{ padding: "16px 20px 0", borderBottom: `1px solid ${C.border}` }}>
            <SectionHead label="System Logs" />
          </div>
          {logs.length === 0 ? (
            <div style={{ padding: 40, textAlign: "center", color: C.inkLight }}>No recent logs.</div>
          ) : (
            logs.map(entry => <LogRow key={entry.id} entry={entry} />)
          )}
        </div>
      </div>
    </div>
  );
}
