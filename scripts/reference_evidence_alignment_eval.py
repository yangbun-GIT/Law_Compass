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

CONTENT_RULES: dict[str, list[list[str]]] = {
    "centerline_obstacle": [
        ["centerline", "중앙선"],
        ["obstacle", "parked vehicle", "주차", "장애"],
        ["oncoming", "마주", "대향", "avoid"],
    ],
    "secondary_collision": [
        ["secondary", "후속", "2차"],
        ["rear", "후방", "뒤차", "추돌"],
    ],
    "signal_transition": [
        ["signal", "신호"],
        ["transition", "yellow", "red", "opponent signal", "cctv", "전환", "황색", "적색", "진입"],
    ],
    "crosswalk_pedestrian_signal": [
        ["crosswalk", "횡단보도"],
        ["pedestrian", "보행", "signal", "신호"],
    ],
    "rear_end_default": [
        ["rear", "후방", "뒤차", "추돌"],
        ["safe distance", "안전거리", "stopped", "정차", "감속"],
    ],
    "front_vehicle_stop_reason": [
        ["front vehicle", "truck", "stopped", "vehicle stops", "brakes", "rear-end bus", "rear-end", "앞차", "정지"],
        ["stop reason", "sudden braking", "time gap", "trigger", "bicycle", "정지 사유", "급정거", "유발"],
    ],
    "unlit_stopped_vehicle_visibility": [
        ["unlit", "stealth", "무등", "스텔스"],
        ["visibility", "night", "시인", "야간"],
        ["stopped", "정차"],
    ],
    "speed_avoidability": [
        ["speed", "speeding", "speed limit", "속도", "제한속도", "과속", "avoidability", "avoid", "회피"],
    ],
    "criminal_civil_split": [
        ["criminal", "형사"],
        ["civil", "민사", "fault ratio", "과실"],
    ],
    "non_contact_bicycle_trigger": [
        ["bicycle", "자전거"],
        ["non-contact", "trigger", "비접촉", "유발"],
        ["rear", "후방", "bus", "버스", "추돌"],
    ],
    "time_gap_sudden_brake": [
        ["time gap", "reaction time", "시간", "여유"],
        ["sudden", "brake", "급", "제동", "급정거"],
    ],
    "stopped_state": [
        ["stopped", "stop", "정차", "정지", "감속"],
    ],
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


def sample_output_path(sample_dir: Path | None, sample_name: str) -> Path | None:
    if sample_dir is None:
        return None
    direct = sample_dir / f"{safe_name(sample_name)}.json"
    if direct.exists():
        return direct
    matches = sorted(sample_dir.glob(f"*{safe_name(sample_name)}*.json"))
    return matches[0] if matches else None


def load_sample_payload(sample_dir: Path | None, sample_name: str) -> tuple[dict[str, Any], str | None]:
    path = sample_output_path(sample_dir, sample_name)
    if path is None:
        return {}, None
    data = load_json(path)
    return data if isinstance(data, dict) else {}, str(path)


def load_batch_payloads(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    data = load_json(path)
    samples = data.get("samples") if isinstance(data, dict) else []
    return {
        str(sample.get("name") or ""): sample
        for sample in samples
        if isinstance(sample, dict) and sample.get("name")
    }


def card_from_payload(stage5_sample: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    card = payload.get("expert_guidance_card") if isinstance(payload.get("expert_guidance_card"), dict) else {}
    if card:
        return card
    batch_card = payload.get("expert_guidance") if isinstance(payload.get("expert_guidance"), dict) else {}
    if batch_card:
        return batch_card
    fallback = stage5_sample.get("expert_guidance")
    return fallback if isinstance(fallback, dict) else {}


def evaluate_card(card: dict[str, Any]) -> dict[str, Any]:
    basis = card.get("basis") if isinstance(card.get("basis"), list) else []
    legal_points = card.get("legal_points") if isinstance(card.get("legal_points"), list) else []
    insurance_steps = card.get("insurance_steps") if isinstance(card.get("insurance_steps"), list) else []
    missing_items = card.get("missing_items") if isinstance(card.get("missing_items"), list) else []

    basis_families = Counter(family_key(item) for item in basis if isinstance(item, dict))
    source_quality_counts = Counter(source_quality_key(item) for item in basis if isinstance(item, dict))
    basis_items = [
        {
            "family_key": family_key(item),
            "family_label": str(item.get("family_label") or ""),
            "source_quality": source_quality_key(item),
            "source_quality_label": str(item.get("source_quality_label") or ""),
            "needs_original_source_review": bool(item.get("needs_original_source_review")),
            "has_source_url": bool(item.get("source_url")),
            "title": str(item.get("title") or ""),
            "reason": str(item.get("reason") or ""),
            "content_text": basis_text(item),
        }
        for item in basis
        if isinstance(item, dict)
    ]
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
        "source_quality_counts": dict(sorted((key, value) for key, value in source_quality_counts.items() if key)),
        "basis_titles": [
            str(item.get("title") or "")
            for item in basis
            if isinstance(item, dict) and item.get("title")
        ][:6],
        "basis_items": basis_items[:8],
    }


def basis_text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(key) or "")
        for key in ("family_label", "title", "reason")
    ).lower()


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


