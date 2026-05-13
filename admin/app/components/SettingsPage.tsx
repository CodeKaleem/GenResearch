"use client";
import { useState } from "react";
import { C, SectionHead, PageTitle, Modal, Field, inputStyle, selectStyle } from "./shared";

function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button onClick={() => onChange(!value)} style={{ width: 44, height: 24, borderRadius: 12, background: value ? C.gold : C.creamDark, border: `1.5px solid ${value ? C.gold : C.border}`, cursor: "pointer", position: "relative", transition: "all .25s", flexShrink: 0 }}>
      <div style={{ width: 17, height: 17, borderRadius: "50%", background: value ? C.white : C.inkLight, position: "absolute", top: 2, left: value ? 22 : 2, transition: "left .25s" }} />
    </button>
  );
}

function SettingRow({ label, sub, children }: { label: string; sub?: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 0", borderBottom: `1px solid ${C.border}` }}>
      <div>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, fontWeight: 500, color: C.inkDark }}>{label}</div>
        {sub && <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.inkLight, marginTop: 2 }}>{sub}</div>}
      </div>
      <div>{children}</div>
    </div>
  );
}

function SettingCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card" style={{ padding: "22px 24px", marginBottom: 22 }}>
      <SectionHead label={title} />
      {children}
    </div>
  );
}

