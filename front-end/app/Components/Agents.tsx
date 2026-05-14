"use client";

import { useState, useEffect } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";
import { getCurrentUserId, subscribeToTasks, type Task as DBTask } from "../../lib/db";
import { supabase } from "../../lib/supabase";

interface Agent {
  id: string; name: string; desc: string; status: "online" | "busy" | "offline";
  tasks: number; avgScore: number; color: string; icon: string; usage: number;
  agentType: string;
}

const AGENT_CONFIG: Omit<Agent, "tasks" | "avgScore" | "usage">[] = [
  { id: "1", name: "Summarization Agent", desc: "Extracts key findings, methodologies, and contributions from research papers into clear, structured summaries.", status: "online", color: C.gold, icon: "◈", agentType: "summarization" },
  { id: "2", name: "Literature Review Agent", desc: "Analyzes multiple papers to produce comparative reviews, identifying research gaps and thematic connections.", status: "online", color: C.sienna, icon: "◉", agentType: "literature_review" },
  { id: "3", name: "Citation Agent", desc: "Automatically extracts and formats references in APA, MLA, IEEE, or Chicago style, verified against CrossRef.", status: "online", color: C.umber, icon: "◎", agentType: "citation" },
  { id: "4", name: "Proposal Drafting Agent", desc: "Transforms research ideas into structured, polished proposals with proper academic tone and organization.", status: "online", color: C.inkMid, icon: "◐", agentType: "proposal" },
];

function StatusDot({ status }: { status: Agent["status"] }) {
  const c = status === "online" ? C.green : status === "busy" ? C.goldLight : C.inkLight;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ width: 7, height: 7, borderRadius: "50%", background: c, boxShadow: status === "online" ? `0 0 6px ${c}88` : "none" }} />
      <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: c, letterSpacing: "0.08em", textTransform: "uppercase" }}>
        {status}
      </span>
    </div>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  const [hov, setHov] = useState(false);
  return (
    <div onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)} style={{ ...cardBase, padding: "28px 24px", background: hov ? C.white : C.creamLight, borderColor: hov ? C.borderGold : C.border, transform: hov ? "translateY(-4px)" : "none", boxShadow: hov ? `0 8px 28px ${C.shadow}` : "none", cursor: "default", position: "relative", overflow: "hidden" }}>
      {hov && <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, transparent, ${agent.color}, transparent)` }} />}
      
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
        <div style={{ width: 44, height: 44, borderRadius: 4, background: `${agent.color}18`, border: `1px solid ${agent.color}33`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20 }}>{agent.icon}</div>
        <StatusDot status={agent.status} />
      </div>

      <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 17, fontWeight: 700, color: C.inkDark, marginBottom: 8 }}>{agent.name}</div>
      <p style={{ ...bodyText, fontSize: 13.5, marginBottom: 18, lineHeight: 1.6 }}>{agent.desc}</p>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        <div>
          <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 22, fontWeight: 900, color: C.inkDark }}>{agent.tasks}</div>
          <div style={{ ...sectionLabel, fontSize: 10 }}>Tasks Done</div>
        </div>
        <div>
          <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 22, fontWeight: 900, color: agent.color }}>{agent.avgScore}</div>
          <div style={{ ...sectionLabel, fontSize: 10 }}>Avg Score</div>
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
          <span style={{ ...bodyText, fontSize: 12 }}>Usage</span>
          <span style={{ ...bodyText, fontSize: 12 }}>{agent.usage}%</span>
        </div>
        <div style={{ height: 4, background: C.creamDark, border: `1px solid ${C.border}`, borderRadius: 2, overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${agent.usage}%`, background: `linear-gradient(90deg, ${agent.color}, ${agent.color}bb)`, borderRadius: 2, transition: "width 1.2s cubic-bezier(.4,0,.2,1)" }} />
        </div>
      </div>

      <button className="btn-ink" style={{ width: "100%", padding: "9px 0", fontSize: 11.5 }}>
        Run Agent
      </button>
    </div>
  );
}

