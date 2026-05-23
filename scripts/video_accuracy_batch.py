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
    if completed.returncode:
        result["stderr"] = completed.stderr[-4000:]
        result["stdout"] = completed.stdout[-4000:]
        return result

    payload = json.loads(sample_output.read_text(encoding="utf-8"))
    metrics = payload.get("video_accuracy_metrics") if isinstance(payload.get("video_accuracy_metrics"), dict) else {}
    expectations = payload.get("accuracy_expectations") if isinstance(payload.get("accuracy_expectations"), dict) else {}
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
    })
    if expectations.get("failed_count"):
        result["status"] = "mismatch"
    return result


def aggregate(samples: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(samples)
    passed = sum(1 for item in samples if item.get("status") == "passed")
    mismatched = sum(1 for item in samples if item.get("status") == "mismatch")
    failed = sum(1 for item in samples if item.get("status") == "failed")
    checked = sum(int(item.get("accuracy_checked_count") or 0) for item in samples)
    accuracy_passed = sum(int(item.get("accuracy_passed_count") or 0) for item in samples)
    return {
        "video_accuracy_batch": "completed" if failed == 0 else "failed",
        "sample_count": total,
        "passed_count": passed,
        "mismatch_count": mismatched,
        "failed_count": failed,
        "accuracy_checked_count": checked,
        "accuracy_passed_count": accuracy_passed,
        "accuracy_failed_count": max(0, checked - accuracy_passed),
        "samples": samples,
    }


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
