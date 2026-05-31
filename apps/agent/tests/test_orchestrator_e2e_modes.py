from app.schemas import AnalysisOutput
from app.services.orchestrator import analyze_case, analyze_video_case


def _frame_refs(count: int = 6) -> list[str]:
    return [f"/frames/frame_{index:03d}.jpg" for index in range(1, count + 1)]


def _openai_yolo_on_metadata(observations: list[dict] | None = None) -> dict:
    return {
        "metadata": {
            "duration_sec": 8.2,
            "representative_frames": _frame_refs(8),
            "observations": observations
            or [
                {
                    "field": "collision_partner_type",
                    "value": "vehicle",
                    "confidence": 0.91,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_004.jpg", "frame_005.jpg"],
                },
                {
                    "field": "collision_point_visible",
                    "value": True,
                    "confidence": 0.9,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_005.jpg"],
                },
                {
                    "field": "stopped",
                    "value": True,
                    "confidence": 0.93,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_003.jpg", "frame_004.jpg"],
                },
            ],
            "openai_frame_analysis": {"enabled": True, "model": "gpt-4.1-mini"},
            "yolo_frame_analysis": {"enabled": True, "model": "yolo11n.pt"},
        }
    }


def _openai_yolo_off_metadata() -> dict:
    return {
        "metadata": {
            "duration_sec": 8.2,
            "representative_frames": _frame_refs(7),
            "openai_frame_analysis": {"enabled": False},
            "yolo_frame_analysis": {"enabled": False},
        }
    }


def _packet_by_id(result: dict) -> dict[str, dict]:
    return {packet["task_id"]: packet for packet in result["agent_task_packets"]["packets"]}


def _assert_contract_output(result: dict) -> None:
    assert result["agent_quality_packet"]["packet_contract"]["required_packets_present"] is True
    assert result["agent_goal_result"]["version"] == "agent-goal-result-v1"
    assert result["agent_replan"]["version"] == "agent-replan-v1"
    assert AnalysisOutput(**result)


def test_text_only_e2e_keeps_existing_contract_without_video_tasks():
    result = analyze_case(
        "신호대기 중 정차한 내 차를 뒤차가 추돌했습니다.",
        structured_facts={
            "stopped": True,
            "opponent_behavior": "rear_collision",
            "accident_party_type": "car_vs_car",
        },
        selected_keywords=["정차", "후방추돌"],
        analysis_mode="fault_ratio",
        case_id="e2e-text-only",
        trace_id="trace-e2e-text-only",
    )

    assert result["agent_plan"]["input_mode"] == "text_only"
    assert "video_observation" not in result["agent_plan"]["execution_order"]
    assert result["scenario_type"] == "rear_end_collision"
    assert result["fault_ratio"]["my"] <= 10
    assert result["trace_id"] == "trace-e2e-text-only"
    _assert_contract_output(result)


def test_video_only_e2e_with_openai_yolo_on_applies_video_observations():
    result = analyze_video_case(
        preprocessed_summary="영상에서 정차 후 차량 충돌 후보가 확인됩니다.",
        ai_profile="default_vehicle_collision",
        specialist_roles=[],
        video_metadata=_openai_yolo_on_metadata(),
        structured_facts={},
        analysis_mode="fault_ratio",
        case_id="e2e-video-only-on",
        upload_id="upload-video-on",
    )

    assert result["agent_plan"]["input_mode"] == "video_only"
    assert result["agent_plan"]["execution_order"][:3] == ["input_normalization", "video_observation", "fact_arbitration"]
    packets = _packet_by_id(result)
    assert packets["video_observation"]["status"] == "succeeded"
    assert packets["fact_arbitration"]["status"] in {"succeeded", "needs_review"}
    assert result["structured_facts"]["collision_partner_type"] == "vehicle"
    assert result["video_input_contract"]["observation_quality_summary"]["accepted_count"] >= 3
    assert result["video_input_contract"]["analysis_recovery"]["status"] == "not_required"
    _assert_contract_output(result)


def test_text_and_video_e2e_arbitrates_video_physical_facts():
    result = analyze_case(
        "뒤에서 차량이 충돌했지만 정차 여부는 기억이 애매합니다.",
        structured_facts={"stopped": False, "accident_party_type": "car_vs_car"},
        selected_keywords=["후방추돌", "차대차"],
        video_metadata=_openai_yolo_on_metadata(
            [
                {
                    "field": "stopped",
                    "value": True,
                    "confidence": 0.96,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_003.jpg", "frame_004.jpg"],
                },
                {
                    "field": "opponent_behavior",
                    "value": "rear_collision",
                    "confidence": 0.96,
                    "source": "frame_analysis:openai",
                    "frame_refs": ["frame_004.jpg", "frame_005.jpg"],
                },
            ]
        ),
        analysis_mode="fault_ratio",
        case_id="e2e-text-video",
    )

    assert result["agent_plan"]["input_mode"] == "text_and_video"
    assert result["structured_facts"]["stopped"] is True
    assert result["structured_facts"]["opponent_behavior"] == "rear_collision"
    assert result["fact_arbitration"]["conflicts"][0]["field"] == "stopped"
    assert result["fact_arbitration"]["conflicts"][0]["winner"] == "video"
    assert result["scenario_type"] == "rear_end_collision"
    _assert_contract_output(result)


