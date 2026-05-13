"use client";
import { useState, useEffect, useRef } from "react";
import { C, Badge, SectionHead, PageTitle } from "./shared";

type LogLevel = "info" | "warn" | "error" | "success";

interface LogEntry {
  id: string; level: LogLevel; message: string;
  time: string; timestamp: number; agent?: string; user?: string;
}

const BASE_LOGS: LogEntry[] = [
  { id: "1",  level: "success", message: "Summarization task completed for user ali.ahmed",       time: "14:32:11", timestamp: Date.now() - 1000*60*2,  agent: "Summarization", user: "ali.ahmed" },
  { id: "2",  level: "warn",    message: "Citation Agent timeout on CrossRef API call — retrying", time: "14:31:44", timestamp: Date.now() - 1000*60*3,  agent: "Citation" },
  { id: "3",  level: "info",    message: "New user registration: nadia.k@fast.edu.pk",            time: "14:30:02", timestamp: Date.now() - 1000*60*4,  user: "nadia.k" },
  { id: "4",  level: "error",   message: "ChromaDB collection query failed — null embedding",     time: "14:28:55", timestamp: Date.now() - 1000*60*5,  agent: "RAG Engine" },
  { id: "5",  level: "success", message: "Literature Review generated — 5 papers, 62s",           time: "14:27:30", timestamp: Date.now() - 1000*60*6,  agent: "Lit Review" },
  { id: "6",  level: "info",    message: "Document processed: bert_nlp_survey.pdf (124 chunks)",  time: "14:26:11", timestamp: Date.now() - 1000*60*7 },
  { id: "7",  level: "warn",    message: "Token usage at 78% of daily limit for user hamza.tariq",time: "14:25:00", timestamp: Date.now() - 1000*60*8,  user: "hamza.tariq" },
  { id: "8",  level: "success", message: "Proposal draft generated — 91s",                        time: "14:23:45", timestamp: Date.now() - 1000*60*9,  agent: "Proposal" },
  { id: "9",  level: "info",    message: "Admin login from 192.168.1.42",                          time: "14:20:00", timestamp: Date.now() - 1000*60*12, user: "Admin" },
  { id: "10", level: "error",   message: "OpenAI API rate limit hit — queuing request",            time: "14:18:30", timestamp: Date.now() - 1000*60*14, agent: "Summarization" },
  { id: "11", level: "success", message: "Index rebuild completed — 3847 documents",               time: "14:15:00", timestamp: Date.now() - 1000*60*17 },
  { id: "12", level: "warn",    message: "Storage at 26% — 12 GB of 45 GB used",                 time: "14:10:00", timestamp: Date.now() - 1000*60*22 },
];

const levelColor: Record<LogLevel, string> = { info: C.blue, warn: C.goldLight, error: C.red, success: C.green };
const levelIcon:  Record<LogLevel, string> = { info: "ℹ", warn: "⚠", error: "✕", success: "✓" };

