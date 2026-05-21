from app.services.accident_perspective import (
    BICYCLE,
    LANE_CHANGING_VEHICLE,
    SIGNAL_COMPLIANT_VEHICLE,
    SIGNAL_VIOLATION_VEHICLE,
    STRAIGHT_VEHICLE,
    VEHICLE,
    infer_user_vehicle_role,
    map_fault_ratio_to_user,
)


def test_lane_change_by_opponent_keeps_straight_vehicle_as_a():
    mapped = map_fault_ratio_to_user(
        scenario_type="lane_change_collision",
        fault={"A": 30, "B": 70},
        text="상대 차량이 갑자기 차선변경하며 끼어들어 충돌했습니다.",
        facts={},
    )
    assert mapped["user_vehicle_role"] == STRAIGHT_VEHICLE
    assert mapped["my"] == 30
    assert mapped["other"] == 70


def test_lane_change_by_user_maps_user_to_b():
    mapped = map_fault_ratio_to_user(
        scenario_type="lane_change_collision",
        fault={"A": 30, "B": 70},
        text="제가 차선변경을 하다가 직진 차량과 충돌했습니다.",
        facts={},
    )
    assert mapped["user_vehicle_role"] == LANE_CHANGING_VEHICLE
    assert mapped["my"] == 70
    assert mapped["other"] == 30


def test_opponent_signal_violation_maps_user_to_compliant_a():
    mapped = map_fault_ratio_to_user(
        scenario_type="intersection_signal_violation",
        fault={"A": 0, "B": 100},
        text="상대 차량이 빨간불에 신호위반을 해서 교차로에서 충돌했습니다.",
        facts={},
    )
    assert mapped["user_vehicle_role"] == SIGNAL_COMPLIANT_VEHICLE
    assert mapped["my"] == 0
    assert mapped["other"] == 100


def test_user_signal_violation_maps_user_to_b():
    mapped = map_fault_ratio_to_user(
        scenario_type="intersection_signal_violation",
        fault={"A": 0, "B": 100},
        text="제가 신호위반을 해서 교차로에서 정상 주행 차량과 충돌했습니다.",
        facts={},
    )
    assert mapped["user_vehicle_role"] == SIGNAL_VIOLATION_VEHICLE
    assert mapped["my"] == 100
    assert mapped["other"] == 0


def test_bicycle_user_maps_to_b_and_vehicle_default_maps_to_a():
    cyclist = map_fault_ratio_to_user(
        scenario_type="bicycle_collision",
        fault={"A": 70, "B": 30},
        text="제가 자전거를 타고 가다가 차량과 충돌했습니다.",
        facts={},
    )
    assert cyclist["user_vehicle_role"] == BICYCLE
    assert cyclist["my"] == 30
    assert cyclist["other"] == 70

    vehicle_role = infer_user_vehicle_role("자전거와 충돌했습니다.", {}, "bicycle_collision")
    assert vehicle_role == VEHICLE
