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
    AnalysisOutput(**result)

