from __future__ import annotations

from app.services.knia import knia_matcher


def _chart(chart_no: str, party: str, scenario: str) -> dict:
    return {
        "id": f"test-{chart_no}",
        "chart_no": chart_no,
        "chart_type": "1",
        "title": f"{chart_no} 기준",
        "major_party_type": party,
        "accident_party_type": party,
        "scenario_type": scenario,
        "base_fault": {"candidates": [{"A": 30, "B": 70}]},
        "adjustments": [],
        "accident_situation": "사고 상황",
        "base_fault_explanation": "기본과실 설명",
        "review_required": False,
        "parsing_confidence": 0.9,
    }


def test_person_matcher_rejects_car_and_bicycle_charts(monkeypatch) -> None:
    monkeypatch.setattr(
        knia_matcher,
        "search_knia_fault_charts",
        lambda *args, **kwargs: [
            _chart("차43", "car_vs_car", "lane_change_collision"),
            _chart("거1", "car_vs_bicycle", "bicycle_collision"),
            _chart("보1", "car_vs_person", "pedestrian_crosswalk_accident"),
        ],
    )

    result = knia_matcher.match_knia_charts(
        description_text="교차로에서 우회전 중 보행자와 충돌했다.",
        structured_facts={"accident_party_type": "car_vs_person", "direct_collision_partner_type": "pedestrian"},
        selected_keywords=["차43", "자전거"],
        scenario_type="pedestrian_crosswalk_accident",
        accident_party_type="car_vs_person",
    )

    assert [item["chart_no"] for item in result["items"]] == ["보1"]
    assert result["rejected_mismatch_count"] == 2


def test_person_matcher_static_fallback_is_knia_family(monkeypatch) -> None:
    monkeypatch.setattr(knia_matcher, "search_knia_fault_charts", lambda *args, **kwargs: [])
    monkeypatch.setattr(knia_matcher, "list_knia_fault_charts_by_party", lambda *args, **kwargs: [])
    monkeypatch.setattr(knia_matcher, "_hybrid_lookup", lambda *args, **kwargs: [])

    result = knia_matcher.match_knia_charts(
        description_text="공사 담당자가 도로 폭 측정 중 갑자기 튀어나와 사고가 발생했다.",
        structured_facts={
            "accident_party_type": "car_vs_person",
            "direct_collision_partner_type": "pedestrian",
            "pedestrian_worker": True,
            "road_work_context": True,
        },
        selected_keywords=[],
        scenario_type="pedestrian_road_work_worker_accident",
        accident_party_type="car_vs_person",
    )

    assert result["items"]
    assert result["items"][0]["chart_no"].startswith("보")
    assert result["items"][0]["source_family"] == "knia"
    assert result["items"][0]["evidence_family"] == "knia"
    assert result["items"][0]["reference_only"] is True
    assert result["no_knia_match_reason"] is None
