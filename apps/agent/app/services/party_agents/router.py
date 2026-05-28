from __future__ import annotations

from typing import Any

from app.services.party_agents.base import PARTY_TYPES, PartyAgentResult, canonical_party
from app.services.party_agents.car_vs_bicycle_agent import CarVsBicycleAgent
from app.services.party_agents.car_vs_car_agent import CarVsCarAgent
from app.services.party_agents.car_vs_motorcycle_agent import CarVsMotorcycleAgent
from app.services.party_agents.car_vs_object_agent import CarVsObjectAgent
from app.services.party_agents.car_vs_person_agent import CarVsPersonAgent
from app.services.party_agents.single_vehicle_agent import SingleVehicleAgent


AGENTS = {
    "car_vs_car": CarVsCarAgent(),
    "car_vs_person": CarVsPersonAgent(),
    "car_vs_bicycle": CarVsBicycleAgent(),
    "car_vs_motorcycle": CarVsMotorcycleAgent(),
    "car_vs_object": CarVsObjectAgent(),
    "single_vehicle": SingleVehicleAgent(),
}


def route_party_agent(
    *,
    description_text: str,
    structured_facts: dict[str, Any] | None = None,
    selected_keywords: list[str] | None = None,
    video_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    facts = structured_facts or {}
    keywords = selected_keywords or []
    haystack = _compact_text(" ".join([description_text or "", " ".join(keywords), str(facts)]))
    declared_party = canonical_party(facts.get("knia_major_party_type") or facts.get("accident_party_type"))
    declared_partner = canonical_party(facts.get("direct_collision_partner_type") or facts.get("collision_partner_type"))
    user_party, user_reason = _infer_from_user_text(haystack, facts)
    video_party, video_confidence = _infer_from_video(video_metadata or {})

    party = declared_party if declared_party != "unknown" else declared_partner
    reason = "structured_party_type" if party != "unknown" else "no_structured_party_type"
    confidence = 0.9 if party != "unknown" else 0.0

    if party == "unknown" and user_party != "unknown":
        party = user_party
        reason = user_reason
        confidence = 0.86
    elif party != "unknown" and user_party != "unknown" and user_party != party:
        # Explicit user text is allowed to refine older structured facts unless the
        # structured facts already describe a direct collision partner.
        if not facts.get("direct_collision_partner_type") and not facts.get("knia_major_party_type"):
            party = user_party
            reason = user_reason
            confidence = 0.84

    if party == "unknown" and video_party != "unknown" and video_confidence >= 0.88:
        party = video_party
        reason = "high_confidence_video_party"
        confidence = video_confidence

    conflict: dict[str, Any] | None = None
    if party != "unknown" and video_party != "unknown" and video_party != party and video_confidence >= 0.9:
        conflict = {
            "status": "party_conflict_video_high_confidence",
            "user_or_structured_party_type": party,
            "video_party_type": video_party,
            "video_confidence": video_confidence,
        }

    if party == "unknown":
        result = PartyAgentResult(
            major_party_type="unknown",
            scenario_type=str(facts.get("accident_type") or "general_collision"),
            confidence=0.0,
            facts_patch={},
            excluded_party_types=[],
            reason="no_direct_collision_partner_identified",
        )
        data = result.to_dict()
        if conflict:
            data["conflict"] = conflict
        return data

    scenario, subtype, tags, patch = _scenario_hint_for_party(party, haystack, facts)
    if conflict:
        patch["party_conflict"] = conflict
    result = AGENTS[party].build_result(
        confidence=confidence,
        reason=reason,
        scenario_type=scenario,
        scenario_subtype=subtype,
        facts_patch=patch,
        scenario_tags=tags,
    ).to_dict()
    return result


def _infer_from_user_text(haystack: str, facts: dict[str, Any]) -> tuple[str, str]:
    partner = canonical_party(facts.get("direct_collision_partner_type") or facts.get("collision_partner_type"))
    if partner != "unknown":
        return partner, "structured_collision_partner"

    direct = _has_any(haystack, ("충돌", "추돌", "부딪", "들이받", "들이박", "박았", "쳤", "접촉"))
    if direct and _has_any(haystack, ("보행자", "사람", "횡단보도 보행자", "아이와", "사람과", "보행자와")):
        return "car_vs_person", "explicit_user_pedestrian_collision"
    if direct and _has_any(haystack, ("자전거와", "자전거를", "자전거 충돌", "자전거 추돌", "차대자전거")):
        return "car_vs_bicycle", "explicit_user_bicycle_collision"
    if direct and _has_any(haystack, ("오토바이", "이륜차", "원동기장치자전거", "바이크")):
        return "car_vs_motorcycle", "explicit_user_motorcycle_collision"
    if direct and _has_any(haystack, ("가드레일", "전봇대", "벽", "중앙분리대", "낙하물", "시설물", "기둥", "기물")):
        return "car_vs_object", "explicit_user_object_collision"
    if _has_any(haystack, ("단독사고", "혼자", "내 차량만", "전복", "도로 이탈", "미끄러")) and not _has_any(
        haystack, ("상대", "앞차", "뒤차", "보행자", "자전거", "오토바이")
    ):
        return "single_vehicle", "single_vehicle_without_other_party"
    if _has_any(haystack, ("트럭", "승용차", "버스", "화물차", "주차 차량", "정차 차량", "앞차", "뒤차", "뒷차", "상대 차량", "상대차", "차량")):
        return "car_vs_car", "explicit_user_vehicle_party"
    return "unknown", "no_user_party_signal"


def _infer_from_video(video_metadata: dict[str, Any]) -> tuple[str, float]:
    contract = video_metadata if "fact_patch" in video_metadata else {}
    fact_patch = contract.get("fact_patch") if isinstance(contract.get("fact_patch"), dict) else {}
    candidates: list[tuple[str, float]] = []
    for key in ("direct_collision_partner_type", "collision_partner_type"):
        party = canonical_party(fact_patch.get(key))
        if party != "unknown":
            candidates.append((party, 0.92 if key == "direct_collision_partner_type" else 0.88))
    for item in contract.get("accepted_observations") or []:
        if not isinstance(item, dict):
            continue
        if item.get("field") in {"direct_collision_partner_type", "collision_partner_type"}:
            party = canonical_party(item.get("value"))
            if party != "unknown":
                candidates.append((party, float(item.get("confidence") or 0.0)))
    if not candidates:
        return "unknown", 0.0
    return max(candidates, key=lambda item: item[1])


def _scenario_hint_for_party(
    party: str,
    haystack: str,
    facts: dict[str, Any],
) -> tuple[str, str | None, list[str], dict[str, Any]]:
    patch: dict[str, Any] = {}
    tags: list[str] = []
    if party == "car_vs_car":
        if _has_any(haystack, ("스텔스", "무등화", "등화 없이", "교량 밑", "교량 아래")) and _has_any(haystack, ("주차", "정차", "트럭", "화물차")):
            patch.update({"is_stealth_parked_vehicle_collision": True, "is_parked_vehicle_collision": True})
            return "stealth_illegal_parked_vehicle_collision", "night_unlit_illegal_parked_vehicle_collision", ["parking", "stopped_vehicle", "unlit_stopped_vehicle", "visibility", "night"], patch
        if _has_any(haystack, ("차선변경", "진로변경", "끼어들", "깜빡이", "방향지시등")):
            return "lane_change_collision", None, ["lane_change", "turn_signal"], patch
        if _has_any(haystack, ("교차로", "신호위반", "적색", "빨간불", "직진", "좌회전")) and not _has_any(haystack, ("신호대기 중 정차", "신호 대기 중 정차")):
            scenario = "intersection_signal_violation" if _has_any(haystack, ("신호위반", "적색", "빨간불")) else "intersection_collision"
            return scenario, None, ["intersection", "signal_violation"], patch
        if _has_any(haystack, ("중앙선", "황색 실선", "장애물", "불법 주정차")):
            return "centerline_obstacle_collision", None, ["centerline", "road_obstruction"], patch
        if _has_any(haystack, ("주차", "정차 차량", "주정차")):
            return "parking_or_stopped_vehicle_accident", None, ["parking", "stopped_vehicle"], patch
        if _has_any(haystack, ("후미", "후방", "뒤차", "뒷차", "앞차", "추돌", "신호대기")):
            return "rear_end_collision", None, ["rear_end", "safe_distance"], patch
        return str(facts.get("accident_type") or "general_vehicle_collision"), None, ["vehicle"], patch
    if party == "car_vs_person":
        return "pedestrian_crosswalk_accident", None, ["pedestrian", "crosswalk"], patch
    if party == "car_vs_bicycle":
        return "bicycle_collision", None, ["bicycle"], patch
    if party == "car_vs_motorcycle":
        return "motorcycle_collision", None, ["motorcycle", "two_wheeler"], patch
    if party == "car_vs_object":
        return "object_collision", None, ["object"], patch
    if party == "single_vehicle":
        return "single_vehicle_accident", None, ["single_vehicle"], patch
    return "general_collision", None, [], patch


def _compact_text(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _has_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token.lower() in text for token in tokens)
