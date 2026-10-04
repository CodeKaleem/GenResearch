-- ============================================================================
-- GenResearch: idempotent Supabase setup for the user app, admin console,
-- FastAPI backend, agent/task tracking, proposal reports, audit and usage data.
--
-- Run in Supabase Dashboard -> SQL Editor as the project owner/postgres.
-- Safe to re-run: tables/columns/indexes/functions are guarded, default rows use
-- ON CONFLICT DO NOTHING, and this script replaces only its named RLS policies
-- and triggers. Existing user data is not truncated or overwritten.
--
-- IMPORTANT:
--   * Frontend clients must use the Supabase publishable/anon key, never the
--     service-role key. Keep SUPABASE_SERVICE_KEY only on the FastAPI server.
--   * This provisions DB schema/access/realtime, not external API secrets,
--     ChromaDB, or the backend's local PDF file storage.
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. Core account and application tables
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name text NOT NULL DEFAULT '',
    email text NOT NULL DEFAULT '',
    institution text NOT NULL DEFAULT '',
    role text NOT NULL DEFAULT 'student' CHECK (role IN ('admin', 'student', 'viewer')),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended')),
    avatar_url text,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS full_name text NOT NULL DEFAULT '';
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS email text NOT NULL DEFAULT '';
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS institution text NOT NULL DEFAULT '';
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'student';
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS avatar_url text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS last_seen_at timestamptz NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.user_preferences (
    user_id uuid PRIMARY KEY REFERENCES public.profiles(id) ON DELETE CASCADE,
    preferences jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.user_preferences ADD COLUMN IF NOT EXISTS preferences jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE public.user_preferences ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.papers (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES public.profiles(id) ON DELETE CASCADE,
    title text NOT NULL,
    authors text NOT NULL DEFAULT '',
    year integer,
    pages integer NOT NULL DEFAULT 0,
    file_size text NOT NULL DEFAULT '',
    file_name text NOT NULL DEFAULT '',
    tags text[] NOT NULL DEFAULT '{}',
    collection text NOT NULL DEFAULT '',
    status text NOT NULL DEFAULT 'unread' CHECK (status IN ('indexed', 'processing', 'unread', 'failed')),
    chunks integer NOT NULL DEFAULT 0,
    storage_path text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS user_id uuid DEFAULT auth.uid();
ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS title text NOT NULL DEFAULT '';
ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS authors text NOT NULL DEFAULT '';
ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS year integer;
ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS pages integer NOT NULL DEFAULT 0;
ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS file_size text NOT NULL DEFAULT '';
ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS file_name text NOT NULL DEFAULT '';
ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS tags text[] NOT NULL DEFAULT '{}';
ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS collection text NOT NULL DEFAULT '';
ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'unread';
ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS chunks integer NOT NULL DEFAULT 0;
ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS storage_path text NOT NULL DEFAULT '';
ALTER TABLE public.papers ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.papers ALTER COLUMN user_id SET DEFAULT auth.uid();

CREATE TABLE IF NOT EXISTS public.tasks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES public.profiles(id) ON DELETE CASCADE,
    title text NOT NULL DEFAULT '',
    agent_type text NOT NULL CHECK (agent_type IN ('summarization', 'literature_review', 'citation', 'proposal')),
    paper_count integer NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    quality_score integer CHECK (quality_score BETWEEN 0 AND 100),
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz
);

ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS user_id uuid DEFAULT auth.uid();
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS title text NOT NULL DEFAULT '';
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS agent_type text NOT NULL DEFAULT 'proposal';
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS paper_count integer NOT NULL DEFAULT 0;
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'pending';
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS quality_score integer;
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.tasks ADD COLUMN IF NOT EXISTS completed_at timestamptz;
ALTER TABLE public.tasks ALTER COLUMN user_id SET DEFAULT auth.uid();

CREATE TABLE IF NOT EXISTS public.task_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id uuid NOT NULL REFERENCES public.tasks(id) ON DELETE CASCADE,
    user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES public.profiles(id) ON DELETE CASCADE,
    type text NOT NULL CHECK (type IN ('summary', 'review', 'citation', 'proposal')),
    title text NOT NULL DEFAULT '',
    content text NOT NULL DEFAULT '',
    score integer NOT NULL DEFAULT 0 CHECK (score BETWEEN 0 AND 100),
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.task_results ADD COLUMN IF NOT EXISTS task_id uuid;
ALTER TABLE public.task_results ADD COLUMN IF NOT EXISTS user_id uuid DEFAULT auth.uid();
ALTER TABLE public.task_results ADD COLUMN IF NOT EXISTS type text NOT NULL DEFAULT 'summary';
ALTER TABLE public.task_results ADD COLUMN IF NOT EXISTS title text NOT NULL DEFAULT '';
ALTER TABLE public.task_results ADD COLUMN IF NOT EXISTS content text NOT NULL DEFAULT '';
ALTER TABLE public.task_results ADD COLUMN IF NOT EXISTS score integer NOT NULL DEFAULT 0;
ALTER TABLE public.task_results ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.task_results ALTER COLUMN user_id SET DEFAULT auth.uid();

CREATE TABLE IF NOT EXISTS public.citations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL DEFAULT auth.uid() REFERENCES public.profiles(id) ON DELETE CASCADE,
    paper_id uuid REFERENCES public.papers(id) ON DELETE SET NULL,
    authors text NOT NULL DEFAULT '',
    year text NOT NULL DEFAULT '',
    title text NOT NULL DEFAULT '',
    source text NOT NULL DEFAULT '',
    doi text,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.citations ADD COLUMN IF NOT EXISTS user_id uuid DEFAULT auth.uid();
ALTER TABLE public.citations ADD COLUMN IF NOT EXISTS paper_id uuid;
ALTER TABLE public.citations ADD COLUMN IF NOT EXISTS authors text NOT NULL DEFAULT '';
ALTER TABLE public.citations ADD COLUMN IF NOT EXISTS year text NOT NULL DEFAULT '';
ALTER TABLE public.citations ADD COLUMN IF NOT EXISTS title text NOT NULL DEFAULT '';
ALTER TABLE public.citations ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT '';
ALTER TABLE public.citations ADD COLUMN IF NOT EXISTS doi text;
ALTER TABLE public.citations ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.citations ALTER COLUMN user_id SET DEFAULT auth.uid();

-- ---------------------------------------------------------------------------
-- 2. Reports, logs, alerts, settings, and usage/grounding audit data
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.research_reports (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL UNIQUE,
    user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    topic text NOT NULL,
    draft_text text,
    completion_guide text,
    outline jsonb,
    citation_registry jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.research_reports ADD COLUMN IF NOT EXISTS session_id uuid;
ALTER TABLE public.research_reports ADD COLUMN IF NOT EXISTS user_id uuid;
ALTER TABLE public.research_reports ADD COLUMN IF NOT EXISTS topic text NOT NULL DEFAULT 'Unknown';
ALTER TABLE public.research_reports ADD COLUMN IF NOT EXISTS draft_text text;
ALTER TABLE public.research_reports ADD COLUMN IF NOT EXISTS completion_guide text;
ALTER TABLE public.research_reports ADD COLUMN IF NOT EXISTS outline jsonb;
ALTER TABLE public.research_reports ADD COLUMN IF NOT EXISTS citation_registry jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE public.research_reports ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE public.research_reports ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
CREATE UNIQUE INDEX IF NOT EXISTS idx_research_reports_session_unique ON public.research_reports(session_id);
CREATE INDEX IF NOT EXISTS idx_research_reports_user_created ON public.research_reports(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.agent_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    level text NOT NULL DEFAULT 'info' CHECK (level IN ('info', 'warn', 'error', 'success')),
    message text NOT NULL,
    agent text,
    user_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    session_id uuid,
    node_name text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.agent_logs ADD COLUMN IF NOT EXISTS level text NOT NULL DEFAULT 'info';
ALTER TABLE public.agent_logs ADD COLUMN IF NOT EXISTS message text NOT NULL DEFAULT '';
ALTER TABLE public.agent_logs ADD COLUMN IF NOT EXISTS agent text;
ALTER TABLE public.agent_logs ADD COLUMN IF NOT EXISTS user_id uuid;
ALTER TABLE public.agent_logs ADD COLUMN IF NOT EXISTS session_id uuid;
ALTER TABLE public.agent_logs ADD COLUMN IF NOT EXISTS node_name text;
ALTER TABLE public.agent_logs ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE public.agent_logs ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.system_alerts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    message text NOT NULL DEFAULT '',
    severity text NOT NULL DEFAULT 'info' CHECK (severity IN ('critical', 'warning', 'info')),
    status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'acknowledged', 'resolved')),
    agent text,
    resolved_at timestamptz,
    resolved_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS title text NOT NULL DEFAULT '';
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS message text NOT NULL DEFAULT '';
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS severity text NOT NULL DEFAULT 'info';
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'active';
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS agent text;
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS resolved_at timestamptz;
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS resolved_by uuid;
ALTER TABLE public.system_alerts ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.platform_settings (
    key text PRIMARY KEY,
    value jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.platform_settings ADD COLUMN IF NOT EXISTS value jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE public.platform_settings ADD COLUMN IF NOT EXISTS updated_by uuid;
ALTER TABLE public.platform_settings ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.api_cost_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    agent text NOT NULL,
    model text NOT NULL DEFAULT '',
    tokens_used integer NOT NULL DEFAULT 0,
    cost_usd numeric(12, 6) NOT NULL DEFAULT 0,
    user_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
    session_id uuid,
    tokens_in integer NOT NULL DEFAULT 0,
    tokens_out integer NOT NULL DEFAULT 0,
    request_id text,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.api_cost_logs ADD COLUMN IF NOT EXISTS agent text NOT NULL DEFAULT 'unknown';
ALTER TABLE public.api_cost_logs ADD COLUMN IF NOT EXISTS model text NOT NULL DEFAULT '';
ALTER TABLE public.api_cost_logs ADD COLUMN IF NOT EXISTS tokens_used integer NOT NULL DEFAULT 0;
ALTER TABLE public.api_cost_logs ADD COLUMN IF NOT EXISTS cost_usd numeric(12, 6) NOT NULL DEFAULT 0;
ALTER TABLE public.api_cost_logs ADD COLUMN IF NOT EXISTS user_id uuid;
ALTER TABLE public.api_cost_logs ADD COLUMN IF NOT EXISTS session_id uuid;
ALTER TABLE public.api_cost_logs ADD COLUMN IF NOT EXISTS tokens_in integer NOT NULL DEFAULT 0;
ALTER TABLE public.api_cost_logs ADD COLUMN IF NOT EXISTS tokens_out integer NOT NULL DEFAULT 0;
ALTER TABLE public.api_cost_logs ADD COLUMN IF NOT EXISTS request_id text;
ALTER TABLE public.api_cost_logs ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.generated_claims (
    claim_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL,
    section text NOT NULL,
    claim_text text NOT NULL,
    cited_chunk_ids text[] NOT NULL DEFAULT '{}',
    verdict text NOT NULL CHECK (verdict IN ('supported', 'unsupported', 'partial')),
    discrepancy text,
    corrected_text text,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.generated_claims ADD COLUMN IF NOT EXISTS session_id uuid;
ALTER TABLE public.generated_claims ADD COLUMN IF NOT EXISTS section text NOT NULL DEFAULT '';
ALTER TABLE public.generated_claims ADD COLUMN IF NOT EXISTS claim_text text NOT NULL DEFAULT '';
ALTER TABLE public.generated_claims ADD COLUMN IF NOT EXISTS cited_chunk_ids text[] NOT NULL DEFAULT '{}';
ALTER TABLE public.generated_claims ADD COLUMN IF NOT EXISTS verdict text NOT NULL DEFAULT 'unsupported';
ALTER TABLE public.generated_claims ADD COLUMN IF NOT EXISTS discrepancy text;
ALTER TABLE public.generated_claims ADD COLUMN IF NOT EXISTS corrected_text text;
ALTER TABLE public.generated_claims ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS public.audit_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid,
    node_name text NOT NULL,
    model_used text,
    prompt_hash text,
    tokens_in integer NOT NULL DEFAULT 0,
    tokens_out integer NOT NULL DEFAULT 0,
    latency_ms integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.audit_log ADD COLUMN IF NOT EXISTS session_id uuid;
ALTER TABLE public.audit_log ADD COLUMN IF NOT EXISTS node_name text NOT NULL DEFAULT 'unknown';
ALTER TABLE public.audit_log ADD COLUMN IF NOT EXISTS model_used text;
ALTER TABLE public.audit_log ADD COLUMN IF NOT EXISTS prompt_hash text;
ALTER TABLE public.audit_log ADD COLUMN IF NOT EXISTS tokens_in integer NOT NULL DEFAULT 0;
ALTER TABLE public.audit_log ADD COLUMN IF NOT EXISTS tokens_out integer NOT NULL DEFAULT 0;
ALTER TABLE public.audit_log ADD COLUMN IF NOT EXISTS latency_ms integer NOT NULL DEFAULT 0;
ALTER TABLE public.audit_log ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now();

-- Add missing foreign-key relationships to pre-existing installations without
-- blocking deployment on historical orphan rows. New writes are still checked.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'papers_user_id_fkey' AND conrelid = 'public.papers'::regclass) THEN
        ALTER TABLE public.papers ADD CONSTRAINT papers_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tasks_user_id_fkey' AND conrelid = 'public.tasks'::regclass) THEN
        ALTER TABLE public.tasks ADD CONSTRAINT tasks_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'task_results_task_id_fkey' AND conrelid = 'public.task_results'::regclass) THEN
        ALTER TABLE public.task_results ADD CONSTRAINT task_results_task_id_fkey
            FOREIGN KEY (task_id) REFERENCES public.tasks(id) ON DELETE CASCADE NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'task_results_user_id_fkey' AND conrelid = 'public.task_results'::regclass) THEN
        ALTER TABLE public.task_results ADD CONSTRAINT task_results_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'citations_user_id_fkey' AND conrelid = 'public.citations'::regclass) THEN
        ALTER TABLE public.citations ADD CONSTRAINT citations_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'citations_paper_id_fkey' AND conrelid = 'public.citations'::regclass) THEN
        ALTER TABLE public.citations ADD CONSTRAINT citations_paper_id_fkey
            FOREIGN KEY (paper_id) REFERENCES public.papers(id) ON DELETE SET NULL NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'research_reports_user_id_fkey' AND conrelid = 'public.research_reports'::regclass) THEN
        ALTER TABLE public.research_reports ADD CONSTRAINT research_reports_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'agent_logs_user_id_fkey' AND conrelid = 'public.agent_logs'::regclass) THEN
        ALTER TABLE public.agent_logs ADD CONSTRAINT agent_logs_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE SET NULL NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'system_alerts_resolved_by_fkey' AND conrelid = 'public.system_alerts'::regclass) THEN
        ALTER TABLE public.system_alerts ADD CONSTRAINT system_alerts_resolved_by_fkey
            FOREIGN KEY (resolved_by) REFERENCES public.profiles(id) ON DELETE SET NULL NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'platform_settings_updated_by_fkey' AND conrelid = 'public.platform_settings'::regclass) THEN
        ALTER TABLE public.platform_settings ADD CONSTRAINT platform_settings_updated_by_fkey
            FOREIGN KEY (updated_by) REFERENCES public.profiles(id) ON DELETE SET NULL NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'api_cost_logs_user_id_fkey' AND conrelid = 'public.api_cost_logs'::regclass) THEN
        ALTER TABLE public.api_cost_logs ADD CONSTRAINT api_cost_logs_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE SET NULL NOT VALID;
    END IF;
