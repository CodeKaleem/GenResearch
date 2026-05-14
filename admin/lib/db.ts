// ============================================================
// GenResearch — Data Access Layer (Admin Console)
// Admin-scoped queries — all rows, all tables
// ============================================================
import { supabase } from "./supabase";

// ── Re-export shared types ──────────────────────────────────
export interface Profile {
  id: string;
  full_name: string;
  email: string;
  institution: string;
  role: string;
  status: string;
  avatar_url: string | null;
  created_at: string;
  last_seen_at: string;
}

export interface Paper {
  id: string;
  user_id: string;
  title: string;
  authors: string;
  year: number | null;
  pages: number;
  file_size: string;
  file_name: string;
  tags: string[];
  collection: string;
  status: "indexed" | "processing" | "unread" | "failed";
  chunks: number;
  storage_path: string;
  created_at: string;
  profiles?: { full_name: string };
}

export interface Task {
  id: string;
  user_id: string;
  title: string;
  agent_type: string;
  paper_count: number;
  status: string;
  quality_score: number | null;
  created_at: string;
  completed_at: string | null;
  profiles?: { full_name: string };
}

export interface AgentLog {
  id: string;
  level: "info" | "warn" | "error" | "success";
  message: string;
  agent: string | null;
  user_id: string | null;
  created_at: string;
}

export interface SystemAlert {
  id: string;
  title: string;
  message: string;
  severity: "critical" | "warning" | "info";
  status: "active" | "acknowledged" | "resolved";
  agent: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  created_at: string;
}

export interface PlatformSetting {
  key: string;
  value: unknown;
  updated_by: string | null;
  updated_at: string;
}

export interface ApiCostLog {
  id: string;
  agent: string;
  model: string;
  tokens_used: number;
  cost_usd: number;
  user_id: string | null;
  created_at: string;
}

export interface PlatformStats {
  total_users: number;
  total_papers: number;
  total_tasks_completed: number;
  active_tasks: number;
  total_citations: number;
}

// ── Profiles (all users) ─────────────────────────────────────
export async function getAllProfiles() {
  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .order("created_at", { ascending: false });
  return { data: (data ?? []) as Profile[], error };
}

export async function getProfile(userId: string) {
  const { data, error } = await supabase.from("profiles").select("*").eq("id", userId).single();
  return { data: data as Profile | null, error };
}

export async function updateProfile(userId: string, updates: Partial<Profile>) {
  return supabase.from("profiles").update(updates).eq("id", userId).select().single();
}

export async function deleteProfile(userId: string) {
  return supabase.from("profiles").delete().eq("id", userId);
}

// ── Papers (all) ─────────────────────────────────────────────
export async function getAllPapers() {
  const { data, error } = await supabase
    .from("papers")
    .select("*, profiles(full_name)")
    .order("created_at", { ascending: false });
  return { data: (data ?? []) as Paper[], error };
}

export async function createPaper(paper: Partial<Paper>) {
  return supabase.from("papers").insert(paper).select().single();
}

export async function updatePaper(paperId: string, updates: Partial<Paper>) {
  return supabase.from("papers").update(updates).eq("id", paperId).select().single();
}

export async function deletePaper(paperId: string) {
  return supabase.from("papers").delete().eq("id", paperId);
}

// ── Tasks (all) ──────────────────────────────────────────────
export async function getAllTasks() {
  const { data, error } = await supabase
    .from("tasks")
    .select("*, profiles(full_name)")
    .order("created_at", { ascending: false });
  return { data: (data ?? []) as Task[], error };
}

// ── Agent Logs ───────────────────────────────────────────────
export async function getAgentLogs(limit = 100) {
  const { data, error } = await supabase
    .from("agent_logs")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(limit);
  return { data: (data ?? []) as AgentLog[], error };
}

export async function createAgentLog(log: Omit<AgentLog, "id" | "created_at">) {
  return supabase.from("agent_logs").insert(log).select().single();
}

export async function clearAgentLogs() {
  return supabase.from("agent_logs").delete().neq("id", "00000000-0000-0000-0000-000000000000");
}

// ── System Alerts ────────────────────────────────────────────
export async function getSystemAlerts() {
  const { data, error } = await supabase
    .from("system_alerts")
    .select("*")
    .order("created_at", { ascending: false });
  return { data: (data ?? []) as SystemAlert[], error };
}

export async function createSystemAlert(alert: Omit<SystemAlert, "id" | "created_at" | "resolved_at" | "resolved_by">) {
  return supabase.from("system_alerts").insert(alert).select().single();
}

export async function updateSystemAlert(alertId: string, updates: Partial<SystemAlert>) {
  return supabase.from("system_alerts").update(updates).eq("id", alertId).select().single();
}

export async function deleteSystemAlert(alertId: string) {
  return supabase.from("system_alerts").delete().eq("id", alertId);
}

// ── Platform Settings ────────────────────────────────────────
export async function getAllSettings() {
  const { data, error } = await supabase.from("platform_settings").select("*");
  if (error || !data) return {};
  const map: Record<string, unknown> = {};
  data.forEach((row: PlatformSetting) => { map[row.key] = row.value; });
  return map;
}

export async function updateSetting(key: string, value: unknown, updatedBy: string) {
  return supabase
    .from("platform_settings")
    .upsert({ key, value: JSON.stringify(value), updated_by: updatedBy, updated_at: new Date().toISOString() })
    .select()
    .single();
}

