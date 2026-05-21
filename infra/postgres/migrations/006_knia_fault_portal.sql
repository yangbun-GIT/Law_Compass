CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knia_sources (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  base_url text NOT NULL,
  terms_note text,
  created_at timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knia_menu_pages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  menu_group text NOT NULL,
  menu_name text NOT NULL,
  page_url text NOT NULL UNIQUE,
  title text,
  content_text text,
  plain_summary text,
  source_url text NOT NULL,
  collected_at timestamp DEFAULT now(),
  updated_at timestamp DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb,
  tsv tsvector
);

CREATE TABLE IF NOT EXISTS knia_fault_charts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chart_no text NOT NULL,
  chart_type text NOT NULL DEFAULT '1',
  title text NOT NULL,
  vehicle_a_label text,
  vehicle_b_label text,
  category_path jsonb DEFAULT '[]'::jsonb,
  accident_summary text,
  applicable_text text,
  non_applicable_text text,
  basic_fault_text text,
  base_fault_a int,
  base_fault_b int,
  adjustment_factors jsonb DEFAULT '[]'::jsonb,
  related_laws jsonb DEFAULT '[]'::jsonb,
  precedents jsonb DEFAULT '[]'::jsonb,
  source_url text NOT NULL,
  thumbnail_url text,
  video_url text,
  media_embed_url text,
  media_provider text DEFAULT 'external_url',
  license_status text DEFAULT 'source_link_only',
  attribution text DEFAULT '출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털',
  collected_at timestamp DEFAULT now(),
  updated_at timestamp DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb,
  tsv tsvector,
  UNIQUE(chart_no, chart_type)
);

CREATE TABLE IF NOT EXISTS knia_fault_chart_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chart_id uuid REFERENCES knia_fault_charts(id) ON DELETE CASCADE,
  chunk_type text NOT NULL,
  chunk_text text NOT NULL,
  plain_summary text,
  scenario_tags text[] DEFAULT '{}',
  keywords text[] DEFAULT '{}',
  source_url text,
  video_url text,
  display_priority int DEFAULT 100,
  tsv tsvector,
  embedding vector(1024),
  created_at timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knia_fault_rankings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  rank_period text DEFAULT 'last_30_days',
  rank_no int NOT NULL,
  chart_no text NOT NULL,
  chart_type text DEFAULT '1',
  title text NOT NULL,
  search_count int,
  percentage numeric,
  source_url text,
  thumbnail_url text,
  collected_at timestamp DEFAULT now(),
  UNIQUE(rank_period, rank_no, collected_at)
);

CREATE TABLE IF NOT EXISTS knia_media_assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chart_id uuid REFERENCES knia_fault_charts(id) ON DELETE CASCADE,
  asset_type text NOT NULL,
  source_url text NOT NULL,
  embed_url text,
  storage_provider text DEFAULT 'external_url',
  storage_key text NULL,
  mime_type text,
  title text,
  attribution text DEFAULT '출처: 과실비율정보포털',
  license_status text DEFAULT 'source_link_only',
  created_at timestamp DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb
);

ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS knia_matches jsonb DEFAULT '[]'::jsonb;
ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS knia_primary_match jsonb;

CREATE INDEX IF NOT EXISTS idx_knia_menu_pages_tsv ON knia_menu_pages USING gin(tsv);
CREATE INDEX IF NOT EXISTS idx_knia_fault_charts_tsv ON knia_fault_charts USING gin(tsv);
CREATE INDEX IF NOT EXISTS idx_knia_fault_chart_chunks_tsv ON knia_fault_chart_chunks USING gin(tsv);
CREATE INDEX IF NOT EXISTS idx_knia_fault_chart_chunks_tags ON knia_fault_chart_chunks USING gin(scenario_tags);
CREATE INDEX IF NOT EXISTS idx_knia_fault_chart_chunks_keywords ON knia_fault_chart_chunks USING gin(keywords);
CREATE INDEX IF NOT EXISTS idx_knia_fault_rankings_chart_no ON knia_fault_rankings(chart_no);
CREATE INDEX IF NOT EXISTS idx_knia_fault_charts_chart_no_type ON knia_fault_charts(chart_no, chart_type);
CREATE INDEX IF NOT EXISTS idx_knia_fault_chart_chunks_chart_id ON knia_fault_chart_chunks(chart_id);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_opclass WHERE opcname = 'vector_cosine_ops') THEN
    CREATE INDEX IF NOT EXISTS idx_knia_fault_chart_chunks_embedding
      ON knia_fault_chart_chunks USING hnsw (embedding vector_cosine_ops);
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'Skipping KNIA vector index: %', SQLERRM;
END $$;
