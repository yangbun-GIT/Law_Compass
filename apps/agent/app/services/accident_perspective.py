from __future__ import annotations

import re
from typing import Any


FRONT_VEHICLE = "front_vehicle"
FOLLOWING_VEHICLE = "following_vehicle"
UNKNOWN_ROLE = "unknown"


def infer_user_vehicle_role(text: str, facts: dict[str, Any] | None = None, scenario_type: str | None = None) -> str:
    facts = facts or {}
    explicit = facts.get("user_vehicle_role") or facts.get("my_vehicle_role") or facts.get("vehicle_role")
    if explicit in {FRONT_VEHICLE, FOLLOWING_VEHICLE}:
        return explicit

    haystack = " ".join([text or "", " ".join(str(v) for v in facts.values() if isinstance(v, (str, int, float, bool)))]).lower()
    if scenario_type == "rear_end_collision" or any(word in haystack for word in ["후미", "뒤차", "뒤에서", "추돌"]):
        if _has_front_vehicle_phrase(haystack):
            return FRONT_VEHICLE
        if _has_following_vehicle_phrase(haystack):
            return FOLLOWING_VEHICLE
        if facts.get("stopped") and not facts.get("sudden_brake"):
            return FRONT_VEHICLE
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

    if scenario_type != "rear_end_collision" or role == UNKNOWN_ROLE:
        return {**fault, "my": a, "other": b, "user_vehicle_role": role}

    # KNIA rear-end chart 41-1 defines A as the following/rear vehicle and B as the front/stopped vehicle.
    if role == FRONT_VEHICLE:
        my, other = b, a
        label = "내 차량은 앞차/피추돌 차량으로 해석했습니다."
    else:
        my, other = a, b
        label = "내 차량은 뒤차/추돌 차량으로 해석했습니다."
    return {
        **fault,
        "my": my,
        "other": other,
        "user_vehicle_role": role,
        "user_vehicle_role_label": label,
    }


def _has_front_vehicle_phrase(text: str) -> bool:
    patterns = [
        r"추돌\s*당",
        r"받혔|받히|받힌|들이받혔",
        r"뒤에서\s*(?:.*?)(?:추돌|박|받|들이받)",
        r"뒤차가\s*(?:.*?)(?:추돌|박|들이받)",
        r"상대(?:방|차| 차량)?이\s*(?:뒤에서|후방에서)",
        r"내\s*차(?:량)?(?:가|는)?\s*(?:정차|신호대기)",
        r"신호대기\s*중",
        r"정차\s*중",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def _has_following_vehicle_phrase(text: str) -> bool:
    patterns = [
        r"내가\s*(?:앞차|선행차|차량을|상대차를).*(?:추돌|박|들이받)",
        r"내\s*차(?:량)?(?:가|는)?\s*(?:앞차|선행차|상대차).*(?:추돌|박|들이받)",
        r"앞차를\s*(?:추돌|박|들이받)",
        r"전방주시|안전거리\s*미확보",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return max(0, min(100, int(round(value))))
    return None
