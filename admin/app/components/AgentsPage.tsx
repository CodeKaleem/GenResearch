"use client";
import { useState, useEffect } from "react";
import { C, Badge, SectionHead, PageTitle, Modal, Bar, Num } from "./shared";
import { subscribeToPlatformStats, subscribeToSystemAlerts, subscribeToTasks, type PlatformStats, type SystemAlert, type Task } from "../../lib/db";

interface Agent {
  id: string; name: string; type: string;
  status: "online" | "degraded" | "offline";
  requests: number; avgTime: string; errorRate: number;
  lastError: string; model: string; rateLimit: number; rateLimitUsed: number;
  sparkRequests: number[];
}

const BASE_AGENTS: Agent[] = [
  { id: "sum",  name: "Summarization Agent",     type: "LLM Pipeline",  status: "offline",   requests: 0, avgTime: "—",  errorRate: 0,  lastError: "—",                         model: "GPT-4o / GPT-3.5", rateLimit: 100, rateLimitUsed: 0, sparkRequests: [0,0,0,0,0,0,0,0,0,0] },
  { id: "lit",  name: "Literature Review Agent", type: "RAG + LLM",     status: "offline",   requests: 0,  avgTime: "—",  errorRate: 0,  lastError: "—",                         model: "GPT-4o", rateLimit: 50,  rateLimitUsed: 0, sparkRequests: [0,0,0,0,0,0,0,0,0,0] },
  { id: "cite", name: "Citation Agent",          type: "API Connector", status: "offline",   requests: 0,  avgTime: "—",  errorRate: 0,  lastError: "—",                         model: "CrossRef API",  rateLimit: 200, rateLimitUsed: 0, sparkRequests: [0,0,0,0,0,0,0,0,0,0] },
  { id: "prop", name: "Proposal Drafting Agent", type: "LLM Pipeline",  status: "offline",   requests: 0,  avgTime: "—",  errorRate: 0,  lastError: "—",                         model: "GPT-4o", rateLimit: 30,  rateLimitUsed: 0, sparkRequests: [0,0,0,0,0,0,0,0,0,0] },
  { id: "rag",  name: "RAG Engine",              type: "Vector Search", status: "offline",   requests: 0, avgTime: "—",   errorRate: 0,  lastError: "—",                         model: "ChromaDB",      rateLimit: 500, rateLimitUsed: 0, sparkRequests: [0,0,0,0,0,0,0,0,0,0] },
];

