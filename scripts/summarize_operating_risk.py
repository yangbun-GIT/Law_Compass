import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = "logs/operating_risk_summary.json"


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def nested_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def nested_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def summarize_batch(batch: dict[str, Any]) -> dict[str, Any]:
    samples = nested_list(batch.get("samples"))
    usage_totals = Counter()
    provider_counts = Counter()
    usage_event_counts = Counter()
    zero_observation_count = 0
    fallback_limited_count = 0
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        provider = str(sample.get("video_provider") or sample.get("provider") or "")
        if provider:
            provider_counts.update([provider])
        frame_analysis = nested_dict(sample.get("frame_analysis") or sample.get("video_analysis"))
        usage = nested_dict(frame_analysis.get("usage") or sample.get("usage"))
        usage_event = nested_dict(frame_analysis.get("ai_usage_event") or sample.get("ai_usage_event"))
        if usage_event:
            usage_event_counts.update([str(usage_event.get("version") or "unknown")])
            if not usage:
                usage = nested_dict(usage_event.get("usage"))
        for key in ("input_tokens", "output_tokens", "total_tokens"):
            usage_totals[key] += safe_int(usage.get(key))
        observations = nested_list(frame_analysis.get("observations") or sample.get("video_observations"))
        if frame_analysis and not observations:
            zero_observation_count += 1
        if any(isinstance(item, dict) and item.get("field") == "visual_evidence_limited" for item in observations):
            fallback_limited_count += 1
    return {
        "sample_count": len(samples),
        "provider_counts": dict(sorted(provider_counts.items())),
        "usage_event_counts": dict(sorted(usage_event_counts.items())),
        "token_usage_totals": {key: value for key, value in usage_totals.items() if value},
        "zero_observation_sample_count": zero_observation_count,
        "visual_evidence_limited_count": fallback_limited_count,
    }


def summarize_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "readiness_counts": nested_dict(evidence.get("readiness_counts")),
        "focus_status_counts": nested_dict(evidence.get("focus_status_counts")),
        "source_quality_counts": nested_dict(evidence.get("source_quality_counts")),
        "source_quality_status_counts": nested_dict(evidence.get("source_quality_status_counts")),
        "static_support_basis_count": safe_int(evidence.get("static_support_basis_count")),
        "original_or_collected_basis_count": safe_int(evidence.get("original_or_collected_basis_count")),
        "basis_needs_original_source_review_count": safe_int(evidence.get("basis_needs_original_source_review_count")),
        "recommendations": nested_list(evidence.get("recommendations")),
    }


def summarize_guidance(guidance: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_count": safe_int(guidance.get("sample_count")),
        "readiness_counts": nested_dict(guidance.get("readiness_counts")),
        "focus_status_counts": nested_dict(guidance.get("focus_status_counts")),
        "conflict_followup_summary": nested_dict(guidance.get("batch_conflict_followup_summary")),
    }


def summarize_calibration(calibration: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_count": safe_int(calibration.get("sample_count")),
        "status_counts": nested_dict(calibration.get("status_counts")),
        "recommendations": nested_list(calibration.get("recommendations")),
    }


def risk_notes(batch: dict[str, Any], evidence: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    token_totals = nested_dict(batch.get("token_usage_totals"))
    if token_totals:
        notes.append("OpenAI token usage metadata was captured for at least one batch path.")
    else:
        notes.append("OpenAI token usage metadata was not found in the supplied batch output; keep usage capture enabled before cost review.")
    if safe_int(evidence.get("static_support_basis_count")):
        notes.append("Static support evidence is still present and must remain labeled as fallback until original sources are imported.")
    if safe_int(evidence.get("basis_needs_original_source_review_count")):
        notes.append("Some displayed basis items still need original-source review.")
    if safe_int(batch.get("zero_observation_sample_count")):
        notes.append("At least one video sample produced zero observations; keep retry/fallback analysis enabled for frame-rich videos.")
    return notes


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize operating risks from guidance, evidence, calibration, and video batch outputs.")
    parser.add_argument("--reference-guidance", help="reference_guidance_eval output JSON")
    parser.add_argument("--reference-evidence", help="reference_evidence_alignment_eval output JSON")
    parser.add_argument("--reference-calibration", help="reference_guidance_calibration_eval output JSON")
    parser.add_argument("--batch-output", help="video_accuracy_batch aggregate JSON")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    guidance = summarize_guidance(load_json(Path(args.reference_guidance).resolve()) if args.reference_guidance else {})
    evidence = summarize_evidence(load_json(Path(args.reference_evidence).resolve()) if args.reference_evidence else {})
    calibration = summarize_calibration(load_json(Path(args.reference_calibration).resolve()) if args.reference_calibration else {})
    batch = summarize_batch(load_json(Path(args.batch_output).resolve()) if args.batch_output else {})
    summary = {
        "operating_risk_summary": "completed",
        "guidance": guidance,
        "evidence": evidence,
        "calibration": calibration,
        "video_batch": batch,
        "risk_notes": risk_notes(batch, evidence),
    }
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
