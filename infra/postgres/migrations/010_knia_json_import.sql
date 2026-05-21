CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS knia_json_import_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_file_path text NOT NULL,
  source_file_hash text NOT NULL,
  source_site text,
  base_url text,
  collected_at text,
  imported_pages int DEFAULT 0,
  imported_documents int DEFAULT 0,
  imported_menu_nodes int DEFAULT 0,
  imported_media_assets int DEFAULT 0,
  imported_chunks int DEFAULT 0,
  status text DEFAULT 'running',
  error_message text,
  started_at timestamp DEFAULT now(),
  finished_at timestamp,
  metadata jsonb DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS knia_myaccident_pages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  myaccident_no int NOT NULL,
  page_url text NOT NULL,
  page_title text,
  page_description text,
  accident_party_type text DEFAULT 'unknown',
  accident_party_label text,
  raw_menu_count int DEFAULT 0,
  source_file_hash text,
  collected_at timestamp DEFAULT now(),
  updated_at timestamp DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb,
  UNIQUE(myaccident_no)
);

CREATE TABLE IF NOT EXISTS knia_menu_nodes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  page_id uuid REFERENCES knia_myaccident_pages(id) ON DELETE CASCADE,
  parent_id uuid REFERENCES knia_menu_nodes(id) ON DELETE CASCADE NULL,
  depth int DEFAULT 0,
  display_order int DEFAULT 0,
  label text NOT NULL,
  normalized_label text,
  category_path jsonb DEFAULT '[]'::jsonb,
  accident_party_type text DEFAULT 'unknown',
  accident_party_label text,
  chart_no text NULL,
  chart_type text NULL,
  source_url text,
  source_snapshot_label text,
  source_file_hash text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp DEFAULT now(),
  updated_at timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knia_reference_documents (
  id text PRIMARY KEY,
  source text,
  source_url text NOT NULL,
  title text,
  label text,
  headings jsonb DEFAULT '[]'::jsonb,
  content text NOT NULL,
  content_hash text NOT NULL,
  myaccident_no int,
  accident_party_type text DEFAULT 'unknown',
  accident_party_label text,
  source_file_hash text,
  metadata jsonb DEFAULT '{}'::jsonb,
  tsv tsvector,
  created_at timestamp DEFAULT now(),
  updated_at timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knia_reference_chunks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id text REFERENCES knia_reference_documents(id) ON DELETE CASCADE,
  chunk_index int NOT NULL,
  chunk_type text DEFAULT 'rag',
  chunk_text text NOT NULL,
  plain_summary text,
  source_url text,
  myaccident_no int,
  accident_party_type text DEFAULT 'unknown',
  accident_party_label text,
  scenario_tags text[] DEFAULT '{}',
  keywords text[] DEFAULT '{}',
  display_tags text[] DEFAULT '{}',
  content_hash text,
  evidence_quality_score numeric DEFAULT 0.5,
  tsv tsvector,
  embedding vector(1024),
  created_at timestamp DEFAULT now()
);

CREATE TABLE IF NOT EXISTS knia_json_media_assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id text NULL,
  menu_node_id uuid NULL,
  asset_type text NOT NULL,
  source_url text NOT NULL,
  embed_url text,
  title text,
  alt text,
  storage_provider text DEFAULT 'external_url',
  storage_key text NULL,
  mime_type text,
  accident_party_type text DEFAULT 'unknown',
  attribution text DEFAULT '출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털',
  license_status text DEFAULT 'source_link_only',
  source_file_hash text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp DEFAULT now(),
  UNIQUE(source_url)
);

CREATE TABLE IF NOT EXISTS semantic_query_cache (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_scope text NOT NULL,
  accident_party_type text,
  scenario_type text,
  normalized_query text NOT NULL,
  query_hash text NOT NULL,
  query_embedding vector(1024),
  result_refs jsonb NOT NULL,
  kb_version text,
  hit_count int DEFAULT 0,
  created_at timestamp DEFAULT now(),
  updated_at timestamp DEFAULT now(),
  expires_at timestamp NULL
);

CREATE TABLE IF NOT EXISTS mcp_tool_calls (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id text NOT NULL,
  tool_name text NOT NULL,
  input_summary text,
  output_summary text,
  status text,
  latency_ms int,
  error_message text,
  created_at timestamp DEFAULT now(),
  metadata jsonb DEFAULT '{}'::jsonb
);

ALTER TABLE knia_json_media_assets ADD COLUMN IF NOT EXISTS document_id text NULL;
ALTER TABLE knia_json_media_assets ADD COLUMN IF NOT EXISTS menu_node_id uuid NULL;
ALTER TABLE knia_json_media_assets ADD COLUMN IF NOT EXISTS embed_url text;
ALTER TABLE semantic_query_cache ADD COLUMN IF NOT EXISTS query_embedding vector(1024);

CREATE INDEX IF NOT EXISTS idx_knia_myaccident_pages_no ON knia_myaccident_pages(myaccident_no);
CREATE INDEX IF NOT EXISTS idx_knia_menu_nodes_page ON knia_menu_nodes(page_id);
CREATE INDEX IF NOT EXISTS idx_knia_menu_nodes_parent ON knia_menu_nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_knia_menu_nodes_chart_no ON knia_menu_nodes(chart_no);
CREATE INDEX IF NOT EXISTS idx_knia_menu_nodes_party ON knia_menu_nodes(accident_party_type);
CREATE INDEX IF NOT EXISTS idx_knia_ref_docs_myaccident ON knia_reference_documents(myaccident_no);
CREATE INDEX IF NOT EXISTS idx_knia_ref_docs_party ON knia_reference_documents(accident_party_type);
CREATE INDEX IF NOT EXISTS idx_knia_ref_docs_tsv ON knia_reference_documents USING gin(tsv);
CREATE INDEX IF NOT EXISTS idx_knia_ref_chunks_doc ON knia_reference_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_knia_ref_chunks_myaccident ON knia_reference_chunks(myaccident_no);
CREATE INDEX IF NOT EXISTS idx_knia_ref_chunks_party ON knia_reference_chunks(accident_party_type);
CREATE INDEX IF NOT EXISTS idx_knia_ref_chunks_tsv ON knia_reference_chunks USING gin(tsv);
CREATE INDEX IF NOT EXISTS idx_knia_ref_chunks_scenario_tags ON knia_reference_chunks USING gin(scenario_tags);
CREATE INDEX IF NOT EXISTS idx_knia_ref_chunks_keywords ON knia_reference_chunks USING gin(keywords);
CREATE INDEX IF NOT EXISTS idx_knia_json_media_source_url ON knia_json_media_assets(source_url);
CREATE INDEX IF NOT EXISTS idx_semantic_query_cache_hash ON semantic_query_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_semantic_query_cache_scope ON semantic_query_cache(source_scope);
CREATE INDEX IF NOT EXISTS idx_semantic_query_cache_party ON semantic_query_cache(accident_party_type);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_trace ON mcp_tool_calls(trace_id);
CREATE INDEX IF NOT EXISTS idx_mcp_tool_calls_tool ON mcp_tool_calls(tool_name);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_knia_ref_chunks_embedding') THEN
    CREATE INDEX idx_knia_ref_chunks_embedding ON knia_reference_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'Skipping knia_reference_chunks vector index: %', SQLERRM;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_semantic_query_cache_embedding') THEN
    CREATE INDEX idx_semantic_query_cache_embedding ON semantic_query_cache USING ivfflat (query_embedding vector_cosine_ops) WITH (lists = 25);
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'Skipping semantic_query_cache vector index: %', SQLERRM;
END $$;
