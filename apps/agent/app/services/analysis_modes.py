from __future__ import annotations

from typing import Any


USER_FRIENDLY_MODE = "user_friendly"
EXPERT_MODE = "expert"

GUIDED_ANALYSIS_MODES = {
    USER_FRIENDLY_MODE,
    EXPERT_MODE,
}

LEGACY_ANALYSIS_MODE_ALIASES = {
    "quick_summary": USER_FRIENDLY_MODE,
    "fault_ratio_focused": USER_FRIENDLY_MODE,
    "insurance_response_focused": USER_FRIENDLY_MODE,
    "fast": USER_FRIENDLY_MODE,
    "summary": USER_FRIENDLY_MODE,
    "quick": USER_FRIENDLY_MODE,
    "fault-focused": USER_FRIENDLY_MODE,
    "fault_ratio": USER_FRIENDLY_MODE,
    "insurance-focused": USER_FRIENDLY_MODE,
    "insurance_response": USER_FRIENDLY_MODE,
    "legal_precedent_focused": EXPERT_MODE,
    "full_deep_research": EXPERT_MODE,
    "deep_research": EXPERT_MODE,
    "debug": EXPERT_MODE,
    "legal-focused": EXPERT_MODE,
    "legal_precedent": EXPERT_MODE,
    "criminal-liability-focused": EXPERT_MODE,
    "evidence-review": EXPERT_MODE,
    "deep": EXPERT_MODE,
    "full": EXPERT_MODE,
    "research": EXPERT_MODE,
}


def normalize_analysis_mode(value: str | None) -> str:
    raw = (value or USER_FRIENDLY_MODE).strip()
    if raw in GUIDED_ANALYSIS_MODES:
        return raw
    return LEGACY_ANALYSIS_MODE_ALIASES.get(raw, USER_FRIENDLY_MODE)


def is_expert_mode(mode: str | None) -> bool:
    return normalize_analysis_mode(mode) == EXPERT_MODE


def is_user_friendly_mode(mode: str | None) -> bool:
    return normalize_analysis_mode(mode) == USER_FRIENDLY_MODE


def build_analysis_mode_contract(mode: str | None) -> dict[str, Any]:
    canonical = normalize_analysis_mode(mode)
    contracts: dict[str, dict[str, Any]] = {
        USER_FRIENDLY_MODE: {
            "label": "일반사용자모드",
            "question_depth": "minimum",
            "visible_sections": [
                "current_situation",
                "fault_ratio",
                "knia_and_video",
            ],
            "hidden_sections": [
                "raw_evidence",
                "developer_diagnostics",
                "model_info",
                "token_usage",
                "internal_trace",
                "long_legal_basis",
            ],
            "max_reason_lines": 5,
            "compact": True,
        },
        EXPERT_MODE: {
            "label": "전문가모드",
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
            "hidden_sections": ["developer_diagnostics"],
            "collapsible_long_sections": True,
            "compact": False,
        },
    }
    return {"mode": canonical, **contracts[canonical]}
