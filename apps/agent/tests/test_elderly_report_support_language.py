from app.services.elderly_friendly.plain_language_agent import PlainLanguageAgent


def test_fault_explanation_softens_when_fault_evidence_is_weak():
    report = PlainLanguageAgent().make_fault_explanation(
        {
            "scenario_type": "rear_end_collision",
            "fault_ratio": {
                "my": 10,
                "other": 90,
                "confidence": 0.8,
                "evidence_support_level": "insufficient",
                "judgment_status": "unsupported",
                "required_evidence_family": "knia",
                "caveats": ["직접적인 KNIA 과실비율 기준 근거가 부족합니다."],
            },
        }
    )

    assert "확정" in report["easy_explanation"]
    assert "KNIA" in report["why"][0]
    assert report["caution"] == "직접적인 KNIA 과실비율 기준 근거가 부족합니다"


def test_legal_explanation_uses_review_language_when_legal_evidence_is_partial():
    report = PlainLanguageAgent().make_legal_explanation(
        {
            "legal_liability": {
                "reporting_required": True,
                "criminal_risk_level": "high",
                "evidence_support_level": "partial",
                "judgment_status": "needs_review",
                "caveats": ["직접적인 법률 근거가 부족합니다."],
            },
            "structured_facts": {},
        }
    )

    assert "단정하기 어렵" in report["simple_summary"]
    assert report["risk_label"] == "확인 필요"
    assert report["caution"] == "직접적인 법률 근거가 부족합니다"
