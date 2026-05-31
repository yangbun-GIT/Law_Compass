from __future__ import annotations

from typing import Any


VERSION = "conditional_judgment.v1"


def build_conditional_judgment(
    *,
    scenario_type: str,
    facts: dict[str, Any],
    text: str = "",
) -> dict[str, Any]:
    """Build scenario-wide conditional outcomes without changing confirmed facts.

    The goal is not to decide a hidden fact.  It exposes branches where a missing
    fact would materially change fault ratio or legal/insurance guidance.
    """

    outcomes: list[dict[str, Any]] = []
    triggers: list[dict[str, Any]] = []

    _extend(outcomes, triggers, _signal_branches(scenario_type, facts, text))
    _extend(outcomes, triggers, _centerline_branches(scenario_type, facts, text))
    _extend(outcomes, triggers, _rear_stop_branches(scenario_type, facts, text))
    _extend(outcomes, triggers, _visibility_speed_branches(scenario_type, facts, text))
    _extend(outcomes, triggers, _non_contact_branches(scenario_type, facts, text))
    _extend(outcomes, triggers, _secondary_collision_branches(facts, text))

    outcomes = merge_conditional_outcomes(outcomes)
    return {
        "version": VERSION,
        "status": "conditional" if outcomes else "not_needed",
        "trigger_count": len(triggers),
        "outcome_count": len(outcomes),
        "triggers": triggers,
        "outcomes": outcomes,
    }


