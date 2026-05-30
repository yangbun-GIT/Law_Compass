from app.services.orchestrator import analyze_case


def _primary_axis(result):
    primary = result.get("knia_primary_match") or {}
    return {
        "chart_no": primary.get("chart_no"),
        "scenario_type": primary.get("scenario_type"),
        "party": primary.get("accident_party_type"),
    }


def _evidence_text(result):
    return " ".join(str(item) for item in (result.get("evidence") or [])[:16]).lower()


def test_new_red_light_waiting_rear_end_keeps_rear_end_axis():
    result = analyze_case(
        "교차로 빨간불 신호대기 중 정차해 있었는데 뒤차가 그대로 추돌했습니다.",
        structured_facts={
            "accident_type": "intersection_signal_violation",
            "accident_party_type": "car_vs_car",
            "stopped_due_to_signal": True,
            "stopped_at_red_light": True,
            "stopped": True,
            "opponent_behavior": "rear_collision",
            "collision_partner_type": "vehicle",
        },
        analysis_mode="fault_ratio",
    )

    primary = _primary_axis(result)
    assert result["scenario_type"] == "rear_end_collision"
    assert result["accident_party_type"] == "car_vs_car"
    assert result["fault_ratio"]["my"] <= 10
    assert primary["scenario_type"] in {None, "rear_end_collision"}
    assert not (primary["chart_no"] or "").startswith(("차12", "차16", "차43"))


def test_unlit_stopped_vehicle_speeding_does_not_use_lane_change_knia_axis():
    result = analyze_case(
        "고속도로에서 등화 없이 정차해 있던 차량을 뒤늦게 보고 충돌했습니다. 제한속도는 100이고 제 속도는 141 정도였습니다.",
        structured_facts={
            "accident_party_type": "car_vs_car",
            "is_stealth_parked_vehicle_collision": True,
            "stopped_vehicle_without_lights": True,
            "reported_speed_kmh": 141,
            "speed_limit_kmh": 100,
            "collision_partner_type": "vehicle",
        },
        analysis_mode="fault_ratio",
    )

    primary = _primary_axis(result)
    assert result["scenario_type"] == "stealth_illegal_parked_vehicle_collision"
    assert result["fault_ratio"]["my"] == 40
    assert result["fault_ratio"]["other"] == 60
    assert primary["scenario_type"] != "lane_change_collision"
    assert not (primary["chart_no"] or "").startswith("차43")


def test_centerline_obstacle_collision_does_not_use_lane_change_or_rear_end_primary():
    result = analyze_case(
        "왕복 2차로에서 불법 주정차 차량을 피해 중앙선을 일부 넘어 정차했고 마주오던 차량이 멈추지 않아 충돌했습니다.",
        structured_facts={
            "accident_party_type": "car_vs_car",
            "centerline_crossed": True,
            "road_obstruction": True,
            "illegal_parking_obstruction": True,
            "opposing_vehicle_present": True,
            "stopped": True,
            "opponent_failed_to_slow": True,
            "collision_partner_type": "vehicle",
        },
        analysis_mode="fault_ratio",
    )

    primary = _primary_axis(result)
    assert result["scenario_type"] == "centerline_obstacle_collision"
    assert result["fault_ratio"]["fault_estimate_source"] == "contextual_complex_case"
    assert primary["scenario_type"] not in {"lane_change_collision", "rear_end_collision"}
    assert not (primary["chart_no"] or "").startswith(("차41", "차42", "차43"))


def test_intersection_vehicle_collision_with_visible_pedestrian_stays_vehicle_axis():
    result = analyze_case(
        "교차로에서 좌회전 중 직진 차량과 충돌했습니다. 횡단보도와 보행자가 주변에 보였지만 사람과 부딪힌 사고는 아닙니다.",
        structured_facts={
            "accident_party_type": "car_vs_car",
            "intersection": True,
            "ego_turn_direction": "left",
            "opponent_behavior": "straight_vehicle",
            "crosswalk_nearby": True,
            "pedestrian_visible": True,
            "collision_partner_type": "vehicle",
            "direct_collision_partner_type": "vehicle",
        },
        analysis_mode="fault_ratio",
    )

    primary = _primary_axis(result)
    evidence_text = _evidence_text(result)
    assert result["accident_party_type"] == "car_vs_car"
    assert result["scenario_type"] in {"intersection_collision", "intersection_signal_violation"}
    assert primary["party"] in {None, "car_vs_car"}
    assert primary["scenario_type"] != "lane_change_collision"
    assert "pedestrian_crosswalk_accident" not in evidence_text
    assert "school_zone_child_accident" not in evidence_text
