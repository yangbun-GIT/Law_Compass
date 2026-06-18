-- Fast path for KNIA chart/detail lookup.
-- PostgreSQL B-tree indexes are used for exact and ordered lookups; this is the
-- database-side B+tree-style acceleration layer paired with Redis response caches.

CREATE INDEX IF NOT EXISTS idx_knia_fault_charts_chart_type_updated
ON knia_fault_charts(chart_no, chart_type, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_knia_fault_charts_party_scenario_chart
ON knia_fault_charts(major_party_type, scenario_type, chart_no, chart_type);

CREATE INDEX IF NOT EXISTS idx_knia_fault_charts_accident_party_scenario_chart
ON knia_fault_charts(accident_party_type, scenario_type, chart_no, chart_type);

CREATE INDEX IF NOT EXISTS idx_knia_ranking_items_party_rank_chart
ON knia_ranking_items(accident_party_type, rank, chart_no, chart_type);

CREATE INDEX IF NOT EXISTS idx_knia_ranking_items_source_rank_chart
ON knia_ranking_items(source_category, rank, chart_no, chart_type);

CREATE INDEX IF NOT EXISTS idx_knia_ranking_items_chart_type_collected
ON knia_ranking_items(chart_no, chart_type, collected_at DESC, rank);

CREATE INDEX IF NOT EXISTS idx_knia_adjustment_factors_chart_order
ON knia_adjustment_factors(chart_no, chart_type, factor_order, id);

CREATE INDEX IF NOT EXISTS idx_knia_ref_sections_chart_type_order
ON knia_chart_reference_sections(chart_no, chart_type, section_type, item_order, id);

CREATE INDEX IF NOT EXISTS idx_knia_reference_documents_chart_party
ON knia_reference_documents(chart_no, major_party_type, scenario_type);

CREATE INDEX IF NOT EXISTS idx_knia_reference_chunks_chart_party
ON knia_reference_chunks(chart_no, major_party_type, scenario_type);
