import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = "http://localhost"
DEFAULT_TIMEOUT_SEC = 240
DEFAULT_OUTPUT_DIR = "logs/video_accuracy"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class BatchError(RuntimeError):
    pass


def load_manifest(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    samples = data.get("samples") if isinstance(data, dict) else data
    if not isinstance(samples, list) or not samples:
        raise BatchError("manifest must contain a non-empty samples array")
    out: list[dict[str, Any]] = []
    for index, sample in enumerate(samples, start=1):
        if not isinstance(sample, dict):
            raise BatchError(f"sample #{index} must be an object")
        name = str(sample.get("name") or f"sample_{index}").strip()
        video_path = str(sample.get("video_path") or "").strip()
        if not video_path:
            raise BatchError(f"{name}: video_path is required")
        out.append({**sample, "name": safe_name(name), "display_name": name, "video_path": video_path})
    return out


def safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return safe or "sample"


def expected_args(flag: str, values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, dict):
        pairs = [f"{field}={value}" for field, value in values.items()]
    elif isinstance(values, list):
        pairs = [str(item) for item in values]
    else:
        raise BatchError(f"{flag} must be an object or an array")
    args: list[str] = []
    for pair in pairs:
        args.extend([flag, pair])
    return args


def run_sample(
    *,
    sample: dict[str, Any],
    repo_root: Path,
    output_dir: Path,
    base_url: str,
    timeout_sec: int,
    fail_on_mismatch: bool,
) -> dict[str, Any]:
    sample_output = output_dir / f"{sample['name']}.json"
    command = [
        sys.executable,
        str(repo_root / "scripts" / "video_agent_e2e.py"),
        "--base-url",
        base_url,
        "--video-path",
        str(Path(str(sample["video_path"])).expanduser()),
        "--timeout-sec",
        str(int(sample.get("timeout_sec") or timeout_sec)),
        "--output-json",
        str(sample_output),
    ]
    case_json = str(sample.get("case_json") or "").strip()
    if case_json:
        command.extend(["--case-json", case_json])
    if sample.get("require_frame_observations"):
        command.append("--require-frame-observations")
    if sample.get("require_agent_video_facts"):
        command.append("--require-agent-video-facts")
    if sample.get("exercise_held_observation_followup"):
        command.append("--exercise-held-observation-followup")
    if not fail_on_mismatch:
        command.append("--allow-accuracy-mismatch")
    command.extend(expected_args("--expect-frame-observation", sample.get("expect_frame_observation")))
    command.extend(expected_args("--expect-agent-fact", sample.get("expect_agent_fact")))

    completed = subprocess.run(command, cwd=repo_root, text=True, encoding="utf-8", errors="replace", capture_output=True)
    result = {
        "name": sample["display_name"],
        "status": "failed" if completed.returncode else "passed",
        "returncode": completed.returncode,
        "output_json": str(sample_output),
    }
    reference = sample.get("reference")
    if isinstance(reference, dict):
        result["reference"] = reference
    if completed.returncode:
        result["stderr"] = completed.stderr[-4000:]
        result["stdout"] = completed.stdout[-4000:]
        return result

    payload = json.loads(sample_output.read_text(encoding="utf-8"))
    metrics = payload.get("video_accuracy_metrics") if isinstance(payload.get("video_accuracy_metrics"), dict) else {}
    expectations = payload.get("accuracy_expectations") if isinstance(payload.get("accuracy_expectations"), dict) else {}
    expert_card = payload.get("expert_guidance_card") if isinstance(payload.get("expert_guidance_card"), dict) else {}
    field_metrics = field_metrics_from_payload(payload)
    result.update({
        "provider": metrics.get("provider"),
        "model": metrics.get("model"),
        "selected_frame_count": metrics.get("selected_frame_count"),
        "frame_observation_count": metrics.get("frame_observation_count"),
        "agent_accepted_count": metrics.get("agent_accepted_count"),
        "agent_uncertain_count": metrics.get("agent_uncertain_count"),
        "applied_count": metrics.get("applied_count"),
        "confirmed_count": metrics.get("confirmed_count"),
        "conflict_count": metrics.get("conflict_count"),
        "accuracy_checked_count": expectations.get("checked_count"),
        "accuracy_passed_count": expectations.get("passed_count"),
        "accuracy_failed_count": expectations.get("failed_count"),
        "expert_guidance": expert_guidance_metrics(expert_card),
        "field_metrics": field_metrics,
    })
    if expectations.get("failed_count"):
        result["status"] = "mismatch"
    return result


def expert_guidance_metrics(card: dict[str, Any]) -> dict[str, Any]:
    if not card:
        return {"present": False}
    return {
        "present": True,
        "status_label": card.get("status_label"),
        "fault_range_label": card.get("fault_range_label"),
        "legal_point_count": int(card.get("legal_point_count") or 0),
        "legal_limit_count": int(card.get("legal_limit_count") or 0),
        "insurance_step_count": int(card.get("insurance_step_count") or 0),
        "insurance_document_count": int(card.get("insurance_document_count") or 0),
        "basis_count": int(card.get("basis_count") or 0),
        "missing_item_count": int(card.get("missing_item_count") or 0),
    }


def field_metrics_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    frame = payload.get("frame_analysis") if isinstance(payload.get("frame_analysis"), dict) else {}
    agent = payload.get("agent_video_input") if isinstance(payload.get("agent_video_input"), dict) else {}
    expectations = payload.get("accuracy_expectations") if isinstance(payload.get("accuracy_expectations"), dict) else {}
    observations = frame.get("observations") if isinstance(frame.get("observations"), list) else []
    fact_patch = agent.get("fact_patch") if isinstance(agent.get("fact_patch"), dict) else {}
    applied = set(str(item) for item in (agent.get("applied_video_fields") or []) if item is not None)
    confirmed = set(str(item) for item in (agent.get("confirmed_fields") or []) if item is not None)
    conflicts = agent.get("conflicts") if isinstance(agent.get("conflicts"), list) else []
    conflict_fields = set(str(item.get("field")) for item in conflicts if isinstance(item, dict) and item.get("field"))
    expectation_by_field: dict[str, list[dict[str, Any]]] = {}
    for check in expectations.get("checks") or []:
        if not isinstance(check, dict) or not check.get("field"):
            continue
        expectation_by_field.setdefault(str(check["field"]), []).append(check)

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in observations:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or "")
        if not field:
            continue
        seen.add(field)
        rows.append(field_metric_row(
            field=field,
            value=item.get("value"),
            confidence=item.get("confidence"),
            frame_ref_count=len(item.get("frame_refs") or []) if isinstance(item.get("frame_refs"), list) else 0,
            from_observation=True,
            fact_patch=fact_patch,
            applied=applied,
            confirmed=confirmed,
            conflict_fields=conflict_fields,
            checks=expectation_by_field.get(field, []),
        ))
    for field, value in fact_patch.items():
        if str(field) in seen:
            continue
        rows.append(field_metric_row(
            field=str(field),
            value=value,
            confidence=None,
            frame_ref_count=0,
            from_observation=False,
            fact_patch=fact_patch,
            applied=applied,
            confirmed=confirmed,
            conflict_fields=conflict_fields,
            checks=expectation_by_field.get(str(field), []),
        ))
    return rows


