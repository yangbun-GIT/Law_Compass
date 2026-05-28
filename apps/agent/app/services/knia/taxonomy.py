from __future__ import annotations

from typing import Any

ATTRIBUTION = "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털"

PARTY_TYPES: dict[str, dict[str, Any]] = {
    "car_vs_car": {
        "label": "차대차 사고",
        "description": "자동차와 자동차 사이의 사고입니다.",
        "keywords": ["차대차", "후미추돌", "차선변경", "진로변경", "교차로", "신호위반", "좌회전", "우회전", "직진", "끼어들기", "주정차 차량 충돌"],
        "actions": ["블랙박스 원본을 보관하세요.", "상대 차량 번호와 연락처를 확인하세요.", "보험사에 사고를 접수하고 사고접수번호를 기록하세요.", "차량 파손 사진과 현장 사진을 저장하세요."],
    },
    "car_vs_person": {
        "label": "차대사람 사고",
        "description": "자동차와 보행자 사이의 사고입니다.",
        "keywords": ["차대사람", "보행자", "무단횡단", "어린이보호구역", "민식이법", "보행자 보호의무", "인명피해", "사람"],
        "actions": ["먼저 다친 사람이 있는지 확인하세요.", "필요하면 119와 112에 신고하세요.", "보행자의 상태와 사고 위치를 기록하세요.", "블랙박스 원본과 현장 사진을 보관하세요."],
    },
    "car_vs_bicycle": {
        "label": "차대자전거 사고",
        "description": "자동차와 자전거 사이의 사고입니다.",
        "keywords": ["차대자전거", "자전거", "자전거도로", "우회전 자전거", "횡단보도 자전거", "측면 충돌", "자전거 운전자"],
        "actions": ["자전거 운전자의 부상 여부를 먼저 확인하세요.", "필요하면 119와 112에 신고하세요.", "자전거 진행 방향과 충돌 위치를 기록하세요.", "블랙박스와 현장 사진을 보관하세요."],
    },
    "car_vs_motorcycle": {
        "label": "차대오토바이 사고",
        "description": "자동차와 오토바이 또는 이륜차 사이의 사고입니다.",
        "keywords": ["차대오토바이", "차대이륜차", "오토바이", "이륜차", "원동기장치자전거", "바이크"],
        "actions": ["이륜차 운전자의 부상 여부를 먼저 확인하세요.", "필요하면 119와 112에 신고하세요.", "진행 방향과 충돌 위치를 기록하세요.", "블랙박스와 현장 사진을 보관하세요."],
    },
    "car_vs_object": {
        "label": "차대기물 사고",
        "description": "자동차와 시설물, 가드레일, 전봇대, 주차장 기둥 같은 물체 사이의 사고입니다.",
        "keywords": ["차대기물", "기물", "가드레일", "전봇대", "중앙분리대", "벽", "주차장 기둥", "시설물", "도로 시설물", "낙하물", "물체 충돌"],
        "actions": ["차량 이동이 위험하면 안전한 곳으로 대피하세요.", "파손된 시설물 또는 물체 사진을 촬영하세요.", "보험사에 단독 또는 기물 사고로 접수하세요.", "도로 시설물 파손이 있으면 관리기관 또는 경찰 신고를 검토하세요."],
    },
    "single_vehicle": {
        "label": "차량단독 사고",
        "description": "다른 차량이나 보행자 없이 혼자 발생한 사고입니다.",
        "keywords": ["차량단독", "단독사고", "혼자", "미끄러짐", "빗길", "눈길", "졸음운전", "운전미숙", "전복", "도로 이탈"],
        "actions": ["운전자와 동승자의 부상 여부를 확인하세요.", "차량이 도로에 위험하게 멈춰 있다면 안전 조치를 하세요.", "보험사에 단독사고로 접수하세요.", "블랙박스 원본과 사고 장소 사진을 보관하세요."],
    },
    "unknown": {
        "label": "사고유형 확인 필요",
        "description": "사고 상대와 상황을 조금 더 확인해야 합니다.",
        "keywords": ["사고유형 확인"],
        "actions": ["사고 상대가 차량인지, 사람인지, 자전거인지, 기물인지 확인해 주세요.", "블랙박스와 현장 사진을 보관하세요.", "다친 사람이 있으면 먼저 구호와 신고를 검토하세요."],
    },
}

