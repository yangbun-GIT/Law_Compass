from app.services.fault_ratio_result_contract import (
    CONDITIONAL_RANGE,
    FALLBACK_NEEDS_EVIDENCE,
    SUPPORTED_RANGE,
    build_fault_ratio_result_contract,
)
from app.services.orchestrator import analyze_case


def test_centerline_obstacle_result_contract_is_supported_range_not_flat_fallback():
    result = analyze_case(
        "왕복 2차로에서 주차 차량 때문에 중앙선을 넘은 채 가다가 멈췄고 마주오던 차가 그대로 오면서 사고가 났습니다.",
        structured_facts={
            "accident_party_type": "car_vs_car",
            "accident_type": "centerline_obstacle_collision",
            "centerline_crossed": True,
            "road_obstruction": True,
            "illegal_parking_obstruction": True,
            "opposing_vehicle_present": True,
            "stopped": True,
            "opposing_vehicle_did_not_stop": True,
            "collision_partner_type": "vehicle",
        },
        analysis_mode="fault_ratio",
    )

    fault = result["fault_ratio"]
    contract = fault["fault_result_contract"]
    assert fault["fault_estimate_source"] == "contextual_complex_case"
    assert fault["my"] == 30
    assert fault["other"] == 70
    assert contract["display_status"] == SUPPORTED_RANGE
    assert contract["is_fallback"] is False
    assert contract["range_basis"] == "contextual_complex_case"
    assert contract["primary_range"]["label"] == "내 책임 30% / 상대 70% 참고"


def test_signal_unknown_result_contract_prefers_conditional_range():
    result = analyze_case(
        "교차로에서 좌회전 중 황색 신호로 바뀌었고 왼쪽 직진 차량과 충돌했습니다. 상대 신호는 보이지 않습니다.",
        structured_facts={
            "accident_party_type": "car_vs_car",
            "intersection": True,
            "ego_turn_direction": "left",
            "user_signal": "yellow_to_red",
            "opponent_signal_visible": False,
            "collision_partner_type": "vehicle",
        },
        analysis_mode="fault_ratio",
    )

    contract = result["fault_ratio"]["fault_result_contract"]
    assert contract["display_status"] == CONDITIONAL_RANGE
    assert contract["has_conditional_outcomes"] is True
    assert "opponent_signal" in contract["needs_confirmation_fields"]
    assert contract["primary_range"]["label"] == "조건별 범위 확인 필요"


def test_flat_default_result_contract_is_labeled_as_evidence_fallback():
    contract = build_fault_ratio_result_contract(
        {
            "my": 50,
            "other": 50,
            "fault_estimate_source": "scenario_default",
            "evidence_support_level": "insufficient",
            "fault_range": {"my": "50%", "other": "50%"},
        },
        scenario_type="general_collision",
        facts={},
        evidence=[],
    )

    assert contract["display_status"] == FALLBACK_NEEDS_EVIDENCE
    assert contract["is_fallback"] is True
    assert contract["fallback_reason"] == "direct_evidence_missing"


def test_conditional_branch_contract_does_not_present_flat_ratio_as_supported():
    contract = build_fault_ratio_result_contract(
        {
            "my": 50,
            "other": 50,
            "fault_estimate_source": "scenario_default",
            "conditional_required_facts": ["opponent_signal"],
            "conditional_outcomes": [
                {"label": "상대 정상 신호", "my_range": "60~80%", "other_range": "20~40%"},
                {"label": "상대 신호위반", "my_range": "20~40%", "other_range": "60~80%"},
            ],
        },
        scenario_type="intersection_signal_violation",
        facts={"opponent_signal_visible": False},
        evidence=[{"title": "신호 준수 의무"}],
    )

    assert contract["display_status"] == CONDITIONAL_RANGE
    assert contract["is_fallback"] is False
    assert contract["primary_range"]["label"] == "조건별 범위 확인 필요"
    assert contract["needs_confirmation_fields"] == ["opponent_signal"]
