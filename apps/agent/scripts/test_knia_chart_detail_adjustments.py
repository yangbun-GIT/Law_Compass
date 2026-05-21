from __future__ import annotations

import json
import sys
from typing import Any

import psycopg
import psycopg.rows

from app.services.knia.knia_collector import KniaCollector
from app.services.knia.knia_fault_adjuster import estimate_knia_fault
from app.services.knia.knia_repository import DB_URL


def fetch_one_chart() -> tuple[str, str]:
    with psycopg.connect(DB_URL) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        for chart_no in ["거41-1", "차43-2", "보13"]:
            cur.execute("SELECT chart_no, COALESCE(chart_type, '1') AS chart_type FROM knia_ranking_items WHERE chart_no=%s LIMIT 1", (chart_no,))
            row = cur.fetchone()
            if row:
                return str(row["chart_no"]), str(row["chart_type"])
        cur.execute("SELECT chart_no, COALESCE(chart_type, '1') AS chart_type FROM knia_ranking_items ORDER BY rank ASC LIMIT 1")
        row = cur.fetchone()
        if not row:
            raise AssertionError("knia_ranking_items is empty")
        return str(row["chart_no"]), str(row["chart_type"])


def db_counts(chart_no: str, chart_type: str) -> dict[str, Any]:
    with psycopg.connect(DB_URL) as conn, conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute("SELECT base_fault_a, base_fault_b, adjustment_factors, related_laws, case_references FROM knia_fault_charts WHERE chart_no=%s AND chart_type=%s", (chart_no, chart_type))
        chart = cur.fetchone()
        cur.execute("SELECT COUNT(*) AS cnt FROM knia_adjustment_factors WHERE chart_no=%s AND chart_type=%s", (chart_no, chart_type))
        factors = int(cur.fetchone()["cnt"])
        cur.execute("SELECT section_type, COUNT(*) AS cnt FROM knia_chart_reference_sections WHERE chart_no=%s AND chart_type=%s GROUP BY section_type", (chart_no, chart_type))
        sections = {str(r["section_type"]): int(r["cnt"]) for r in cur.fetchall()}
        return {"chart": dict(chart) if chart else None, "factor_count": factors, "sections": sections}


def main() -> None:
    collector = KniaCollector()
    ranking = collector.collect_ranking()
    assert ranking.get("ranking_count", 0) > 0, ranking
    chart_no, chart_type = fetch_one_chart()
    detail = collector.collect_chart_detail(chart_no, chart_type)
    assert detail["ok"], detail
    counts = db_counts(chart_no, chart_type)
    assert counts["chart"], counts
    assert counts["chart"].get("base_fault_a") is not None or counts["chart"].get("base_fault_b") is not None, counts
    assert counts["factor_count"] >= 0, counts
    assert "adjustment_explanation" in counts["sections"] or "related_law" in counts["sections"] or "case_reference" in counts["sections"], counts
    estimate = estimate_knia_fault(
        chart_no=chart_no,
        chart_type=chart_type,
        description_text="밤에 자전거가 도로를 횡단하다가 정상 주행 중인 차량과 충돌했습니다.",
        selected_keywords=["야간", "자전거", "횡단"],
        structured_facts={"light_condition": "night", "bicycle_crossing": True},
        video_metadata={"objects": ["bicycle", "car"], "light_condition": "night"},
    )
    assert estimate["final_fault"]["A"] + estimate["final_fault"]["B"] == 100, estimate
    factor_labels = {f["label"] for f in KniaCollector().repo.get_chart_adjustments(chart_no, chart_type)}
    for selected in estimate.get("selected_adjustments", []):
        assert selected["label"] in factor_labels, selected
    print(json.dumps({"ranking": ranking, "detail": detail, "counts": counts, "estimate": estimate}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"TEST_FAILED: {exc}", file=sys.stderr)
        raise
