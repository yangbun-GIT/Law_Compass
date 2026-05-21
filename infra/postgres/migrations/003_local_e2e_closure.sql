ALTER TABLE uploads
  ADD COLUMN IF NOT EXISTS frame_dir TEXT,
  ADD COLUMN IF NOT EXISTS preprocess_summary TEXT;

ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS artifacts JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS attempt INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_error TEXT,
  ADD COLUMN IF NOT EXISTS next_run_at TIMESTAMPTZ;

UPDATE jobs SET attempt = attempts WHERE attempt <> attempts;

ALTER TABLE analysis_results
  ADD COLUMN IF NOT EXISTS structured_facts JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS recommended_keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS suggested_next_inputs JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS report_payload JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE cases
  ADD COLUMN IF NOT EXISTS input_text_structured JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE cases
SET input_text_structured = structured_facts
WHERE input_text_structured = '{}'::jsonb
  AND structured_facts <> '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_jobs_status_type_next_run ON jobs(status, type, next_run_at);
CREATE INDEX IF NOT EXISTS idx_uploads_case_id ON uploads(case_id);
CREATE INDEX IF NOT EXISTS idx_analysis_results_case_id ON analysis_results(case_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_results_structured_gin ON analysis_results USING gin(structured_facts jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_analysis_results_report_gin ON analysis_results USING gin(report_payload jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_uploads_metadata_gin ON uploads USING gin(metadata jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_kb_embeddings_hnsw
  ON kb_embeddings USING hnsw (embedding vector_cosine_ops)
  WITH (m = 8, ef_construction = 40);
