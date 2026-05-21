from __future__ import annotations

from typing import Any


SUPPORT_DIRECT = "direct"
SUPPORT_PARTIAL = "partial"
SUPPORT_INSUFFICIENT = "insufficient"

ANY_EVIDENCE_CAVEAT = "연결된 근거가 부족하므로 확정 판단이 아니라 참고 정보로만 확인해야 합니다."
LEGAL_EVIDENCE_CAVEAT = "직접적인 법률 근거가 부족하므로 법규·형사책임 판단은 추가 확인이 필요합니다."
KNIA_EVIDENCE_CAVEAT = "직접적인 KNIA 과실비율 기준 근거가 부족하므로 과실비율은 일반 추정으로만 보아야 합니다."
INSURANCE_EVIDENCE_CAVEAT = "보험 처리 안내는 입력 사실과 일반 절차를 바탕으로 한 참고 정보이며, 보험사 심사 결과와 달라질 수 있습니다."


def guard_traffic_law_output(data: dict[str, Any] | None, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    output = _guard_dict(data, evidence, required_family="legal")
    output.setdefault("required_facts", [])
    if output["evidence_support_level"] != SUPPORT_DIRECT:
        _append_unique(output, "caveats", LEGAL_EVIDENCE_CAVEAT)
    return output


def guard_fault_ratio_output(data: dict[str, Any] | None, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    output = _guard_dict(data, evidence, required_family="knia")
    output.setdefault("key_factors", ["사고 유형", "입력 사실", "관련 법규와 KNIA 기준"])
    output["my"] = _bounded_percent(output.get("my"), fallback=50)
    output["other"] = _bounded_percent(output.get("other"), fallback=100 - output["my"])
    if output["my"] + output["other"] != 100:
        other = 100 - output["my"]
        output["other"] = max(0, min(100, other))
        _append_unique(output, "caveats", "과실비율 합계가 100이 아니어서 참고 표시용으로 보정했습니다.")

    support = output["evidence_support_level"]
    if support == SUPPORT_INSUFFICIENT:
        output["confidence"] = _cap_confidence(output.get("confidence"), 0.45)
        _append_unique(output, "caveats", KNIA_EVIDENCE_CAVEAT)
    elif support == SUPPORT_PARTIAL:
        output["confidence"] = _cap_confidence(output.get("confidence"), 0.65)
        _append_unique(output, "caveats", "KNIA 직접 기준이 아닌 간접 근거가 포함되어 과실비율 확정에는 추가 확인이 필요합니다.")
    else:
        output["confidence"] = _cap_confidence(output.get("confidence"), 0.85)
    return output


def guard_criminal_liability_output(data: dict[str, Any] | None, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    output = _guard_dict(data, evidence, required_family="legal")
    output.setdefault("checklist", [])
    if output["evidence_support_level"] != SUPPORT_DIRECT:
        _append_unique(output, "caveats", LEGAL_EVIDENCE_CAVEAT)
        output.setdefault("decision_status", "needs_review")
    else:
        output.setdefault("decision_status", "reference_only")
    return output


def guard_insurance_output(data: dict[str, Any] | None, evidence: list[dict[str, Any]]) -> dict[str, Any]:
    output = _guard_dict(data, evidence, required_family="any")
    output.setdefault("steps", [])
    output.setdefault("required_documents", [])
    _append_unique(output, "caveats", INSURANCE_EVIDENCE_CAVEAT)
    return output


def _guard_dict(data: dict[str, Any] | None, evidence: list[dict[str, Any]], *, required_family: str) -> dict[str, Any]:
    output = dict(data or {})
    output["evidence_count"] = len(evidence)
    output["evidence_ids"] = _evidence_ids(evidence)
    output["evidence_support_level"] = _support_level(evidence, required_family=required_family)
    if output["evidence_support_level"] == SUPPORT_INSUFFICIENT:
        _append_unique(output, "caveats", ANY_EVIDENCE_CAVEAT)
    return output


def _support_level(evidence: list[dict[str, Any]], *, required_family: str) -> str:
    if not evidence:
        return SUPPORT_INSUFFICIENT
    if required_family == "any":
        return SUPPORT_DIRECT
    families = {_family(item) for item in evidence}
    if required_family in families:
        return SUPPORT_DIRECT
    return SUPPORT_PARTIAL


def _family(item: dict[str, Any]) -> str:
    source_type = str(item.get("source_type") or "").lower()
    source = " ".join(
        [
            str(item.get("source") or ""),
            str(item.get("title") or ""),
            str(item.get("source_url") or ""),
            str(item.get("law_name") or ""),
        ]
    ).lower()
    if source_type.startswith("knia") or "knia" in source or "과실비율정보포털" in source:
        return "knia"
    if item.get("chunk_id") or item.get("law_name") or "law.go.kr" in source or "법" in source:
        return "legal"
    return "general"


def _evidence_ids(evidence: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for item in evidence[:6]:
        ref = item.get("chunk_id") or item.get("source_url") or item.get("title")
        if ref:
            ids.append(str(ref))
    return ids


def _append_unique(output: dict[str, Any], key: str, value: str) -> None:
    current = output.get(key) or []
    if isinstance(current, (str, bytes)):
        current = [current]
    elif not isinstance(current, list):
        current = [current]
    values = [str(item) for item in current if item]
    if value not in values:
        values.append(value)
    output[key] = values


def _bounded_percent(value: Any, *, fallback: int) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = fallback
    return max(0, min(100, number))


def _cap_confidence(value: Any, maximum: float) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = maximum
    return round(max(0.0, min(maximum, confidence)), 2)
