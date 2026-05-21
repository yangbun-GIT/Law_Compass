CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS knia_ranking_items (
  id BIGSERIAL PRIMARY KEY,
  source_category TEXT NOT NULL,
  accident_party_type TEXT NOT NULL,
  rank INTEGER NOT NULL,
  chart_no TEXT NOT NULL,
  title TEXT NOT NULL,
  search_count INTEGER,
  percentage NUMERIC(6,2),
  source_url TEXT NOT NULL DEFAULT 'https://accident.knia.or.kr/ranking',
  chart_url TEXT,
  raw JSONB NOT NULL DEFAULT '{}'::jsonb,
  collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(source_category, rank, chart_no)
);

CREATE INDEX IF NOT EXISTS idx_knia_ranking_items_source_category ON knia_ranking_items(source_category);
CREATE INDEX IF NOT EXISTS idx_knia_ranking_items_party_type ON knia_ranking_items(accident_party_type);
CREATE INDEX IF NOT EXISTS idx_knia_ranking_items_chart_no ON knia_ranking_items(chart_no);
CREATE INDEX IF NOT EXISTS idx_knia_ranking_items_title ON knia_ranking_items USING gin(to_tsvector('simple', title));
CREATE INDEX IF NOT EXISTS idx_knia_ranking_items_collected_at ON knia_ranking_items(collected_at DESC);
