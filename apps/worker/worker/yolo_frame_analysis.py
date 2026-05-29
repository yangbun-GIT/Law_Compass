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

VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle"}


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
    detections: list[dict[str, Any]] = []
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
            if len(detections) < YOLO_MAX_DETECTIONS:
                detections.append({
                    "frame_ref": frame_ref,
                    "time_sec": frame_meta.get("time_sec"),
                    "role": frame_meta.get("role"),
                    "event_candidate_id": frame_meta.get("event_candidate_id"),
                    "event_phase": frame_meta.get("event_phase"),
                    "class_id": class_id,
                    "label": label,
                    "confidence": round(confidence, 4),
                    "bbox_xyxy": xyxy,
                })
            class_counts[label] += 1
            class_frame_refs[label].add(frame_ref)
            class_confidences[label].append(confidence)

    total_detection_count = sum(class_counts.values())
    observations = _observation_candidates(class_frame_refs, class_confidences, YOLO_MAX_FRAME_REFS)
    event_candidate_summary = _event_candidate_summaries(detections, selected_frames)
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
            "stored_detection_count": len(detections),
            "detections_truncated": total_detection_count > len(detections),
            "class_counts": dict(class_counts),
            "event_candidate_count": len(event_candidate_summary),
            "top_event_candidate_id": event_candidate_summary[0]["event_candidate_id"] if event_candidate_summary else "",
        },
        "event_candidate_summary": event_candidate_summary,
        "observations": observations,
        "detections": detections,
        "notes": [
            "YOLO detections are object-location candidates only.",
            "Do not infer collision_partner_type or fault ratio from YOLO object presence alone.",
            "Use these observations only after Agent fact arbitration.",
        ],
        "context_refs": {
            "case_id": context.get("case_id"),
            "upload_id": context.get("upload_id"),
        },
        "created_at": _now_iso(),
    }


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
            "person_detection_count": 0,
            "traffic_light_detection_count": 0,
            "max_vehicle_confidence": 0.0,
            "max_vehicle_bbox_area": 0.0,
            "event_phase_counts": Counter(),
        })
        summary["frame_refs"].add(frame_ref)
        summary["event_phase_counts"][str(detection.get("event_phase") or frame_meta.get("event_phase") or "unknown")] += 1
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
        score = _candidate_score(
            vehicle_detection_count=int(item["vehicle_detection_count"]),
            visible_frame_count=len(frame_refs),
            max_vehicle_confidence=float(item["max_vehicle_confidence"]),
            max_vehicle_bbox_area=float(item["max_vehicle_bbox_area"]),
            person_detection_count=int(item["person_detection_count"]),
            traffic_light_detection_count=int(item["traffic_light_detection_count"]),
            event_phase_counts=event_phase_counts,
        )
        normalized.append({
            "event_candidate_id": item["event_candidate_id"],
            "score": score,
            "frame_refs": frame_refs,
            "vehicle_detection_count": item["vehicle_detection_count"],
            "person_detection_count": item["person_detection_count"],
            "traffic_light_detection_count": item["traffic_light_detection_count"],
            "max_vehicle_confidence": round(float(item["max_vehicle_confidence"]), 4),
            "max_vehicle_bbox_area": round(float(item["max_vehicle_bbox_area"]), 2),
            "event_phase_counts": event_phase_counts,
            "interpretation": "YOLO-ranked accident-window candidate for frame selection only.",
        })
    return sorted(
        normalized,
        key=lambda item: (
            -float(item["score"]),
            -int(item["vehicle_detection_count"]),
            str(item["event_candidate_id"]),
        ),
    )


def _candidate_score(
    *,
    vehicle_detection_count: int,
    visible_frame_count: int,
    max_vehicle_confidence: float,
    max_vehicle_bbox_area: float,
    person_detection_count: int,
    traffic_light_detection_count: int,
    event_phase_counts: dict[str, int],
) -> float:
    event_phase_boost = 1.0 if event_phase_counts.get("event_candidate") else 0.0
    score = (
        vehicle_detection_count * 3.0
        + visible_frame_count * 1.5
        + max_vehicle_confidence * 2.0
        + min(max_vehicle_bbox_area / 20000.0, 2.0)
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
    if any(label in class_frame_refs for label in VEHICLE_CLASSES):
        frame_refs = _limited_frame_refs({ref for label in VEHICLE_CLASSES for ref in class_frame_refs.get(label, set())}, max_frame_refs)
        confidences = [conf for label in VEHICLE_CLASSES for conf in class_confidences.get(label, [])]
        observations.append({
            "field": "primary_collision_target",
            "value": "vehicle_candidate",
            "confidence": round(min(max(confidences or [0.0]), 0.72), 4),
            "source": "vision_model:yolo",
            "frame_refs": frame_refs,
            "reason": "YOLO detected vehicle-class objects. This is an object inventory candidate, not proof of collision target.",
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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
