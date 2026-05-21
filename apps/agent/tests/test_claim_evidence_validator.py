from app.services.claim_evidence_validator import apply_claim_evidence_audit, validate_claim_evidence


def test_claim_evidence_marks_supported_knia_fault():
    result = validate_claim_evidence(
        legal_analysis={"applicable_rules": ["REAR_END_SAFE_DISTANCE"], "legal_issue_summary": "안전거리 의무 검토"},
        fault_ratio={"my": 30, "other": 70, "basis": "KNIA 기준 반영"},
        legal_liability={"reporting_required": False, "criminal_risk_level": "low"},
        insurance_guide={"summary": "보험 접수 후 증빙 확보"},
        action_plan=["블랙박스 원본을 보관하세요."],
        evidence=[
            {"chunk_id": "law-1", "title": "도로교통법 안전거리", "law_name": "도로교통법", "source_url": "https://www.law.go.kr"},
            {"source_type": "knia_base_fault", "title": "KNIA 원문 기본과실", "source_url": "https://accident.knia.or.kr/myaccident-content"},
        ],
    )

    assert result["coverage_level"] == "high"
    assert result["unsupported_claim_count"] == 0
    fault_claims = [claim for claim in result["claims"] if claim["claim_type"] == "fault_ratio_estimate"]
    assert fault_claims and fault_claims[0]["support_level"] == "supported"


def test_claim_evidence_lowers_audit_when_missing_support():
    result = validate_claim_evidence(
        legal_analysis={"applicable_rules": ["SIGNAL_VIOLATION"]},
        fault_ratio={"my": 50, "other": 50, "basis": "일반 추정"},
        legal_liability={"reporting_required": True},
        insurance_guide={},
        action_plan=[],
        evidence=[],
    )
    audit = apply_claim_evidence_audit({"uncertainty_level": "low", "weak_points": []}, result)

    assert result["coverage_level"] == "low"
    assert result["unsupported_claim_count"] >= 1
    assert audit["uncertainty_level"] == "high"
    assert audit["claim_evidence_coverage"]["level"] == "low"


def test_claim_evidence_prefers_used_evidence_ids():
    result = validate_claim_evidence(
        legal_analysis={
            "applicable_rules": ["SAFE_DISTANCE"],
            "used_evidence_ids": ["law-used"],
        },
        fault_ratio={},
        legal_liability={},
        insurance_guide={},
        action_plan=[],
        evidence=[
            {"chunk_id": "law-unused", "title": "사용하지 않은 법률 근거", "law_name": "도로교통법"},
            {"chunk_id": "law-used", "title": "사용한 법률 근거", "law_name": "도로교통법"},
        ],
    )

    legal_claim = next(claim for claim in result["claims"] if claim["claim_type"] == "legal_rules")
    assert legal_claim["evidence_refs"][0]["ref_id"] == "law-used"
