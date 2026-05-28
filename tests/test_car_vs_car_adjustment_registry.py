from app.services.knia.adjustments.registry import evaluate_adjustments


def test_rear_end_unknown_brake_light_creates_unknown_and_condition():
    result = evaluate_adjustments(
        "rear_end_collision",
        "car_vs_car",
        {"stopped": True, "brake_light": "unknown", "stop_reason": "red_light"},
        None,
        "빨간불 신호대기 중 정차해 있었는데 뒤차가 추돌했다. 브레이크등 작동 여부는 모르겠다.",
    )

    assert result["base_fault"] == {"my": 0, "other": 100}
    assert result["final_fault"] == {"my": 0, "other": 100}
    assert any(item["factor_id"] == "brake_light_failure" for item in result["unknown_adjustments"])
    assert any("브레이크등" in item["label"] for item in result["conditional_outcomes"])


def test_rear_end_lawful_stop_does_not_apply_sudden_brake_without_reason():
    result = evaluate_adjustments(
        "rear_end_collision",
        "car_vs_car",
        {"stopped": True, "sudden_brake": True, "stop_reason": "red_light", "brake_light": "normal"},
        None,
        "신호대기 중 급정거처럼 멈춘 뒤 뒤차가 추돌했다.",
    )

    assert not result["applied_adjustments"]
    assert any(item["factor_id"] == "sudden_brake_without_reason" for item in result["not_applied_adjustments"])


def test_stealth_parking_registry_returns_80_90_or_100_condition_range():
    result = evaluate_adjustments(
        "stealth_illegal_parked_vehicle_collision",
        "car_vs_car",
        {"is_stealth_parked_vehicle_collision": True, "stopped_vehicle_without_lights": True},
        None,
        "늦은 밤 교량 밑 스텔스 주차 트럭과 충돌했다.",
    )

    assert result["base_fault"]["other"] >= 80
    assert any("100" in item["other_range"] for item in result["conditional_outcomes"])