END
$$;

-- ---------------------------------------------------------------------------
-- 3. Indexes used by frontend filters, admin joins, and backend lookups
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_user_preferences_updated_at ON public.user_preferences(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_papers_user_id ON public.papers(user_id);
CREATE INDEX IF NOT EXISTS idx_papers_status ON public.papers(status);
CREATE INDEX IF NOT EXISTS idx_papers_collection ON public.papers(collection);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON public.tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON public.tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent_created ON public.tasks(agent_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_task_results_user_id ON public.task_results(user_id);
CREATE INDEX IF NOT EXISTS idx_task_results_task_id ON public.task_results(task_id);
CREATE INDEX IF NOT EXISTS idx_citations_user_id ON public.citations(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_level ON public.agent_logs(level);
CREATE INDEX IF NOT EXISTS idx_agent_logs_created_at ON public.agent_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_logs_user_created ON public.agent_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_alerts_created_at ON public.system_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_cost_logs_created_at ON public.api_cost_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_cost_logs_agent ON public.api_cost_logs(agent);
CREATE INDEX IF NOT EXISTS idx_api_cost_logs_session ON public.api_cost_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_api_cost_logs_user_created ON public.api_cost_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_claims_session ON public.generated_claims(session_id);
CREATE INDEX IF NOT EXISTS idx_generated_claims_verdict ON public.generated_claims(verdict);
CREATE INDEX IF NOT EXISTS idx_audit_log_session ON public.audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON public.audit_log(created_at DESC);

-- ---------------------------------------------------------------------------
-- 4. Authorization helpers (SECURITY DEFINER avoids profiles RLS recursion)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.profiles AS p
        WHERE p.id = auth.uid()
          AND p.role = 'admin'
          AND p.status = 'active'
    );
$$;

CREATE OR REPLACE FUNCTION public.is_active_account()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.profiles AS p
        WHERE p.id = auth.uid()
          AND p.status = 'active'
    );
$$;

REVOKE ALL ON FUNCTION public.is_admin() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.is_active_account() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_admin() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.is_active_account() TO authenticated, service_role;

-- Prevent a normal user from promoting themselves, changing their account
-- status/email/identity, even though the profile editor uses UPDATE on row.
CREATE OR REPLACE FUNCTION public.protect_profile_privileges()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    IF auth.uid() IS NOT NULL AND NOT public.is_admin() THEN
        NEW.id := OLD.id;
        NEW.email := OLD.email;
        NEW.role := OLD.role;
        NEW.status := OLD.status;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_profiles_protect_privileges ON public.profiles;
CREATE TRIGGER trg_profiles_protect_privileges
BEFORE UPDATE ON public.profiles
FOR EACH ROW EXECUTE FUNCTION public.protect_profile_privileges();

-- ---------------------------------------------------------------------------
-- 5. Profile creation/backfill, account deletion, timestamps, and task status
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, email, institution, role, status)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data ->> 'full_name', ''),
        COALESCE(NEW.email, ''),
        COALESCE(NEW.raw_user_meta_data ->> 'institution', ''),
        'student', -- Never accept role from user-controlled signup metadata.
        'active'
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

