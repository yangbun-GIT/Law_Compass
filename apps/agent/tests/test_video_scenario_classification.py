from app.services.scenario_classifier import classify_scenario


def test_non_contact_bicycle_trigger_remains_vehicle_rear_end_context():
    result = classify_scenario(
        "자전거를 피하려고 멈춘 뒤 뒤에서 오던 버스가 추돌했습니다.",
        {
            "non_contact_trigger": True,
            "trigger_actor_type": "bicycle",
            "direct_collision_partner_type": "vehicle",
            "rear_vehicle_collision": True,
            "collision_partner_type": "vehicle",
        },
        [],
    )

    assert result["scenario_type"] == "rear_end_collision"
    assert result["accident_party_type"] == "car_vs_car"
    assert "non_contact_trigger" in result["scenario_tags"]
    assert "bicycle" in result["scenario_tags"]
