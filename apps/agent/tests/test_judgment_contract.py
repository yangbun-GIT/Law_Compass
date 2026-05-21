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


def test_judgment_contract_separates_input_evidence_and_knia_blockers():
    contract = build_judgment_contract(
        scenario={"scenario_type": "intersection_signal_violation", "accident_party_type": "car_vs_car", "confidence": 0.9},
        evidence=[{"chunk_id": "law-1", "law_name": "도로교통법", "score": 0.41}],
        legal_analysis={"judgment_status": STATUS_SUPPORTED, "evidence_support_level": "direct", "required_evidence_family": "legal"},
        fault_ratio={"judgment_status": STATUS_NEEDS_REVIEW, "evidence_support_level": "partial", "required_evidence_family": "knia"},
        legal_liability={"judgment_status": STATUS_SUPPORTED, "evidence_support_level": "direct", "required_evidence_family": "legal"},
        insurance_guide={"judgment_status": STATUS_SUPPORTED, "evidence_support_level": "direct", "required_evidence_family": "any"},
        action_plan=["증거 보관"],
        evidence_audit={
            "evidence_quality": "medium",
            "scenario_evidence_coverage": {
                "coverage_level": "medium",
                "decision_ready": False,
                "missing_evidence_families": ["knia"],
                "missing_requirements": ["family:knia", "required_input_fields"],
            },
        },
        claim_evidence={
            "coverage_level": "medium",
            "coverage_ratio": 0.8,
            "unsupported_claim_count": 0,
            "weak_claim_count": 1,
        },
        missing_fields=["user_signal"],
        knia_matches=[],
        knia_fault_estimate=None,
    )

    categories = {item["category"] for item in contract["decision_blockers"]}
    assert contract["version"] == "agent-judgment-contract-v2"
    assert contract["overall_status"] == STATUS_NEEDS_REVIEW
    assert contract["decision_readiness"]["label"] == "추가 확인 필요"
    assert {"input_missing", "evidence_missing", "knia_missing"}.issubset(categories)
    assert "knia_basis_missing_or_incomplete" in contract["blocking_reasons"]
    assert contract["knia_basis"]["requires_knia"] is True
    assert contract["knia_basis"]["matched_chart_count"] == 0


def test_judgment_contract_tracks_knia_adjustment_basis_when_available():
    contract = build_judgment_contract(
        scenario={"scenario_type": "rear_end_collision", "accident_party_type": "car_vs_car", "confidence": 0.9},
        evidence=[
            {"chunk_id": "law-1", "law_name": "도로교통법", "score": 0.41},
            {"source_type": "knia_base_fault", "score": 0.42},
        ],
        legal_analysis={"judgment_status": STATUS_SUPPORTED, "evidence_support_level": "direct", "required_evidence_family": "legal"},
        fault_ratio={"judgment_status": STATUS_SUPPORTED, "evidence_support_level": "direct", "required_evidence_family": "knia"},
        legal_liability={"judgment_status": STATUS_SUPPORTED, "evidence_support_level": "direct", "required_evidence_family": "legal"},
        insurance_guide={"judgment_status": STATUS_SUPPORTED, "evidence_support_level": "direct", "required_evidence_family": "any"},
        action_plan=["증거 보관"],
        evidence_audit={
            "evidence_quality": "high",
            "scenario_evidence_coverage": {
                "coverage_level": "high",
                "decision_ready": True,
                "missing_evidence_families": [],
                "missing_requirements": [],
            },
        },
        claim_evidence={
            "coverage_level": "high",
            "coverage_ratio": 1.0,
            "unsupported_claim_count": 0,
            "weak_claim_count": 0,
        },
        missing_fields=[],
        knia_matches=[{"chart_no": "차41-1", "title": "후행 직진 대 선행 진로변경"}],
        knia_fault_estimate={
            "base_fault": {"A": 0, "B": 100},
            "final_fault": {"A": 10, "B": 90},
            "selected_adjustments": [{"label": "현저한 과실"}],
            "rejected_adjustments": [{"label": "야간"}],
        },
    )

    knia_stage = next(stage for stage in contract["stage_statuses"] if stage["name"] == "knia_fault_basis")
    assert knia_stage["status"] == STATUS_SUPPORTED
    assert contract["knia_basis"]["primary_chart_no"] == "차41-1"
    assert contract["knia_basis"]["applied_adjustment_count"] == 1
    assert contract["knia_basis"]["rejected_adjustment_count"] == 1
