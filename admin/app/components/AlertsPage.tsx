"use client";
import { useState, useEffect } from "react";
import { C, Badge, SectionHead, PageTitle, Modal, Field, inputStyle, selectStyle } from "./shared";
import { subscribeToSystemAlerts, updateSystemAlert as updateAlert, deleteSystemAlert as deleteAlert, createSystemAlert as createAlert, type SystemAlert } from "../../lib/db";

type Severity = "critical" | "warning" | "info";
type AlertStatus = "active" | "acknowledged" | "resolved";

interface Alert {
  id: string; title: string; message: string;
  severity: Severity; status: AlertStatus;
  time: string; agent?: string; resolvedAt?: string;
}

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
    }}>
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

      {expanded && (
        <div style={{ padding: "0 18px 16px 50px", borderTop: `1px solid ${C.border}`, paddingTop: 14 }}>
          <p style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, color: C.inkMid, lineHeight: 1.7, marginBottom: 14 }}>{alert.message}</p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {alert.status === "active" && (
              <>
                <button className="btn-gold" style={{ fontSize: 11, padding: "6px 14px" }} onClick={onAcknowledge}>✓ Acknowledge</button>
                <button className="btn-green" style={{ fontSize: 11, padding: "6px 14px" }} onClick={onResolve}>✔ Mark Resolved</button>
                <button className="btn-ghost" style={{ fontSize: 11, padding: "6px 12px" }} onClick={onDismiss}>Dismiss</button>
              </>
            )}
            {alert.status === "acknowledged" && (
              <>
                <button className="btn-green" style={{ fontSize: 11, padding: "6px 14px" }} onClick={onResolve}>✔ Mark Resolved</button>
                <button className="btn-ghost" style={{ fontSize: 11, padding: "6px 12px" }} onClick={onDismiss}>Dismiss</button>
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

function CreateAlertModal({ onClose, onCreate }: { onClose: () => void; onCreate: (a: Omit<SystemAlert, "id" | "created_at" | "resolved_at" | "resolved_by">) => void }) {
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
          onCreate({ title, message, severity, status: "active", agent: null });
          onClose();
        }}>Create Alert</button>
      </div>
    </Modal>
  );
}

export default function AlertsPage() {
  const [dbAlerts, setDbAlerts] = useState<SystemAlert[]>([]);
  const [filterStatus, setFilterStatus] = useState<AlertStatus | "All">("All");
  const [filterSeverity, setFilterSeverity] = useState<Severity | "All">("All");
  const [showCreate, setShowCreate] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    return subscribeToSystemAlerts(setDbAlerts);
  }, []);

  const alerts: Alert[] = dbAlerts.map(a => ({
    id: a.id,
    title: a.title,
    message: a.message,
    severity: a.severity as Severity,
    status: a.status as AlertStatus,
    time: new Date(a.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    agent: a.agent || undefined,
    resolvedAt: a.resolved_at ? new Date(a.resolved_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : undefined
  }));

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3000); };

  const handleAction = async (action: string, id: string) => {
    if (action === "acknowledge") {
      await updateAlert(id, { status: "acknowledged" });
      showToast("Alert acknowledged");
    } else if (action === "resolve") {
      await updateAlert(id, { status: "resolved", resolved_at: new Date().toISOString() });
      showToast("Alert marked as resolved");
    } else if (action === "dismiss") {
      await deleteAlert(id);
      showToast("Alert dismissed");
    }
  };

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
            <button className="btn-ghost">Acknowledge All</button>
            <button className="btn-ink" onClick={() => setShowCreate(true)}>+ Create Alert</button>
          </>
        }
      />

      {toast && (
        <div style={{ position: "fixed", bottom: 28, right: 28, zIndex: 900, background: C.inkDark, color: C.cream, padding: "12px 20px", borderRadius: 4, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, boxShadow: `0 8px 24px rgba(0,0,0,0.18)`, animation: "fadeUp .3s both", display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ color: C.green }}>✓</span> {toast}
        </div>
      )}

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

      {filtered.length === 0
        ? <div style={{ padding: 48, textAlign: "center", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 15, color: C.inkLight }}>✓ No alerts match your current filter.</div>
        : filtered.map(a => (
          <AlertCard key={a.id} alert={a}
            onAcknowledge={() => handleAction("acknowledge", a.id)}
            onResolve={() => handleAction("resolve", a.id)}
            onDismiss={() => handleAction("dismiss", a.id)}
          />
        ))
      }

      {showCreate && <CreateAlertModal onClose={() => setShowCreate(false)} onCreate={async (a) => { await createAlert(a); showToast("Alert created"); }} />}
    </div>
  );
}
