from __future__ import annotations

from app.services.knia import knia_matcher


def _chart(chart_no: str, party: str, scenario: str) -> dict:
    return {
        "id": f"test-{chart_no}",
        "chart_no": chart_no,
        "chart_type": "1",
        "title": f"{chart_no} 기준",
        "major_party_type": party,
        "scenario_type": scenario,
        "scenario_subtype": "fixture",
        "base_fault": {"candidates": [{"A": 30, "B": 70}]},
        "adjustments": [],
        "accident_situation": "구조화 사고 상황",
        "base_fault_explanation": "구조화 기본과실 설명",
        "review_required": False,
        "parsing_confidence": 0.91,
    }


def test_matcher_prefers_structured_chart_before_legacy_lookup(monkeypatch):
    monkeypatch.setattr(knia_matcher, "search_knia_fault_charts", lambda *args, **kwargs: [_chart("차43", "car_vs_car", "lane_change_collision")])

    result = knia_matcher.match_knia_charts(
        description_text="상대 차량이 차선변경하다 충돌",
        structured_facts={"accident_party_type": "car_vs_car"},
        selected_keywords=[],
        scenario_type="lane_change_collision",
        accident_party_type="car_vs_car",
    )

    assert result["structured_chart_used"] is True
    assert result["chart_no"] == "차43"
    assert result["items"][0]["structured_chart_used"] is True
    assert result["items"][0]["major_party_type"] == "car_vs_car"
    assert result["items"][0]["review_required"] is False


def test_car_vs_car_structured_search_rejects_person_and_bicycle(monkeypatch):
    monkeypatch.setattr(
        knia_matcher,
        "search_knia_fault_charts",
        lambda *args, **kwargs: [
            _chart("보1", "car_vs_person", "pedestrian_accident"),
            _chart("거41", "car_vs_bicycle", "bicycle_collision"),
            _chart("차43", "car_vs_car", "lane_change_collision"),
        ],
    )

    result = knia_matcher.match_knia_charts(
        description_text="차대차 차선변경 사고",
        structured_facts={"accident_party_type": "car_vs_car"},
        selected_keywords=["자전거"],
        scenario_type="lane_change_collision",
        accident_party_type="car_vs_car",
    )

    assert [item["chart_no"] for item in result["items"]] == ["차43"]
    assert result["rejected_mismatch_count"] == 2


def test_bicycle_and_person_parties_prioritize_matching_prefix(monkeypatch):
    monkeypatch.setattr(knia_matcher, "search_knia_fault_charts", lambda party, *_args, **_kwargs: [_chart("거41" if party == "car_vs_bicycle" else "보1", party, "fixture")])

    bicycle = knia_matcher.match_knia_charts(
        description_text="자전거와 직접 충돌",
        structured_facts={"accident_party_type": "car_vs_bicycle"},
        selected_keywords=[],
        scenario_type="bicycle_collision",
        accident_party_type="car_vs_bicycle",
    )
    person = knia_matcher.match_knia_charts(
        description_text="횡단보도에서 보행자와 충돌",
        structured_facts={"accident_party_type": "car_vs_person"},
        selected_keywords=[],
        scenario_type="pedestrian_crosswalk_accident",
        accident_party_type="car_vs_person",
    )

    assert bicycle["items"][0]["chart_no"].startswith("거")
    assert person["items"][0]["chart_no"].startswith("보")
