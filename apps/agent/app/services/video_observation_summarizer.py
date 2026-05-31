from __future__ import annotations

from typing import Any


CONFIRMED_MIN_CONFIDENCE = 0.82
LIKELY_MIN_CONFIDENCE = 0.62

FIELD_LABELS = {
    "ego_vehicle_type": "블랙박스 차량 유형",
    "direct_collision_partner_type": "직접 충돌 대상",
    "collision_partner_type": "충돌 상대",
    "primary_collision_target": "충돌 대상",
    "school_zone": "어린이보호구역",
    "speed_limit_kmh": "제한속도",
    "road_marking_school_zone_visible": "어린이보호구역 노면표시",
    "speed_limit_sign_visible": "제한속도 표지",
    "oncoming_bicycle_present": "맞은편 자전거",
    "opposing_direction_actor_type": "맞은편 진행 대상",
    "child_candidate": "어린이 후보",
    "overlay_text_hint": "영상 자막 단서",
    "collision_point_visible": "충돌 지점",
    "collision_point_location": "충돌 위치",
    "impact_visible": "충격 장면",
    "centerline_crossed": "중앙선 침범",
    "opponent_signal_violation": "상대 신호위반",
}

VALUE_LABELS = {
    "motorcycle": "오토바이",
    "two_wheeler": "이륜차",
    "bicycle": "자전거",
    "cyclist": "자전거",
    "vehicle": "차량",
    "pedestrian": "보행자",
    "object": "시설물",
    "front_center": "전방 중앙",
    "front_left": "전방 좌측",
    "front_right": "전방 우측",
    "rear": "후방",
    "left": "좌측",
    "right": "우측",
    "true": "확인됨",
    "false": "확인되지 않음",
}

SUMMARY_FIELDS = (
    "ego_vehicle_type",
    "school_zone",
    "speed_limit_kmh",
    "oncoming_bicycle_present",
    "opposing_direction_actor_type",
    "direct_collision_partner_type",
    "primary_collision_target",
    "collision_point_visible",
    "impact_visible",
)


def summarize_client_pre_observations(client_pre_observations: dict[str, Any] | None) -> dict[str, Any]:
    """Compatibility wrapper for the mobile video-only demo route.

    The mobile demo endpoint predates ``build_video_scene_summary`` and imports
    this function directly during app startup. Keep this small adapter so the
    route can reuse the same visual-summary contract without breaking imports.
    """

    source = client_pre_observations if isinstance(client_pre_observations, dict) else {}
    fact_patch = source.get("fact_patch") if isinstance(source.get("fact_patch"), dict) else {}
    accepted = _observations(source.get("accepted_observations"))
    uncertain = _observations(source.get("uncertain_observations"))
    supporting = _observations(source.get("supporting_observations"))
    raw_observations = _observations(source.get("observations"))

    if raw_observations and not accepted:
        accepted = raw_observations

    for item in [*accepted, *supporting, *uncertain]:
        field = str(item.get("field") or "").strip()
        if field and field not in fact_patch and item.get("value") not in {None, ""}:
            fact_patch[field] = item.get("value")

    contract = {
        "fact_patch": fact_patch,
        "accepted_observations": accepted,
        "uncertain_observations": uncertain,
        "supporting_observations": supporting,
    }
    frame_analysis = source.get("frame_analysis") if isinstance(source.get("frame_analysis"), dict) else {}
    metadata = source.get("video_metadata") if isinstance(source.get("video_metadata"), dict) else {}
    summary = build_video_scene_summary(contract, frame_analysis=frame_analysis, metadata=metadata)
    observations = [*accepted, *uncertain, *supporting]

    return {
        "mode": str(source.get("mode") or "video_only_mlkit_demo"),
        "status": "ok",
        "summary": summary.get("summary_text") or summary.get("title") or "",
        "observations": observations,
        "facts": fact_patch,
        "analysis_readiness": {
            "ready": bool(summary.get("available")),
            "needs_user_confirmation_count": len(summary.get("needs_user_confirmation") or []),
        },
        "observation_summary": summary,
        "video_observation_summary": summary,
        "candidate_accident_context": {
            "title": summary.get("title"),
            "summary_text": summary.get("summary_text"),
            "confirmed_visual_facts": summary.get("confirmed_visual_facts") or [],
            "needs_user_confirmation": summary.get("needs_user_confirmation") or [],
        },
        "fault_ratio_result": {},
        "forbidden_field_paths": [],
    }


