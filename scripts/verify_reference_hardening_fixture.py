import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "video_accuracy" / "reference_hardening_minimal"
OUTPUT_DIR = REPO_ROOT / "logs" / "video_accuracy" / "reference_hardening_fixture_smoke"


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class FixtureVerificationError(RuntimeError):
    pass


def run_step(name: str, args: list[str]) -> None:
    print(f"==> {name}")
    result = subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        print(result.stdout)
        raise FixtureVerificationError(f"{name} failed with exit code {result.returncode}")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def count(data: dict[str, Any], key: str, value: str) -> int:
    values = data.get(key)
    if not isinstance(values, dict):
        return 0
    return int(values.get(value) or 0)


def require_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise FixtureVerificationError(f"{label}: expected {expected!r}, got {actual!r}")


def verify_unresolved_outputs(guidance: dict[str, Any], evidence: dict[str, Any], calibration: dict[str, Any]) -> None:
    require_equal(
        "unresolved guidance ready count",
        count(guidance, "readiness_counts", "ready_for_legal_knia_insurance_evidence_eval"),
        1,
    )
    require_equal(
        "unresolved guidance conflict-gated count",
        count(guidance, "readiness_counts", "needs_conflict_resolution_before_guidance"),
        1,
    )
    require_equal(
        "unresolved evidence ready count",
        count(evidence, "readiness_counts", "ready_for_stage8_guidance_calibration"),
        1,
    )
    require_equal(
        "unresolved calibration pass count",
        count(calibration, "status_counts", "calibrated_for_user_flow"),
        1,
    )
    require_equal(
        "unresolved calibration blocked count",
        count(calibration, "status_counts", "blocked_by_reference_gate"),
        1,
    )


def verify_resolved_outputs(guidance: dict[str, Any], evidence: dict[str, Any], calibration: dict[str, Any]) -> None:
    require_equal(
        "resolved guidance ready count",
        count(guidance, "readiness_counts", "ready_for_legal_knia_insurance_evidence_eval"),
        2,
    )
    require_equal(
        "resolved focus count",
        count(guidance, "focus_status_counts", "conflict_resolved_ready_for_evidence_review"),
        2,
    )
    followup = guidance.get("batch_conflict_followup_summary")
    if not isinstance(followup, dict):
        raise FixtureVerificationError("resolved guidance missing batch_conflict_followup_summary")
    require_equal("resolved followup present count", int(followup.get("present_count") or 0), 1)
    require_equal("resolved followup resolved count", int(followup.get("resolved_count") or 0), 1)
    require_equal("resolved followup unresolved count", int(followup.get("unresolved_count") or 0), 0)
    require_equal(
        "resolved evidence ready count",
        count(evidence, "readiness_counts", "ready_for_stage8_guidance_calibration"),
        2,
    )
    require_equal("resolved evidence resolved sample count", int(evidence.get("resolved_conflict_sample_count") or 0), 1)
    require_equal(
        "resolved calibration pass count",
        count(calibration, "status_counts", "calibrated_for_user_flow"),
        2,
    )


def run_fixture_set(label: str, batch_file: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    guidance_output = OUTPUT_DIR / f"{label}_guidance.json"
    evidence_output = OUTPUT_DIR / f"{label}_evidence_alignment.json"
    calibration_output = OUTPUT_DIR / f"{label}_calibration.json"
    manifest = FIXTURE_DIR / "manifest.json"
    batch = FIXTURE_DIR / batch_file

    run_step(
        f"{label} reference guidance",
        [
            "scripts/reference_guidance_eval.py",
            "--manifest",
            str(manifest),
            "--batch-output",
            str(batch),
            "--output",
            str(guidance_output),
        ],
    )
    run_step(
        f"{label} evidence alignment",
        [
            "scripts/reference_evidence_alignment_eval.py",
            "--reference-eval",
            str(guidance_output),
            "--batch-output",
            str(batch),
            "--output",
            str(evidence_output),
        ],
    )
    run_step(
        f"{label} guidance calibration",
        [
            "scripts/reference_guidance_calibration_eval.py",
            "--manifest",
            str(manifest),
            "--batch-output",
            str(batch),
            "--reference-eval",
            str(guidance_output),
            "--output",
            str(calibration_output),
        ],
    )
    return load_json(guidance_output), load_json(evidence_output), load_json(calibration_output)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    unresolved = run_fixture_set("unresolved", "batch_aggregate.json")
    verify_unresolved_outputs(*unresolved)
    resolved = run_fixture_set("resolved", "batch_aggregate_conflict_resolved.json")
    verify_resolved_outputs(*resolved)
    print("reference_hardening_fixture=passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FixtureVerificationError as exc:
        print(f"reference_hardening_fixture=failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