INSERT INTO public.profiles (id, full_name, email, institution, role, status)
SELECT
    u.id,
    COALESCE(u.raw_user_meta_data ->> 'full_name', ''),
    COALESCE(u.email, ''),
    COALESCE(u.raw_user_meta_data ->> 'institution', ''),
    'student',
    'active'
FROM auth.users AS u
ON CONFLICT (id) DO NOTHING;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- The admin console's Delete User action deletes a profile row. Mirror that
-- deletion to Auth so the UI does not leave an orphaned login account.
CREATE OR REPLACE FUNCTION public.delete_auth_user_for_deleted_profile()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    DELETE FROM auth.users WHERE id = OLD.id;
    RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_profiles_delete_auth_user ON public.profiles;
CREATE TRIGGER trg_profiles_delete_auth_user
AFTER DELETE ON public.profiles
FOR EACH ROW EXECUTE FUNCTION public.delete_auth_user_for_deleted_profile();

CREATE OR REPLACE FUNCTION public.update_last_seen()
RETURNS void
LANGUAGE sql
SECURITY DEFINER
SET search_path = ''
AS $$
    UPDATE public.profiles SET last_seen_at = now() WHERE id = auth.uid();
$$;
REVOKE ALL ON FUNCTION public.update_last_seen() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.update_last_seen() TO authenticated;

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_research_reports_updated_at ON public.research_reports;
CREATE TRIGGER trg_research_reports_updated_at
BEFORE UPDATE ON public.research_reports
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_user_preferences_updated_at ON public.user_preferences;
CREATE TRIGGER trg_user_preferences_updated_at
BEFORE UPDATE ON public.user_preferences
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

