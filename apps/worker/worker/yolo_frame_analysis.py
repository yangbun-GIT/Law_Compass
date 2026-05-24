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
YOLO_FRAME_SELECTION_STRATEGY = "ffmpeg-representative-frames-object-inventory"
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

    for result_index, result in enumerate(results):
        frame_ref = _result_frame_ref(result, selected_frame_refs, result_index)
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
        },
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


def _result_frame_ref(result: Any, selected_frame_refs: list[str], result_index: int) -> str:
    if 0 <= result_index < len(selected_frame_refs):
        return selected_frame_refs[result_index]
    return Path(str(getattr(result, "path", ""))).name


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
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