PRIORITY = ["car_vs_person", "car_vs_bicycle", "car_vs_motorcycle", "car_vs_object", "single_vehicle", "car_vs_car"]

DISPLAY_TAG_RULES: list[tuple[str, list[str]]] = [
    ("후미추돌", ["후미", "뒤차", "후방", "안전거리", "추돌"]),
    ("정차 중", ["정차", "신호대기", "서행"]),
    ("차선변경", ["차선", "진로변경", "끼어", "방향지시등"]),
    ("교차로", ["교차로", "좌회전", "우회전", "직진"]),
    ("신호위반", ["신호위반", "빨간불", "적색"]),
    ("횡단보도", ["횡단보도"]),
    ("보행자", ["보행자", "사람", "어린이"]),
    ("자전거", ["자전거"]),
    ("오토바이", ["오토바이", "이륜차", "원동기장치자전거"]),
    ("기물", ["기물", "시설물", "가드레일", "전봇대", "중앙분리대", "벽", "기둥"]),
    ("단독사고", ["단독", "혼자", "전복", "미끄러짐", "도로 이탈", "빗길", "눈길"]),
]

def party_label(accident_party_type: str | None) -> str:
    return PARTY_TYPES.get(accident_party_type or "unknown", PARTY_TYPES["unknown"])["label"]

def party_description(accident_party_type: str | None) -> str:
    return PARTY_TYPES.get(accident_party_type or "unknown", PARTY_TYPES["unknown"])["description"]

def party_actions(accident_party_type: str | None) -> list[str]:
    return list(PARTY_TYPES.get(accident_party_type or "unknown", PARTY_TYPES["unknown"])["actions"])

def infer_display_tags(text: str, limit: int = 6) -> list[str]:
    tags: list[str] = []
    hay = text or ""
    for label, words in DISPLAY_TAG_RULES:
        if any(word in hay for word in words) and label not in tags:
            tags.append(label)
    return tags[:limit]

def classify_knia_accident_party_type(chart_data: dict[str, Any]) -> dict[str, Any]:
    parts: list[str] = []
    for key in ["title", "accident_summary", "applicable_text", "non_applicable_text", "basic_fault_text", "chart_no"]:
        value = chart_data.get(key)
        if value:
            parts.append(str(value))
    for value in chart_data.get("category_path") or []:
        parts.append(str(value))
    for value in chart_data.get("keywords") or []:
        parts.append(str(value))
    text = " ".join(parts)
    party = infer_party_type_from_text(text, chart_data)
    label = party_label(party)
    tags = infer_display_tags(text)
    if label not in tags and party != "unknown":
        tags.insert(0, label)
    return {
        "accident_party_type": party,
        "accident_party_label": label,
        "display_tags": tags[:8],
        "scenario_summary_easy": party_description(party),
        "recommended_user_actions": party_actions(party),
        "vehicle_a_role": _vehicle_role_a(party),
        "vehicle_b_role": _vehicle_role_b(party),
        "vulnerable_road_user_type": _vulnerable_type(party),
        "object_type": _object_type(text) if party == "car_vs_object" else None,
    }

