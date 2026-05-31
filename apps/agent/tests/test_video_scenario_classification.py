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


def test_non_contact_motorcycle_single_fall_is_not_direct_motorcycle_collision():
    result = classify_scenario(
        "Narrow curved road. Oncoming motorcycle fell alone near the ego car. No contact with ego vehicle.",
        {
            "direct_contact_with_ego": False,
            "ego_collision_confirmed": False,
            "opponent_single_fall": True,
            "non_contact_near_miss": True,
            "opposing_motorcycle_present": True,
            "curve_road": True,
            "narrow_road": True,
            "road_width_m": 3.8,
            "ego_kept_right": True,
            "opponent_failed_keep_right": True,
        },
        [],
    )

    assert result["scenario_type"] == "narrow_curve_oncoming_motorcycle_loss_of_control"
    assert result["accident_party_type"] == "non_contact_involving_motorcycle"
    assert result["major_party_type"] == "non_contact_involving_motorcycle"
    assert "non_contact" in result["scenario_tags"]
    assert "single_fall" in result["scenario_tags"]