CREATE OR REPLACE FUNCTION public.set_task_completion_timestamp()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    IF NEW.status IN ('completed', 'failed') THEN
        NEW.completed_at := COALESCE(NEW.completed_at, now());
    ELSE
        NEW.completed_at := NULL;
    END IF;
    RETURN NEW;
END;
$$;

UPDATE public.tasks
SET completed_at = COALESCE(completed_at, created_at, now())
WHERE status IN ('completed', 'failed') AND completed_at IS NULL;

DROP TRIGGER IF EXISTS trg_tasks_completion_timestamp ON public.tasks;
CREATE TRIGGER trg_tasks_completion_timestamp
BEFORE INSERT OR UPDATE OF status ON public.tasks
FOR EACH ROW EXECUTE FUNCTION public.set_task_completion_timestamp();

CREATE OR REPLACE FUNCTION public.set_alert_resolution()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    IF NEW.status = 'resolved' THEN
        NEW.resolved_at := COALESCE(NEW.resolved_at, now());
        NEW.resolved_by := COALESCE(NEW.resolved_by, auth.uid());
    ELSIF NEW.status = 'active' THEN
        NEW.resolved_at := NULL;
        NEW.resolved_by := NULL;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_system_alerts_resolution ON public.system_alerts;
CREATE TRIGGER trg_system_alerts_resolution
BEFORE INSERT OR UPDATE OF status ON public.system_alerts
FOR EACH ROW EXECUTE FUNCTION public.set_alert_resolution();