// ── API Cost Logs ────────────────────────────────────────────
export async function getApiCostLogs(limit = 100) {
  const { data, error } = await supabase
    .from("api_cost_logs")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(limit);
  return { data: (data ?? []) as ApiCostLog[], error };
}

export async function getAggregatedApiCosts() {
  const { data, error } = await supabase
    .from("api_cost_logs")
    .select("agent, cost_usd, tokens_used");
  
  if (error || !data) return [];
  
  const aggregation: Record<string, { agent: string; cost: number; tokens: number }> = {};
  data.forEach(log => {
    if (!aggregation[log.agent]) {
      aggregation[log.agent] = { agent: log.agent, cost: 0, tokens: 0 };
    }
    aggregation[log.agent].cost += Number(log.cost_usd);
    aggregation[log.agent].tokens += Number(log.tokens_used);
  });
  
  return Object.values(aggregation);
}

// ── Platform Stats ───────────────────────────────────────────
export async function getPlatformStats() {
  const { data, error } = await supabase.from("platform_stats").select("*").single();
  if (error) return { total_users: 0, total_papers: 0, total_tasks_completed: 0, active_tasks: 0, total_citations: 0 } as PlatformStats;
  return data as PlatformStats;
}

// ── Realtime Subscriptions ───────────────────────────────────
export function subscribeToProfiles(callback: (profiles: Profile[]) => void) {
  getAllProfiles().then(({ data }) => callback(data));
  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`admin_profiles_rt_${channelId}`)
    .on("postgres_changes", { event: "*", schema: "public", table: "profiles" },
      () => { getAllProfiles().then(({ data }) => callback(data)); }
    )
    .subscribe();
  return () => { supabase.removeChannel(channel); };
}

export function subscribeToPapers(callback: (papers: Paper[]) => void) {
  getAllPapers().then(({ data }) => callback(data));
  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`admin_papers_rt_${channelId}`)
    .on("postgres_changes", { event: "*", schema: "public", table: "papers" },
      () => { getAllPapers().then(({ data }) => callback(data)); }
    )
    .subscribe();
  return () => { supabase.removeChannel(channel); };
}

export function subscribeToAgentLogs(callback: (logs: AgentLog[]) => void) {
  getAgentLogs().then(({ data }) => callback(data));
  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`admin_logs_rt_${channelId}`)
    .on("postgres_changes", { event: "*", schema: "public", table: "agent_logs" },
      () => { getAgentLogs().then(({ data }) => callback(data)); }
    )
    .subscribe();
  return () => { supabase.removeChannel(channel); };
}

export function subscribeToSystemAlerts(callback: (alerts: SystemAlert[]) => void) {
  getSystemAlerts().then(({ data }) => callback(data));
  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`admin_alerts_rt_${channelId}`)
    .on("postgres_changes", { event: "*", schema: "public", table: "system_alerts" },
      () => { getSystemAlerts().then(({ data }) => callback(data)); }
    )
    .subscribe();
  return () => { supabase.removeChannel(channel); };
}

export function subscribeToSettings(callback: (settings: Record<string, unknown>) => void) {
  getAllSettings().then(callback);
  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`admin_settings_rt_${channelId}`)
    .on("postgres_changes", { event: "*", schema: "public", table: "platform_settings" },
      () => { getAllSettings().then(callback); }
    )
    .subscribe();
  return () => { supabase.removeChannel(channel); };
}

export function subscribeToPlatformStats(callback: (stats: PlatformStats) => void) {
  getPlatformStats().then(callback);
  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`admin_stats_rt_${channelId}`)
    .on("postgres_changes", { event: "*", schema: "public", table: "profiles" }, () => { getPlatformStats().then(callback); })
    .on("postgres_changes", { event: "*", schema: "public", table: "papers" }, () => { getPlatformStats().then(callback); })
    .on("postgres_changes", { event: "*", schema: "public", table: "tasks" }, () => { getPlatformStats().then(callback); })
    .subscribe();
  return () => { supabase.removeChannel(channel); };
}

export function subscribeToApiCosts(callback: (costs: any[]) => void) {
  getAggregatedApiCosts().then(callback);
  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`admin_costs_rt_${channelId}`)
    .on("postgres_changes", { event: "INSERT", schema: "public", table: "api_cost_logs" },
      () => { getAggregatedApiCosts().then(callback); }
    )
    .subscribe();
  return () => { supabase.removeChannel(channel); };
}

export function subscribeToApiCostLogs(callback: (logs: ApiCostLog[]) => void) {
  getApiCostLogs().then(({ data }) => callback(data));
  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`admin_cost_logs_rt_${channelId}`)
    .on("postgres_changes", { event: "INSERT", schema: "public", table: "api_cost_logs" },
      () => { getApiCostLogs().then(({ data }) => callback(data)); }
    )
    .subscribe();
  return () => { supabase.removeChannel(channel); };
}

export function subscribeToTasks(callback: (tasks: Task[]) => void) {
  getAllTasks().then(({ data }) => callback(data));
  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`admin_tasks_rt_${channelId}`)
    .on("postgres_changes", { event: "*", schema: "public", table: "tasks" },
      () => { getAllTasks().then(({ data }) => callback(data)); }
    )
    .subscribe();
  return () => { supabase.removeChannel(channel); };
}
