// ============================================================
// GenResearch — Data Access Layer (Front-End)
// All Supabase queries go through this file
// ============================================================
import { supabase } from "./supabase";

// ── Types ────────────────────────────────────────────────────
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
}

export interface Task {
  id: string;
  user_id: string;
  title: string;
  agent_type: "summarization" | "literature_review" | "citation" | "proposal";
  paper_count: number;
  status: "pending" | "processing" | "completed" | "failed";
  quality_score: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface TaskResult {
  id: string;
  task_id: string;
  user_id: string;
  type: "summary" | "review" | "citation" | "proposal";
  title: string;
  content: string;
  score: number;
  created_at: string;
}

export interface Citation {
  id: string;
  user_id: string;
  paper_id: string | null;
  authors: string;
  year: string;
  title: string;
  source: string;
  doi: string | null;
  created_at: string;
}

export interface PlatformStats {
  total_users: number;
  total_papers: number;
  total_tasks_completed: number;
  active_tasks: number;
  total_citations: number;
}

// ── Auth Helpers ─────────────────────────────────────────────
export async function getCurrentUserId(): Promise<string | null> {
  const { data: { user } } = await supabase.auth.getUser();
  return user?.id ?? null;
}

export async function updateLastSeen() {
  await supabase.rpc("update_last_seen");
}

// ── Public Stats (no auth needed — Home page) ───────────────
export async function getPlatformStats() {
  const { data, error } = await supabase
    .from("platform_stats")
    .select("*")
    .single();
  if (error) return { total_users: 0, total_papers: 0, total_tasks_completed: 0, active_tasks: 0, total_citations: 0 } as PlatformStats;
  return data as PlatformStats;
}

// ── Profiles ─────────────────────────────────────────────────
export async function getProfile(userId: string) {
  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", userId)
    .single();
  return { data: data as Profile | null, error };
}

export async function updateProfile(userId: string, updates: Partial<Profile>) {
  const { data, error } = await supabase
    .from("profiles")
    .update(updates)
    .eq("id", userId)
    .select()
    .single();
  return { data: data as Profile | null, error };
}

// ── Papers ───────────────────────────────────────────────────
export async function getUserPapers(userId: string) {
  const { data, error } = await supabase
    .from("papers")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false });
  return { data: (data ?? []) as Paper[], error };
}

export async function createPaper(paper: Omit<Paper, "id" | "created_at" | "chunks" | "storage_path"> & { chunks?: number; storage_path?: string }) {
  const { data, error } = await supabase
    .from("papers")
    .insert(paper)
    .select()
    .single();
  return { data: data as Paper | null, error };
}

export async function updatePaper(paperId: string, updates: Partial<Paper>) {
  const { data, error } = await supabase
    .from("papers")
    .update(updates)
    .eq("id", paperId)
    .select()
    .single();
  return { data: data as Paper | null, error };
}

export async function deletePaper(paperId: string) {
  return supabase.from("papers").delete().eq("id", paperId);
}

// ── Tasks ────────────────────────────────────────────────────
export async function getUserTasks(userId: string) {
  const { data, error } = await supabase
    .from("tasks")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false });
  return { data: (data ?? []) as Task[], error };
}

export async function createTask(task: Omit<Task, "id" | "created_at" | "completed_at" | "quality_score">) {
  const { data, error } = await supabase
    .from("tasks")
    .insert(task)
    .select()
    .single();
  return { data: data as Task | null, error };
}

export async function updateTask(taskId: string, updates: Partial<Task>) {
  return supabase.from("tasks").update(updates).eq("id", taskId);
}

// ── Task Results ─────────────────────────────────────────────
export async function getUserResults(userId: string) {
  const { data, error } = await supabase
    .from("task_results")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false });
  return { data: (data ?? []) as TaskResult[], error };
}

export async function createTaskResult(result: Omit<TaskResult, "id" | "created_at">) {
  return supabase.from("task_results").insert(result).select().single();
}

// ── Citations ────────────────────────────────────────────────
export async function getUserCitations(userId: string) {
  const { data, error } = await supabase
    .from("citations")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false });
  return { data: (data ?? []) as Citation[], error };
}

export async function createCitation(citation: Omit<Citation, "id" | "created_at">) {
  return supabase.from("citations").insert(citation).select().single();
}

export async function deleteCitation(citationId: string) {
  return supabase.from("citations").delete().eq("id", citationId);
}

// ── Realtime Subscriptions ───────────────────────────────────
export function subscribeToPapers(userId: string, callback: (papers: Paper[]) => void) {
  // Initial fetch
  getUserPapers(userId).then(({ data }) => callback(data));

  // Listen for changes
  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`papers_realtime_${channelId}`)
    .on("postgres_changes", { event: "*", schema: "public", table: "papers", filter: `user_id=eq.${userId}` },
      () => { getUserPapers(userId).then(({ data }) => callback(data)); }
    )
    .subscribe();

  return () => { supabase.removeChannel(channel); };
}

export function subscribeToTasks(userId: string, callback: (tasks: Task[]) => void) {
  getUserTasks(userId).then(({ data }) => callback(data));

  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`tasks_realtime_${channelId}`)
    .on("postgres_changes", { event: "*", schema: "public", table: "tasks", filter: `user_id=eq.${userId}` },
      () => { getUserTasks(userId).then(({ data }) => callback(data)); }
    )
    .subscribe();

  return () => { supabase.removeChannel(channel); };
}

export function subscribeToResults(userId: string, callback: (results: TaskResult[]) => void) {
  getUserResults(userId).then(({ data }) => callback(data));

  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`results_realtime_${channelId}`)
    .on("postgres_changes", { event: "*", schema: "public", table: "task_results", filter: `user_id=eq.${userId}` },
      () => { getUserResults(userId).then(({ data }) => callback(data)); }
    )
    .subscribe();

  return () => { supabase.removeChannel(channel); };
}

export function subscribeToCitations(userId: string, callback: (citations: Citation[]) => void) {
  getUserCitations(userId).then(({ data }) => callback(data));

  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`citations_realtime_${channelId}`)
    .on("postgres_changes", { event: "*", schema: "public", table: "citations", filter: `user_id=eq.${userId}` },
      () => { getUserCitations(userId).then(({ data }) => callback(data)); }
    )
    .subscribe();

  return () => { supabase.removeChannel(channel); };
}

export function subscribeToPlatformStats(callback: (stats: PlatformStats) => void) {
  // Initial fetch
  getPlatformStats().then(callback);

  // Re-fetch when any tracked table changes
  const channelId = Math.random().toString(36).substring(2, 10);
  const channel = supabase
    .channel(`stats_realtime_${channelId}`)
    .on("postgres_changes", { event: "*", schema: "public", table: "profiles" },
      () => { getPlatformStats().then(callback); }
    )
    .on("postgres_changes", { event: "*", schema: "public", table: "papers" },
      () => { getPlatformStats().then(callback); }
    )
    .on("postgres_changes", { event: "*", schema: "public", table: "tasks" },
      () => { getPlatformStats().then(callback); }
    )
    .subscribe();

  return () => { supabase.removeChannel(channel); };
}