def test_followup_reanalysis_e2e_uses_bounded_replan_policy():
    result = analyze_case(
        "보완 답변을 반영해 다시 분석합니다.",
        structured_facts={
            "_followup_iteration": 1,
            "_followup_answered_fields": ["injury", "stopped"],
            "_followup_unresolved_fields": ["opponent_signal"],
            "accident_party_type": "car_vs_car",
            "injury": False,
            "stopped": True,
        },
        selected_keywords=["보완답변", "정차"],
        analysis_mode="fault_ratio",
        case_id="e2e-followup",
    )

    assert result["agent_plan"]["input_mode"] == "followup_reanalysis"
    assert result["agent_plan"]["replan_policy"] == "bounded_on_blocker"
    assert any(
        ref["ref_type"] == "questionnaire_answer"
        for task in result["agent_plan"]["tasks"]
        for ref in task["input_refs"]
    )
    assert result["agent_trace"]["task_plan"]["input_mode"] == "followup_reanalysis"
    _assert_contract_output(result)


def test_knia_available_e2e_exposes_basis_when_matching_chart_exists():
    result = analyze_case(
        "같은 방향으로 주행 중 앞 차량이 차선을 변경해 내 차와 충돌했습니다.",
        structured_facts={
            "accident_party_type": "car_vs_car",
            "accident_type": "lane_change_collision",
            "lane_change": True,
        },
        selected_keywords=["차선변경", "진로변경", "차대차"],
        analysis_mode="fault_ratio",
        case_id="e2e-knia-available",
    )

    knia_status = result["agent_quality_packet"]["evidence_source_status"]["sources"]["knia_chart_match"]
    assert result["agent_plan"]["input_mode"] == "text_only"
    assert result["knia_primary_match"]
    assert knia_status["status"] in {"ready", "degraded_with_fallback"}
    assert knia_status["item_count"] >= 1
    assert result["fault_ratio"]["knia_reference_fault"]
    assert result["fault_ratio"]["fault_result_contract"]["display_status"] == "supported_range"
    _assert_contract_output(result)


def test_knia_missing_e2e_keeps_result_as_reference_or_needs_review():
    result = analyze_case(
        "사고가 났지만 충돌 대상과 신호, 정차 여부를 아직 알 수 없습니다.",
        structured_facts={},
        selected_keywords=[],
        analysis_mode="fault_ratio",
        case_id="e2e-knia-missing",
    )

    knia_status = result["agent_quality_packet"]["evidence_source_status"]["sources"]["knia_chart_match"]
    assert result["agent_plan"]["input_mode"] == "text_only"
    assert not result["knia_primary_match"]
    assert knia_status["status"] in {"empty", "unavailable"}
    assert result["agent_goal_result"]["goal"]["finality"] != "decision_ready"
    assert result["fault_ratio"]["fault_result_contract"]["display_status"] == "fallback_needs_evidence"
    assert result["agent_judgment"]["must_not_present_as_final"] is True
    _assert_contract_output(result)


def test_video_only_e2e_with_openai_yolo_off_fallback_keeps_recovery_plan():
    result = analyze_video_case(
        preprocessed_summary="",
        ai_profile="default_vehicle_collision",
        specialist_roles=[],
        video_metadata=_openai_yolo_off_metadata(),
        structured_facts={},
        analysis_mode="fault_ratio",
        case_id="e2e-video-off",
        upload_id="upload-video-off",
    )

    recovery = result["video_input_contract"]["analysis_recovery"]
    assert result["agent_plan"]["input_mode"] == "video_only"
    assert result["video_input_contract"]["observation_quality_summary"]["accepted_count"] == 0
    assert recovery["status"] == "frame_rich_no_actionable_observation"
    assert {item["code"] for item in recovery["actions"]} >= {
        "select_event_window_frames",
        "enable_openai_frame_analysis",
        "enable_yolo_frame_analysis",
        "ask_user_confirmation",
    }
    assert result["agent_goal_result"]["goal"]["finality"] != "decision_ready"
    _assert_contract_output(result)


def test_followup_reanalysis_with_video_keeps_both_questionnaire_and_video_tasks():
    result = analyze_case(
        "보완 답변과 영상 관찰값을 함께 반영합니다.",
        structured_facts={
            "_followup_iteration": 2,
            "_followup_answered_fields": ["collision_partner_type"],
            "_followup_unresolved_fields": ["opponent_signal"],
            "accident_party_type": "car_vs_car",
        },
        selected_keywords=["차대차", "재분석"],
        video_metadata=_openai_yolo_on_metadata(),
        analysis_mode="fault_ratio",
        case_id="e2e-followup-video",
    )

    assert result["agent_plan"]["input_mode"] == "followup_reanalysis"
    assert "video_observation" in result["agent_plan"]["execution_order"]
    assert "fact_arbitration" in result["agent_plan"]["execution_order"]
    assert any(
        ref["ref_type"] == "questionnaire_answer"
        for task in result["agent_plan"]["tasks"]
        for ref in task["input_refs"]
    )
    assert result["video_input_contract"]["observation_quality_summary"]["accepted_count"] >= 3
    _assert_contract_output(result)
