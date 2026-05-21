CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

DO $$ BEGIN
  CREATE TYPE user_role AS ENUM ('user', 'admin');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
  CREATE TYPE case_status AS ENUM ('draft', 'ready', 'analyzing', 'completed', 'failed', 'archived');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
  CREATE TYPE upload_status AS ENUM ('init', 'uploaded', 'verified', 'processing', 'ready', 'failed', 'deleted');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
  CREATE TYPE job_type AS ENUM ('video_preprocess', 'video_analyze', 'kb_embed');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
  CREATE TYPE job_status AS ENUM ('queued', 'running', 'retrying', 'succeeded', 'failed', 'dead');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email CITEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  display_name VARCHAR(80) NOT NULL,
  role user_role NOT NULL DEFAULT 'user',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  token_hash TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  rotated_from UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_refresh_user_id ON auth_refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_active ON auth_refresh_tokens(user_id, expires_at) WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id UUID NOT NULL REFERENCES users(id),
  title VARCHAR(140) NOT NULL,
  description_text TEXT,
  status case_status NOT NULL DEFAULT 'draft',
  happened_at TIMESTAMPTZ,
  location_text VARCHAR(240),
  tags TEXT[] NOT NULL DEFAULT '{}',
  latest_result_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_cases_owner_created ON cases(owner_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);

CREATE TABLE IF NOT EXISTS uploads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES cases(id),
  owner_user_id UUID NOT NULL REFERENCES users(id),
  s3_bucket TEXT NOT NULL,
  s3_key TEXT NOT NULL UNIQUE,
  file_name VARCHAR(255) NOT NULL,
  content_type VARCHAR(100) NOT NULL,
  file_size_bytes BIGINT,
  etag VARCHAR(128),
  status upload_status NOT NULL DEFAULT 'init',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_uploads_case_owner ON uploads(case_id, owner_user_id);
CREATE INDEX IF NOT EXISTS idx_uploads_status ON uploads(status);

CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID REFERENCES cases(id),
  upload_id UUID REFERENCES uploads(id),
  owner_user_id UUID REFERENCES users(id),
  type job_type NOT NULL,
  status job_status NOT NULL DEFAULT 'queued',
  attempts INT NOT NULL DEFAULT 0,
  max_attempts INT NOT NULL DEFAULT 5,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  error_info JSONB,
  scheduled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_jobs_owner_status ON jobs(owner_user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_type_status ON jobs(type, status);

CREATE TABLE IF NOT EXISTS analysis_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES cases(id),
  owner_user_id UUID NOT NULL REFERENCES users(id),
  version INT NOT NULL DEFAULT 1,
  source_type VARCHAR(20) NOT NULL,
  result JSONB NOT NULL,
  evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
  uncertainty JSONB NOT NULL DEFAULT '{}'::jsonb,
  model_info JSONB NOT NULL DEFAULT '{}'::jsonb,
  prompt_policy_version_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(case_id, version)
);
CREATE INDEX IF NOT EXISTS idx_results_case_version ON analysis_results(case_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_results_evidence_gin ON analysis_results USING gin(evidence jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_results_model_info_gin ON analysis_results USING gin(model_info);

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY,
  trace_id UUID NOT NULL,
  actor_user_id UUID,
  actor_role VARCHAR(16),
  action VARCHAR(120) NOT NULL,
  target_type VARCHAR(40),
  target_id UUID,
  ip INET,
  user_agent TEXT,
  req_hash VARCHAR(128),
  res_hash VARCHAR(128),
  status_code INT,
  extra JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_trace ON audit_logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor_user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS kb_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(120) NOT NULL,
  source_type VARCHAR(40) NOT NULL,
  source_uri TEXT,
  jurisdiction VARCHAR(40) DEFAULT 'KR',
  effective_date DATE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS kb_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id UUID NOT NULL REFERENCES kb_sources(id),
  title TEXT NOT NULL,
  doc_type VARCHAR(40) NOT NULL,
  published_at DATE,
  raw_text TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  tsv tsvector,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_kb_documents_tsv ON kb_documents USING gin(tsv);

CREATE TABLE IF NOT EXISTS kb_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES kb_documents(id),
  chunk_index INT NOT NULL,
  chunk_text TEXT NOT NULL,
  chunk_summary TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  tsv tsvector,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(document_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_tsv ON kb_chunks USING gin(tsv);

CREATE TABLE IF NOT EXISTS kb_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chunk_id UUID NOT NULL UNIQUE REFERENCES kb_chunks(id),
  embedding vector(1024) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_kb_embeddings_ivfflat ON kb_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS idempotency_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key_hash VARCHAR(128) NOT NULL,
  user_id UUID NOT NULL REFERENCES users(id),
  route VARCHAR(120) NOT NULL,
  request_hash VARCHAR(128) NOT NULL,
  response_code INT,
  response_body JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  UNIQUE (key_hash, user_id, route)
);
CREATE INDEX IF NOT EXISTS idx_idempo_expires ON idempotency_keys(expires_at);

CREATE TABLE IF NOT EXISTS prompt_policy_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(120) NOT NULL,
  version VARCHAR(40) NOT NULL,
  policy_text TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(name, version)
);

ALTER TABLE cases
  ADD CONSTRAINT fk_cases_latest_result
  FOREIGN KEY (latest_result_id) REFERENCES analysis_results(id)
  DEFERRABLE INITIALLY DEFERRED;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cases_updated_at ON cases;
CREATE TRIGGER trg_cases_updated_at BEFORE UPDATE ON cases FOR EACH ROW EXECUTE FUNCTION set_updated_at();
DROP TRIGGER IF EXISTS trg_uploads_updated_at ON uploads;
CREATE TRIGGER trg_uploads_updated_at BEFORE UPDATE ON uploads FOR EACH ROW EXECUTE FUNCTION set_updated_at();
DROP TRIGGER IF EXISTS trg_jobs_updated_at ON jobs;
CREATE TRIGGER trg_jobs_updated_at BEFORE UPDATE ON jobs FOR EACH ROW EXECUTE FUNCTION set_updated_at();
DROP TRIGGER IF EXISTS trg_kb_documents_updated_at ON kb_documents;
CREATE TRIGGER trg_kb_documents_updated_at BEFORE UPDATE ON kb_documents FOR EACH ROW EXECUTE FUNCTION set_updated_at();