export default function SettingsPage() {
  const [toast, setToast] = useState("");
  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3000); };

  // General
  const [platformName, setPlatformName] = useState("GenResearch");
  const [adminEmail, setAdminEmail] = useState("admin@comsats.edu.pk");
  const [timezone, setTimezone] = useState("Asia/Karachi");

  // AI / LLM
  const [model, setModel] = useState("gpt-3.5-turbo");
  const [temperature, setTemperature] = useState("0.7");
  const [maxTokens, setMaxTokens] = useState("2048");
  const [streamEnabled, setStreamEnabled] = useState(true);

  // Notifications
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [agentFailAlert, setAgentFailAlert] = useState(true);
  const [costAlert, setCostAlert] = useState(true);
  const [newUserAlert, setNewUserAlert] = useState(false);
  const [dailyDigest, setDailyDigest] = useState(true);

  // Security
  const [mfaRequired, setMfaRequired] = useState(false);
  const [sessionTimeout, setSessionTimeout] = useState("60");
  const [ipWhitelist, setIpWhitelist] = useState(false);

  // ChromaDB / RAG
  const [chunkSize, setChunkSize] = useState("512");
  const [chunkOverlap, setChunkOverlap] = useState("64");
  const [topK, setTopK] = useState("5");
  const [embeddingModel, setEmbeddingModel] = useState("text-embedding-ada-002");

  // Maintenance
  const [maintenanceMode, setMaintenanceMode] = useState(false);
  const [autoBackup, setAutoBackup] = useState(true);

  // API Key modal
  const [showApiKey, setShowApiKey] = useState(false);
  const [newApiKey, setNewApiKey] = useState("");

  return (
    <div style={{ animation: "fadeUp .5s both" }}>
      <PageTitle
        title="Settings"
        sub="Configuration"
        actions={<button className="btn-gold" onClick={() => showToast("All settings saved successfully")}>Save All Changes</button>}
      />

      {toast && (
        <div style={{ position: "fixed", bottom: 28, right: 28, zIndex: 900, background: C.inkDark, color: C.cream, padding: "12px 20px", borderRadius: 4, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, boxShadow: `0 8px 24px rgba(0,0,0,0.18)`, animation: "fadeUp .3s both", display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ color: C.green }}>✓</span> {toast}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 22 }}>
        {/* LEFT */}
        <div>
          {/* General */}
          <SettingCard title="General">
            <Field label="Platform Name">
              <input style={inputStyle} value={platformName} onChange={e => setPlatformName(e.target.value)} />
            </Field>
            <Field label="Admin Contact Email">
              <input style={inputStyle} type="email" value={adminEmail} onChange={e => setAdminEmail(e.target.value)} />
            </Field>
            <Field label="Timezone">
              <select style={selectStyle} value={timezone} onChange={e => setTimezone(e.target.value)}>
                <option value="Asia/Karachi">Asia/Karachi (PKT, UTC+5)</option>
                <option value="UTC">UTC</option>
                <option value="America/New_York">America/New_York (EST)</option>
                <option value="Europe/London">Europe/London (GMT)</option>
              </select>
            </Field>
            <button className="btn-ink" style={{ marginTop: 8 }} onClick={() => showToast("General settings saved")}>Save General</button>
          </SettingCard>

          {/* AI/LLM */}
          <SettingCard title="AI & LLM Configuration">
            <Field label="Default LLM Model">
              <select style={selectStyle} value={model} onChange={e => setModel(e.target.value)}>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                <option value="gpt-4">GPT-4</option>
                <option value="gpt-4o">GPT-4o</option>
                <option value="gpt-4o-mini">GPT-4o Mini</option>
              </select>
            </Field>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <Field label="Temperature (0–1)">
                <input style={inputStyle} type="number" step="0.1" min="0" max="1" value={temperature} onChange={e => setTemperature(e.target.value)} />
              </Field>
              <Field label="Max Tokens">
                <input style={inputStyle} type="number" value={maxTokens} onChange={e => setMaxTokens(e.target.value)} />
              </Field>
            </div>
            <SettingRow label="Streaming Responses" sub="Enable token streaming for real-time LLM output">
              <Toggle value={streamEnabled} onChange={setStreamEnabled} />
            </SettingRow>
            <div style={{ marginTop: 14 }}>
              <button className="btn-ghost" onClick={() => setShowApiKey(true)}>🔑 Rotate OpenAI API Key</button>
            </div>
          </SettingCard>

          {/* RAG */}
          <SettingCard title="RAG & ChromaDB">
            <Field label="Embedding Model">
              <select style={selectStyle} value={embeddingModel} onChange={e => setEmbeddingModel(e.target.value)}>
                <option value="text-embedding-ada-002">text-embedding-ada-002</option>
                <option value="text-embedding-3-small">text-embedding-3-small</option>
                <option value="text-embedding-3-large">text-embedding-3-large</option>
              </select>
            </Field>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              <Field label="Chunk Size">
                <input style={inputStyle} type="number" value={chunkSize} onChange={e => setChunkSize(e.target.value)} />
              </Field>
              <Field label="Chunk Overlap">
                <input style={inputStyle} type="number" value={chunkOverlap} onChange={e => setChunkOverlap(e.target.value)} />
              </Field>
              <Field label="Top-K Results">
                <input style={inputStyle} type="number" value={topK} onChange={e => setTopK(e.target.value)} />
              </Field>
            </div>
            <button className="btn-ink" style={{ marginTop: 8 }} onClick={() => showToast("RAG configuration updated")}>Apply RAG Settings</button>
          </SettingCard>
        </div>

        {/* RIGHT */}
        <div>
          {/* Notifications */}
          <SettingCard title="Notifications & Alerts">
            <SettingRow label="Email Alerts" sub="Send alerts to admin contact email">
              <Toggle value={emailAlerts} onChange={setEmailAlerts} />
            </SettingRow>
            <SettingRow label="Agent Failure Alerts" sub="Notify when an AI agent goes offline or degrades">
              <Toggle value={agentFailAlert} onChange={setAgentFailAlert} />
            </SettingRow>
            <SettingRow label="Cost Threshold Alerts" sub="Alert when API spend exceeds 80% of daily limit">
              <Toggle value={costAlert} onChange={setCostAlert} />
            </SettingRow>
            <SettingRow label="New User Registrations" sub="Email notification for each new signup">
              <Toggle value={newUserAlert} onChange={setNewUserAlert} />
            </SettingRow>
            <SettingRow label="Daily Activity Digest" sub="Receive a daily summary at 08:00 PKT">
              <Toggle value={dailyDigest} onChange={setDailyDigest} />
            </SettingRow>
            <div style={{ marginTop: 16 }}>
              <button className="btn-ghost" onClick={() => showToast("Test alert sent to admin email")}>Send Test Alert</button>
            </div>
          </SettingCard>

          {/* Security */}
          <SettingCard title="Security">
            <SettingRow label="Require MFA" sub="All admin accounts must use multi-factor authentication">
              <Toggle value={mfaRequired} onChange={setMfaRequired} />
            </SettingRow>
            <SettingRow label="IP Whitelisting" sub="Restrict admin panel access to approved IPs only">
              <Toggle value={ipWhitelist} onChange={setIpWhitelist} />
            </SettingRow>
            <Field label="Session Timeout (minutes)">
              <input style={inputStyle} type="number" value={sessionTimeout} onChange={e => setSessionTimeout(e.target.value)} />
            </Field>
            <div style={{ marginTop: 8, display: "flex", gap: 10 }}>
              <button className="btn-ghost" onClick={() => showToast("All user sessions terminated")}>Force Logout All Users</button>
              <button className="btn-ghost" onClick={() => showToast("Security audit log downloaded")}>Download Audit Log</button>
            </div>
          </SettingCard>

          {/* Maintenance */}
          <SettingCard title="Maintenance">
            <SettingRow label="Maintenance Mode" sub="Show a maintenance page to all non-admin users">
              <Toggle value={maintenanceMode} onChange={setMaintenanceMode} />
            </SettingRow>
            <SettingRow label="Automatic Backups" sub="Daily backup of ChromaDB collections and uploads">
              <Toggle value={autoBackup} onChange={setAutoBackup} />
            </SettingRow>
            <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 10 }}>
              <button className="btn-ghost" onClick={() => showToast("Manual backup initiated…")}>↓ Run Manual Backup</button>
              <button className="btn-ghost" onClick={() => showToast("Cache cleared successfully")}>🗑 Clear Application Cache</button>
              <button className="btn-red" style={{ fontSize: 12 }} onClick={() => { if (confirm("Flush all ChromaDB collections? This CANNOT be undone.")) showToast("ChromaDB flushed"); }}>⚠ Flush ChromaDB Collections</button>
            </div>
          </SettingCard>
        </div>
      </div>

      {/* API Key Modal */}
      {showApiKey && (
        <Modal title="Rotate OpenAI API Key" onClose={() => setShowApiKey(false)}>
          <div style={{ padding: "12px 14px", background: C.redFaint, border: `1px solid ${C.red}33`, borderRadius: 3, marginBottom: 16 }}>
            <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12.5, color: C.red }}>⚠ Rotating the key will immediately invalidate the current one. All active AI tasks will pause until the new key is applied.</div>
          </div>
          <Field label="New OpenAI API Key">
            <input style={inputStyle} type="password" placeholder="sk-proj-…" value={newApiKey} onChange={e => setNewApiKey(e.target.value)} />
          </Field>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 20 }}>
            <button className="btn-ghost" onClick={() => setShowApiKey(false)}>Cancel</button>
            <button className="btn-gold" onClick={() => { setShowApiKey(false); showToast("API key updated and applied"); }}>Apply New Key</button>
          </div>
        </Modal>
      )}
    </div>
  );
}
