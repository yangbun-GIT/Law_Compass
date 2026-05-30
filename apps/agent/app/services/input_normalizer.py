from __future__ import annotations

import json
from typing import Any
from app.services.analysis_modes import normalize_analysis_mode
from app.services.fact_arbitration import arbitrate_facts
from app.services.llm_client import generate_accident_input_filter
from app.services.party_agents.router import route_party_agent
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
    "collision_target": "충돌 대상",
    "parked_vehicle_position": "상대 차량 위치",
    "parked_vehicle_lighting": "상대 차량 등화",
    "visibility_condition": "시야 조건",
    "opponent_impairment": "상대 운전자 상태",
    "avoidability": "회피 가능성",
    "fault_ratio_claim_target": "과실비율 주장 목표",
}
VALUE_LABELS = {
    "rear_end_collision": "후미추돌 사고",
    "stealth_illegal_parked_vehicle_collision": "야간 스텔스 불법 정차 차량 충돌",
    "intersection_collision": "교차로 충돌",
    "lane_change_collision": "차선변경 충돌",
    "pedestrian": "보행자 사고",
    "red": "적색 신호",
    "green": "녹색 신호",
    "yellow": "황색 신호",
    "truck": "트럭 또는 대형 차량",
    "parked_vehicle": "주차 또는 정차 차량",
    "traffic_space": "통행 공간에 걸침",
    "flowerbed_or_median": "화단 또는 중앙분리대 주변",
    "under_bridge": "교량 아래",
    "unlit_stealth": "스텔스 상태",
    "night_dark": "야간 어두운 환경",
    "under_bridge_dark": "교량 아래 조도 불량",
    "drunk_driving_confirmed": "음주운전 확인",
    "suspected_drunk": "음주운전 의심",
    "limited": "회피 제한",
    "nearly_impossible": "회피 거의 불가능",
    "opponent_100_ego_0_possible": "상대 100 대 내 차량 0 주장 가능",
    "opponent_90_ego_10": "상대 90 대 내 차량 10",
    "opponent_80_ego_20": "상대 80 대 내 차량 20",
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


def _has_road_worker_pedestrian_context(text: str) -> bool:
    tokens = (
        "공사 담당자",
        "공사작업자",
        "공사 작업자",
        "도로 작업자",
        "작업자",
        "인부",
        "도로 폭 측정",
        "도로폭 측정",
        "차도 진입",
        "도로쪽",
        "도로 쪽",
        "갑자기 튀어나",
        "갑자기 뛰어나",
        "차를 보지 않고",
        "차량을 보지 않고",
    )
    return any(token in text for token in tokens)


def _enrich_road_worker_pedestrian_facts(facts: dict[str, Any], text: str) -> dict[str, Any]:
    if not _has_road_worker_pedestrian_context(text):
        return facts
    enriched = dict(facts)
    enriched.update(
        {
            "accident_party_type": "car_vs_person",
            "knia_major_party_type": "car_vs_person",
            "major_party_type": "car_vs_person",
            "collision_partner_type": "person",
            "direct_collision_partner_type": "person",
            "direct_collision_target": "road_work_worker",
            "scenario_type": "pedestrian_accident",
            "accident_type": "pedestrian_roadway_worker_accident",
            "accident_subtype": "pedestrian_roadway_or_work_zone",
            "scenario_subtype": "pedestrian_roadway_or_work_zone",
            "pedestrian_context": "road_worker_or_construction_worker",
            "pedestrian_on_roadway": True,
            "pedestrian_involved": True,
            "pedestrian_worker": True,
            "road_worker": True,
            "road_work_context": True,
            "work_zone_context": True,
            "sudden_entry": True,
            "pedestrian_sudden_entry": True,
            "lookout_failure_by_pedestrian": True,
            "crosswalk_nearby": False,
            "excluded_knia_party_types": ["car_vs_car", "car_vs_bicycle", "car_vs_motorcycle", "car_vs_object", "single_vehicle"],
        }
    )
    return enriched


def _normalize_accident_typos(text: str) -> str:
    return (
        str(text or "")
        .replace("눚은밤", "늦은 밤")
        .replace("늦은밤", "늦은 밤")
        .replace("부딛", "부딪")
        .replace("부딧", "부딪")
        .replace("상태였가", "상태였다")
        .replace("정차중", "정차 중")
        .replace("신호대기중", "신호대기 중")
    )


def _has_stealth_illegal_parked_vehicle_context(text: str) -> bool:
    hay = _normalize_accident_typos(text).lower()
    collision = _contains_any(hay, ("부딪", "충돌", "박", "들이받", "들이박", "파손", "폐차"))
    parked_vehicle = _contains_any(
        hay,
        (
            "주차",
            "정차",
            "방치",
            "세워",
            "세워진",
            "서있",
            "서 있",
            "트럭",
            "화물차",
            "주차해둔",
            "주차된",
            "정차된",
        ),
    )
    visibility_or_place = _contains_any(
        hay,
        (
            "스텔스",
            "무등화",
            "미등",
            "비상등",
            "차폭등",
            "불빛",
            "등화",
            "야간",
            "밤",
            "늦은 밤",
            "새벽",
            "어두",
            "교량 밑",
            "교량밑",
            "교량 아래",
            "화단",
            "중앙분리대",
            "갓길",
        ),
    )
    impairment = _contains_any(hay, ("음주", "술", "만취", "음주운전"))
    return collision and parked_vehicle and (visibility_or_place or impairment)


def _enrich_stealth_illegal_parked_vehicle_facts(facts: dict[str, Any], text: str) -> dict[str, Any]:
    enriched = dict(facts)
    hay = _normalize_accident_typos(text).lower()
    if not _has_stealth_illegal_parked_vehicle_context(hay):
        return enriched

    enriched["accident_type"] = "stealth_illegal_parked_vehicle_collision"
    enriched["knia_major_party_type"] = "car_vs_car"
    enriched["accident_party_type"] = "car_vs_car"
    enriched["accident_subtype"] = "night_unlit_illegal_parked_vehicle_collision"
    enriched["collision_partner_type"] = "vehicle"
    enriched["direct_collision_partner_type"] = "vehicle"
    enriched["target_vehicle_status"] = "abnormal_parked"
    enriched["is_parked_vehicle_collision"] = True
    enriched["is_stealth_parked_vehicle_collision"] = True
    enriched["requires_high_opponent_fault_review"] = True

    _set_if_empty(enriched, "collision_target", "truck" if _contains_any(hay, ("트럭", "화물차")) else "parked_vehicle")

    if _contains_any(hay, ("화단", "중앙분리대")):
        _set_if_empty(enriched, "parked_vehicle_position", "flowerbed_or_median")
        enriched["abnormal_parking"] = True
    elif _contains_any(hay, ("교량 밑", "교량밑", "교량 아래")):
        _set_if_empty(enriched, "parked_vehicle_position", "under_bridge")
        enriched["abnormal_parking"] = True
    elif _contains_any(hay, ("갓길", "도로 가장자리", "통행 공간")):
        _set_if_empty(enriched, "parked_vehicle_position", "traffic_space")
        enriched["abnormal_parking"] = True

    if _contains_any(hay, ("스텔스", "무등화", "미등", "비상등", "차폭등", "등화 없이", "불빛 없이")):
        _set_if_empty(enriched, "parked_vehicle_lighting", "unlit_stealth")
        enriched["stopped_vehicle_without_lights"] = True
        enriched["night_no_lights_or_low_visibility"] = True

    if _contains_any(hay, ("교량 밑", "교량밑", "교량 아래")):
        _set_if_empty(enriched, "visibility_condition", "under_bridge_dark")
        enriched["night_no_lights_or_low_visibility"] = True
    elif _contains_any(hay, ("밤", "야간", "늦은 밤", "새벽", "어두")):
        _set_if_empty(enriched, "visibility_condition", "night_dark")
        enriched["night_no_lights_or_low_visibility"] = True

    if _contains_any(hay, ("음주운전", "음주", "만취", "술")):
        _set_if_empty(enriched, "opponent_impairment", "drunk_driving_confirmed")
        enriched["opponent_drunk_or_abnormal_operation"] = True
        enriched["twelve_gross_negligence_context"] = True

    if _contains_any(hay, ("피하지 못", "발견 즉시", "못 피", "회피 불가", "시야", "어두")):
        _set_if_empty(enriched, "avoidability", "nearly_impossible")
        enriched["low_avoidability"] = True

    lighting = str(enriched.get("parked_vehicle_lighting") or "")
    visibility = str(enriched.get("visibility_condition") or "")
    position = str(enriched.get("parked_vehicle_position") or "")
    impairment = str(enriched.get("opponent_impairment") or "")
    avoidability = str(enriched.get("avoidability") or "")

    strong_visibility = lighting == "unlit_stealth" and visibility in {"night_dark", "under_bridge_dark"}
    abnormal_position = position in {"traffic_space", "flowerbed_or_median", "under_bridge", "roadside"}
    drunk = impairment in {"drunk_driving_confirmed", "suspected_drunk"}
    hard_to_avoid = avoidability in {"limited", "nearly_impossible"}

    if strong_visibility and abnormal_position and drunk and hard_to_avoid:
        enriched["fault_ratio_claim_target"] = "opponent_100_ego_0_possible"
        enriched["fault_ratio_realistic_target"] = "opponent_90_ego_10"
        enriched["fault_ratio_minimum_target"] = "opponent_80_ego_20"
    elif strong_visibility and (abnormal_position or drunk):
        enriched["fault_ratio_claim_target"] = "opponent_90_ego_10"
        enriched["fault_ratio_realistic_target"] = "opponent_80_ego_20"
        enriched["fault_ratio_minimum_target"] = "opponent_70_ego_30"
    else:
        enriched["fault_ratio_realistic_target"] = "opponent_80_ego_20"

    return enriched


def _deterministic_accident_input_filter(text: str, facts: dict[str, Any] | None = None) -> dict[str, Any]:
    base_facts = dict(facts or {})
    hay = _normalize_accident_typos(text).lower()

    collision = _contains_any(hay, ("부딪", "충돌", "박", "들이받", "들이박", "파손", "폐차"))
    vehicle = _contains_any(hay, ("트럭", "화물차", "차량", "상대차", "앞차", "승용차"))
    parked = _contains_any(hay, ("주차", "정차", "방치", "세워", "서 있", "서있", "화단", "갓길"))
    risk = _contains_any(
        hay,
        (
            "스텔스",
            "무등화",
            "등화 없이",
            "미등",
            "비상등",
            "차폭등",
            "야간",
            "밤",
            "새벽",
            "교량 밑",
            "교량 아래",
            "어두",
            "음주",
            "음주운전",
        ),
    )

    if not (collision and vehicle and parked and risk):
        return {
            "matched": False,
            "confidence": 0.0,
            "facts_patch": {},
            "exclude_party_types": [],
            "scenario_tags": [],
            "reason": "deterministic_criteria_not_matched",
        }

    patch: dict[str, Any] = {
        "knia_major_party_type": "car_vs_car",
        "accident_party_type": "car_vs_car",
        "accident_type": "stealth_illegal_parked_vehicle_collision",
        "accident_subtype": "night_unlit_illegal_parked_vehicle_collision",
        "collision_partner_type": "vehicle",
        "direct_collision_partner_type": "vehicle",
        "target_vehicle_status": "abnormal_parked",
        "is_parked_vehicle_collision": True,
        "is_stealth_parked_vehicle_collision": True,
        "night_no_lights_or_low_visibility": True,
        "abnormal_parking": True,
        "parked_vehicle_lighting": "unlit_stealth",
        "fault_ratio_claim_target": "opponent_100_ego_0_possible",
        "fault_ratio_realistic_target": "opponent_90_ego_10",
        "fault_ratio_minimum_target": "opponent_80_ego_20",
    }
    patch["collision_target"] = "truck" if _contains_any(hay, ("트럭", "화물차")) else "parked_vehicle"
    if _contains_any(hay, ("교량 밑", "교량 아래", "교량밑")):
        patch["parked_vehicle_position"] = "under_bridge"
        patch["visibility_condition"] = "under_bridge_dark"
    else:
        patch["parked_vehicle_position"] = "flowerbed_or_median" if _contains_any(hay, ("화단", "중앙분리대")) else "under_bridge"
        patch["visibility_condition"] = "night_dark"

    if _contains_any(hay, ("음주", "음주운전", "만취", "술")):
        patch["opponent_impairment"] = "drunk_driving_confirmed"
        patch["opponent_drunk_or_abnormal_operation"] = True
        patch["twelve_gross_negligence_context"] = True

    return {
        "matched": True,
        "confidence": 0.92,
        "knia_major_party_type": "car_vs_car",
        "accident_type": "stealth_illegal_parked_vehicle_collision",
        "accident_subtype": "night_unlit_illegal_parked_vehicle_collision",
        "collision_partner_type": "vehicle",
        "direct_collision_target": patch.get("collision_target"),
        "target_vehicle_status": "abnormal_parked",
        "scenario_tags": [
            "parking",
            "stopped_vehicle",
            "unlit_stopped_vehicle",
            "visibility",
            "night",
            "road_obstruction",
            "avoidability",
        ],
        "facts_patch": patch,
        "exclude_party_types": ["car_vs_bicycle", "car_vs_person"],
        "reason": "deterministic_stealth_parked_vehicle_collision",
    }


def _apply_accident_input_filter_result(
    facts: dict[str, Any],
    filter_result: dict[str, Any] | None,
) -> dict[str, Any]:
    if not filter_result:
        return facts
    patched = dict(facts)
    patch = filter_result.get("facts_patch")
    if isinstance(patch, dict):
        patched.update(patch)
    for key in ("knia_major_party_type", "accident_type", "accident_subtype", "collision_partner_type", "target_vehicle_status"):
        value = filter_result.get(key)
        if value not in (None, "", "unknown"):
            patched[key] = value
    if patched.get("accident_type") == "stealth_illegal_parked_vehicle_collision":
        patched["accident_party_type"] = "car_vs_car"
        patched["knia_major_party_type"] = "car_vs_car"
        patched["collision_partner_type"] = "vehicle"
        patched["direct_collision_partner_type"] = "vehicle"
        patched.pop("bicycle_involved", None)
        patched.pop("possible_trigger_vehicle", None)
        patched.pop("trigger_actor_type", None)
        patched.pop("bicycle_location", None)
        patched.pop("bicycle_movement", None)
    return patched


def _apply_party_agent_result(
    facts: dict[str, Any],
    party_agent_result: dict[str, Any] | None,
) -> dict[str, Any]:
    if not party_agent_result:
        return facts
    patched = dict(facts)
    patch = party_agent_result.get("facts_patch")
    if isinstance(patch, dict):
        patched.update({key: value for key, value in patch.items() if value is not None})
    party = party_agent_result.get("major_party_type")
    if party and party != "unknown":
        patched["knia_major_party_type"] = party
        patched["accident_party_type"] = party
    if party_agent_result.get("scenario_type") and party_agent_result.get("scenario_type") != "general_vehicle_collision":
        _set_if_empty(patched, "accident_type", party_agent_result.get("scenario_type"))
    if party_agent_result.get("scenario_subtype"):
        _set_if_empty(patched, "accident_subtype", party_agent_result.get("scenario_subtype"))
    excluded = party_agent_result.get("excluded_party_types")
    if isinstance(excluded, list):
        patched["excluded_knia_party_types"] = excluded
    if party_agent_result.get("conflict"):
        patched["party_conflict"] = party_agent_result.get("conflict")
    return _apply_party_guard_facts(patched, party_agent_result)


def _apply_party_guard_facts(
    facts: dict[str, Any],
    party_agent_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    guarded = dict(facts)
    party = str(
        guarded.get("knia_major_party_type")
        or guarded.get("accident_party_type")
        or (party_agent_result or {}).get("major_party_type")
        or ""
    )
    if party and party != "unknown":
        guarded["knia_major_party_type"] = party
        guarded["accident_party_type"] = party
    if party == "car_vs_car":
        guarded["collision_partner_type"] = "vehicle"
        guarded["direct_collision_partner_type"] = "vehicle"
        guarded.setdefault("excluded_knia_party_types", ["car_vs_person", "car_vs_bicycle", "car_vs_motorcycle", "car_vs_object", "single_vehicle"])
        if guarded.get("accident_type") == "stealth_illegal_parked_vehicle_collision":
            for key in ("bicycle_involved", "possible_trigger_vehicle", "trigger_actor_type", "bicycle_location", "bicycle_movement"):
                guarded.pop(key, None)
    elif party == "car_vs_person":
        if guarded.get("road_worker") or guarded.get("accident_type") == "pedestrian_roadway_worker_accident":
            guarded["collision_partner_type"] = "person"
            guarded["direct_collision_partner_type"] = "person"
            guarded.setdefault("direct_collision_target", "road_work_worker")
        else:
            guarded["collision_partner_type"] = "pedestrian"
            guarded["direct_collision_partner_type"] = "pedestrian"
        guarded.setdefault("excluded_knia_party_types", ["car_vs_car", "car_vs_bicycle", "car_vs_motorcycle", "car_vs_object", "single_vehicle"])
    elif party == "car_vs_bicycle":
        guarded["collision_partner_type"] = "bicycle"
        guarded["direct_collision_partner_type"] = "bicycle"
        guarded.setdefault("excluded_knia_party_types", ["car_vs_car", "car_vs_person", "car_vs_motorcycle", "car_vs_object", "single_vehicle"])
    elif party == "car_vs_motorcycle":
        guarded["collision_partner_type"] = "motorcycle"
        guarded["direct_collision_partner_type"] = "motorcycle"
        guarded.setdefault("excluded_knia_party_types", ["car_vs_car", "car_vs_person", "car_vs_bicycle", "car_vs_object", "single_vehicle"])
    elif party == "car_vs_object":
        guarded["collision_partner_type"] = "object"
        guarded["direct_collision_partner_type"] = "object"
        guarded.setdefault("excluded_knia_party_types", ["car_vs_car", "car_vs_person", "car_vs_bicycle", "car_vs_motorcycle", "single_vehicle"])
    elif party == "single_vehicle":
        guarded["collision_partner_type"] = "none"
        guarded.pop("direct_collision_partner_type", None)
        guarded.setdefault("excluded_knia_party_types", ["car_vs_car", "car_vs_person", "car_vs_bicycle", "car_vs_motorcycle", "car_vs_object"])
    return guarded


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
    hay = _normalize_accident_typos(text).lower()
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

    centerline_text = _contains_any(
        hay,
        ("중앙선", "황색 실선", "황색실선", "센터라인", "centerline", "yellow line"),
    )
    centerline_obstruction_text = _contains_any(
        hay,
        (
            "불법주정차",
            "불법 주정차",
            "주정차량",
            "주차 차량",
            "주차된",
            "정차 차량",
            "도로를 점유",
            "도로 점유",
            "막고 있어",
            "막혀",
            "장애물",
            "가구",
            "사물",
            "적재물",
            "obstacle",
            "parked vehicle",
        ),
    )
    oncoming_text = _contains_any(
        hay,
        (
            "마주오",
            "마주 오",
            "대향",
            "반대편",
            "상대차",
            "상대 차량",
            "오던 차",
            "오는 차",
            "역방향",
            "oncoming",
            "opposite direction",
        ),
    )
    if centerline_text and (centerline_obstruction_text or oncoming_text or enriched.get("centerline_crossed") is True):
        _set_if_empty(enriched, "accident_party_type", "car_vs_car")
        _set_if_empty(enriched, "knia_major_party_type", "car_vs_car")
        _set_if_empty(enriched, "collision_partner_type", "vehicle")
        _set_if_empty(enriched, "direct_collision_partner_type", "vehicle")
        if _is_empty(enriched.get("accident_type")) or str(enriched.get("accident_type")) in {
            "general_collision",
            "general_vehicle_collision",
            "parking_or_stopped_vehicle_accident",
        }:
            enriched["accident_type"] = "centerline_obstacle_collision"
        enriched["centerline_crossed"] = True
        if centerline_obstruction_text:
            enriched["road_obstruction"] = True
            if _contains_any(hay, ("불법주정차", "불법 주정차", "주정차량", "주차 차량", "주차된", "정차 차량", "parked vehicle")):
                enriched["illegal_parking_obstruction"] = True
                _set_if_empty(enriched, "centerline_cross_reason", "parked_vehicle_obstruction")
            else:
                _set_if_empty(enriched, "centerline_cross_reason", "road_obstruction")
        if oncoming_text:
            enriched["opposing_vehicle_present"] = True
        if _contains_any(hay, ("멈췄", "멈췄는데", "멈춰", "멈춘", "거의 멈", "정차", "정지", "감속")):
            enriched["stopped"] = True
        if _contains_any(hay, ("못봤", "못 봤", "보지 못", "못보", "그대로", "달려", "멈추지", "감속하지")):
            enriched["opposing_vehicle_did_not_stop"] = True
            _set_if_empty(enriched, "opponent_behavior", "oncoming_vehicle_did_not_stop")

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
        enriched["non_contact_trigger"] = True
        enriched["trigger_actor_type"] = "bicycle"
        enriched["possible_trigger_vehicle"] = "bicycle"
        enriched["rear_vehicle_collision"] = True
        enriched["collision_partner_type"] = "vehicle"
        enriched["direct_collision_partner_type"] = "vehicle"
        enriched["accident_party_type"] = "car_vs_car"
        enriched["knia_major_party_type"] = "car_vs_car"
        enriched["accident_type"] = "non_contact_trigger"
    enriched = _enrich_stealth_illegal_parked_vehicle_facts(enriched, hay)

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
    clean_text = _normalize_accident_typos(clean_text)
    keywords = [str(x).strip() for x in (selected_keywords or []) if str(x).strip()]
    video_contract = normalize_video_input_contract(video_metadata, preprocessed_summary=clean_text)
    user_facts = _normalize_fact_aliases(_compact_for_analysis(structured_facts or {}))
    party_agent_result = route_party_agent(
        description_text=clean_text,
        structured_facts=user_facts,
        selected_keywords=keywords,
        video_metadata=video_contract,
    )
    user_facts = _apply_party_agent_result(user_facts, party_agent_result)
    user_facts = _enrich_road_worker_pedestrian_facts(user_facts, clean_text)
    user_facts = _enrich_textual_traffic_facts(user_facts, clean_text)
    party_agent_result = route_party_agent(
        description_text=clean_text,
        structured_facts=user_facts,
        selected_keywords=keywords,
        video_metadata=video_contract,
    )
    user_facts = _apply_party_agent_result(user_facts, party_agent_result)
    user_facts = _enrich_road_worker_pedestrian_facts(user_facts, clean_text)
    deterministic_filter = _deterministic_accident_input_filter(clean_text, user_facts)
    llm_filter = generate_accident_input_filter(
        description_text=clean_text,
        structured_facts=user_facts,
        selected_keywords=selected_keywords or [],
    )
    selected_filter = deterministic_filter if float(deterministic_filter.get("confidence") or 0.0) >= 0.85 else llm_filter
    user_facts = _apply_accident_input_filter_result(user_facts, selected_filter)
    user_facts = _apply_party_agent_result(user_facts, party_agent_result)
    arbitration = arbitrate_facts(user_facts=user_facts, video_contract=video_contract)
    fact_arbitration = arbitration["contract"]
    facts = _enrich_textual_traffic_facts(_compact_for_analysis(arbitration["facts"]), clean_text)
    facts = _enrich_road_worker_pedestrian_facts(facts, clean_text)
    facts = _apply_accident_input_filter_result(facts, selected_filter)
    facts = _apply_party_agent_result(facts, party_agent_result)
    facts = _apply_party_guard_facts(facts, party_agent_result)
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
        "held_video_fields": fact_arbitration.get("held_video_fields"),
        "tentatively_supported_fields": fact_arbitration.get("tentatively_supported_fields"),
        "confirmation_fields": fact_arbitration.get("confirmation_fields"),
        "conflicts": fact_arbitration.get("conflicts"),
        "pending_video_confirmations": fact_arbitration.get("pending_video_confirmations"),
    })
    party_agent_for_text = _compact_for_analysis(party_agent_result)
    merged_text = "\n".join([
        clean_text,
        "분석용 KNIA 대분류 라우터: " + json.dumps(party_agent_for_text, ensure_ascii=False, separators=(",", ":")),
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
        "party_agent_result": party_agent_result,
        "knia_major_party_type": facts.get("knia_major_party_type") or (party_agent_result or {}).get("major_party_type") or "unknown",
        "excluded_knia_party_types": facts.get("excluded_knia_party_types") or (party_agent_result or {}).get("excluded_party_types") or [],
        "direct_collision_partner_type": facts.get("direct_collision_partner_type"),
        "direct_collision_target": facts.get("direct_collision_target"),
        "environment_context": facts.get("environment_context") or {},
        "analysis_mode": canonical_analysis_mode,
        "security_flags": security_flags,
        "missing_fields": missing_fields,
        "merged_text": merged_text,
    }
