-- Run after complete_frontend_backend_setup.sql to verify that the expected
-- objects exist in the current Supabase project.
SELECT 'table' AS object_type, expected.name AS object_name,
       to_regclass(format('public.%I', expected.name)) IS NOT NULL AS exists
FROM unnest(ARRAY[
    'profiles', 'user_preferences', 'papers', 'tasks', 'task_results',
    'citations', 'research_reports', 'agent_logs', 'system_alerts',
    'platform_settings', 'api_cost_logs', 'generated_claims', 'audit_log'
]) AS expected(name)
UNION ALL
SELECT 'view', expected.name,
       to_regclass(format('public.%I', expected.name)) IS NOT NULL
FROM unnest(ARRAY['platform_stats', 'agent_usage_stats']) AS expected(name)
UNION ALL
SELECT 'function', expected.name,
       to_regprocedure(expected.signature) IS NOT NULL
FROM (VALUES
    ('update_last_seen', 'public.update_last_seen()'),
    ('is_admin', 'public.is_admin()'),
    ('is_active_account', 'public.is_active_account()')
) AS expected(name, signature)
ORDER BY object_type, object_name;

-- List realtime publication membership for the client-subscribed tables.
SELECT schemaname, tablename
FROM pg_publication_tables
WHERE pubname = 'supabase_realtime'
  AND schemaname = 'public'
ORDER BY tablename;
