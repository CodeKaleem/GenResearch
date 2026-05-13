"use client";

import { useState, useEffect } from "react";
import { supabase } from "../../lib/supabase";
import { C, sectionLabel, headingStyle, bodyText, cardBase } from "./theme";

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
  const [user, setUser] = useState<{ name: string; email: string; institution: string } | null>(null);

  useEffect(() => {
    const fetchUser = async () => {
      const { data: { user: sbUser } } = await supabase.auth.getUser();
      if (sbUser) {
        setUser({
          name: sbUser.user_metadata?.full_name || "Researcher",
          email: sbUser.email || "",
          institution: sbUser.user_metadata?.institution || "GenResearch",
        });
      }
    };
    fetchUser();
  }, []);

  return (
    <>
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
              <div style={{ width: 64, height: 64, borderRadius: "50%", background: C.inkDark, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Playfair Display', serif", fontSize: 24, fontWeight: 700, color: C.cream, flexShrink: 0 }}>{user?.name.charAt(0) || "U"}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 18, fontWeight: 700, color: C.inkDark }}>{user?.name || "Loading..."}</div>
                <div style={{ ...bodyText, fontSize: 13, marginTop: 2 }}>{user?.email}</div>
                <div style={{ ...bodyText, fontSize: 12, marginTop: 2 }}>{user?.institution}</div>
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {[{ l: "Full Name", v: user?.name }, { l: "Email", v: user?.email }, { l: "Institution", v: user?.institution }].map(f => (
                <div key={f.l}>
                  <label style={{ ...sectionLabel, fontSize: 10, display: "block", marginBottom: 6 }}>{f.l}</label>
                  <input key={f.v} defaultValue={f.v} style={{ width: "100%", padding: "9px 12px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: C.white, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkDark, outline: "none" }} onFocus={e => (e.target.style.borderColor = C.gold)} onBlur={e => (e.target.style.borderColor = C.border)} />
                </div>
              ))}
            </div>
            <button className="btn-ink" style={{ marginTop: 20, padding: "9px 24px", fontSize: 11.5 }} onClick={() => alert("Profile saved successfully!")}>Save Changes</button>
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
          <div className="fade-3" style={{ ...cardBase, padding: "22px 20px" }}>
            <div style={{ ...sectionLabel, fontSize: 10, marginBottom: 16 }}>API Configuration</div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ ...sectionLabel, fontSize: 10, display: "block", marginBottom: 6 }}>OpenAI API Key</label>
              <input defaultValue="sk-••••••••••••••••••••3xYz" type="password" style={{ width: "100%", padding: "9px 12px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: C.white, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkDark, outline: "none" }} />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ ...sectionLabel, fontSize: 10, display: "block", marginBottom: 6 }}>CrossRef Email</label>
              <input defaultValue={user?.email || ""} style={{ width: "100%", padding: "9px 12px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: C.white, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkDark, outline: "none" }} />
            </div>
            <button className="btn-outline" style={{ width: "100%", padding: "8px 0", fontSize: 11.5 }} onClick={() => alert("API keys updated!")}>Update Keys</button>
          </div>

          {/* Storage */}
          <div className="fade-4" style={{ ...cardBase, padding: "22px 20px" }}>
            <div style={{ ...sectionLabel, fontSize: 10, marginBottom: 14 }}>Storage & Usage</div>
            {[{ l: "Papers Stored", v: "12", m: "of 100" }, { l: "Storage Used", v: "1.2 GB", m: "of 5 GB" }, { l: "Tasks This Month", v: "8", m: "of 50" }, { l: "API Calls", v: "124", m: "of 1,000" }].map(s => (
              <div key={s.l} style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: `1px solid ${C.border}` }}>
                <span style={{ ...bodyText, fontSize: 13 }}>{s.l}</span>
                <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkDark, fontWeight: 600 }}>{s.v} <span style={{ fontWeight: 400, color: C.inkLight }}>{s.m}</span></span>
              </div>
            ))}
          </div>

          {/* Danger zone */}
          <div className="fade-5" style={{ ...cardBase, padding: "22px 20px", borderColor: `${C.sienna}33` }}>
            <div style={{ ...sectionLabel, fontSize: 10, marginBottom: 12, color: C.sienna }}>Danger Zone</div>
            <p style={{ ...bodyText, fontSize: 12.5, marginBottom: 14 }}>Permanently delete your account and all associated data. This action cannot be undone.</p>
            <button style={{ width: "100%", padding: "9px 0", borderRadius: 3, border: `1.5px solid ${C.sienna}55`, background: "transparent", fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 12, fontWeight: 600, color: C.sienna, cursor: "pointer", letterSpacing: "0.08em", textTransform: "uppercase", transition: "all .2s" }}
              onMouseEnter={e => { e.currentTarget.style.background = `${C.sienna}12`; }}
              onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}
            >Delete Account</button>
          </div>
        </div>
      </div>
    </>
  );
}