-- ---------------------------------------------------------------------------
-- 6. Row-level security policies. Named policies are recreated on every run.
-- ---------------------------------------------------------------------------
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.papers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.task_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.citations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.research_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.system_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platform_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_cost_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generated_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

-- Replace all RLS policies on the tables managed by this application. Keeping
-- an old permissive policy could bypass the row restrictions below.
DROP POLICY IF EXISTS profiles_select_own ON public.profiles;
DROP POLICY IF EXISTS profiles_update_own ON public.profiles;
DROP POLICY IF EXISTS profiles_admin_insert ON public.profiles;
DROP POLICY IF EXISTS profiles_admin_delete ON public.profiles;
DROP POLICY IF EXISTS gr_profiles_select ON public.profiles;
DROP POLICY IF EXISTS gr_profiles_update ON public.profiles;
DROP POLICY IF EXISTS gr_profiles_delete ON public.profiles;
DROP POLICY IF EXISTS gr_user_preferences_select ON public.user_preferences;
DROP POLICY IF EXISTS gr_user_preferences_insert ON public.user_preferences;
DROP POLICY IF EXISTS gr_user_preferences_update ON public.user_preferences;
DROP POLICY IF EXISTS gr_user_preferences_delete ON public.user_preferences;

DROP POLICY IF EXISTS papers_select ON public.papers;
DROP POLICY IF EXISTS papers_insert ON public.papers;
DROP POLICY IF EXISTS papers_update ON public.papers;
DROP POLICY IF EXISTS papers_delete ON public.papers;
DROP POLICY IF EXISTS gr_papers_select ON public.papers;
DROP POLICY IF EXISTS gr_papers_insert ON public.papers;
DROP POLICY IF EXISTS gr_papers_update ON public.papers;
DROP POLICY IF EXISTS gr_papers_delete ON public.papers;

DROP POLICY IF EXISTS tasks_select ON public.tasks;
DROP POLICY IF EXISTS tasks_insert ON public.tasks;
DROP POLICY IF EXISTS tasks_update ON public.tasks;
DROP POLICY IF EXISTS tasks_delete ON public.tasks;
DROP POLICY IF EXISTS gr_tasks_select ON public.tasks;
DROP POLICY IF EXISTS gr_tasks_insert ON public.tasks;
DROP POLICY IF EXISTS gr_tasks_update ON public.tasks;
DROP POLICY IF EXISTS gr_tasks_delete ON public.tasks;

DROP POLICY IF EXISTS task_results_select ON public.task_results;
DROP POLICY IF EXISTS task_results_insert ON public.task_results;
DROP POLICY IF EXISTS gr_task_results_select ON public.task_results;
DROP POLICY IF EXISTS gr_task_results_insert ON public.task_results;
DROP POLICY IF EXISTS gr_task_results_delete ON public.task_results;

DROP POLICY IF EXISTS citations_select ON public.citations;
DROP POLICY IF EXISTS citations_insert ON public.citations;
DROP POLICY IF EXISTS citations_delete ON public.citations;
DROP POLICY IF EXISTS gr_citations_select ON public.citations;
DROP POLICY IF EXISTS gr_citations_insert ON public.citations;
DROP POLICY IF EXISTS gr_citations_update ON public.citations;
DROP POLICY IF EXISTS gr_citations_delete ON public.citations;

DROP POLICY IF EXISTS agent_logs_admin_select ON public.agent_logs;
DROP POLICY IF EXISTS agent_logs_admin_insert ON public.agent_logs;
DROP POLICY IF EXISTS agent_logs_admin_delete ON public.agent_logs;
DROP POLICY IF EXISTS gr_agent_logs_select ON public.agent_logs;
DROP POLICY IF EXISTS gr_agent_logs_admin_insert ON public.agent_logs;
DROP POLICY IF EXISTS gr_agent_logs_admin_delete ON public.agent_logs;

DROP POLICY IF EXISTS system_alerts_admin_select ON public.system_alerts;
DROP POLICY IF EXISTS system_alerts_admin_insert ON public.system_alerts;
DROP POLICY IF EXISTS system_alerts_admin_update ON public.system_alerts;
DROP POLICY IF EXISTS system_alerts_admin_delete ON public.system_alerts;
DROP POLICY IF EXISTS gr_system_alerts_admin_select ON public.system_alerts;
DROP POLICY IF EXISTS gr_system_alerts_admin_insert ON public.system_alerts;
DROP POLICY IF EXISTS gr_system_alerts_admin_update ON public.system_alerts;
DROP POLICY IF EXISTS gr_system_alerts_admin_delete ON public.system_alerts;

