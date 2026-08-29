# ============================================================
# GenResearch — Database Schema Setup
# SQL script to be executed in Supabase SQL editor
# ============================================================

-- Create the research_reports table for Phase 5 (C2)
CREATE TABLE IF NOT EXISTS public.research_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,
    user_id UUID NOT NULL,
    topic TEXT NOT NULL,
    draft_text TEXT,
    completion_guide TEXT,
    outline JSONB,
    citation_registry JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast lookup by session
CREATE INDEX IF NOT EXISTS idx_research_reports_session ON public.research_reports(session_id);
