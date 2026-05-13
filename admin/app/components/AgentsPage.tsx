"use client";
import { useState } from "react";
import { C, Badge, SectionHead, PageTitle, Modal, Bar, Num } from "./shared";

interface Agent {
  id: string; name: string; type: string;
  status: "online" | "degraded" | "offline";
  requests: number; avgTime: string; errorRate: number; uptime: number;
  lastError: string; model: string; rateLimit: number; rateLimitUsed: number;
  sparkRequests: number[];
}

const AGENTS: Agent[] = [
  { id: "sum",  name: "Summarization Agent",     type: "LLM Pipeline",  status: "online",   requests: 1842, avgTime: "24s",  errorRate: 1.2,  uptime: 99.8, lastError: "—",                         model: "GPT-3.5-turbo", rateLimit: 100, rateLimitUsed: 62, sparkRequests: [120,140,155,180,200,190,210,220,195,215] },
  { id: "lit",  name: "Literature Review Agent", type: "RAG + LLM",     status: "online",   requests: 634,  avgTime: "58s",  errorRate: 2.1,  uptime: 99.1, lastError: "—",                         model: "GPT-3.5-turbo", rateLimit: 50,  rateLimitUsed: 28, sparkRequests: [40,55,62,58,70,65,72,80,75,85] },
  { id: "cite", name: "Citation Agent",          type: "API Connector", status: "degraded", requests: 411,  avgTime: "12s",  errorRate: 8.4,  uptime: 94.3, lastError: "CrossRef timeout 14:31:44",  model: "CrossRef API",  rateLimit: 200, rateLimitUsed: 180, sparkRequests: [30,28,35,20,15,10,18,12,8,10] },
  { id: "prop", name: "Proposal Drafting Agent", type: "LLM Pipeline",  status: "online",   requests: 287,  avgTime: "91s",  errorRate: 1.8,  uptime: 98.6, lastError: "—",                         model: "GPT-3.5-turbo", rateLimit: 30,  rateLimitUsed: 12, sparkRequests: [18,20,22,25,28,30,27,32,35,30] },
  { id: "rag",  name: "RAG Engine",              type: "Vector Search", status: "online",   requests: 3104, avgTime: "4s",   errorRate: 0.4,  uptime: 99.9, lastError: "Null embed 14:28:55",       model: "ChromaDB",      rateLimit: 500, rateLimitUsed: 210, sparkRequests: [280,300,310,320,340,290,330,350,310,340] },
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
          { label: "Uptime",      value: `${agent.uptime}%`,            color: C.green },
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
  const [agents, setAgents] = useState<Agent[]>(AGENTS);
  const [detailAgent, setDetailAgent] = useState<Agent | null>(null);
  const [restartToast, setRestartToast] = useState("");

  const restartAgent = (id: string, name: string) => {
    setAgents(prev => prev.map(a => a.id === id ? { ...a, status: "online", errorRate: 0.5, uptime: 99.9 } : a));
    setRestartToast(`${name} restarted successfully`);
    setTimeout(() => setRestartToast(""), 3000);
  };

  const statusColor = (s: string) => ({ online: C.green, degraded: C.goldLight, offline: C.red }[s] ?? C.inkLight);

  const online = agents.filter(a => a.status === "online").length;
  const degraded = agents.filter(a => a.status === "degraded").length;
  const totalReqs = agents.reduce((s, a) => s + a.requests, 0);
  const avgUptime = (agents.reduce((s, a) => s + a.uptime, 0) / agents.length).toFixed(1);

  return (
    <div style={{ animation: "fadeUp .5s both" }}>
      <PageTitle
        title="Agent Monitor"
        sub="AI Infrastructure"
        actions={<><button className="btn-ghost" onClick={() => { setAgents(AGENTS); setRestartToast("All agents reset to baseline"); setTimeout(() => setRestartToast(""), 3000); }}>Reset All</button><button className="btn-ink" onClick={() => { setAgents(prev => prev.map(a => ({ ...a, status: "online" as const, errorRate: 0.5, uptime: 99.9 }))); setRestartToast("All agents restarted"); setTimeout(() => setRestartToast(""), 3000); }}>⟳ Restart All</button></>}
      />

      {/* Toast */}
      {restartToast && (
        <div style={{ position: "fixed", bottom: 28, right: 28, zIndex: 900, background: C.inkDark, color: C.cream, padding: "12px 20px", borderRadius: 4, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, boxShadow: `0 8px 24px ${C.shadowMd}`, animation: "fadeUp .3s both", display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ color: C.green }}>✓</span> {restartToast}
        </div>
      )}

      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "Online",       value: online,    color: C.green,   suffix: ` / ${agents.length}` },
          { label: "Degraded",     value: degraded,  color: C.goldLight, suffix: " agent(s)" },
          { label: "Total Requests", value: totalReqs, color: C.gold,  suffix: "" },
          { label: "Avg Uptime",   value: parseFloat(avgUptime), color: C.blue, suffix: "%" },
        ].map(s => (
          <div key={s.label} className="card" style={{ padding: "16px 18px" }}>
            <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 26, fontWeight: 900, color: s.color }}><Num to={s.value} suffix={s.suffix} /></div>
            <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.inkLight, letterSpacing: "0.10em", textTransform: "uppercase", marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Agent cards */}
      <div style={{ display: "grid", gap: 16 }}>
        {agents.map(agent => {
          const sc = statusColor(agent.status);
          return (
            <div key={agent.id} className="card" style={{ padding: "20px 22px", transition: "box-shadow .2s" }}
              onMouseEnter={e => (e.currentTarget.style.boxShadow = `0 6px 24px ${C.shadow}`)}
              onMouseLeave={e => (e.currentTarget.style.boxShadow = "none")}
            >
              <div style={{ display: "grid", gridTemplateColumns: "2fr 110px 90px 90px 160px 160px auto", alignItems: "center", gap: 12 }}>
                {/* Name + status */}
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{ width: 10, height: 10, borderRadius: "50%", background: sc, boxShadow: agent.status === "online" ? `0 0 8px ${sc}` : "none", animation: agent.status === "online" ? "adminPulse 2s ease infinite" : "none", flexShrink: 0 }} />
                  <div>
                    <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14.5, fontWeight: 600, color: C.inkDark }}>{agent.name}</div>
                    <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, color: C.inkLight }}>{agent.type} · {agent.model}</div>
                  </div>
                </div>
                {/* Status badge */}
                <div><Badge label={agent.status} color={sc} /></div>
                {/* Requests */}
                <div>
                  <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 800, color: C.inkDark }}>{agent.requests.toLocaleString()}</div>
                  <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, color: C.inkLight, letterSpacing: "0.08em", textTransform: "uppercase" }}>Requests</div>
                </div>
                {/* Avg time */}
                <div>
                  <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 800, color: C.inkDark }}>{agent.avgTime}</div>
                  <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10, color: C.inkLight, letterSpacing: "0.08em", textTransform: "uppercase" }}>Avg Time</div>
                </div>
                {/* Error rate */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.inkLight }}>Error Rate</span>
                    <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: agent.errorRate > 5 ? C.red : C.green }}>{agent.errorRate}%</span>
                  </div>
                  <Bar value={agent.errorRate * 10} color={agent.errorRate > 5 ? C.red : C.green} />
                </div>
                {/* Uptime */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.inkLight }}>Uptime</span>
                    <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.gold }}>{agent.uptime}%</span>
                  </div>
                  <Bar value={agent.uptime} color={C.gold} />
                </div>
                {/* Actions */}
                <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                  <button className="btn-ghost" style={{ padding: "6px 12px", fontSize: 11 }} onClick={() => setDetailAgent(agent)}>Details</button>
                  {agent.status !== "online" && (
                    <button className="btn-red" style={{ padding: "6px 12px" }} onClick={() => restartAgent(agent.id, agent.name)}>Restart</button>
                  )}
                </div>
              </div>

              {/* Last error warning */}
              {agent.status === "degraded" && (
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