DROP POLICY IF EXISTS platform_settings_admin_select ON public.platform_settings;
DROP POLICY IF EXISTS platform_settings_admin_insert ON public.platform_settings;
DROP POLICY IF EXISTS platform_settings_admin_update ON public.platform_settings;
DROP POLICY IF EXISTS gr_platform_settings_admin_select ON public.platform_settings;
DROP POLICY IF EXISTS gr_platform_settings_admin_insert ON public.platform_settings;
DROP POLICY IF EXISTS gr_platform_settings_admin_update ON public.platform_settings;
DROP POLICY IF EXISTS gr_platform_settings_admin_delete ON public.platform_settings;

DROP POLICY IF EXISTS api_cost_logs_admin_select ON public.api_cost_logs;
DROP POLICY IF EXISTS api_cost_logs_admin_insert ON public.api_cost_logs;
DROP POLICY IF EXISTS gr_api_cost_logs_admin_select ON public.api_cost_logs;
DROP POLICY IF EXISTS gr_api_cost_logs_select ON public.api_cost_logs;

DROP POLICY IF EXISTS gr_reports_select ON public.research_reports;
DROP POLICY IF EXISTS gr_claims_select ON public.generated_claims;
DROP POLICY IF EXISTS gr_audit_select ON public.audit_log;

-- Remove unexpected legacy policies on these managed tables too; permissive
-- PostgreSQL policies are ORed together, so an old broad policy could bypass
-- the restrictions defined below.
DO $$
DECLARE
    existing_policy record;
BEGIN
    FOR existing_policy IN
        SELECT schemaname, tablename, policyname
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = ANY (ARRAY[
              'profiles', 'user_preferences', 'papers', 'tasks', 'task_results',
              'citations', 'research_reports', 'agent_logs', 'system_alerts',
              'platform_settings', 'api_cost_logs', 'generated_claims', 'audit_log'
          ])
    LOOP
        EXECUTE format(
            'DROP POLICY %I ON %I.%I',
            existing_policy.policyname,
            existing_policy.schemaname,
            existing_policy.tablename
        );
    END LOOP;
END
$$;

CREATE POLICY gr_profiles_select ON public.profiles
FOR SELECT TO authenticated
USING (id = (SELECT auth.uid()) OR public.is_admin());

CREATE POLICY gr_profiles_update ON public.profiles
FOR UPDATE TO authenticated
USING (id = (SELECT auth.uid()) OR public.is_admin())
WITH CHECK (id = (SELECT auth.uid()) OR public.is_admin());

CREATE POLICY gr_profiles_delete ON public.profiles
FOR DELETE TO authenticated
USING (public.is_admin());

CREATE POLICY gr_user_preferences_select ON public.user_preferences
FOR SELECT TO authenticated
USING (user_id = (SELECT auth.uid()) OR public.is_admin());
CREATE POLICY gr_user_preferences_insert ON public.user_preferences
FOR INSERT TO authenticated
WITH CHECK (user_id = (SELECT auth.uid()) AND public.is_active_account());
CREATE POLICY gr_user_preferences_update ON public.user_preferences
FOR UPDATE TO authenticated
USING (user_id = (SELECT auth.uid()) OR public.is_admin())
WITH CHECK (user_id = (SELECT auth.uid()) OR public.is_admin());
CREATE POLICY gr_user_preferences_delete ON public.user_preferences
FOR DELETE TO authenticated
USING (public.is_admin());

CREATE POLICY gr_papers_select ON public.papers
FOR SELECT TO authenticated
USING (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));
CREATE POLICY gr_papers_insert ON public.papers
FOR INSERT TO authenticated
WITH CHECK (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));
CREATE POLICY gr_papers_update ON public.papers
FOR UPDATE TO authenticated
USING (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()))
WITH CHECK (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));
CREATE POLICY gr_papers_delete ON public.papers
FOR DELETE TO authenticated
USING (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));

CREATE POLICY gr_tasks_select ON public.tasks
FOR SELECT TO authenticated
USING (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));
CREATE POLICY gr_tasks_insert ON public.tasks
FOR INSERT TO authenticated
WITH CHECK (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));
CREATE POLICY gr_tasks_update ON public.tasks
FOR UPDATE TO authenticated
USING (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()))
WITH CHECK (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));
CREATE POLICY gr_tasks_delete ON public.tasks
FOR DELETE TO authenticated
USING (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));

CREATE POLICY gr_task_results_select ON public.task_results
FOR SELECT TO authenticated
USING (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));
CREATE POLICY gr_task_results_insert ON public.task_results
FOR INSERT TO authenticated
WITH CHECK (
    public.is_admin()
    OR (
        user_id = (SELECT auth.uid())
        AND public.is_active_account()
        AND EXISTS (
            SELECT 1 FROM public.tasks AS t
            WHERE t.id = task_id AND t.user_id = (SELECT auth.uid())
        )
    )
);
CREATE POLICY gr_task_results_delete ON public.task_results
FOR DELETE TO authenticated
USING (public.is_admin() OR user_id = (SELECT auth.uid()));

