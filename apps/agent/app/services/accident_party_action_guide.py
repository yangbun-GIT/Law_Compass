from __future__ import annotations
from typing import Any
from app.services.knia.taxonomy import party_actions, party_description, party_label

GUIDE_META = {
    "car_vs_car": {
        "title": "차대차 사고 조치 안내",
        "summary": "자동차와 자동차 사이의 사고는 블랙박스, 상대 차량 정보, 보험 접수가 중요합니다.",
        "cautions": ["현장에서 감정적으로 과실을 확정하지 마세요.", "블랙박스 원본을 편집하지 말고 보관하세요."],
        "needed_info": ["정차 여부", "신호 상태", "차선변경 여부", "상대 차량 번호", "블랙박스 영상"],
    },
    "car_vs_person": {
        "title": "차대사람 사고 조치 안내",
        "summary": "보행자와 관련된 사고는 다친 사람 확인과 신고 여부 확인이 가장 중요합니다.",
        "cautions": ["절대 현장을 떠나지 마세요.", "상태가 가벼워 보여도 병원 진료와 신고가 필요할 수 있습니다."],
        "needed_info": ["보행자 부상 여부", "횡단보도 여부", "신호 상태", "어린이보호구역 여부", "경찰 신고 여부"],
    },
    "car_vs_bicycle": {
        "title": "차대자전거 사고 조치 안내",
        "summary": "자전거 운전자의 부상 여부와 자전거 진행 방향을 먼저 확인해야 합니다.",
        "cautions": ["자전거 사고도 인명피해가 있으면 신고가 필요할 수 있습니다.", "자전거 파손 상태와 위치를 사진으로 남겨두세요."],
        "needed_info": ["자전거 운전자 부상 여부", "자전거도로 여부", "진행 방향", "충돌 위치", "블랙박스 영상"],
    },
    "car_vs_object": {
        "title": "차대기물 사고 조치 안내",
        "summary": "시설물이나 물체를 들이받은 사고는 안전 확보와 파손 사진 기록이 중요합니다.",
        "cautions": ["도로 위에 차량이 멈춰 있으면 2차 사고 위험이 있습니다.", "공공 시설물 파손은 관리기관이나 경찰 신고가 필요할 수 있습니다."],
        "needed_info": ["파손된 물체 종류", "사고 위치", "노면 상태", "차량 파손 사진", "관리기관 연락 여부"],
    },
    "single_vehicle": {
        "title": "차량단독 사고 조치 안내",
        "summary": "혼자 발생한 사고는 부상 확인, 2차 사고 방지, 보험 접수가 중요합니다.",
        "cautions": ["비상등과 안전삼각대 등으로 2차 사고를 막아야 합니다.", "빗길, 눈길, 졸음 등 원인을 기록해 두세요."],
        "needed_info": ["운전자와 동승자 부상 여부", "노면 상태", "사고 위치", "블랙박스 영상", "차량 이동 가능 여부"],
    },
    "unknown": {
        "title": "사고유형 확인 안내",
        "summary": "사고 상대가 차량, 사람, 자전거, 기물 중 무엇인지 확인이 필요합니다.",
        "cautions": ["다친 사람이 있으면 먼저 구호와 신고를 검토하세요."],
        "needed_info": ["사고 상대", "부상 여부", "블랙박스 여부", "사고 장소"],
    },
}

def build_party_type_action_guide(accident_party_type: str, facts: dict[str, Any] | None = None, scenario_type: str | None = None) -> dict[str, Any]:
    facts = facts or {}
    party = accident_party_type or "unknown"
    meta = GUIDE_META.get(party, GUIDE_META["unknown"])
    needed = list(meta["needed_info"])
    if facts.get("injury") is None and "부상 여부" not in " ".join(needed):
        needed.insert(0, "다친 사람이 있는지")
    return {
        "title": meta["title"],
        "label": party_label(party),
        "summary": meta["summary"] or party_description(party),
        "top_actions": party_actions(party),
        "cautions": meta["cautions"],
        "needed_info": needed[:6],
        "scenario_type": scenario_type,
    }
