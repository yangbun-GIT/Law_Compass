from app.services.evidence_quality_gate import evaluate_evidence_quality


def test_rear_end_evidence_matches_scenario_profile():
    result = evaluate_evidence_quality(
        scenario_type="rear_end_collision",
        missing_fields=[],
        evidence=[
            {
                "chunk_id": "law-safe-distance",
                "title": "도로교통법 안전거리 확보",
                "law_name": "도로교통법",
                "plain_summary": "뒤차는 앞차와 안전거리를 유지해야 하며 후방 추돌 위험을 피해야 합니다.",
                "score": 0.4,
            },
            {
                "source_type": "knia_base_fault",
                "title": "KNIA 차41-1 후방 추돌 기준",
                "scenario_tags": ["rear_end"],
                "score": 0.45,
            },
        ],
    )

    assert result["coverage_level"] == "medium"
    assert result["decision_ready"] is False
    assert result["scenario_relevant_count"] == 2
    assert result["evidence_family_counts"]["legal"] == 1
    assert result["evidence_family_counts"]["knia"] == 1
    assert result["missing_requirements"] == ["total_evidence"]


def test_complete_rear_end_evidence_is_high_coverage():
    result = evaluate_evidence_quality(
        scenario_type="rear_end_collision",
        missing_fields=[],
        evidence=[
            {"chunk_id": "law-safe-distance", "scenario_tags": ["rear_end", "safe_distance"], "score": 0.4},
            {"chunk_id": "law-duty", "scenario_tags": ["rear_end"], "score": 0.36},
            {"source_type": "knia_base_fault", "title": "KNIA rear-end base fault", "scenario_tags": ["rear_end"], "score": 0.42},
            {"source_type": "knia_chart", "title": "KNIA safe distance chart", "scenario_tags": ["safe_distance"], "score": 0.39},
        ],
    )

    assert result["coverage_level"] == "high"
    assert result["decision_ready"] is True
    assert result["scenario_relevant_count"] == 4
    assert result["missing_evidence_families"] == []
    assert result["missing_requirements"] == []


def test_unrelated_evidence_is_not_treated_as_signal_support():
    result = evaluate_evidence_quality(
        scenario_type="intersection_signal_violation",
        missing_fields=[],
        evidence=[
            {
                "chunk_id": "law-lane-change",
                "title": "진로변경 방법",
                "law_name": "도로교통법",
                "plain_summary": "차선변경 차량은 방향지시등을 사용해야 합니다.",
                "score": 0.5,
            }
        ],
    )

    assert result["coverage_level"] == "low"
    assert result["scenario_relevant_count"] == 0
    assert "scenario_relevant_evidence" in result["missing_requirements"]
    assert "사고 유형과 직접 맞는 근거 신호를 확인하지 못했습니다." in result["weak_points"]


def test_no_evidence_is_low_coverage():
    result = evaluate_evidence_quality(
        scenario_type="bicycle_collision",
        missing_fields=[],
        evidence=[],
    )

    assert result["coverage_level"] == "low"
    assert result["scenario_relevant_count"] == 0
    assert result["missing_evidence_families"] == ["legal", "knia"]
    assert "total_evidence" in result["missing_requirements"]
