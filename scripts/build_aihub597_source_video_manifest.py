"""Build a local video-accuracy manifest from downloaded AI-Hub 597 source videos.

This script does not download files and does not call model APIs. It connects
local source videos with their AI-Hub accident-object label JSON so the video
pipeline can be evaluated against a broader, balanced local sample set.
Generated manifests should stay under .local/ or logs/ and must not be
committed because they contain local video paths.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ACCIDENT_OBJECT_TO_TARGET = {
    0: "vehicle",
    1: "pedestrian",
    2: "motorcycle",
    3: "bicycle",
}


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def accident_target(label_path: Path) -> str:
    payload = load_json(label_path)
    video = payload.get("video") if isinstance(payload, dict) else {}
    try:
        code = int(video.get("accident_object"))
    except (TypeError, ValueError, AttributeError):
        code = -1
    return ACCIDENT_OBJECT_TO_TARGET.get(code, "unknown")


def index_labels(labels_root: Path) -> dict[str, Path]:
    labels: dict[str, Path] = {}
    for path in labels_root.rglob("*.json"):
        labels[path.stem] = path.resolve()
    return labels


def candidate_videos(video_root: Path, labels: dict[str, Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for video_path in sorted(video_root.rglob("*")):
        if video_path.suffix.lower() not in {".mp4", ".mov", ".mkv", ".avi"}:
            continue
        label_path = labels.get(video_path.stem)
        if not label_path:
            continue
        target = accident_target(label_path)
        if target == "unknown":
            continue
        rows.append({
            "name": video_path.stem,
            "target": target,
            "video_path": video_path.resolve(),
            "label_json": label_path,
            "size_bytes": video_path.stat().st_size,
        })
    return rows


def select_balanced(rows: list[dict[str, Any]], per_target: int, max_samples: int) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(rows, key=lambda item: (item["target"], item["size_bytes"], item["name"])):
        target = str(row["target"])
        if per_target > 0 and len(buckets[target]) >= per_target:
            continue
        buckets[target].append(row)
    selected: list[dict[str, Any]] = []
    for target in ("vehicle", "pedestrian", "motorcycle", "bicycle"):
        selected.extend(buckets.get(target, []))
    if max_samples > 0:
        selected = selected[:max_samples]
    return selected


def build_sample(row: dict[str, Any], case_json: Path) -> dict[str, Any]:
    return {
        "name": row["name"],
        "video_path": str(row["video_path"]),
        "case_json": str(case_json.resolve()),
        "require_frame_observations": True,
        "require_agent_video_facts": False,
        "reference": {
            "source_type": "aihub597_source_video_local",
            "label_json": str(row["label_json"]),
            "expected_direct_collision_partner_type": row["target"],
            "purpose": "evaluation_only_not_agent_input",
            "calibration_purpose": "video_fact_extraction_target_alignment",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an AI-Hub 597 source-video batch manifest.")
    parser.add_argument("--video-root", default=".local/aihub597_source_validation_recommended/videos")
    parser.add_argument("--labels-root", default="datasets/aihub/traffic-accident-video/labels/video")
    parser.add_argument("--case-json", default=".local/aihub597_source_validation_recommended/neutral_case.json")
    parser.add_argument("--output", default=".local/aihub597_source_validation_recommended/batch_manifest.generated.json")
    parser.add_argument("--per-target", type=int, default=4)
    parser.add_argument("--max-samples", type=int, default=16)
    args = parser.parse_args()

    video_root = Path(args.video_root).expanduser().resolve()
    labels_root = Path(args.labels_root).expanduser().resolve()
    case_json = Path(args.case_json).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()

    if not video_root.exists():
        raise SystemExit(f"video root does not exist: {video_root}")
    if not labels_root.exists():
        raise SystemExit(f"labels root does not exist: {labels_root}")
    if not case_json.exists():
        raise SystemExit(f"case json does not exist: {case_json}")

    rows = candidate_videos(video_root, index_labels(labels_root))
    selected = select_balanced(rows, args.per_target, args.max_samples)
    manifest = {
        "samples": [build_sample(row, case_json) for row in selected],
        "metadata": {
            "source": "AI-Hub 597 local source videos",
            "candidate_video_count": len(rows),
            "selected_sample_count": len(selected),
            "per_target": args.per_target,
            "policy": "Generated manifest is local-only. Do not commit raw video paths or files.",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = defaultdict(int)
    for row in selected:
        counts[row["target"]] += 1
    print(json.dumps({
        "output": str(output),
        "candidate_video_count": len(rows),
        "selected_sample_count": len(selected),
        "target_counts": dict(sorted(counts.items())),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
