from __future__ import annotations

from typing import Any


FRONT_VEHICLE = "front_vehicle"
FOLLOWING_VEHICLE = "following_vehicle"
STRAIGHT_VEHICLE = "straight_vehicle"
LANE_CHANGING_VEHICLE = "lane_changing_vehicle"
SIGNAL_COMPLIANT_VEHICLE = "signal_compliant_vehicle"
SIGNAL_VIOLATION_VEHICLE = "signal_violation_vehicle"
VEHICLE = "vehicle"
PEDESTRIAN = "pedestrian"
BICYCLE = "bicycle"
OBJECT_OR_FACILITY = "object_or_facility"
SINGLE_VEHICLE = "single_vehicle"
UNKNOWN_ROLE = "unknown"

_KNOWN_ROLES = {
    FRONT_VEHICLE,
    FOLLOWING_VEHICLE,
    STRAIGHT_VEHICLE,
    LANE_CHANGING_VEHICLE,
    SIGNAL_COMPLIANT_VEHICLE,
    SIGNAL_VIOLATION_VEHICLE,
    VEHICLE,
    PEDESTRIAN,
    BICYCLE,
    OBJECT_OR_FACILITY,
    SINGLE_VEHICLE,
}


def infer_user_vehicle_role(text: str, facts: dict[str, Any] | None = None, scenario_type: str | None = None) -> str:
    facts = facts or {}
    explicit = facts.get("user_vehicle_role") or facts.get("my_vehicle_role") or facts.get("vehicle_role")
    if explicit in _KNOWN_ROLES:
        return str(explicit)

    haystack = _haystack(text, facts)
    if _is_rear_end_context(scenario_type, haystack):
        if _facts_indicate_front_vehicle_rear_end(facts):
            return FRONT_VEHICLE
        if _has_front_vehicle_phrase(haystack):
            return FRONT_VEHICLE
        if _has_following_vehicle_phrase(haystack):
            return FOLLOWING_VEHICLE
        if facts.get("stopped") and not facts.get("sudden_brake"):
            return FRONT_VEHICLE

    if scenario_type == "lane_change_collision":
        if _truthy_any(facts, ["my_lane_change", "user_lane_change", "changed_lane_by_user"]):
            return LANE_CHANGING_VEHICLE
        if _truthy_any(facts, ["opponent_lane_change", "other_lane_change", "changed_lane_by_opponent"]):
            return STRAIGHT_VEHICLE
        if _has_my_action(haystack, ["차선변경", "차로변경", "진로변경", "끼어들", "끼어들기"]):
            return LANE_CHANGING_VEHICLE
        if _has_opponent_action(haystack, ["차선변경", "차로변경", "진로변경", "끼어들", "끼어들기"]):
            return STRAIGHT_VEHICLE

    if scenario_type == "intersection_signal_violation":
        if _truthy_any(facts, ["my_signal_violation", "user_signal_violation"]):
            return SIGNAL_VIOLATION_VEHICLE
        if _truthy_any(facts, ["opponent_signal_violation", "other_signal_violation"]):
            return SIGNAL_COMPLIANT_VEHICLE
        if _has_my_action(haystack, ["신호위반", "빨간불", "적색신호", "정지신호"]):
            return SIGNAL_VIOLATION_VEHICLE
        if _has_opponent_action(haystack, ["신호위반", "빨간불", "적색신호", "정지신호"]):
            return SIGNAL_COMPLIANT_VEHICLE

    if scenario_type in {"pedestrian_crosswalk_accident", "school_zone_child_accident"}:
        if _has_user_role_phrase(haystack, ["보행자", "걸어가", "횡단 중", "횡단보도 건너", "도보"]):
            return PEDESTRIAN
        return VEHICLE

    if scenario_type == "bicycle_collision":
        if _has_user_role_phrase(haystack, ["자전거", "자전거를 타", "자전거 운전자", "자전거 주행"]):
            return BICYCLE
        return VEHICLE

    if scenario_type == "object_collision":
        return VEHICLE

    if scenario_type == "single_vehicle_accident":
        return SINGLE_VEHICLE

    return UNKNOWN_ROLE


