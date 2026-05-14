"use client";
import { useState, useEffect } from "react";
import { C, globalStyles } from "./shared";
import { subscribeToPlatformStats, subscribeToSystemAlerts, subscribeToAgentLogs, type PlatformStats, type SystemAlert, type AgentLog } from "../../lib/db";
import OverviewPage from "./OverviewPage";
import UsersPage from "./UsersPage";
import AgentsPage from "./AgentsPage";
import DocumentsPage from "./DocumentsPage";
import LogsPage from "./LogsPage";
import SettingsPage from "./SettingsPage";
import AlertsPage from "./AlertsPage";

// ═══════════════════════════════════════════════════════════════
//  SIDEBAR NAV ITEM
// ═══════════════════════════════════════════════════════════════
interface NavItem { icon: string; label: string; badge?: number; danger?: boolean; id: string; }
function SideItem({ icon, label, active, badge, danger, onClick }: NavItem & { active?: boolean; onClick: () => void; }) {
  const [hov, setHov] = useState(false);
  return (
    <button onClick={onClick} onMouseEnter={() => setHov(true)} onMouseLeave={() => setHov(false)}
      style={{ width: "100%", textAlign: "left", display: "flex", alignItems: "center", gap: 10, padding: "10px 14px", margin: "1px 0", background: active ? C.inkDark : hov ? C.goldFaint : "transparent", border: "none", borderRadius: 3, cursor: "pointer", transition: "all .2s" }}>
      <span style={{ fontSize: 14, flexShrink: 0, opacity: active ? 1 : 0.7 }}>{icon}</span>
      <span style={{ flex: 1, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13.5, fontWeight: active ? 600 : 400, color: active ? C.cream : hov ? C.gold : danger ? C.red : C.inkLight, letterSpacing: "0.02em" }}>{label}</span>
      {badge !== undefined && badge > 0 && (
        <span style={{ fontSize: 10, fontWeight: 700, background: active ? C.goldLight : danger ? C.red : C.gold, color: active ? C.inkDark : C.cream, borderRadius: 10, padding: "1px 7px", fontFamily: "'Crimson Pro', Georgia, serif" }}>{badge}</span>
      )}
    </button>
  );
}

import { supabase } from "../../lib/supabase";

