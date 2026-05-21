from app.services.evidence_quality_gate import evaluate_evidence_quality
from app.services.static_legal_fallback import retrieve_static_legal_chunks


def test_static_fallback_returns_bicycle_specific_evidence():
    items = retrieve_static_legal_chunks("자전거를 타고 가다가 차량과 충돌했습니다 차대 자전거", limit=4)

    assert any("bicycle" in item.get("scenario_tags", []) for item in items)
    assert any("자전거" in item["title"] for item in items)


def test_bicycle_static_support_improves_scenario_relevance():
    legal_items = retrieve_static_legal_chunks("자전거 차량 충돌 차대 자전거", limit=4)
    evidence = [
        *legal_items,
        {
            "source_type": "knia_base_fault",
            "title": "KNIA 차대 자전거 기준",
            "scenario_tags": ["bicycle"],
            "score": 0.4,
        },
    ]

    coverage = evaluate_evidence_quality(
        scenario_type="bicycle_collision",
        evidence=evidence,
        missing_fields=[],
    )

    assert coverage["coverage_level"] in {"medium", "high"}
    assert coverage["scenario_relevant_count"] >= 2
    assert "scenario_relevant_evidence" not in coverage["missing_requirements"]
