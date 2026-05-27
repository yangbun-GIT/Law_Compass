from __future__ import annotations

import json
from typing import Any
from app.services.analysis_modes import normalize_analysis_mode
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

def _normalize_fact_aliases(facts: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(facts)
    if "crosswalk_nearby" not in normalized and normalized.get("crosswalk") is True:
        normalized["crosswalk_nearby"] = True
    if "opponent_signal_violation" not in normalized and normalized.get("other_signal_violation") is not None:
        normalized["opponent_signal_violation"] = normalized.get("other_signal_violation")
    return normalized

def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)

def _set_if_empty(facts: dict[str, Any], key: str, value: Any) -> None:
    if _is_empty(facts.get(key)):
        facts[key] = value

def _has_lawful_red_light_stop_context(text: str) -> bool:
    stop_tokens = (
        "신호대기",
        "신호 대기",
        "빨간불에 정차",
        "빨간불 정차",
        "적색신호 대기",
        "적색 신호 대기",
        "신호대기 중 정차",
        "신호 대기 중 정차",
        "정지선에서 대기",
        "정지선 대기",
        "red light stop",
        "stopped at red",
    )
    return _contains_any(text, stop_tokens)

def _has_actor_signal_violation_context(text: str, actor_tokens: tuple[str, ...]) -> bool:
    for actor in actor_tokens:
        start = 0
        while True:
            index = text.find(actor, start)
            if index == -1:
                break
            local = text[index : index + len(actor) + 64]
            if _contains_any(local, ("신호위반", "신호 위반", "signal violation")):
                return True
            if _has_red_light_violation_context(local):
                return True
            start = index + len(actor)
    return False

def _has_opponent_signal_violation_context(text: str) -> bool:
    return _has_actor_signal_violation_context(
        text,
        ("상대", "상대방", "상대 차량", "상대차", "상대 차", "다른 차", "opponent", "other vehicle"),
    )

def _has_user_signal_violation_context(text: str) -> bool:
    return _has_actor_signal_violation_context(
        text,
        ("내가", "제가", "내 차가", "제 차가", "내 차량이", "제 차량이", "우리 차가", "본인이", "my car", "my vehicle"),
    )

def _has_red_light_violation_context(text: str) -> bool:
    red_context = _contains_any(text, ("빨간불", "적색신호", "적색 신호", "정지신호", "red light", "red signal"))
    violation_context = _contains_any(
        text,
        (
            "진입",
            "들어갔",
            "통과",
            "무시",
            "위반",
            "진행",
            "교차로로",
            "entered",
            "ran",
            "ignored",
            "violation",
        ),
    )
    lawful_stop = _has_lawful_red_light_stop_context(text)
    return red_context and violation_context and not lawful_stop

def _has_rear_end_victim_context(text: str) -> bool:
    rear_actor = _contains_any(text, ("뒷차", "뒷 차", "뒤차", "뒤 차", "후방 차량", "후속 차량", "뒤 차량", "rear vehicle", "vehicle behind"))
    impact = _contains_any(text, ("추돌", "들이받", "박았", "받았", "받힘", "hit from behind", "rear-ended"))
    stopped = _contains_any(text, ("정차", "정지", "멈춰", "멈춘", "대기", "stopped"))
    my_vehicle = _contains_any(text, ("내 차", "제 차", "내 차량", "제 차량", "my car", "my vehicle"))
    return rear_actor and impact and (stopped or my_vehicle)

