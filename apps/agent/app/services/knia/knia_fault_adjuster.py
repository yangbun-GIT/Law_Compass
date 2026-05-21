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
