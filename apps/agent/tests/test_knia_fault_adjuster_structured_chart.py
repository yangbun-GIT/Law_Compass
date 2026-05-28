from __future__ import annotations

from app.services.knia.knia_fault_adjuster import calculate_fault_from_structured_chart


def test_structured_chart_calculates_base_and_confirmed_adjustments():
    chart = {
        "chart_no": "차43",
        "title": "진로변경 사고",
        "major_party_type": "car_vs_car",
        "scenario_type": "lane_change_collision",
        "base_fault": {"candidates": [{"A": 30, "B": 70}]},
        "adjustments": [{"label": "B 진로변경 신호불이행", "fact_key": "turn_signal", "delta_b": 10}],
        "review_required": False,
        "parsing_confidence": 0.92,
    }

    result = calculate_fault_from_structured_chart(chart, {"turn_signal": True})

    assert result["base_fault"] == {"A": 30, "B": 70}
    assert result["final_fault"] == {"A": 20, "B": 80}
    assert result["selected_adjustments"]
    assert result["reference_only"] is False
    assert result["policy"]["llm_must_not_generate_fault_numbers"] is True


def test_unknown_adjustment_creates_conditional_outcome():
    chart = {
        "chart_no": "차41",
        "title": "안전거리미확보 추돌",
        "major_party_type": "car_vs_car",
        "scenario_type": "rear_end_collision",
        "base_fault": {"candidates": [{"A": 100, "B": 0}]},
        "adjustments": [{"label": "B 제동등화의 고장", "fact_key": "brake_light_fault", "delta_b": 20}],
        "review_required": False,
        "parsing_confidence": 0.9,
    }

    result = calculate_fault_from_structured_chart(chart, {"brake_light_fault": "unknown"})

    assert result["final_fault"] == {"A": 100, "B": 0}
    assert result["unknown_adjustments"]
    assert result["conditional_outcomes"]


def test_review_required_chart_is_reference_only_low_confidence():
    chart = {
        "chart_no": "차43",
        "title": "진로변경 사고",
        "major_party_type": "car_vs_car",
        "scenario_type": "lane_change_collision",
        "base_fault": {"candidates": [{"A": 30, "B": 70}]},
        "adjustments": [],
        "review_required": True,
        "parsing_confidence": 0.68,
    }

    result = calculate_fault_from_structured_chart(chart, {})

    assert result["reference_only"] is True
    assert result["review_required"] is True
    assert result["confidence"] <= 0.45
