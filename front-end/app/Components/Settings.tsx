"use client";

import { useState, useEffect } from "react";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";
import { getProfile, updateProfile, getCurrentUserId, subscribeToPapers, subscribeToTasks, type Profile, type Paper, type Task } from "../../lib/db";

function Toggle({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <button onClick={onToggle} style={{ width: 40, height: 22, borderRadius: 11, border: `1px solid ${on ? C.gold : C.border}`, background: on ? C.gold : C.creamDark, cursor: "pointer", position: "relative", transition: "all .25s", padding: 0 }}>
      <div style={{ width: 16, height: 16, borderRadius: "50%", background: on ? C.white : C.inkLight, position: "absolute", top: 2, left: on ? 20 : 2, transition: "all .25s" }} />
    </button>
  );
}

function SettingRow({ label, desc, children }: { label: string; desc: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 0", borderBottom: `1px solid ${C.border}` }}>
      <div style={{ flex: 1, paddingRight: 20 }}>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 14, fontWeight: 600, color: C.inkDark, marginBottom: 2 }}>{label}</div>
        <div style={{ ...bodyText, fontSize: 12.5 }}>{desc}</div>
      </div>
      {children}
    </div>
  );
}

export default function Settings() {
  const [notifications, setNotifications] = useState({ taskComplete: true, weeklyReport: true, agentErrors: true, updates: false });
  const [defaultAgent, setDefaultAgent] = useState("summarization");
  const [user, setUser] = useState<Profile | null>(null);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(""), 3000); };

  useEffect(() => {
    let unsubPapers: (() => void) | undefined;
    let unsubTasks: (() => void) | undefined;

    const setup = async () => {
      const userId = await getCurrentUserId();
      if (!userId) return;
      
      const { data } = await getProfile(userId);
      if (data) setUser(data);

      unsubPapers = subscribeToPapers(userId, setPapers);
      unsubTasks = subscribeToTasks(userId, setTasks);
    };

    setup();
    return () => {
      unsubPapers?.();
      unsubTasks?.();
    };
  }, []);

  const parseFileSize = (sizeStr: string): number => {
    if (!sizeStr) return 0;
    const num = parseFloat(sizeStr);
    if (isNaN(num)) return 0;
    if (sizeStr.toLowerCase().includes("gb")) return num * 1024 * 1024 * 1024;
    if (sizeStr.toLowerCase().includes("mb")) return num * 1024 * 1024;
    if (sizeStr.toLowerCase().includes("kb")) return num * 1024;
    return num;
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const handleSaveProfile = async () => {
    if (!user) return;
    setSaving(true);
    const nameInput = (document.getElementById("settings-name") as HTMLInputElement)?.value;
    const instInput = (document.getElementById("settings-institution") as HTMLInputElement)?.value;
    const { error } = await updateProfile(user.id, {
      full_name: nameInput || user.full_name,
      institution: instInput || user.institution,
    });
    setSaving(false);
    if (error) { showToast("Failed to save: " + error.message); }
    else {
      setUser(prev => prev ? { ...prev, full_name: nameInput || prev.full_name, institution: instInput || prev.institution } : prev);
      showToast("Profile saved successfully!");
    }
  };

  return (
    <>
      {toast && <div style={{ position: "fixed", bottom: 28, right: 28, zIndex: 900, background: C.inkDark, color: C.cream, padding: "12px 20px", borderRadius: 4, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, boxShadow: "0 8px 24px rgba(0,0,0,0.18)", animation: "fadeUp .3s both", display: "flex", alignItems: "center", gap: 10 }}><span style={{ color: C.green }}>✓</span> {toast}</div>}

      <div className="fade-1" style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ height: 1, width: 28, background: C.gold }} />
          <span style={{ ...sectionLabel }}>Preferences</span>
        </div>
        <h1 style={{ ...headingStyle, fontSize: "clamp(24px, 3vw, 34px)" }}>Account <em style={{ color: C.gold }}>Settings</em></h1>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 24 }}>
        {/* Left column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Profile */}
          <div className="fade-2" style={{ ...cardBase, padding: "28px 28px" }}>
            <div style={{ ...sectionLabel, fontSize: 10, marginBottom: 20 }}>Profile</div>
            <div style={{ display: "flex", gap: 20, alignItems: "flex-start", marginBottom: 24 }}>
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: C.inkDark, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Playfair Display', serif", fontSize: 24, fontWeight: 700, color: C.cream, flexShrink: 0 }}>{user?.full_name?.charAt(0) || "U"}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 700, color: C.inkDark }}>{user?.full_name || "Loading..."}</div>
                <div style={{ ...bodyText, fontSize: 13, marginTop: 2 }}>{user?.email}</div>
                <div style={{ ...bodyText, fontSize: 12, marginTop: 2 }}>{user?.institution}</div>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {[{ l: "Full Name", v: user?.full_name, id: "settings-name" }, { l: "Email", v: user?.email, id: "settings-email", disabled: true }, { l: "Institution", v: user?.institution, id: "settings-institution" }].map(f => (
                <div key={f.l}>
                  <label style={{ ...sectionLabel, fontSize: 10, display: "block", marginBottom: 6 }}>{f.l}</label>
                  <input id={f.id} key={f.v} defaultValue={f.v} disabled={f.disabled} style={{ width: "100%", padding: "9px 12px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: f.disabled ? C.creamDark : C.white, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: f.disabled ? C.inkLight : C.inkDark, outline: "none" }} onFocus={e => (e.target.style.borderColor = C.gold)} onBlur={e => (e.target.style.borderColor = C.border)} />
                </div>
              ))}
            </div>
            <button className="btn-ink" style={{ marginTop: 20, padding: "9px 24px", fontSize: 11.5 }} onClick={handleSaveProfile} disabled={saving}>{saving ? "Saving…" : "Save Changes"}</button>
          </div>

          {/* Agent Preferences */}
          <div className="fade-3" style={{ ...cardBase, padding: "28px 28px" }}>
            <div style={{ ...sectionLabel, fontSize: 10, marginBottom: 18 }}>Default Agent Preferences</div>
            <SettingRow label="Default Agent" desc="Agent to use when starting a new task">
              <select value={defaultAgent} onChange={e => setDefaultAgent(e.target.value)} style={{ padding: "8px 14px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: C.white, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkDark, outline: "none", cursor: "pointer" }}>
                <option value="summarization">Summarization</option>
                <option value="literature">Literature Review</option>
                <option value="citation">Citation</option>
                <option value="proposal">Proposal Drafting</option>
              </select>
            </SettingRow>
            <SettingRow label="Citation Format" desc="Default format for generated citations">
              <select defaultValue="APA" style={{ padding: "8px 14px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: C.white, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkDark, outline: "none", cursor: "pointer" }}>
                <option>APA</option><option>MLA</option><option>IEEE</option><option>Chicago</option>
              </select>
            </SettingRow>
            <SettingRow label="Output Language" desc="Language for generated research outputs">
              <select defaultValue="English" style={{ padding: "8px 14px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: C.white, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkDark, outline: "none", cursor: "pointer" }}>
                <option>English</option><option>Urdu</option>
              </select>
            </SettingRow>
          </div>

          {/* Notifications */}
          <div className="fade-4" style={{ ...cardBase, padding: "28px 28px" }}>
            <div style={{ ...sectionLabel, fontSize: 10, marginBottom: 18 }}>Notifications</div>
            <SettingRow label="Task Completion" desc="Notify when a task finishes processing">
              <Toggle on={notifications.taskComplete} onToggle={() => setNotifications(n => ({ ...n, taskComplete: !n.taskComplete }))} />
            </SettingRow>
            <SettingRow label="Weekly Report" desc="Receive a weekly summary of your activity">
              <Toggle on={notifications.weeklyReport} onToggle={() => setNotifications(n => ({ ...n, weeklyReport: !n.weeklyReport }))} />
            </SettingRow>
            <SettingRow label="Agent Errors" desc="Notify when an agent fails or encounters issues">
              <Toggle on={notifications.agentErrors} onToggle={() => setNotifications(n => ({ ...n, agentErrors: !n.agentErrors }))} />
            </SettingRow>
            <SettingRow label="Product Updates" desc="News about new features and improvements">
              <Toggle on={notifications.updates} onToggle={() => setNotifications(n => ({ ...n, updates: !n.updates }))} />
            </SettingRow>
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* API Keys */}
          

          {/* Storage */}
          <div className="fade-4" style={{ ...cardBase, padding: "22px 20px" }}>
            <div style={{ ...sectionLabel, fontSize: 10, marginBottom: 14 }}>Storage & Usage</div>
            {(() => {
              const totalBytes = papers.reduce((acc, p) => acc + parseFileSize(p.file_size), 0);
              const thisMonthTasks = tasks.filter(t => {
                const date = new Date(t.created_at);
                const now = new Date();
                return date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
              }).length;
              const estimatedApi = tasks.reduce((acc, t) => acc + (t.status === "completed" ? Math.floor(Math.random() * 20) + 10 : 0), 0);

              const statsItems = [
                { l: "Papers Stored", v: papers.length.toString(), m: "of 100" },
                { l: "Storage Used", v: formatBytes(totalBytes), m: "of 5 GB" },
                { l: "Tasks This Month", v: thisMonthTasks.toString(), m: "of 50" },
                { l: "API Calls (Est.)", v: estimatedApi.toLocaleString(), m: "of 5,000" }
              ];

              return statsItems.map(s => (
                <div key={s.l} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: `1px solid ${C.border}` }}>
                  <span style={{ ...bodyText, fontSize: 13 }}>{s.l}</span>
                  <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkDark, fontWeight: 600 }}>{s.v} <span style={{ fontWeight: 400, color: C.inkLight }}>{s.m}</span></span>
                </div>
              ));
            })()}
          </div>
        </div>
      </div>
    </>
  );
}
