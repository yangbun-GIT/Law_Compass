from __future__ import annotations

import json
from typing import Any

from app.services.knia.knia_repository import KniaRepository


def _as_text(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            parts.append(json.dumps(value, ensure_ascii=False))
        else:
            parts.append(str(value))
    return " ".join(parts).lower()


def _clamp(value: int) -> int:
    return max(0, min(100, int(value)))


def _effect(delta_a: int, delta_b: int) -> dict[str, int]:
    # KNIA UI calculates A = baseA + sum(A deltas) - sum(B deltas), B mirrors it.
    if delta_a:
        return {"A": delta_a, "B": -delta_a}
    if delta_b:
        return {"A": -delta_b, "B": delta_b}
    return {"A": 0, "B": 0}


def calculate_fault_from_structured_chart(
    chart: dict[str, Any],
    facts: dict[str, Any] | None,
    user_vehicle_role: str | None = None,
) -> dict[str, Any]:
    facts = facts or {}
    selected_candidate = select_structured_base_fault_candidate(chart, facts, user_vehicle_role)
    base = _candidate_fault_pair(selected_candidate)
    review_required = bool(chart.get("review_required", False))
    reference_only = not structured_chart_final_fault_eligible(chart, selected_candidate)
    if not base:
        return {
            "base_fault": {},
            "selected_adjustments": [],
            "rejected_adjustments": [],
            "unknown_adjustments": [],
            "conditional_outcomes": [],
            "final_fault": {},
            "fault_range": {},
            "source_chart": _structured_source_chart(chart),
            "review_required": review_required,
            "reference_only": True,
            "confidence": min(float(chart.get("parsing_confidence") or 0.35), 0.45),
            "policy": {"source": "structured_knia_json", "final_fault_blocked_reason": "base_fault_missing_or_incomplete"},
        }

    a = base["A"]
    b = base["B"]
    applied: list[dict[str, Any]] = []
    not_applied: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    conditional: list[dict[str, Any]] = []

    for factor in chart.get("adjustments") or chart.get("adjustment_factors") or []:
        if not isinstance(factor, dict):
            continue
        label = str(factor.get("label") or factor.get("label_candidate") or factor.get("source_line") or "구조화 수정요소").strip()
        fact_key = factor.get("fact_key") or factor.get("condition_code") or _infer_adjustment_fact_key(label)
        value = facts.get(fact_key) if fact_key else None
        delta_a, delta_b = _structured_adjustment_delta(factor)
        applies_to = str(factor.get("applies_to") or factor.get("applies_to_candidate") or "").upper()
        if applies_to == "A" and delta_a == 0:
            delta_a = int(factor.get("delta") or 0)
        if applies_to == "B" and delta_b == 0:
            delta_b = int(factor.get("delta") or 0)
        if not delta_a and not delta_b:
            not_applied.append({"label": label, "reason": "숫자 가감값이 구조화되어 있지 않아 자동 적용하지 않았습니다."})
            continue
        if factor.get("review_required"):
            unknown.append({"label": label, "reason": "수정요소 자체가 검수 필요 상태입니다.", "fact_key": fact_key})
            conditional.append(_conditional_outcome(label, a, delta_a, delta_b, "수정요소 검수 및 인과관계가 확인되는 경우"))
            continue
        if value in {True, "yes", "confirmed", "true", "applies"} and factor.get("causal_relationship", True) is not False:
            effect = _effect(delta_a, delta_b)
            a += effect["A"]
            b += effect["B"]
            applied.append({"label": label, "delta_a": delta_a, "delta_b": delta_b, "applied_effect": effect, "matched_by": [fact_key] if fact_key else [], "source": "KNIA 구조화 수정요소"})
        elif value in {None, "unknown", "모름", ""}:
            unknown.append({"label": label, "reason": "사실관계가 확인되지 않아 적용하지 않았습니다.", "fact_key": fact_key})
            conditional.append(_conditional_outcome(label, a, delta_a, delta_b, "해당 사실과 사고 인과관계가 확인되는 경우"))
        else:
            not_applied.append({"label": label, "reason": "입력 사실상 적용 조건이 확인되지 않았습니다.", "fact_key": fact_key})

    a = _clamp(a)
    b = _clamp(100 - a)
    confidence = float(chart.get("parsing_confidence") or 0.65)
    if review_required and reference_only:
        confidence = min(confidence, 0.45)
    elif review_required:
        confidence = max(min(confidence, 0.72), 0.62)
    return {
        "base_fault": base,
        "selected_adjustments": applied,
        "rejected_adjustments": not_applied,
        "unknown_adjustments": unknown,
        "conditional_outcomes": conditional,
        "final_fault": {"A": a, "B": b},
        "fault_range": {"A": f"{max(a - 10, 0)}~{min(a + 10, 100)}", "B": f"{max(b - 10, 0)}~{min(b + 10, 100)}"},
        "source_chart": _structured_source_chart(chart, selected_candidate),
        "review_required": review_required,
        "reference_only": reference_only,
        "confidence": confidence,
        "policy": {
            "source": "structured_knia_json",
            "llm_must_not_generate_fault_numbers": True,
            "reference_only": reference_only,
            "review_required_is_metadata_only": bool(review_required and not reference_only),
        },
    }


def select_structured_base_fault_candidate(
    chart: dict[str, Any],
    facts: dict[str, Any] | None = None,
    user_vehicle_role: str | None = None,
) -> dict[str, Any] | None:
    base_fault = chart.get("base_fault") or {}
    candidates: list[dict[str, Any]] = []
    for candidate in base_fault.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        a = candidate.get("A")
        b = candidate.get("B")
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            normalized = dict(candidate)
            a_i = _clamp(int(a))
            normalized["A"] = a_i
            normalized["B"] = _clamp(100 - a_i if int(a) + int(b) != 100 else int(b))
            candidates.append(normalized)
    a = base_fault.get("A")
    b = base_fault.get("B")
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        a_i = _clamp(int(a))
        normalized = dict(base_fault)
        normalized["A"] = a_i
        normalized["B"] = _clamp(100 - a_i if int(a) + int(b) != 100 else int(b))
        candidates.append(normalized)
    if not candidates:
        return None

    preferred = _preferred_subchart_numbers(chart, facts or {}, user_vehicle_role)
    for chart_no in preferred:
        for candidate in candidates:
            if str(candidate.get("subchart_no") or "") == chart_no:
                return candidate
    requested = str(chart.get("chart_no") or "")
    if "-" in requested:
        for candidate in candidates:
            if str(candidate.get("subchart_no") or "") == requested:
                return candidate
    return candidates[0]


def structured_chart_final_fault_eligible(chart: dict[str, Any], candidate: dict[str, Any] | None = None) -> bool:
    if chart.get("reference_only_forced"):
        return False
    selected = candidate if candidate is not None else select_structured_base_fault_candidate(chart)
    if not _candidate_fault_pair(selected):
        return False
    if not (chart.get("major_party_type") or chart.get("accident_party_type")):
        return False
    if not chart.get("scenario_type"):
        return False
    if chart.get("review_required") and not _chart_has_supporting_text(chart):
        return False
    return True


def _candidate_fault_pair(candidate: dict[str, Any] | None) -> dict[str, int] | None:
    if not candidate:
        return None
    a = candidate.get("A")
    b = candidate.get("B")
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        a_i = _clamp(int(a))
        return {"A": a_i, "B": _clamp(100 - a_i if int(a) + int(b) != 100 else int(b))}
    return None


def _preferred_subchart_numbers(
    chart: dict[str, Any],
    facts: dict[str, Any],
    user_vehicle_role: str | None,
) -> list[str]:
    scenario_type = str(chart.get("scenario_type") or facts.get("scenario_type") or facts.get("accident_type") or "")
    chart_no = str(chart.get("aggregate_chart_no") or chart.get("chart_no") or "")
    if scenario_type == "rear_end_collision" or chart_no.startswith("차41"):
        return ["차41-1"]
    if scenario_type == "lane_change_collision" or chart_no.startswith("차43"):
        return ["차43-2"]
    return []


def _chart_has_supporting_text(chart: dict[str, Any]) -> bool:
    return any(
        bool(chart.get(key))
        for key in (
            "raw_text",
            "accident_situation",
            "accident_summary",
            "base_fault_explanation",
            "basic_fault_text",
            "related_laws",
        )
    )


def _structured_adjustment_delta(factor: dict[str, Any]) -> tuple[int, int]:
    return int(factor.get("delta_a") or 0), int(factor.get("delta_b") or 0)


def _infer_adjustment_fact_key(label: str) -> str | None:
    if "방향" in label or "신호" in label:
        return "turn_signal"
    if "야간" in label or "시야" in label:
        return "night_or_visibility_limited"
    if "중대한" in label:
        return "gross_negligence"
    if "현저한" in label:
        return "significant_negligence"
    return None


def _conditional_outcome(label: str, base_a: int, delta_a: int, delta_b: int, condition: str) -> dict[str, Any]:
    effect = _effect(delta_a, delta_b)
    next_a = _clamp(base_a + effect["A"])
    return {"label": label, "condition": condition, "fault_if_confirmed": {"A": next_a, "B": 100 - next_a}}


def _structured_source_chart(chart: dict[str, Any], selected_candidate: dict[str, Any] | None = None) -> dict[str, Any]:
    aggregate_chart_no = chart.get("aggregate_chart_no") or chart.get("chart_no")
    display_chart_no = (selected_candidate or {}).get("subchart_no") or chart.get("chart_no")
    return {
        "chart_no": display_chart_no,
        "aggregate_chart_no": aggregate_chart_no if aggregate_chart_no != display_chart_no else None,
        "chart_type": chart.get("chart_type") or "1",
        "title": chart.get("title"),
        "major_party_type": chart.get("major_party_type") or chart.get("accident_party_type"),
        "scenario_type": chart.get("scenario_type"),
        "scenario_subtype": chart.get("scenario_subtype"),
        "scenario_tags": chart.get("scenario_tags") or [],
        "display_tags": chart.get("display_tags") or [],
        "keywords": chart.get("keywords") or [],
        "review_required": bool(chart.get("review_required", False)),
        "parsing_confidence": chart.get("parsing_confidence"),
        "source_type": "knia_structured_chart",
    }


def _match_factor(label: str, evidence_text: str, facts: dict[str, Any], video_metadata: dict[str, Any]) -> tuple[bool, list[str], str, float]:
    label_l = label.lower()
    matched: list[str] = []

    def has_any(words: list[str]) -> bool:
        return any(word.lower() in evidence_text for word in words)

    if any(word in label for word in ["야간", "시야장애", "시야 장애"]):
        if has_any(["야간", "밤", "어두", "시야장애", "시야 장애", "night"]):
            matched.append("야간 또는 시야장애 입력")
    if any(word in label for word in ["어린이", "노인", "장애인"]):
        if has_any(["어린이", "아이", "노인", "고령", "장애인", "child", "elderly"]):
            matched.append("취약 교통참여자 입력")
    if "자전거 도로" in label or "자전거도로" in label:
        if has_any(["자전거도로", "자전거 도로", "bike_lane", "bicycle_road"]):
            matched.append("자전거도로 관련 입력")
    if "차로" in label and "이상" in label:
        lane_count = facts.get("lane_count") or video_metadata.get("lane_count")
        if has_any(["2차로", "3차로", "다차로", "차로 이상", "multi_lane"]) or (isinstance(lane_count, int) and lane_count >= 2):
            matched.append("2차로 이상 도로 입력")
    if "현저한 과실" in label:
        if has_any(["전방주시", "급제동", "급진입", "과속", "휴대전화", "방향지시등", "음주", "현저한 과실"]):
            matched.append("현저한 과실 관련 입력")
    if "중대한 과실" in label:
        if has_any(["음주", "무면허", "역주행", "중앙선", "제한속도 20", "졸음", "마약", "중대한 과실"]):
            matched.append("중대한 과실 관련 입력")
    if "안전모" in label:
        if has_any(["안전모 미착용", "헬멧 미착용", "helmet"]):
            matched.append("안전모 미착용 입력")

    if matched:
        return True, matched, "입력 내용이 KNIA 원문 가감요소 조건과 맞습니다.", 0.82
    return False, [], "입력에서 이 가감요소를 뒷받침할 근거가 부족합니다.", 0.3


def estimate_knia_fault(
    chart_no: str,
    chart_type: str = "1",
    description_text: str = "",
    selected_keywords: list[str] | None = None,
    structured_facts: dict[str, Any] | None = None,
    video_metadata: dict[str, Any] | None = None,
    scenario_type: str | None = None,
    accident_party_type: str | None = None,
    repo: KniaRepository | None = None,
) -> dict[str, Any]:
    repo = repo or KniaRepository()
    chart = repo.get_chart(chart_no, chart_type)
    if not chart:
        raise ValueError(f"KNIA chart not found: {chart_no}/{chart_type}")
    if chart.get("base_fault") or chart.get("major_party_type"):
        structured_result = calculate_fault_from_structured_chart(chart, structured_facts or {})
        if structured_result.get("base_fault"):
            return structured_result
    factors = repo.get_chart_adjustments(chart_no, chart_type)
    facts = structured_facts or {}
    video = video_metadata or {}
    keywords = selected_keywords or []
    evidence_text = _as_text(description_text, keywords, facts, video, scenario_type, accident_party_type)

    base_a = int(chart.get("base_fault_a") if chart.get("base_fault_a") is not None else chart.get("applied_fault_a") or 50)
    base_b = int(chart.get("base_fault_b") if chart.get("base_fault_b") is not None else chart.get("applied_fault_b") or (100 - base_a))
    a = base_a
    b = base_b
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    used_groups: set[str] = set()

    for factor in factors:
        label = factor.get("label") or ""
        should_apply, matched_by, reason, confidence = _match_factor(label, evidence_text, facts, video)
        condition_code = str(factor.get("condition_code") or "")
        mutual_group = "major_fault" if "중대한 과실" in label or "현저한 과실" in label else condition_code
        if should_apply and mutual_group and mutual_group in used_groups and ("중대한 과실" in label or "현저한 과실" in label):
            rejected.append({"label": label, "reason": "같은 그룹에서 이미 더 적절한 가감요소를 적용했습니다."})
            continue
        if not should_apply:
            rejected.append({"label": label, "reason": reason})
            continue
        delta_a = int(factor.get("delta_a") or 0)
        delta_b = int(factor.get("delta_b") or 0)
        effect = _effect(delta_a, delta_b)
        a += effect["A"]
        b += effect["B"]
        if mutual_group:
            used_groups.add(mutual_group)
        selected.append({
            "label": label,
            "delta_a": delta_a,
            "delta_b": delta_b,
            "applied_effect": effect,
            "matched_by": matched_by,
            "confidence": confidence,
            "source": "KNIA 가감요소",
            "source_detail_url": factor.get("source_detail_url") or chart.get("source_detail_url") or chart.get("source_url"),
        })

    a = _clamp(a)
    b = _clamp(100 - a)
    steps = [f"기본과실 A{base_a}:B{base_b}"]
    for item in selected:
        effect = item["applied_effect"]
        steps.append(f"{item['label']}: A {effect['A']:+d}, B {effect['B']:+d}")
    steps.append(f"최종 A{a}:B{b}")
    return {
        "base_fault": {"A": base_a, "B": base_b},
        "selected_adjustments": selected,
        "rejected_adjustments": rejected,
        "final_fault": {"A": a, "B": b},
        "calculation_steps": steps,
        "evidence_used": [
            {"type": "description_text", "value": description_text[:240]} if description_text else None,
            {"type": "selected_keywords", "value": keywords} if keywords else None,
            {"type": "structured_facts", "value": facts} if facts else None,
            {"type": "video_metadata", "value": video} if video else None,
        ],
        "source_chart": {
            "chart_no": chart_no,
            "chart_type": chart_type,
            "source_detail_url": chart.get("source_detail_url") or chart.get("source_url"),
        },
        "notice": "KNIA 원문 기준 기반 참고 산정입니다. 최종 과실비율은 보험사·분쟁심의위·수사기관·법원 판단에 따라 달라질 수 있습니다.",
    }
