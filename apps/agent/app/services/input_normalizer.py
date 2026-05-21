from __future__ import annotations

import json
from typing import Any
from app.services.fact_arbitration import arbitrate_facts
from app.services.security_filter import sanitize_input
from app.services.video_input_contract import normalize_video_input_contract

REQUIRED_FACTS = ["accident_type", "signal_state", "injury", "opponent_behavior", "damage_level"]
EMPTY_VALUES = {None, "", "unknown", "모름", "None", "null"}
FIELD_LABELS = {
    "accident_type": "사고 유형",
    "signal_state": "신호 상태",
    "injury": "다친 사람 여부",
    "opponent_behavior": "상대 차량 행동",
    "damage_level": "차량 손상 정도",
    "stopped": "정차 중",
    "sudden_brake": "급정거",
    "school_zone": "어린이보호구역",
    "victim_is_child": "피해자가 어린이",
    "crosswalk_nearby": "횡단보도 근처",
    "lane_change": "차선 변경",
    "intersection": "교차로",
    "pedestrian": "보행자 관련",
    "opponent_signal_violation": "상대 신호위반",
    "weather": "날씨",
    "light_condition": "주야 상태",
}
VALUE_LABELS = {
    "rear_end_collision": "후미추돌 사고",
    "intersection_collision": "교차로 충돌",
    "lane_change_collision": "차선변경 충돌",
    "pedestrian": "보행자 사고",
    "red": "적색 신호",
    "green": "녹색 신호",
    "yellow": "황색 신호",
    True: "예",
    False: "아니오",
}

def _is_empty(value: Any) -> bool:
    if isinstance(value, (dict, list, set, tuple)):
        return len(value) == 0
    if value in EMPTY_VALUES:
        return True
    if isinstance(value, str) and value.strip() in EMPTY_VALUES:
        return True
    return False

def clean_structured_facts_for_display(facts: dict[str, Any] | None) -> dict[str, str]:
    display: dict[str, str] = {}
    for key, value in (facts or {}).items():
        if not key or key.startswith("_") or _is_empty(value):
            continue
        label = FIELD_LABELS.get(key, key.replace("_", " "))
        if isinstance(value, bool):
            if value:
                display[label] = "예"
            continue
        if isinstance(value, (dict, list)):
            continue
        display[label] = str(VALUE_LABELS.get(value, value))
    return display

def format_facts_as_korean_sentences(facts: dict[str, Any] | None) -> str:
    display = clean_structured_facts_for_display(facts)
    if not display:
        return "추가로 확인할 사고 정보가 있습니다."
    return " ".join(f"{key}은(는) {value}입니다." for key, value in display.items())

def _compact_for_analysis(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _compact_for_analysis(v) for k, v in value.items() if k and not _is_empty(v)}
    if isinstance(value, list):
        return [_compact_for_analysis(v) for v in value if not _is_empty(v)]
    return value

def normalize_analysis_input(description_text: str, structured_facts: dict[str, Any] | None = None, selected_keywords: list[str] | None = None, video_metadata: dict[str, Any] | None = None, analysis_mode: str | None = None) -> dict[str, Any]:
    clean_text, security_flags = sanitize_input(description_text or "")
    video_contract = normalize_video_input_contract(video_metadata, preprocessed_summary=clean_text)
    user_facts = _compact_for_analysis(structured_facts or {})
    arbitration = arbitrate_facts(user_facts=user_facts, video_contract=video_contract)
    fact_arbitration = arbitration["contract"]
    facts = _compact_for_analysis(arbitration["facts"])
    keywords = [str(x).strip() for x in (selected_keywords or []) if str(x).strip()]
    missing_fields = [field for field in REQUIRED_FACTS if _is_empty(facts.get(field))]
    facts_display = clean_structured_facts_for_display(facts)
    user_visible_summary_text = clean_text or format_facts_as_korean_sentences(facts)
    video_contract_for_text = _compact_for_analysis({
        "version": video_contract.get("version"),
        "technical_metadata": video_contract.get("technical_metadata"),
        "accepted_observations": video_contract.get("accepted_observations"),
        "uncertain_observations": video_contract.get("uncertain_observations"),
        "warnings": video_contract.get("warnings"),
    })
    arbitration_for_text = _compact_for_analysis({
        "version": fact_arbitration.get("version"),
        "applied_video_fields": fact_arbitration.get("applied_video_fields"),
        "kept_user_fields": fact_arbitration.get("kept_user_fields"),
        "confirmed_fields": fact_arbitration.get("confirmed_fields"),
        "conflicts": fact_arbitration.get("conflicts"),
    })
    merged_text = "\n".join([
        clean_text,
        "분석용 사고 사실: " + json.dumps(facts, ensure_ascii=False, separators=(",", ":")),
        "분석용 선택 키워드: " + ", ".join(keywords),
        "분석용 영상 입력 계약: " + json.dumps(video_contract_for_text, ensure_ascii=False, separators=(",", ":")),
        "분석용 사실 중재 계약: " + json.dumps(arbitration_for_text, ensure_ascii=False, separators=(",", ":")),
        "분석 모드: " + (analysis_mode or "quick_summary"),
    ])
    return {
        "description_text": clean_text,
        "user_visible_summary_text": user_visible_summary_text,
        "structured_facts": facts,
        "facts_for_display": facts_display,
        "selected_keywords": keywords,
        "video_metadata": video_metadata or {},
        "video_input_contract": video_contract,
        "fact_arbitration": fact_arbitration,
        "analysis_mode": analysis_mode or "quick_summary",
        "security_flags": security_flags,
        "missing_fields": missing_fields,
        "merged_text": merged_text,
    }
