"use client";
import { useState } from "react";
import { C, Badge, SectionHead, PageTitle, Modal, Field, inputStyle, selectStyle } from "./shared";

type Severity = "critical" | "warning" | "info";
type AlertStatus = "active" | "acknowledged" | "resolved";

interface Alert {
  id: string; title: string; message: string;
  severity: Severity; status: AlertStatus;
  time: string; agent?: string; resolvedAt?: string;
}

const INITIAL_ALERTS: Alert[] = [
  { id: "1", title: "Citation Agent Degraded",         message: "CrossRef API error rate at 8.4% (threshold: 5%). Tasks may fail or return incomplete citations. Check API key configuration in Settings.", severity: "critical", status: "active",       time: "14:31:44", agent: "Citation Agent" },
  { id: "2", title: "API Cost Approaching Limit",      message: "Today's OpenAI spend is at $4.32 (43% of $10 daily limit). At current rate, limit will be reached by 22:00 PKT.", severity: "warning",  status: "active",       time: "14:25:00" },
  { id: "3", title: "ChromaDB Query Failure",          message: "RAG Engine returned a null embedding on 3 consecutive requests. Likely cause: corrupted vector for document #487.", severity: "critical", status: "acknowledged", time: "14:28:55", agent: "RAG Engine" },
  { id: "4", title: "User Token Limit Warning",        message: "User hamza.tariq has consumed 78% of his daily token quota. Auto-throttling will activate at 90%.", severity: "warning",  status: "acknowledged", time: "14:25:00" },
  { id: "5", title: "Storage Usage > 25%",             message: "ChromaDB + uploads now at 12 GB of 45 GB. No immediate action required, but plan for expansion beyond 35 GB.", severity: "info",     status: "active",       time: "14:10:00" },
  { id: "6", title: "Slow LLM Response Detected",     message: "Summarization Agent average response time increased to 38s (baseline: 24s). May indicate OpenAI service degradation.", severity: "warning",  status: "resolved",     time: "13:55:00", resolvedAt: "14:20:00" },
  { id: "7", title: "New Admin Login from New IP",     message: "Admin account logged in from 192.168.1.42 — an IP not previously seen. Verify this is an authorized session.", severity: "warning",  status: "resolved",     time: "14:20:00", resolvedAt: "14:22:00" },
];

const severityColor: Record<Severity, string> = { critical: C.red, warning: C.goldLight, info: C.blue };
const severityIcon:  Record<Severity, string> = { critical: "⚠", warning: "⚑", info: "ℹ" };
const statusColor:   Record<AlertStatus, string> = { active: C.red, acknowledged: C.goldLight, resolved: C.green };