def merge_conditional_outcomes(*groups: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in groups:
        for item in group or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("condition_key") or item.get("label") or "").strip().lower()
            if not key:
                key = "|".join(str(item.get(field) or "").strip().lower() for field in ("my_range", "other_range", "explanation"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _extend(
    outcomes: list[dict[str, Any]],
    triggers: list[dict[str, Any]],
    packet: dict[str, Any],
) -> None:
    if packet.get("outcomes"):
        outcomes.extend(packet["outcomes"])
        triggers.append(
            {
                "type": packet.get("type"),
                "reason": packet.get("reason"),
                "required_facts": packet.get("required_facts") or [],
            }
        )


def _signal_branches(scenario_type: str, facts: dict[str, Any], text: str) -> dict[str, Any]:
    haystack = _haystack(facts, text)
    is_intersection = (
        scenario_type in {"intersection_signal_violation", "intersection_collision"}
        or facts.get("intersection") is True
        or "교차로" in haystack
    )
    signal_issue = any(token in haystack for token in ("신호", "황색", "적색", "yellow", "red", "signal"))
    opponent_unknown = (
        facts.get("opponent_signal_visible") is False
        or _unknown(facts.get("opponent_signal"))
        or facts.get("signal_timing_uncertain") is True
        or facts.get("cctv_needed") is True
    )
    ego_signal_known = bool(facts.get("user_signal") or facts.get("signal_transition") or "황색" in haystack or "적색" in haystack)
    if not (is_intersection and signal_issue and opponent_unknown and ego_signal_known):
        return {}
    return {
        "type": "opponent_signal_uncertainty",
        "reason": "상대 차량 신호 또는 정지선 통과 시점이 확인되지 않으면 결론이 갈립니다.",
        "required_facts": ["opponent_signal", "opponent_stop_line_entry_time", "signal_cycle_or_cctv"],
        "outcomes": [
            {
                "condition_key": "opponent_signal_normal",
                "label": "상대 차량 신호가 녹색 또는 정상 진행 신호인 경우",
                "my_range": "70~90%",
                "other_range": "10~30%",
                "explanation": "내 차량이 황색 전환 뒤 좌회전 또는 교차로 통과를 계속했고 상대 차량은 정상 직진 신호였다면, 내 차량의 진입 판단과 양보 의무가 더 무겁게 평가될 수 있습니다.",
                "basis": ["내 차량 정지선 통과 시점", "황색·적색 전환 시점", "상대 차량 진행 신호", "교차로 CCTV 또는 신호 주기표"],
                "required_facts": ["opponent_signal", "signal_cycle_or_cctv"],
            },
            {
                "condition_key": "opponent_signal_violation",
                "label": "상대 차량도 적색 또는 신호위반으로 진입한 경우",
                "my_range": "20~40%",
                "other_range": "60~80%",
                "explanation": "상대 차량이 적색 신호 또는 신호위반 상태로 진입했다면 상대 차량의 신호준수·전방주시 의무 위반이 중심 쟁점이 됩니다.",
                "basis": ["상대 차량 신호 색상", "상대 차량 정지선 통과 시점", "교차로 CCTV", "목격자 또는 신호체계 자료"],
                "required_facts": ["opponent_signal", "opponent_stop_line_entry_time"],
            },
        ],
    }


def _centerline_branches(scenario_type: str, facts: dict[str, Any], text: str) -> dict[str, Any]:
    haystack = _haystack(facts, text)
    centerline = (
        scenario_type == "centerline_obstacle_collision"
        or facts.get("centerline_crossed") is True
        or any(token in haystack for token in ("중앙선", "황색 실선", "centerline"))
    )
    if not centerline:
        return {}
    reason = str(facts.get("centerline_cross_reason") or facts.get("centerline_reason") or "").strip().lower()
    reason_unclear = not reason or reason in {"unknown", "unclear", "확인 중", "모름"}
    obstacle_context = (
        facts.get("road_obstruction") is True
        or facts.get("illegal_parking_obstruction") is True
        or any(token in haystack for token in ("주차", "주정차", "장애물", "가구", "적치물", "obstacle"))
    )
    if not (reason_unclear or obstacle_context):
        return {}
    return {
        "type": "centerline_reason_uncertainty",
        "reason": "중앙선 침범이 불가피한 장애물 회피인지, 무리한 중앙선 침범인지에 따라 책임 방향이 달라집니다.",
        "required_facts": ["centerline_cross_reason", "road_obstruction", "opposing_vehicle_avoidability"],
        "outcomes": [
            {
                "condition_key": "centerline_obstacle_unavoidable",
                "label": "불법 주정차·장애물 회피가 불가피했던 경우",
                "my_range": "20~40%",
                "other_range": "60~80%",
                "explanation": "정상 차로가 막혀 중앙선 일부 침범이 불가피했고, 대향 차량이 감속·회피할 수 있었는데 그대로 진행했다면 상대 책임이 더 크게 검토될 수 있습니다.",
                "basis": ["불법 주정차 또는 장애물 위치", "내 차량 정차·감속 여부", "대향 차량 전방주시·감속 가능성", "후속 추돌 분리"],
                "required_facts": ["road_obstruction", "ego_stopped_or_slowed", "opposing_vehicle_avoidability"],
            },
            {
                "condition_key": "centerline_illegal_or_avoidable_crossing",
                "label": "장애물 회피가 충분히 가능했거나 무리한 중앙선 침범인 경우",
                "my_range": "60~80%",
                "other_range": "20~40%",
                "explanation": "중앙선 침범을 피할 수 있었거나 대향 차량 진행을 충분히 기다릴 수 있었다면 중앙선을 넘은 차량의 책임이 커질 수 있습니다.",
                "basis": ["회피 가능한 대기 공간", "대향 차량 접근 거리", "중앙선 침범 지속 시간", "진행 재개 시점"],
                "required_facts": ["avoidable_crossing", "oncoming_vehicle_distance", "waiting_space"],
            },
        ],
    }


def _rear_stop_branches(scenario_type: str, facts: dict[str, Any], text: str) -> dict[str, Any]:
    haystack = _haystack(facts, text)
    rear_context = (
        scenario_type == "rear_end_collision"
        or facts.get("rear_vehicle_collision") is True
        or any(token in haystack for token in ("후방", "후미", "뒤차", "뒤에서", "rear"))
    )
    stopped_context = facts.get("stopped") is True or facts.get("front_vehicle_stopped") is True or "정차" in haystack or "멈" in haystack
    if not (rear_context and stopped_context):
        return {}
    stop_reason = str(facts.get("stop_reason") or facts.get("sudden_brake_reason") or facts.get("lawful_stop_reason") or "").strip().lower()
    if stop_reason and stop_reason not in {"unknown", "unclear", "모름", "확인 중"}:
        return {}
    return {
        "type": "stop_reason_uncertainty",
        "reason": "앞차 또는 내 차량이 멈춘 이유가 확인되지 않으면 후방추돌 과실 조정이 달라집니다.",
        "required_facts": ["stop_reason", "sudden_brake", "brake_light", "following_distance"],
        "outcomes": [
            {
                "condition_key": "lawful_or_traffic_stop",
                "label": "신호·정체·보행자 보호 등 정당한 정차인 경우",
                "my_range": "0~10%",
                "other_range": "90~100%",
                "explanation": "정당한 이유로 정차했고 뒤차가 안전거리를 확보하지 못해 추돌했다면 뒤차 책임을 중심으로 봅니다.",
                "basis": ["정차 사유", "브레이크등", "뒤차 안전거리", "충돌 직전 속도"],
                "required_facts": ["stop_reason", "brake_light", "following_distance"],
            },
            {
                "condition_key": "unnecessary_sudden_stop",
                "label": "이유 없는 급정차 또는 불필요한 정차인 경우",
                "my_range": "10~30%",
                "other_range": "70~90%",
                "explanation": "앞차 정차가 객관적으로 불필요하거나 급정거 사유가 없었다면 앞차 과실이 일부 가산될 수 있습니다.",
                "basis": ["급정거 여부", "정차 사유 부재", "후방 차량 반응 가능 시간", "브레이크등 정상 여부"],
                "required_facts": ["sudden_brake", "stop_reason", "reaction_time_gap"],
            },
        ],
    }


def _visibility_speed_branches(scenario_type: str, facts: dict[str, Any], text: str) -> dict[str, Any]:
    haystack = _haystack(facts, text)
    visibility_or_unlit = (
        scenario_type in {"parking_or_stopped_vehicle_accident", "stealth_illegal_parked_vehicle_collision"}
        or facts.get("stopped_vehicle_without_lights") is True
        or facts.get("night_no_lights_or_low_visibility") is True
        or any(token in haystack for token in ("무등화", "스텔스", "야간", "시야", "unlit", "visibility"))
    )
    speed_unknown_or_issue = (
        facts.get("speeding") is True
        or facts.get("overspeeding") is True
        or _unknown(facts.get("reported_speed_kmh"))
        or _unknown(facts.get("speed_limit_kmh"))
        or any(token in haystack for token in ("과속", "제한속도", "km/h", "시속"))
    )
    if not (visibility_or_unlit and speed_unknown_or_issue):
        return {}
    return {
        "type": "visibility_speed_uncertainty",
        "reason": "무등화·시야·속도·회피 가능성은 민사 과실과 형사 책임을 분리해서 봐야 합니다.",
        "required_facts": ["lighting_state", "visibility", "reported_speed_kmh", "speed_limit_kmh", "avoidability"],
        "outcomes": [
            {
                "condition_key": "unlit_low_visibility_unavoidable",
                "label": "무등화·저시야로 회피가 거의 불가능했던 경우",
                "my_range": "0~20%",
                "other_range": "80~100%",
                "explanation": "상대 차량이 통행 공간에 식별 조치 없이 정차했고 제한속도 준수 상태에서도 회피가 어려웠다면 상대 책임을 강하게 주장할 수 있습니다.",
                "basis": ["등화 상태", "정차 위치", "조도·시야", "제한속도 준수 여부", "회피 가능성 감정"],
                "required_facts": ["lighting_state", "avoidability", "speed_limit_kmh"],
            },
            {
                "condition_key": "speeding_or_visible_obstacle",
                "label": "과속 또는 발견 가능성이 인정되는 경우",
                "my_range": "20~50%",
                "other_range": "50~80%",
                "explanation": "내 차량 과속이나 전방주시로 발견 가능한 정차 차량이었다는 점이 확인되면 내 책임 범위가 커질 수 있습니다.",
                "basis": ["실제 속도", "제한속도", "충돌 전 인지 가능 시간", "전조등·도로조명"],
                "required_facts": ["reported_speed_kmh", "visibility", "reaction_time_gap"],
            },
        ],
    }


def _non_contact_branches(scenario_type: str, facts: dict[str, Any], text: str) -> dict[str, Any]:
    haystack = _haystack(facts, text)
    non_contact = (
        facts.get("non_contact_trigger") is True
        or any(token in haystack for token in ("비접촉", "자전거", "급히 멈", "급정차 유발", "trigger"))
    )
    rear_context = scenario_type == "rear_end_collision" or facts.get("rear_vehicle_collision") is True or "후방" in haystack or "뒤" in haystack
    if not (non_contact and rear_context):
        return {}
    return {
        "type": "non_contact_trigger_uncertainty",
        "reason": "직접 충돌 차량과 사고를 유발한 객체가 다를 수 있으므로 원인 제공자와 뒤차 안전거리를 분리해야 합니다.",
        "required_facts": ["trigger_actor_type", "trigger_actor_behavior", "reaction_time_gap", "rear_vehicle_following_distance"],
        "outcomes": [
            {
                "condition_key": "third_party_trigger_primary",
                "label": "자전거·보행자·물체가 비접촉으로 사고를 유발한 경우",
                "my_range": "0~20%",
                "other_range": "80~100%",
                "explanation": "내 차량 정지는 사고 회피를 위한 불가피한 조치였고, 뒤차가 충분한 반응 시간이 있었는데 추돌했다면 뒤차와 유발 주체의 책임을 우선 검토합니다.",
                "basis": ["유발 객체 종류", "유발 객체 진행 방향", "내 차량 정지 불가피성", "뒤차 반응 시간"],
                "required_facts": ["trigger_actor_type", "reaction_time_gap", "rear_vehicle_collision"],
            },
            {
                "condition_key": "ego_sudden_maneuver_primary",
                "label": "내 차량이 급차로변경 후 급정차한 경우",
                "my_range": "40~70%",
                "other_range": "30~60%",
                "explanation": "유발 객체가 있더라도 내 차량이 급차로변경이나 예측 어려운 급정차를 했다면 내 책임이 커질 수 있습니다.",
                "basis": ["차로변경 시점", "방향지시등", "정지까지 시간", "뒤차와 거리"],
                "required_facts": ["lane_change_timing", "turn_signal", "reaction_time_gap"],
            },
        ],
    }


def _secondary_collision_branches(facts: dict[str, Any], text: str) -> dict[str, Any]:
    haystack = _haystack(facts, text)
    secondary = facts.get("secondary_collision") is True or any(token in haystack for token in ("2차 충돌", "뒤차하고도", "후속 추돌", "secondary"))
    if not secondary:
        return {}
    return {
        "type": "secondary_collision_split",
        "reason": "1차 충돌과 후속 추돌은 원인과 책임 주체가 다를 수 있어 분리 검토가 필요합니다.",
        "required_facts": ["first_collision_sequence", "secondary_collision_sequence", "rear_vehicle_following_distance"],
        "outcomes": [
            {
                "condition_key": "first_and_secondary_collision_split",
                "label": "1차 충돌과 후속 추돌을 분리하는 경우",
                "my_range": "사고별 별도 산정",
                "other_range": "사고별 별도 산정",
                "explanation": "대향 차량과의 1차 충돌, 뒤차와의 2차 추돌은 각각의 원인과 회피 가능성을 따로 보아야 합니다.",
                "basis": ["1차 충돌 시점", "2차 추돌 시점", "후속 차량 안전거리", "1차 사고 후 정차 위치"],
                "required_facts": ["first_collision_sequence", "secondary_collision_sequence"],
            }
        ],
    }


def _haystack(facts: dict[str, Any], text: str) -> str:
    values = [text or ""]
    values.extend(str(value) for value in facts.values() if value is not None)
    return " ".join(values).lower()


def _unknown(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip().lower()
    return text in {"", "unknown", "unclear", "none", "null", "모름", "확인 중", "확인필요", "확인 필요"}
