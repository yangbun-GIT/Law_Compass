from app.services.accident_perspective import FRONT_VEHICLE, FOLLOWING_VEHICLE, infer_user_vehicle_role, map_fault_ratio_to_user
from app.services.static_legal_fallback import retrieve_static_legal_chunks


def test_rear_end_victim_maps_knia_a_b_to_user_fault():
    mapped = map_fault_ratio_to_user(
        scenario_type="rear_end_collision",
        fault={"A": 100, "B": 0},
        text="정차 중 뒤에서 추돌당했습니다.",
        facts={},
    )
    assert mapped["user_vehicle_role"] == FRONT_VEHICLE
    assert mapped["my"] == 0
    assert mapped["other"] == 100


def test_rear_end_following_vehicle_keeps_a_as_user_fault():
    mapped = map_fault_ratio_to_user(
        scenario_type="rear_end_collision",
        fault={"A": 100, "B": 0},
        text="제가 앞차를 추돌했습니다.",
        facts={},
    )
    assert mapped["user_vehicle_role"] == FOLLOWING_VEHICLE
    assert mapped["my"] == 100
    assert mapped["other"] == 0


def test_front_vehicle_stopped_fact_infers_user_as_following_vehicle():
    role = infer_user_vehicle_role(
        "우회전 중 앞차가 횡단보도 앞에서 멈춰 제 차가 뒤에서 추돌했습니다.",
        {"front_vehicle_stopped": True, "stopped": False},
        "rear_end_collision",
    )
    assert role == FOLLOWING_VEHICLE


def test_rear_end_phrases_infer_front_vehicle():
    assert infer_user_vehicle_role("신호대기 중 뒤차가 후미를 추돌했습니다", {}, "rear_end_collision") == FRONT_VEHICLE
    assert infer_user_vehicle_role("정차 중 뒤차가 들이받았습니다", {}, "rear_end_collision") == FRONT_VEHICLE


def test_static_fallback_returns_korean_rear_end_basis():
    items = retrieve_static_legal_chunks("정차 중 뒤차 후미추돌 안전거리", limit=3)
    assert items
    assert all("Fault Ratio Guide" not in item["title"] for item in items)
    assert items[0]["law_name"] in {"과실비율 인정기준", "도로교통법"}
