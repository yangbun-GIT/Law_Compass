from app.services.conditional_judgment import build_conditional_judgment
from app.services.orchestrator import analyze_case


def _labels(packet):
    return [item["label"] for item in packet["outcomes"]]


def test_signal_unknown_intersection_splits_opponent_signal_outcomes():
    packet = build_conditional_judgment(
        scenario_type="intersection_signal_violation",
        facts={
            "intersection": True,
            "user_signal": "yellow_to_red",
            "opponent_signal_visible": False,
        },
        text="교차로 좌회전 중 황색 신호로 바뀌었고 왼쪽에서 직진 차량이 들어와 충돌했습니다.",
    )

    labels = _labels(packet)
    assert packet["status"] == "conditional"
    assert "상대 차량 신호가 녹색 또는 정상 진행 신호인 경우" in labels
    assert "상대 차량도 적색 또는 신호위반으로 진입한 경우" in labels
    assert "opponent_signal" in packet["triggers"][0]["required_facts"]


def test_centerline_unknown_reason_splits_obstacle_and_unlawful_crossing():
    packet = build_conditional_judgment(
        scenario_type="centerline_obstacle_collision",
        facts={
            "centerline_crossed": True,
            "road_obstruction": True,
            "opposing_vehicle_present": True,
        },
        text="왕복 2차로에서 중앙선을 일부 넘은 상태로 마주오던 차량과 충돌했습니다.",
    )

    labels = _labels(packet)
    assert "불법 주정차·장애물 회피가 불가피했던 경우" in labels
    assert "장애물 회피가 충분히 가능했거나 무리한 중앙선 침범인 경우" in labels


def test_rear_end_unknown_stop_reason_splits_lawful_and_unnecessary_stop():
    packet = build_conditional_judgment(
        scenario_type="rear_end_collision",
        facts={"front_vehicle_stopped": True, "collision_partner_type": "vehicle"},
        text="우회전 중 앞차가 멈춰서 뒤에서 추돌했습니다.",
    )

    labels = _labels(packet)
    assert "신호·정체·보행자 보호 등 정당한 정차인 경우" in labels
    assert "이유 없는 급정차 또는 불필요한 정차인 경우" in labels


def test_non_contact_trigger_and_secondary_collision_are_separate_conditions():
    packet = build_conditional_judgment(
        scenario_type="rear_end_collision",
        facts={
            "non_contact_trigger": True,
            "trigger_actor_type": "bicycle",
            "rear_vehicle_collision": True,
            "secondary_collision": True,
        },
        text="자전거를 보고 멈췄고 뒤차가 후방 추돌했습니다. 이후 2차 충돌도 있었습니다.",
    )

    labels = _labels(packet)
    assert "자전거·보행자·물체가 비접촉으로 사고를 유발한 경우" in labels
    assert "내 차량이 급차로변경 후 급정차한 경우" in labels
    assert "1차 충돌과 후속 추돌을 분리하는 경우" in labels


def test_analyze_case_exposes_conditional_outcomes_instead_of_flat_unknown_fallback():
    result = analyze_case(
        "교차로 좌회전 중 황색 신호로 바뀌었고 왼쪽 직진 차량과 충돌했습니다. 상대 신호는 보이지 않습니다.",
        structured_facts={
            "accident_party_type": "car_vs_car",
            "intersection": True,
            "ego_turn_direction": "left",
            "user_signal": "yellow_to_red",
            "opponent_signal_visible": False,
            "collision_partner_type": "vehicle",
            "direct_collision_partner_type": "vehicle",
        },
        analysis_mode="fault_ratio",
    )

    fault = result["fault_ratio"]
    assert result["scenario_type"] in {"intersection_signal_violation", "intersection_collision"}
    assert len(fault.get("conditional_outcomes") or []) >= 2
    assert fault.get("conditional_judgment", {}).get("status") == "conditional"
    assert not (fault["my"] == 50 and fault["other"] == 50 and not fault.get("conditional_outcomes"))
