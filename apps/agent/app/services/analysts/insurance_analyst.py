from __future__ import annotations

from typing import Any

from app.services.analyst_output_guard import guard_insurance_output
from app.services.llm_client import generate_insurance_analysis
from app.services.llm_policy import attach_llm_usage, evaluate_llm_usage, mark_llm_output_unavailable


def analyze_insurance(
    *,
    scenario_type: str,
    facts: dict[str, Any],
    evidence: list[dict[str, Any]],
    text: str,
) -> dict[str, Any]:
    llm_usage = evaluate_llm_usage(section="insurance_guidance", evidence=evidence, facts=facts)
    llm = generate_insurance_analysis(text=text, scenario_type=scenario_type, facts=facts, evidence=evidence) if llm_usage["allowed"] else None
    if llm:
        return attach_llm_usage(guard_insurance_output(llm, evidence), llm_usage, used=True)
    if llm_usage["allowed"]:
        llm_usage = mark_llm_output_unavailable(llm_usage, stage="insurance_guidance")
    claim_type = ["대물"]
    if facts.get("injury"):
        claim_type.append("대인")
    return attach_llm_usage(guard_insurance_output({
        "summary": "보험 접수 후 대물/대인 여부를 구분하고 증빙을 단계적으로 확보하세요.",
        "claim_type": claim_type,
        "steps": ["보험사 사고접수번호 발급", "블랙박스 원본/대표 프레임 제출", "현장 사진과 목격자 정보 정리", "수리 견적서와 진단서 확보"],
        "required_documents": ["블랙박스 원본", "사고 현장 사진", "차량 파손 사진", "수리 견적서", "진단서 또는 진료확인서(부상 시)", "보험 사고접수번호"],
        "settlement_example": "치료비, 수리비, 휴업손해, 위자료 등은 증빙과 보험사 심사에 따라 달라지며 확정 금액처럼 보아서는 안 됩니다.",
        "next_steps": ["대인 접수 필요 여부 확인", "수리 견적 1차 확보", "과실비율 분쟁 시 근거 자료 제출"],
    }, evidence), llm_usage, used=False)
