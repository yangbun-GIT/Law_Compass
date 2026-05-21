from __future__ import annotations

from typing import Any

from app.services.chat.chat_service_guide import service_guide
from app.services.accident_party_action_guide import build_party_type_action_guide


def build_chat_reply(intent: str, message: str, draft_case: dict[str, Any] | None, knia_primary: dict[str, Any] | None, safety: dict[str, Any]) -> str:
    if not safety.get("allowed"):
        return safety.get("safe_reply") or "그 요청은 도와드릴 수 없습니다. 안전한 사고 대응 방법은 안내해 드릴 수 있습니다."
    prefix = ""
    if safety.get("severity") == "medium" and safety.get("safe_reply"):
        prefix = safety["safe_reply"] + "\n\n"
    if intent in {"accident_quick_help", "create_case_draft"} and draft_case:
        facts = draft_case.get("structured_facts") or {}
        guide = build_party_type_action_guide(facts.get("accident_party_type", "unknown"), facts, facts.get("accident_type"))
        actions = guide.get("top_actions") or ["블랙박스 원본을 보관하세요.", "다친 사람이 있으면 병원 진료를 받아두세요.", "보험사에 사고를 접수하세요."]
        lines = [
            _scenario_sentence(draft_case),
            "먼저 아래 3가지를 해 주세요.",
            f"1. {actions[0]}",
            f"2. {actions[1] if len(actions) > 1 else '다친 사람이 있는지 확인하세요.'}",
            f"3. {actions[2] if len(actions) > 2 else '보험사에 사고를 접수하세요.'}",
            "",
            "채팅 내용을 바탕으로 사고 입력 초안도 만들었습니다.",
        ]
        if knia_primary:
            lines.extend([
                "",
                "입력하신 상황과 비슷한 과실비율 인정기준도 찾았습니다.",
                f"'{knia_primary.get('chart_no')} {knia_primary.get('title')}' 기준을 참고할 수 있습니다.",
                "관련 기준과 영상은 원본 사이트 링크로 확인할 수 있습니다.",
            ])
        return prefix + "\n".join(lines)
    if intent == "knia_fault_standard_help":
        if knia_primary:
            return prefix + f"입력하신 내용과 비슷한 과실비율 기준을 찾았습니다.\n'{knia_primary.get('chart_no')} {knia_primary.get('title')}' 기준입니다.\n원문 기준과 관련 영상 링크를 함께 확인해 보실 수 있습니다.\n\n단, 최종 과실비율은 보험사나 분쟁심의 결과에 따라 달라질 수 있습니다."
        return prefix + "비슷한 사고 기준을 찾으려면 사고 상황을 한두 문장으로 적어 주세요. 많이 검색된 사고유형 페이지에서도 대표 기준을 볼 수 있습니다."
    if intent == "smalltalk":
        return prefix + service_guide(intent, message)
    if intent == "unsupported":
        return prefix + service_guide(intent, message)
    return prefix + service_guide(intent, message)


def _scenario_sentence(draft_case: dict[str, Any]) -> str:
    facts = draft_case.get("structured_facts") or {}
    accident_type = facts.get("accident_type")
    party = facts.get("accident_party_type")
    if party == "car_vs_person":
        return "차대사람 사고일 수 있습니다. 먼저 다친 사람이 있는지 확인하고, 필요하면 119와 112에 신고해 주세요."
    if party == "car_vs_bicycle":
        return "차대자전거 사고로 보입니다. 먼저 자전거 운전자가 다쳤는지 확인해 주세요."
    if party == "car_vs_object":
        return "차대기물 사고로 보입니다. 안전한 곳으로 이동하고 시설물 파손 사진을 남겨 주세요."
    if party == "single_vehicle":
        return "차량단독 사고로 보입니다. 부상 여부와 2차 사고 위험을 먼저 확인해 주세요."
    if accident_type == "rear_end_collision":
        return "후미추돌 사고로 보입니다. 뒤차의 안전거리 유지 여부가 중요합니다."
    if accident_type == "lane_change_collision":
        return "차선변경 사고로 보입니다. 방향지시등과 진입 시점이 중요합니다."
    if accident_type == "intersection_collision":
        return "교차로 사고로 보입니다. 신호 상태와 진입 시점이 중요합니다."
    if facts.get("school_zone"):
        return "어린이보호구역 사고로 보입니다. 신고와 형사 문제 확인이 필요할 수 있습니다."
    return "교통사고 상황으로 보입니다. 입력 내용을 바탕으로 차근차근 정리해 드릴게요."