def field_metric_row(
    *,
    field: str,
    value: Any,
    confidence: Any,
    frame_ref_count: int,
    from_observation: bool,
    fact_patch: dict[str, Any],
    applied: set[str],
    confirmed: set[str],
    conflict_fields: set[str],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "field": field,
        "value": value,
        "confidence": confidence,
        "frame_ref_count": frame_ref_count,
        "from_observation": from_observation,
        "in_fact_patch": field in fact_patch,
        "applied": field in applied,
        "confirmed": field in confirmed,
        "conflict": field in conflict_fields,
        "expectation_checked_count": len(checks),
        "expectation_passed_count": sum(1 for item in checks if item.get("passed")),
        "expectation_failed_count": sum(1 for item in checks if not item.get("passed")),
    }


def aggregate(samples: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(samples)
    passed = sum(1 for item in samples if item.get("status") == "passed")
    mismatched = sum(1 for item in samples if item.get("status") == "mismatch")
    failed = sum(1 for item in samples if item.get("status") == "failed")
    checked = sum(int(item.get("accuracy_checked_count") or 0) for item in samples)
    accuracy_passed = sum(int(item.get("accuracy_passed_count") or 0) for item in samples)
    field_summary = aggregate_field_metrics(samples)
    recommendations = calibration_recommendations(samples, field_summary)
    expert_summary = aggregate_expert_guidance(samples)
    return {
        "video_accuracy_batch": "completed" if failed == 0 else "failed",
        "sample_count": total,
        "passed_count": passed,
        "mismatch_count": mismatched,
        "failed_count": failed,
        "accuracy_checked_count": checked,
        "accuracy_passed_count": accuracy_passed,
        "accuracy_failed_count": max(0, checked - accuracy_passed),
        "calibration_readiness": calibration_readiness(total, max(0, checked - accuracy_passed), failed),
        "field_summary": field_summary,
        "expert_guidance_summary": expert_summary,
        "recommendations": recommendations,
        "samples": samples,
    }


def aggregate_expert_guidance(samples: list[dict[str, Any]]) -> dict[str, Any]:
    present_samples = [
        sample.get("expert_guidance")
        for sample in samples
        if isinstance(sample.get("expert_guidance"), dict) and sample["expert_guidance"].get("present")
    ]
    return {
        "present_count": len(present_samples),
        "missing_count": max(0, len(samples) - len(present_samples)),
        "with_fault_range_count": sum(1 for item in present_samples if item.get("fault_range_label")),
        "with_legal_points_count": sum(1 for item in present_samples if int(item.get("legal_point_count") or 0) > 0),
        "with_insurance_steps_count": sum(1 for item in present_samples if int(item.get("insurance_step_count") or 0) > 0),
        "with_basis_count": sum(1 for item in present_samples if int(item.get("basis_count") or 0) > 0),
        "with_missing_items_count": sum(1 for item in present_samples if int(item.get("missing_item_count") or 0) > 0),
    }


def aggregate_field_metrics(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_field: dict[str, dict[str, Any]] = {}
    for sample in samples:
        for item in sample.get("field_metrics") or []:
            if not isinstance(item, dict) or not item.get("field"):
                continue
            field = str(item["field"])
            bucket = by_field.setdefault(field, {
                "field": field,
                "observation_count": 0,
                "fact_patch_count": 0,
                "applied_count": 0,
                "confirmed_count": 0,
                "conflict_count": 0,
                "expectation_checked_count": 0,
                "expectation_passed_count": 0,
                "expectation_failed_count": 0,
                "confidence_values": [],
                "frame_ref_counts": [],
                "values": {},
            })
            bucket["observation_count"] += 1 if item.get("from_observation") else 0
            bucket["fact_patch_count"] += 1 if item.get("in_fact_patch") else 0
            bucket["applied_count"] += 1 if item.get("applied") else 0
            bucket["confirmed_count"] += 1 if item.get("confirmed") else 0
            bucket["conflict_count"] += 1 if item.get("conflict") else 0
            bucket["expectation_checked_count"] += int(item.get("expectation_checked_count") or 0)
            bucket["expectation_passed_count"] += int(item.get("expectation_passed_count") or 0)
            bucket["expectation_failed_count"] += int(item.get("expectation_failed_count") or 0)
            if isinstance(item.get("confidence"), (int, float)):
                bucket["confidence_values"].append(float(item["confidence"]))
            if isinstance(item.get("frame_ref_count"), int):
                bucket["frame_ref_counts"].append(int(item["frame_ref_count"]))
            value_key = str(item.get("value"))
            bucket["values"][value_key] = bucket["values"].get(value_key, 0) + 1

    summary: list[dict[str, Any]] = []
    for field in sorted(by_field):
        bucket = by_field[field]
        confidence_values = bucket.pop("confidence_values")
        frame_ref_counts = bucket.pop("frame_ref_counts")
        bucket["avg_confidence"] = round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else None
        bucket["min_confidence"] = round(min(confidence_values), 3) if confidence_values else None
        bucket["max_confidence"] = round(max(confidence_values), 3) if confidence_values else None
        bucket["avg_frame_refs"] = round(sum(frame_ref_counts) / len(frame_ref_counts), 2) if frame_ref_counts else 0
        checked = int(bucket["expectation_checked_count"] or 0)
        passed = int(bucket["expectation_passed_count"] or 0)
        bucket["expectation_pass_rate"] = round(passed / checked, 3) if checked else None
        summary.append(bucket)
    return summary


def calibration_readiness(sample_count: int, accuracy_failed_count: int, failed_count: int) -> str:
    if failed_count:
        return "pipeline_failures_first"
    if sample_count < 3:
        return "collect_more_samples"
    if accuracy_failed_count:
        return "inspect_mismatches_before_threshold_change"
    return "ready_for_threshold_review"


def calibration_recommendations(samples: list[dict[str, Any]], field_summary: list[dict[str, Any]]) -> list[dict[str, str]]:
    recommendations: list[dict[str, str]] = []
    if len(samples) < 3:
        recommendations.append({
            "type": "collect_more_samples",
            "message": "Threshold 조정 전 최소 3개 이상의 실제 사고 영상 샘플을 같은 manifest로 측정하세요.",
        })
    failed_samples = [sample for sample in samples if sample.get("status") == "failed"]
    if failed_samples:
        recommendations.append({
            "type": "fix_pipeline_failures",
            "message": f"E2E 자체가 실패한 샘플 {len(failed_samples)}개를 먼저 확인하세요.",
        })
    for field in field_summary:
        checked = int(field.get("expectation_checked_count") or 0)
        failed = int(field.get("expectation_failed_count") or 0)
        conflicts = int(field.get("conflict_count") or 0)
        observations = int(field.get("observation_count") or 0)
        fact_patch = int(field.get("fact_patch_count") or 0)
        if checked and failed:
            recommendations.append({
                "type": "inspect_field_mismatch",
                "message": f"{field['field']} 기대값 실패 {failed}/{checked}건을 확인한 뒤 prompt 또는 threshold를 조정하세요.",
            })
        if observations >= 3 and fact_patch == 0:
            recommendations.append({
                "type": "review_field_threshold",
                "message": f"{field['field']} 관찰값은 {observations}건이지만 fact_patch 반영이 없습니다. confidence/frame_ref 기준이 과도한지 검토하세요.",
            })
        if conflicts:
            recommendations.append({
                "type": "review_conflict_gate",
                "message": f"{field['field']} 충돌 {conflicts}건이 있습니다. 사용자 입력 우선/영상 우선 정책과 보완 질문 흐름을 확인하세요.",
            })
    if not recommendations:
        recommendations.append({
            "type": "no_threshold_change",
            "message": "현재 배치 기준에서는 즉시 조정할 위험 신호가 없습니다. threshold 변경 전 결과 화면과 원본 샘플을 최종 확인하세요.",
        })
    return recommendations


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multiple video_agent_e2e calibration samples and aggregate metrics.")
    parser.add_argument("--manifest", required=True, help="JSON file with a samples array.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--fail-on-mismatch", action="store_true", help="Fail each sample when expected values do not match.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = Path(args.manifest).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    samples = load_manifest(manifest_path)
    results = [
        run_sample(
            sample=sample,
            repo_root=repo_root,
            output_dir=output_dir,
            base_url=args.base_url,
            timeout_sec=args.timeout_sec,
            fail_on_mismatch=args.fail_on_mismatch,
        )
        for sample in samples
    ]
    summary = aggregate(results)
    summary_path = output_dir / "aggregate.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["failed_count"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BatchError as exc:
        print(f"video_accuracy_batch=failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