def build_video_scene_summary(
    video_contract: dict[str, Any] | None,
    frame_analysis: dict[str, Any] | None = None,
    yolo_analysis: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a user-facing scene summary from visual observations only.

    The summary intentionally separates visually supported facts from items that
    still need user confirmation. It must not expose raw paths, prompts, storage
    keys, or model internals to the ordinary report surface.
    """

    contract = video_contract if isinstance(video_contract, dict) else {}
    frame = frame_analysis if isinstance(frame_analysis, dict) else {}
    meta = metadata if isinstance(metadata, dict) else {}

    accepted = _observations(contract.get("accepted_observations"))
    uncertain = _observations(contract.get("uncertain_observations"))
    supporting = _observations(contract.get("supporting_observations"))
    fact_patch = contract.get("fact_patch") if isinstance(contract.get("fact_patch"), dict) else {}

    if not (accepted or uncertain or supporting or fact_patch):
        reason = str(frame.get("reason") or meta.get("reason") or "").strip()
        return {
            "available": False,
            "status": "visual_analysis_unavailable",
            "title": "영상에서 확인된 사고 개요",
            "summary_text": "",
            "confirmed_visual_facts": [],
            "likely_visual_context": [],
            "needs_user_confirmation": _default_confirmation_questions(fact_patch, uncertain),
            "diagnostic_reason": reason,
        }

    facts = _best_values(fact_patch, accepted, uncertain)
    confirmed = _fact_items(facts, accepted, minimum=CONFIRMED_MIN_CONFIDENCE, fields=SUMMARY_FIELDS)
    likely = _fact_items(facts, [*accepted, *uncertain, *supporting], minimum=LIKELY_MIN_CONFIDENCE, fields=SUMMARY_FIELDS)
    summary_text = _compose_scene_sentence(facts, confirmed, likely)

    return {
        "available": bool(summary_text or confirmed or likely),
        "status": "visual_summary_ready" if summary_text else "visual_summary_partial",
        "title": "영상에서 확인된 사고 개요",
        "summary_text": summary_text,
        "confirmed_visual_facts": confirmed[:8],
        "likely_visual_context": [item for item in likely if item not in confirmed][:8],
        "needs_user_confirmation": _default_confirmation_questions(facts, uncertain),
        "source": "video_frame_observations",
    }


def _compose_scene_sentence(
    facts: dict[str, Any],
    confirmed: list[dict[str, Any]],
    likely: list[dict[str, Any]],
) -> str:
    ego = _value(facts, "ego_vehicle_type")
    direct = _value(facts, "direct_collision_partner_type") or _value(facts, "primary_collision_target")
    opposing = _value(facts, "opposing_direction_actor_type")
    school_zone = facts.get("school_zone") is True or facts.get("road_marking_school_zone_visible") is True
    speed_limit = _speed_limit_text(facts.get("speed_limit_kmh"))
    oncoming_bicycle = facts.get("oncoming_bicycle_present") is True or opposing == "bicycle"

    parts: list[str] = []
    if ego == "motorcycle":
        parts.append("오토바이 블랙박스 관점")
    elif ego:
        parts.append(f"{_label_value(ego)} 블랙박스 관점")
    else:
        parts.append("블랙박스 영상")

    road_context: list[str] = []
    if school_zone:
        road_context.append("어린이보호구역")
    if speed_limit:
        road_context.append(speed_limit)
    if road_context:
        parts.append(f"{'·'.join(road_context)} 도로에서")
    else:
        parts.append("주행 중")

    if oncoming_bicycle and direct == "bicycle":
        parts.append("맞은편 방향의 자전거가 진행 경로에 들어와 직접 충돌한 장면으로 보입니다.")
    elif direct == "bicycle":
        parts.append("자전거와 직접 충돌한 장면으로 보입니다.")
    elif direct:
        parts.append(f"{_label_value(direct)}와 접촉한 장면으로 보입니다.")
    elif oncoming_bicycle:
        parts.append("맞은편 방향의 자전거가 충돌 경로에 들어온 장면이 확인됩니다.")
    elif confirmed or likely:
        labels = [str(item.get("label") or "") for item in [*confirmed, *likely] if item.get("label")]
        parts.append(f"{', '.join(labels[:3])} 단서가 영상에서 확인됩니다.")
    else:
        return ""

    return " ".join(part for part in parts if part).strip()


def _default_confirmation_questions(facts: dict[str, Any], uncertain: list[dict[str, Any]]) -> list[dict[str, str]]:
    fields = {str(item.get("field") or "") for item in uncertain if isinstance(item, dict)}
    questions: list[dict[str, str]] = []

    if facts.get("child_candidate") is True or "child_candidate" in fields:
        questions.append({"field": "victim_is_child", "label": "피해자가 어린이였는지 확인"})
    if facts.get("speed_limit_kmh") or facts.get("school_zone") is True:
        questions.append({"field": "actual_speed_kmh", "label": "실제 주행속도 확인"})
    if facts.get("oncoming_bicycle_present") is True or facts.get("opposing_direction_actor_type") == "bicycle":
        questions.append({"field": "centerline_crossed", "label": "중앙선 침범 또는 진행 방향 확인"})
    if "opponent_signal_violation" in fields or not facts.get("opponent_signal_violation"):
        questions.append({"field": "opponent_signal_violation", "label": "상대방 신호위반 여부 확인"})
    if not facts.get("direct_collision_partner_type"):
        questions.append({"field": "direct_collision_partner_type", "label": "직접 충돌한 대상 확인"})

    if not questions:
        questions.append({"field": "scene_context", "label": "충돌 직전 위치와 진행 방향 확인"})
    return _dedupe_by_field(questions)[:5]


def _best_values(
    fact_patch: dict[str, Any],
    accepted: list[dict[str, Any]],
    uncertain: list[dict[str, Any]],
) -> dict[str, Any]:
    facts = dict(fact_patch)
    for item in [*accepted, *uncertain]:
        field = str(item.get("field") or "")
        if not field or field in facts:
            continue
        if _confidence(item) >= LIKELY_MIN_CONFIDENCE:
            facts[field] = item.get("value")
    return facts


def _fact_items(
    facts: dict[str, Any],
    observations: list[dict[str, Any]],
    *,
    minimum: float,
    fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for field in fields:
        value = facts.get(field)
        if value in {None, "", "unknown", False}:
            continue
        confidence = _best_confidence(field, observations)
        if confidence < minimum and field not in facts:
            continue
        out.append({
            "field": field,
            "label": FIELD_LABELS.get(field, field.replace("_", " ")),
            "value": _label_value(value),
            "confidence": round(confidence or minimum, 2),
        })
    return out


def _observations(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _best_confidence(field: str, observations: list[dict[str, Any]]) -> float:
    values = [_confidence(item) for item in observations if item.get("field") == field]
    return max(values) if values else CONFIRMED_MIN_CONFIDENCE


def _confidence(item: dict[str, Any]) -> float:
    try:
        return float(item.get("confidence") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _value(facts: dict[str, Any], field: str) -> str:
    return str(facts.get(field) or "").strip().lower()


def _label_value(value: Any) -> str:
    if isinstance(value, bool):
        return VALUE_LABELS[str(value).lower()]
    text = str(value).strip()
    normalized = text.lower()
    if normalized.endswith("_candidate"):
        normalized = normalized[: -len("_candidate")]
    return VALUE_LABELS.get(normalized, text)


def _speed_limit_text(value: Any) -> str:
    try:
        speed = int(float(str(value).replace("km/h", "").strip()))
    except (TypeError, ValueError):
        return ""
    if speed <= 0:
        return ""
    return f"{speed}km/h 제한구역"


def _dedupe_by_field(items: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        field = item.get("field") or item.get("label") or ""
        if not field or field in seen:
            continue
        seen.add(field)
        out.append(item)
    return out
