from __future__ import annotations

import re
from typing import Any

SCENARIO_LABELS = {
    "rear_end_collision": "후미추돌 사고",
    "school_zone_child_accident": "어린이보호구역 사고",
    "intersection_signal_violation": "교차로 신호위반 사고",
    "lane_change_collision": "차선변경 사고",
    "pedestrian_crosswalk_accident": "보행자 사고",
    "drunk_or_unlicensed_accident": "음주 또는 무면허 의심 사고",
    "hit_and_run_risk": "사고 후 미조치 의심 사고",
    "parking_or_stopped_vehicle_accident": "중앙선·정차 차량 관련 차대차 사고",
    "general_vehicle_collision": "차량 충돌 사고",
}

RISK_LABELS = {"low": "낮음", "medium": "보통", "high": "높음", "unknown": "확인 필요", "very_high": "매우 높음", "none": "낮음"}

RULE_LABELS = {
    "ROAD_ACCIDENT_REPORTING_DUTY": "사고 후 정차하고 필요한 조치를 해야 하는 의무",
    "SAFE_DRIVING_DUTY": "주변을 잘 살피며 안전하게 운전해야 하는 의무",
    "SIGNAL_VIOLATION": "신호를 지켜야 하는 의무",
    "CENTER_LINE_VIOLATION": "중앙선을 넘지 않아야 하는 의무",
    "CROSSWALK_PEDESTRIAN_PROTECTION": "횡단보도에서 보행자를 보호해야 하는 의무",
    "SCHOOL_ZONE_CHILD_PROTECTION": "어린이보호구역에서 더 조심해야 하는 의무",
    "TWELVE_GROSS_NEGLIGENCE": "큰 위반이 있는 사고인지 확인해야 하는 기준",
    "DRUNK_DRIVING_RISK": "음주운전 여부 확인",
    "UNLICENSED_DRIVING_RISK": "무면허 운전 여부 확인",
    "HIT_AND_RUN_RISK": "사고 후 도주 여부 확인",
    "REAR_END_SAFE_DISTANCE": "앞차와 안전거리를 지켜야 하는 의무",
    "LANE_CHANGE_CAUTION": "차선을 바꿀 때 조심해야 하는 의무",
}

FIELD_LABELS = {
    "accident_type": "사고 유형",
    "signal_state": "신호 상태",
    "injury": "다친 사람이 있는지",
    "opponent_behavior": "상대 차량의 행동",
    "damage_level": "차량 파손 정도",
    "school_zone": "어린이보호구역 여부",
    "victim_is_child": "피해자가 어린이인지",
    "stopped": "정차 중이었는지",
    "sudden_brake": "급정거가 있었는지",
    "police_reported": "경찰 신고를 했는지",
}

_INTERNAL_PATTERNS = [
    re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b"),
    re.compile(r"\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b"),
    re.compile(r"score\s*[:=]?\s*\d+(?:\.\d+)?", re.I),
    re.compile(r"chunk[_ ]?id\s*[:=]?\s*[\w-]+", re.I),
    re.compile(r"model[_ ]?info", re.I),
]

def scenario_label(value: str | None) -> str:
    return SCENARIO_LABELS.get(value or "", "교통사고")

def risk_label(value: str | None) -> str:
    return RISK_LABELS.get(str(value or "unknown"), "확인 필요")

def confidence_label(score: float | int | None) -> str:
    try: value = float(score or 0)
    except (TypeError, ValueError): value = 0
    if value >= 0.68: return "비교적 신뢰할 수 있음"
    if value >= 0.45: return "보통"
    return "추가 확인 필요"

def evidence_confidence_label(score: float | int | None) -> str:
    try: value = float(score or 0)
    except (TypeError, ValueError): value = 0
    if value >= 0.55: return "높음"
    if value >= 0.25: return "보통"
    return "낮음"

def rule_label(value: str | None) -> str:
    return RULE_LABELS.get(value or "", "교통사고 관련 확인 사항")

def field_label(value: str | None) -> str:
    return FIELD_LABELS.get(value or "", "추가 정보")

def scrub_user_text(text: Any, fallback: str = "확인이 필요합니다.") -> str:
    value = str(text or "").strip()
    if not value: return fallback
    for pattern in _INTERNAL_PATTERNS:
        value = pattern.sub("", value)
    value = re.sub(r"\?{2,}", "", value)
    value = value.replace("medium", "보통").replace("high", "높음").replace("low", "낮음")
    value = re.sub(r"\s+", " ", value).strip(" -:/,.")
    return value or fallback

def as_percent(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None: return default
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return default