def infer_party_type_from_text(text: str, facts: dict[str, Any] | None = None) -> str:
    facts = facts or {}
    hay = " ".join([text or "", str(facts)]).lower()
    declared_party = str(facts.get("accident_party_type") or "").strip().lower()
    if declared_party in {"car_vs_parked_vehicle", "vehicle", "car", "truck", "parked_vehicle", "stopped_vehicle"}:
        return "car_vs_car"
    if facts.get("accident_party_type") in PARTY_TYPES:
        return str(facts["accident_party_type"])
    if str(facts.get("accident_type") or "").strip().lower() == "stealth_illegal_parked_vehicle_collision":
        return "car_vs_car"
    partner_type = str(facts.get("collision_partner_type") or "").strip().lower()
    if partner_type in {"vehicle", "car", "truck", "bus", "van", "motor_vehicle", "other_vehicle", "parked_vehicle", "stopped_vehicle"}:
        return "car_vs_car"
    if partner_type in {"pedestrian", "person"}:
        return "car_vs_person"
    direct_bicycle_collision_text = any(
        token in hay
        for token in ("자전거와 충돌", "자전거와 부딪", "자전거를 쳤", "자전거 추돌", "hit bicycle", "collided with bicycle")
    )
    if partner_type in {"bicycle", "bike", "cyclist"} and direct_bicycle_collision_text:
        return "car_vs_bicycle"
    if partner_type in {"motorcycle", "two_wheeler", "motorbike"}:
        return "car_vs_motorcycle"
    if any(token in hay for token in ("트럭", "화물차", "주차", "정차", "스텔스", "무등화", "교량 아래", "교량 밑", "화단")):
        return "car_vs_car"
    if partner_type in {"object", "fixed_object", "road_object", "obstacle"}:
        return "car_vs_object"
    if facts.get("pedestrian") or facts.get("pedestrian_visible") or facts.get("victim_is_child"):
        return "car_vs_person"
    if facts.get("accident_type") in {"pedestrian", "pedestrian_crosswalk_accident", "school_zone_child_accident"}:
        return "car_vs_person"
    if facts.get("accident_type") in {"intersection_collision", "intersection_signal_violation"}:
        return "car_vs_car"
    if facts.get("accident_type") == "bicycle_collision" and direct_bicycle_collision_text:
        return "car_vs_bicycle"
    if facts.get("accident_type") == "object_collision":
        return "car_vs_object"
    if facts.get("accident_type") == "single_vehicle_accident":
        return "single_vehicle"
    if facts.get("intersection") or facts.get("centerline_crossed") or facts.get("opposing_vehicle_present"):
        return "car_vs_car"
    checks = [
        ("car_vs_person", ["차대사람", "보행자", "무단횡단", "어린이보호구역", "민식이", "사람을", "사람과", "아이와", "인명피해"]),
        ("car_vs_bicycle", ["차대자전거", "자전거와 충돌", "자전거를 쳤", "자전거 추돌", "자전거 운전자"]),
        ("car_vs_motorcycle", ["차대오토바이", "차대이륜차", "오토바이", "이륜차", "원동기장치자전거", "바이크"]),
        ("car_vs_object", ["차대기물", "기물", "시설물", "가드레일", "전봇대", "중앙분리대", "주차장 기둥", "벽", "낙하물", "물체"]),
        ("single_vehicle", ["차량단독", "단독사고", "혼자", "미끄러", "빗길", "눈길", "졸음운전", "운전미숙", "전복", "도로 이탈"]),
        ("car_vs_car", ["차대차", "후미", "뒤차", "차선변경", "진로변경", "교차로", "신호위반", "좌회전", "우회전", "직진", "끼어들", "차량", "car-to-car", "vehicle", "intersection", "left-turn", "straight vehicle"]),
    ]
    for party in PRIORITY:
        words = next((w for p, w in checks if p == party), [])
        if any(word.lower() in hay for word in words):
            return party
    return "unknown"

def _vehicle_role_a(party: str) -> str | None:
    return {
        "car_vs_car": "A차량",
        "car_vs_person": "차량",
        "car_vs_bicycle": "차량",
        "car_vs_motorcycle": "차량",
        "car_vs_object": "차량",
        "single_vehicle": "사고 차량",
    }.get(party)

def _vehicle_role_b(party: str) -> str | None:
    return {
        "car_vs_car": "B차량",
        "car_vs_person": "보행자",
        "car_vs_bicycle": "자전거 운전자",
        "car_vs_motorcycle": "오토바이 운전자",
        "car_vs_object": "시설물 또는 물체",
        "single_vehicle": "없음",
    }.get(party)

def _vulnerable_type(party: str) -> str | None:
    return {"car_vs_person": "보행자", "car_vs_bicycle": "자전거 운전자", "car_vs_motorcycle": "오토바이 운전자"}.get(party)

def _object_type(text: str) -> str | None:
    for word in ["가드레일", "전봇대", "중앙분리대", "주차장 기둥", "기둥", "벽", "시설물", "낙하물"]:
        if word in text:
            return word
    return "시설물 또는 물체"
