"use client";

import { useState } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";

interface Agent {
  id: string; name: string; desc: string; status: "online" | "busy" | "offline";
  tasks: number; avgScore: number; color: string; icon: string; usage: number;
}

const agents: Agent[] = [
  { id: "1", name: "Summarization Agent", desc: "Extracts key findings, methodologies, and contributions from research papers into clear, structured summaries.", status: "online", tasks: 42, avgScore: 89, color: C.gold, icon: "◈", usage: 50 },
  { id: "2", name: "Literature Review Agent", desc: "Analyzes multiple papers to produce comparative reviews, identifying research gaps and thematic connections.", status: "busy", tasks: 18, avgScore: 91, color: C.sienna, icon: "◉", usage: 25 },
  { id: "3", name: "Citation Agent", desc: "Automatically extracts and formats references in APA, MLA, IEEE, or Chicago style, verified against CrossRef.", status: "online", tasks: 31, avgScore: 95, color: C.umber, icon: "◎", usage: 13 },
  { id: "4", name: "Proposal Drafting Agent", desc: "Transforms research ideas into structured, polished proposals with proper academic tone and organization.", status: "online", tasks: 12, avgScore: 84, color: C.inkMid, icon: "◐", usage: 12 },
];

const activityLog = [
  { agent: "Summarization Agent", action: "Completed summary for 'Transformer Architectures in NLP'", time: "Today, 2:14 PM", color: C.gold },
  { agent: "Literature Review Agent", action: "Started comparative analysis for BERT vs GPT study", time: "Today, 3:01 PM", color: C.sienna },
  { agent: "Citation Agent", action: "Extracted 4 citations in APA format", time: "Yesterday, 4:22 PM", color: C.umber },
  { agent: "Summarization Agent", action: "Completed summary for 'Federated Learning Survey'", time: "Yesterday, 11:15 AM", color: C.gold },
  { agent: "Proposal Drafting Agent", action: "Generated proposal draft for RL in Robotics", time: "3 days ago", color: C.inkMid },
  { agent: "Citation Agent", action: "Formatted 12 references in IEEE style", time: "4 days ago", color: C.umber },
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

      <button className="btn-ink" style={{ width: "100%", padding: "9px 0", fontSize: 11.5 }} onClick={() => alert(agent.status === "busy" ? "Viewing progress for " + agent.name : "Running " + agent.name + "…")}>
        {agent.status === "busy" ? "View Progress" : "Run Agent"}
      </button>
    </div>
  );
}

export default function Agents() {
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
          {activityLog.map((a, i) => (
            <div key={i} style={{ display: "flex", gap: 12, padding: "12px 0", borderBottom: i < activityLog.length - 1 ? `1px solid ${C.border}` : "none" }}>
              <div style={{ width: 30, height: 30, borderRadius: "50%", background: `${a.color}18`, border: `1px solid ${a.color}33`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, flexShrink: 0 }}>⚡</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkDark, lineHeight: 1.5 }}>
                  <strong style={{ color: a.color }}>{a.agent}</strong> — {a.action}
                </div>
                <div style={{ ...bodyText, fontSize: 11, marginTop: 2 }}>{a.time}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
