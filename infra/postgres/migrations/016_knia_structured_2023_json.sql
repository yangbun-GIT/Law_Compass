CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE IF EXISTS knia_fault_charts
  ADD COLUMN IF NOT EXISTS document_id text,
  ADD COLUMN IF NOT EXISTS major_party_type text,
  ADD COLUMN IF NOT EXISTS scenario_type text,
  ADD COLUMN IF NOT EXISTS scenario_subtype text,
  ADD COLUMN IF NOT EXISTS page_start int,
  ADD COLUMN IF NOT EXISTS page_end int,
  ADD COLUMN IF NOT EXISTS vehicle_roles jsonb DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS base_fault jsonb DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS adjustments jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS accident_situation text,
  ADD COLUMN IF NOT EXISTS base_fault_explanation text,
  ADD COLUMN IF NOT EXISTS usage_notes text,
  ADD COLUMN IF NOT EXISTS raw_text text,
  ADD COLUMN IF NOT EXISTS parsing_confidence numeric,
  ADD COLUMN IF NOT EXISTS review_required boolean DEFAULT false;

UPDATE knia_fault_charts
SET major_party_type = COALESCE(major_party_type, accident_party_type)
WHERE major_party_type IS NULL;

ALTER TABLE IF EXISTS knia_reference_documents
  ADD COLUMN IF NOT EXISTS chart_no text,
  ADD COLUMN IF NOT EXISTS major_party_type text,
  ADD COLUMN IF NOT EXISTS scenario_type text,
  ADD COLUMN IF NOT EXISTS scenario_subtype text,
  ADD COLUMN IF NOT EXISTS chunk_type text,
  ADD COLUMN IF NOT EXISTS page_start int,
  ADD COLUMN IF NOT EXISTS page_end int,
  ADD COLUMN IF NOT EXISTS review_required boolean DEFAULT false;

ALTER TABLE IF EXISTS knia_reference_chunks
  ADD COLUMN IF NOT EXISTS chart_no text,
  ADD COLUMN IF NOT EXISTS major_party_type text,
  ADD COLUMN IF NOT EXISTS scenario_type text,
  ADD COLUMN IF NOT EXISTS review_required boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_knia_fault_charts_chart_no
ON knia_fault_charts(chart_no);

CREATE INDEX IF NOT EXISTS idx_knia_fault_charts_major_party
ON knia_fault_charts(major_party_type);

CREATE INDEX IF NOT EXISTS idx_knia_fault_charts_scenario_type
ON knia_fault_charts(scenario_type);

CREATE INDEX IF NOT EXISTS idx_knia_fault_charts_party_scenario
ON knia_fault_charts(major_party_type, scenario_type);

CREATE INDEX IF NOT EXISTS idx_knia_reference_documents_chart_no
ON knia_reference_documents(chart_no);

CREATE INDEX IF NOT EXISTS idx_knia_reference_documents_party_scenario
ON knia_reference_documents(major_party_type, scenario_type);

CREATE INDEX IF NOT EXISTS idx_knia_reference_chunks_chart_no
ON knia_reference_chunks(chart_no);

CREATE INDEX IF NOT EXISTS idx_knia_reference_chunks_party_scenario
ON knia_reference_chunks(major_party_type, scenario_type);
