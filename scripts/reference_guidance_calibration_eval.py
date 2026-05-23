import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = "logs/video_accuracy/reference_guidance_calibration_eval.json"


CALIBRATION_RULES: dict[str, dict[str, Any]] = {
    "accident_1_centerline_obstacle_oncoming_secondary_rear": {
        "expected_my_range": (20, 40),
        "expected_other_range": (60, 80),
        "required_basis_terms": ("centerline", "oncoming", "secondary"),
        "required_missing_terms": ("인명피해", "신호"),
    },
    "accident_2_left_turn_signal_transition": {
        "expected_my_range": (70, 90),
        "expected_other_range": (10, 30),
        "required_basis_terms": ("signal", "cctv"),
        "required_missing_terms": ("신호", "상대"),
        "preferred_next_focus_terms": ("신호", "상대"),
    },
    "accident_4_stealth_stopped_vehicle_fatal": {
        "expected_my_range": (30, 50),
        "expected_other_range": (50, 70),
        "required_basis_terms": ("unlit", "speed", "avoidability", "criminal", "civil"),
        "required_limit_terms": ("확정", "참고", "바꿀 수"),
    },
}


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class CalibrationEvalError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    data = load_json(path)
    samples = data.get("samples") if isinstance(data, dict) else []
    return {
        str(sample.get("name") or ""): sample
        for sample in samples
        if isinstance(sample, dict) and sample.get("name")
    }


def load_batch_samples(path: Path) -> dict[str, dict[str, Any]]:
    data = load_json(path)
    samples = data.get("samples") if isinstance(data, dict) else []
    return {
        str(sample.get("name") or ""): sample
        for sample in samples
        if isinstance(sample, dict) and sample.get("name")
    }


def range_from_label(label: str) -> dict[str, tuple[int, int] | None]:
    my_match = re.search(r"내\s*책임\s*(\d{1,3})\s*~\s*(\d{1,3})%", label)
    other_match = re.search(r"상대\s*(\d{1,3})\s*~\s*(\d{1,3})%", label)
    return {
        "my": _range_tuple(my_match),
        "other": _range_tuple(other_match),
    }


def _range_tuple(match: re.Match[str] | None) -> tuple[int, int] | None:
    if not match:
        return None
    left, right = int(match.group(1)), int(match.group(2))
    return (min(left, right), max(left, right))


def overlaps(actual: tuple[int, int] | None, expected: tuple[int, int] | None) -> bool:
    if not actual or not expected:
        return False
    return max(actual[0], expected[0]) <= min(actual[1], expected[1])


def text_blob(values: Any) -> str:
    return json.dumps(values, ensure_ascii=False).lower()


def term_ready(blob: str, terms: tuple[str, ...]) -> tuple[bool, list[str]]:
    missing = [term for term in terms if term.lower() not in blob]
    return not missing, missing


