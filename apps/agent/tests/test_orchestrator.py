from app.schemas import AnalysisOutput
from app.services.orchestration_analysis import _apply_knia_fault_estimate
from app.services.orchestrator import analyze_case, analyze_video_case


def test_analyze_case_minimum_fields():
    result = analyze_case("신호대기 중 후방 차량 추돌")
    keys = {
        "accident_summary",
        "structured_facts",
        "fault_ratio",
        "insurance_guide",
        "legal_liability",
        "action_plan",
        "evidence",
        "claim_evidence",
        "agent_trace",
        "agent_quality_packet",
        "reflection_loop",
        "uncertainty",
        "disclaimers",
        "followup_questions",
        "model_info",
    }
    assert keys.issubset(set(result.keys()))
    assert result["claim_evidence"]["claim_count"] >= 1
    assert "coverage_level" in result["claim_evidence"]
    assert "claim_evidence_coverage" in result["evidence_audit"]
    assert "evidence_support_level" in result["legal_analysis"]
    assert "evidence_support_level" in result["fault_ratio"]
    assert "evidence_support_level" in result["legal_liability"]
    assert "evidence_support_level" in result["insurance_guide"]
    assert result["model_info"]["llm_policy"]["version"] == "llm-policy-v1"
    assert "fault_ratio_analysis" in result["model_info"]["llm_policy"]["sections"]
    assert result["agent_trace"]["version"] == "agent-execution-trace-v1"
    assert result["agent_trace"]["trace_policy"] == "safe_metadata_only_no_raw_user_text"
    assert result["agent_trace"]["step_count"] == len(result["agent_trace"]["steps"])
    assert result["agent_quality_packet"]["version"] == "agent-quality-packet-v1"
    assert result["agent_quality_packet"]["packet_contract"]["required_packets_present"] is True
    assert result["agent_quality_packet"]["guardrail_checks"]["safe_metadata_only"] is True
    assert result["agent_quality_packet"]["evidence_source_status"]["version"] == "evidence-source-status-v1"
    assert result["expert_guidance_sections"]["version"] == "expert-guidance-sections-v1"
    assert "expert_guidance_sections" in AnalysisOutput(**result).model_dump()
    assert result["model_info"]["agent_quality_packet_version"] == "agent-quality-packet-v1"
    assert result["model_info"]["evidence_source_status"]["version"] == "evidence-source-status-v1"
    assert result["reflection_loop"]["version"] == "agent-reflection-loop-v1"
    assert result["reflection_loop"]["next_action"] in {
        "finalize",
        "request_missing_input",
        "present_reference_only",
        "manual_review",
    }
    assert {step["id"] for step in result["agent_trace"]["steps"]} >= {
        "input_normalization",
        "scenario_classification",
        "evidence_retrieval",
        "reflection_loop",
        "judgment_contract",
    }
    assert "신호대기 중 후방 차량 추돌" not in str(result["agent_trace"])
    AnalysisOutput(**result)


def test_analyze_video_case_applies_video_input_contract():
    result = analyze_video_case(
        preprocessed_summary="정차 중 뒤에서 추돌당한 사고",
        ai_profile="default_vehicle_collision",
        specialist_roles=[],
        video_metadata={
            "metadata": {
                "duration_sec": 9.2,
                "representative_frames": ["/frames/1.jpg"],
                "observations": [
                    {
                        "field": "stopped",
                        "value": True,
                        "confidence": 0.9,
                        "source": "frame_analysis",
                        "frame_refs": ["frame_1.jpg"],
                    },
                    {
                        "field": "opponent_behavior",
                        "value": "rear_collision",
                        "confidence": 0.9,
                        "source": "frame_analysis",
                        "frame_refs": ["frame_1.jpg"],
                    },
                ],
            }
        },
        structured_facts={},
    )

    assert result["structured_facts"]["stopped"] is True
    assert result["structured_facts"]["opponent_behavior"] == "rear_collision"
    assert result["video_input_contract"]["version"] == "agent-video-input-contract-v1"
    assert result["model_info"]["video_input_contract"]["technical_metadata"]["representative_frame_count"] == 1
    trace_steps = {step["id"]: step for step in result["agent_trace"]["steps"]}
    assert trace_steps["input_normalization"]["packet"]["has_video_contract"] is True
    assert trace_steps["fact_arbitration"]["packet"]["video_observation_count"] == 2
    assert "requery_attempted" in trace_steps["reflection_loop"]["packet"]
    assert result["expert_guidance_sections"]["version"] == "expert-guidance-sections-v1"
    assert "expert_guidance_sections" in AnalysisOutput(**result).model_dump()
    AnalysisOutput(**result)


