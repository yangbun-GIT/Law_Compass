ALTER TABLE knia_ranking_items
ADD COLUMN IF NOT EXISTS chart_type TEXT DEFAULT '1',
ADD COLUMN IF NOT EXISTS source_detail_url TEXT,
ADD COLUMN IF NOT EXISTS local_chart_url TEXT,
ADD COLUMN IF NOT EXISTS source_onclick TEXT;

CREATE INDEX IF NOT EXISTS idx_knia_ranking_items_chart_type ON knia_ranking_items(chart_type);
CREATE INDEX IF NOT EXISTS idx_knia_ranking_items_source_detail_url ON knia_ranking_items(source_detail_url);
