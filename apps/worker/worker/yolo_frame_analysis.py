import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


YOLO_FRAME_ANALYSIS_CONTRACT_VERSION = "yolo-frame-analysis-v1"
YOLO_FRAME_SELECTION_STRATEGY = "ffmpeg-event-frames-object-inventory"
ENABLE_YOLO_FRAME_ANALYSIS = os.getenv("ENABLE_YOLO_FRAME_ANALYSIS", "0") == "1"
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "").strip()
YOLO_DEVICE = os.getenv("YOLO_DEVICE", "cpu").strip() or "cpu"
YOLO_CONFIDENCE = max(0.01, min(0.95, _float_env("YOLO_CONFIDENCE", 0.25)))
YOLO_FRAME_ANALYSIS_MAX_FRAMES = max(1, min(60, _int_env("YOLO_FRAME_ANALYSIS_MAX_FRAMES", 18)))
YOLO_MAX_DETECTIONS = max(0, min(5000, _int_env("YOLO_MAX_DETECTIONS", 1000)))
YOLO_MAX_FRAME_REFS = max(1, min(60, _int_env("YOLO_MAX_FRAME_REFS", 24)))

VEHICLE_CLASSES = {"car", "truck", "bus"}
MOTORCYCLE_CLASSES = {"motorcycle"}
BICYCLE_CLASSES = {"bicycle"}
PEDESTRIAN_CLASSES = {"person"}
TRAFFIC_LIGHT_CLASSES = {"traffic light"}
TARGET_CLASS_GROUPS = {
    "vehicle": VEHICLE_CLASSES,
    "motorcycle": MOTORCYCLE_CLASSES,
    "bicycle": BICYCLE_CLASSES,
    "pedestrian": PEDESTRIAN_CLASSES,
}
MOBILE_TARGET_CLASSES = set().union(*TARGET_CLASS_GROUPS.values())
OVERLAY_NOISE_CLASSES = {"person"}