function AlertCard({ alert, onAcknowledge, onResolve, onDismiss }: {
  alert: Alert;
  onAcknowledge: () => void;
  onResolve: () => void;
  onDismiss: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const sc = severityColor[alert.severity];

  return (
    <div style={{
      background: C.creamLight,
      border: `1px solid ${alert.status === "active" ? sc + "44" : C.border}`,
      borderLeft: `3px solid ${sc}`,
      borderRadius: 4,
      marginBottom: 12,
      overflow: "hidden",
      transition: "box-shadow .2s",
    }}
      onMouseEnter={e => (e.currentTarget.style.boxShadow = `0 4px 18px ${C.shadow}`)}
      onMouseLeave={e => (e.currentTarget.style.boxShadow = "none")}
    >
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 14, padding: "16px 18px", cursor: "pointer" }} onClick={() => setExpanded(e => !e)}>
        <span style={{ fontSize: 18, color: sc, flexShrink: 0, marginTop: 1 }}>{severityIcon[alert.severity]}</span>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4, flexWrap: "wrap" }}>
            <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 15, fontWeight: 700, color: C.inkDark }}>{alert.title}</span>
            <Badge label={alert.severity}    color={sc} pulse={alert.status === "active" && alert.severity === "critical"} />
            <Badge label={alert.status}      color={statusColor[alert.status]} />
            {alert.agent && <Badge label={alert.agent} color={C.umber} />}
          </div>
          <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkLight }}>
            {expanded ? alert.message : alert.message.slice(0, 90) + (alert.message.length > 90 ? "…" : "")}
          </div>
        </div>
        <div style={{ flexShrink: 0, textAlign: "right" }}>
          <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, color: C.inkLight }}>{alert.time}</div>
          {alert.resolvedAt && <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, color: C.green }}>Resolved {alert.resolvedAt}</div>}
        </div>
        <span style={{ color: C.inkLight, fontSize: 12, flexShrink: 0, marginTop: 4 }}>{expanded ? "▲" : "▼"}</span>
      </div>

      {/* Expanded actions */}
      {expanded && (
        <div style={{ padding: "0 18px 16px 50px", borderTop: `1px solid ${C.border}`, paddingTop: 14 }}>
          <p style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkMid, lineHeight: 1.7, marginBottom: 14 }}>{alert.message}</p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {alert.status === "active" && (
              <>
                <button className="btn-gold" style={{ fontSize: 11, padding: "6px 14px" }} onClick={e => { e.stopPropagation(); onAcknowledge(); }}>✓ Acknowledge</button>
                <button className="btn-green" style={{ fontSize: 11, padding: "6px 14px" }} onClick={e => { e.stopPropagation(); onResolve(); }}>✔ Mark Resolved</button>
                <button className="btn-ghost" style={{ fontSize: 11, padding: "6px 12px" }} onClick={e => { e.stopPropagation(); onDismiss(); }}>Dismiss</button>
              </>
            )}
            {alert.status === "acknowledged" && (
              <>
                <button className="btn-green" style={{ fontSize: 11, padding: "6px 14px" }} onClick={e => { e.stopPropagation(); onResolve(); }}>✔ Mark Resolved</button>
                <button className="btn-ghost" style={{ fontSize: 11, padding: "6px 12px" }} onClick={e => { e.stopPropagation(); onDismiss(); }}>Dismiss</button>
              </>
            )}
            {alert.status === "resolved" && (
              <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.green }}>✔ This alert has been resolved.</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function CreateAlertModal({ onClose, onCreate }: { onClose: () => void; onCreate: (a: Alert) => void }) {
  const [title, setTitle]   = useState("");
  const [message, setMessage] = useState("");
  const [severity, setSeverity] = useState<Severity>("warning");

  return (
    <Modal title="Create System Alert" onClose={onClose}>
      <Field label="Alert Title">
        <input style={inputStyle} placeholder="e.g. Scheduled Maintenance Tonight" value={title} onChange={e => setTitle(e.target.value)} />
      </Field>
      <Field label="Severity">
        <select style={selectStyle} value={severity} onChange={e => setSeverity(e.target.value as Severity)}>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="critical">Critical</option>
        </select>
      </Field>
      <Field label="Message">
        <textarea style={{ ...inputStyle, height: 100, resize: "vertical" }} placeholder="Describe the issue and recommended action…" value={message} onChange={e => setMessage(e.target.value)} />
      </Field>
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 20 }}>
        <button className="btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn-gold" onClick={() => {
          if (!title) return;
          const now = new Date();
          onCreate({ id: Date.now().toString(), title, message: message || "No details provided.", severity, status: "active", time: now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) });
          onClose();
        }}>Create Alert</button>
      </div>
    </Modal>
  );
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>(INITIAL_ALERTS);
  const [filterStatus, setFilterStatus] = useState<AlertStatus | "All">("All");
  const [filterSeverity, setFilterSeverity] = useState<Severity | "All">("All");
  const [showCreate, setShowCreate] = useState(false);
  const [toast, setToast] = useState("");

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3000); };

  const update = (id: string, patch: Partial<Alert>) =>
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, ...patch } : a));

  const acknowledge = (id: string) => { update(id, { status: "acknowledged" }); showToast("Alert acknowledged"); };
  const resolve = (id: string) => {
    const now = new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
    update(id, { status: "resolved", resolvedAt: now });
    showToast("Alert marked as resolved");
  };
  const dismiss = (id: string) => { setAlerts(prev => prev.filter(a => a.id !== id)); showToast("Alert dismissed"); };

  const filtered = alerts.filter(a => {
    const matchS = filterStatus === "All" || a.status === filterStatus;
    const matchSev = filterSeverity === "All" || a.severity === filterSeverity;
    return matchS && matchSev;
  });

  const active  = alerts.filter(a => a.status === "active").length;
  const acked   = alerts.filter(a => a.status === "acknowledged").length;
  const resolved = alerts.filter(a => a.status === "resolved").length;

  return (
    <div style={{ animation: "fadeUp .5s both" }}>
      <PageTitle
        title="Alerts & Notifications"
        sub="System Health"
        actions={
          <>
            <button className="btn-ghost" onClick={() => { setAlerts(prev => prev.map(a => a.status === "active" ? { ...a, status: "acknowledged" as AlertStatus } : a)); showToast("All active alerts acknowledged"); }}>Acknowledge All</button>
            <button className="btn-ink" onClick={() => setShowCreate(true)}>+ Create Alert</button>
          </>
        }
      />

      {toast && (
        <div style={{ position: "fixed", bottom: 28, right: 28, zIndex: 900, background: C.inkDark, color: C.cream, padding: "12px 20px", borderRadius: 4, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, boxShadow: `0 8px 24px rgba(0,0,0,0.18)`, animation: "fadeUp .3s both", display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ color: C.green }}>✓</span> {toast}
        </div>
      )}

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "Active",       value: active,   color: C.red },
          { label: "Acknowledged", value: acked,    color: C.goldLight },
          { label: "Resolved",     value: resolved, color: C.green },
        ].map(s => (
          <div key={s.label} className="card" style={{ padding: "16px 20px", borderLeft: `3px solid ${s.color}` }}>
            <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 32, fontWeight: 900, color: s.color }}>{s.value}</div>
            <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11, fontWeight: 600, color: C.inkLight, letterSpacing: "0.10em", textTransform: "uppercase", marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>
        {(["All", "active", "acknowledged", "resolved"] as const).map(f => (
          <button key={f} onClick={() => setFilterStatus(f)}
            style={{ padding: "7px 18px", background: filterStatus === f ? C.inkDark : "transparent", border: `1.5px solid ${filterStatus === f ? C.inkDark : C.border}`, borderRadius: 20, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: filterStatus === f ? C.cream : C.inkLight, cursor: "pointer", transition: "all .2s" }}
          >{f.charAt(0).toUpperCase() + f.slice(1)}</button>
        ))}
        <div style={{ width: 1, background: C.border, margin: "0 4px" }} />
        {(["All", "critical", "warning", "info"] as const).map(f => {
          const color = f === "All" ? C.inkLight : severityColor[f as Severity];
          return (
            <button key={f} onClick={() => setFilterSeverity(f)}
              style={{ padding: "7px 18px", background: filterSeverity === f ? color : "transparent", border: `1.5px solid ${filterSeverity === f ? color : C.border}`, borderRadius: 20, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: filterSeverity === f ? "#fff" : color, cursor: "pointer", transition: "all .2s" }}
            >{f.charAt(0).toUpperCase() + f.slice(1)}</button>
          );
        })}
      </div>

      {/* Alert list */}
      {filtered.length === 0
        ? <div style={{ padding: 48, textAlign: "center", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 15, color: C.inkLight }}>✓ No alerts match your current filter.</div>
        : filtered.map(a => (
          <AlertCard key={a.id} alert={a}
            onAcknowledge={() => acknowledge(a.id)}
            onResolve={() => resolve(a.id)}
            onDismiss={() => dismiss(a.id)}
          />
        ))
      }

      {showCreate && <CreateAlertModal onClose={() => setShowCreate(false)} onCreate={a => { setAlerts(prev => [a, ...prev]); showToast("Alert created"); }} />}
    </div>
  );
}
