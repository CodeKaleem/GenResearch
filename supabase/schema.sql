-- ============================================================
-- GenResearch — Unified Database Schema
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- ============================================================

-- ── Helper: check if user is admin ──────────────────────────
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid() AND role = 'admin'
  );
$$;

-- ============================================================
-- 1. PROFILES
-- ============================================================
CREATE TABLE IF NOT EXISTS public.profiles (
  id          uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name   text NOT NULL DEFAULT '',
  email       text NOT NULL DEFAULT '',
  institution text NOT NULL DEFAULT '',
  role        text NOT NULL DEFAULT 'student' CHECK (role IN ('admin', 'student', 'viewer')),
  status      text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
  avatar_url  text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Students: read & update own row
CREATE POLICY "profiles_select_own" ON public.profiles
  FOR SELECT USING (id = auth.uid() OR public.is_admin());

CREATE POLICY "profiles_update_own" ON public.profiles
  FOR UPDATE USING (id = auth.uid() OR public.is_admin());

-- Admins: full insert/delete
CREATE POLICY "profiles_admin_insert" ON public.profiles
  FOR INSERT WITH CHECK (public.is_admin() OR id = auth.uid());

CREATE POLICY "profiles_admin_delete" ON public.profiles
  FOR DELETE USING (public.is_admin());

-- ============================================================
-- 2. PAPERS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.papers (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  title        text NOT NULL,
  authors      text NOT NULL DEFAULT '',
  year         int,
  pages        int DEFAULT 0,
  file_size    text DEFAULT '',
  file_name    text DEFAULT '',
  tags         text[] DEFAULT '{}',
  collection   text DEFAULT '',
  status       text NOT NULL DEFAULT 'unread' CHECK (status IN ('indexed', 'processing', 'unread', 'failed')),
  chunks       int DEFAULT 0,           -- reserved for future ChromaDB integration
  storage_path text DEFAULT '',          -- Supabase Storage / future file path
  created_at   timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.papers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "papers_select" ON public.papers
  FOR SELECT USING (user_id = auth.uid() OR public.is_admin());

CREATE POLICY "papers_insert" ON public.papers
  FOR INSERT WITH CHECK (user_id = auth.uid() OR public.is_admin());

CREATE POLICY "papers_update" ON public.papers
  FOR UPDATE USING (user_id = auth.uid() OR public.is_admin());

CREATE POLICY "papers_delete" ON public.papers
  FOR DELETE USING (user_id = auth.uid() OR public.is_admin());

CREATE INDEX IF NOT EXISTS idx_papers_user_id ON public.papers(user_id);
CREATE INDEX IF NOT EXISTS idx_papers_status ON public.papers(status);
CREATE INDEX IF NOT EXISTS idx_papers_collection ON public.papers(collection);

-- ============================================================
-- 3. TASKS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.tasks (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  title         text NOT NULL,
  agent_type    text NOT NULL CHECK (agent_type IN ('summarization', 'literature_review', 'citation', 'proposal')),
  paper_count   int DEFAULT 0,
  status        text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  quality_score int CHECK (quality_score >= 0 AND quality_score <= 100),
  created_at    timestamptz NOT NULL DEFAULT now(),
  completed_at  timestamptz
);

ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tasks_select" ON public.tasks
  FOR SELECT USING (user_id = auth.uid() OR public.is_admin());

CREATE POLICY "tasks_insert" ON public.tasks
  FOR INSERT WITH CHECK (user_id = auth.uid() OR public.is_admin());

CREATE POLICY "tasks_update" ON public.tasks
  FOR UPDATE USING (user_id = auth.uid() OR public.is_admin());

CREATE POLICY "tasks_delete" ON public.tasks
  FOR DELETE USING (user_id = auth.uid() OR public.is_admin());

CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON public.tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON public.tasks(status);

-- ============================================================
-- 4. TASK_RESULTS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.task_results (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id    uuid NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
  user_id    uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  type       text NOT NULL CHECK (type IN ('summary', 'review', 'citation', 'proposal')),
  title      text NOT NULL DEFAULT '',
  content    text NOT NULL DEFAULT '',
  score      int DEFAULT 0 CHECK (score >= 0 AND score <= 100),
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.task_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "task_results_select" ON public.task_results
  FOR SELECT USING (user_id = auth.uid() OR public.is_admin());

CREATE POLICY "task_results_insert" ON public.task_results
  FOR INSERT WITH CHECK (user_id = auth.uid() OR public.is_admin());

CREATE INDEX IF NOT EXISTS idx_task_results_user_id ON public.task_results(user_id);
CREATE INDEX IF NOT EXISTS idx_task_results_task_id ON public.task_results(task_id);

-- ============================================================
-- 5. CITATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.citations (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  paper_id   uuid REFERENCES public.papers(id) ON DELETE SET NULL,
  authors    text NOT NULL DEFAULT '',
  year       text NOT NULL DEFAULT '',
  title      text NOT NULL DEFAULT '',
  source     text NOT NULL DEFAULT '',
  doi        text,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.citations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "citations_select" ON public.citations
  FOR SELECT USING (user_id = auth.uid() OR public.is_admin());

CREATE POLICY "citations_insert" ON public.citations
  FOR INSERT WITH CHECK (user_id = auth.uid() OR public.is_admin());

CREATE POLICY "citations_delete" ON public.citations
  FOR DELETE USING (user_id = auth.uid() OR public.is_admin());

CREATE INDEX IF NOT EXISTS idx_citations_user_id ON public.citations(user_id);

-- ============================================================
-- 6. AGENT_LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.agent_logs (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  level      text NOT NULL DEFAULT 'info' CHECK (level IN ('info', 'warn', 'error', 'success')),
  message    text NOT NULL,
  agent      text,
  user_id    uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.agent_logs ENABLE ROW LEVEL SECURITY;

-- Only admins can read/write logs
CREATE POLICY "agent_logs_admin_select" ON public.agent_logs
  FOR SELECT USING (public.is_admin());

CREATE POLICY "agent_logs_admin_insert" ON public.agent_logs
  FOR INSERT WITH CHECK (public.is_admin());

CREATE POLICY "agent_logs_admin_delete" ON public.agent_logs
  FOR DELETE USING (public.is_admin());

CREATE INDEX IF NOT EXISTS idx_agent_logs_level ON public.agent_logs(level);
CREATE INDEX IF NOT EXISTS idx_agent_logs_created_at ON public.agent_logs(created_at DESC);

-- ============================================================
-- 7. SYSTEM_ALERTS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.system_alerts (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title       text NOT NULL,
  message     text NOT NULL DEFAULT '',
  severity    text NOT NULL DEFAULT 'info' CHECK (severity IN ('critical', 'warning', 'info')),
  status      text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'acknowledged', 'resolved')),
  agent       text,
  resolved_at timestamptz,
  resolved_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.system_alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "system_alerts_admin_select" ON public.system_alerts
  FOR SELECT USING (public.is_admin());

CREATE POLICY "system_alerts_admin_insert" ON public.system_alerts
  FOR INSERT WITH CHECK (public.is_admin());

CREATE POLICY "system_alerts_admin_update" ON public.system_alerts
  FOR UPDATE USING (public.is_admin());

CREATE POLICY "system_alerts_admin_delete" ON public.system_alerts
  FOR DELETE USING (public.is_admin());

-- ============================================================
-- 8. PLATFORM_SETTINGS
-- ============================================================
CREATE TABLE IF NOT EXISTS public.platform_settings (
  key        text PRIMARY KEY,
  value      jsonb NOT NULL DEFAULT '{}',
  updated_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.platform_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "platform_settings_admin_select" ON public.platform_settings
  FOR SELECT USING (public.is_admin());

CREATE POLICY "platform_settings_admin_insert" ON public.platform_settings
  FOR INSERT WITH CHECK (public.is_admin());

CREATE POLICY "platform_settings_admin_update" ON public.platform_settings
  FOR UPDATE USING (public.is_admin());

-- ============================================================
-- 9. API_COST_LOGS (reserved for future FastAPI integration)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.api_cost_logs (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  agent       text NOT NULL,
  model       text NOT NULL DEFAULT '',
  tokens_used int NOT NULL DEFAULT 0,
  cost_usd    numeric(10,4) NOT NULL DEFAULT 0,
  user_id     uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.api_cost_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "api_cost_logs_admin_select" ON public.api_cost_logs
  FOR SELECT USING (public.is_admin());

CREATE POLICY "api_cost_logs_admin_insert" ON public.api_cost_logs
  FOR INSERT WITH CHECK (public.is_admin());

CREATE INDEX IF NOT EXISTS idx_api_cost_logs_created_at ON public.api_cost_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_cost_logs_agent ON public.api_cost_logs(agent);

-- ============================================================
-- PUBLIC STATS VIEW (for Home page — no auth required)
-- ============================================================
CREATE OR REPLACE VIEW public.platform_stats AS
SELECT
  (SELECT count(*) FROM public.profiles WHERE status = 'active') AS total_users,
  (SELECT count(*) FROM public.papers) AS total_papers,
  (SELECT count(*) FROM public.tasks WHERE status = 'completed') AS total_tasks_completed,
  (SELECT count(*) FROM public.tasks WHERE status = 'processing') AS active_tasks,
  (SELECT count(*) FROM public.citations) AS total_citations;

-- Grant anonymous access to the stats view (public landing page)
GRANT SELECT ON public.platform_stats TO anon;
GRANT SELECT ON public.platform_stats TO authenticated;

-- ============================================================
-- AUTO-CREATE PROFILE ON SIGNUP (trigger)
-- ============================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, email, institution, role, status)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data ->> 'full_name', ''),
    COALESCE(NEW.email, ''),
    COALESCE(NEW.raw_user_meta_data ->> 'institution', ''),
    COALESCE(NEW.raw_user_meta_data ->> 'role', 'student'),
    'active'
  );
  RETURN NEW;
END;
$$;

-- Drop existing trigger if any, then create
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- UPDATE last_seen_at on login
-- ============================================================
CREATE OR REPLACE FUNCTION public.update_last_seen()
RETURNS void
LANGUAGE sql
SECURITY DEFINER
AS $$
  UPDATE public.profiles
  SET last_seen_at = now()
  WHERE id = auth.uid();
$$;

-- ============================================================
-- DEFAULT PLATFORM SETTINGS (insert once)
-- ============================================================
INSERT INTO public.platform_settings (key, value) VALUES
  ('platform_name', '"GenResearch"'),
  ('admin_email', '"admin@comsats.edu.pk"'),
  ('timezone', '"Asia/Karachi"'),
  ('default_model', '"gpt-3.5-turbo"'),
  ('temperature', '0.7'),
  ('max_tokens', '2048'),
  ('stream_enabled', 'true'),
  ('daily_budget', '10'),
  ('monthly_budget', '150'),
  ('chunk_size', '512'),
  ('chunk_overlap', '64'),
  ('top_k', '5'),
  ('embedding_model', '"text-embedding-ada-002"'),
  ('maintenance_mode', 'false'),
  ('auto_backup', 'true'),
  ('email_alerts', 'true'),
  ('agent_fail_alert', 'true'),
  ('cost_alert', 'true'),
  ('new_user_alert', 'false'),
  ('daily_digest', 'true'),
  ('mfa_required', 'false'),
  ('session_timeout', '60'),
  ('ip_whitelist', 'false')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- ENABLE REALTIME for key tables
-- ============================================================
ALTER PUBLICATION supabase_realtime ADD TABLE public.profiles;
ALTER PUBLICATION supabase_realtime ADD TABLE public.papers;
ALTER PUBLICATION supabase_realtime ADD TABLE public.tasks;
ALTER PUBLICATION supabase_realtime ADD TABLE public.task_results;
ALTER PUBLICATION supabase_realtime ADD TABLE public.agent_logs;
ALTER PUBLICATION supabase_realtime ADD TABLE public.system_alerts;
ALTER PUBLICATION supabase_realtime ADD TABLE public.platform_settings;
