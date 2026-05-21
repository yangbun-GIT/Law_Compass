from __future__ import annotations

import hashlib
from typing import Any


def validate_claim_evidence(
    *,
    legal_analysis: dict[str, Any],
    fault_ratio: dict[str, Any],
    legal_liability: dict[str, Any],
    insurance_guide: dict[str, Any],
    action_plan: list[str],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence_refs = [_evidence_ref(item) for item in evidence]
    legal_refs = [ref for ref in evidence_refs if ref["family"] == "legal"]
    knia_refs = [ref for ref in evidence_refs if ref["family"] == "knia"]
    any_refs = evidence_refs[:6]

    claims: list[dict[str, Any]] = []
    claims.extend(_legal_claims(legal_analysis, legal_refs, any_refs))
    claims.extend(_fault_claims(fault_ratio, knia_refs, any_refs))
    claims.extend(_liability_claims(legal_liability, legal_refs, any_refs))
    claims.extend(_insurance_claims(insurance_guide, any_refs))
    claims.extend(_action_claims(action_plan, any_refs))

    unsupported = [claim for claim in claims if claim["support_level"] == "unsupported"]
    weak = [claim for claim in claims if claim["support_level"] == "weak"]
    supported_count = len(claims) - len(unsupported)
    coverage_ratio = round(supported_count / len(claims), 4) if claims else 0.0
    coverage_level = "high" if coverage_ratio >= 0.85 and not unsupported else ("medium" if coverage_ratio >= 0.6 else "low")

    warnings: list[str] = []
    if unsupported:
        warnings.append("일부 판단은 연결된 근거가 없어 단정 표현을 피해야 합니다.")
    if weak:
        warnings.append("일부 판단은 간접 근거만 있어 추가 확인이 필요합니다.")
    if not knia_refs:
        warnings.append("KNIA 기준 근거가 없어 과실비율은 일반 추정으로만 표시해야 합니다.")
    if not legal_refs:
        warnings.append("법률 근거가 없어 법규·형사책임 판단은 낮은 신뢰도로 표시해야 합니다.")

    return {
        "coverage_level": coverage_level,
        "coverage_ratio": coverage_ratio,
        "claim_count": len(claims),
        "supported_claim_count": supported_count,
        "unsupported_claim_count": len(unsupported),
        "weak_claim_count": len(weak),
        "claims": claims,
        "unsupported_claims": unsupported,
        "warnings": list(dict.fromkeys(warnings)),
    }


def apply_claim_evidence_audit(evidence_audit: dict[str, Any], claim_evidence: dict[str, Any]) -> dict[str, Any]:
    updated = dict(evidence_audit)
    weak_points = list(updated.get("weak_points") or [])
    updated["claim_evidence_coverage"] = {
        "level": claim_evidence.get("coverage_level"),
        "ratio": claim_evidence.get("coverage_ratio"),
        "unsupported_claim_count": claim_evidence.get("unsupported_claim_count", 0),
        "weak_claim_count": claim_evidence.get("weak_claim_count", 0),
    }
    for warning in claim_evidence.get("warnings") or []:
        if warning not in weak_points:
            weak_points.append(warning)
    updated["weak_points"] = weak_points
    if claim_evidence.get("coverage_level") == "low":
        updated["uncertainty_level"] = "high"
    elif claim_evidence.get("coverage_level") == "medium" and updated.get("uncertainty_level") == "low":
        updated["uncertainty_level"] = "medium"
    return updated


def _legal_claims(legal_analysis: dict[str, Any], legal_refs: list[dict[str, Any]], any_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    refs = _prefer_used_refs(legal_refs or any_refs, legal_analysis.get("used_evidence_ids") or legal_analysis.get("evidence_ids"))
    rules = [str(x) for x in legal_analysis.get("applicable_rules") or [] if x]
    if rules:
        claims.append(_claim("legal_rules", f"적용 가능 법규: {', '.join(rules[:5])}", refs, required_family="legal"))
    issue = str(legal_analysis.get("legal_issue_summary") or "").strip()
    if issue:
        claims.append(_claim("legal_issue_summary", issue, refs, required_family="legal"))
    flags = [str(x) for x in legal_analysis.get("risk_flags") or [] if x]
    if flags:
        claims.append(_claim("legal_risk_flags", f"법률 리스크 검토 항목: {', '.join(flags[:5])}", refs, required_family="legal"))
    return claims


def _fault_claims(fault_ratio: dict[str, Any], knia_refs: list[dict[str, Any]], any_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    refs = _prefer_used_refs(knia_refs or any_refs, fault_ratio.get("used_evidence_ids") or fault_ratio.get("evidence_ids"))
    my = fault_ratio.get("my")
    other = fault_ratio.get("other")
    if isinstance(my, (int, float)) and isinstance(other, (int, float)):
        claims.append(_claim("fault_ratio_estimate", f"참고 과실비율: 내 책임 {int(my)}%, 상대방 {int(other)}%", refs, required_family="knia"))
    basis = str(fault_ratio.get("basis") or "").strip()
    if basis:
        claims.append(_claim("fault_ratio_basis", basis, refs, required_family="knia"))
    return claims


def _liability_claims(legal_liability: dict[str, Any], legal_refs: list[dict[str, Any]], any_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    refs = _prefer_used_refs(legal_refs or any_refs, legal_liability.get("used_evidence_ids") or legal_liability.get("evidence_ids"))
    if "reporting_required" in legal_liability:
        label = "경찰 신고 또는 형사책임 검토가 필요합니다." if legal_liability.get("reporting_required") else "현재 입력만으로는 신고 필요성이 높게 보이지 않습니다."
        claims.append(_claim("reporting_required", label, refs, required_family="legal"))
    level = legal_liability.get("criminal_risk_level")
    if level:
        claims.append(_claim("criminal_risk_level", f"형사책임 리스크 수준: {level}", refs, required_family="legal"))
    return claims


def _insurance_claims(insurance_guide: dict[str, Any], any_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = str(insurance_guide.get("summary") or "").strip()
    if not summary:
        return []
    refs = _prefer_used_refs(any_refs, insurance_guide.get("used_evidence_ids") or insurance_guide.get("evidence_ids"))
    return [_claim("insurance_summary", summary, refs, required_family="any")]


def _action_claims(action_plan: list[str], any_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for idx, action in enumerate(action_plan[:3], start=1):
        if str(action).strip():
            claims.append(_claim(f"action_plan_{idx}", str(action), any_refs, required_family="any"))
    return claims


def _claim(claim_type: str, text: str, refs: list[dict[str, Any]], *, required_family: str) -> dict[str, Any]:
    selected = refs[:4]
    support_level = "supported" if selected else "unsupported"
    if selected and required_family != "any" and not any(ref["family"] == required_family for ref in selected):
        support_level = "weak"
    return {
        "claim_id": _claim_id(claim_type, text),
        "claim_type": claim_type,
        "text": text,
        "required_evidence_family": required_family,
        "support_level": support_level,
        "evidence_refs": selected,
    }


def _prefer_used_refs(refs: list[dict[str, Any]], used_ids: Any) -> list[dict[str, Any]]:
    if isinstance(used_ids, (str, bytes)):
        used_items = [used_ids]
    else:
        used_items = used_ids or []
    ids = {str(item) for item in used_items if item}
    if not ids:
        return refs
    selected = [ref for ref in refs if str(ref.get("ref_id")) in ids]
    return selected or refs


def _evidence_ref(item: dict[str, Any]) -> dict[str, Any]:
    source_type = str(item.get("source_type") or "")
    family = _family(item)
    ref_id = str(item.get("chunk_id") or item.get("source_url") or item.get("title") or source_type or "evidence")
    return {
        "ref_id": ref_id,
        "title": item.get("title"),
        "source_type": source_type or None,
        "source_url": item.get("source_url"),
        "used_for": item.get("used_for"),
        "family": family,
    }


def _family(item: dict[str, Any]) -> str:
    source_type = str(item.get("source_type") or "").lower()
    source = " ".join([str(item.get("source") or ""), str(item.get("title") or ""), str(item.get("source_url") or "")]).lower()
    if source_type.startswith("knia") or "knia" in source or "과실비율정보포털" in source:
        return "knia"
    if item.get("chunk_id") or item.get("law_name") or "law.go.kr" in source or "법" in source:
        return "legal"
    return "general"


def _claim_id(claim_type: str, text: str) -> str:
    digest = hashlib.sha1(f"{claim_type}:{text}".encode("utf-8")).hexdigest()[:10]
    return f"{claim_type}:{digest}"
