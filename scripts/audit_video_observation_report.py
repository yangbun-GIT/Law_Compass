"""Build a repeatable audit report for video observation accuracy.

The script compares a video accuracy batch aggregate with a local reference
manifest. It does not call model APIs, download media, or read raw videos.
Use it to lock what each sample extracted, what matched the reference, and
what still needs follow-up before changing the video pipeline again.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = "logs/video_accuracy/p2_2a_observation_audit.json"

FIELD_CONTEXT_ALIASES: dict[str, tuple[str, ...]] = {
    "centerline_context": ("centerline", "centerline_cross", "centerline_cross_reason"),
    "parked_vehicle_obstacle": (
        "parked_vehicle",
        "parked_vehicle_obstruction",
        "road_obstruction",
        "obstacle",
    ),
    "oncoming_vehicle": ("oncoming", "opposing", "opponent_vehicle", "opponent"),
    "secondary_rear_collision": ("secondary", "rear_collision", "rear_end", "bus_rear"),
    "intersection_context": ("intersection", "crosswalk_nearby", "traffic_signal", "signal"),
    "ego_signal_timing": ("ego_signal", "signal_timing", "yellow", "red", "traffic_signal"),
    "opponent_signal_unknown": ("opponent_signal", "opponent_signal_visible"),
    "front_vehicle_stopped": ("front_vehicle_stopped", "front_vehicle_stop_reason"),
    "stopped_vehicle": ("stopped_vehicle", "stopped_vehicle_without_lights", "unlit"),
    "bicycle_trigger": ("bicycle", "trigger_actor", "non_contact_trigger"),
    "vehicle_visible": ("vehicle", "front_vehicle", "stopped_vehicle", "primary_collision_target"),
}

POLLUTION_FIELD_HINTS: dict[str, tuple[str, ...]] = {
    "pedestrian_crosswalk_accident": ("pedestrian_collision", "pedestrian_crosswalk_accident"),
    "pedestrian_collision": ("pedestrian_collision",),
    "opponent_signal_violation_when_not_visible": ("opponent_signal_violation",),
    "simple_rear_end_only": ("simple_rear_end_only",),
    "centerline_violation_without_obstacle_context": ("centerline_violation",),
    "bicycle_direct_collision": ("bicycle_direct_collision", "collision_partner_type bicycle"),
}

DIRECT_TARGET_FIELDS = (
    "direct_collision_partner_type",
    "collision_partner_type",
    "primary_collision_target",
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_reference_cases(path: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(path)
    cases = payload.get("cases") if isinstance(payload, dict) else []
    out: dict[str, dict[str, Any]] = {}
    for case in cases or []:
        if isinstance(case, dict) and case.get("id"):
            out[str(case["id"])] = case
    return out


def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def text(value: Any) -> str:
    return str(value or "").strip()


def norm(value: Any) -> str:
    return text(value).lower().replace("-", "_").replace(" ", "_")


def field_metrics(sample: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in safe_list(sample.get("field_metrics")) if isinstance(item, dict)]


def promoted_metric(item: dict[str, Any]) -> bool:
    return bool(
        item.get("applied")
        or item.get("confirmed")
        or item.get("in_fact_patch")
        or item.get("supporting")
    )


def all_field_text(sample: dict[str, Any], *, promoted_only: bool = False) -> str:
    parts: list[str] = []
    for item in field_metrics(sample):
        if promoted_only and not promoted_metric(item):
            continue
        parts.append(norm(item.get("field")))
        parts.append(norm(item.get("value")))
    return " ".join(part for part in parts if part)


def direct_target(sample: dict[str, Any]) -> dict[str, Any]:
    for item in field_metrics(sample):
        field = norm(item.get("field"))
        if field not in DIRECT_TARGET_FIELDS:
            continue
        value = norm(item.get("value"))
        if "vehicle" in value or "car" in value:
            return {"value": "vehicle", "raw": item.get("value"), "candidate": "candidate" in value}
        if "pedestrian" in value or "person" in value:
            return {"value": "pedestrian", "raw": item.get("value"), "candidate": "candidate" in value}
        if "bicycle" in value or "bike" in value:
            return {"value": "bicycle", "raw": item.get("value"), "candidate": "candidate" in value}
        if "object" in value:
            return {"value": "object", "raw": item.get("value"), "candidate": "candidate" in value}
    return {"value": "unknown", "raw": None, "candidate": False}


def expected_context_status(sample: dict[str, Any], contexts: list[str]) -> dict[str, list[str]]:
    haystack = all_field_text(sample)
    matched: list[str] = []
    missing: list[str] = []
    for context in contexts:
        aliases = FIELD_CONTEXT_ALIASES.get(context, (context,))
        if any(alias in haystack for alias in aliases):
            matched.append(context)
        else:
            missing.append(context)
    return {"matched": matched, "missing": missing}


def pollution_status(sample: dict[str, Any], forbidden: list[str]) -> dict[str, Any]:
    promoted = all_field_text(sample, promoted_only=True)
    uncertain = all_field_text(sample, promoted_only=False)
    promoted_hits: list[str] = []
    uncertain_only_hits: list[str] = []
    for rule in forbidden:
        aliases = POLLUTION_FIELD_HINTS.get(rule, (rule,))
        promoted_hit = any(alias in promoted for alias in aliases)
        any_hit = any(alias in uncertain for alias in aliases)
        if promoted_hit:
            promoted_hits.append(rule)
        elif any_hit:
            uncertain_only_hits.append(rule)
    return {
        "promoted_hits": promoted_hits,
        "uncertain_only_hits": uncertain_only_hits,
        "has_promoted_pollution": bool(promoted_hits),
    }


def parse_output_json(path_value: Any) -> dict[str, Any]:
    if not path_value:
        return {"checked": False, "status": "missing_path"}
    path = Path(str(path_value))
    if not path.exists():
        return {"checked": False, "status": "missing_file", "path": str(path)}
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001 - audit must report malformed payloads.
        return {"checked": True, "status": "invalid_json", "path": str(path), "error": str(exc)}
    return {"checked": True, "status": "valid_json", "path": str(path), "top_level_keys": sorted(payload.keys())[:20]}


def audit_sample(sample: dict[str, Any], reference: dict[str, Any] | None) -> dict[str, Any]:
    expectations = reference.get("reference_expectations") if isinstance(reference, dict) else {}
    expectations = expectations if isinstance(expectations, dict) else {}
    expected_direct = text(expectations.get("direct_collision_partner_type")) or "unknown"
    actual_direct = direct_target(sample)
    context = expected_context_status(sample, [text(item) for item in safe_list(expectations.get("expected_context"))])
    pollution = pollution_status(sample, [text(item) for item in safe_list(expectations.get("must_not_promote"))])
    ambiguous_branches = safe_list(expectations.get("ambiguous_branches"))
    output_json = parse_output_json(sample.get("output_json"))

    accepted_count = int(sample.get("agent_accepted_count") or 0)
    frame_observation_count = int(sample.get("frame_observation_count") or 0)
    direct_match = expected_direct == "unknown" or actual_direct["value"] == expected_direct
    weak_reasons: list[str] = []
    fail_reasons: list[str] = []

    if frame_observation_count == 0:
        fail_reasons.append("zero_frame_observations")
    if not direct_match:
        fail_reasons.append("direct_collision_target_mismatch")
    if pollution["has_promoted_pollution"]:
        fail_reasons.append("forbidden_context_promoted")
    if output_json["status"] == "invalid_json":
        fail_reasons.append("sample_output_json_invalid")
    if accepted_count == 0 and frame_observation_count > 0:
        weak_reasons.append("observations_remained_uncertain")
    if context["missing"]:
        weak_reasons.append("expected_context_missing")
    if ambiguous_branches:
        # The aggregate currently exposes missing-info cards but not a full
        # conditional outcome structure for all samples. Keep this as a review
        # item instead of pretending the branch is fully covered.
        weak_reasons.append("ambiguous_branch_requires_explicit_output_review")
    if actual_direct.get("candidate"):
        weak_reasons.append("direct_target_is_candidate_not_confirmed")

    status = "pass"
    if fail_reasons:
        status = "fail"
    elif weak_reasons:
        status = "weak"

    return {
        "name": sample.get("name"),
        "status": status,
        "fail_reasons": fail_reasons,
        "weak_reasons": weak_reasons,
        "reference_case_id": reference.get("id") if isinstance(reference, dict) else None,
        "matched_reference": bool(reference),
        "expected_direct_collision_partner_type": expected_direct,
        "actual_direct_collision_partner_type": actual_direct,
        "frame_observation_count": frame_observation_count,
        "agent_accepted_count": accepted_count,
        "agent_uncertain_count": int(sample.get("agent_uncertain_count") or 0),
        "agent_supporting_count": int(sample.get("agent_supporting_count") or 0),
        "applied_count": int(sample.get("applied_count") or 0),
        "confirmed_count": int(sample.get("confirmed_count") or 0),
        "conflict_count": int(sample.get("conflict_count") or 0),
        "selected_frame_count": sample.get("selected_frame_count"),
        "expected_context": context,
        "pollution": pollution,
        "ambiguous_branch_count": len(ambiguous_branches),
        "missing_info_priority": sample.get("missing_info_priority"),
        "video_display": sample.get("video_display"),
        "key_fields": [
            {
                "field": item.get("field"),
                "value": item.get("value"),
                "confidence": item.get("confidence"),
                "applied": bool(item.get("applied")),
                "confirmed": bool(item.get("confirmed")),
                "conflict": bool(item.get("conflict")),
                "supporting": bool(item.get("supporting")),
                "frame_ref_count": item.get("frame_ref_count"),
            }
            for item in field_metrics(sample)
        ],
        "output_json_parse": output_json,
    }


def build_summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = {"pass": 0, "weak": 0, "fail": 0}
    for sample in samples:
        status_counts[str(sample.get("status"))] = status_counts.get(str(sample.get("status")), 0) + 1
    return {
        "sample_count": len(samples),
        "status_counts": status_counts,
        "fail_sample_count": status_counts.get("fail", 0),
        "weak_sample_count": status_counts.get("weak", 0),
        "zero_observation_count": sum(1 for item in samples if item.get("frame_observation_count") == 0),
        "promoted_pollution_count": sum(1 for item in samples if item.get("pollution", {}).get("has_promoted_pollution")),
        "invalid_output_json_count": sum(
            1 for item in samples if item.get("output_json_parse", {}).get("status") == "invalid_json"
        ),
        "candidate_direct_target_count": sum(
            1 for item in samples if item.get("actual_direct_collision_partner_type", {}).get("candidate")
        ),
        "missing_context_sample_count": sum(1 for item in samples if item.get("expected_context", {}).get("missing")),
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# P2-2a Video Observation Audit",
        "",
        "This report is generated from existing batch artifacts. It does not call model APIs or read raw videos.",
        "",
        "## Summary",
        "",
    ]
    summary = report["summary"]
    for key in (
        "sample_count",
        "fail_sample_count",
        "weak_sample_count",
        "zero_observation_count",
        "promoted_pollution_count",
        "invalid_output_json_count",
        "candidate_direct_target_count",
        "missing_context_sample_count",
    ):
        lines.append(f"- {key}: {summary.get(key)}")
    lines.extend(["", "## Samples", ""])
    for item in report["samples"]:
        lines.append(f"### {item['name']}")
        lines.append("")
        lines.append(f"- status: {item['status']}")
        lines.append(f"- fail_reasons: {', '.join(item['fail_reasons']) or 'none'}")
        lines.append(f"- weak_reasons: {', '.join(item['weak_reasons']) or 'none'}")
        lines.append(
            "- direct_target: "
            f"expected={item['expected_direct_collision_partner_type']}, "
            f"actual={item['actual_direct_collision_partner_type']['raw']}"
        )
        lines.append(
            "- observations: "
            f"frame={item['frame_observation_count']}, "
            f"accepted={item['agent_accepted_count']}, "
            f"uncertain={item['agent_uncertain_count']}, "
            f"applied={item['applied_count']}, confirmed={item['confirmed_count']}"
        )
        lines.append(f"- missing_expected_context: {', '.join(item['expected_context']['missing']) or 'none'}")
        lines.append(f"- promoted_pollution: {', '.join(item['pollution']['promoted_hits']) or 'none'}")
        lines.append(f"- uncertain_only_noise: {', '.join(item['pollution']['uncertain_only_hits']) or 'none'}")
        lines.append(f"- output_json_parse: {item['output_json_parse']['status']}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aggregate", required=True, help="Path to video_accuracy_batch aggregate.json")
    parser.add_argument("--reference-manifest", required=True, help="Path to local reference case manifest")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="JSON report output path")
    parser.add_argument("--markdown-output", help="Optional Markdown report output path")
    args = parser.parse_args()

    aggregate_path = Path(args.aggregate)
    reference_path = Path(args.reference_manifest)
    aggregate = load_json(aggregate_path)
    if not isinstance(aggregate, dict) or not isinstance(aggregate.get("samples"), list):
        raise SystemExit("aggregate must be a JSON object with a samples array")
    references = load_reference_cases(reference_path)
    audited = [
        audit_sample(sample, references.get(str(sample.get("name") or "")))
        for sample in aggregate["samples"]
        if isinstance(sample, dict)
    ]
    report = {
        "audit": "p2_2a_video_observation_audit",
        "aggregate": str(aggregate_path),
        "reference_manifest": str(reference_path),
        "summary": build_summary(audited),
        "samples": audited,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown_output:
        write_markdown(Path(args.markdown_output), report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
