-- Elderly-friendly report and display-oriented evidence fields.
-- Safe to run repeatedly.

ALTER TABLE analysis_results
  ADD COLUMN IF NOT EXISTS elderly_friendly_report JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE kb_chunks
  ADD COLUMN IF NOT EXISTS plain_summary TEXT,
  ADD COLUMN IF NOT EXISTS related_reason TEXT,
  ADD COLUMN IF NOT EXISTS display_priority INT NOT NULL DEFAULT 100,
  ADD COLUMN IF NOT EXISTS source_url TEXT,
  ADD COLUMN IF NOT EXISTS law_name TEXT,
  ADD COLUMN IF NOT EXISTS article_title TEXT;

CREATE INDEX IF NOT EXISTS idx_kb_chunks_display_priority ON kb_chunks(display_priority);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_law_name ON kb_chunks(law_name);
CREATE INDEX IF NOT EXISTS idx_kb_chunks_plain_fields_gin
  ON kb_chunks USING gin ((to_tsvector('simple', coalesce(plain_summary,'') || ' ' || coalesce(related_reason,''))));
