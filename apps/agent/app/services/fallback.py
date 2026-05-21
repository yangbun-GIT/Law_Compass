from typing import Any


def build_fallback(facts: dict[str, Any]) -> dict[str, Any]:
    return {
        "accident_summary": facts.get("summary", "정보 부족으로 요약 실패"),
        "structured_facts": facts,
        "fault_ratio": {"estimate": "불충분", "confidence": 0.2, "reason": "근거가 부족합니다."},
        "insurance_guide": {"summary": "기본 접수 및 증빙 확보를 우선하세요.", "steps": ["보험사 사고 접수", "증빙자료 보관"]},
        "legal_liability": {"reporting_required": "추가 확인 필요", "checklist": ["인명피해 여부", "도주/음주 여부"]},
        "action_plan": ["추가 사실을 입력하면 정확도를 개선할 수 있습니다."],
        "evidence": [],
        "uncertainty": {"level": "high", "reason": "facts/evidence 부족"},
        "disclaimers": ["법률 자문이 아닙니다."],
        "followup_questions": ["사고 당시 신호 상태는 어땠나요?", "상대 차량의 차선 변경 여부가 있나요?"],
        "model_info": {"orchestrator": "lawcompass-tpg-v1", "fallback": True},
    }