function AgentDetailModal({ agent, onClose, onRestart }: { agent: Agent; onClose: () => void; onRestart: () => void }) {
  const statusColor = { online: C.green, degraded: C.goldLight, offline: C.red }[agent.status];
  return (
    <Modal title={agent.name} onClose={onClose}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        {[
          { label: "Status",      value: agent.status.toUpperCase(),    color: statusColor },
          { label: "Type",        value: agent.type,                    color: C.inkDark },
          { label: "Model",       value: agent.model,                   color: C.gold },
          { label: "Avg Time",    value: agent.avgTime,                 color: C.inkDark },
          { label: "Total Reqs",  value: agent.requests.toLocaleString(), color: C.inkDark },
          { label: "Success Rate", value: `${100 - agent.errorRate}%`,      color: C.green },
        ].map(s => (
          <div key={s.label} style={{ background: C.creamDark, borderRadius: 3, padding: "12px 14px", border: `1px solid ${C.border}` }}>
            <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, fontWeight: 600, color: C.gold, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 4 }}>{s.label}</div>
            <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 16, fontWeight: 800, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.gold, letterSpacing: "0.12em", textTransform: "uppercase", marginBottom: 6 }}>Rate Limit Usage</div>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
          <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight }}>{agent.rateLimitUsed} / {agent.rateLimit} req/min</span>
          <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, fontWeight: 600, color: agent.rateLimitUsed / agent.rateLimit > 0.8 ? C.red : C.gold }}>{Math.round((agent.rateLimitUsed / agent.rateLimit) * 100)}%</span>
        </div>
        <Bar value={(agent.rateLimitUsed / agent.rateLimit) * 100} color={agent.rateLimitUsed / agent.rateLimit > 0.8 ? C.red : C.gold} />
      </div>
      {agent.lastError !== "—" && (
        <div style={{ padding: "10px 14px", background: C.redFaint, border: `1px solid ${C.red}33`, borderRadius: 3, marginBottom: 16 }}>
          <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.red, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 3 }}>Last Error</div>
          <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.red }}>{agent.lastError}</div>
        </div>
      )}
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button className="btn-ghost" onClick={onClose}>Close</button>
        <button className="btn-red" onClick={() => { onRestart(); onClose(); }}>Restart Agent</button>
      </div>
    </Modal>
  );
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>(BASE_AGENTS);
  const [stats, setStats] = useState<PlatformStats>({ total_users: 0, total_papers: 0, total_tasks_completed: 0, active_tasks: 0, total_citations: 0 });
  const [alerts, setAlerts] = useState<SystemAlert[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [detailAgent, setDetailAgent] = useState<Agent | null>(null);
  const [restartToast, setRestartToast] = useState("");

  useEffect(() => {
    const unsubStats = subscribeToPlatformStats(setStats);
    const unsubAlerts = subscribeToSystemAlerts(setAlerts);
    const unsubTasks = subscribeToTasks(setTasks);

    return () => {
      unsubStats();
      unsubAlerts();
      unsubTasks();
    };
  }, []);

  useEffect(() => {
    setAgents(prev => prev.map(agent => {
      const typeKey = agent.name.split(" ")[0];
      const activeAlert = alerts.find(a => a.agent?.startsWith(typeKey) && a.status === "active");
      const agentTasks = tasks.filter(t => t.agent_type.replace(/_/g, " ").toLowerCase().startsWith(typeKey.toLowerCase()));
      
      return {
        ...agent,
        status: activeAlert ? (activeAlert.severity === "critical" ? "offline" : "degraded") : (agentTasks.length > 0 ? "online" : "offline"),
        lastError: activeAlert ? activeAlert.message : "—",
        requests: agentTasks.length,
        avgTime: agentTasks.length > 0 ? "Real-time" : "—"
      };
    }));
  }, [alerts, tasks]);

  const restartAgent = (id: string, name: string) => {
    setRestartToast(`${name} restarted successfully`);
    setTimeout(() => setRestartToast(""), 3000);
  };

  const statusColor = (s: string) => ({ online: C.green, degraded: C.goldLight, offline: C.red }[s] ?? C.inkLight);

  const online = agents.filter(a => a.status === "online").length;
  const degraded = agents.filter(a => a.status === "degraded" || a.status === "offline").length;

  return (
    <div style={{ animation: "fadeUp .5s both" }}>
      <PageTitle
        title="Agent Monitor"
        sub="AI Infrastructure"
        actions={<><button className="btn-ghost">System Logs</button><button className="btn-ink">⟳ Restart All</button></>}
      />

      {restartToast && (
        <div style={{ position: "fixed", bottom: 28, right: 28, zIndex: 900, background: C.inkDark, color: C.cream, padding: "12px 20px", borderRadius: 4, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, boxShadow: `0 8px 24px ${C.shadowMd}`, animation: "fadeUp .3s both", display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ color: C.green }}>✓</span> {restartToast}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "Online",       value: online,    color: C.green,   suffix: ` / ${agents.length}` },
          { label: "Alerts / Off", value: degraded,  color: C.red,      suffix: " active" },
          { label: "Total Tasks",  value: stats.total_tasks_completed, color: C.gold,  suffix: "" },
          { label: "Health Score", value: online > 0 ? Math.round((online / agents.length) * 100) : 0, color: C.blue, suffix: "%" },
        ].map(s => (
          <div key={s.label} className="card" style={{ padding: "16px 18px" }}>
            <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 26, fontWeight: 900, color: s.color }}><Num to={s.value} suffix={s.suffix} /></div>
            <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.inkLight, letterSpacing: "0.10em", textTransform: "uppercase", marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gap: 16 }}>
        {agents.map(agent => {
          const sc = statusColor(agent.status);
          return (
            <div key={agent.id} className="card" style={{ padding: "20px 22px", transition: "box-shadow .2s" }}>
              <div style={{ display: "grid", gridTemplateColumns: "2fr 110px 90px 90px 160px 160px auto", alignItems: "center", gap: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ width: 10, height: 10, borderRadius: "50%", background: sc, boxShadow: agent.status === "online" ? `0 0 8px ${sc}` : "none", animation: agent.status === "online" ? "adminPulse 2s ease infinite" : "none", flexShrink: 0 }} />
                  <div>
                    <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14.5, fontWeight: 600, color: C.inkDark }}>{agent.name}</div>
                    <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, color: C.inkLight }}>{agent.type} · {agent.model}</div>
                  </div>
                </div>
                <div><Badge label={agent.status} color={sc} /></div>
                <div>
                  <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 800, color: C.inkDark }}>{agent.requests.toLocaleString()}</div>
                  <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, color: C.inkLight, letterSpacing: "0.08em", textTransform: "uppercase" }}>Requests</div>
                </div>
                <div>
                  <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 800, color: C.inkDark }}>{agent.avgTime}</div>
                  <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, color: C.inkLight, letterSpacing: "0.08em", textTransform: "uppercase" }}>Avg Time</div>
                </div>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.inkLight }}>Error Rate</span>
                    <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: agent.errorRate > 5 ? C.red : C.green }}>{agent.errorRate}%</span>
                  </div>
                  <Bar value={agent.errorRate * 10} color={agent.errorRate > 5 ? C.red : C.green} />
                </div>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.inkLight }}>Success Rate</span>
                    <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.green }}>{100 - agent.errorRate}%</span>
                  </div>
                  <Bar value={100 - agent.errorRate} color={C.green} />
                </div>
                <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                  <button className="btn-ghost" style={{ padding: "6px 12px", fontSize: 11 }} onClick={() => setDetailAgent(agent)}>Details</button>
                  {agent.status !== "online" && (
                    <button className="btn-red" style={{ padding: "6px 12px" }} onClick={() => restartAgent(agent.id, agent.name)}>Restart</button>
                  )}
                </div>
              </div>

              {agent.status !== "online" && (
                <div style={{ marginTop: 14, padding: "8px 12px", background: C.redFaint, border: `1px solid ${C.red}33`, borderRadius: 3, display: "flex", gap: 10, alignItems: "center" }}>
                  <span style={{ color: C.red }}>⚠</span>
                  <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.red }}>{agent.lastError}</span>
                  <button className="btn-red" style={{ marginLeft: "auto", padding: "5px 12px" }} onClick={() => restartAgent(agent.id, agent.name)}>Restart Now</button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {detailAgent && (
        <AgentDetailModal agent={detailAgent} onClose={() => setDetailAgent(null)} onRestart={() => restartAgent(detailAgent.id, detailAgent.name)} />
      )}
    </div>
  );
}