def evaluate_sample(name: str, manifest_sample: dict[str, Any], batch_sample: dict[str, Any]) -> dict[str, Any]:
    rule = CALIBRATION_RULES.get(name, {})
    expert = batch_sample.get("expert_guidance") if isinstance(batch_sample.get("expert_guidance"), dict) else {}
    priority = batch_sample.get("missing_info_priority") if isinstance(batch_sample.get("missing_info_priority"), dict) else {}
    expected_reference = (manifest_sample.get("reference") or {}).get("expected_guidance_range")
    label = str(expert.get("fault_range_label") or "")
    actual_ranges = range_from_label(label)

    checks: list[dict[str, Any]] = []
    if rule.get("expected_my_range"):
        checks.append({
            "id": "my_fault_range_overlaps_reference_band",
            "passed": overlaps(actual_ranges["my"], tuple(rule["expected_my_range"])),
            "actual": actual_ranges["my"],
            "expected": tuple(rule["expected_my_range"]),
        })
    if rule.get("expected_other_range"):
        checks.append({
            "id": "other_fault_range_overlaps_reference_band",
            "passed": overlaps(actual_ranges["other"], tuple(rule["expected_other_range"])),
            "actual": actual_ranges["other"],
            "expected": tuple(rule["expected_other_range"]),
        })

    basis_ready, missing_basis_terms = term_ready(text_blob(expert.get("basis") or []), tuple(rule.get("required_basis_terms") or ()))
    if rule.get("required_basis_terms"):
        checks.append({
            "id": "basis_mentions_reference_focus_terms",
            "passed": basis_ready,
            "missing_terms": missing_basis_terms,
        })

    missing_ready, missing_missing_terms = term_ready(text_blob(expert.get("missing_items") or []), tuple(rule.get("required_missing_terms") or ()))
    if rule.get("required_missing_terms"):
        checks.append({
            "id": "missing_items_prompt_reference_decisive_facts",
            "passed": missing_ready,
            "missing_terms": missing_missing_terms,
        })

    limits_ready, missing_limit_terms = term_ready(text_blob(expert.get("legal_limits") or []), tuple(rule.get("required_limit_terms") or ()))
    if rule.get("required_limit_terms"):
        checks.append({
            "id": "limits_keep_guidance_non_final",
            "passed": limits_ready,
            "missing_terms": missing_limit_terms,
        })

    preferred_terms = tuple(rule.get("preferred_next_focus_terms") or ())
    if preferred_terms:
        top_label = str(priority.get("top_label") or "")
        top_ready = any(term.lower() in top_label.lower() for term in preferred_terms)
        checks.append({
            "id": "next_focus_prioritizes_decisive_user_question",
            "passed": top_ready,
            "actual": top_label,
            "expected_any_of": preferred_terms,
        })

    failed = [check for check in checks if not check["passed"]]
    return {
        "name": name,
        "pipeline_status": batch_sample.get("status") or "missing",
        "expected_guidance_range": expected_reference,
        "fault_range_label": label,
        "missing_info_top_label": priority.get("top_label"),
        "calibration_status": "calibrated_for_user_flow" if not failed else "needs_user_flow_calibration",
        "checks": checks,
        "failed_checks": failed,
    }


def aggregate(samples: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(sample["calibration_status"] for sample in samples)
    failed_ids = Counter(
        check["id"]
        for sample in samples
        for check in sample["failed_checks"]
    )
    recommendations: list[str] = []
    if failed_ids.get("next_focus_prioritizes_decisive_user_question"):
        recommendations.append("전문가 reference에서 결론을 바꾸는 신호/CCTV/정차 사유 질문이 인명피해 같은 후속 처리 질문보다 먼저 보이도록 입력 계약을 조정한다.")
    if failed_ids.get("my_fault_range_overlaps_reference_band") or failed_ids.get("other_fault_range_overlaps_reference_band"):
        recommendations.append("근거는 맞지만 예상 과실 범위가 reference band와 벗어난 샘플은 fault_ratio_analyst의 contextual rule을 조정한다.")
    if failed_ids.get("basis_mentions_reference_focus_terms"):
        recommendations.append("근거 제목과 reason이 쟁점 키워드를 담지 못한 경우 검색어 또는 static fallback evidence를 보강한다.")
    if failed_ids.get("missing_items_prompt_reference_decisive_facts"):
        recommendations.append("전문가 카드의 추가 확인 항목이 reference 쟁점과 어긋나면 input_requirements와 expert_guidance missing_facts를 함께 점검한다.")

    return {
        "reference_guidance_calibration_eval": "completed",
        "sample_count": len(samples),
        "calibrated_count": status_counts.get("calibrated_for_user_flow", 0),
        "needs_calibration_count": status_counts.get("needs_user_flow_calibration", 0),
        "status_counts": dict(sorted(status_counts.items())),
        "failed_check_counts": dict(sorted(failed_ids.items())),
        "recommendations": recommendations,
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate user-facing guidance calibration against lawyer-reference samples.")
    parser.add_argument("--manifest", required=True, help="JSON manifest with samples and reference evaluation metadata.")
    parser.add_argument("--batch-output", required=True, help="video_accuracy_batch aggregate.json.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    batch_path = Path(args.batch_output).expanduser().resolve()
    manifest = load_manifest(manifest_path)
    batch_samples = load_batch_samples(batch_path)

    evaluated = [
        evaluate_sample(name, sample, batch_samples.get(name, {"name": name, "status": "missing"}))
        for name, sample in manifest.items()
        if name in CALIBRATION_RULES
    ]
    if not evaluated:
        raise CalibrationEvalError("No samples matched calibration rules.")

    summary = aggregate(evaluated)
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CalibrationEvalError as exc:
        print(f"reference_guidance_calibration_eval=failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
