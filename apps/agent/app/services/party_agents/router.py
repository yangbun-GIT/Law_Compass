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
    direct_target = _detect_direct_collision_target(haystack, facts)
    declared_party = canonical_party(facts.get("knia_major_party_type") or facts.get("accident_party_type"))
    declared_partner = canonical_party(facts.get("direct_collision_partner_type") or facts.get("collision_partner_type"))
    user_party, user_reason = _infer_from_user_text(haystack, facts)
    video_party, video_confidence = _infer_from_video(video_metadata or {})

    direct_party = str(direct_target.get("party") or "unknown")
    direct_locked = direct_party != "unknown" and float(direct_target.get("confidence") or 0.0) >= 0.75
    if direct_locked:
        party = direct_party
        reason = str(direct_target.get("reason") or "explicit_direct_collision_target")
        confidence = float(direct_target.get("confidence") or 0.9)
    else:
        party = declared_party if declared_party != "unknown" else declared_partner
        reason = "structured_party_type" if party != "unknown" else "no_structured_party_type"
        confidence = 0.9 if party != "unknown" else 0.0

    if party == "unknown" and user_party != "unknown":
        party = user_party
        reason = user_reason
        confidence = 0.86
    elif not direct_locked and party != "unknown" and user_party != "unknown" and user_party != party:
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

    scenario, subtype, tags, patch = _scenario_hint_for_party(party, haystack, {**facts, **(direct_target.get("facts_patch") or {})})
    if isinstance(direct_target.get("facts_patch"), dict):
        patch.update(direct_target["facts_patch"])
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