def test_crosswalk_alias_rear_end_case_keeps_following_vehicle_fault():
    result = analyze_case(
        "우회전 중 앞차가 횡단보도 앞에서 일시정지했고 제 차가 뒤에서 추돌했습니다.",
        structured_facts={
            "accident_type": "후방 추돌",
            "crosswalk": True,
            "pedestrian_signal": "red",
            "front_vehicle_stopped": True,
            "stopped": False,
            "opponent_behavior": "앞차가 횡단보도 앞에서 일시정지",
        },
        selected_keywords=["우회전", "횡단보도", "후방 추돌"],
        analysis_mode="fault_ratio",
    )

    assert result["structured_facts"]["crosswalk_nearby"] is True
    assert result["scenario_type"] == "rear_end_collision"
    assert result["fault_ratio"]["user_vehicle_role"] == "following_vehicle"
    assert result["fault_ratio"]["my"] >= 90


def test_reference_complex_contexts_use_contextual_fault_ranges():
    centerline = analyze_case(
        "주차 차량을 피하려고 중앙선을 넘은 상태로 가다가 멈췄고 마주오던 차와 충돌했습니다.",
        structured_facts={
            "centerline_crossed": True,
            "centerline_cross_reason": "주차 차량 회피",
            "stopped": True,
            "secondary_collision": True,
            "opponent_behavior": "마주오던 차량과 충돌 후 뒤차와도 충돌",
        },
        selected_keywords=["중앙선", "주차 차량", "후속 추돌"],
        analysis_mode="fault_ratio",
    )
    unlit = analyze_case(
        "야간에 등화 없이 정차한 차량을 추돌했습니다.",
        structured_facts={
            "stopped_vehicle_without_lights": True,
            "light_condition": "night",
            "reported_speed_kmh": 141,
            "speed_limit_kmh": 100,
            "fatality": True,
            "opponent_behavior": "무등화 정차 차량",
        },
        selected_keywords=["무등화", "정차 차량", "속도"],
        analysis_mode="fault_ratio",
    )
    bicycle = analyze_case(
        "자전거를 보고 정지했는데 뒤 고속버스가 후방 추돌했습니다.",
        structured_facts={
            "stopped": True,
            "bicycle_involved": True,
            "possible_trigger_vehicle": "자전거",
            "rear_vehicle_collision": True,
            "opponent_behavior": "뒤 고속버스가 후방 추돌",
        },
        selected_keywords=["자전거", "비접촉", "후방 추돌"],
        analysis_mode="fault_ratio",
    )

    assert centerline["fault_ratio"]["my"] == 30
    assert unlit["fault_ratio"]["my"] == 40
    assert bicycle["fault_ratio"]["my"] == 20


def test_contextual_complex_fault_estimate_is_not_overwritten_by_knia_base_fault():
    fault_ratio = {
        "my": 30,
        "other": 70,
        "fault_estimate_source": "contextual_complex_case",
        "basis": "contextual estimate",
    }

    _apply_knia_fault_estimate(
        fault_ratio=fault_ratio,
        knia_fault_estimate={"final_fault": {"A": 100, "B": 0}},
        scenario={"scenario_type": "rear_end_collision"},
        normalized={
            "description_text": "주차 차량 회피 후 정차 중 마주오던 차량과 충돌",
            "structured_facts": {
                "centerline_crossed": True,
                "centerline_cross_reason": "주차 차량 회피",
                "stopped": True,
            },
        },
    )

    assert fault_ratio["my"] == 30
    assert fault_ratio["other"] == 70
    assert fault_ratio["knia_reference_fault"] == {"A": 100, "B": 0}
    assert fault_ratio["knia_override_policy"] == "preserved_contextual_complex_case_estimate"


def test_uncertain_signal_transition_does_not_treat_user_as_clear_victim():
    result = analyze_case(
        "교차로에서 좌회전 중 직진 차량과 충돌했고 진입 후 황색, 충돌 시 적색으로 바뀐 것 같습니다.",
        structured_facts={
            "intersection": True,
            "turning": "left_turn",
            "signal_state": "황색에서 적색으로 변경",
            "signal_timing_uncertain": True,
            "cctv_needed": True,
            "opponent_behavior": "좌측 1차로 직진 차량",
        },
        selected_keywords=["좌회전", "직진 차량", "신호 변경", "CCTV"],
        analysis_mode="fault_ratio",
    )

    assert result["scenario_type"] == "intersection_signal_violation"
    assert result["fault_ratio"]["my"] == 80
    assert result["fault_ratio"]["other"] == 20