// ═══════════════════════════════════════════════════════════════
//  MAIN ADMIN DASHBOARD
// ═══════════════════════════════════════════════════════════════
export default function AdminDashboard() {
  const [activeNav, setActiveNav] = useState("Overview");
  const [scrolled, setScrolled]   = useState(false);
  const [clock, setClock]         = useState("");
  const [user, setUser]           = useState<{ name: string } | null>(null);
  const [stats, setStats]         = useState<PlatformStats>({ total_users: 0, total_papers: 0, total_tasks_completed: 0, active_tasks: 0, total_citations: 0 });
  const [alerts, setAlerts]       = useState<SystemAlert[]>([]);
  const [logs, setLogs]           = useState<AgentLog[]>([]);

  useEffect(() => {
    let isMounted = true;
    const fetchUser = async () => {
      const { data: { user: sbUser } } = await supabase.auth.getUser();
      if (sbUser && isMounted) {
        setUser({ name: sbUser.user_metadata?.full_name || "Admin" });
      }
    };
    fetchUser();

    const unsubStats = subscribeToPlatformStats(setStats);
    const unsubAlerts = subscribeToSystemAlerts(setAlerts);
    const unsubLogs = subscribeToAgentLogs(setLogs);

    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll);
    return () => {
      isMounted = false;
      window.removeEventListener("scroll", onScroll);
      unsubStats();
      unsubAlerts();
      unsubLogs();
    };
  }, []);

  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    tick(); const id = setInterval(tick, 1000); return () => clearInterval(id);
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
  };

  const navItems: NavItem[] = [
    { id:"Overview",       icon:"⌂",  label:"Overview" },
    { id:"Users",          icon:"👥", label:"User Management",  badge: stats.total_users },
    { id:"Agents",         icon:"⚙",  label:"Agent Monitor" },
    { id:"Documents",      icon:"📄", label:"Documents & Index" },
    { id:"Logs",           icon:"📋", label:"System Logs",      badge: logs.length },
    { id:"Settings",       icon:"◌",  label:"Settings" },
    { id:"Alerts",         icon:"🔔", label:"Alerts",           badge: alerts.filter(a => a.status === "active").length, danger:true },
  ];

  const renderPage = () => {
    switch(activeNav) {
      case "Overview": return <OverviewPage />;
      case "Users": return <UsersPage />;
      case "Agents": return <AgentsPage />;
      case "Documents": return <DocumentsPage />;
      case "Logs": return <LogsPage />;
      case "Settings": return <SettingsPage />;
      case "Alerts": return <AlertsPage />;
      default: return <OverviewPage />;
    }
  };

  return (
    <>
      <style>{globalStyles}</style>

      {/* TOP NAVIGATION BAR */}
      <nav style={{ position: "fixed", top: 0, left: 0, right: 0, zIndex: 300, height: 60, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 28px", background: scrolled ? "rgba(245,240,232,0.98)" : "rgba(245,240,232,0.98)", backdropFilter: "blur(16px)", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 30, height: 30, position: "relative", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ width: 24, height: 24, border: `2px solid ${C.gold}`, transform: "rotate(45deg)", position: "absolute" }} />
            <span style={{ fontFamily: "'Playfair Display', serif", fontSize: 11, fontWeight: 700, color: C.gold, position: "relative", zIndex: 1 }}>G</span>
          </div>
          <div>
            <div style={{ fontFamily: "'Playfair Display', serif", fontSize: 15, fontWeight: 800, color: C.inkDark, lineHeight: 1 }}>GenResearch</div>
            <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 8.5, color: C.red, letterSpacing: "0.22em", textTransform: "uppercase", fontWeight: 600 }}>Admin Console</div>
          </div>
        </div>

        <div style={{ flex: 1, maxWidth: 340, margin: "0 32px", position: "relative" }}>
          <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: C.inkLight, fontSize: 13 }}>🔍</span>
          <input placeholder="Search users, logs, tasks…" style={{ width: "100%", padding: "8px 12px 8px 32px", border: `1.5px solid ${C.border}`, borderRadius: 3, background: C.white, fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkDark, outline: "none" }} />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 13, color: C.inkLight, background: C.creamDark, border: `1px solid ${C.border}`, borderRadius: 3, padding: "5px 12px" }}>{clock}</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, background: C.greenFaint, border: `1px solid ${C.green}33`, borderRadius: 20, padding: "5px 12px" }}>
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: C.green, animation: "adminPulse 2s ease infinite", display: "inline-block" }} />
            <span style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 11.5, color: C.green, fontWeight: 600 }}>Operational</span>
          </div>
          <div style={{ position: "relative", cursor: "pointer", padding: 4 }} onClick={() => setActiveNav("Alerts")}>
            <span style={{ fontSize: 16, color: C.inkLight }}>🔔</span>
            <div style={{ position: "absolute", top: 1, right: 1, width: 7, height: 7, borderRadius: "50%", background: C.red, animation: "adminPulse 2s ease infinite" }} />
          </div>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: C.inkDark, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Playfair Display', serif", fontSize: 12, fontWeight: 700, color: C.cream, cursor: "pointer" }}>{user?.name.charAt(0) || "A"}</div>
        </div>
      </nav>

      {/* SIDEBAR */}
      <aside style={{ position: "fixed", top: 60, left: 0, bottom: 0, width: 216, background: C.creamLight, borderRight: `1px solid ${C.border}`, overflowY: "auto", zIndex: 200, padding: "18px 10px", display: "flex", flexDirection: "column" }}>
        <div style={{ fontFamily: "'Crimson Pro', Georgia, serif", fontSize: 9.5, fontWeight: 600, color: C.gold, letterSpacing: "0.18em", textTransform: "uppercase", padding: "0 6px", marginBottom: 8 }}>Admin Panel</div>
        {navItems.map(item => (
          <SideItem key={item.id} {...item} active={activeNav === item.id} onClick={() => setActiveNav(item.id)} />
        ))}
        <div style={{ marginTop: "auto", padding: "0 4px" }}>
          <button className="btn-ghost" style={{ width: "100%", textAlign: "left", padding: "10px 14px", border: "none", color: C.red }} onClick={handleSignOut}>Sign Out</button>
        </div>
      </aside>


      {/* MAIN CONTENT */}
      <main style={{ marginLeft: 216, marginTop: 60, minHeight: "calc(100vh - 60px)", padding: "32px 36px 60px", background: C.cream }}>
        {renderPage()}
      </main>
    </>
  );
}
