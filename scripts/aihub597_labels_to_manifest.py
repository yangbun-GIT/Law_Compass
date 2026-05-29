import argparse
import json
import re
from pathlib import Path


DATASET_NAME = "AI-Hub traffic accident video dataset"
DATASET_KEY = "597"
PARTNER_TYPE_BY_ACCIDENT_OBJECT = {
    "0": "vehicle",
    "1": "pedestrian",
    "2": "motorcycle",
    "3": "bicycle",
}


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_").lower()
    return cleaned or "aihub597_case"


def infer_split(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    text = str(path)
    if "training" in parts or "1.Training" in text:
        return "training"
    if "validation" in parts or "2.Validation" in text:
        return "validation"
    return "unknown"


def infer_partner_type(path: Path, video: dict | None = None) -> str:
    accident_object_value = None if video is None else video.get("accident_object")
    accident_object = "" if accident_object_value is None else str(accident_object_value)
    if accident_object in PARTNER_TYPE_BY_ACCIDENT_OBJECT:
        return PARTNER_TYPE_BY_ACCIDENT_OBJECT[accident_object]
    text = path.name.lower()
    if "pedestrian" in text:
        return "pedestrian"
    if "two-wheeled" in text or "motorcycle" in text:
        return "motorcycle"
    if "bicycle" in text:
        return "bicycle"
    if "vehicle" in text:
        return "vehicle"
    return "unknown"


def scenario_summary(video: dict) -> str:
    parts = [
        f"traffic_accident_type={video.get('traffic_accident_type')}",
        f"accident_object={video.get('accident_object')}",
        f"accident_place={video.get('accident_place')}",
        f"accident_place_feature={video.get('accident_place_feature')}",
        f"vehicle_a_progress_info={video.get('vehicle_a_progress_info')}",
        f"vehicle_b_progress_info={video.get('vehicle_b_progress_info')}",
        f"fault_ratio_A_B={video.get('accident_negligence_rateA')}:{video.get('accident_negligence_rateB')}",
    ]
    return ", ".join(parts)


def expected_context(video: dict) -> list[str]:
    context = []
    for key in (
        "traffic_accident_type",
        "accident_place",
        "accident_place_feature",
        "vehicle_a_progress_info",
        "vehicle_b_progress_info",
        "damage_location",
        "weather",
    ):
        value = video.get(key)
        if value not in ("", None):
            context.append(f"{key}:{value}")
    return context[:8]


def load_file_key_map(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    mapping = {}
    for line in text.splitlines():
        if "| 509" not in line or "`" not in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        file_key = cells[0]
        filename = cells[1].strip("`")
        mapping[filename] = file_key
    return mapping


def load_local_index(labels_root: Path) -> dict[str, dict]:
    index_path = labels_root / "index.json"
    if not index_path.exists():
        return {}
    entries = json.loads(index_path.read_text(encoding="utf-8"))
    return {entry.get("file_name", ""): entry for entry in entries if entry.get("kind") == "json"}


def select_balanced_files(files: list[Path], per_target: int, targets: list[str]) -> list[Path]:
    buckets = {target: [] for target in targets}
    for path in files:
        if all(len(items) >= per_target for items in buckets.values()):
            break
        data = json.loads(path.read_text(encoding="utf-8"))
        partner_type = infer_partner_type(path, data.get("video", {}))
        if partner_type in buckets and len(buckets[partner_type]) < per_target:
            buckets[partner_type].append(path)
    selected: list[Path] = []
    for target in targets:
        selected.extend(buckets[target])
    return selected


def build_case(path: Path, file_key_map: dict[str, str], local_index: dict[str, dict]) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    video = data.get("video", {})
    partner_type = infer_partner_type(path, video)
    index_entry = local_index.get(path.name, {})
    source_zip = index_entry.get("source_zip", "")
    file_key = index_entry.get("file_key") or file_key_map.get(source_zip, "")
    must_not = []
    if partner_type != "pedestrian":
        must_not.append("pedestrian_as_direct_collision_target")
    if partner_type != "motorcycle":
        must_not.append("motorcycle_as_direct_collision_target")
    if partner_type != "bicycle":
        must_not.append("bicycle_as_direct_collision_target")

    return {
        "id": slug(f"aihub597_{path.stem}"),
        "title": path.stem,
        "source_type": "aihub_sample",
        "reference_role": "calibration_reference_only",
        "review_status": "candidate_requires_manual_review",
        "dataset_ref": {
            "provider": "AI-Hub",
            "dataset_name": DATASET_NAME,
            "dataset_key": DATASET_KEY,
            "file_key": file_key,
            "split": infer_split(path),
        },
        "scenario_summary": scenario_summary(video),
        "reference_notes": [
            "Automatically generated from AI-Hub label JSON.",
            "Do not use as Agent input fact until the matching raw video is reviewed.",
        ],
        "reference_outcome": {
            "known_result_status": "public_reported",
            "known_result_summary": (
                f"AI-Hub label fault ratio A {video.get('accident_negligence_rateA')} / "
                f"B {video.get('accident_negligence_rateB')}"
            ),
            "confidence_note": "Calibration reference only, not a final legal outcome.",
        },
        "reference_expectations": {
            "direct_collision_partner_type": partner_type,
            "accident_event_required": True,
            "expected_context": expected_context(video),
            "must_not_promote": must_not,
        },
        "evaluation_focus": [
            "direct_collision_partner_type",
            "context_pollution_guard",
            "fault_ratio_reference_range",
            "aihub_label_alignment",
        ],
        "usage_policy": {
            "agent_input_allowed": False,
            "raw_video_commit_allowed": False,
            "notes": "Use AI-Hub labels only as evaluation and calibration references.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert AI-Hub 597 label JSON files to a LawCompass reference manifest.")
    parser.add_argument("--labels-root", default="datasets/aihub/traffic-accident-video/labels/video")
    parser.add_argument("--file-key-doc", default="docs/AIHUB_597_LABEL_FILEKEYS.md")
    parser.add_argument("--output", default=".local/aihub597_video_label_manifest.json")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--balanced", action="store_true", help="Select a balanced sample by direct collision partner type.")
    parser.add_argument("--per-target", type=int, default=50, help="Number of cases per target when --balanced is used.")
    parser.add_argument("--targets", default="vehicle,pedestrian,motorcycle,bicycle", help="Comma-separated target order for --balanced.")
    args = parser.parse_args()

    labels_root = Path(args.labels_root)
    file_key_map = load_file_key_map(Path(args.file_key_doc))
    local_index = load_local_index(labels_root)
    files = sorted((labels_root / "training" / "json").glob("*.json"))
    files += sorted((labels_root / "validation" / "json").glob("*.json"))
    if args.balanced:
        targets = [item.strip() for item in args.targets.split(",") if item.strip()]
        files = select_balanced_files(files, args.per_target, targets)
    elif args.limit > 0:
        files = files[: args.limit]

    manifest = {
        "version": "1.0",
        "purpose": "AI-Hub 597 video label reference candidates for LawCompass evaluation. Local-only generated artifact.",
        "cases": [build_case(path, file_key_map, local_index) for path in files],
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(manifest['cases'])} cases to {output}")


if __name__ == "__main__":
    main()
