from app.services.knia.knia_matcher import _is_strict_scenario_mismatch, _scenario_chart_score_adjustment, _to_match


def test_signal_violation_boosts_signal_chart_over_lane_change_chart():
    signal_adjustment = _scenario_chart_score_adjustment(
        {"chart_no": "차12-1"},
        ["intersection", "signal_violation", "fault_ratio"],
        "교차로 신호위반 충돌 적색 신호",
    )
    lane_adjustment = _scenario_chart_score_adjustment(
        {"chart_no": "차43-2"},
        ["intersection", "signal_violation", "fault_ratio"],
        "후행 직진 대 선행 진로변경 차로를 변경",
    )
    assert signal_adjustment > 0
    assert lane_adjustment < 0


def test_to_match_uses_chart_number_party_label_when_imported_label_is_stale():
    match = _to_match(
        {
            "id": "00000000-0000-0000-0000-000000000000",
            "chart_no": "차43-2",
            "chart_type": "1",
            "title": "후행 직진 대 선행 진로변경",
            "accident_party_label": "차대사람 사고",
        },
        0.5,
        "테스트",
    )
    assert match["accident_party_type"] == "car_vs_car"
    assert match["accident_party_label"] == "차대차 사고"


def test_signal_violation_scenario_rejects_unrelated_rear_end_chart():
    assert _is_strict_scenario_mismatch(
        "intersection_signal_violation",
        {"chart_no": "차41-1"},
        "양 차량 주행 중 후방 추돌 안전거리",
    )
    assert not _is_strict_scenario_mismatch(
        "intersection_signal_violation",
        {"chart_no": "차12-1"},
        "교차로 신호위반 충돌",
    )


def test_rear_end_scenario_rejects_left_turn_straight_chart_family():
    assert _is_strict_scenario_mismatch(
        "rear_end_collision",
        {"chart_no": "차16-1", "accident_party_type": "car_vs_car"},
        "신호등 없는 교차로 직진 대 좌회전 사고",
    )
    assert _is_strict_scenario_mismatch(
        "rear_end_collision",
        {"chart_no": "차43-2", "accident_party_type": "car_vs_car"},
        "후행 직진 대 선행 진로변경 차로를 변경",
    )
    assert not _is_strict_scenario_mismatch(
        "rear_end_collision",
        {"chart_no": "차41-1", "accident_party_type": "car_vs_car"},
        "뒤차 안전거리 미확보 후미추돌 정차 차량 추돌",
    )
