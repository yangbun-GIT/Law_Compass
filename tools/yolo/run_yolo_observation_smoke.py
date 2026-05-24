from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ultralytics import YOLO


VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a local YOLO smoke test and emit LawCompass-compatible video observation candidates.",
    )
    parser.add_argument("--source", required=True, help="Image, video, or directory path to analyze.")
    parser.add_argument("--model", required=True, help="YOLO model path, for example C:/.../yolo11n.pt.")
    parser.add_argument("--output-json", required=True, help="Output JSON path for normalized observation candidates.")
    parser.add_argument("--device", default="0", help="YOLO device. Use 0 for first GPU or cpu.")
    parser.add_argument("--conf", type=float, default=0.25, help="YOLO confidence threshold.")
    parser.add_argument("--project", default="C:/Users/yangbun/Documents/OSS/yolo-runs", help="YOLO run output directory.")
    parser.add_argument("--name", default="lawcompass-smoke", help="YOLO run name.")
    parser.add_argument("--save", action="store_true", help="Save annotated prediction images/videos.")
    parser.add_argument("--max-frame-refs", type=int, default=24, help="Maximum frame refs to keep per observation.")
    parser.add_argument("--max-detections", type=int, default=1000, help="Maximum raw detections to keep in output JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model = YOLO(args.model)
    results = model.predict(
        source=args.source,
        device=args.device,
        conf=args.conf,
        project=args.project,
        name=args.name,
        exist_ok=True,
        save=args.save,
        stream=True,
        verbose=False,
    )
    payload = build_payload(results, args)
    output_path = Path(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output_json": str(output_path),
        "frames_analyzed": payload["summary"]["frames_analyzed"],
        "detections": payload["summary"]["total_detections"],
        "observations": len(payload["observations"]),
    }, ensure_ascii=False))
    return 0


def build_payload(results: Any, args: argparse.Namespace) -> dict[str, Any]:
    detections: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    class_frame_refs: dict[str, set[str]] = defaultdict(set)
    class_confidences: dict[str, list[float]] = defaultdict(list)
    frame_count = 0

    for result in results:
        frame_count += 1
        frame_ref = frame_reference(result, frame_count)
        names = result.names or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            continue
        for box in boxes:
            class_id = int(box.cls[0].item())
            label = str(names.get(class_id, class_id))
            confidence = float(box.conf[0].item())
            xyxy = [round(float(value), 2) for value in box.xyxy[0].tolist()]
            if len(detections) < args.max_detections:
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

    observations = observation_candidates(class_frame_refs, class_confidences, max_frame_refs=max(1, args.max_frame_refs))
    total_detection_count = sum(class_counts.values())
    return {
        "version": "lawcompass-yolo-observation-smoke-v1",
        "provider": "ultralytics-yolo",
        "source": "vision_model:yolo",
        "model": str(args.model),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "source": str(args.source),
            "device": str(args.device),
            "conf": args.conf,
        },
        "summary": {
            "frames_analyzed": frame_count,
            "total_detections": total_detection_count,
            "class_counts": dict(class_counts),
            "stored_detection_count": len(detections),
            "detections_truncated": total_detection_count > len(detections),
        },
        "observations": observations,
        "detections": detections,
        "notes": [
            "YOLO detections are object-location evidence only, not legal or accident-causation conclusions.",
            "Do not infer collision_partner_type from object presence alone.",
            "Feed high-confidence observations through Agent fact arbitration before user-facing use.",
        ],
    }


def observation_candidates(
    class_frame_refs: dict[str, set[str]],
    class_confidences: dict[str, list[float]],
    *,
    max_frame_refs: int,
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    if "person" in class_frame_refs:
        observations.append(_presence_observation("pedestrian_visible", True, "person", class_frame_refs, class_confidences, max_frame_refs))
    if "traffic light" in class_frame_refs:
        observations.append(_presence_observation("opponent_signal_visible", True, "traffic light", class_frame_refs, class_confidences, max_frame_refs))
    if any(label in class_frame_refs for label in VEHICLE_CLASSES):
        frame_refs = limited_frame_refs({ref for label in VEHICLE_CLASSES for ref in class_frame_refs.get(label, set())}, max_frame_refs)
        confidences = [conf for label in VEHICLE_CLASSES for conf in class_confidences.get(label, [])]
        observations.append({
            "field": "primary_collision_target",
            "value": "vehicle_candidate",
            "confidence": round(min(max(confidences or [0.0]), 0.72), 4),
            "source": "vision_model:yolo",
            "frame_refs": frame_refs,
            "reason": "YOLO detected vehicle-class objects. This is a candidate object inventory, not proof of collision target.",
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
        "frame_refs": limited_frame_refs(class_frame_refs.get(label, set()), max_frame_refs),
        "reason": f"YOLO detected {label}. This indicates visible object presence only.",
    }


def limited_frame_refs(frame_refs: set[str], limit: int) -> list[str]:
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


def frame_reference(result: Any, frame_count: int) -> str:
    path = Path(str(result.path))
    if path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        return f"{path.stem}_frame_{frame_count:06d}.jpg"
    return path.name


if __name__ == "__main__":
    raise SystemExit(main())
