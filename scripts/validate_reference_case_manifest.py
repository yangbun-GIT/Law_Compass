"""Validate external video reference-case manifests before evaluation.

The manifest is allowed to contain links, short manual summaries, and
calibration notes. It must not become an Agent input payload, a raw-media
commit path, or a hidden answer key.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = "logs/video_accuracy/reference_case_manifest_preflight.json"
SOURCE_TYPES = {"local_user_provided", "aihub_sample", "public_reference_link", "official_evidence"}
REFERENCE_ROLES = {
    "evaluation_only_not_agent_input",
    "calibration_reference_only",
    "official_evidence_reference_only",
}
REVIEW_STATUSES = {"candidate_requires_manual_review", "reviewed_for_evaluation", "rejected"}
COLLISION_TARGETS = {"vehicle", "pedestrian", "motorcycle", "bicycle", "object", "unknown"}
KNOWN_RESULT_STATUSES = {
    "unknown",
    "not_public",
    "public_reported",
    "court_decision_reported",
    "insurer_result_reported",
}
PLACEHOLDER_MARKERS = {
    "placeholder",
    "path/to",
    "local-only",
    "<",
    ">",
}
FORBIDDEN_COMMITTED_PATH_PATTERNS = [
    re.compile(r"^[a-zA-Z]:[/\\]Users[/\\]", re.IGNORECASE),
    re.compile(r"^\\\\"),
    re.compile(r"^/Users/"),
    re.compile(r"^/home/[^/]+/"),
]


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def issue(case_id: str, code: str, message: str, severity: str = "error") -> dict[str, str]:
    return {"case": case_id, "severity": severity, "code": code, "message": message}


def is_placeholder_path(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def path_is_inside_repo(value: str, manifest_path: Path) -> bool:
    raw = Path(value).expanduser()
    candidates = [raw]
    if not raw.is_absolute():
        candidates.extend([REPO_ROOT / raw, manifest_path.parent / raw])
    for candidate in candidates:
        try:
            candidate.resolve().relative_to(REPO_ROOT)
            return True
        except ValueError:
            continue
    return False


def looks_like_private_local_path(value: str) -> bool:
    if not value or is_placeholder_path(value):
        return False
    normalized = value.replace("\\", "/")
    return any(pattern.search(normalized) for pattern in FORBIDDEN_COMMITTED_PATH_PATTERNS)


def as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def validate_reference_expectations(case_id: str, value: Any) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not isinstance(value, dict):
        return [issue(case_id, "missing_reference_expectations", "reference_expectations must be an object")]
    direct = str(value.get("direct_collision_partner_type") or "")
    if direct not in COLLISION_TARGETS:
        issues.append(issue(case_id, "invalid_direct_collision_partner_type", "direct_collision_partner_type must be a known target enum"))
    must_not_promote = as_string_list(value.get("must_not_promote"))
    if not must_not_promote:
        issues.append(issue(case_id, "missing_must_not_promote", "must_not_promote must contain at least one pollution guard"))
    expected_context = as_string_list(value.get("expected_context"))
    if not expected_context and direct == "unknown":
        issues.append(issue(case_id, "weak_expectation_context", "unknown direct target needs expected_context for useful evaluation", "warning"))
    branches = value.get("ambiguous_branches")
    if branches is not None:
        if not isinstance(branches, list):
            issues.append(issue(case_id, "invalid_ambiguous_branches", "ambiguous_branches must be an array"))
        else:
            for index, branch in enumerate(branches, start=1):
                if not isinstance(branch, dict) or not str(branch.get("condition") or "").strip() or not str(branch.get("expected_guidance") or "").strip():
                    issues.append(issue(case_id, "invalid_ambiguous_branch", f"ambiguous_branches[{index}] needs condition and expected_guidance"))
    return issues


def validate_usage_policy(case_id: str, value: Any, source_type: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not isinstance(value, dict):
        return [issue(case_id, "missing_usage_policy", "usage_policy must be an object")]
    if value.get("agent_input_allowed") is not False:
        issues.append(issue(case_id, "agent_input_allowed_not_false", "reference cases must not be injected into Agent user-case payloads"))
    if value.get("raw_video_commit_allowed") is not False:
        issues.append(issue(case_id, "raw_video_commit_allowed_not_false", "raw media must not be committed"))
    notes = str(value.get("notes") or "").strip()
    if not notes:
        issues.append(issue(case_id, "missing_usage_notes", "usage_policy.notes is required"))
    if source_type == "public_reference_link" and "download" in notes.lower() and "not" not in notes.lower() and "do not" not in notes.lower():
        issues.append(issue(case_id, "ambiguous_download_policy", "public reference notes must not imply raw video download is allowed", "warning"))
    return issues


def validate_reference_outcome(case_id: str, value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    issues: list[dict[str, str]] = []
    if not isinstance(value, dict):
        return [issue(case_id, "invalid_reference_outcome", "reference_outcome must be an object")]
    status = str(value.get("known_result_status") or "unknown")
    if status not in KNOWN_RESULT_STATUSES:
        issues.append(issue(case_id, "invalid_known_result_status", "known_result_status must be a known enum"))
    summary = str(value.get("known_result_summary") or "").strip()
    if status not in {"unknown", "not_public"} and not summary:
        issues.append(issue(case_id, "missing_known_result_summary", "public or reported result needs a short summary"))
    confidence = str(value.get("confidence_note") or "").lower()
    if "정답" in confidence or "answer key" in confidence:
        issues.append(issue(case_id, "answer_key_language", "reference outcome must not be described as an answer key"))
    return issues


def validate_case(case: Any, index: int, manifest_path: Path) -> list[dict[str, str]]:
    case_id = f"case_{index}"
    issues: list[dict[str, str]] = []
    if not isinstance(case, dict):
        return [issue(case_id, "case_not_object", "case must be an object")]
    case_id = str(case.get("id") or case_id)
    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", case_id):
        issues.append(issue(case_id, "invalid_id", "id must use lowercase letters, numbers, underscore, or hyphen"))
    source_type = str(case.get("source_type") or "")
    if source_type not in SOURCE_TYPES:
        issues.append(issue(case_id, "invalid_source_type", "source_type is invalid"))
    reference_role = str(case.get("reference_role") or "")
    if reference_role not in REFERENCE_ROLES:
        issues.append(issue(case_id, "invalid_reference_role", "reference_role must isolate this case from Agent input facts"))
    if reference_role not in {"evaluation_only_not_agent_input", "calibration_reference_only", "official_evidence_reference_only"}:
        issues.append(issue(case_id, "unsafe_reference_role", "reference_role is not safe for evaluation-only use"))
    review_status = str(case.get("review_status") or "")
    if review_status not in REVIEW_STATUSES:
        issues.append(issue(case_id, "invalid_review_status", "review_status must be candidate, reviewed, or rejected"))
    if not str(case.get("scenario_summary") or "").strip():
        issues.append(issue(case_id, "missing_scenario_summary", "scenario_summary is required"))
    if not as_string_list(case.get("evaluation_focus")):
        issues.append(issue(case_id, "missing_evaluation_focus", "evaluation_focus must contain at least one focus item"))

    if source_type == "public_reference_link" and not str(case.get("source_url") or "").startswith(("http://", "https://")):
        issues.append(issue(case_id, "missing_public_source_url", "public_reference_link needs an http(s) source_url"))
    if source_type == "local_user_provided" and not str(case.get("local_video_path") or "").strip():
        issues.append(issue(case_id, "missing_local_video_path", "local_user_provided needs a local_video_path placeholder or local-only path"))
    local_video_path = str(case.get("local_video_path") or "").strip()
    if local_video_path:
        if looks_like_private_local_path(local_video_path):
            issues.append(issue(case_id, "private_local_path_in_manifest", "committed manifest must not contain a real user-local path"))
        if path_is_inside_repo(local_video_path, manifest_path) and not local_video_path.startswith((".local", "logs", "datasets", "storage")):
            issues.append(issue(case_id, "repo_raw_media_path", "local_video_path should not point to a tracked repo path"))

    if source_type == "aihub_sample":
        dataset_ref = case.get("dataset_ref")
        if not isinstance(dataset_ref, dict) or not str(dataset_ref.get("dataset_key") or "").strip():
            issues.append(issue(case_id, "missing_aihub_dataset_ref", "aihub_sample needs dataset_ref.dataset_key"))

    if review_status == "reviewed_for_evaluation":
        expectations = case.get("reference_expectations") if isinstance(case.get("reference_expectations"), dict) else {}
        direct = str(expectations.get("direct_collision_partner_type") or "")
        if direct == "unknown":
            issues.append(issue(case_id, "reviewed_case_still_unknown_target", "reviewed cases should resolve direct_collision_partner_type unless deliberately impossible", "warning"))

    issues.extend(validate_reference_expectations(case_id, case.get("reference_expectations")))
    issues.extend(validate_usage_policy(case_id, case.get("usage_policy"), source_type))
    issues.extend(validate_reference_outcome(case_id, case.get("reference_outcome")))
    return issues


def validate_manifest(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    issues: list[dict[str, str]] = []
    if not isinstance(payload, dict):
        raise ValueError("manifest must be an object")
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("manifest.cases must be an array")
    names = Counter()
    source_counts = Counter()
    reviewed_count = 0
    for index, case in enumerate(cases, start=1):
        if isinstance(case, dict):
            names[str(case.get("id") or f"case_{index}")] += 1
            source_counts[str(case.get("source_type") or "unknown")] += 1
            if case.get("review_status") == "reviewed_for_evaluation":
                reviewed_count += 1
        issues.extend(validate_case(case, index, path))
    for case_id, count in names.items():
        if count > 1:
            issues.append(issue(case_id, "duplicate_case_id", "case id must be unique"))
    error_count = sum(1 for item in issues if item["severity"] == "error")
    warning_count = sum(1 for item in issues if item["severity"] == "warning")
    return {
        "reference_case_manifest_preflight": "completed",
        "manifest": str(path),
        "case_count": len(cases),
        "reviewed_for_evaluation_count": reviewed_count,
        "source_type_counts": dict(source_counts),
        "issue_count": len(issues),
        "error_count": error_count,
        "warning_count": warning_count,
        "status": "passed" if error_count == 0 else "failed",
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a video reference-case manifest.")
    parser.add_argument("--manifest", required=True, help="Reference case manifest JSON.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="JSON output path.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    result = validate_manifest(manifest_path)
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "case_count": result["case_count"],
        "error_count": result["error_count"],
        "warning_count": result["warning_count"],
        "output": str(output_path),
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
