from __future__ import annotations

from typing import Any

from app.services.llm_client import generate_action_plan


def analyze_action_plan(
    *,
    scenario_type: str,
    facts: dict[str, Any],
    legal_liability: dict[str, Any],
    insurance_guide: dict[str, Any],
    evidence: list[dict[str, Any]],
    text: str,
) -> list[str]:
    llm = generate_action_plan(text=text, scenario_type=scenario_type, facts=facts, evidence=evidence)
    if isinstance(llm, dict) and isinstance(llm.get("action_plan"), list):
        return [str(x) for x in llm["action_plan"]]
    actions = ["블랙박스 원본과 추출된 대표 프레임을 보관하세요.", "보험사에 사고를 접수하고 사고접수번호를 기록하세요.", "차량 파손 사진과 수리 견적서를 확보하세요."]
    if facts.get("injury"):
        actions.insert(1, "통증이 있다면 병원 진료를 받고 진단서 또는 진료확인서를 확보하세요.")
    if legal_liability.get("reporting_required"):
        actions.append("인명피해, 12대 중과실, 도주/음주/무면허 의심이 있으면 경찰 신고를 검토하세요.")
    if scenario_type == "school_zone_child_accident":
        actions.append("어린이보호구역 표지, 제한속도, 피해자 나이, 상해 여부를 즉시 정리하세요.")
    return actions
