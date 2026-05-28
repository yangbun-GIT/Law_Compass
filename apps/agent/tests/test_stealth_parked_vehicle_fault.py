from app.services.input_normalizer import normalize_analysis_input
from app.services.scenario_classifier import classify_scenario
from app.services.analysts.fault_ratio_analyst import analyze_fault_ratio


def test_stealth_parked_truck_is_not_50_50():
    text = "늦은 밤 교량 밑에 스텔스로 주차해둔 트럭과 부딪혀서 승용차 앞이 완전 파손됐다. 앞차는 음주운전으로 인해 화단에 스텔스 주차가 된 상태였다."
    normalized = normalize_analysis_input(text)
    facts = normalized["structured_facts"]

    scenario = classify_scenario(normalized["merged_text"], facts, normalized["selected_keywords"])
    assert scenario["scenario_type"] == "stealth_illegal_parked_vehicle_collision"

    result = analyze_fault_ratio(
        scenario_type=scenario["scenario_type"],
        facts=facts,
        evidence=[],
        text=normalized["merged_text"],
    )

    assert result["my"] <= 20
    assert result["other"] >= 80
    assert result["fault_estimate_source"] == "stealth_illegal_parked_vehicle_rule"