create table if not exists paper_structure (
  paper_id uuid primary key,
  user_id uuid not null,
  status text not null check (status in ('pending','ready','partial','failed','no_text_layer')),
  extractor_version text not null,
  page_count int,
  references_start_page int,
  reference_count int,
  expected_reference_count int,
  missing_reference_ids int[] default '{}',
  section_count int,
  body_char_coverage numeric,
  paper_type text,
  error text,
  updated_at timestamptz default now()
);

create table if not exists paper_sections (
  id uuid primary key default gen_random_uuid(),
  paper_id uuid not null,
  user_id uuid not null,
  ordinal int not null,
  level int not null,
  title text not null,
  page_start int,
  page_end int,
  text text not null,
  cited_refs int[] default '{}',
  is_fallback_window boolean default false,
  unique (paper_id, ordinal)
);

create table if not exists paper_references (
  id uuid primary key default gen_random_uuid(),
  paper_id uuid not null,
  user_id uuid not null,
  ref_number int,
  raw text not null,
  authors text,
  title text,
  year int,
  venue text,
  doi text,
  arxiv_id text,
  parse_confidence numeric,
  verified boolean default false,
  verification_source text,
  unique (paper_id, ref_number)
);

create table if not exists paper_items (
  id uuid primary key default gen_random_uuid(),
  paper_id uuid not null,
  user_id uuid not null,
  kind text check (kind in ('table','figure')),
  label text,
  caption text,
  page int
);

create table if not exists paper_section_insights (
  paper_id uuid,
  section_ordinal int,
  intent text,
  prompt_version text,
  section_hash text,
  items jsonb not null,
  created_at timestamptz default now(),
  primary key (paper_id, section_ordinal, intent, prompt_version, section_hash)
);

create index if not exists idx_paper_structure_paper_id on paper_structure (paper_id);
create index if not exists idx_paper_structure_user_id_paper_id on paper_structure (user_id, paper_id);
create index if not exists idx_paper_sections_paper_id on paper_sections (paper_id);
create index if not exists idx_paper_sections_user_id_paper_id on paper_sections (user_id, paper_id);
create index if not exists idx_paper_references_paper_id on paper_references (paper_id);
create index if not exists idx_paper_references_user_id_paper_id on paper_references (user_id, paper_id);
create index if not exists idx_paper_items_paper_id on paper_items (paper_id);
create index if not exists idx_paper_items_user_id_paper_id on paper_items (user_id, paper_id);
