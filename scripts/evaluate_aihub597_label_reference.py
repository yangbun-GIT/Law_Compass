"""Evaluate AI-Hub 597 label manifests as LawCompass reference candidates.

This script does not call OpenAI, run YOLO, or download media. It checks whether
the AI-Hub label manifest is useful as a broad reference set for video-fact
extraction evaluation, then writes a small balanced candidate list for later raw
video validation.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = ".local/aihub597_video_label_manifest.json"
DEFAULT_OUTPUT = ".local/aihub597_label_reference_eval.json"
DEFAULT_REQUIRED_TARGETS = ("vehicle", "pedestrian", "motorcycle", "bicycle")


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def direct_target(case: dict[str, Any]) -> str:
    expectations = case.get("reference_expectations")
    if not isinstance(expectations, dict):
        return "unknown"
    return str(expectations.get("direct_collision_partner_type") or "unknown")


def dataset_ref(case: dict[str, Any]) -> dict[str, Any]:
    value = case.get("dataset_ref")
    return value if isinstance(value, dict) else {}


def expected_context(case: dict[str, Any]) -> list[str]:
    expectations = case.get("reference_expectations")
    if not isinstance(expectations, dict):
        return []
    value = expectations.get("expected_context")
    return [str(item) for item in value] if isinstance(value, list) else []


def must_not_promote(case: dict[str, Any]) -> list[str]:
    expectations = case.get("reference_expectations")
    if not isinstance(expectations, dict):
        return []
    value = expectations.get("must_not_promote")
    return [str(item) for item in value] if isinstance(value, list) else []


def balance_cases(cases: list[dict[str, Any]], per_target: int, targets: tuple[str, ...]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        target = direct_target(case)
        if target in targets:
            buckets[target].append(case)
    selected: list[dict[str, Any]] = []
    for target in targets:
        selected.extend(buckets[target][:per_target])
    return selected


def case_summary(case: dict[str, Any]) -> dict[str, Any]:
    ref = dataset_ref(case)
    return {
        "id": case.get("id"),
        "title": case.get("title"),
        "direct_collision_partner_type": direct_target(case),
        "split": ref.get("split"),
        "label_file_key": ref.get("file_key"),
        "dataset_key": ref.get("dataset_key"),
        "expected_context": expected_context(case),
    }


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = Path(args.manifest).expanduser().resolve()
    payload = load_json(manifest_path)
    cases = payload.get("cases") if isinstance(payload, dict) else []
    if not isinstance(cases, list):
        raise ValueError("manifest.cases must be an array")

    required_targets = tuple(str(item).strip() for item in args.required_targets.split(",") if str(item).strip())
    target_counts = Counter(direct_target(case) for case in cases if isinstance(case, dict))
    split_counts = Counter(str(dataset_ref(case).get("split") or "unknown") for case in cases if isinstance(case, dict))
    known_count = sum(count for target, count in target_counts.items() if target != "unknown")
    guard_count = sum(1 for case in cases if isinstance(case, dict) and must_not_promote(case))
    context_count = sum(1 for case in cases if isinstance(case, dict) and expected_context(case))
    known_rate = round(known_count / len(cases), 4) if cases else 0.0
    guard_rate = round(guard_count / len(cases), 4) if cases else 0.0
    context_rate = round(context_count / len(cases), 4) if cases else 0.0
    missing_targets = [target for target in required_targets if target_counts.get(target, 0) == 0]

    balanced = balance_cases([case for case in cases if isinstance(case, dict)], args.per_target, required_targets)
    failure_axes: list[str] = []
    if len(cases) < args.min_sample_count:
        failure_axes.append("sample_count_below_threshold")
    if known_rate < args.min_known_target_rate:
        failure_axes.append("known_direct_target_rate_below_threshold")
    if guard_rate < args.min_guard_rate:
        failure_axes.append("pollution_guard_coverage_below_threshold")
    if context_rate < args.min_context_rate:
        failure_axes.append("expected_context_coverage_below_threshold")
    if missing_targets:
        failure_axes.append("required_direct_target_type_missing")
    if len(balanced) < args.min_balanced_sample_count:
        failure_axes.append("balanced_candidate_count_below_threshold")

    status = "needs_attention" if failure_axes else "passed"
    return {
        "aihub597_label_reference_eval": "completed",
        "manifest": str(manifest_path),
        "mode": "label_manifest_static",
        "summary": {
            "status": status,
            "case_count": len(cases),
            "target_counts": dict(target_counts),
            "split_counts": dict(split_counts),
            "known_direct_target_rate": known_rate,
            "pollution_guard_coverage": guard_rate,
            "expected_context_coverage": context_rate,
            "required_targets": list(required_targets),
            "missing_required_targets": missing_targets,
            "balanced_candidate_count": len(balanced),
            "failure_axes": failure_axes,
        },
        "thresholds": {
            "min_sample_count": args.min_sample_count,
            "min_known_target_rate": args.min_known_target_rate,
            "min_guard_rate": args.min_guard_rate,
            "min_context_rate": args.min_context_rate,
            "min_balanced_sample_count": args.min_balanced_sample_count,
            "per_target": args.per_target,
        },
        "balanced_raw_video_validation_candidates": [case_summary(case) for case in balanced],
        "raw_video_validation": {
            "openai_yolo_alignment_status": "requires_raw_video_samples",
            "reason": "AI-Hub labels can validate reference coverage, but OpenAI+YOLO frame extraction can only be compared after the matching source videos are available locally.",
            "next_action": "Download a small balanced TS/VS source-video subset matching the selected label cases, then run the video pipeline and compare outputs against this manifest.",
            "git_policy": "Do not commit raw videos, AI-Hub labels, generated manifests, or API keys.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate AI-Hub 597 label manifest readiness.")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--required-targets", default=",".join(DEFAULT_REQUIRED_TARGETS))
    parser.add_argument("--per-target", type=int, default=50)
    parser.add_argument("--min-sample-count", type=int, default=200)
    parser.add_argument("--min-balanced-sample-count", type=int, default=200)
    parser.add_argument("--min-known-target-rate", type=float, default=0.95)
    parser.add_argument("--min-guard-rate", type=float, default=1.0)
    parser.add_argument("--min-context-rate", type=float, default=0.95)
    parser.add_argument("--fail-on-threshold", action="store_true")
    args = parser.parse_args()

    result = build_result(args)
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = result["summary"]
    print(json.dumps({
        "status": summary["status"],
        "case_count": summary["case_count"],
        "target_counts": summary["target_counts"],
        "balanced_candidate_count": summary["balanced_candidate_count"],
        "failure_axes": summary["failure_axes"],
        "output": str(output_path),
    }, ensure_ascii=False, indent=2))
    return 1 if args.fail_on_threshold and summary["status"] != "passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
