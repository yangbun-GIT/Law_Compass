"""Compare AI-Hub 597 source-video labels with LawCompass video extraction output.

This evaluator is for calibration only. It does not call OpenAI, does not
download media, and does not feed labels into Agent inference. It checks whether
the video pipeline extracted target-type signals that agree with the AI-Hub
accident_object label.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ACCIDENT_OBJECT_TO_TARGET = {
    0: "vehicle",
    1: "pedestrian",
    2: "motorcycle",
    3: "bicycle",
}

TARGET_FIELDS = {
    "direct_collision_partner_type",
    "collision_partner_type",
    "primary_collision_target",
}

DIRECT_TARGET_FIELDS = {
    "direct_collision_partner_type",
    "collision_partner_type",
}


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_target(value: Any) -> str:
    text = re.sub(r"[^a-z0-9가-힣]+", "_", str(value or "").lower()).strip("_")
    if text.endswith("_candidate"):
        text = text[: -len("_candidate")]
    if text in {"vehicle", "car", "truck", "bus", "van"} or "vehicle" in text:
        return "vehicle"
    if text in {"pedestrian", "person"} or "pedestrian" in text:
        return "pedestrian"
    if text in {"motorcycle", "motorbike", "scooter", "moped", "two_wheeler", "two_wheeled"} or "motorcycle" in text or "two_wheeler" in text:
        return "motorcycle"
    if text in {"bicycle", "bike", "cyclist"} or "bicycle" in text:
        return "bicycle"
    if text in {"object", "obstacle", "facility"} or "object" in text:
        return "object"
    return "unknown"


def manifest_samples(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    samples = payload.get("samples") if isinstance(payload, dict) else payload
    if not isinstance(samples, list):
        raise ValueError("manifest must contain a samples array")
    return [sample for sample in samples if isinstance(sample, dict)]


def aggregate_samples(path: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(path)
    samples = payload.get("samples") if isinstance(payload, dict) else payload
    if not isinstance(samples, list):
        raise ValueError("batch aggregate must contain a samples array")
    out: dict[str, dict[str, Any]] = {}
    for sample in samples:
        if isinstance(sample, dict) and sample.get("name"):
            out[str(sample["name"])] = sample
    return out


def expected_target_from_label(sample: dict[str, Any]) -> tuple[str, str]:
    reference = sample.get("reference") if isinstance(sample.get("reference"), dict) else {}
    label_path = Path(str(reference.get("label_json") or "")).expanduser()
    if not label_path.exists():
        return "unknown", str(label_path)
    label = load_json(label_path)
    video = label.get("video") if isinstance(label, dict) else {}
    code = video.get("accident_object") if isinstance(video, dict) else None
    try:
        parsed_code = int(code)
    except (TypeError, ValueError):
        parsed_code = -1
    return ACCIDENT_OBJECT_TO_TARGET.get(parsed_code, "unknown"), str(label_path)


def extracted_targets(sample: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in sample.get("field_metrics") or []:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or "")
        if field not in TARGET_FIELDS:
            continue
        target = normalize_target(item.get("value"))
        if target == "unknown":
            continue
        rows.append({
            "field": field,
            "target": target,
            "raw_value": item.get("value"),
            "from_observation": bool(item.get("from_observation")),
            "in_fact_patch": bool(item.get("in_fact_patch")),
            "applied": bool(item.get("applied")),
            "confirmed": bool(item.get("confirmed")),
            "supporting": bool(item.get("supporting")),
            "confidence": item.get("confidence"),
            "frame_ref_count": item.get("frame_ref_count"),
        })
    return rows


def score_sample(manifest_sample: dict[str, Any], batch_by_name: dict[str, dict[str, Any]]) -> dict[str, Any]:
    name = str(manifest_sample.get("name") or "")
    batch = batch_by_name.get(name, {})
    expected, label_path = expected_target_from_label(manifest_sample)
    targets = extracted_targets(batch)
    observation_hits = [item for item in targets if item["from_observation"] and item["target"] == expected]
    agent_hits = [
        item for item in targets
        if item["target"] == expected and (item["in_fact_patch"] or item["applied"] or item["confirmed"])
    ]
    direct_pollution = [
        item for item in targets
        if item["field"] in DIRECT_TARGET_FIELDS and item["target"] != expected
    ]
    agent_direct_pollution = [
        item for item in direct_pollution
        if item["in_fact_patch"] or item["applied"] or item["confirmed"]
    ]
    return {
        "name": name,
        "matched_batch_sample": bool(batch),
        "label_json": label_path,
        "expected_target": expected,
        "extracted_targets": targets,
        "observation_target_hit": bool(observation_hits),
        "agent_target_hit": bool(agent_hits),
        "direct_target_pollution": bool(direct_pollution),
        "agent_direct_target_pollution": bool(agent_direct_pollution),
        "direct_target_pollution_values": direct_pollution,
        "agent_direct_target_pollution_values": agent_direct_pollution,
        "frame_observation_count": batch.get("frame_observation_count"),
        "agent_accepted_count": batch.get("agent_accepted_count"),
        "agent_uncertain_count": batch.get("agent_uncertain_count"),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    by_target: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        target = str(row.get("expected_target") or "unknown")
        by_target[target]["sample_count"] += 1
        by_target[target]["observation_target_hit_count"] += int(bool(row.get("observation_target_hit")))
        by_target[target]["agent_target_hit_count"] += int(bool(row.get("agent_target_hit")))
        by_target[target]["direct_target_pollution_count"] += int(bool(row.get("direct_target_pollution")))
        by_target[target]["agent_direct_target_pollution_count"] += int(bool(row.get("agent_direct_target_pollution")))
    target_summary = {
        target: {
            **dict(counter),
            "observation_target_hit_rate": rate(counter["observation_target_hit_count"], counter["sample_count"]),
            "agent_target_hit_rate": rate(counter["agent_target_hit_count"], counter["sample_count"]),
            "direct_target_pollution_rate": rate(counter["direct_target_pollution_count"], counter["sample_count"]),
            "agent_direct_target_pollution_rate": rate(counter["agent_direct_target_pollution_count"], counter["sample_count"]),
        }
        for target, counter in sorted(by_target.items())
    }
    return {
        "sample_count": total,
        "matched_batch_sample_count": sum(1 for row in rows if row.get("matched_batch_sample")),
        "observation_target_hit_count": sum(1 for row in rows if row.get("observation_target_hit")),
        "agent_target_hit_count": sum(1 for row in rows if row.get("agent_target_hit")),
        "direct_target_pollution_count": sum(1 for row in rows if row.get("direct_target_pollution")),
        "agent_direct_target_pollution_count": sum(1 for row in rows if row.get("agent_direct_target_pollution")),
        "observation_target_hit_rate": rate(sum(1 for row in rows if row.get("observation_target_hit")), total),
        "agent_target_hit_rate": rate(sum(1 for row in rows if row.get("agent_target_hit")), total),
        "direct_target_pollution_rate": rate(sum(1 for row in rows if row.get("direct_target_pollution")), total),
        "agent_direct_target_pollution_rate": rate(sum(1 for row in rows if row.get("agent_direct_target_pollution")), total),
        "target_summary": target_summary,
    }


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate AI-Hub 597 label target extraction from a video batch aggregate.")
    parser.add_argument("--manifest", required=True, help="Batch manifest with reference.label_json entries.")
    parser.add_argument("--batch-aggregate", required=True, help="video_accuracy_batch aggregate.json output.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-observation-target-hit-rate", type=float, default=0.8)
    parser.add_argument("--max-direct-target-pollution-rate", type=float, default=0.0)
    parser.add_argument("--max-agent-direct-target-pollution-rate", type=float, default=0.0)
    parser.add_argument("--fail-on-threshold", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    aggregate_path = Path(args.batch_aggregate).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    batch_by_name = aggregate_samples(aggregate_path)
    rows = [score_sample(sample, batch_by_name) for sample in manifest_samples(manifest_path)]
    summary = summarize(rows)
    status = "passed"
    if summary["observation_target_hit_rate"] < args.min_observation_target_hit_rate:
        status = "needs_attention"
    if summary["direct_target_pollution_rate"] > args.max_direct_target_pollution_rate:
        status = "needs_attention"
    if summary["agent_direct_target_pollution_rate"] > args.max_agent_direct_target_pollution_rate:
        status = "needs_attention"
    result = {
        "aihub597_video_batch_target_eval": "completed",
        "status": status,
        "manifest": str(manifest_path),
        "batch_aggregate": str(aggregate_path),
        "thresholds": {
            "min_observation_target_hit_rate": args.min_observation_target_hit_rate,
            "max_direct_target_pollution_rate": args.max_direct_target_pollution_rate,
            "max_agent_direct_target_pollution_rate": args.max_agent_direct_target_pollution_rate,
        },
        "summary": summary,
        "samples": rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, **summary, "output": str(output_path)}, ensure_ascii=False, indent=2))
    return 1 if args.fail_on_threshold and status != "passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
