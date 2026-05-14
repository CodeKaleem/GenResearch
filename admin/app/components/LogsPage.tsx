"use client";
import { useState, useEffect, useRef } from "react";
import { C, Badge, SectionHead, PageTitle } from "./shared";
import { subscribeToAgentLogs, type AgentLog } from "../../lib/db";

type LogLevel = "info" | "warn" | "error" | "success";

interface LogEntry {
  id: string; level: LogLevel; message: string;
  time: string; timestamp: number; agent: string | null; user?: string | null;
}

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
  const [dbLogs, setDbLogs] = useState<AgentLog[]>([]);
  const [filter, setFilter] = useState<"All" | LogLevel>("All");
  const [search, setSearch] = useState("");
  const [liveMode, setLiveMode] = useState(true);
  const [newestId, setNewestId] = useState<string | null>(null);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!liveMode) return;
    const unsub = subscribeToAgentLogs((logs) => {
      setDbLogs(logs);
      if (logs.length > 0) setNewestId(logs[0].id);
    });
    return () => unsub();
  }, [liveMode]);

  const logs: LogEntry[] = dbLogs.map(l => ({
    id: l.id,
    level: l.level as LogLevel,
    message: l.message,
    time: new Date(l.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
    timestamp: new Date(l.created_at).getTime(),
    agent: l.agent,
    user: l.user_id?.split("-")[0] || "System"
  }));

  const filtered = logs.filter(l => {
    const matchLevel = filter === "All" || l.level === filter;
    const q = search.toLowerCase();
    const matchQ = !q || l.message.toLowerCase().includes(q) || (l.agent || "").toLowerCase().includes(q) || (l.user || "").toLowerCase().includes(q);
    return matchLevel && matchQ;
  });

  const counts = { 
    info: logs.filter(l => l.level === "info").length, 
    warn: logs.filter(l => l.level === "warn").length, 
    error: logs.filter(l => l.level === "error").length, 
    success: logs.filter(l => l.level === "success").length 
  };

  return (
    <div style={{ animation: "fadeUp .5s both" }}>
      <PageTitle
        title="System Logs"
        sub="Observability"
        actions={
          <>
            <button className="btn-ghost">↓ Export</button>
            <button className={`btn-${liveMode ? "gold" : "ghost"}`} onClick={() => setLiveMode(l => !l)}
              style={{ display: "flex", alignItems: "center", gap: 6 }}
            >
              {liveMode && <span style={{ width: 7, height: 7, borderRadius: "50%", background: C.cream, animation: "adminPulse 1.6s ease infinite", flexShrink: 0 }} />}
              {liveMode ? "Live" : "Paused"}
            </button>
          </>
        }
      />

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
                  <button className="btn-red" style={{ padding: "3px 10px" }} onClick={() => { setDbLogs([]); setShowClearConfirm(false); }}>Yes</button>
                  <button className="btn-ghost" style={{ padding: "3px 10px" }} onClick={() => setShowClearConfirm(false)}>No</button>
                </span>
            }
          </div>
        </div>

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
