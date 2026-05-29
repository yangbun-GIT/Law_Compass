import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = "logs/video_accuracy/manifest_preflight.json"
SENSITIVE_CASE_TOKENS = {
    "accident_negligence_rate",
    "accident_object",
    "expert_lawyer_opinion",
    "expert_opinion",
    "known_result",
    "reference_outcome",
    "expected_guidance_range",
    "evaluation_focus",
    "evaluation_only_not_agent_input",
    "traffic_accident_type",
}


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class ManifestValidationError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_existing_path(value: str, *, manifest_path: Path) -> Path:
    raw = Path(value).expanduser()
    candidates = [raw]
    if not raw.is_absolute():
        candidates.extend([REPO_ROOT / raw, manifest_path.parent / raw])
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve() if candidates else raw.resolve()


def as_samples(data: Any) -> list[dict[str, Any]]:
    samples = data.get("samples") if isinstance(data, dict) else data
    if not isinstance(samples, list):
        raise ManifestValidationError("manifest must be an object with samples array or a samples array")
    return samples


def string_map(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def validate_case_json(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    case = payload.get("case") if isinstance(payload, dict) and isinstance(payload.get("case"), dict) else payload
    if not isinstance(case, dict):
        raise ManifestValidationError(f"{path}: case_json must contain an object or a case object")
    if not str(case.get("description_text") or "").strip() and not string_map(case.get("structured_facts")):
        raise ManifestValidationError(f"{path}: case_json needs description_text or structured_facts")
    return case


def sample_issue(sample_name: str, code: str, message: str, severity: str = "error") -> dict[str, str]:
    return {
        "sample": sample_name,
        "severity": severity,
        "code": code,
        "message": message,
    }


def case_contains_reference_tokens(case_path: Path) -> list[str]:
    text = case_path.read_text(encoding="utf-8-sig", errors="replace").lower()
    return sorted(token for token in SENSITIVE_CASE_TOKENS if token.lower() in text)


def resolved_reference_label_path(reference: dict[str, Any], manifest_path: Path) -> Path | None:
    label_json = str(reference.get("label_json") or "").strip()
    if not label_json:
        return None
    return resolve_existing_path(label_json, manifest_path=manifest_path)


def validate_manifest(
    *,
    manifest_path: Path,
    min_samples: int,
    require_reference: bool,
    allow_missing_files: bool,
) -> dict[str, Any]:
    data = load_json(manifest_path)
    samples = as_samples(data)
    issues: list[dict[str, str]] = []
    names: Counter[str] = Counter()
    reference_count = 0
    require_frame_count = 0
    require_agent_fact_count = 0
    conflict_followup_count = 0
    held_followup_count = 0

    if len(samples) < min_samples:
        issues.append(sample_issue(
            "<manifest>",
            "too_few_samples",
            f"manifest has {len(samples)} samples, expected at least {min_samples}",
        ))

    for index, sample in enumerate(samples, start=1):
        if not isinstance(sample, dict):
            issues.append(sample_issue(f"sample_{index}", "sample_not_object", "sample must be an object"))
            continue

        name = str(sample.get("name") or f"sample_{index}").strip()
        names[name] += 1
        reference = sample.get("reference") if isinstance(sample.get("reference"), dict) else {}
        if reference:
            reference_count += 1
        elif require_reference:
            issues.append(sample_issue(name, "missing_reference", "sample.reference is required for evaluation manifest"))

        if reference and str(reference.get("purpose") or "") != "evaluation_only_not_agent_input":
            issues.append(sample_issue(
                name,
                "reference_purpose_not_isolated",
                "sample.reference.purpose must be evaluation_only_not_agent_input",
            ))
        reference_label_path = resolved_reference_label_path(reference, manifest_path)

        if sample.get("require_frame_observations"):
            require_frame_count += 1
        if sample.get("require_agent_video_facts"):
            require_agent_fact_count += 1
        if sample.get("exercise_conflict_followup"):
            conflict_followup_count += 1
        if sample.get("exercise_held_observation_followup"):
            held_followup_count += 1

        video_path = str(sample.get("video_path") or "").strip()
        if not video_path:
            issues.append(sample_issue(name, "missing_video_path", "sample.video_path is required"))
        else:
            resolved_video = resolve_existing_path(video_path, manifest_path=manifest_path)
            if not resolved_video.exists() and not allow_missing_files:
                issues.append(sample_issue(name, "video_not_found", "sample.video_path does not exist"))

        case_json = str(sample.get("case_json") or "").strip()
        if not case_json:
            issues.append(sample_issue(name, "missing_case_json", "sample.case_json is required for reproducible evaluation"))
        else:
            resolved_case = resolve_existing_path(case_json, manifest_path=manifest_path)
            if reference_label_path and resolved_case == reference_label_path:
                issues.append(sample_issue(
                    name,
                    "reference_label_used_as_case_json",
                    "sample.case_json must not point to sample.reference.label_json; labels are evaluation-only answer keys",
                ))
            if not resolved_case.exists():
                if not allow_missing_files:
                    issues.append(sample_issue(name, "case_json_not_found", "sample.case_json does not exist"))
            else:
                try:
                    validate_case_json(resolved_case)
                except (json.JSONDecodeError, OSError, ManifestValidationError) as exc:
                    issues.append(sample_issue(name, "invalid_case_json", str(exc)))
                leaked_tokens = case_contains_reference_tokens(resolved_case)
                if leaked_tokens:
                    issues.append(sample_issue(
                        name,
                        "reference_token_in_case_json",
                        f"case_json contains evaluation-only token(s): {', '.join(leaked_tokens)}",
                    ))

    duplicates = sorted(name for name, value in names.items() if value > 1)
    for name in duplicates:
        issues.append(sample_issue(name, "duplicate_sample_name", "sample.name must be unique"))

    error_count = sum(1 for issue in issues if issue.get("severity") == "error")
    warning_count = sum(1 for issue in issues if issue.get("severity") == "warning")
    return {
        "video_accuracy_manifest_preflight": "completed",
        "manifest": str(manifest_path),
        "sample_count": len(samples),
        "reference_count": reference_count,
        "require_frame_observations_count": require_frame_count,
        "require_agent_video_facts_count": require_agent_fact_count,
        "exercise_conflict_followup_count": conflict_followup_count,
        "exercise_held_observation_followup_count": held_followup_count,
        "issue_count": len(issues),
        "error_count": error_count,
        "warning_count": warning_count,
        "status": "passed" if error_count == 0 else "failed",
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preflight-check a video accuracy manifest before running costly OpenAI/video E2E batches.",
    )
    parser.add_argument("--manifest", required=True, help="Video accuracy manifest JSON.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="JSON output path.")
    parser.add_argument("--min-samples", type=int, default=1)
    parser.add_argument("--require-reference", action="store_true")
    parser.add_argument("--allow-missing-files", action="store_true", help="Validate manifest shape without requiring local video/case files.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    result = validate_manifest(
        manifest_path=manifest_path,
        min_samples=max(1, int(args.min_samples)),
        require_reference=bool(args.require_reference),
        allow_missing_files=bool(args.allow_missing_files),
    )
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "sample_count": result["sample_count"],
        "error_count": result["error_count"],
        "warning_count": result["warning_count"],
        "output": str(output_path),
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
