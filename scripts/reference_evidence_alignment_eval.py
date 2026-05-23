import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT = "logs/video_accuracy/reference_evidence_alignment_eval.json"
READY_STATUS = "ready_for_legal_knia_insurance_evidence_eval"

REQUIRED_FAMILIES: dict[str, set[str]] = {
    "centerline_obstacle": {"knia", "legal", "insurance"},
    "secondary_collision": {"knia", "legal", "insurance"},
    "signal_transition": {"knia", "legal", "insurance"},
    "crosswalk_pedestrian_signal": {"knia", "legal", "insurance"},
    "rear_end_default": {"knia", "legal", "insurance"},
    "front_vehicle_stop_reason": {"knia", "legal", "insurance"},
    "unlit_stopped_vehicle_visibility": {"knia", "legal", "insurance"},
    "speed_avoidability": {"legal", "insurance"},
    "criminal_civil_split": {"legal", "insurance"},
    "non_contact_bicycle_trigger": {"knia", "legal", "insurance"},
    "time_gap_sudden_brake": {"knia", "legal", "insurance"},
    "stopped_state": {"knia", "legal", "insurance"},
}


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


class EvidenceAlignmentError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip()) or "sample"


def sample_output_path(sample_dir: Path, sample_name: str) -> Path | None:
    direct = sample_dir / f"{safe_name(sample_name)}.json"
    if direct.exists():
        return direct
    matches = sorted(sample_dir.glob(f"*{safe_name(sample_name)}*.json"))
    return matches[0] if matches else None


def load_sample_payload(sample_dir: Path, sample_name: str) -> tuple[dict[str, Any], str | None]:
    path = sample_output_path(sample_dir, sample_name)
    if path is None:
        return {}, None
    data = load_json(path)
    return data if isinstance(data, dict) else {}, str(path)


