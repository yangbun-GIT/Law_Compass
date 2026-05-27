from __future__ import annotations

from typing import Any


GUIDED_ANALYSIS_MODES = {
    "quick_summary",
    "fault_ratio_focused",
    "legal_precedent_focused",
    "insurance_response_focused",
    "full_deep_research",
}

LEGACY_ANALYSIS_MODE_ALIASES = {
    "fault-focused": "fault_ratio_focused",
    "fault_ratio": "fault_ratio_focused",
    "legal-focused": "legal_precedent_focused",
    "legal_precedent": "legal_precedent_focused",
    "insurance-focused": "insurance_response_focused",
    "insurance_response": "insurance_response_focused",
    "deep_research": "full_deep_research",
    "full": "full_deep_research",
    "criminal-liability-focused": "legal_precedent_focused",
    "evidence-review": "full_deep_research",
}


def normalize_analysis_mode(value: str | None) -> str:
    raw = (value or "quick_summary").strip()
    canonical = LEGACY_ANALYSIS_MODE_ALIASES.get(raw, raw)
    return canonical if canonical in GUIDED_ANALYSIS_MODES else "quick_summary"


def build_analysis_mode_contract(mode: str | None) -> dict[str, Any]:
    canonical = normalize_analysis_mode(mode)
    contracts: dict[str, dict[str, Any]] = {
        "quick_summary": {
            "label": "빠른 요약",
            "question_depth": "minimum",
            "visible_sections": [
                "headline",
                "accident_type",
                "fault_ratio",
                "short_reason",
                "must_check",
                "knia_link",
            ],
            "hidden_sections": ["long_legal_basis", "raw_evidence", "developer_diagnostics"],
            "max_reason_lines": 3,
        },
        "fault_ratio_focused": {
            "label": "과실비율 중심",
            "question_depth": "knia_adjustments",
            "visible_sections": [
                "base_fault",
                "applied_adjustments",
                "not_applied_adjustments",
                "final_fault",
                "fault_up_down_factors",
                "knia_link",
            ],
            "hidden_sections": ["developer_diagnostics"],
        },
        "legal_precedent_focused": {
            "label": "법률/판례 근거 중심",
            "question_depth": "legal_and_knia",
            "visible_sections": [
                "fault_ratio",
                "knia_basis",
                "related_laws",
                "precedents",
                "legal_issues",
                "additional_evidence",
                "knia_link",
            ],
            "hidden_sections": ["developer_diagnostics"],
        },
        "insurance_response_focused": {
            "label": "보험 대응 중심",
            "question_depth": "insurance_practical",
            "visible_sections": [
                "fault_ratio",
                "insurer_talking_points",
                "documents",
                "response_points",
                "treatment_repair_rental_guidance",
                "knia_link",
            ],
            "hidden_sections": ["developer_diagnostics"],
        },
        "full_deep_research": {
            "label": "전체 심층 리서치 분석",
            "question_depth": "full",
            "visible_sections": [
                "facts",
                "video_observations",
                "scenario",
                "knia_basis",
                "fault_adjustments",
                "legal_precedent",
                "insurance_response",
                "additional_checks",
                "evidence_list",
                "knia_link",
            ],
            "collapsible_long_sections": True,
            "hidden_sections": ["developer_diagnostics"],
        },
    }
    return {"mode": canonical, **contracts[canonical]}
