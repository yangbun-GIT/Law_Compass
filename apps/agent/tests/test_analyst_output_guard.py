from app.services.analyst_output_guard import (
    SUPPORT_DIRECT,
    SUPPORT_INSUFFICIENT,
    SUPPORT_PARTIAL,
    guard_criminal_liability_output,
    guard_fault_ratio_output,
    guard_traffic_law_output,
)


def test_fault_ratio_caps_confidence_without_knia_evidence():
    guarded = guard_fault_ratio_output(
        {"my": 80, "other": 20, "confidence": 0.99, "basis": "일반 추정", "caveats": "기존 경고"},
        [],
    )

    assert guarded["evidence_support_level"] == SUPPORT_INSUFFICIENT
    assert guarded["confidence"] <= 0.45
    assert "기존 경고" in guarded["caveats"]


def test_fault_ratio_marks_partial_when_only_legal_evidence_exists():
    guarded = guard_fault_ratio_output(
        {"my": 30, "other": 70, "confidence": 0.99},
        [{"chunk_id": "law-1", "title": "도로교통법", "law_name": "도로교통법"}],
    )

    assert guarded["evidence_support_level"] == SUPPORT_PARTIAL
    assert guarded["confidence"] <= 0.65


def test_legal_and_criminal_outputs_mark_direct_legal_support():
    evidence = [{"chunk_id": "law-1", "title": "도로교통법", "law_name": "도로교통법"}]

    legal = guard_traffic_law_output({"applicable_rules": ["SAFE_DISTANCE"]}, evidence)
    liability = guard_criminal_liability_output({"reporting_required": False}, evidence)

    assert legal["evidence_support_level"] == SUPPORT_DIRECT
    assert liability["evidence_support_level"] == SUPPORT_DIRECT
    assert liability["decision_status"] == "reference_only"
