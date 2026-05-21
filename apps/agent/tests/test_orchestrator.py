from app.schemas import AnalysisOutput
from app.services.orchestrator import analyze_case


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

