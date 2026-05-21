ALTER TABLE IF EXISTS knia_fault_charts
ADD COLUMN IF NOT EXISTS source_detail_url TEXT,
ADD COLUMN IF NOT EXISTS accident_explanation TEXT,
ADD COLUMN IF NOT EXISTS accident_situation_lines JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS applied_fault_a INTEGER,
ADD COLUMN IF NOT EXISTS applied_fault_b INTEGER,
ADD COLUMN IF NOT EXISTS adjustment_factors JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS adjustment_explanations JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS related_laws JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS case_references JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS raw_detail JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS raw_html_hash TEXT,
ADD COLUMN IF NOT EXISTS detail_collected_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS knia_adjustment_factors (
  id BIGSERIAL PRIMARY KEY,
  chart_no TEXT NOT NULL,
  chart_type TEXT NOT NULL DEFAULT '1',
  source_case_id TEXT DEFAULT 'case1',
  factor_order INTEGER NOT NULL DEFAULT 0,
  label TEXT NOT NULL,
  condition_code TEXT,
  checkbox_value TEXT,
  delta_a INTEGER NOT NULL DEFAULT 0,
  delta_b INTEGER NOT NULL DEFAULT 0,
  raw JSONB NOT NULL DEFAULT '{}'::jsonb,
  source_detail_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(chart_no, chart_type, source_case_id, factor_order, label)
);

CREATE INDEX IF NOT EXISTS idx_knia_adjustment_factors_chart
ON knia_adjustment_factors(chart_no, chart_type);

CREATE INDEX IF NOT EXISTS idx_knia_adjustment_factors_label
ON knia_adjustment_factors(label);

CREATE TABLE IF NOT EXISTS knia_chart_reference_sections (
  id BIGSERIAL PRIMARY KEY,
  chart_no TEXT NOT NULL,
  chart_type TEXT NOT NULL DEFAULT '1',
  section_type TEXT NOT NULL,
  title TEXT,
  body TEXT,
  law_title TEXT,
  law_text TEXT,
  case_title TEXT,
  case_body TEXT,
  decision_summary TEXT,
  item_order INTEGER NOT NULL DEFAULT 0,
  source_detail_url TEXT,
  raw JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_knia_ref_sections_unique
ON knia_chart_reference_sections(
  chart_no,
  chart_type,
  section_type,
  item_order,
  COALESCE(title, ''),
  COALESCE(law_title, ''),
  COALESCE(case_title, '')
);

CREATE INDEX IF NOT EXISTS idx_knia_ref_sections_chart
ON knia_chart_reference_sections(chart_no, chart_type);

CREATE INDEX IF NOT EXISTS idx_knia_ref_sections_type
ON knia_chart_reference_sections(section_type);

CREATE INDEX IF NOT EXISTS idx_knia_ref_sections_law_title
ON knia_chart_reference_sections(law_title);

CREATE INDEX IF NOT EXISTS idx_knia_ref_sections_body
ON knia_chart_reference_sections
USING gin(to_tsvector('simple', COALESCE(body, '') || ' ' || COALESCE(law_text, '') || ' ' || COALESCE(case_body, '')));

ALTER TABLE IF EXISTS analysis_results
ADD COLUMN IF NOT EXISTS knia_applied_adjustments JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS knia_base_fault JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS knia_final_fault JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS knia_adjustment_reason TEXT,
ADD COLUMN IF NOT EXISTS knia_reference_evidence JSONB DEFAULT '[]'::jsonb;