def analyze_frames_with_yolo(frame_details: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    selected_frames = _select_yolo_frames(frame_details, YOLO_FRAME_ANALYSIS_MAX_FRAMES)
    selection_metadata = _frame_selection_metadata(frame_details, selected_frames)
    if not ENABLE_YOLO_FRAME_ANALYSIS:
        return {
            "version": YOLO_FRAME_ANALYSIS_CONTRACT_VERSION,
            "enabled": False,
            "reason": "ENABLE_YOLO_FRAME_ANALYSIS is not 1",
            **selection_metadata,
        }
    if not selected_frames:
        return {
            "version": YOLO_FRAME_ANALYSIS_CONTRACT_VERSION,
            "enabled": False,
            "reason": "no frames extracted",
            **selection_metadata,
        }
    if not YOLO_MODEL_PATH:
        return {
            "version": YOLO_FRAME_ANALYSIS_CONTRACT_VERSION,
            "enabled": False,
            "reason": "YOLO_MODEL_PATH is empty",
            **selection_metadata,
        }
    try:
        from ultralytics import YOLO
    except ModuleNotFoundError as exc:
        return {
            "version": YOLO_FRAME_ANALYSIS_CONTRACT_VERSION,
            "enabled": True,
            "provider": "ultralytics-yolo",
            "model": YOLO_MODEL_PATH,
            "error": f"ultralytics is not installed: {exc}",
            **selection_metadata,
            "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
            "observations": [],
            "created_at": _now_iso(),
        }
    try:
        model = YOLO(YOLO_MODEL_PATH)
        results = model.predict(
            source=[frame["path"] for frame in selected_frames],
            device=YOLO_DEVICE,
            conf=YOLO_CONFIDENCE,
            stream=True,
            verbose=False,
        )
        payload = _build_yolo_payload(results, selected_frames, context, selection_metadata)
        print(json.dumps({
            "event": "yolo_frame_analysis",
            "model": payload.get("model"),
            "frames": payload.get("selected_frame_count"),
            "detections": (payload.get("summary") or {}).get("total_detections"),
            "observations": payload.get("observations") or [],
        }, ensure_ascii=False))
        return payload
    except Exception as exc:
        return {
            "version": YOLO_FRAME_ANALYSIS_CONTRACT_VERSION,
            "enabled": True,
            "provider": "ultralytics-yolo",
            "model": YOLO_MODEL_PATH,
            "device": YOLO_DEVICE,
            "error": str(exc),
            **selection_metadata,
            "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
            "observations": [],
            "created_at": _now_iso(),
        }


def _build_yolo_payload(
    results: Any,
    selected_frames: list[dict[str, Any]],
    context: dict[str, Any],
    selection_metadata: dict[str, Any],
) -> dict[str, Any]:
    raw_detections: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    class_frame_refs: dict[str, set[str]] = defaultdict(set)
    class_confidences: dict[str, list[float]] = defaultdict(list)
    selected_frame_refs = [Path(frame["path"]).name for frame in selected_frames]
    frame_meta_by_ref = {Path(frame["path"]).name: frame for frame in selected_frames}

    for result_index, result in enumerate(results):
        frame_ref = _result_frame_ref(result, selected_frame_refs, result_index)
        frame_meta = frame_meta_by_ref.get(frame_ref, {})
        names = result.names or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        for box in boxes:
            class_id = int(box.cls[0].item())
            label = str(names.get(class_id, class_id))
            confidence = float(box.conf[0].item())
            xyxy = [round(float(value), 2) for value in box.xyxy[0].tolist()]
            raw_detections.append({
                "frame_ref": frame_ref,
                "time_sec": frame_meta.get("time_sec"),
                "role": frame_meta.get("role"),
                "event_candidate_id": frame_meta.get("event_candidate_id"),
                "event_phase": frame_meta.get("event_phase"),
                "class_id": class_id,
                "label": label,
                "confidence": round(confidence, 4),
                "bbox_xyxy": xyxy,
                "frame_shape": _result_frame_shape(result),
            })

    detections, ignored_detections = _filter_overlay_noise(raw_detections)
    stored_detections = detections[:YOLO_MAX_DETECTIONS]
    stored_ignored_detections = ignored_detections[:YOLO_MAX_DETECTIONS]
    for detection in detections:
        label = str(detection.get("label") or "")
        frame_ref = str(detection.get("frame_ref") or "")
        confidence = float(detection.get("confidence") or 0.0)
        class_counts[label] += 1
        class_frame_refs[label].add(frame_ref)
        class_confidences[label].append(confidence)

    total_detection_count = sum(class_counts.values())
    object_observations = _observation_candidates(class_frame_refs, class_confidences, YOLO_MAX_FRAME_REFS)
    event_candidate_summary = _event_candidate_summaries(detections, selected_frames)
    temporal_sequence_summary = _temporal_sequence_summaries(detections, event_candidate_summary, selected_frames)
    sequence_observations = _sequence_observation_candidates(
        temporal_sequence_summary,
        YOLO_MAX_FRAME_REFS,
    )
    observations = [*object_observations, *sequence_observations]
    ignored_class_counts = Counter(str(item.get("label") or "") for item in ignored_detections)
    target_counts = _target_type_counts(class_counts)
    return {
        "version": YOLO_FRAME_ANALYSIS_CONTRACT_VERSION,
        "enabled": True,
        "provider": "ultralytics-yolo",
        "source": "vision_model:yolo",
        "model": YOLO_MODEL_PATH,
        "device": YOLO_DEVICE,
        "confidence_threshold": YOLO_CONFIDENCE,
        **selection_metadata,
        "analyzed_frames": [_public_frame_ref(frame) for frame in selected_frames],
        "summary": {
            "total_detections": total_detection_count,
            "raw_detection_count": len(raw_detections),
            "stored_detection_count": len(stored_detections),
            "detections_truncated": total_detection_count > len(stored_detections),
            "ignored_detection_count": len(ignored_detections),
            "ignored_class_counts": dict(ignored_class_counts),
            "class_counts": dict(class_counts),
            "target_type_counts": target_counts,
            "event_candidate_count": len(event_candidate_summary),
            "top_event_candidate_id": event_candidate_summary[0]["event_candidate_id"] if event_candidate_summary else "",
            "sequence_observation_count": len(sequence_observations),
        },
        "event_candidate_summary": event_candidate_summary,
        "temporal_sequence_summary": temporal_sequence_summary,
        "observations": observations,
        "detections": stored_detections,
        "ignored_detections": stored_ignored_detections,
        "notes": [
            "YOLO detections are object-location candidates only.",
            "Static edge overlays and broadcast UI detections are excluded from observations.",
            "Temporal sequence observations are confidence-limited candidates, not collision conclusions.",
            "Do not infer collision_partner_type or fault ratio from YOLO object presence alone.",
            "Use these observations only after Agent fact arbitration.",
        ],
        "context_refs": {
            "case_id": context.get("case_id"),
            "upload_id": context.get("upload_id"),
        },
        "created_at": _now_iso(),
    }


def _result_frame_shape(result: Any) -> list[int] | None:
    shape = getattr(result, "orig_shape", None)
    if isinstance(shape, (list, tuple)) and len(shape) >= 2:
        return [int(shape[0]), int(shape[1])]
    return None


def _filter_overlay_noise(detections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    overlay_candidates: list[tuple[int, dict[str, Any], dict[str, float]]] = []
    for index, detection in enumerate(detections):
        label = str(detection.get("label") or "")
        if label not in OVERLAY_NOISE_CLASSES:
            continue
        geometry = _normalized_bbox_geometry(detection)
        if not geometry or not _is_edge_overlay_candidate(geometry):
            continue
        overlay_candidates.append((index, detection, geometry))

    repeated_overlay_indexes = _repeated_overlay_indexes(overlay_candidates)
    filtered: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    for index, detection in enumerate(detections):
        if index not in repeated_overlay_indexes:
            filtered.append(detection)
            continue
        geometry = _normalized_bbox_geometry(detection) or {}
        ignored.append({
            **detection,
            "ignore_reason": "static_edge_overlay_or_broadcast_ui",
            "bbox_position": {
                "cx": round(float(geometry.get("cx", 0.0)), 4),
                "cy": round(float(geometry.get("cy", 0.0)), 4),
                "area_ratio": round(float(geometry.get("area_ratio", 0.0)), 4),
            },
        })
    return filtered, ignored


def _repeated_overlay_indexes(candidates: list[tuple[int, dict[str, Any], dict[str, float]]]) -> set[int]:
    grouped: dict[tuple[str, int, int], list[int]] = defaultdict(list)
    for index, detection, geometry in candidates:
        key = (
            str(detection.get("label") or ""),
            round(float(geometry["cx"]) / 0.06),
            round(float(geometry["cy"]) / 0.06),
        )
        grouped[key].append(index)
    repeated: set[int] = set()
    for indexes in grouped.values():
        if len(indexes) >= 3:
            repeated.update(indexes)
    return repeated


def _normalized_bbox_geometry(detection: dict[str, Any]) -> dict[str, float] | None:
    shape = detection.get("frame_shape")
    bbox = detection.get("bbox_xyxy")
    if not isinstance(shape, list) or len(shape) < 2:
        return None
    if not isinstance(bbox, list) or len(bbox) < 4:
        return None
    height = float(shape[0] or 0.0)
    width = float(shape[1] or 0.0)
    if width <= 0 or height <= 0:
        return None
    x1, y1, x2, y2 = [float(value or 0.0) for value in bbox[:4]]
    left = max(0.0, min(1.0, x1 / width))
    top = max(0.0, min(1.0, y1 / height))
    right = max(0.0, min(1.0, x2 / width))
    bottom = max(0.0, min(1.0, y2 / height))
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "cx": (left + right) / 2,
        "cy": (top + bottom) / 2,
        "area_ratio": max(0.0, right - left) * max(0.0, bottom - top),
    }


def _is_edge_overlay_candidate(geometry: dict[str, float]) -> bool:
    area_ratio = float(geometry.get("area_ratio") or 0.0)
    if area_ratio <= 0 or area_ratio > 0.12:
        return False
    near_edge = (
        geometry["left"] <= 0.18
        or geometry["right"] >= 0.82
        or geometry["top"] <= 0.18
        or geometry["bottom"] >= 0.88
    )
    near_corner_or_ui_band = (
        (geometry["top"] <= 0.22 and (geometry["left"] <= 0.30 or geometry["right"] >= 0.70))
        or (geometry["bottom"] >= 0.82 and area_ratio <= 0.06)
    )
    return near_edge and near_corner_or_ui_band


def rank_frame_details_by_yolo(frame_details: list[dict[str, Any]], yolo_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Annotate frame details with the strongest YOLO-backed accident-window candidate.

    This ranking is an input-selection hint only. It must not be treated as a
    collision fact, legal conclusion, or fault-ratio signal.
    """
    if not isinstance(yolo_payload, dict) or yolo_payload.get("enabled") is not True:
        return frame_details
    summaries = [
        item for item in yolo_payload.get("event_candidate_summary") or []
        if isinstance(item, dict) and item.get("event_candidate_id")
    ]
    if not summaries:
        return frame_details
    rank_by_id = {str(item["event_candidate_id"]): index + 1 for index, item in enumerate(summaries)}
    score_by_id = {str(item["event_candidate_id"]): item.get("score") for item in summaries}
    enriched: list[dict[str, Any]] = []
    for frame in frame_details:
        candidate_id = str(frame.get("event_candidate_id") or "")
        rank = rank_by_id.get(candidate_id)
        if not rank:
            enriched.append(frame)
            continue
        reason = str(frame.get("selection_reason") or "")
        if rank == 1 and "yolo_ranked_event_candidate" not in reason:
            reason = f"{reason}+yolo_ranked_event_candidate" if reason else "yolo_ranked_event_candidate"
        enriched.append({
            **frame,
            "vision_event_candidate_rank": rank,
            "vision_event_score": score_by_id.get(candidate_id),
            "selection_reason": reason,
            "vision_event_source": "vision_model:yolo",
        })
    return enriched


def _result_frame_ref(result: Any, selected_frame_refs: list[str], result_index: int) -> str:
    if 0 <= result_index < len(selected_frame_refs):
        return selected_frame_refs[result_index]
    return Path(str(getattr(result, "path", ""))).name


def _event_candidate_summaries(detections: list[dict[str, Any]], selected_frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frame_meta_by_ref = {Path(frame["path"]).name: frame for frame in selected_frames}
    grouped: dict[str, dict[str, Any]] = {}
    for detection in detections:
        frame_ref = str(detection.get("frame_ref") or "")
        frame_meta = frame_meta_by_ref.get(frame_ref, {})
        candidate_id = str(detection.get("event_candidate_id") or frame_meta.get("event_candidate_id") or "")
        if not candidate_id:
            continue
        label = str(detection.get("label") or "")
        confidence = float(detection.get("confidence") or 0.0)
        xyxy = detection.get("bbox_xyxy") if isinstance(detection.get("bbox_xyxy"), list) else []
        area = _bbox_area(xyxy)
        summary = grouped.setdefault(candidate_id, {
            "event_candidate_id": candidate_id,
            "frame_refs": set(),
            "vehicle_detection_count": 0,
            "mobile_target_detection_count": 0,
            "target_detection_counts": Counter(),
            "max_target_confidences": defaultdict(float),
            "max_target_bbox_areas": defaultdict(float),
            "person_detection_count": 0,
            "traffic_light_detection_count": 0,
            "max_vehicle_confidence": 0.0,
            "max_vehicle_bbox_area": 0.0,
            "event_phase_counts": Counter(),
        })
        summary["frame_refs"].add(frame_ref)
        summary["event_phase_counts"][str(detection.get("event_phase") or frame_meta.get("event_phase") or "unknown")] += 1
        target_type = _target_type_for_label(label)
        if target_type:
            summary["mobile_target_detection_count"] += 1
            summary["target_detection_counts"][target_type] += 1
            summary["max_target_confidences"][target_type] = max(
                float(summary["max_target_confidences"][target_type]),
                confidence,
            )
            summary["max_target_bbox_areas"][target_type] = max(
                float(summary["max_target_bbox_areas"][target_type]),
                area,
            )
        if label in VEHICLE_CLASSES:
            summary["vehicle_detection_count"] += 1
            summary["max_vehicle_confidence"] = max(float(summary["max_vehicle_confidence"]), confidence)
            summary["max_vehicle_bbox_area"] = max(float(summary["max_vehicle_bbox_area"]), area)
        elif label == "person":
            summary["person_detection_count"] += 1
        elif label == "traffic light":
            summary["traffic_light_detection_count"] += 1

    normalized: list[dict[str, Any]] = []
    for item in grouped.values():
        frame_refs = sorted(item["frame_refs"])
        event_phase_counts = dict(item["event_phase_counts"])
        target_detection_counts = dict(item["target_detection_counts"])
        dominant_target_type = _dominant_target_type(target_detection_counts)
        score = _candidate_score(
            vehicle_detection_count=int(item["vehicle_detection_count"]),
            mobile_target_detection_count=int(item["mobile_target_detection_count"]),
            visible_frame_count=len(frame_refs),
            max_target_confidence=max([0.0, *[float(value) for value in item["max_target_confidences"].values()]]),
            max_target_bbox_area=max([0.0, *[float(value) for value in item["max_target_bbox_areas"].values()]]),
            person_detection_count=int(item["person_detection_count"]),
            traffic_light_detection_count=int(item["traffic_light_detection_count"]),
            event_phase_counts=event_phase_counts,
        )
        normalized.append({
            "event_candidate_id": item["event_candidate_id"],
            "score": score,
            "frame_refs": frame_refs,
            "vehicle_detection_count": item["vehicle_detection_count"],
            "mobile_target_detection_count": item["mobile_target_detection_count"],
            "target_detection_counts": target_detection_counts,
            "dominant_target_type": dominant_target_type,
            "person_detection_count": item["person_detection_count"],
            "traffic_light_detection_count": item["traffic_light_detection_count"],
            "max_vehicle_confidence": round(float(item["max_vehicle_confidence"]), 4),
            "max_vehicle_bbox_area": round(float(item["max_vehicle_bbox_area"]), 2),
            "max_target_confidences": {key: round(float(value), 4) for key, value in item["max_target_confidences"].items()},
            "max_target_bbox_areas": {key: round(float(value), 2) for key, value in item["max_target_bbox_areas"].items()},
            "event_phase_counts": event_phase_counts,
            "interpretation": "YOLO-ranked accident-window candidate for frame selection only.",
        })
    return sorted(
        normalized,
        key=lambda item: (
            -float(item["score"]),
            -int(item["mobile_target_detection_count"]),
            str(item["event_candidate_id"]),
        ),
    )


def _temporal_sequence_summaries(
    detections: list[dict[str, Any]],
    event_candidate_summary: list[dict[str, Any]],
    selected_frames: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not event_candidate_summary:
        return []
    frame_meta_by_ref = {Path(frame["path"]).name: frame for frame in selected_frames}
    detections_by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for detection in detections:
        candidate_id = str(detection.get("event_candidate_id") or "")
        if not candidate_id:
            continue
        detections_by_candidate[candidate_id].append(detection)

    summaries: list[dict[str, Any]] = []
    ordered_candidate_ids = [str(item.get("event_candidate_id") or "") for item in event_candidate_summary]
    for rank, candidate_id in enumerate([item for item in ordered_candidate_ids if item], start=1):
        candidate_detections = detections_by_candidate.get(candidate_id) or []
        if not candidate_detections:
            continue
        phase_frame_refs: dict[str, set[str]] = defaultdict(set)
        vehicle_frame_refs: set[str] = set()
        target_frame_refs: dict[str, set[str]] = defaultdict(set)
        vehicle_phase_counts: Counter[str] = Counter()
        target_phase_counts: dict[str, Counter[str]] = defaultdict(Counter)
        target_detection_counts: Counter[str] = Counter()
        target_confidences: dict[str, list[float]] = defaultdict(list)
        largest_target_area: dict[str, float] = defaultdict(float)
        largest_target_frame_ref: dict[str, str] = {}
        class_counts: Counter[str] = Counter()
        largest_vehicle_area = 0.0
        largest_vehicle_frame_ref = ""
        for detection in candidate_detections:
            frame_ref = str(detection.get("frame_ref") or "")
            frame_meta = frame_meta_by_ref.get(frame_ref, {})
            phase = str(detection.get("event_phase") or frame_meta.get("event_phase") or "unknown")
            label = str(detection.get("label") or "")
            class_counts[label] += 1
            phase_frame_refs[phase].add(frame_ref)
            area = _bbox_area(detection.get("bbox_xyxy") if isinstance(detection.get("bbox_xyxy"), list) else [])
            target_type = _target_type_for_label(label)
            if target_type:
                confidence = float(detection.get("confidence") or 0.0)
                target_frame_refs[target_type].add(frame_ref)
                target_phase_counts[target_type][phase] += 1
                target_detection_counts[target_type] += 1
                target_confidences[target_type].append(confidence)
                if area > largest_target_area[target_type]:
                    largest_target_area[target_type] = area
                    largest_target_frame_ref[target_type] = frame_ref
            if label in VEHICLE_CLASSES:
                vehicle_frame_refs.add(frame_ref)
                vehicle_phase_counts[phase] += 1
                if area > largest_vehicle_area:
                    largest_vehicle_area = area
                    largest_vehicle_frame_ref = frame_ref

        if not target_frame_refs:
            continue
        dominant_target_type = _dominant_sequence_target_type(target_detection_counts, target_phase_counts, largest_target_area)
        dominant_frame_refs = target_frame_refs.get(dominant_target_type, set()) if dominant_target_type else set()
        dominant_phase_counts = target_phase_counts.get(dominant_target_type, Counter())
        event_target_count = int(dominant_phase_counts.get("event_candidate") or 0)
        sequence_quality = _sequence_quality(phase_frame_refs, event_target_count)
        summaries.append({
            "event_candidate_id": candidate_id,
            "rank": rank,
            "sequence_quality": sequence_quality,
            "frame_refs": _limited_frame_refs(dominant_frame_refs, YOLO_MAX_FRAME_REFS),
            "phase_frame_refs": {
                phase: sorted(refs)
                for phase, refs in sorted(phase_frame_refs.items())
                if refs
            },
            "class_counts": dict(class_counts),
            "target_detection_counts": dict(target_detection_counts),
            "target_frame_counts": {key: len(value) for key, value in target_frame_refs.items()},
            "target_phase_counts": {key: dict(value) for key, value in target_phase_counts.items()},
            "target_max_confidences": {key: round(max(value), 4) for key, value in target_confidences.items() if value},
            "dominant_target_type": dominant_target_type,
            "dominant_target_frame_count": len(dominant_frame_refs),
            "event_target_detection_count": event_target_count,
            "largest_target_bbox_area": round(float(largest_target_area.get(dominant_target_type or "", 0.0)), 2),
            "largest_target_frame_ref": largest_target_frame_ref.get(dominant_target_type or "", ""),
            "vehicle_frame_count": len(vehicle_frame_refs),
            "vehicle_phase_counts": dict(vehicle_phase_counts),
            "event_vehicle_detection_count": int(vehicle_phase_counts.get("event_candidate") or 0),
            "largest_vehicle_bbox_area": round(largest_vehicle_area, 2),
            "largest_vehicle_frame_ref": largest_vehicle_frame_ref,
            "interpretation": (
                "Chronological object-presence sequence for accident-window review only. "
                "It should support frame selection and user confirmation, not decide fault."
            ),
        })
    return summaries


def _sequence_quality(phase_frame_refs: dict[str, set[str]], event_vehicle_count: int) -> str:
    has_pre = bool(phase_frame_refs.get("pre_event_context"))
    has_event = bool(phase_frame_refs.get("event_candidate")) and event_vehicle_count > 0
    has_post = bool(phase_frame_refs.get("post_event_context"))
    if has_pre and has_event and has_post:
        return "pre_event_event_post_sequence"
    if has_event and (has_pre or has_post):
        return "partial_event_sequence"
    if has_event:
        return "event_only_sequence"
    return "object_presence_sequence"


def _sequence_observation_candidates(
    temporal_sequence_summary: list[dict[str, Any]],
    max_frame_refs: int,
) -> list[dict[str, Any]]:
    if not temporal_sequence_summary:
        return []
    top = temporal_sequence_summary[0]
    frame_refs = _limited_frame_refs(set(top.get("frame_refs") or []), max_frame_refs)
    if not frame_refs:
        return []
    dominant_target_type = str(top.get("dominant_target_type") or "unknown")
    event_target_count = int(top.get("event_target_detection_count") or top.get("event_vehicle_detection_count") or 0)
    target_frame_count = int(top.get("dominant_target_frame_count") or top.get("vehicle_frame_count") or 0)
    largest_target_bbox_area = float(top.get("largest_target_bbox_area") or top.get("largest_vehicle_bbox_area") or 0.0)
    sequence_quality = str(top.get("sequence_quality") or "")
    observations: list[dict[str, Any]] = [
        {
            "field": "accident_event_candidate",
            "value": True,
            "confidence": _bounded_sequence_confidence(0.8, target_frame_count, event_target_count, 0.87),
            "source": "vision_model:yolo_sequence",
            "frame_refs": frame_refs,
            "reason": (
                f"YOLO observed {dominant_target_type} objects through the top-ranked event window. "
                "This marks a candidate accident sequence for review, not a final collision finding."
            ),
        }
    ]
    if (
        dominant_target_type in TARGET_CLASS_GROUPS
        and dominant_target_type != "vehicle"
        and event_target_count >= 1
        and target_frame_count >= 2
    ):
        observations.append({
            "field": "primary_collision_target",
            "value": f"{dominant_target_type}_candidate",
            "confidence": _direct_target_sequence_confidence(sequence_quality, target_frame_count, event_target_count, cap=0.78),
            "source": "vision_model:yolo_sequence",
            "frame_refs": frame_refs,
            "reason": (
                f"The dominant moving target in the event window is {dominant_target_type}. "
                "YOLO cannot verify physical contact by itself, so this remains a target candidate."
            ),
        })
    elif dominant_target_type == "vehicle" and event_target_count >= 1 and target_frame_count >= 2:
        observations.append({
            "field": "primary_collision_target",
            "value": "vehicle_candidate",
            "confidence": _bounded_sequence_confidence(0.66, target_frame_count, event_target_count, 0.74),
            "source": "vision_model:yolo_sequence",
            "frame_refs": frame_refs,
            "reason": (
                "YOLO observed vehicles in the candidate event window, but vehicle presence alone "
                "can include ego/nearby traffic. Treat this as an object inventory candidate until "
                "OpenAI or user facts identify the actual collision partner."
            ),
        })
    if event_target_count >= 2 or (event_target_count >= 1 and largest_target_bbox_area >= 80000):
        observations.append({
            "field": "collision_point_visible",
            "value": True,
            "confidence": _bounded_sequence_confidence(0.74, target_frame_count, event_target_count, 0.83),
            "source": "vision_model:yolo_sequence",
            "frame_refs": frame_refs,
            "reason": (
                f"{dominant_target_type} detections concentrate in the candidate event window ({sequence_quality}). "
                "This is a collision-point confirmation candidate, not a verified impact."
            ),
        })
    return observations


def _bounded_sequence_confidence(base: float, target_frame_count: int, event_target_count: int, cap: float) -> float:
    value = base + min(target_frame_count, 6) * 0.015 + min(event_target_count, 4) * 0.015
    return round(min(value, cap), 4)


def _direct_target_sequence_confidence(
    sequence_quality: str,
    target_frame_count: int,
    event_target_count: int,
    cap: float = 0.85,
) -> float:
    base = 0.78 if sequence_quality == "pre_event_event_post_sequence" else 0.74
    if sequence_quality == "partial_event_sequence":
        base = 0.76
    return _bounded_sequence_confidence(base, target_frame_count, event_target_count, cap)


def _candidate_score(
    *,
    vehicle_detection_count: int,
    mobile_target_detection_count: int,
    visible_frame_count: int,
    max_target_confidence: float,
    max_target_bbox_area: float,
    person_detection_count: int,
    traffic_light_detection_count: int,
    event_phase_counts: dict[str, int],
) -> float:
    event_phase_boost = 1.0 if event_phase_counts.get("event_candidate") else 0.0
    score = (
        mobile_target_detection_count * 3.0
        + vehicle_detection_count * 0.5
        + visible_frame_count * 1.5
        + max_target_confidence * 2.0
        + min(max_target_bbox_area / 20000.0, 2.0)
        + traffic_light_detection_count * 0.35
        + person_detection_count * 0.15
        + event_phase_boost
    )
    return round(score, 4)


def _bbox_area(xyxy: list[Any]) -> float:
    if len(xyxy) != 4:
        return 0.0
    x1, y1, x2, y2 = [float(value or 0.0) for value in xyxy]
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _observation_candidates(
    class_frame_refs: dict[str, set[str]],
    class_confidences: dict[str, list[float]],
    max_frame_refs: int,
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    if "person" in class_frame_refs:
        observations.append(_presence_observation("pedestrian_visible", True, "person", class_frame_refs, class_confidences, max_frame_refs))
    if "traffic light" in class_frame_refs:
        observations.append(_presence_observation("opponent_signal_visible", True, "traffic light", class_frame_refs, class_confidences, max_frame_refs))
    for target_type, labels in TARGET_CLASS_GROUPS.items():
        if not any(label in class_frame_refs for label in labels):
            continue
        frame_refs = _limited_frame_refs({ref for label in labels for ref in class_frame_refs.get(label, set())}, max_frame_refs)
        confidences = [conf for label in labels for conf in class_confidences.get(label, [])]
        observations.append({
            "field": "primary_collision_target",
            "value": f"{target_type}_candidate",
            "confidence": round(min(max(confidences or [0.0]), 0.72), 4),
            "source": "vision_model:yolo",
            "frame_refs": frame_refs,
            "reason": f"YOLO detected {target_type} objects. This is an object inventory candidate, not proof of collision target.",
        })
    return observations


def _presence_observation(
    field: str,
    value: bool,
    label: str,
    class_frame_refs: dict[str, set[str]],
    class_confidences: dict[str, list[float]],
    max_frame_refs: int,
) -> dict[str, Any]:
    confidences = class_confidences.get(label) or [0.0]
    return {
        "field": field,
        "value": value,
        "confidence": round(min(max(confidences), 0.74), 4),
        "source": "vision_model:yolo",
        "frame_refs": _limited_frame_refs(class_frame_refs.get(label, set()), max_frame_refs),
        "reason": f"YOLO detected {label}. This indicates visible object presence only.",
    }


def _select_yolo_frames(frame_details: list[dict[str, Any]], max_frames: int) -> list[dict[str, Any]]:
    frames = [frame for frame in frame_details if frame.get("path") and Path(frame["path"]).exists()]
    if len(frames) <= max_frames:
        return frames
    event_frames = [frame for frame in frames if frame.get("role") in {"accident_candidate", "event_context"}]
    if event_frames:
        return _spread_frames([frames[0], *event_frames, frames[-1]], max_frames)
    return _spread_frames(frames, max_frames)


def _spread_frames(frames: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for frame in frames:
        key = str(frame.get("path"))
        if key not in seen:
            unique.append(frame)
            seen.add(key)
    if count >= len(unique):
        return unique
    if count <= 1:
        return [unique[len(unique) // 2]]
    selected: list[dict[str, Any]] = []
    for step in range(count):
        index = round(step * (len(unique) - 1) / (count - 1))
        frame = unique[index]
        if frame not in selected:
            selected.append(frame)
    return selected


def _frame_selection_metadata(frame_details: list[dict[str, Any]], selected_frames: list[dict[str, Any]]) -> dict[str, Any]:
    available_frame_count = len([frame for frame in frame_details if frame.get("path") and Path(frame["path"]).exists()])
    return {
        "frame_selection_strategy": YOLO_FRAME_SELECTION_STRATEGY,
        "available_frame_count": available_frame_count,
        "selected_frame_count": len(selected_frames),
        "frame_selection_max_frames": YOLO_FRAME_ANALYSIS_MAX_FRAMES,
    }


def _limited_frame_refs(frame_refs: set[str], limit: int) -> list[str]:
    refs = sorted(frame_refs)
    if len(refs) <= limit:
        return refs
    head_count = max(1, limit // 3)
    tail_count = max(1, limit // 3)
    middle_count = max(0, limit - head_count - tail_count)
    middle: list[str] = []
    if middle_count:
        step = max(1, len(refs) // (middle_count + 1))
        middle = [refs[min(len(refs) - 1, step * (index + 1))] for index in range(middle_count)]
    return list(dict.fromkeys([*refs[:head_count], *middle, *refs[-tail_count:]]))


def _public_frame_ref(frame: dict[str, Any]) -> dict[str, Any]:
    return {
        "frame_ref": Path(str(frame.get("path", ""))).name,
        "time_sec": frame.get("time_sec"),
        "role": frame.get("role"),
        "event_candidate_id": frame.get("event_candidate_id"),
        "event_phase": frame.get("event_phase"),
    }


def _target_type_for_label(label: str) -> str | None:
    normalized = str(label or "").strip().lower()
    for target_type, labels in TARGET_CLASS_GROUPS.items():
        if normalized in labels:
            return target_type
    return None


def _target_type_counts(class_counts: Counter[str]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for label, count in class_counts.items():
        target_type = _target_type_for_label(label)
        if target_type:
            counts[target_type] += int(count)
    return dict(counts)


def _dominant_target_type(counts: dict[str, int]) -> str:
    if not counts:
        return ""
    priority = {"pedestrian": 0, "bicycle": 1, "motorcycle": 2, "vehicle": 3}
    return sorted(
        counts,
        key=lambda key: (-int(counts.get(key) or 0), priority.get(key, 99), key),
    )[0]


def _dominant_sequence_target_type(
    target_detection_counts: Counter[str],
    target_phase_counts: dict[str, Counter[str]],
    largest_target_area: dict[str, float],
) -> str:
    if not target_detection_counts:
        return ""
    priority = {"pedestrian": 0, "bicycle": 1, "motorcycle": 2, "vehicle": 3}
    return sorted(
        target_detection_counts,
        key=lambda key: (
            -int((target_phase_counts.get(key) or Counter()).get("event_candidate") or 0),
            -int(target_detection_counts.get(key) or 0),
            -float(largest_target_area.get(key) or 0.0),
            priority.get(key, 99),
            key,
        ),
    )[0]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
