from app.services.input_normalizer import normalize_analysis_input
from app.services.scenario_classifier import classify_scenario
from app.services.scenario_search_terms import scenario_search_terms


def test_stealth_parked_truck_forces_car_vs_car_and_removes_bicycle_pollution():
    text = (
        "눚은밤 교량 밑에 스텔스로 주차해둔 음주운전 트럭과 사고. "
        "눚은밤 교량 밑에 스텔스로 주차해둔 트럭과 부딛혀서 승용차 앞이 완전 파손. "
        "폐차처리정도가 되었다. 앞차는 음주운전으로 인해 화단에 스텔스 주차가 된 상태였가 "
        "그 차와 나의 차가 부딛힌 사고였다."
    )
    normalized = normalize_analysis_input(
        description_text=text,
        structured_facts={"possible_trigger_vehicle": "bicycle", "bicycle_involved": True},
        selected_keywords=["자전거", "과실비율"],
    )
    facts = normalized["structured_facts"]

    assert facts.get("accident_type") == "stealth_illegal_parked_vehicle_collision"
    assert facts.get("accident_party_type") == "car_vs_car"
    assert facts.get("knia_major_party_type") == "car_vs_car"
    assert facts.get("collision_partner_type") == "vehicle"
    assert "bicycle_involved" not in facts
    assert "possible_trigger_vehicle" not in facts
    assert "trigger_actor_type" not in facts
    assert "bicycle_location" not in facts
    assert "bicycle_movement" not in facts

    scenario = classify_scenario(
        normalized["description_text"],
        facts,
        normalized["selected_keywords"],
    )
    assert scenario["scenario_type"] == "stealth_illegal_parked_vehicle_collision"
    assert scenario["accident_party_type"] == "car_vs_car"
    assert "bicycle" not in scenario["scenario_tags"]

    terms = scenario_search_terms(
        scenario_type=scenario["scenario_type"],
        scenario_tags=scenario["scenario_tags"],
        facts=facts,
        selected_keywords=normalized["selected_keywords"],
        accident_party_type=scenario["accident_party_type"],
        max_terms=60,
    )
    joined = " ".join(terms).lower()
    assert "자전거" not in joined
    assert "bicycle" not in joined
    assert "cyclist" not in joined
