ALTER TABLE uploads
  ADD COLUMN IF NOT EXISTS storage_provider VARCHAR(20) NOT NULL DEFAULT 's3',
  ADD COLUMN IF NOT EXISTS storage_path TEXT,
  ADD COLUMN IF NOT EXISTS derived_path TEXT;

CREATE INDEX IF NOT EXISTS idx_uploads_storage_provider ON uploads(storage_provider, status);

ALTER TABLE cases
  ADD COLUMN IF NOT EXISTS structured_facts JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS selected_keywords TEXT[] NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS analysis_mode VARCHAR(40) NOT NULL DEFAULT 'quick_summary';

CREATE INDEX IF NOT EXISTS idx_cases_structured_facts_gin ON cases USING gin(structured_facts jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_cases_selected_keywords ON cases USING gin(selected_keywords);

CREATE INDEX IF NOT EXISTS idx_kb_chunks_doc_order ON kb_chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_kb_documents_type_created ON kb_documents(doc_type, created_at DESC);