def card_from_payload(stage5_sample: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    card = payload.get("expert_guidance_card") if isinstance(payload.get("expert_guidance_card"), dict) else {}
    if card:
        return card
    fallback = stage5_sample.get("expert_guidance")
    return fallback if isinstance(fallback, dict) else {}


def evaluate_card(card: dict[str, Any]) -> dict[str, Any]:
    basis = card.get("basis") if isinstance(card.get("basis"), list) else []
    legal_points = card.get("legal_points") if isinstance(card.get("legal_points"), list) else []
    insurance_steps = card.get("insurance_steps") if isinstance(card.get("insurance_steps"), list) else []
    missing_items = card.get("missing_items") if isinstance(card.get("missing_items"), list) else []

    basis_families = Counter(family_key(item) for item in basis if isinstance(item, dict))
    has_detail = bool(basis or legal_points or insurance_steps or missing_items)
    return {
        "present": bool(card.get("present", True) if card else False),
        "detail_available": has_detail,
        "status_label": card.get("status_label"),
        "fault_range_label": card.get("fault_range_label"),
        "legal_point_count": int(card.get("legal_point_count") or len(legal_points) or 0),
        "insurance_step_count": int(card.get("insurance_step_count") or len(insurance_steps) or 0),
        "basis_count": int(card.get("basis_count") or len(basis) or 0),
        "missing_item_count": int(card.get("missing_item_count") or len(missing_items) or 0),
        "basis_family_counts": dict(sorted((key, value) for key, value in basis_families.items() if key)),
        "basis_titles": [
            str(item.get("title") or "")
            for item in basis
            if isinstance(item, dict) and item.get("title")
        ][:6],
    }


def family_key(value: Any) -> str:
    if isinstance(value, dict):
        text = " ".join(str(value.get(key) or "") for key in ("family_label", "title", "reason")).lower()
    else:
        text = str(value or "").lower()
    if "knia" in text or "fault ratio" in text or "과실" in text:
        return "knia"
    if "legal" in text or "law" in text or "road traffic act" in text or "법" in text:
        return "legal"
    if "insurance" in text or "보험" in text:
        return "insurance"
    if text:
        return "general"
    return ""


def evaluate_focus(row: dict[str, Any], card_eval: dict[str, Any]) -> dict[str, Any]:
    criterion_id = str(row.get("criterion_id") or "unknown")
    required = REQUIRED_FAMILIES.get(criterion_id, {"legal", "insurance"})
    families = set(card_eval.get("basis_family_counts") or {})
    if int(card_eval.get("insurance_step_count") or 0) > 0:
        families.add("insurance")
    if row.get("status") == "needs_user_video_conflict_resolution":
        status = "blocked_by_video_user_conflict"
    elif not card_eval.get("present"):
        status = "missing_expert_guidance_card"
    elif not card_eval.get("fault_range_label") or card_eval.get("legal_point_count", 0) <= 0:
        status = "missing_visible_guidance"
    elif card_eval.get("insurance_step_count", 0) <= 0:
        status = "missing_insurance_guidance"
    elif card_eval.get("basis_count", 0) <= 0:
        status = "missing_basis"
    elif not card_eval.get("detail_available"):
        status = "summary_ready_but_detail_capture_needed"
    else:
        missing = sorted(required - families)
        status = "evidence_family_gap" if missing else "evidence_alignment_ready"
    return {
        "focus": row.get("focus"),
        "criterion_id": criterion_id,
        "reference_status": row.get("status"),
        "required_families": sorted(required),
        "available_families": sorted(families),
        "missing_families": sorted(required - families) if card_eval.get("detail_available") else [],
        "status": status,
    }


def evaluate_sample(stage5_sample: dict[str, Any], sample_dir: Path) -> dict[str, Any]:
    payload, output_json = load_sample_payload(sample_dir, str(stage5_sample.get("name") or ""))
    card_eval = evaluate_card(card_from_payload(stage5_sample, payload))
    focus_rows = [
        evaluate_focus(row, card_eval)
        for row in stage5_sample.get("focus_evaluations") or []
        if isinstance(row, dict)
    ]
    statuses = {row["status"] for row in focus_rows}
    if stage5_sample.get("guidance_readiness") != READY_STATUS:
        readiness = "not_ready_due_to_reference_gate"
    elif "missing_expert_guidance_card" in statuses or "missing_visible_guidance" in statuses:
        readiness = "display_contract_fix_required"
    elif "missing_basis" in statuses or "missing_insurance_guidance" in statuses:
        readiness = "basis_or_insurance_gap"
    elif "summary_ready_but_detail_capture_needed" in statuses:
        readiness = "ready_but_needs_detailed_card_capture"
    elif "evidence_family_gap" in statuses:
        readiness = "needs_evidence_family_retrieval"
    else:
        readiness = "ready_for_manual_reference_evidence_review"
    return {
        "name": stage5_sample.get("name"),
        "case_title": stage5_sample.get("case_title"),
        "source_output_json": output_json,
        "reference_guidance_readiness": stage5_sample.get("guidance_readiness"),
        "alignment_readiness": readiness,
        "card_evaluation": card_eval,
        "focus_alignment": focus_rows,
        "next_actions": next_actions(readiness),
    }


def next_actions(readiness: str) -> list[str]:
    if readiness == "not_ready_due_to_reference_gate":
        return ["Resolve video/user conflicts or missing facts before evidence alignment."]
    if readiness == "ready_but_needs_detailed_card_capture":
        return ["Regenerate E2E/batch output with detailed expert guidance card capture enabled."]
    if readiness == "needs_evidence_family_retrieval":
        return ["Add missing KNIA/legal/insurance evidence family through Agent search terms or fallback references."]
    if readiness == "basis_or_insurance_gap":
        return ["Fix missing basis or insurance guidance in the expert guidance card."]
    if readiness == "display_contract_fix_required":
        return ["Fix Gateway/Frontend expert guidance display contract before accuracy tuning."]
    return ["Review actual evidence title/content fit against the expert reference focus items."]


def aggregate(samples: list[dict[str, Any]]) -> dict[str, Any]:
    readiness_counts = Counter(sample["alignment_readiness"] for sample in samples)
    focus_counts = Counter(row["status"] for sample in samples for row in sample["focus_alignment"])
    detail_gap_count = sum(1 for sample in samples if not sample["card_evaluation"].get("detail_available"))
    return {
        "reference_evidence_alignment_eval": "completed",
        "sample_count": len(samples),
        "readiness_counts": dict(sorted(readiness_counts.items())),
        "focus_status_counts": dict(sorted(focus_counts.items())),
        "detail_capture_gap_count": detail_gap_count,
        "ready_for_manual_reference_evidence_review_count": readiness_counts.get(
            "ready_for_manual_reference_evidence_review",
            0,
        ),
        "recommendations": recommendations(readiness_counts, detail_gap_count),
        "samples": samples,
    }


def recommendations(readiness_counts: Counter, detail_gap_count: int) -> list[str]:
    output: list[str] = []
    if detail_gap_count:
        output.append("Detailed expert guidance card fields are missing. Regenerate E2E output before content-fit review.")
    if readiness_counts.get("needs_evidence_family_retrieval"):
        output.append("Some samples are missing required evidence families. Reinforce Agent search terms or fallback references.")
    if readiness_counts.get("ready_for_manual_reference_evidence_review"):
        output.append("Detailed evidence families are ready. Review actual evidence title/content fit next.")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate whether expert guidance evidence is aligned with lawyer-reference focus items.",
    )
    parser.add_argument("--reference-eval", required=True, help="reference_guidance_eval_stage5.json")
    parser.add_argument("--sample-dir", required=True, help="Directory containing video_agent_e2e sample JSON outputs.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--include-not-ready", action="store_true", help="Also evaluate samples blocked by the reference gate.")
    args = parser.parse_args()

    reference_eval_path = Path(args.reference_eval).expanduser().resolve()
    sample_dir = Path(args.sample_dir).expanduser().resolve()
    data = load_json(reference_eval_path)
    samples = data.get("samples") if isinstance(data.get("samples"), list) else []
    if not samples:
        raise EvidenceAlignmentError("reference eval must contain samples")
    selected = [
        sample
        for sample in samples
        if args.include_not_ready or sample.get("guidance_readiness") == READY_STATUS
    ]
    evaluated = [evaluate_sample(sample, sample_dir) for sample in selected if isinstance(sample, dict)]
    summary = aggregate(evaluated)
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceAlignmentError as exc:
        print(f"reference_evidence_alignment_eval=failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
