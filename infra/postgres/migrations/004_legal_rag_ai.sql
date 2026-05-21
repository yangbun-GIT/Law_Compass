CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE kb_sources
  ADD COLUMN IF NOT EXISTS provider TEXT,
  ADD COLUMN IF NOT EXISTS version_tag TEXT,
  ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE kb_documents
  ADD COLUMN IF NOT EXISTS jurisdiction TEXT NOT NULL DEFAULT 'KR',
  ADD COLUMN IF NOT EXISTS effective_date DATE,
  ADD COLUMN IF NOT EXISTS summary TEXT;

ALTER TABLE kb_chunks
  ADD COLUMN IF NOT EXISTS article_no TEXT,
  ADD COLUMN IF NOT EXISTS clause_no TEXT,
  ADD COLUMN IF NOT EXISTS scenario_tags TEXT[] NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS keywords TEXT[] NOT NULL DEFAULT '{}';

ALTER TABLE kb_embeddings
  ADD COLUMN IF NOT EXISTS embedding_model TEXT NOT NULL DEFAULT 'deterministic-1024';

CREATE TABLE IF NOT EXISTS kb_ingest_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,
  status TEXT NOT NULL,
  inserted_documents INT NOT NULL DEFAULT 0,
  inserted_chunks INT NOT NULL DEFAULT 0,
  error_message TEXT,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS legal_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_code TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  description TEXT NOT NULL,
  scenario_tags TEXT[] NOT NULL DEFAULT '{}',
  required_facts TEXT[] NOT NULL DEFAULT '{}',
  risk_flags TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS scenario_legal_mappings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scenario_type TEXT NOT NULL,
  rule_code TEXT NOT NULL,
  weight NUMERIC NOT NULL DEFAULT 1.0,
  required_facts TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE analysis_results
  ADD COLUMN IF NOT EXISTS legal_analysis JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS scenario_type TEXT,
  ADD COLUMN IF NOT EXISTS used_evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS legal_risk_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS persona_outputs JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS evidence_audit JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_kb_documents_tsv_gin ON kb_documents USING gin(tsv);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_tsv_gin ON kb_chunks USING gin(tsv);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_scenario_tags_gin ON kb_chunks USING gin(scenario_tags);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_keywords_gin ON kb_chunks USING gin(keywords);
CREATE INDEX IF NOT EXISTS idx_scenario_legal_mappings_type ON scenario_legal_mappings(scenario_type);
CREATE INDEX IF NOT EXISTS idx_legal_rules_rule_code ON legal_rules(rule_code);
CREATE INDEX IF NOT EXISTS idx_legal_rules_scenario_tags_gin ON legal_rules USING gin(scenario_tags);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname = current_schema()
      AND indexname = 'idx_kb_embeddings_embedding_hnsw_1024'
  ) THEN
    CREATE INDEX idx_kb_embeddings_embedding_hnsw_1024
      ON kb_embeddings USING hnsw (embedding vector_cosine_ops)
      WITH (m = 8, ef_construction = 40);
  END IF;
END $$;