export default function Agents() {
  const [dbTasks, setDbTasks] = useState<DBTask[]>([]);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    let isMounted = true;
    let unsubTasks: (() => void) | undefined;
    let unsubLogs: (() => void) | undefined;

    getCurrentUserId().then(uid => {
      if (uid) {
        unsubTasks = subscribeToTasks(uid, setDbTasks);
        
        // Manual subscription for agent_logs (only user's logs)
        const channelId = Math.random().toString(36).substring(2, 10);
        const channel = supabase
          .channel(`user_agent_logs_${channelId}`)
          .on("postgres_changes", { event: "INSERT", schema: "public", table: "agent_logs", filter: `user_id=eq.${uid}` }, 
            payload => { if (isMounted) setLogs(prev => [payload.new, ...prev].slice(0, 10)); }
          )
          .subscribe();
        
        supabase.from("agent_logs").select("*").eq("user_id", uid).order("created_at", { ascending: false }).limit(10)
          .then(({ data }) => { if (isMounted) setLogs(data || []); });

        unsubLogs = () => supabase.removeChannel(channel);
      }
    });

    return () => {
      isMounted = false;
      unsubTasks?.();
      unsubLogs?.();
    };
  }, []);

  const agents: Agent[] = AGENT_CONFIG.map(cfg => {
    const agentTasks = dbTasks.filter(t => t.agent_type === cfg.agentType);
    const completed = agentTasks.filter(t => t.status === "completed");
    const avg = completed.length > 0 ? Math.round(completed.reduce((acc, t) => acc + (t.quality_score || 0), 0) / completed.length) : 0;
    const usage = dbTasks.length > 0 ? Math.round((agentTasks.length / dbTasks.length) * 100) : 0;
    
    return {
      ...cfg,
      tasks: completed.length,
      avgScore: avg,
      usage: usage,
      status: agentTasks.some(t => t.status === "processing") ? "busy" : "online"
    };
  });

  return (
    <>
      <div className="fade-1" style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ height: 1, width: 28, background: C.gold }} />
          <span style={{ ...sectionLabel }}>AI Workforce</span>
        </div>
        <h1 style={{ ...headingStyle, fontSize: "clamp(24px, 3vw, 34px)" }}>Research <em style={{ color: C.gold }}>Agents</em></h1>
        <p style={{ ...bodyText, fontSize: 15, marginTop: 6, maxWidth: 540 }}>Four specialized AI agents, each purpose-built for a specific academic research task.</p>
      </div>

      <div className="fade-2" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 18, marginBottom: 36 }}>
        {agents.map((a, i) => <div key={a.id} style={{ animation: `fadeUp .6s ${i * 0.08 + 0.1}s both` }}><AgentCard agent={a} /></div>)}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 24 }}>
        <div style={{ flex: 1, height: 1, background: C.border }} />
        <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 14, color: C.gold }}>✦</div>
        <div style={{ flex: 1, height: 1, background: C.border }} />
      </div>

      <div className="fade-3">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <div style={{ height: 1, width: 22, background: C.gold }} />
          <span style={{ ...sectionLabel }}>Agent Activity Log</span>
        </div>
        <div style={{ ...cardBase, padding: "20px 22px" }}>
          {logs.length === 0 ? (
            <div style={{ textAlign: "center", padding: "40px 0", ...bodyText, fontSize: 14 }}>No recent activity.</div>
          ) : (
            logs.map((a, i) => {
              const cfg = AGENT_CONFIG.find(c => c.name.includes(a.agent) || c.agentType === a.agent);
              const color = cfg?.color || C.gold;
              return (
                <div key={a.id || i} style={{ display: "flex", gap: 12, padding: "12px 0", borderBottom: i < logs.length - 1 ? `1px solid ${C.border}` : "none" }}>
                  <div style={{ width: 30, height: 30, borderRadius: "50%", background: `${color}18`, border: `1px solid ${color}33`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, flexShrink: 0 }}>
                    {a.level === "error" ? "⚠" : "⚡"}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkDark, lineHeight: 1.5 }}>
                      <strong style={{ color: color }}>{a.agent}</strong> — {a.message}
                    </div>
                    <div style={{ ...bodyText, fontSize: 11, marginTop: 2 }}>{new Date(a.created_at).toLocaleString()}</div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </>
  );
}
