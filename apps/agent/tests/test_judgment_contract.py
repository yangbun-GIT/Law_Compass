from app.services.claim_evidence_validator import validate_claim_evidence
from app.services.judgment_contract import (
    STATUS_NEEDS_REVIEW,
    STATUS_SUPPORTED,
    STATUS_UNSUPPORTED,
    apply_judgment_contract_to_output,
    build_judgment_contract,
)


def test_claim_evidence_respects_analyst_insufficient_support():
    result = validate_claim_evidence(
        legal_analysis={"applicable_rules": ["SAFE_DISTANCE"], "evidence_support_level": "insufficient"},
        fault_ratio={},
        legal_liability={},
        insurance_guide={},
        action_plan=[],
        evidence=[{"chunk_id": "law-1", "title": "도로교통법", "law_name": "도로교통법"}],
    )

    legal_claim = next(claim for claim in result["claims"] if claim["claim_type"] == "legal_rules")
    assert legal_claim["support_level"] == "unsupported"
    assert result["coverage_level"] == "low"


def test_judgment_contract_blocks_final_language_when_claims_are_unsupported():
    claim_evidence = {
        "coverage_level": "low",
        "coverage_ratio": 0.4,
        "unsupported_claim_count": 1,
        "weak_claim_count": 0,
    }
    contract = build_judgment_contract(
        scenario={"scenario_type": "rear_end_collision", "accident_party_type": "car_vs_car", "confidence": 0.9},
        evidence=[],
        legal_analysis={"judgment_status": STATUS_UNSUPPORTED, "evidence_support_level": "insufficient", "required_evidence_family": "legal"},
        fault_ratio={"judgment_status": STATUS_NEEDS_REVIEW, "evidence_support_level": "partial", "required_evidence_family": "knia"},
        legal_liability={"judgment_status": STATUS_UNSUPPORTED, "evidence_support_level": "insufficient", "required_evidence_family": "legal"},
        insurance_guide={"judgment_status": STATUS_SUPPORTED, "evidence_support_level": "direct", "required_evidence_family": "any"},
        action_plan=[],
        evidence_audit={"evidence_quality": "low"},
        claim_evidence=claim_evidence,
        missing_fields=["신호 상태"],
    )

    assert contract["overall_status"] == STATUS_UNSUPPORTED
    assert contract["must_not_present_as_final"] is True
    assert "unsupported_claims_present" in contract["blocking_reasons"]

    output = apply_judgment_contract_to_output(
        {
            "disclaimers": [],
            "model_info": {},
            "uncertainty": {"level": "low", "reason": "old"},
            "fault_ratio": {"my": 80, "other": 20, "confidence": 0.99},
            "legal_liability": {"criminal_risk_level": "high", "confidence": 0.91},
            "insurance_guide": {"confidence": 0.9},
        },
        contract,
    )
    assert output["agent_judgment"] == contract
    assert output["uncertainty"]["level"] == "medium"
    assert output["disclaimers"]
    assert output["presentation_policy"]["finality"] == "blocked_for_final"
    assert output["fault_ratio"]["presentation_status"] == "review_required"
    assert output["fault_ratio"]["confidence"] <= 0.65
    assert output["legal_liability"]["presentation_status"] == "blocked_for_final"
    assert output["legal_liability"]["confidence"] <= 0.35
    assert output["insurance_guide"].get("presentation_status") is None


def test_evidence_retrieval_requires_high_scenario_coverage_for_supported_stage():
    claim_evidence = {
        "coverage_level": "high",
        "coverage_ratio": 1.0,
        "unsupported_claim_count": 0,
        "weak_claim_count": 0,
    }
    contract = build_judgment_contract(
        scenario={"scenario_type": "rear_end_collision", "accident_party_type": "car_vs_car", "confidence": 0.9},
        evidence=[
            {"chunk_id": "law-1", "score": 0.4},
            {"chunk_id": "law-2", "score": 0.36},
            {"source_type": "knia_base_fault", "score": 0.39},
        ],
        legal_analysis={"judgment_status": STATUS_SUPPORTED, "evidence_support_level": "direct", "required_evidence_family": "legal"},
        fault_ratio={"judgment_status": STATUS_SUPPORTED, "evidence_support_level": "direct", "required_evidence_family": "knia"},
        legal_liability={"judgment_status": STATUS_SUPPORTED, "evidence_support_level": "direct", "required_evidence_family": "legal"},
        insurance_guide={"judgment_status": STATUS_SUPPORTED, "evidence_support_level": "direct", "required_evidence_family": "any"},
        action_plan=["preserve evidence"],
        evidence_audit={
            "evidence_quality": "medium",
            "scenario_evidence_coverage": {
                "coverage_level": "medium",
                "decision_ready": False,
                "missing_requirements": ["total_evidence"],
            },
        },
        claim_evidence=claim_evidence,
        missing_fields=[],
    )

    retrieval_stage = next(stage for stage in contract["stage_statuses"] if stage["name"] == "evidence_retrieval")
    assert retrieval_stage["status"] == STATUS_NEEDS_REVIEW
    assert contract["overall_status"] == STATUS_NEEDS_REVIEW
    assert "coverage=medium" in retrieval_stage["summary"]
