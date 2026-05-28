from __future__ import annotations

from app.services.dynamic_questionnaire import build_dynamic_questionnaire
from app.services.input_normalizer import normalize_analysis_input
from app.services.knia.knia_matcher import match_knia_charts
from app.services.scenario_classifier import classify_scenario


WORKER_TEXT = "현재 공사를 하기 위한 공사 담당자가 도로 폭 측정을 위하여, 도로쪽의 차량을 아예 보지도 않고, 갑자기 튀어나와 발생한 사고입니다."


def test_worker_accident_normalizes_to_car_vs_person() -> None:
    normalized = normalize_analysis_input(WORKER_TEXT)
    facts = normalized["structured_facts"]

    assert facts["knia_major_party_type"] == "car_vs_person"
    assert facts["accident_party_type"] == "car_vs_person"
    assert facts["collision_partner_type"] == "pedestrian"
    assert facts["direct_collision_partner_type"] == "pedestrian"
    assert facts["direct_collision_target"] == "road_work_worker"
    assert facts["pedestrian_worker"] is True
    assert facts["road_work_context"] is True
    assert facts["pedestrian_sudden_entry"] is True


def test_worker_accident_classifier_stays_inside_person_party() -> None:
    normalized = normalize_analysis_input(WORKER_TEXT)
    scenario = classify_scenario(
        normalized["description_text"],
        normalized["structured_facts"],
        normalized["selected_keywords"],
    )

    assert scenario["accident_party_type"] == "car_vs_person"
    assert scenario["scenario_type"] in {"pedestrian_road_work_worker_accident", "pedestrian_sudden_entry_accident"}
    assert "pedestrian" in scenario["scenario_tags"]


def test_worker_accident_knia_matcher_returns_only_person_prefix() -> None:
    normalized = normalize_analysis_input(WORKER_TEXT)
    scenario = classify_scenario(
        normalized["description_text"],
        normalized["structured_facts"],
        normalized["selected_keywords"],
    )
    result = match_knia_charts(
        description_text=normalized["description_text"],
        structured_facts=normalized["structured_facts"],
        selected_keywords=["차43", "차41", "자전거"],
        scenario_type=scenario["scenario_type"],
        accident_party_type=scenario["accident_party_type"],
        limit=5,
    )

    assert result["requested_party_type"] == "car_vs_person"
    assert result["items"]
    assert all(str(item.get("chart_no") or "").startswith(("보", "蹂")) for item in result["items"])
    assert not any(str(item.get("chart_no") or "").startswith(("차", "李", "거", "자", "嫄")) for item in result["items"])


def test_worker_accident_questions_focus_on_pedestrian_worker_facts() -> None:
    normalized = normalize_analysis_input(WORKER_TEXT)
    questionnaire = build_dynamic_questionnaire(
        scenario_type="pedestrian_road_work_worker_accident",
        accident_party_type="car_vs_person",
        analysis_mode="fault_ratio_focused",
        description_text=normalized["description_text"],
        structured_facts=normalized["structured_facts"],
    )
    fact_keys = {question["fact_key"] for question in questionnaire["questions"]}

    assert "pedestrian_role" in fact_keys
    assert "pedestrian_worker" in fact_keys
    assert "pedestrian_sudden_entry" in fact_keys
    assert "road_work_safety_measures" in fact_keys
    assert "driver_visibility_of_pedestrian" in fact_keys
