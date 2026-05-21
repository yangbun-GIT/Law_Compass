from app.services.analyst_output_guard import (
    SUPPORT_DIRECT,
    SUPPORT_INSUFFICIENT,
    SUPPORT_PARTIAL,
    guard_criminal_liability_output,
    guard_fault_ratio_output,
    guard_traffic_law_output,
)
from app.services.analyst_output_contracts import validate_criminal_liability_output, validate_fault_ratio_output


def test_fault_ratio_caps_confidence_without_knia_evidence():
    guarded = guard_fault_ratio_output(
        {"my": 80, "other": 20, "confidence": 0.99, "basis": "일반 추정", "caveats": "기존 경고"},
        [],
    )

    assert guarded["evidence_support_level"] == SUPPORT_INSUFFICIENT
    assert guarded["judgment_status"] == "unsupported"
    assert guarded["used_evidence_ids"] == []
    assert guarded["confidence"] <= 0.45
    assert "기존 경고" in guarded["caveats"]


def test_fault_ratio_marks_partial_when_only_legal_evidence_exists():
    guarded = guard_fault_ratio_output(
        {"my": 30, "other": 70, "confidence": 0.99},
        [{"chunk_id": "law-1", "title": "도로교통법", "law_name": "도로교통법"}],
    )

    assert guarded["evidence_support_level"] == SUPPORT_PARTIAL
    assert guarded["judgment_status"] == "needs_review"
    assert guarded["used_evidence_ids"] == ["law-1"]
    assert guarded["confidence"] <= 0.65


def test_legal_and_criminal_outputs_mark_direct_legal_support():
    evidence = [{"chunk_id": "law-1", "title": "도로교통법", "law_name": "도로교통법"}]

    legal = guard_traffic_law_output({"applicable_rules": ["SAFE_DISTANCE"]}, evidence)
    liability = guard_criminal_liability_output({"reporting_required": False}, evidence)

    assert legal["evidence_support_level"] == SUPPORT_DIRECT
    assert legal["judgment_status"] == "evidence_supported"
    assert legal["used_evidence_ids"] == ["law-1"]
    assert liability["evidence_support_level"] == SUPPORT_DIRECT
    assert liability["decision_status"] == "reference_only"


def test_contract_normalizes_llm_shape_without_dropping_extra_context():
    validated = validate_fault_ratio_output(
        {
            "my": "30",
            "other": "70",
            "confidence": "0.82",
            "key_factors": "정차 여부",
            "evidence_count": 1,
            "evidence_ids": "law-1",
            "used_evidence_ids": "law-1",
            "required_evidence_family": "knia",
            "evidence_support_level": SUPPORT_DIRECT,
            "judgment_status": "evidence_supported",
            "caveats": "참고용",
            "source_model": "test-model",
        }
    )

    assert validated["my"] == 30
    assert validated["other"] == 70
    assert validated["confidence"] == 0.82
    assert validated["key_factors"] == ["정차 여부"]
    assert validated["evidence_ids"] == ["law-1"]
    assert validated["used_evidence_ids"] == ["law-1"]
    assert validated["required_evidence_family"] == "knia"
    assert validated["judgment_status"] == "evidence_supported"
    assert validated["caveats"] == ["참고용"]
    assert validated["source_model"] == "test-model"


def test_contract_tolerates_korean_boolean_and_scalar_fields():
    validated = validate_criminal_liability_output(
        {
            "reporting_required": "예",
            "criminal_risk_level": ["high"],
            "risk_flags": "signal_violation_review",
            "checklist": None,
            "evidence_support_level": SUPPORT_DIRECT,
        }
    )

    assert validated["reporting_required"] is True
    assert validated["criminal_risk_level"] == "high"
    assert validated["risk_flags"] == ["signal_violation_review"]
    assert validated["checklist"] == []
