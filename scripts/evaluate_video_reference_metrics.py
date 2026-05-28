"""Evaluate video/reference accuracy metrics from a batch aggregate.

This script does not call OpenAI or download media. It compares safe reference
case expectations against an already produced batch aggregate and produces
repeatable metrics for accident-target accuracy, pollution, zero observations,
evidence fit, and conditional-branch coverage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = "logs/video_accuracy/video_reference_metrics.json"
TARGET_FIELDS = [
    "direct_collision_partner_type",
    "collision_partner_type",
    "primary_collision_target",
    "accident_party_type",
]
PARTY_BY_DIRECT_TARGET = {
    "vehicle": {"car_vs_car", "vehicle", "차대차"},
    "pedestrian": {"car_vs_person", "vehicle_vs_pedestrian", "pedestrian", "차대사람", "차대보행자"},
    "bicycle": {"car_vs_bicycle", "vehicle_vs_bicycle", "bicycle", "차대자전거"},
    "object": {"vehicle_vs_object", "object", "시설물", "물체"},
}
CONTEXT_ALIASES = {
    "centerline_context": ["centerline", "중앙선"],
    "parked_vehicle_obstacle": ["parked", "parking", "주차", "장애물"],
    "oncoming_vehicle": ["oncoming", "마주", "대향"],
    "secondary_rear_collision": ["secondary", "2차", "후속", "rear"],
    "intersection_context": ["intersection", "교차로"],
    "ego_signal_timing": ["signal", "신호", "황색", "적색", "녹색"],
    "opponent_signal_unknown": ["opponent signal", "상대 신호", "신호"],
    "vehicle_visible": ["vehicle", "차량"],
    "pedestrian_visible": ["pedestrian", "보행자", "사람"],
}


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9가-힣]+", "_", str(value or "").lower()).strip("_")


def text_blob(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).lower()


def load_reference_cases(path: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(path)
    cases = payload.get("cases") if isinstance(payload, dict) else []
    out: dict[str, dict[str, Any]] = {}
    for case in cases or []:
        if isinstance(case, dict) and case.get("id"):
            out[str(case["id"])] = case
    return out


def load_batch_samples(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    if isinstance(payload, dict) and isinstance(payload.get("samples"), list):
        return [item for item in payload["samples"] if isinstance(item, dict)]
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    raise ValueError("batch aggregate must contain a samples array")


def reference_id_for_sample(sample: dict[str, Any]) -> str:
    for key in ("reference_case_id", "reference_id", "case_id"):
        if sample.get(key):
            return str(sample[key])
    reference = sample.get("reference") if isinstance(sample.get("reference"), dict) else {}
    for key in ("reference_case_id", "reference_id", "case_id", "id"):
        if reference.get(key):
            return str(reference[key])
    return str(sample.get("name") or "")


def value_from_field_metrics(sample: dict[str, Any], field_names: list[str]) -> Any:
    field_set = set(field_names)
    for item in sample.get("field_metrics") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("field") or "") in field_set and item.get("value") is not None:
            return item.get("value")
    return None


def nested_values(payload: Any, key: str) -> list[Any]:
    values: list[Any] = []
    if isinstance(payload, dict):
        for current_key, current_value in payload.items():
            if current_key == key:
                values.append(current_value)
            values.extend(nested_values(current_value, key))
    elif isinstance(payload, list):
        for item in payload:
            values.extend(nested_values(item, key))
    return values


def actual_direct_target(sample: dict[str, Any]) -> str:
    value = value_from_field_metrics(sample, ["direct_collision_partner_type", "collision_partner_type", "primary_collision_target"])
    if value is None:
        for key in ("direct_collision_partner_type", "collision_partner_type", "primary_collision_target"):
            values = nested_values(sample, key)
            if values:
                value = values[0]
                break
    normalized = normalize(value)
    if normalized in {"vehicle", "car", "차량", "차"} or "vehicle" in normalized:
        return "vehicle"
    if normalized in {"pedestrian", "person", "보행자", "사람"} or "pedestrian" in normalized:
        return "pedestrian"
    if normalized in {"bicycle", "bike", "자전거"} or "bicycle" in normalized:
        return "bicycle"
    if normalized in {"object", "facility", "물체", "시설물"} or "object" in normalized:
        return "object"
    return "unknown"


def actual_party_type(sample: dict[str, Any]) -> str:
    value = value_from_field_metrics(sample, ["accident_party_type"])
    if value is None:
        values = nested_values(sample, "accident_party_type")
        value = values[0] if values else None
    return normalize(value)


def evidence_blob(sample: dict[str, Any]) -> str:
    expert = sample.get("expert_guidance") if isinstance(sample.get("expert_guidance"), dict) else {}
    basis = expert.get("basis") if isinstance(expert.get("basis"), list) else []
    legal_points = expert.get("legal_points") if isinstance(expert.get("legal_points"), list) else []
    legal_limits = expert.get("legal_limits") if isinstance(expert.get("legal_limits"), list) else []
    return text_blob({"basis": basis, "legal_points": legal_points, "legal_limits": legal_limits})


def conditional_blob(sample: dict[str, Any]) -> str:
    return text_blob({
        "conditional_outcome_card": sample.get("conditional_outcome_card"),
        "expert_guidance": sample.get("expert_guidance"),
        "missing_info_priority": sample.get("missing_info_priority"),
    })


def contains_any(blob: str, needles: list[str]) -> bool:
    return any(str(needle).lower() in blob for needle in needles if str(needle).strip())


def forbidden_hit(blob: str, forbidden: list[str]) -> list[str]:
    hits: list[str] = []
    for item in forbidden:
        normalized = str(item or "").strip()
        if not normalized:
            continue
        alternatives = {normalized.lower(), normalized.replace("_", " ").lower()}
        if any(alt and alt in blob for alt in alternatives):
            hits.append(normalized)
    return hits


def context_hit(blob: str, contexts: list[str]) -> tuple[list[str], list[str]]:
    matched: list[str] = []
    missing: list[str] = []
    for context in contexts:
        aliases = CONTEXT_ALIASES.get(str(context), [str(context).replace("_", " ")])
        if contains_any(blob, aliases):
            matched.append(str(context))
        else:
            missing.append(str(context))
    return matched, missing


def score_sample(sample: dict[str, Any], reference: dict[str, Any] | None) -> dict[str, Any]:
    expectations = reference.get("reference_expectations") if isinstance(reference, dict) else {}
    if not isinstance(expectations, dict):
        expectations = {}
    expected_direct = str(expectations.get("direct_collision_partner_type") or "unknown")
    actual_direct = actual_direct_target(sample)
    actual_party = actual_party_type(sample)
    expected_party_values = PARTY_BY_DIRECT_TARGET.get(expected_direct, set())
    direct_scored = expected_direct != "unknown"
    direct_passed = direct_scored and actual_direct == expected_direct
    party_scored = bool(expected_party_values)
    party_passed = party_scored and (actual_party in {normalize(item) for item in expected_party_values} or actual_direct == expected_direct)

    blob = text_blob(sample)
    basis_blob = evidence_blob(sample)
    forbidden = [str(item) for item in expectations.get("must_not_promote") or []]
    pollution_hits = forbidden_hit(blob, forbidden)
    evidence_pollution_hits = forbidden_hit(basis_blob, forbidden)
    expected_context = [str(item) for item in expectations.get("expected_context") or []]
    matched_context, missing_context = context_hit(basis_blob, expected_context)

    frame_count = int(sample.get("frame_observation_count") or 0)
    ambiguous_branches = expectations.get("ambiguous_branches") if isinstance(expectations.get("ambiguous_branches"), list) else []
    conditional_text = conditional_blob(sample)
    conditional_required = bool(ambiguous_branches)
    conditional_present = bool(sample.get("conditional_outcome_card")) or contains_any(conditional_text, ["조건", "달라지는 판단", "경우", "분기"])

    evidence_mismatch = bool(evidence_pollution_hits) or (bool(expected_context) and not matched_context)
    return {
        "name": sample.get("name"),
        "reference_case_id": reference.get("id") if isinstance(reference, dict) else None,
        "matched_reference": bool(reference),
        "expected_direct_collision_partner_type": expected_direct,
        "actual_direct_collision_partner_type": actual_direct,
        "direct_collision_target_scored": direct_scored,
        "direct_collision_target_passed": direct_passed,
        "actual_accident_party_type": actual_party or "unknown",
        "accident_party_scored": party_scored,
        "accident_party_passed": party_passed,
        "frame_observation_count": frame_count,
        "zero_observations": frame_count == 0,
        "context_pollution_hits": pollution_hits,
        "context_pollution": bool(pollution_hits),
        "evidence_pollution_hits": evidence_pollution_hits,
        "matched_expected_context": matched_context,
        "missing_expected_context": missing_context,
        "evidence_mismatch": evidence_mismatch,
        "conditional_branch_required": conditional_required,
        "conditional_branch_present": conditional_present,
        "conditional_branch_passed": (not conditional_required) or conditional_present,
        "status": sample.get("status"),
    }


def rate(passed: int, total: int) -> float | None:
    return round(passed / total, 3) if total else None


def count_true(samples: list[dict[str, Any]], key: str) -> int:
    return sum(1 for item in samples if item.get(key))


def metric_status(summary: dict[str, Any], thresholds: dict[str, float]) -> str:
    failures: list[str] = []
    for key, threshold in thresholds.items():
        value = summary.get(key)
        if value is None:
            continue
        if key.endswith("_max"):
            metric_name = key[:-4]
            if summary.get(metric_name) is not None and float(summary[metric_name]) > threshold:
                failures.append(metric_name)
        elif float(value) < threshold:
            failures.append(key)
    if summary.get("reference_matched_rate") is not None and summary["reference_matched_rate"] < 1:
        failures.append("reference_matched_rate")
    return "needs_attention" if failures else "passed"


def aggregate(scored: list[dict[str, Any]], thresholds: dict[str, float]) -> dict[str, Any]:
    total = len(scored)
    reference_matched = count_true(scored, "matched_reference")
    direct_scored = count_true(scored, "direct_collision_target_scored")
    direct_passed = count_true(scored, "direct_collision_target_passed")
    party_scored = count_true(scored, "accident_party_scored")
    party_passed = count_true(scored, "accident_party_passed")
    conditional_required = count_true(scored, "conditional_branch_required")
    conditional_passed = sum(1 for item in scored if item.get("conditional_branch_required") and item.get("conditional_branch_present"))
    zero_observations = count_true(scored, "zero_observations")
    context_pollution = count_true(scored, "context_pollution")
    evidence_mismatch = count_true(scored, "evidence_mismatch")
    summary = {
        "sample_count": total,
        "reference_matched_count": reference_matched,
        "reference_matched_rate": rate(reference_matched, total),
        "direct_collision_target_scored_count": direct_scored,
        "direct_collision_target_passed_count": direct_passed,
        "direct_collision_target_accuracy": rate(direct_passed, direct_scored),
        "accident_party_scored_count": party_scored,
        "accident_party_passed_count": party_passed,
        "accident_party_accuracy": rate(party_passed, party_scored),
        "context_pollution_count": context_pollution,
        "context_pollution_rate": rate(context_pollution, total),
        "zero_observation_count": zero_observations,
        "zero_observation_rate": rate(zero_observations, total),
        "evidence_mismatch_count": evidence_mismatch,
        "evidence_mismatch_rate": rate(evidence_mismatch, total),
        "conditional_branch_required_count": conditional_required,
        "conditional_branch_passed_count": conditional_passed,
        "conditional_branch_coverage": rate(conditional_passed, conditional_required),
    }
    summary["status"] = metric_status({
        **summary,
        "context_pollution_rate_max": summary["context_pollution_rate"],
        "zero_observation_rate_max": summary["zero_observation_rate"],
        "evidence_mismatch_rate_max": summary["evidence_mismatch_rate"],
    }, thresholds)
    return summary


def build_thresholds(args: argparse.Namespace) -> dict[str, float]:
    return {
        "direct_collision_target_accuracy": float(args.min_direct_target_accuracy),
        "accident_party_accuracy": float(args.min_accident_party_accuracy),
        "context_pollution_rate_max": float(args.max_context_pollution_rate),
        "zero_observation_rate_max": float(args.max_zero_observation_rate),
        "evidence_mismatch_rate_max": float(args.max_evidence_mismatch_rate),
        "conditional_branch_coverage": float(args.min_conditional_branch_coverage),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate fixed video/reference accuracy metrics.")
    parser.add_argument("--reference-manifest", required=True, help="Reference case manifest JSON.")
    parser.add_argument("--batch-aggregate", required=True, help="video_accuracy_batch aggregate JSON.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--min-direct-target-accuracy", type=float, default=0.8)
    parser.add_argument("--min-accident-party-accuracy", type=float, default=0.8)
    parser.add_argument("--max-context-pollution-rate", type=float, default=0.0)
    parser.add_argument("--max-zero-observation-rate", type=float, default=0.2)
    parser.add_argument("--max-evidence-mismatch-rate", type=float, default=0.2)
    parser.add_argument("--min-conditional-branch-coverage", type=float, default=0.8)
    parser.add_argument("--fail-on-threshold", action="store_true")
    args = parser.parse_args()

    reference_path = Path(args.reference_manifest).expanduser().resolve()
    aggregate_path = Path(args.batch_aggregate).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    references = load_reference_cases(reference_path)
    samples = load_batch_samples(aggregate_path)
    scored = []
    for sample in samples:
        ref_id = reference_id_for_sample(sample)
        reference = references.get(ref_id) or references.get(str(sample.get("name") or ""))
        scored.append(score_sample(sample, reference))
    thresholds = build_thresholds(args)
    summary = aggregate(scored, thresholds)
    result = {
        "video_reference_metrics": "completed",
        "reference_manifest": str(reference_path),
        "batch_aggregate": str(aggregate_path),
        "thresholds": thresholds,
        "summary": summary,
        "samples": scored,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": summary["status"],
        "sample_count": summary["sample_count"],
        "direct_collision_target_accuracy": summary["direct_collision_target_accuracy"],
        "context_pollution_rate": summary["context_pollution_rate"],
        "zero_observation_rate": summary["zero_observation_rate"],
        "evidence_mismatch_rate": summary["evidence_mismatch_rate"],
        "conditional_branch_coverage": summary["conditional_branch_coverage"],
        "output": str(output_path),
    }, ensure_ascii=False, indent=2))
    return 1 if args.fail_on_threshold and summary["status"] != "passed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
