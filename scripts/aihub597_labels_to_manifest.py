import argparse
import json
import re
from pathlib import Path


DATASET_NAME = "AI-Hub 교통사고 영상 데이터"
DATASET_KEY = "597"


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_").lower()
    return cleaned or "aihub597_case"


def infer_split(path: Path) -> str:
    text = str(path)
    if "1.Training" in text:
        return "training"
    if "2.Validation" in text:
        return "validation"
    return "unknown"


def infer_file_key(path: Path, file_key_map: dict[str, str]) -> str:
    parent_zip_name = None
    for part in path.parts:
        if part.startswith(("TL_", "VL_")) and part.endswith(".zip"):
            parent_zip_name = part
            break
    if not parent_zip_name:
        folder = path.parent.name
        parent_zip_name = f"{folder}.zip" if folder.startswith(("TL_", "VL_")) else folder
    return file_key_map.get(parent_zip_name, "")


def infer_partner_type(path: Path, video: dict) -> str:
    text = str(path)
    if "차대보행자" in text or "pedestrian" in path.name:
        return "pedestrian"
    if "차대자전거" in text or "bicycle" in path.name:
        return "bicycle"
    return "vehicle"


def scenario_summary(video: dict) -> str:
    parts = [
        f"사고유형={video.get('traffic_accident_type')}",
        f"사고대상={video.get('accident_object')}",
        f"장소={video.get('accident_place')}",
        f"장소특징={video.get('accident_place_feature')}",
        f"A진행={video.get('vehicle_a_progress_info')}",
        f"B진행={video.get('vehicle_b_progress_info')}",
        f"과실A:B={video.get('accident_negligence_rateA')}:{video.get('accident_negligence_rateB')}",
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


def build_case(path: Path, file_key_map: dict[str, str]) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    video = data.get("video", {})
    partner_type = infer_partner_type(path, video)
    must_not = []
    if partner_type != "pedestrian":
        must_not.append("pedestrian_as_direct_collision_target")
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
            "file_key": infer_file_key(path, file_key_map),
            "split": infer_split(path),
        },
        "scenario_summary": scenario_summary(video),
        "reference_notes": [
            "AI-Hub 라벨에서 생성한 자동 reference 후보입니다.",
            "원천 영상 확인 전까지 Agent 입력 사실로 사용하지 않습니다.",
        ],
        "reference_outcome": {
            "known_result_status": "public_reported",
            "known_result_summary": (
                f"라벨 과실비율 A {video.get('accident_negligence_rateA')} / "
                f"B {video.get('accident_negligence_rateB')}"
            ),
            "confidence_note": "AI-Hub 라벨 기반 보정 참고값이며 실제 사건 판단으로 단정하지 않습니다.",
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
            "notes": "AI-Hub 라벨은 평가와 보정 reference로만 사용한다.",
        },
    }


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert AI-Hub 597 label JSON files to a LawCompass reference manifest.")
    parser.add_argument("--labels-root", default="datasets/aihub/traffic-accident-video/aihubshell")
    parser.add_argument("--file-key-doc", default="docs/AIHUB_597_LABEL_FILEKEYS.md")
    parser.add_argument("--output", default=".local/aihub597_video_label_manifest.json")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    labels_root = Path(args.labels_root)
    file_key_map = load_file_key_map(Path(args.file_key_doc))
    files = sorted(labels_root.rglob("*.json"))
    if args.limit > 0:
        files = files[: args.limit]

    manifest = {
        "version": "1.0",
        "purpose": "AI-Hub 597 video label reference candidates for LawCompass evaluation. Local-only generated artifact.",
        "cases": [build_case(path, file_key_map) for path in files],
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(manifest['cases'])} cases to {output}")


if __name__ == "__main__":
    main()