function LogRow({ entry, highlight }: { entry: LogEntry; highlight?: boolean }) {
  const lc = levelColor[entry.level];
  return (
    <div style={{ display: "flex", gap: 12, alignItems: "flex-start", padding: "9px 16px", borderBottom: `1px solid ${C.border}`, fontFamily: "'Crimson Pro', Georgia, serif", background: highlight ? `${lc}08` : "transparent", transition: "background .4s" }}>
      <span style={{ fontSize: 12, color: lc, flexShrink: 0, marginTop: 2 }}>{levelIcon[entry.level]}</span>
      <div style={{ flex: 1 }}>
        <span style={{ fontSize: 13, color: C.inkDark }}>{entry.message}</span>
        {entry.agent && <span style={{ fontSize: 11, color: C.gold, marginLeft: 8, background: C.goldFaint, border: `1px solid ${C.borderGold}`, borderRadius: 2, padding: "0px 6px" }}>{entry.agent}</span>}
        {entry.user && <span style={{ fontSize: 11, color: C.blue, marginLeft: 6, background: C.blueFaint, border: `1px solid ${C.blue}33`, borderRadius: 2, padding: "0px 6px" }}>{entry.user}</span>}
      </div>
      <span style={{ fontSize: 11, color: C.inkLight, flexShrink: 0, fontVariantNumeric: "tabular-nums" }}>{entry.time}</span>
    </div>
  );
}

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>(BASE_LOGS);
  const [filter, setFilter] = useState<"All" | LogLevel>("All");
  const [search, setSearch] = useState("");
  const [liveMode, setLiveMode] = useState(true);
  const [newestId, setNewestId] = useState<string | null>(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Simulate live log feed
  useEffect(() => {
    if (!liveMode) return;
    const LIVE_MESSAGES: Array<{ level: LogLevel; message: string; agent?: string; user?: string }> = [
      { level: "info",    message: "Health check ping — all services responding",          agent: "Monitor" },
      { level: "success", message: "Citation task completed — 3 references resolved",      agent: "Citation" },
      { level: "warn",    message: "Slow response from LLM (>90s) for user sara.malik",   agent: "Summarization", user: "sara.malik" },
      { level: "info",    message: "User kaleem@comsats.edu.pk started new research task", user: "kaleem" },
      { level: "error",   message: "Vector similarity search failed — retrying query",     agent: "RAG Engine" },
      { level: "success", message: "Proposal outline generated for usman.q@giki.edu.pk",   agent: "Proposal", user: "usman.q" },
    ];
    const interval = setInterval(() => {
      const msg = LIVE_MESSAGES[Math.floor(Math.random() * LIVE_MESSAGES.length)];
      const id = Date.now().toString();
      const now = new Date();
      const newEntry: LogEntry = { id, ...msg, time: now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" }), timestamp: now.getTime() };
      setLogs(prev => [newEntry, ...prev.slice(0, 99)]);
      setNewestId(id);
    }, 5000);
    return () => clearInterval(interval);
  }, [liveMode]);

  const filtered = logs.filter(l => {
    const matchLevel = filter === "All" || l.level === filter;
    const q = search.toLowerCase();
    const matchQ = !q || l.message.toLowerCase().includes(q) || (l.agent || "").toLowerCase().includes(q) || (l.user || "").toLowerCase().includes(q);
    return matchLevel && matchQ;
  });

  const counts = { info: logs.filter(l => l.level === "info").length, warn: logs.filter(l => l.level === "warn").length, error: logs.filter(l => l.level === "error").length, success: logs.filter(l => l.level === "success").length };

  return (
    <div style={{ animation: "fadeUp .5s both" }}>
      <PageTitle
        title="System Logs"
        sub="Observability"
        actions={
          <>
            <button className="btn-ghost" onClick={() => alert("Exporting logs…")}>↓ Export</button>
            <button className={`btn-${liveMode ? "gold" : "ghost"}`} onClick={() => setLiveMode(l => !l)}
              style={{ display: "flex", alignItems: "center", gap: 6 }}
            >
              {liveMode && <span style={{ width: 7, height: 7, borderRadius: "50%", background: C.cream, animation: "adminPulse 1.6s ease infinite", flexShrink: 0 }} />}
              {liveMode ? "Live" : "Paused"}
            </button>
          </>
        }
      />

      {/* Level summary pills */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
        {(["All", "success", "info", "warn", "error"] as const).map(f => {
          const count = f === "All" ? logs.length : counts[f as LogLevel];
          const color = f === "All" ? C.inkDark : levelColor[f as LogLevel];
          const active = filter === f;
          return (
            <button key={f} onClick={() => setFilter(f)}
              style={{ padding: "7px 16px", background: active ? color : "transparent", border: `1.5px solid ${active ? color : C.border}`, borderRadius: 20, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: active ? (f === "All" ? C.cream : "#fff") : color, cursor: "pointer", transition: "all .2s", display: "flex", alignItems: "center", gap: 6 }}
            >
              {f !== "All" && <span>{levelIcon[f as LogLevel]}</span>}
              {f === "All" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
              <span style={{ background: active ? "rgba(255,255,255,0.25)" : `${color}22`, borderRadius: 10, padding: "0 7px", fontSize: 11 }}>{count}</span>
            </button>
          );
        })}
        <div style={{ marginLeft: "auto", position: "relative" }}>
          <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: C.inkLight, fontSize: 13 }}>🔍</span>
          <input placeholder="Filter logs…" value={search} onChange={e => setSearch(e.target.value)}
            style={{ padding: "7px 12px 7px 30px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: "white", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkDark, outline: "none", width: 220 }}
            onFocus={e => (e.target.style.borderColor = C.gold)}
            onBlur={e => (e.target.style.borderColor = C.border)}
          />
        </div>
      </div>

      <div className="card">
        <div style={{ padding: "12px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ height: 1, width: 22, background: C.gold }} />
            <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 10.5, fontWeight: 600, color: C.gold, letterSpacing: "0.18em", textTransform: "uppercase" }}>System Logs</span>
            {liveMode && <span style={{ display: "flex", alignItems: "center", gap: 5, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.green }}><span style={{ width: 6, height: 6, borderRadius: "50%", background: C.green, animation: "adminPulse 1.6s ease infinite", display: "inline-block" }} /> Live</span>}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.inkLight }}>{filtered.length} entries</span>
            {!showClearConfirm
              ? <button className="btn-ghost" style={{ padding: "4px 12px", fontSize: 11 }} onClick={() => setShowClearConfirm(true)}>Clear</button>
              : <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.red, display: "flex", alignItems: "center", gap: 6 }}>
                  Confirm clear?
                  <button className="btn-red" style={{ padding: "3px 10px" }} onClick={() => { setLogs([]); setShowClearConfirm(false); }}>Yes</button>
                  <button className="btn-ghost" style={{ padding: "3px 10px" }} onClick={() => setShowClearConfirm(false)}>No</button>
                </span>
            }
          </div>
        </div>

        {/* Log entries */}
        <div style={{ maxHeight: "calc(100vh - 420px)", overflowY: "auto", minHeight: 300 }}>
          {filtered.length === 0
            ? <div style={{ padding: 40, textAlign: "center", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, color: C.inkLight }}>No logs match your filter.</div>
            : filtered.map(entry => <LogRow key={entry.id} entry={entry} highlight={entry.id === newestId} />)
          }
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
}