def _enrich_textual_traffic_facts(facts: dict[str, Any], text: str) -> dict[str, Any]:
    """Fill broadly applicable traffic facts that the UI can express but users often write in free text."""
    enriched = dict(facts)
    hay = text.lower()
    party = str(enriched.get("accident_party_type") or "").strip().lower()
    partner = str(enriched.get("collision_partner_type") or "").strip().lower()
    vehicle_declared = party == "car_vs_car" or partner in {"vehicle", "car", "truck", "bus", "van"}

    if vehicle_declared:
        _set_if_empty(enriched, "collision_partner_type", "vehicle")
        # People or a crosswalk can be visible road context without being the accident target.
        if enriched.get("pedestrian_visible") is True and not _contains_any(hay, ("보행자를", "사람을", "보행자와", "사람과", "pedestrian collision")):
            enriched["pedestrian_context_only"] = True

    if _contains_any(hay, ("교차로", "intersection")):
        _set_if_empty(enriched, "intersection", True)
    if _contains_any(hay, ("좌회전", "left turn", "left-turn")):
        _set_if_empty(enriched, "ego_turn_direction", "left")
    elif _contains_any(hay, ("우회전", "right turn", "right-turn")):
        _set_if_empty(enriched, "ego_turn_direction", "right")

    left_turn = enriched.get("ego_turn_direction") == "left"
    straight_opponent = _contains_any(hay, ("직진", "straight"))
    signal_text = _contains_any(hay, ("신호", "황색", "노란불", "적색", "빨간불", "yellow", "red", "signal"))
    if left_turn and straight_opponent:
        _set_if_empty(enriched, "opponent_behavior", "straight_from_left")
        _set_if_empty(enriched, "collision_partner_type", "vehicle")
        _set_if_empty(enriched, "accident_party_type", "car_vs_car")
        if signal_text or enriched.get("intersection") is True:
            _set_if_empty(enriched, "intersection", True)
            _set_if_empty(enriched, "accident_type", "intersection_signal_violation")

    if _contains_any(hay, ("황색", "노란불", "yellow")):
        _set_if_empty(enriched, "user_signal", "yellow")
    if _has_lawful_red_light_stop_context(hay):
        _set_if_empty(enriched, "lawful_stop_reason", "traffic_signal")
        _set_if_empty(enriched, "stopped_at_red_light", True)
        _set_if_empty(enriched, "stopped_due_to_signal", True)
        _set_if_empty(enriched, "rear_end_context", True)
        _set_if_empty(enriched, "stopped", True)
    opponent_signal_violation_text = _has_opponent_signal_violation_context(hay)
    user_signal_violation_text = _has_user_signal_violation_context(hay)
    if opponent_signal_violation_text:
        _set_if_empty(enriched, "opponent_signal_violation", True)
        _set_if_empty(enriched, "intersection", True)
        _set_if_empty(enriched, "accident_type", "intersection_signal_violation")
        if enriched.get("user_signal_violation") is True and not user_signal_violation_text:
            enriched.pop("user_signal_violation", None)
    elif user_signal_violation_text or _has_red_light_violation_context(hay):
        _set_if_empty(enriched, "user_signal_violation", True)
        _set_if_empty(enriched, "intersection", True)
        _set_if_empty(enriched, "accident_type", "intersection_signal_violation")
    if _contains_any(hay, ("적색", "빨간불", "red")) and _contains_any(hay, ("변경", "바뀌", "전환", "changed", "turn")):
        _set_if_empty(enriched, "signal_transition", "yellow_to_red")
    if _contains_any(hay, ("황색", "노란불", "yellow")) and _contains_any(hay, ("적색", "빨간불", "red")):
        _set_if_empty(enriched, "signal_transition", "yellow_to_red")
        _set_if_empty(enriched, "signal_timing_uncertain", True)
        _set_if_empty(enriched, "cctv_needed", True)

    opponent_signal_unknown_text = _contains_any(
        hay,
        ("상대 신호 정보 없음", "상대 신호 모름", "상대 신호 확인 불가", "상대 신호가 안 보", "opponent signal unknown", "opponent signal not visible"),
    )
    if opponent_signal_unknown_text or (enriched.get("intersection") is True and enriched.get("signal_transition") and _is_empty(enriched.get("opponent_signal"))):
        _set_if_empty(enriched, "opponent_signal_visible", False)
        _set_if_empty(enriched, "signal_timing_uncertain", True)
        _set_if_empty(enriched, "cctv_needed", True)
    bicycle_trigger_text = _contains_any(hay, ("자전거", "bicycle", "cyclist"))
    rear_vehicle_text = _contains_any(hay, ("뒤에서", "후방", "뒤차", "후미", "후속", "버스가", "bus", "rear"))
    stop_or_avoid_text = _contains_any(hay, ("멈췄", "정지", "급정거", "피하", "avoid", "stopped"))
    direct_bicycle_collision_text = _contains_any(hay, ("자전거를 쳤", "자전거와 충돌", "자전거 추돌", "hit bicycle", "collided with bicycle"))
    if bicycle_trigger_text and rear_vehicle_text and stop_or_avoid_text and not direct_bicycle_collision_text:
        _set_if_empty(enriched, "non_contact_trigger", True)
        _set_if_empty(enriched, "trigger_actor_type", "bicycle")
        _set_if_empty(enriched, "possible_trigger_vehicle", "bicycle")
        _set_if_empty(enriched, "rear_vehicle_collision", True)
        _set_if_empty(enriched, "collision_partner_type", "vehicle")
        _set_if_empty(enriched, "direct_collision_partner_type", "vehicle")
        _set_if_empty(enriched, "accident_party_type", "car_vs_car")
        _set_if_empty(enriched, "accident_type", "non_contact_trigger")
    if _has_rear_end_victim_context(hay):
        _set_if_empty(enriched, "collision_partner_type", "vehicle")
        _set_if_empty(enriched, "direct_collision_partner_type", "vehicle")
        _set_if_empty(enriched, "accident_party_type", "car_vs_car")
        _set_if_empty(enriched, "opponent_behavior", "rear_collision")
        _set_if_empty(enriched, "accident_type", "rear_end_collision")
        _set_if_empty(enriched, "rear_end_context", True)
    return enriched

def normalize_analysis_input(description_text: str, structured_facts: dict[str, Any] | None = None, selected_keywords: list[str] | None = None, video_metadata: dict[str, Any] | None = None, analysis_mode: str | None = None) -> dict[str, Any]:
    clean_text, security_flags = sanitize_input(description_text or "")
    video_contract = normalize_video_input_contract(video_metadata, preprocessed_summary=clean_text)
    user_facts = _normalize_fact_aliases(_compact_for_analysis(structured_facts or {}))
    user_facts = _enrich_textual_traffic_facts(user_facts, clean_text)
    arbitration = arbitrate_facts(user_facts=user_facts, video_contract=video_contract)
    fact_arbitration = arbitration["contract"]
    facts = _enrich_textual_traffic_facts(_compact_for_analysis(arbitration["facts"]), clean_text)
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
    ])
    canonical_analysis_mode = normalize_analysis_mode(analysis_mode)
    return {
        "description_text": clean_text,
        "user_visible_summary_text": user_visible_summary_text,
        "structured_facts": facts,
        "facts_for_display": facts_display,
        "selected_keywords": keywords,
        "video_metadata": video_metadata or {},
        "video_input_contract": video_contract,
        "fact_arbitration": fact_arbitration,
        "analysis_mode": canonical_analysis_mode,
        "security_flags": security_flags,
        "missing_fields": missing_fields,
        "merged_text": merged_text,
    }