CREATE POLICY gr_citations_select ON public.citations
FOR SELECT TO authenticated
USING (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));
CREATE POLICY gr_citations_insert ON public.citations
FOR INSERT TO authenticated
WITH CHECK (
    public.is_admin()
    OR (
        user_id = (SELECT auth.uid())
        AND public.is_active_account()
        AND (
            paper_id IS NULL
            OR EXISTS (
                SELECT 1 FROM public.papers AS p
                WHERE p.id = paper_id AND p.user_id = (SELECT auth.uid())
            )
        )
    )
);
CREATE POLICY gr_citations_update ON public.citations
FOR UPDATE TO authenticated
USING (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()))
WITH CHECK (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));
CREATE POLICY gr_citations_delete ON public.citations
FOR DELETE TO authenticated
USING (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));

CREATE POLICY gr_agent_logs_select ON public.agent_logs
FOR SELECT TO authenticated
USING (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));
CREATE POLICY gr_agent_logs_admin_insert ON public.agent_logs
FOR INSERT TO authenticated
WITH CHECK (public.is_admin());
CREATE POLICY gr_agent_logs_admin_delete ON public.agent_logs
FOR DELETE TO authenticated
USING (public.is_admin());

CREATE POLICY gr_system_alerts_admin_select ON public.system_alerts
FOR SELECT TO authenticated USING (public.is_admin());
CREATE POLICY gr_system_alerts_admin_insert ON public.system_alerts
FOR INSERT TO authenticated WITH CHECK (public.is_admin());
CREATE POLICY gr_system_alerts_admin_update ON public.system_alerts
FOR UPDATE TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());
CREATE POLICY gr_system_alerts_admin_delete ON public.system_alerts
FOR DELETE TO authenticated USING (public.is_admin());

CREATE POLICY gr_platform_settings_admin_select ON public.platform_settings
FOR SELECT TO authenticated USING (public.is_admin());
CREATE POLICY gr_platform_settings_admin_insert ON public.platform_settings
FOR INSERT TO authenticated WITH CHECK (public.is_admin());
CREATE POLICY gr_platform_settings_admin_update ON public.platform_settings
FOR UPDATE TO authenticated USING (public.is_admin()) WITH CHECK (public.is_admin());
CREATE POLICY gr_platform_settings_admin_delete ON public.platform_settings
FOR DELETE TO authenticated USING (public.is_admin());

CREATE POLICY gr_api_cost_logs_select ON public.api_cost_logs
FOR SELECT TO authenticated
USING (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));

CREATE POLICY gr_reports_select ON public.research_reports
FOR SELECT TO authenticated
USING (public.is_admin() OR (user_id = (SELECT auth.uid()) AND public.is_active_account()));

CREATE POLICY gr_claims_select ON public.generated_claims
FOR SELECT TO authenticated
USING (
    public.is_admin()
    OR EXISTS (
        SELECT 1 FROM public.research_reports AS r
        WHERE r.session_id = generated_claims.session_id
          AND r.user_id = (SELECT auth.uid())
          AND public.is_active_account()
    )
);

CREATE POLICY gr_audit_select ON public.audit_log
FOR SELECT TO authenticated
USING (
    public.is_admin()
    OR EXISTS (
        SELECT 1 FROM public.research_reports AS r
        WHERE r.session_id = audit_log.session_id
          AND r.user_id = (SELECT auth.uid())
          AND public.is_active_account()
    )
);

-- ---------------------------------------------------------------------------
-- 7. SQL privileges: RLS determines which rows are visible/writable.
-- ---------------------------------------------------------------------------
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
REVOKE ALL ON public.profiles, public.user_preferences, public.papers, public.tasks,
    public.task_results, public.citations, public.agent_logs, public.system_alerts,
    public.platform_settings, public.api_cost_logs, public.research_reports,
    public.generated_claims, public.audit_log FROM anon;
GRANT SELECT, UPDATE, DELETE ON public.profiles TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_preferences TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.papers TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.tasks TO authenticated;
GRANT SELECT, INSERT, DELETE ON public.task_results TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.citations TO authenticated;
GRANT SELECT, INSERT, DELETE ON public.agent_logs TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.system_alerts TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.platform_settings TO authenticated;
GRANT SELECT ON public.api_cost_logs TO authenticated;
GRANT SELECT ON public.research_reports, public.generated_claims, public.audit_log TO authenticated;

GRANT ALL ON public.profiles, public.papers, public.tasks, public.task_results,
    public.user_preferences, public.citations, public.agent_logs, public.system_alerts, public.platform_settings,
    public.api_cost_logs, public.research_reports, public.generated_claims, public.audit_log
TO service_role;

-- ---------------------------------------------------------------------------
-- 8. Read-only aggregate views used by public landing and admin dashboards
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW public.platform_stats AS
SELECT
    (SELECT count(*) FROM public.profiles WHERE status = 'active')::bigint AS total_users,
    (SELECT count(*) FROM public.papers)::bigint AS total_papers,
    (SELECT count(*) FROM public.tasks WHERE status = 'completed')::bigint AS total_tasks_completed,
    (SELECT count(*) FROM public.tasks WHERE status = 'processing')::bigint AS active_tasks,
    (SELECT count(*) FROM public.citations)::bigint AS total_citations;

