from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

JUDGMENT_FIELDS = {
    "fault_ratio",
    "accident_party_type",
    "collision_partner_type",
    "signal_violation",
    "knia_chart_no",
    "legal_judgment",
}


def summarize_client_pre_observations(payload: dict[str, Any] | None) -> dict[str, Any]:
    source = payload if isinstance(payload, dict) else {}
    observations = source.get("observations") if isinstance(source.get("observations"), list) else []
    object_observations = [item for item in observations if isinstance(item, dict) and item.get("field") == "object_candidate"]

    counts: Counter[str] = Counter()
    tracks: dict[str, list[dict[str, Any]]] = defaultdict(list)
    forbidden = _find_forbidden_fields(source)

    for item in object_observations:
        label = _canonical_label(item)
        counts[label] += 1
        track_id = item.get("track_id")
        if track_id is not None and str(track_id).strip():
            tracks[str(track_id)].append(item)

    track_summary = [_summarize_track(track_id, rows) for track_id, rows in tracks.items()]
    moving_tracks = sum(1 for item in track_summary if item["movement_score"] >= 0.08)
    stationary_tracks = sum(1 for item in track_summary if item["stationary_likelihood"] >= 0.7)
    possible_context = {
        "possible_car_vs_car": counts["vehicle"] >= 2 or (counts["vehicle"] >= 1 and len(track_summary) >= 2),
        "possible_car_vs_person": counts["person"] > 0,
        "possible_car_vs_bicycle": counts["bicycle"] > 0,
        "possible_car_vs_motorcycle": counts["motorcycle"] > 0,
        "possible_signal_related": counts["traffic_light"] > 0,
    }

    candidate = _candidate_context(counts, track_summary, possible_context)
    status = _readiness_status(counts, track_summary, candidate)

    return {
        "mode": "video_only_mlkit_demo",
        "status": "ok",
        "analysis_readiness": {
            "can_infer_accident_context": candidate["confidence"] > 0,
            "can_estimate_fault_ratio": False,
            "status": status,
            "reason": _readiness_reason(status, candidate),
        },
        "observation_summary": {
            "vehicles_detected": counts["vehicle"],
            "persons_detected": counts["person"],
            "bicycles_detected": counts["bicycle"],
            "motorcycles_detected": counts["motorcycle"],
            "traffic_lights_detected": counts["traffic_light"],
            "unknown_objects_detected": counts["unknown_object"],
            "moving_tracks": moving_tracks,
            "stationary_tracks": stationary_tracks,
        },
        "video_observation_summary": {
            "detected_objects": {
                "vehicle": counts["vehicle"],
                "person": counts["person"],
                "bicycle": counts["bicycle"],
                "motorcycle": counts["motorcycle"],
                "traffic_light": counts["traffic_light"],
                "unknown_object": counts["unknown_object"],
            },
            "track_summary": track_summary,
            "possible_context": possible_context,
            "limitations": [
                "ML Kit 객체 후보만으로 신호위반을 확정할 수 없습니다.",
                "영상만으로 내 차량과 상대 차량 역할을 확정할 수 없습니다.",
                "객체 후보는 Agent fact arbitration을 거치기 전의 참고 관찰값입니다.",
            ],
        },
        "candidate_accident_context": candidate,
        "fault_ratio_result": {
            "judgment_status": "needs_review",
            "presentation_status": "reference_only",
            "reason": "영상 관찰값만으로 KNIA chart와 과실비율을 확정할 수 없습니다.",
        },
        "forbidden_field_paths": forbidden,
    }


def _canonical_label(item: dict[str, Any]) -> str:
    raw = " ".join(
        str(value or "").lower()
        for value in (
            item.get("value"),
            _dict(item.get("metadata")).get("label"),
            _dict(item.get("metadata")).get("raw_category"),
        )
    )
    if any(token in raw for token in ("traffic_light", "traffic light", "signal", "신호등")):
        return "traffic_light"
    if any(token in raw for token in ("motorcycle", "motorbike", "scooter", "moped", "two_wheeler", "two-wheeler", "오토바이", "이륜차", "원동기")):
        return "motorcycle"
    if any(token in raw for token in ("bicycle", "bike", "cyclist", "자전거")):
        return "bicycle"
    if any(token in raw for token in ("person", "pedestrian", "사람", "보행자")):
        return "person"
    if any(token in raw for token in ("car", "vehicle", "truck", "bus", "자동차", "차량", "트럭")):
        return "vehicle"
    return "unknown_object"


def _summarize_track(track_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda item: _num(item.get("frame_time_sec")))
    centers = [_center(item.get("bbox")) for item in ordered]
    distances = [
        math.dist(centers[index - 1], centers[index])
        for index in range(1, len(centers))
        if centers[index - 1] is not None and centers[index] is not None
    ]
    movement_score = min(1.0, sum(distances))
    label = _canonical_label(ordered[0]) if ordered else "unknown_object"
    return {
        "track_id": track_id,
        "label": label,
        "first_seen_sec": _num(ordered[0].get("frame_time_sec")) if ordered else 0,
        "last_seen_sec": _num(ordered[-1].get("frame_time_sec")) if ordered else 0,
        "movement_score": round(movement_score, 4),
        "stationary_likelihood": round(max(0.0, 1.0 - movement_score * 4), 4),
        "observation_count": len(ordered),
    }


