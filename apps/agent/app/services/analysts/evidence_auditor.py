from __future__ import annotations

from typing import Any

from app.services.evidence_quality_gate import evaluate_evidence_quality


_QUALITY_ORDER = {"low": 0, "medium": 1, "high": 2}


def audit_evidence(
    *,
    scenario_type: str,
    evidence: list[dict[str, Any]],
    legal_analysis: dict[str, Any],
    fault_ratio: dict[str, Any],
    missing_fields: list[str],
) -> dict[str, Any]:
    count = len(evidence)
    avg_score = sum(float(ev.get("score", 0) or 0) for ev in evidence) / count if count else 0.0
    weak_points = []
    if count < 3:
        weak_points.append("검색된 법률 근거가 부족합니다.")
    if avg_score < 0.25:
        weak_points.append("근거 점수가 낮아 추가 확인이 필요합니다.")
    if missing_fields:
        weak_points.append("필수 사고 사실 일부가 비어 있습니다.")
    base_quality = "high" if count >= 5 and avg_score >= 0.35 and not missing_fields else ("medium" if count >= 3 else "low")
    scenario_coverage = evaluate_evidence_quality(
        scenario_type=scenario_type,
        evidence=evidence,
        missing_fields=missing_fields,
    )
    weak_points.extend(scenario_coverage.get("weak_points") or [])
    quality = _lower_quality(base_quality, str(scenario_coverage.get("coverage_level") or "low"))
    return {
        "evidence_quality": quality,
        "evidence_count": count,
        "average_score": round(avg_score, 4),
        "used_evidence_ids": [ev.get("chunk_id") for ev in evidence if ev.get("chunk_id")],
        "scenario_evidence_coverage": scenario_coverage,
        "weak_points": weak_points,
        "followup_questions": _followups(scenario_type, missing_fields),
        "uncertainty_level": "low" if quality == "high" else ("medium" if quality == "medium" else "high"),
    }


def _lower_quality(first: str, second: str) -> str:
    return first if _QUALITY_ORDER.get(first, 0) <= _QUALITY_ORDER.get(second, 0) else second


def _followups(scenario_type: str, missing_fields: list[str]) -> list[str]:
    out = [f"{field} 정보를 추가로 입력해 주세요." for field in missing_fields]
    if scenario_type == "school_zone_child_accident":
        out.extend(["피해자가 만 13세 미만인지 확인해 주세요.", "어린이보호구역 표지와 제한속도를 확인해 주세요."])
    if scenario_type == "intersection_signal_violation":
        out.append("내 차량과 상대 차량의 신호 색상 및 진입 시점을 각각 확인해 주세요.")
    if scenario_type == "rear_end_collision":
        out.append("정차 상태가 몇 초 이상 지속됐는지, 급정거 여부를 확인해 주세요.")
    return list(dict.fromkeys(out))[:8]