GRANT SELECT ON public.platform_stats TO anon, authenticated;

CREATE OR REPLACE VIEW public.agent_usage_stats
WITH (security_invoker = true)
AS
WITH task_usage AS (
    SELECT agent_type AS agent,
           count(*)::bigint AS task_count,
           count(*) FILTER (WHERE status = 'completed')::bigint AS tasks_completed,
           count(*) FILTER (WHERE status = 'processing')::bigint AS active_tasks
    FROM public.tasks
    GROUP BY agent_type
), cost_usage AS (
    SELECT agent,
           count(*)::bigint AS api_requests,
           COALESCE(sum(tokens_used), 0)::bigint AS tokens_used,
           COALESCE(sum(cost_usd), 0)::numeric(14, 6) AS cost_usd
    FROM public.api_cost_logs
    GROUP BY agent
)
SELECT COALESCE(t.agent, c.agent) AS agent,
       COALESCE(t.task_count, 0)::bigint AS task_count,
       COALESCE(t.tasks_completed, 0)::bigint AS tasks_completed,
       COALESCE(t.active_tasks, 0)::bigint AS active_tasks,
       COALESCE(c.api_requests, 0)::bigint AS api_requests,
       COALESCE(c.tokens_used, 0)::bigint AS tokens_used,
       COALESCE(c.cost_usd, 0)::numeric(14, 6) AS cost_usd
FROM task_usage AS t
FULL OUTER JOIN cost_usage AS c ON c.agent = t.agent
WHERE public.is_admin();

GRANT SELECT ON public.agent_usage_stats TO authenticated;

-- ---------------------------------------------------------------------------
-- 9. Idempotent platform-setting seeds (never overwrite configured values)
-- ---------------------------------------------------------------------------
INSERT INTO public.platform_settings (key, value) VALUES
    ('platform_name', '"GenResearch"'::jsonb),
    ('admin_email', '"admin@comsats.edu.pk"'::jsonb),
    ('timezone', '"Asia/Karachi"'::jsonb),
    ('default_model', '"gpt-3.5-turbo"'::jsonb),
    ('temperature', '0.7'::jsonb),
    ('max_tokens', '2048'::jsonb),
    ('stream_enabled', 'true'::jsonb),
    ('daily_budget', '10'::jsonb),
    ('monthly_budget', '150'::jsonb),
    ('chunk_size', '512'::jsonb),
    ('chunk_overlap', '64'::jsonb),
    ('top_k', '5'::jsonb),
    ('embedding_model', '"text-embedding-ada-002"'::jsonb),
    ('maintenance_mode', 'false'::jsonb),
    ('auto_backup', 'true'::jsonb),
    ('email_alerts', 'true'::jsonb),
    ('agent_fail_alert', 'true'::jsonb),
    ('cost_alert', 'true'::jsonb),
    ('new_user_alert', 'false'::jsonb),
    ('daily_digest', 'true'::jsonb),
    ('mfa_required', 'false'::jsonb),
    ('session_timeout', '60'::jsonb),
    ('ip_whitelist', 'false'::jsonb)
ON CONFLICT (key) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 10. Realtime publication. Add each table only if not already published.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    table_name text;
    realtime_tables text[] := ARRAY[
        'profiles', 'papers', 'tasks', 'task_results', 'citations',
        'agent_logs', 'system_alerts', 'platform_settings', 'api_cost_logs',
        'research_reports', 'generated_claims', 'audit_log'
    ];
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime'
    ) THEN
        EXECUTE 'CREATE PUBLICATION supabase_realtime';
    END IF;

    FOREACH table_name IN ARRAY realtime_tables LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_publication_tables
            WHERE pubname = 'supabase_realtime'
              AND schemaname = 'public'
              AND tablename = table_name
        ) THEN
            EXECUTE format('ALTER PUBLICATION supabase_realtime ADD TABLE public.%I', table_name);
        END IF;
    END LOOP;
END
$$;

COMMIT;

-- ---------------------------------------------------------------------------
-- Integration map
--   User frontend: profiles, papers, tasks, task_results, citations,
--                  user_preferences, agent_logs (own rows), platform_stats,
--                  update_last_seen().
--   Admin frontend: all profiles/papers/tasks, agent_logs, system_alerts,
--                   platform_settings, api_cost_logs, platform_stats,
--                   agent_usage_stats.
--   FastAPI backend (service_role): papers, tasks, task_results, citations,
--                   agent_logs, system_alerts, api_cost_logs, research_reports,
--                   generated_claims, audit_log.
--   Auth signup: creates a student profile; admin role must be assigned by an
--                existing administrator through the protected profiles table.
-- First-admin bootstrap (run once, replacing the email):
--   UPDATE public.profiles SET role = 'admin'
--   WHERE email = 'your-admin-email@example.com';
--
-- Direct UI controls that currently only show toast/local state (for example,
-- Admin Settings save buttons, restart/rebuild actions, and some upload/download
-- placeholders) still need application/API handlers; SQL cannot wire a button
-- that does not call Supabase or the FastAPI backend. The existing admin paper
-- upload modal stores metadata only. User PDF file bytes currently live in the
-- FastAPI server's local storage, not in Supabase Storage.
-- ---------------------------------------------------------------------------
