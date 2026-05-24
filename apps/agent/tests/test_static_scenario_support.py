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


def test_lane_change_static_support_includes_fault_ratio_family():
    items = retrieve_static_legal_chunks("상대 차량 차선변경 진로변경 방향지시등 없이 끼어들기", limit=5)
    coverage = evaluate_evidence_quality(
        scenario_type="lane_change_collision",
        evidence=items,
        missing_fields=[],
    )

    assert any(item["chunk_id"] == "static:fault-guide:lane-change" for item in items)
    assert coverage["evidence_family_counts"]["legal"] >= 1
    assert coverage["evidence_family_counts"]["knia"] >= 1
    assert coverage["scenario_relevant_count"] >= 2
    assert "family:knia" not in coverage["missing_requirements"]


def test_pedestrian_and_school_zone_static_support_have_direct_fault_guides():
    pedestrian = retrieve_static_legal_chunks("횡단보도 보행자 보호의무 보행자 신호 사고", limit=5)
    school_zone = retrieve_static_legal_chunks("어린이보호구역 스쿨존 어린이 제한속도 사고", limit=5)

    pedestrian_coverage = evaluate_evidence_quality(
        scenario_type="pedestrian_crosswalk_accident",
        evidence=pedestrian,
        missing_fields=[],
    )
    school_coverage = evaluate_evidence_quality(
        scenario_type="school_zone_child_accident",
        evidence=school_zone,
        missing_fields=[],
    )

    assert any(item["chunk_id"] == "static:fault-guide:pedestrian-crosswalk" for item in pedestrian)
    assert any(item["chunk_id"] == "static:fault-guide:school-zone" for item in school_zone)
    assert "family:knia" not in pedestrian_coverage["missing_requirements"]
    assert "family:knia" not in school_coverage["missing_requirements"]
    assert pedestrian_coverage["scenario_relevant_count"] >= 2
    assert school_coverage["scenario_relevant_count"] >= 2


def test_static_support_returns_front_vehicle_stop_reference_for_crosswalk_rear_end():
    items = retrieve_static_legal_chunks(
        "우회전 중 횡단보도 앞 앞차 정지 사유 보행자 신호 후방추돌 급정거 안전거리",
        limit=5,
    )

    ids = {item["chunk_id"] for item in items}
    assert "static:legal:front-vehicle-stop-rear-end-duty" in ids
    assert "static:fault-guide:crosswalk-front-stop-rear-end" in ids


def test_static_support_returns_bicycle_trigger_legal_and_knia_reference():
    items = retrieve_static_legal_chunks(
        "자전거 비접촉 유발 트럭 정지 후방 버스 추돌 시간적 여유 급제동 안전거리",
        limit=5,
    )

    ids = {item["chunk_id"] for item in items}
    assert "static:legal:bicycle-trigger-rear-end-duty" in ids
    assert "static:knia:bicycle-non-contact-trigger" in ids
