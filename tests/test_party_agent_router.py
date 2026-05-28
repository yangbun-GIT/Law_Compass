from app.services.party_agents.router import route_party_agent


def test_vehicle_rear_end_routes_to_car_vs_car_first():
    result = route_party_agent(
        description_text="빨간불 신호대기 중 정차해 있었는데 뒤차가 추돌했다.",
        structured_facts={},
        selected_keywords=[],
        video_metadata={},
    )

    assert result["major_party_type"] == "car_vs_car"
    assert result["scenario_type"] == "rear_end_collision"
    assert result["facts_patch"]["collision_partner_type"] == "vehicle"
    assert "car_vs_person" in result["excluded_party_types"]
    assert "car_vs_bicycle" in result["excluded_party_types"]


def test_direct_bicycle_collision_routes_only_when_direct_collision_is_textual():
    result = route_party_agent(
        description_text="자전거와 직접 충돌했다.",
        structured_facts={},
        selected_keywords=[],
        video_metadata={},
    )

    assert result["major_party_type"] == "car_vs_bicycle"
    assert result["scenario_type"] == "bicycle_collision"


def test_user_party_wins_but_high_confidence_video_conflict_is_marked():
    result = route_party_agent(
        description_text="상대 차량과 충돌했습니다.",
        structured_facts={"accident_party_type": "car_vs_car"},
        selected_keywords=[],
        video_metadata={
            "fact_patch": {"direct_collision_partner_type": "pedestrian"},
            "accepted_observations": [
                {"field": "direct_collision_partner_type", "value": "pedestrian", "confidence": 0.95}
            ],
        },
    )

    assert result["major_party_type"] == "car_vs_car"
    assert result["facts_patch"]["party_conflict"]["status"] == "party_conflict_video_high_confidence"
