from app.schemas import AnalysisOutput
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
    assert result["model_info"]["agent_quality_packet_version"] == "agent-quality-packet-v1"
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
                    {"field": "stopped", "value": True, "confidence": 0.9, "source": "frame_analysis"},
                    {"field": "impact_direction", "value": "rear", "confidence": 0.9, "source": "frame_analysis"},
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
    AnalysisOutput(**result)

