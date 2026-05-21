from __future__ import annotations

import json
import os

import psycopg
import psycopg.rows
from app.services.knia.knia_collector import KniaCollector

DB_URL = os.getenv("DATABASE_URL", "postgresql://law:lawpass@postgres:5432/lawcompass")

if __name__ == "__main__":
    collector = KniaCollector()
    ranking = collector.collect_ranking()
    assert ranking.get("ranking_count", 0) > 0, "ranking_count가 0입니다"
    categories = ranking.get("categories") or {}
    for label in ["전체", "차대차", "차대사람", "차대자전거"]:
        assert categories.get(label, 0) > 0, f"{label} 카테고리 수집 결과가 없습니다"

    with psycopg.connect(DB_URL, row_factory=psycopg.rows.dict_row) as conn, conn.cursor() as cur:
        for party in ["all", "car_vs_car", "car_vs_person", "car_vs_bicycle"]:
            cur.execute("SELECT count(*) AS c FROM knia_ranking_items WHERE accident_party_type=%s", (party,))
            assert cur.fetchone()["c"] > 0, f"DB에 {party} ranking item이 없습니다"
        cur.execute("SELECT rank, chart_no, title, source_category, accident_party_type FROM knia_ranking_items ORDER BY updated_at DESC, rank ASC LIMIT 5")
        rows = [dict(r) for r in cur.fetchall()]
        assert rows, "ranking item sample이 없습니다"
        for row in rows:
            for key in ["rank", "chart_no", "title", "source_category", "accident_party_type"]:
                assert row.get(key) is not None, f"필수 필드 누락: {key}"

    charts = collector.collect_fault_charts(chart_nos=["차41-1", "차43-2"], max_charts=2)
    assert charts.get("collected_charts", 0) > 0
    print(json.dumps({"collector_test": "passed", "ranking": ranking, "charts": charts}, ensure_ascii=False, indent=2))

