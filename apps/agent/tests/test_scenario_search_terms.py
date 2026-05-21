from app.services.keyword_recommender import recommend_keywords, suggest_next_inputs
from app.services.scenario_classifier import classify_scenario
from app.services.scenario_search_terms import expand_query_text, scenario_search_terms


def test_bicycle_collision_expands_search_terms():
    terms = scenario_search_terms(
        scenario_type="bicycle_collision",
        scenario_tags=["bicycle"],
        facts={"accident_party_type": "car_vs_bicycle"},
        selected_keywords=[],
    )
    assert "자전거" in terms
    assert "차대 자전거" in terms


def test_query_expansion_preserves_original_text():
    expanded = expand_query_text(
        "교차로에서 사고가 났습니다",
        scenario_type="intersection_signal_violation",
        scenario_tags=["intersection", "signal_violation"],
        facts={},
        selected_keywords=[],
    )
    assert expanded.startswith("교차로에서 사고가 났습니다")
    assert "신호위반" in expanded


def test_recommend_keywords_covers_non_vehicle_scenarios():
    keywords = recommend_keywords(
        "object_collision",
        {"accident_party_type": "car_vs_object"},
        [],
        evidence=[],
    )
    assert "시설물 충돌" in keywords
    assert "대물배상" in keywords


def test_next_inputs_cover_parking_and_bicycle():
    parking = suggest_next_inputs({}, "parking_or_stopped_vehicle_accident", [])
    bicycle = suggest_next_inputs({}, "bicycle_collision", [])
    assert any("주차" in item or "정차" in item for item in parking)
    assert any("자전거" in item for item in bicycle)


def test_parking_text_does_not_default_to_rear_end():
    scenario = classify_scenario("주차된 차량을 출차 중 접촉했습니다", {}, [])
    assert scenario["scenario_type"] == "parking_or_stopped_vehicle_accident"
    assert scenario["accident_party_type"] == "car_vs_car"
