from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_APP = REPO_ROOT / "apps" / "agent"
if str(AGENT_APP) not in sys.path:
    sys.path.insert(0, str(AGENT_APP))

from app.services.fact_arbitration import arbitrate_facts
from app.services.video_input_contract import normalize_video_input_contract


VERSION = "lawcompass-video-openai-yolo-merge-eval-v1"
YOLO_CANDIDATE_FIELDS = {
    "pedestrian_visible",
    "opponent_signal_visible",
    "primary_collision_target",
}


def main() -> int:
    args = parse_args()
    manifest_path = resolve_path(args.manifest)
    openai_dir = resolve_path(args.openai_batch_dir)
    yolo_dir = resolve_path(args.yolo_dir)
    output_path = resolve_path(args.output)

    manifest = read_json(manifest_path)
    samples = manifest.get("samples") if isinstance(manifest, dict) else None
    if not isinstance(samples, list):
        raise SystemExit(f"Manifest must contain a samples array: {manifest_path}")

    results: list[dict[str, Any]] = []
    for index, sample in enumerate(samples, start=1):
        if not isinstance(sample, dict):
            continue
        result = evaluate_sample(sample, index=index, openai_dir=openai_dir, yolo_dir=yolo_dir)
        results.append(result)

    aggregate = aggregate_results(results)
    output = {
        "version": VERSION,
        "manifest": str(manifest_path.relative_to(REPO_ROOT) if manifest_path.is_relative_to(REPO_ROOT) else manifest_path),
        "openai_batch_dir": str(openai_dir.relative_to(REPO_ROOT) if openai_dir.is_relative_to(REPO_ROOT) else openai_dir),
        "yolo_dir": str(yolo_dir.relative_to(REPO_ROOT) if yolo_dir.is_relative_to(REPO_ROOT) else yolo_dir),
        "sample_count": len(results),
        "aggregate": aggregate,
        "samples": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(aggregate, ensure_ascii=False, indent=2))
    return 0 if aggregate["contamination_regression_count"] == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge existing OpenAI frame-analysis debug observations and YOLO smoke "
            "observations, then verify Agent fact-contract/arbitration behavior."
        )
    )
    parser.add_argument("--manifest", required=True, help="Reference manifest with sample names/video paths.")
    parser.add_argument("--openai-batch-dir", required=True, help="Directory containing video_agent_e2e per-sample JSON.")
    parser.add_argument("--yolo-dir", required=True, help="Directory containing car_accident_N YOLO smoke JSON.")
    parser.add_argument("--output", required=True, help="JSON output path for the merge evaluation summary.")
    return parser.parse_args()


def evaluate_sample(sample: dict[str, Any], *, index: int, openai_dir: Path, yolo_dir: Path) -> dict[str, Any]:
    name = str(sample.get("name") or f"sample_{index}")
    video_path = Path(str(sample.get("video_path") or f"car_accident_{index}.mp4"))
    video_stem = video_path.stem or f"car_accident_{index}"
    openai_payload = read_json(openai_dir / f"{name}.json")
    yolo_payload = read_json(yolo_dir / f"{video_stem}.json")
    case_facts = read_case_facts(sample.get("case_json"))

    openai_observations = source_observations(
        [
            *as_list(openai_payload.get("agent_video_input", {}).get("accepted_observations")),
            *as_list(openai_payload.get("agent_video_input", {}).get("uncertain_observations")),
            *as_list(openai_payload.get("agent_video_input", {}).get("supporting_observations")),
        ],
        default_source="frame_analysis:openai_debug_contract",
    )
    yolo_observations = source_observations(
        as_list(yolo_payload.get("observations")),
        default_source="vision_model:yolo",
    )
    representative_frame_count = int(
        openai_payload.get("video_fact_card", {}).get("representative_frame_count")
        or openai_payload.get("frame_analysis", {}).get("selected_frame_count")
        or 0
    )

    contract = normalize_video_input_contract(
        {
            "metadata": {
                "representative_frames": [f"{video_stem}_representative_{frame_index:03d}.jpg" for frame_index in range(1, representative_frame_count + 1)],
                "observations": [*openai_observations, *yolo_observations],
                "openai_frame_analysis": {
                    "enabled": True,
                    "selected_frame_count": representative_frame_count,
                },
                "yolo_frame_analysis": {
                    "enabled": True,
                    "provider": yolo_payload.get("provider"),
                    "model": display_model_name(yolo_payload.get("model")),
                    "summary": yolo_payload.get("summary") if isinstance(yolo_payload.get("summary"), dict) else {},
                },
            }
        }
    )
    arbitration = arbitrate_facts(user_facts=case_facts, video_contract=contract)
    yolo_candidate_summary = summarize_yolo_candidates(contract)
    contamination_flags = contamination_regressions(contract, arbitration)

    return {
        "name": name,
        "video_stem": video_stem,
        "input_case_fact_count": len(case_facts),
        "openai_observation_count": len(openai_observations),
        "yolo_observation_count": len(yolo_observations),
        "representative_frame_count": representative_frame_count,
        "accepted_count": len(contract["accepted_observations"]),
        "uncertain_count": len(contract["uncertain_observations"]),
        "supporting_count": len(contract["supporting_observations"]),
        "fact_patch_fields": sorted(contract["fact_patch"].keys()),
        "applied_video_fields": arbitration["contract"]["applied_video_fields"],
        "confirmed_fields": arbitration["contract"]["confirmed_fields"],
        "conflict_count": len(arbitration["contract"]["conflicts"]),
        "yolo_candidate_summary": yolo_candidate_summary,
        "contamination_regressions": contamination_flags,
        "recovery_status": contract["observation_quality_summary"].get("recovery_status"),
    }


