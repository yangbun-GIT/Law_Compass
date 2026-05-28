from __future__ import annotations

from app.services.dynamic_questionnaire import build_dynamic_questionnaire


def test_car_vs_person_worker_questionnaire_uses_worker_fact_keys() -> None:
    questionnaire = build_dynamic_questionnaire(
        scenario_type="pedestrian_road_work_worker_accident",
        accident_party_type="car_vs_person",
        analysis_mode="fault_ratio_focused",
        structured_facts={"accident_party_type": "car_vs_person", "pedestrian_worker": True},
    )

    fact_keys = [question["fact_key"] for question in questionnaire["questions"]]
    assert fact_keys[:5] == [
        "pedestrian_role",
        "pedestrian_worker",
        "pedestrian_location",
        "pedestrian_sudden_entry",
        "road_work_safety_measures",
    ]
    assert "driver_visibility_of_pedestrian" in fact_keys


def test_car_vs_car_lane_change_questionnaire_is_not_replaced_by_person_questions() -> None:
    questionnaire = build_dynamic_questionnaire(
        scenario_type="lane_change_collision",
        accident_party_type="car_vs_car",
        analysis_mode="fault_ratio_focused",
        structured_facts={"accident_party_type": "car_vs_car"},
    )

    fact_keys = {question["fact_key"] for question in questionnaire["questions"]}
    assert "lane_change_actor" in fact_keys
    assert "turn_signal" in fact_keys
    assert "pedestrian_role" not in fact_keys
