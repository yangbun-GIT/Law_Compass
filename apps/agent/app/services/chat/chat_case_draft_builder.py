from __future__ import annotations

from typing import Any


def build_case_draft(message: str, context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    text = message or ""
    injury = _has_any(text, ["아파", "통증", "다쳤", "병원", "진단서", "목", "허리", "부상"])
    has_blackbox = _has_any(text, ["블랙박스", "영상", "동영상"])

    if _has_any(text, ["보행자", "횡단보도", "사람을", "사람과", "사람 친", "아이", "어린이보호구역", "스쿨존", "민식이"]):
        school_zone = _has_any(text, ["어린이보호구역", "스쿨존", "민식이", "아이"])
        return {
            "title": "어린이보호구역 보행자 사고" if school_zone else "차량과 보행자 접촉 사고",
            "description_text": _normalize_description(text, "차량과 보행자 사이에 접촉 사고가 발생했습니다."),
            "structured_facts": {
                "accident_type": "school_zone_child_accident" if school_zone else "pedestrian_crosswalk_accident",
                "accident_party_type": "car_vs_person",
                "pedestrian": True,
                "school_zone": school_zone,
                "victim_is_child": school_zone or None,
                "crosswalk_nearby": _has_any(text, ["횡단보도"]),
                "injury": True if injury or school_zone else None,
                "signal_state": "unknown",
                "blackbox": True if has_blackbox else None,
            },
            "selected_keywords": ["차대사람", "보행자", "횡단보도", "부상확인", "신고", "블랙박스"],
            "analysis_mode": "criminal-liability-focused",
            "ai_profile": "pedestrian_focus",
            "followup_questions": ["보행자가 다쳤나요?", "횡단보도나 어린이보호구역이었나요?", "119나 112 신고를 했나요?"],
        }
    if _has_any(text, ["자전거", "자전거도로"]):
        return {
            "title": "차량과 자전거 충돌 사고",
            "description_text": _normalize_description(text, "차량과 자전거가 충돌한 사고입니다."),
            "structured_facts": {"accident_type": "bicycle_collision", "accident_party_type": "car_vs_bicycle", "injury": True if injury else None, "blackbox": True if has_blackbox else None},
            "selected_keywords": ["차대자전거", "자전거", "부상확인", "블랙박스", "과실비율"],
            "analysis_mode": "fault-focused",
            "ai_profile": "pedestrian_focus",
            "followup_questions": ["자전거 운전자가 다쳤나요?", "자전거 진행 방향은 어땠나요?", "자전거도로 또는 횡단보도였나요?"],
        }
    if _has_any(text, ["가드레일", "전봇대", "중앙분리대", "시설물", "기물", "기둥", "벽", "낙하물"]):
        return {
            "title": "차량과 시설물 충돌 사고",
            "description_text": _normalize_description(text, "차량이 시설물 또는 기물과 충돌한 사고입니다."),
            "structured_facts": {"accident_type": "object_collision", "accident_party_type": "car_vs_object", "object_collision": True, "injury": True if injury else None, "blackbox": True if has_blackbox else None},
            "selected_keywords": ["차대기물", "시설물", "파손사진", "단독사고", "보험접수"],
            "analysis_mode": "insurance-focused",
            "ai_profile": "default_vehicle_collision",
            "followup_questions": ["다친 사람이 있나요?", "어떤 시설물이 파손됐나요?", "차량이 도로 위에 위험하게 멈춰 있나요?"],
        }
    if _has_any(text, ["혼자", "단독", "미끄러", "빗길", "눈길", "전복", "도로 이탈", "졸음"]):
        return {
            "title": "차량단독 사고",
            "description_text": _normalize_description(text, "다른 차량 없이 혼자 발생한 차량단독 사고입니다."),
            "structured_facts": {"accident_type": "single_vehicle_accident", "accident_party_type": "single_vehicle", "single_vehicle": True, "injury": True if injury else None, "blackbox": True if has_blackbox else None},
            "selected_keywords": ["차량단독", "단독사고", "2차사고방지", "블랙박스", "보험접수"],
            "analysis_mode": "insurance-focused",
            "ai_profile": "default_vehicle_collision",
            "followup_questions": ["운전자나 동승자가 다쳤나요?", "차량 이동이 가능한가요?", "노면 상태는 빗길이나 눈길이었나요?"],
        }
    if _has_any(text, ["후미", "뒤차", "뒤에서", "뒤 차량", "박았", "추돌"]):
        signal = "red" if _has_any(text, ["신호대기", "빨간불", "적색", "정차"] ) else "unknown"
        stopped = _has_any(text, ["정차", "신호대기", "멈춰", "서 있었"])
        return {
            "title": "정차 중 후미추돌 사고" if stopped else "후미추돌 사고",
            "description_text": _normalize_description(text, "신호대기 또는 정차 중 뒤 차량이 후미를 추돌했습니다."),
            "structured_facts": {"accident_type": "rear_end_collision", "accident_party_type": "car_vs_car", "stopped": stopped, "opponent_behavior": "rear_collision", "signal_state": signal, "injury": True if injury else None, "blackbox": True if has_blackbox else None},
            "selected_keywords": ["후미추돌", "정차중", "안전거리", "블랙박스", "대인접수", "진단서"] if injury else ["후미추돌", "정차중", "안전거리", "블랙박스", "보험접수"],
            "analysis_mode": "fault-focused",
            "ai_profile": "rear_end_focus",
            "followup_questions": ["사고 당시 완전히 정차 중이었나요?", "목이나 허리 통증이 있나요?", "블랙박스 영상이 있나요?"],
        }
    if _has_any(text, ["신호위반", "빨간불", "적색", "교차로"]):
        return {
            "title": "교차로 신호위반 의심 사고",
            "description_text": _normalize_description(text, "교차로에서 상대 차량의 신호위반이 의심되는 충돌 사고입니다."),
            "structured_facts": {"accident_type": "intersection_collision", "accident_party_type": "car_vs_car", "intersection": True, "opponent_signal_violation": _has_any(text, ["상대", "빨간불", "신호위반"]), "injury": True if injury else None, "signal_state": "green" if _has_any(text, ["내 신호", "초록", "녹색"] ) else "unknown"},
            "selected_keywords": ["신호위반", "교차로", "우선권", "과실비율", "블랙박스"],
            "analysis_mode": "fault-focused",
            "ai_profile": "intersection_focus",
            "followup_questions": ["내 차량 신호는 어떤 색이었나요?", "상대 차량 신호위반 장면이 영상에 있나요?"],
        }
    if _has_any(text, ["차선", "진로변경", "끼어", "방향지시등", "깜빡이"]):
        return {
            "title": "차선변경 중 충돌 사고",
            "description_text": _normalize_description(text, "상대 차량의 차선변경 또는 진로변경 중 충돌한 사고입니다."),
            "structured_facts": {"accident_type": "lane_change_collision", "accident_party_type": "car_vs_car", "lane_change": True, "turn_signal": False if _has_any(text, ["방향지시등 없이", "깜빡이 없이"] ) else None, "side_collision": True, "injury": True if injury else None},
            "selected_keywords": ["차선변경", "방향지시등", "진로변경", "측면충돌", "과실비율"],
            "analysis_mode": "fault-focused",
            "ai_profile": "lane_change_focus",
            "followup_questions": ["상대 차량이 방향지시등을 켰나요?", "충돌 위치가 측면인가요?"],
        }
    if _has_any(text, ["주차", "정차 중", "주정차"]):
        return {
            "title": "주정차 중 접촉 사고",
            "description_text": _normalize_description(text, "주차 또는 정차 중 접촉 사고가 발생했습니다."),
            "structured_facts": {"accident_type": "parking_or_stopped_vehicle_accident", "accident_party_type": "car_vs_car", "stopped": True, "injury": True if injury else None},
            "selected_keywords": ["주정차", "접촉사고", "블랙박스", "보험접수"],
            "analysis_mode": "quick_summary",
            "ai_profile": "default_vehicle_collision",
            "followup_questions": ["차량이 합법적으로 정차 중이었나요?", "상대 차량 연락처를 확보했나요?"],
        }
    return None


def _has_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def _normalize_description(text: str, fallback: str) -> str:
    clean = " ".join((text or "").split())
    return clean if len(clean) >= 8 else fallback
