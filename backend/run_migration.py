"""
Run the research_reports migration against Supabase.
Uses the service-role key to execute raw SQL via the pg REST endpoint.
"""
import sys
import os
import requests

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import settings

SQL = """
CREATE TABLE IF NOT EXISTS public.research_reports (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       UUID NOT NULL UNIQUE,
    user_id          UUID NOT NULL,
    topic            TEXT NOT NULL,
    draft_text       TEXT,
    completion_guide TEXT,
    outline          JSONB,
    citation_registry JSONB,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_reports_session
    ON public.research_reports(session_id);

CREATE INDEX IF NOT EXISTS idx_research_reports_user
    ON public.research_reports(user_id);
"""

def run():
    # Use Supabase's REST SQL endpoint (requires service-role key)
    url = f"{settings.SUPABASE_URL}/rest/v1/rpc/exec_sql"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    # Supabase exposes pg via the pg-meta endpoint on port 5432 internally,
    # but from outside we use the Management API if available, or a pg_query RPC.
    # The cleanest approach without the CLI is to hit pg directly via psycopg2
    # using the Supabase connection string.
    try:
        import psycopg2

        # Build postgres URL from Supabase project ref
        # Supabase URL is like: https://<ref>.supabase.co
        ref = settings.SUPABASE_URL.replace("https://", "").split(".")[0]
        db_url = f"postgresql://postgres.{ref}:{settings.SUPABASE_SERVICE_KEY}@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(SQL)
        conn.close()
        print("✅ Migration applied successfully via psycopg2.")

    except ImportError:
        print("psycopg2 not available, trying supabase-py rpc...")
        # Fall back: create a stored procedure via RPC if it exists
        from database.supabase_client import get_supabase
        sb = get_supabase()
        # Try running raw SQL via pg_query (only works if the function exists)
        try:
            res = sb.rpc("exec_sql", {"sql": SQL}).execute()
            print(f"✅ RPC result: {res.data}")
        except Exception as e:
            print(f"❌ RPC also failed: {e}")
            print("\n⚠ Please run the following SQL manually in your Supabase SQL editor:")
            print("-" * 60)
            print(SQL)
            print("-" * 60)

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("\n⚠ Please run the following SQL manually in your Supabase SQL editor:")
        print("   Dashboard → SQL Editor → New Query → paste and run:")
        print("-" * 60)
        print(SQL)
        print("-" * 60)

if __name__ == "__main__":
    run()
