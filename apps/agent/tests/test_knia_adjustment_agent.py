from app.services.knia.knia_adjustment_agent import apply_knia_adjustment_agent


def _estimate():
    return {
        "base_fault": {"A": 0, "B": 100},
        "final_fault": {"A": 0, "B": 100},
        "source_chart": {"chart_no": "차99-9", "title": "후미추돌 정차 차량 기준"},
    }


def test_rear_end_sudden_brake_with_red_light_reason_keeps_low_user_fault():
    fault = {"my": 0, "other": 100, "user_vehicle_role": "front_vehicle"}

    result = apply_knia_adjustment_agent(
        fault_ratio=fault,
        knia_fault_estimate=_estimate(),
        scenario_type="rear_end_collision",
        description_text="빨간불 신호대기 중 정차했다가 뒤차가 추돌했습니다. 급정거처럼 보일 수 있습니다.",
        structured_facts={"sudden_brake": True, "stop_reason": "red_light", "user_vehicle_role": "front_vehicle"},
    )

    assert fault["my"] <= 10
    assert fault["other"] >= 90
    assert result["applied_adjustments"] == []
    assert any(item["factor_id"] == "sudden_brake_without_reason" for item in result["not_applied_adjustments"])


def test_rear_end_sudden_brake_without_reason_increases_user_fault():
    fault = {"my": 0, "other": 100, "user_vehicle_role": "front_vehicle"}

    result = apply_knia_adjustment_agent(
        fault_ratio=fault,
        knia_fault_estimate=_estimate(),
        scenario_type="rear_end_collision",
        description_text="정차 직전에 이유 없이 급정거했고 뒤차가 추돌했습니다.",
        structured_facts={"sudden_brake": True, "stop_reason": "no_reason", "user_vehicle_role": "front_vehicle"},
    )

    assert fault["my"] > 0
    assert fault["other"] < 100
    assert result["applied_adjustments"][0]["factor_id"] == "sudden_brake_without_reason"


def test_rear_end_brake_light_failure_increases_user_fault():
    fault = {"my": 0, "other": 100, "user_vehicle_role": "front_vehicle"}

    result = apply_knia_adjustment_agent(
        fault_ratio=fault,
        knia_fault_estimate=_estimate(),
        scenario_type="rear_end_collision",
        description_text="정차 중 뒤차가 추돌했습니다.",
        structured_facts={"brake_light": "failed", "user_vehicle_role": "front_vehicle"},
    )

    assert fault["my"] >= 10
    assert any(item["factor_id"] == "brake_light_failure" for item in result["applied_adjustments"])


def test_unknown_sudden_brake_reason_adds_caveat_without_numeric_adjustment():
    fault = {"my": 0, "other": 100, "user_vehicle_role": "front_vehicle"}

    result = apply_knia_adjustment_agent(
        fault_ratio=fault,
        knia_fault_estimate=_estimate(),
        scenario_type="rear_end_collision",
        description_text="급정거 여부는 잘 모르겠고 뒤차가 추돌했습니다.",
        structured_facts={"sudden_brake": True, "sudden_brake_reason": "unknown", "user_vehicle_role": "front_vehicle"},
    )

    assert fault["my"] == 0
    assert fault["other"] == 100
    assert result["caveats"]
    assert result["not_applied_adjustments"][0]["answer"] == "unknown"


def test_incompatible_knia_basis_blocks_adjustment_agent():
    fault = {"my": 0, "other": 100}

    result = apply_knia_adjustment_agent(
        fault_ratio=fault,
        knia_fault_estimate={
            "source_chart": {"chart_no": "차16-1", "title": "좌회전 대 직진"},
            "final_fault": {"A": 50, "B": 50},
        },
        scenario_type="rear_end_collision",
        description_text="정차 중 뒤차가 추돌했습니다.",
        structured_facts={"sudden_brake": True, "stop_reason": "no_reason"},
    )

    assert result["status"] == "rejected_incompatible_knia_basis"
    assert fault["my"] == 0
    assert fault["other"] == 100