def _candidate_context(counts: Counter[str], tracks: list[dict[str, Any]], possible_context: dict[str, bool]) -> dict[str, Any]:
    evidence: list[str] = []
    missing = [
        "충돌 시점",
        "내 차량과 상대 차량 구분",
        "신호 상태",
        "차로 관계",
        "도로 형태",
    ]
    possible_party_type: str | None = None
    confidence = 0.0

    if possible_context["possible_car_vs_car"]:
        possible_party_type = "car_vs_car"
        confidence = min(0.65, 0.28 + counts["vehicle"] * 0.08 + len(tracks) * 0.04)
        evidence.append(f"차량 객체 후보 {counts['vehicle']}개가 감지되었습니다.")
        if tracks:
            evidence.append(f"추적 가능한 객체 후보 {len(tracks)}개가 여러 프레임에서 관찰되었습니다.")
    elif possible_context["possible_car_vs_person"]:
        possible_party_type = "car_vs_person"
        confidence = min(0.58, 0.24 + counts["person"] * 0.08)
        evidence.append(f"사람 객체 후보 {counts['person']}개가 감지되었습니다.")
    elif possible_context["possible_car_vs_motorcycle"]:
        possible_party_type = "car_vs_motorcycle"
        confidence = min(0.58, 0.24 + counts["motorcycle"] * 0.08)
        evidence.append(f"오토바이/이륜차 객체 후보 {counts['motorcycle']}개가 감지되었습니다.")
    elif possible_context["possible_car_vs_bicycle"]:
        possible_party_type = "car_vs_bicycle"
        confidence = min(0.56, 0.24 + counts["bicycle"] * 0.08)
        evidence.append(f"자전거 객체 후보 {counts['bicycle']}개가 감지되었습니다.")
    elif counts["traffic_light"]:
        confidence = 0.18
        evidence.append("신호등 객체 후보가 감지되었지만 충돌 대상은 확인되지 않았습니다.")
    elif counts["unknown_object"]:
        confidence = 0.12
        evidence.append("알 수 없는 객체 후보가 감지되었습니다.")

    if possible_context["possible_signal_related"]:
        evidence.append("신호등 후보가 있어 신호 관련 여부를 추가 확인할 수 있습니다.")
        missing.append("각 차량의 진입 신호와 신호 변경 시점")

    if not evidence:
        missing.insert(0, "충분한 객체 후보")

    return {
        "possible_party_type": possible_party_type,
        "confidence": round(confidence, 4),
        "evidence": evidence,
        "missing_facts": missing,
        "collision_frame_candidates": [],
        "questions_to_ask": [
            "충돌 순간이 영상에 명확히 보이나요?",
            "내 차량과 상대 차량은 각각 어느 쪽인가요?",
            "신호등이나 차선, 횡단보도가 영상에 보이나요?",
        ],
        "knia_chart_determinable": False,
        "reference_only": True,
    }


def _readiness_status(counts: Counter[str], tracks: list[dict[str, Any]], candidate: dict[str, Any]) -> str:
    if candidate.get("confidence", 0) <= 0:
        return "insufficient_video_only"
    if counts["vehicle"] or counts["person"] or counts["bicycle"] or counts["motorcycle"]:
        return "sufficient_for_knia_major_candidate"
    if tracks:
        return "sufficient_for_context_candidate"
    return "insufficient_video_only"


def _readiness_reason(status: str, candidate: dict[str, Any]) -> str:
    if status == "insufficient_video_only":
        return "객체 후보가 부족하여 영상만으로 사고상황 후보를 만들기 어렵습니다."
    if status == "sufficient_for_knia_major_candidate":
        return "객체 후보로 KNIA 대분류 후보는 볼 수 있지만, chart_no와 과실비율 산정에는 충돌 시점과 역할 정보가 부족합니다."
    return "일부 객체 흐름은 보이지만 KNIA 기준과 과실비율 산정에는 추가 정보가 필요합니다."


def _center(raw_bbox: Any) -> tuple[float, float]:
    if not isinstance(raw_bbox, list | tuple) or len(raw_bbox) < 4:
        return (0.0, 0.0)
    left, top, right, bottom = [_num(value) for value in raw_bbox[:4]]
    return ((left + right) / 2, (top + bottom) / 2)


def _num(value: Any) -> float:
    try:
        parsed = float(value)
    except Exception:
        return 0.0
    if not math.isfinite(parsed):
        return 0.0
    return parsed


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _find_forbidden_fields(value: Any, path: str = "$") -> list[str]:
    if isinstance(value, list):
        found: list[str] = []
        for index, item in enumerate(value):
            found.extend(_find_forbidden_fields(item, f"{path}[{index}]"))
        return found
    if not isinstance(value, dict):
        return []
    found = []
    for key, nested in value.items():
        next_path = f"{path}.{key}"
        if key in JUDGMENT_FIELDS:
            found.append(next_path)
        found.extend(_find_forbidden_fields(nested, next_path))
    return found
