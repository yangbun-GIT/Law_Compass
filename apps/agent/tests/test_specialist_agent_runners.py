from app.services.specialist_agent_runners import (
    VERSION,
    attach_specialist_agent_results,
    run_specialist_agent,
    SPECIALIST_RUN_INPUTS,
)


def test_specialist_agent_runners_attach_all_standard_results_without_raw_text():
    output = {
        "structured_facts": {"accident_party_type": "car_vs_car"},
        "video_input_contract": {"accepted_observations": [{"field": "collision_point_visible"}]},
        "fact_arbitration": {"conflicts": []},
        "legal_analysis": {"summary": "law"},
        "fault_ratio": {"my": 30, "other": 70},
        "legal_liability": {"criminal_risk_level": "low"},
        "insurance_guide": {"steps": ["접수"]},
        "action_plan": ["블랙박스 원본 보관"],
        "evidence_audit": {"uncertainty_level": "medium"},
        "claim_evidence": {"claim_count": 3},
        "knia_match_summary": {"chart_no": "차43-2"},
        "agent_judgment": {"finality": "reference_only"},
        "presentation_policy": {"finality": "reference_only"},
        "elderly_friendly_report": {"summary": "safe"},
    }

    attach_specialist_agent_results(output)
    packet = output["specialist_agent_results"]

    assert packet["version"] == VERSION
    assert packet["result_count"] == 10
    assert packet["safe_metadata_only"] is True
    assert set(packet["role_ids"]) == {item.role_id for item in SPECIALIST_RUN_INPUTS}
    assert all("raw_user_text" not in str(result) for result in packet["results"])


def test_specialist_runner_keeps_video_observation_out_of_fault_authority():
    output = {
        "structured_facts": {"accident_party_type": "car_vs_car"},
        "video_input_contract": {"accepted_observations": [{"field": "primary_collision_target"}]},
    }
    video_input = next(item for item in SPECIALIST_RUN_INPUTS if item.role_id == "video_observation_agent")

    result = run_specialist_agent(video_input, output)

    assert result.role_id == "video_observation_agent"
    assert result.finality == "needs_review"
    assert all(claim.claim_type != "fault_ratio_reference" for claim in result.claims)


def test_specialist_runner_returns_uncertainty_when_section_is_missing():
    output = {"structured_facts": {"accident_party_type": "car_vs_car"}}
    knia_input = next(item for item in SPECIALIST_RUN_INPUTS if item.role_id == "knia_fault_standard_agent")

    result = run_specialist_agent(knia_input, output)

    assert result.role_id == "knia_fault_standard_agent"
    assert result.claims == []
    assert result.uncertainties
