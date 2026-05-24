from app.services.keyword_recommender import recommend_keywords, suggest_next_inputs
from app.services.knia.taxonomy import infer_party_type_from_text
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


def test_fact_values_expand_retrieval_terms():
    terms = scenario_search_terms(
        scenario_type="rear_end_collision",
        scenario_tags=["rear_end"],
        facts={
            "stopped": True,
            "opponent_behavior": "rear_collision",
            "damage_level": "minor_rear_bumper_damage",
        },
        selected_keywords=[],
        max_terms=40,
    )

    assert "정차 차량 추돌" in terms
    assert "후방 범퍼 파손" in terms


def test_reference_guidance_fact_values_expand_terms():
    terms = scenario_search_terms(
        scenario_type="parking_or_stopped_vehicle_accident",
        scenario_tags=["stopped_vehicle", "centerline"],
        facts={
            "centerline_crossed": True,
            "secondary_collision": True,
            "stopped_vehicle_without_lights": True,
            "reported_speed_kmh": 141,
            "speed_limit_kmh": 100,
            "fatality": True,
        },
        selected_keywords=[],
        max_terms=40,
    )

    assert "centerline obstacle avoidance" in terms
    assert "secondary collision" in terms
    assert "unlit stopped vehicle" in terms
    assert "avoidability analysis" in terms
    assert "criminal civil liability split" in terms


def test_bicycle_trigger_expands_terms():
    terms = scenario_search_terms(
        scenario_type="bicycle_collision",
        scenario_tags=["bicycle", "rear_end"],
        facts={
            "bicycle_involved": True,
            "possible_trigger_vehicle": "bicycle",
            "time_gap_sec": 4,
            "sudden_brake": True,
        },
        selected_keywords=[],
    )

    assert "non-contact bicycle trigger" in terms
    assert "reaction time gap" in terms


def test_lane_change_actor_expands_directional_terms():
    opponent_terms = scenario_search_terms(
        scenario_type="lane_change_collision",
        scenario_tags=["lane_change"],
        facts={"lane_change_actor": "opponent"},
        selected_keywords=[],
    )
    user_terms = scenario_search_terms(
        scenario_type="lane_change_collision",
        scenario_tags=["lane_change"],
        facts={"lane_change_actor": "user"},
        selected_keywords=[],
    )

    assert "상대 차량 차선변경" in opponent_terms
    assert "내 차량 차선변경" in user_terms


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


def test_crosswalk_rear_end_is_classified_as_rear_end():
    scenario = classify_scenario(
        "우회전 중 횡단보도 앞에서 정차한 앞차를 뒤에서 추돌했습니다.",
        {"crosswalk_nearby": True, "stopped": True},
        [],
    )
    assert scenario["scenario_type"] == "rear_end_collision"
    assert "crosswalk" in scenario["scenario_tags"]


def test_intersection_crosswalk_without_pedestrian_stays_car_vs_car():
    scenario = classify_scenario(
        "intersection crosswalk area left-turn vehicle and straight vehicle collision",
        {"crosswalk_nearby": True, "intersection": True, "pedestrian": False},
        [],
    )

    assert scenario["accident_party_type"] == "car_vs_car"
    assert scenario["scenario_type"] != "pedestrian_crosswalk_accident"
    assert "crosswalk" in scenario["scenario_tags"]


def test_centerline_obstruction_context_is_car_vs_car():
    scenario = classify_scenario(
        "two-way one-lane road, yellow centerline crossed because of illegally parked vehicle and oncoming car collision",
        {
            "centerline_crossed": True,
            "centerline_cross_reason": "parked_vehicle_obstruction",
            "illegal_parking_obstruction": True,
            "opposing_vehicle_present": True,
        },
        [],
    )

    assert scenario["accident_party_type"] == "car_vs_car"
    assert scenario["scenario_type"] == "parking_or_stopped_vehicle_accident"
    assert "road_obstruction" in scenario["scenario_tags"]
    assert "oncoming_vehicle" in scenario["scenario_tags"]


def test_crosswalk_text_without_pedestrian_does_not_infer_car_vs_person():
    party = infer_party_type_from_text(
        "intersection crosswalk car-to-car crash",
        {"crosswalk_nearby": True, "intersection": True},
    )

    assert party == "car_vs_car"


def test_collision_partner_type_drives_party_before_environment_context():
    vehicle_party = infer_party_type_from_text(
        "crosswalk is visible near intersection",
        {"crosswalk_nearby": True, "collision_partner_type": "vehicle"},
    )
    pedestrian_party = infer_party_type_from_text(
        "intersection area",
        {"collision_partner_type": "pedestrian"},
    )

    assert vehicle_party == "car_vs_car"
    assert pedestrian_party == "car_vs_person"


def test_unlit_stopped_vehicle_is_classified_as_stopped_vehicle_case():
    scenario = classify_scenario(
        "야간에 등화 없이 정차한 차량을 추돌했습니다.",
        {"stopped_vehicle_without_lights": True, "light_condition": "night"},
        [],
    )
    assert scenario["scenario_type"] == "parking_or_stopped_vehicle_accident"
    assert "visibility" in scenario["scenario_tags"]