def _detect_direct_collision_target(haystack: str, facts: dict[str, Any]) -> dict[str, Any]:
    partner = canonical_party(facts.get("direct_collision_partner_type"))
    if partner != "unknown":
        return {
            "party": partner,
            "confidence": 0.9,
            "reason": "structured_direct_collision_partner",
            "facts_patch": {},
        }

    direct_collision = _has_any(
        haystack,
        (
            "충돌",
            "추돌",
            "부딪",
            "접촉",
            "쳤",
            "치었",
            "들이받",
            "들이박",
            "박았",
            "사고",
            "발생",
            "파손",
            "hit",
            "collision",
            "collided",
        ),
    )
    sudden_entry = _has_any(haystack, ("튀어나", "뛰어나", "갑자기 나", "갑자기 들어", "차도로 들어", "도로쪽", "차도"))
    non_contact = _has_any(haystack, ("비접촉", "직접 충돌 없음", "접촉 없이", "피하려고", "회피하다"))
    rear_vehicle_collision = _has_any(haystack, ("뒤차", "뒷차", "후방", "후미", "버스가", "앞차", "상대 차량", "차량과 충돌"))

    person_tokens = (
        "보행자",
        "사람",
        "작업자",
        "공사 담당자",
        "공사 인부",
        "도로 작업자",
        "측량 작업자",
        "신호수",
        "교통 통제원",
        "도로 폭 측정",
        "도로공사 인원",
        "인부",
        "차도에 나온 사람",
    )
    worker_tokens = (
        "작업자",
        "공사 담당자",
        "공사 인부",
        "도로 작업자",
        "측량 작업자",
        "신호수",
        "교통 통제원",
        "도로 폭 측정",
        "도로공사 인원",
        "인부",
    )
    bicycle_tokens = ("자전거", "자전거를 탄 사람", "자전거 운전자", "bicycle", "cyclist")
    motorcycle_tokens = ("오토바이", "이륜차", "원동기장치자전거", "바이크", "motorcycle", "motorbike")
    object_tokens = ("라바콘", "콘", "공사 표지판", "표지판", "펜스", "방호벽", "가드레일", "전봇대", "벽", "중앙분리대", "시설물", "장비", "낙하물")
    vehicle_tokens = ("차량", "상대 차량", "상대차", "앞차", "뒤차", "뒷차", "트럭", "화물차", "승용차", "버스", "주차 차량", "정차 차량")

    if non_contact and rear_vehicle_collision and _has_any(haystack, bicycle_tokens + person_tokens):
        trigger = "bicycle" if _has_any(haystack, bicycle_tokens) else "pedestrian"
        return {
            "party": "car_vs_car",
            "confidence": 0.86,
            "reason": "non_contact_trigger_with_vehicle_direct_collision",
            "facts_patch": {
                "trigger_actor_type": trigger,
                "non_contact_trigger": True,
                "direct_collision_partner_type": "vehicle",
                "collision_partner_type": "vehicle",
            },
        }

    if direct_collision and _has_any(haystack, bicycle_tokens):
        return {
            "party": "car_vs_bicycle",
            "confidence": 0.93,
            "reason": "explicit_direct_bicycle_collision",
            "facts_patch": {
                "collision_partner_type": "bicycle",
                "direct_collision_partner_type": "bicycle",
                "direct_collision_target": "bicycle",
                "bicycle_involved": True,
            },
        }

    if direct_collision and _has_any(haystack, motorcycle_tokens):
        return {
            "party": "car_vs_motorcycle",
            "confidence": 0.93,
            "reason": "explicit_direct_motorcycle_collision",
            "facts_patch": {
                "collision_partner_type": "motorcycle",
                "direct_collision_partner_type": "motorcycle",
                "direct_collision_target": "motorcycle",
                "motorcycle_involved": True,
            },
        }

    person_signal = _has_any(haystack, person_tokens)
    if person_signal and (direct_collision or sudden_entry):
        worker = _has_any(haystack, worker_tokens)
        road_work = worker or _has_any(haystack, ("도로 공사", "공사구역", "공사 구역", "도로 폭 측정", "측량"))
        direct_target = "road_work_worker" if worker else "pedestrian"
        scenario = "pedestrian_road_work_worker_accident" if road_work else "pedestrian_sudden_entry_accident"
        subtype = "pedestrian_sudden_entry_from_road_work" if road_work and sudden_entry else None
        return {
            "party": "car_vs_person",
            "confidence": 0.94 if worker else 0.9,
            "reason": "explicit_direct_pedestrian_worker_collision" if worker else "explicit_direct_pedestrian_collision",
            "facts_patch": {
                "collision_partner_type": "pedestrian",
                "direct_collision_partner_type": "pedestrian",
                "direct_collision_target": direct_target,
                "pedestrian_involved": True,
                "pedestrian_worker": bool(worker),
                "road_work_context": bool(road_work),
                "pedestrian_sudden_entry": bool(sudden_entry),
                "accident_type": scenario,
                "scenario_type": scenario,
                "accident_subtype": subtype,
                "environment_context": _environment_context(haystack),
                "party_confidence": 0.94 if worker else 0.9,
                "party_reason": "직접 충돌 대상으로 사람/작업자가 확인되었습니다.",
            },
        }

    if direct_collision and _has_any(haystack, object_tokens):
        return {
            "party": "car_vs_object",
            "confidence": 0.9,
            "reason": "explicit_direct_object_collision",
            "facts_patch": {
                "collision_partner_type": "object",
                "direct_collision_partner_type": "object",
                "direct_collision_target": "road_object",
                "environment_context": _environment_context(haystack),
            },
        }

    if direct_collision and _has_any(haystack, vehicle_tokens):
        return {
            "party": "car_vs_car",
            "confidence": 0.88,
            "reason": "explicit_direct_vehicle_collision",
            "facts_patch": {
                "collision_partner_type": "vehicle",
                "direct_collision_partner_type": "vehicle",
                "direct_collision_target": "vehicle",
                "environment_context": _environment_context(haystack),
            },
        }

    if _has_any(haystack, ("혼자", "단독", "단독사고", "전복", "미끄러", "도로 이탈")) and not _has_any(haystack, person_tokens + bicycle_tokens + motorcycle_tokens + vehicle_tokens):
        return {
            "party": "single_vehicle",
            "confidence": 0.82,
            "reason": "single_vehicle_without_direct_counterparty",
            "facts_patch": {"collision_partner_type": "none", "environment_context": _environment_context(haystack)},
        }

    return {"party": "unknown", "confidence": 0.0, "reason": "no_direct_collision_target", "facts_patch": {}}


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
        if item.get("context_only") is True or item.get("is_context_only") is True:
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
        patch.update(
            {
                key: value
                for key, value in {
                    "pedestrian_involved": facts.get("pedestrian_involved"),
                    "pedestrian_worker": facts.get("pedestrian_worker"),
                    "road_work_context": facts.get("road_work_context"),
                    "pedestrian_sudden_entry": facts.get("pedestrian_sudden_entry"),
                    "direct_collision_target": facts.get("direct_collision_target"),
                    "environment_context": facts.get("environment_context"),
                }.items()
                if value is not None
            }
        )
        tags = ["pedestrian"]
        if facts.get("road_work_context") or _has_any(haystack, ("공사", "작업자", "도로 폭 측정", "측량")):
            tags.extend(["road_work", "worker", "sudden_entry"] if facts.get("pedestrian_sudden_entry") or _has_any(haystack, ("튀어나", "갑자기")) else ["road_work", "worker"])
            return "pedestrian_road_work_worker_accident", "pedestrian_sudden_entry_from_road_work" if facts.get("pedestrian_sudden_entry") else None, tags, patch
        if _has_any(haystack, ("갑자기", "튀어나", "뛰어나", "차도")):
            tags.extend(["sudden_entry", "roadway"])
            return "pedestrian_sudden_entry_accident", None, tags, patch
        if _has_any(haystack, ("횡단보도", "보행자 신호")):
            tags.extend(["crosswalk"])
            return "pedestrian_crosswalk_accident", None, tags, patch
        if _has_any(haystack, ("도로 가장자리", "차도 가장자리", "갓길")):
            tags.extend(["road_edge"])
            return "pedestrian_on_road_edge_accident", None, tags, patch
        return str(facts.get("accident_type") or "pedestrian_crosswalk_accident"), None, tags, patch
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


def _environment_context(haystack: str) -> dict[str, bool]:
    return {
        "road": _has_any(haystack, ("도로", "차도", "차로")),
        "intersection": _has_any(haystack, ("교차로", "우회전", "좌회전", "직진")),
        "construction": _has_any(haystack, ("공사", "작업자", "도로 폭 측정", "측량", "라바콘", "방호벽")),
        "crosswalk": _has_any(haystack, ("횡단보도", "보행자 신호")),
    }
