-- Grounding and observability tables for verified proposal runs.
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

CREATE INDEX IF NOT EXISTS idx_generated_claims_session ON public.generated_claims(session_id);
CREATE INDEX IF NOT EXISTS idx_generated_claims_verdict ON public.generated_claims(verdict);

CREATE TABLE IF NOT EXISTS public.audit_log (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid,
  node_name text NOT NULL,
  model_used text,
  prompt_hash text,
  tokens_in int NOT NULL DEFAULT 0,
  tokens_out int NOT NULL DEFAULT 0,
  latency_ms int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_session ON public.audit_log(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON public.audit_log(created_at DESC);