def source_quality_key(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    raw = str(value.get("source_quality") or "").strip()
    if raw:
        return raw
    label = str(value.get("source_quality_label") or "").lower()
    if "보조" in label or "static" in label:
        return "static_support"
    if "원문" in label or "수집" in label:
        return "collected_original"
    if "보험" in label:
        return "practice_reference"
    if label:
        return "curated_reference"
    return ""


def evaluate_content_fit(criterion_id: str, card_eval: dict[str, Any]) -> dict[str, Any]:
    groups = CONTENT_RULES.get(criterion_id, [])
    basis_items = [item for item in card_eval.get("basis_items") or [] if isinstance(item, dict)]
    if not groups:
        return {
            "content_fit_status": "content_rule_not_defined",
            "required_keyword_groups": [],
            "missing_keyword_groups": [],
            "matched_basis_titles": [],
        }

    group_results = []
    missing_groups: list[list[str]] = []
    for group in groups:
        matches = sorted(
            {
                token
                for token in group
                if any(token.lower() in str(item.get("content_text") or "") for item in basis_items)
            }
        )
        if not matches:
            missing_groups.append(group)
        group_results.append({"required_any_of": group, "matched_tokens": matches})

    matched_basis_titles = [
        str(item.get("title") or "")
        for item in basis_items
        if _basis_matches_all_groups(str(item.get("content_text") or ""), groups)
    ][:5]
    partial_basis_titles = [
        str(item.get("title") or "")
        for item in basis_items
        if not _basis_matches_all_groups(str(item.get("content_text") or ""), groups)
        and _basis_matches_any_group(str(item.get("content_text") or ""), groups)
    ][:5]
    status = "content_fit_ready" if not missing_groups else "content_keyword_gap"
    if status == "content_fit_ready" and not matched_basis_titles and partial_basis_titles:
        status = "combined_content_fit_ready"
    return {
        "content_fit_status": status,
        "required_keyword_groups": group_results,
        "missing_keyword_groups": missing_groups,
        "matched_basis_titles": matched_basis_titles,
        "partial_basis_titles": partial_basis_titles,
    }


def _basis_matches_all_groups(text: str, groups: list[list[str]]) -> bool:
    return bool(groups) and all(any(token.lower() in text for token in group) for group in groups)


def _basis_matches_any_group(text: str, groups: list[list[str]]) -> bool:
    return any(any(token.lower() in text for token in group) for group in groups)


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
    content_eval = evaluate_content_fit(criterion_id, card_eval)
    if status == "evidence_alignment_ready":
        content_status = content_eval.get("content_fit_status")
        if content_status == "content_keyword_gap":
            status = "evidence_content_gap"
        elif content_status == "content_rule_not_defined":
            status = "evidence_alignment_ready"
        else:
            status = "evidence_content_ready"
    return {
        "focus": row.get("focus"),
        "criterion_id": criterion_id,
        "reference_status": row.get("status"),
        "required_families": sorted(required),
        "available_families": sorted(families),
        "missing_families": sorted(required - families) if card_eval.get("detail_available") else [],
        "status": status,
        "content_fit": content_eval,
    }


def evaluate_sample(stage5_sample: dict[str, Any], sample_dir: Path | None, batch_sample: dict[str, Any] | None = None) -> dict[str, Any]:
    payload, output_json = load_sample_payload(sample_dir, str(stage5_sample.get("name") or ""))
    source_batch_output = False
    if not payload and batch_sample:
        payload = batch_sample
        source_batch_output = True
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
    elif "evidence_content_gap" in statuses:
        readiness = "needs_evidence_content_fit"
    else:
        readiness = "ready_for_stage8_guidance_calibration"
    return {
        "name": stage5_sample.get("name"),
        "case_title": stage5_sample.get("case_title"),
        "source_output_json": output_json,
        "source_batch_output": source_batch_output,
        "reference_guidance_readiness": stage5_sample.get("guidance_readiness"),
        "conflict_followup_resolved": bool(stage5_sample.get("conflict_followup_resolved")),
        "conflict_followup": stage5_sample.get("conflict_followup")
        if isinstance(stage5_sample.get("conflict_followup"), dict)
        else {"present": False},
        "alignment_readiness": readiness,
        "card_evaluation": card_eval,
        "focus_alignment": focus_rows,
        "extra_basis_review": extra_basis_review(card_eval, focus_rows),
        "next_actions": next_actions(readiness),
    }


def extra_basis_review(card_eval: dict[str, Any], focus_rows: list[dict[str, Any]]) -> dict[str, Any]:
    focus_criteria = {
        str(row.get("criterion_id") or "")
        for row in focus_rows
        if isinstance(row, dict) and row.get("criterion_id") in CONTENT_RULES
    }
    basis_items = [item for item in card_eval.get("basis_items") or [] if isinstance(item, dict)]
    extra_titles = []
    for item in basis_items:
        text = str(item.get("content_text") or "")
        if any(_basis_matches_any_group(text, CONTENT_RULES[criterion]) for criterion in focus_criteria):
            continue
        title = str(item.get("title") or "")
        if title:
            extra_titles.append(title)
    return {
        "extra_basis_count": len(extra_titles),
        "extra_basis_titles": extra_titles[:6],
    }


def next_actions(readiness: str) -> list[str]:
    if readiness == "not_ready_due_to_reference_gate":
        return ["Resolve video/user conflicts or missing facts before evidence alignment."]
    if readiness == "ready_but_needs_detailed_card_capture":
        return ["Regenerate E2E/batch output with detailed expert guidance card capture enabled."]
    if readiness == "needs_evidence_family_retrieval":
        return ["Add missing KNIA/legal/insurance evidence family through Agent search terms or fallback references."]
    if readiness == "needs_evidence_content_fit":
        return ["Improve evidence retrieval, fallback references, or guidance basis selection so title/reason text matches the expert focus item."]
    if readiness == "basis_or_insurance_gap":
        return ["Fix missing basis or insurance guidance in the expert guidance card."]
    if readiness == "display_contract_fix_required":
        return ["Fix Gateway/Frontend expert guidance display contract before accuracy tuning."]
    return ["Proceed to guidance calibration using content-fit-ready evidence references."]


def aggregate(samples: list[dict[str, Any]]) -> dict[str, Any]:
    readiness_counts = Counter(sample["alignment_readiness"] for sample in samples)
    focus_counts = Counter(row["status"] for sample in samples for row in sample["focus_alignment"])
    detail_gap_count = sum(1 for sample in samples if not sample["card_evaluation"].get("detail_available"))
    extra_basis_count = sum(int((sample.get("extra_basis_review") or {}).get("extra_basis_count") or 0) for sample in samples)
    resolved_conflict_count = sum(1 for sample in samples if sample.get("conflict_followup_resolved"))
    source_quality_counts: Counter[str] = Counter()
    for sample in samples:
        source_quality_counts.update(sample["card_evaluation"].get("source_quality_counts") or {})
    return {
        "reference_evidence_alignment_eval": "completed",
        "sample_count": len(samples),
        "readiness_counts": dict(sorted(readiness_counts.items())),
        "focus_status_counts": dict(sorted(focus_counts.items())),
        "detail_capture_gap_count": detail_gap_count,
        "extra_basis_review_count": extra_basis_count,
        "source_quality_counts": dict(sorted(source_quality_counts.items())),
        "static_support_basis_count": int(source_quality_counts.get("static_support", 0)),
        "original_or_collected_basis_count": int(source_quality_counts.get("collected_original", 0)),
        "resolved_conflict_sample_count": resolved_conflict_count,
        "ready_for_manual_reference_evidence_review_count": readiness_counts.get(
            "ready_for_manual_reference_evidence_review",
            0,
        ),
        "ready_for_stage8_guidance_calibration_count": readiness_counts.get(
            "ready_for_stage8_guidance_calibration",
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
    if readiness_counts.get("needs_evidence_content_fit"):
        output.append("Some focus items lack content-fit evidence. Improve retrieval/fallback/basis selection before guidance calibration.")
    if readiness_counts.get("ready_for_stage8_guidance_calibration"):
        output.append("Evidence title/reason content fits the expert focus items. Proceed to guidance calibration.")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate whether expert guidance evidence is aligned with lawyer-reference focus items.",
    )
    parser.add_argument("--reference-eval", required=True, help="reference_guidance_eval_stage5.json")
    parser.add_argument("--sample-dir", help="Directory containing video_agent_e2e sample JSON outputs.")
    parser.add_argument("--batch-output", help="Optional video_accuracy_batch aggregate.json used when sample JSON files are unavailable.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--include-not-ready", action="store_true", help="Also evaluate samples blocked by the reference gate.")
    args = parser.parse_args()

    reference_eval_path = Path(args.reference_eval).expanduser().resolve()
    sample_dir = Path(args.sample_dir).expanduser().resolve() if args.sample_dir else None
    batch_payloads = load_batch_payloads(Path(args.batch_output).expanduser().resolve() if args.batch_output else None)
    if sample_dir is None and not batch_payloads:
        raise EvidenceAlignmentError("Either --sample-dir or --batch-output is required")
    data = load_json(reference_eval_path)
    samples = data.get("samples") if isinstance(data.get("samples"), list) else []
    if not samples:
        raise EvidenceAlignmentError("reference eval must contain samples")
    selected = [
        sample
        for sample in samples
        if args.include_not_ready or sample.get("guidance_readiness") == READY_STATUS
    ]
    evaluated = [
        evaluate_sample(sample, sample_dir, batch_payloads.get(str(sample.get("name") or "")))
        for sample in selected
        if isinstance(sample, dict)
    ]
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
