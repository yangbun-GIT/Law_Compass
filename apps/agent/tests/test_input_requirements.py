from app.services.input_requirements import build_followup_loop_state, build_input_requirements
from app.services.orchestrator import analyze_case


def test_rear_end_text_uses_targeted_input_questions():
    requirements = build_input_requirements(
        facts={},
        scenario_type="rear_end_collision",
        missing_fields=["accident_type", "signal_state", "injury", "opponent_behavior", "damage_level"],
        description_text="정차 중 뒤에서 추돌당했습니다.",
    )

    questions = requirements["questions"]
    fields = {item["field"] for item in questions}
    question_text = " ".join(item["question"] for item in questions)

    assert "accident_type" not in fields
    assert "opponent_behavior" not in fields
    assert "signal_state" not in requirements["blocking_fields"]
    assert "injury" in requirements["blocking_fields"]
    assert "다친 사람이 있나요?" in question_text
    assert all("accident_type" not in item["question"] for item in questions)


def test_signal_transition_requires_each_party_signal_confirmation():
    requirements = build_input_requirements(
        facts={
            "accident_type": "좌회전 직진 충돌",
            "intersection": True,
            "signal_state": "황색에서 적색으로 변경",
            "signal_timing_uncertain": True,
            "cctv_needed": True,
        },
        scenario_type="intersection_signal_violation",
        missing_fields=["injury", "damage_level"],
        description_text="교차로에서 좌회전 중 진입 후 황색불이 되었고 충돌할 때는 빨간불로 바뀐 것 같습니다.",
    )

    fields = [item["field"] for item in requirements["questions"]]

    assert fields[:2] == ["opponent_signal", "user_signal"]
    assert "opponent_signal" in requirements["blocking_fields"]
    assert "user_signal" in requirements["blocking_fields"]
    assert "injury" in fields


def test_orchestrator_exposes_required_input_contract_in_report():
    result = analyze_case("정차 중 뒤에서 추돌당했습니다.")

    requirements = result["input_requirements"]
    missing_info = result["elderly_friendly_report"]["missing_info"]["items"]

    assert requirements["version"] == "agent-input-requirements-v1"
    assert result["required_input_questions"]
    assert "required_input_fields_missing" in result["agent_judgment"]["blocking_reasons"]
    assert any("다친 사람" in item for item in missing_info)
    assert not any("accident_type" in item for item in missing_info)
    assert result["followup_loop"]["status"] in {"waiting_for_input", "continue"}
    assert result["followup_loop"]["remaining_question_count"] >= 1


def test_followup_loop_completes_when_blocking_fields_are_resolved():
    requirements = build_input_requirements(
        facts={"injury": False, "stopped": True, "_followup_iteration": 1, "_followup_answered_fields": ["injury", "stopped"]},
        scenario_type="rear_end_collision",
        missing_fields=["injury"],
        description_text="정차 중 뒤에서 추돌당했습니다.",
    )
    loop = build_followup_loop_state(requirements, {"_followup_iteration": 1, "_followup_answered_fields": ["injury", "stopped"]})

    assert "injury" not in requirements["blocking_fields"]
    assert loop["status"] in {"complete", "optional_followup_available"}
    assert loop["stop_reason"] in {"required_inputs_resolved", "blocking_inputs_resolved"}


def test_followup_loop_stops_after_max_iterations():
    requirements = build_input_requirements(
        facts={"_followup_iteration": 3, "_followup_unresolved_fields": ["injury"]},
        scenario_type="rear_end_collision",
        missing_fields=["injury"],
        description_text="뒤에서 추돌당했습니다.",
    )
    loop = build_followup_loop_state(requirements, {"_followup_iteration": 3, "_followup_unresolved_fields": ["injury"]})

    assert loop["status"] == "stopped"
    assert loop["stop_reason"] == "max_iterations_reached"
    assert loop["can_request_more_input"] is False