def map_fault_ratio_to_user(
    *,
    scenario_type: str,
    fault: dict[str, Any],
    text: str,
    facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    role = infer_user_vehicle_role(text, facts, scenario_type)
    a = _as_int(fault.get("A"))
    b = _as_int(fault.get("B"))
    if a is None:
        a = _as_int(fault.get("my"))
    if b is None:
        b = _as_int(fault.get("other"))
    if a is None or b is None:
        return {**fault, "user_vehicle_role": role}

    user_party = _user_knia_party(scenario_type, role)
    if user_party == "B":
        my, other = b, a
    else:
        my, other = a, b

    mapped = {
        **fault,
        "my": my,
        "other": other,
        "user_vehicle_role": role,
    }
    label = _role_label(role, user_party)
    if label:
        mapped["user_vehicle_role_label"] = label
    return mapped


def _user_knia_party(scenario_type: str, role: str) -> str:
    if scenario_type == "rear_end_collision":
        if role == FRONT_VEHICLE:
            return "B"
        return "A"
    if scenario_type == "lane_change_collision":
        if role == LANE_CHANGING_VEHICLE:
            return "B"
        return "A"
    if scenario_type == "intersection_signal_violation":
        if role == SIGNAL_VIOLATION_VEHICLE:
            return "B"
        return "A"
    if scenario_type in {"pedestrian_crosswalk_accident", "school_zone_child_accident"}:
        if role == PEDESTRIAN:
            return "B"
        return "A"
    if scenario_type == "bicycle_collision":
        if role == BICYCLE:
            return "B"
        return "A"
    return "A"


def _role_label(role: str, party: str) -> str | None:
    labels = {
        FRONT_VEHICLE: "내 차량은 앞차/정차 차량(B)으로 해석했습니다.",
        FOLLOWING_VEHICLE: "내 차량은 뒤차/추돌 차량(A)으로 해석했습니다.",
        STRAIGHT_VEHICLE: "내 차량은 직진 차량(A)으로 해석했습니다.",
        LANE_CHANGING_VEHICLE: "내 차량은 진로변경 차량(B)으로 해석했습니다.",
        SIGNAL_COMPLIANT_VEHICLE: "내 차량은 정상 신호 차량(A)으로 해석했습니다.",
        SIGNAL_VIOLATION_VEHICLE: "내 차량은 신호위반 차량(B)으로 해석했습니다.",
        VEHICLE: f"내 차량은 KNIA 기준 {party} 차량으로 해석했습니다.",
        PEDESTRIAN: "사용자는 보행자(B)로 해석했습니다.",
        BICYCLE: "사용자는 자전거 운전자(B)로 해석했습니다.",
        SINGLE_VEHICLE: "내 차량은 단독 사고 차량(A)으로 해석했습니다.",
    }
    return labels.get(role)


def _haystack(text: str, facts: dict[str, Any]) -> str:
    fact_text = " ".join(str(v) for v in facts.values() if isinstance(v, (str, int, float, bool)))
    return " ".join([text or "", fact_text]).lower()


def _is_rear_end_context(scenario_type: str | None, text: str) -> bool:
    return scenario_type == "rear_end_collision" or any(
        word in text for word in ["후미", "뒷차", "뒤에서", "추돌", "받힘", "받혔"]
    )


def _facts_indicate_front_vehicle_rear_end(facts: dict[str, Any]) -> bool:
    if facts.get("stopped") is not True:
        return False
    if facts.get("sudden_brake") is True:
        return False
    return str(facts.get("opponent_behavior") or "").strip().lower() in {
        "rear_collision",
        "rear_end",
        "rear_impact",
        "hit_from_behind",
    }


def _has_front_vehicle_phrase(text: str) -> bool:
    front_markers = ["정차", "신호대기", "앞차", "앞 차량", "선행차", "선행 차량"]
    impact_markers = ["뒤에서", "후미", "뒷차", "받힘", "받혔", "추돌당", "추돌 받"]
    return _contains_any(text, front_markers) and _contains_any(text, impact_markers)


def _has_following_vehicle_phrase(text: str) -> bool:
    my_markers = ["내가", "제가", "내 차", "제 차", "우리 차"]
    front_markers = ["앞차", "앞 차량", "선행차", "선행 차량"]
    impact_markers = ["추돌", "받음", "들이받", "박았", "박음"]
    if _contains_any(text, my_markers) and _contains_any(text, front_markers) and _contains_any(text, impact_markers):
        return True
    return _contains_any(text, ["전방주시", "안전거리 미확보"])


def _has_my_action(text: str, actions: list[str]) -> bool:
    my_markers = ["내가", "제가", "내 차", "제 차", "우리 차", "본인", "운전자 본인"]
    return _contains_any(text, my_markers) and _contains_any(text, actions)


def _has_opponent_action(text: str, actions: list[str]) -> bool:
    opponent_markers = ["상대", "상대방", "상대 차량", "상대차", "다른 차", "앞차", "옆 차", "옆차"]
    return _contains_any(text, opponent_markers) and _contains_any(text, actions)


def _has_user_role_phrase(text: str, role_markers: list[str]) -> bool:
    my_markers = ["내가", "제가", "나는", "저는", "본인"]
    return _contains_any(text, my_markers) and _contains_any(text, role_markers)


def _truthy_any(facts: dict[str, Any], keys: list[str]) -> bool:
    return any(bool(facts.get(key)) for key in keys)


def _contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return max(0, min(100, int(round(value))))
    return None
