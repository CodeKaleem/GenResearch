"use client";
import { useState } from "react";
import { C, PageTitle, SectionHead, Num, StatCardProps, StatCard, Badge, UserTableRow, UserRow, AgentHealth, AgentHealthRow, LogEntry, LogRow, CostRow, Bar } from "./shared";

// ── Data ────────────────────────────────────────────────────
const users: UserRow[] = [
  { id:"1", name:"Ali Ahmed",      email:"ali.ahmed@comsats.edu.pk",   role:"Admin",      papers:12, tasks:8,  status:"active",    joined:"Jan 2025" },
  { id:"2", name:"Kaleem Abbasi",  email:"kaleem@comsats.edu.pk",      role:"Researcher", papers:18, tasks:15, status:"active",    joined:"Jan 2025" },
  { id:"3", name:"Sara Malik",     email:"sara.malik@uet.edu.pk",      role:"Researcher", papers:7,  tasks:4,  status:"active",    joined:"Feb 2025" },
];

const agents: AgentHealth[] = [
  { name:"Summarization Agent",      status:"online",   requests:1842, avgTime:"24s",  errorRate:1.2, uptime:99.8 },
  { name:"Literature Review Agent",  status:"online",   requests:634,  avgTime:"58s",  errorRate:2.1, uptime:99.1 },
  { name:"Citation Agent",           status:"degraded", requests:411,  avgTime:"12s",  errorRate:8.4, uptime:94.3 },
];

const logs: LogEntry[] = [
  { id:"1", level:"success", message:"Summarization task completed for user ali.ahmed",       time:"14:32:11", agent:"Summarization" },
  { id:"2", level:"warn",    message:"Citation Agent timeout on CrossRef API call — retrying",time:"14:31:44", agent:"Citation" },
  { id:"4", level:"error",   message:"ChromaDB collection query failed — null embedding",     time:"14:28:55", agent:"RAG Engine" },
];

const statCards: StatCardProps[] = [
  { icon:"👥", label:"Total Users",     value:142,    suffix:"",    sub:"Registered researchers",      trend:"+12 this month",  trendUp:true,  color:C.gold,   sparkData:[80,90,95,102,110,118,125,130,135,142] },
  { icon:"📄", label:"Papers Indexed",  value:3847,   suffix:"",    sub:"Across all collections",      trend:"+284 this week",  trendUp:true,  color:C.sienna, sparkData:[3100,3200,3350,3480,3550,3620,3700,3780,3820,3847] },
  { icon:"⚙",  label:"Tasks Completed", value:9214,   suffix:"",    sub:"Since platform launch",       trend:"+63 today",       trendUp:true,  color:C.umber,  sparkData:[8000,8300,8500,8700,8850,8980,9050,9120,9180,9214] },
  { icon:"⚡", label:"Avg Response",    value:28,     suffix:"s",   sub:"LLM generation time",         trend:"−4s vs last wk",  trendUp:true,  color:C.green,  sparkData:[38,35,34,32,31,30,29,28,28,28] },
];

export default function OverviewPage() {
  const [alertDismissed, setAlertDismissed] = useState(false);

  return (
    <div style={{ animation: "fadeUp .5s both" }}>
      <PageTitle title="System Overview" sub={new Date().toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })} actions={<><button className="btn-ghost">Export Report</button><button className="btn-gold">+ Invite User</button></>} />

      {!alertDismissed && (
        <div className="a1" style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 18px", marginBottom: 24, background: C.redFaint, border: `1px solid ${C.red}44`, borderLeft: `3px solid ${C.red}`, borderRadius: 4 }}>
          <span style={{ color: C.red, fontSize: 15, flexShrink: 0 }}>⚠</span>
          <div style={{ flex: 1 }}>
            <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 13, fontWeight: 700, color: C.red }}>Citation Agent Degraded — </span>
            <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkMid }}>CrossRef API error rate at 8.4%. Tasks may fail. Check API key configuration.</span>
          </div>
          <button onClick={() => setAlertDismissed(true)} style={{ background: "transparent", border: "none", cursor: "pointer", color: C.red, fontSize: 16, lineHeight: 1, flexShrink: 0, padding: 2 }}>✕</button>
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
            <SectionHead label="User Management" />
          </div>
          {users.map(u => <UserTableRow key={u.id} user={u} />)}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div className="card" style={{ padding: "20px 18px" }}>
            <SectionHead label="API Cost Breakdown" />
            <CostRow label="Summarization Agent" tokens="841K tokens" cost="$1.68" pct={40} color={C.gold} />
            <CostRow label="Literature Review"   tokens="562K tokens" cost="$1.12" pct={27} color={C.sienna} />
          </div>
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
          {logs.map(entry => <LogRow key={entry.id} entry={entry} />)}
        </div>
      </div>
    </div>
  );
}