def source_observations(observations: list[Any], *, default_source: str) -> list[dict[str, Any]]:
    sourced: list[dict[str, Any]] = []
    for item in observations:
        if not isinstance(item, dict):
            continue
        sourced.append({**item, "source": item.get("source") or default_source})
    return sourced


def summarize_yolo_candidates(contract: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "accepted": [],
        "uncertain": [],
        "supporting": [],
        "ignored": [],
    }
    for bucket_name in ("accepted", "uncertain", "supporting", "ignored"):
        contract_key = f"{bucket_name}_observations"
        for item in as_list(contract.get(contract_key)):
            if not isinstance(item, dict):
                continue
            field = str(item.get("field") or "")
            source = str(item.get("source") or "")
            if field in YOLO_CANDIDATE_FIELDS and source.startswith("vision_model:yolo"):
                summary[bucket_name].append({
                    "field": field,
                    "value": item.get("value"),
                    "confidence": item.get("confidence"),
                    "reason": item.get("reason"),
                    "frame_ref_count": len(item.get("frame_refs") or []),
                })
    return summary


def contamination_regressions(contract: dict[str, Any], arbitration: dict[str, Any]) -> list[str]:
    fact_patch = contract.get("fact_patch") if isinstance(contract.get("fact_patch"), dict) else {}
    accepted_yolo_fields = {
        str(item.get("field"))
        for item in as_list(contract.get("accepted_observations"))
        if isinstance(item, dict) and str(item.get("source") or "").startswith("vision_model:yolo")
    }
    applied = set(arbitration.get("contract", {}).get("applied_video_fields") or [])
    confirmed = set(arbitration.get("contract", {}).get("confirmed_fields") or [])

    flags: list[str] = []
    for field in sorted(YOLO_CANDIDATE_FIELDS):
        if field in accepted_yolo_fields:
            flags.append(f"yolo_candidate_accepted:{field}")
        if field in fact_patch:
            flags.append(f"yolo_candidate_fact_patch:{field}")
        if field in applied:
            flags.append(f"yolo_candidate_applied:{field}")
        if field in confirmed:
            flags.append(f"yolo_candidate_confirmed:{field}")
    return flags


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    total_yolo_observations = sum(int(item.get("yolo_observation_count") or 0) for item in results)
    total_openai_observations = sum(int(item.get("openai_observation_count") or 0) for item in results)
    contamination_count = sum(len(item.get("contamination_regressions") or []) for item in results)
    yolo_uncertain_count = sum(len(item.get("yolo_candidate_summary", {}).get("uncertain") or []) for item in results)
    yolo_accepted_count = sum(len(item.get("yolo_candidate_summary", {}).get("accepted") or []) for item in results)
    return {
        "sample_count": len(results),
        "openai_observation_count": total_openai_observations,
        "yolo_observation_count": total_yolo_observations,
        "yolo_candidate_uncertain_count": yolo_uncertain_count,
        "yolo_candidate_accepted_count": yolo_accepted_count,
        "applied_video_field_count": sum(len(item.get("applied_video_fields") or []) for item in results),
        "confirmed_video_field_count": sum(len(item.get("confirmed_fields") or []) for item in results),
        "conflict_count": sum(int(item.get("conflict_count") or 0) for item in results),
        "contamination_regression_count": contamination_count,
        "status": "pass" if contamination_count == 0 else "fail",
    }


def read_case_facts(case_json: Any) -> dict[str, Any]:
    if not case_json:
        return {}
    path = resolve_path(str(case_json))
    if not path.exists():
        return {}
    data = read_json(path)
    case = data.get("case") if isinstance(data.get("case"), dict) else data
    facts = case.get("structured_facts") if isinstance(case, dict) else {}
    return dict(facts) if isinstance(facts, dict) else {}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Required JSON file does not exist: {path}")
    text = path.read_text(encoding="utf-8-sig")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise SystemExit(f"Expected a JSON object: {path}")
    return data


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def display_model_name(model: Any) -> str | None:
    if not model:
        return None
    return Path(str(model)).name


def resolve_path(path: str | Path) -> Path:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = REPO_ROOT / resolved
    return resolved


if __name__ == "__main__":
    raise SystemExit(main())
