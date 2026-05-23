from __future__ import annotations

from typing import Any


VERSION = "expert-guidance-sections-v1"


def build_expert_guidance_sections(
    *,
    scenario: dict[str, Any],
    facts: dict[str, Any],
    legal_analysis: dict[str, Any],
    fault_ratio: dict[str, Any],
    legal_liability: dict[str, Any],
    insurance_guide: dict[str, Any],
    evidence: list[dict[str, Any]],
    evidence_audit: dict[str, Any],
    claim_evidence: dict[str, Any],
    input_requirements: dict[str, Any] | None = None,
    reflection_loop: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a user-safe expert guidance packet from existing analyst outputs."""

    input_requirements = input_requirements or {}
    reflection_loop = reflection_loop or {}
    basis = _basis_summary(
        evidence,
        context_text=_guidance_context_text(
            scenario=scenario,
            facts=facts,
            legal_analysis=legal_analysis,
            fault_ratio=fault_ratio,
        ),
    )
    missing_facts = _missing_facts(input_requirements, legal_analysis, reflection_loop)
    status = _status(evidence_audit, claim_evidence, missing_facts)
    fault_range = _fault_range(fault_ratio, status)

    return {
        "version": VERSION,
        "status": status,
        "summary": _summary(status, scenario, fault_range),
        "legal_prediction": {
            "title": "법률 관점 예상",
            "summary": _legal_summary(scenario, fault_range, legal_analysis, legal_liability),
            "fault_range_label": fault_range,
            "civil_points": _civil_points(fault_ratio, evidence_audit),
            "criminal_points": _criminal_points(legal_liability),
            "basis": basis,
            "limits": _limits(status, missing_facts),
        },
        "insurance_prediction": {
            "title": "보험 처리 예상",
            "summary": _safe_text(
                insurance_guide.get("summary"),
                "보험 접수 후 대물·대인 처리 여부와 과실비율 협의 가능성을 확인해야 합니다.",
            ),
            "expected_steps": _safe_list(insurance_guide.get("steps"), 5),
            "documents": _safe_list(insurance_guide.get("required_documents"), 6),
            "basis": basis[:3],
        },
        "missing_facts": {
            "title": "추가 확인 필요",
            "items": missing_facts[:6],
        },
        "notice": (
            "이 내용은 유사 근거와 입력 사실을 바탕으로 한 참고용 예상입니다. "
            "실제 결과는 보험사, 분쟁심의, 수사기관, 법원의 판단에 따라 달라질 수 있습니다."
        ),
    }


def _status(evidence_audit: dict[str, Any], claim_evidence: dict[str, Any], missing_facts: list[str]) -> str:
    unsupported = int(claim_evidence.get("unsupported_claim_count") or 0)
    weak = int(claim_evidence.get("weak_claim_count") or 0)
    coverage = str(claim_evidence.get("coverage_level") or evidence_audit.get("uncertainty_level") or "")
    if missing_facts or unsupported > 0:
        return "needs_more_facts"
    if coverage == "high" and weak == 0:
        return "evidence_supported_reference"
    return "reference_only"


def _summary(status: str, scenario: dict[str, Any], fault_range: str) -> str:
    label = _safe_text(scenario.get("accident_party_label"), _scenario_label(str(scenario.get("scenario_type") or "")))
    if status == "needs_more_facts":
        return f"{label}로 보이며, {fault_range}를 좁히려면 핵심 사실을 더 확인해야 합니다."
    if status == "evidence_supported_reference":
        return f"{label}에 대해 확인된 근거를 기준으로 {fault_range} 범위의 참고 판단을 제시합니다."
    return f"{label}에 대해 현재 근거로 가능한 {fault_range} 참고 범위를 제시합니다."


def _legal_summary(
    scenario: dict[str, Any],
    fault_range: str,
    legal_analysis: dict[str, Any],
    legal_liability: dict[str, Any],
) -> str:
    issue = _safe_text(
        legal_analysis.get("legal_issue_summary"),
        "사고 유형과 주요 사실을 기준으로 법률 쟁점을 확인했습니다.",
    )
    risk = str(legal_liability.get("criminal_risk_level") or "unknown")
    risk_label = {
        "high": "형사 쟁점이 높게 검토될 수 있습니다",
        "medium": "형사 쟁점은 보통 수준으로 검토됩니다",
        "low": "형사 쟁점은 낮은 편으로 보입니다",
    }.get(risk, "형사 쟁점은 추가 확인이 필요합니다")
    return f"{issue} 현재는 {fault_range}로 안내하며, {risk_label}."


def _fault_range(fault_ratio: dict[str, Any], status: str) -> str:
    my = _number(fault_ratio.get("my"))
    other = _number(fault_ratio.get("other"))
    if my is None or other is None:
        return "과실범위 확인 필요"
    margin = 5 if status == "evidence_supported_reference" else 10
    my_min = max(0, my - margin)
    my_max = min(100, my + margin)
    other_min = max(0, 100 - my_max)
    other_max = min(100, 100 - my_min)
    if my_min == my_max:
        return f"내 책임 {my}% / 상대 {other}% 참고"
    return f"내 책임 {my_min}~{my_max}% / 상대 {other_min}~{other_max}% 참고"


def _civil_points(fault_ratio: dict[str, Any], evidence_audit: dict[str, Any]) -> list[str]:
    items = _safe_list(fault_ratio.get("key_factors"), 4)
    if not items:
        items = ["사고 유형", "정차·신호·차선변경 여부", "유사 KNIA 기준", "관련 법령 근거"]
    coverage = evidence_audit.get("scenario_evidence_coverage") or {}
    level = coverage.get("coverage_level")
    if level:
        items.append(f"근거 충족도는 {_level_label(level)}입니다.")
    return items[:5]


def _criminal_points(legal_liability: dict[str, Any]) -> list[str]:
    items = _safe_list(legal_liability.get("checklist"), 5)
    if not items:
        items = ["인명피해 여부", "신호위반·중앙선 침범 등 중대한 위반 여부", "사고 후 조치 여부"]
    if legal_liability.get("reporting_required") is True:
        items.insert(0, "신고 또는 형사 절차 검토가 필요할 수 있습니다.")
    return list(dict.fromkeys(items))[:5]


def _basis_summary(evidence: list[dict[str, Any]], *, context_text: str = "") -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in evidence:
        title = _safe_text(
            item.get("title") or item.get("article_title") or item.get("law_name") or item.get("chunk_summary"),
            "교통사고 관련 근거",
        )
        family_key = _family_key(item)
        family = _family_label(item)
        reason = _safe_text(
            item.get("related_reason") or item.get("used_for") or item.get("plain_summary") or item.get("snippet"),
            "입력 사고와 연결해 참고할 수 있는 근거입니다.",
        )
        key = f"{family}:{title}"
        if key in seen:
            continue
        seen.add(key)
        content_text = f"{title} {reason} {item.get('source') or ''} {item.get('law_name') or ''}"
        candidates.append(
            {
                "_family_key": family_key,
                "_relevance_score": str(_relevance_score(content_text, context_text)),
                "family_label": family,
                "title": title,
                "reason": reason,
            }
        )
    return _balanced_basis(candidates)


def _balanced_basis(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    selected_ids: set[int] = set()

    for family_key in ("legal", "knia", "insurance"):
        family_candidates = sorted(
            enumerate(candidates),
            key=lambda pair: int(pair[1].get("_relevance_score") or 0),
            reverse=True,
        )
        for index, item in family_candidates:
            if index in selected_ids or item.get("_family_key") != family_key:
                continue
            selected.append(item)
            selected_ids.add(index)
            break

    relevant_candidates = sorted(
        enumerate(candidates),
        key=lambda pair: int(pair[1].get("_relevance_score") or 0),
        reverse=True,
    )
    for index, item in relevant_candidates:
        if index in selected_ids:
            continue
        if int(item.get("_relevance_score") or 0) <= 0 and _has_core_basis(selected):
            continue
        selected.append(item)
        selected_ids.add(index)
        if len(selected) >= 5:
            break

    return [
        {key: value for key, value in item.items() if key not in {"_family_key", "_relevance_score"}}
        for item in selected[:5]
    ]


def _has_core_basis(items: list[dict[str, str]]) -> bool:
    families = {item.get("_family_key") for item in items}
    return "legal" in families and "knia" in families


def _guidance_context_text(
    *,
    scenario: dict[str, Any],
    facts: dict[str, Any],
    legal_analysis: dict[str, Any],
    fault_ratio: dict[str, Any],
) -> str:
    parts = [
        scenario.get("scenario_type"),
        scenario.get("accident_party_label"),
        scenario.get("summary"),
        legal_analysis.get("legal_issue_summary"),
    ]
    parts.extend(_safe_list(legal_analysis.get("required_facts"), 10))
    parts.extend(_safe_list(fault_ratio.get("key_factors"), 10))
    parts.extend(_flatten_values(facts))
    scenario_type = str(scenario.get("scenario_type") or "")
    if scenario_type == "intersection_signal_violation":
        parts.extend(["intersection", "signal", "신호", "교차로", "좌회전", "cctv"])
    if scenario_type == "rear_end_collision":
        parts.extend(["rear", "stopped", "safe distance", "후방", "정차", "안전거리"])
    if scenario_type == "parking_or_stopped_vehicle_accident":
        parts.extend(["stopped vehicle", "정차"])
    fact_text = " ".join(_flatten_values(facts)).lower()
    if facts.get("crosswalk_nearby") is True or "crosswalk" in fact_text:
        parts.extend(["crosswalk", "pedestrian", "pedestrian signal", "front vehicle", "stop reason"])
    if facts.get("front_vehicle_stopped") is True or "front_vehicle_stopped" in fact_text:
        parts.extend(["front vehicle", "stop reason", "sudden braking", "safe distance"])
    if facts.get("bicycle_involved") is True or facts.get("possible_trigger_vehicle") == "bicycle" or "bicycle" in fact_text:
        parts.extend(["bicycle", "non-contact", "trigger", "time gap", "rear-end bus", "sudden braking"])
    if (
        facts.get("stopped_vehicle_without_lights") is True
        or "without_lights" in fact_text
        or "unlit" in fact_text
        or "무등" in fact_text
        or "스텔스" in fact_text
    ):
        parts.extend(["unlit", "visibility", "night", "무등화", "시인성", "야간"])
    return " ".join(str(part or "") for part in parts).lower()


def _flatten_values(value: Any) -> list[str]:
    if isinstance(value, dict):
        output: list[str] = []
        for key, item in value.items():
            output.append(str(key))
            output.extend(_flatten_values(item))
        return output
    if isinstance(value, list):
        output = []
        for item in value:
            output.extend(_flatten_values(item))
        return output
    if value is None:
        return []
    return [str(value)]


def _relevance_score(content_text: str, context_text: str) -> int:
    content = content_text.lower()
    context = context_text.lower()
    score = 0
    for terms in _topic_groups():
        content_has = any(term in content for term in terms)
        context_has = any(term in context for term in terms)
        if content_has and context_has:
            score += 4
        elif content_has and not context_has:
            score -= 5
    return score


def _topic_groups() -> tuple[tuple[str, ...], ...]:
    return (
        ("signal", "신호", "intersection", "교차로", "cctv", "yellow", "red", "좌회전"),
        ("lane change", "차로변경", "진로변경", "끼어들기", "merge"),
        ("rear", "후방", "뒤차", "추돌", "safe distance", "안전거리"),
        ("stopped", "정차", "정지", "감속"),
        ("crosswalk", "pedestrian", "pedestrian signal", "횡단보도", "보행자", "보행자 신호"),
        ("front vehicle", "stop reason", "sudden braking", "앞차", "정지 사유", "급정거"),
        ("centerline", "중앙선", "obstacle", "장애", "parked vehicle", "주차"),
        ("oncoming", "마주", "대향", "avoidability", "avoid", "회피"),
        ("unlit", "무등", "stealth", "스텔스", "visibility", "시인", "night", "야간"),
        ("speed", "speeding", "speed limit", "속도", "과속", "제한속도"),
        ("criminal", "형사", "civil", "민사", "fatality", "사망"),
        ("bicycle", "자전거", "non-contact", "비접촉", "trigger", "유발"),
    )


def _missing_facts(
    input_requirements: dict[str, Any],
    legal_analysis: dict[str, Any],
    reflection_loop: dict[str, Any],
) -> list[str]:
    questions = []
    for item in input_requirements.get("questions") or []:
        if isinstance(item, dict):
            questions.append(_safe_text(item.get("question") or item.get("label"), "추가 사실 확인이 필요합니다."))
    for item in legal_analysis.get("required_facts") or []:
        questions.append(_safe_text(item, "추가 사실 확인이 필요합니다."))
    for item in reflection_loop.get("recovery_suggestions") or []:
        questions.append(_safe_text(item, "추가 사실 확인이 필요합니다."))
    return list(dict.fromkeys([item for item in questions if item]))[:8]


def _limits(status: str, missing_facts: list[str]) -> list[str]:
    items = ["확정 판결이나 최종 보험 처리 결과가 아니라 참고용 예상입니다."]
    if status == "needs_more_facts":
        items.append("핵심 사실이 보완되기 전에는 과실범위를 넓게 봐야 합니다.")
    if missing_facts:
        items.append("CCTV, 신호체계, 충돌 직전 속도, 정차 사유 같은 사실이 결론을 바꿀 수 있습니다.")
    return items


def _family_key(item: dict[str, Any]) -> str:
    source_type = str(item.get("source_type") or "").lower()
    joined = " ".join(str(item.get(key) or "").lower() for key in ("source", "title", "source_url", "law_name"))
    if source_type.startswith("knia") or "knia" in joined or "fault ratio" in joined or "과실" in joined:
        return "knia"
    if source_type.startswith("insurance") or "insurance" in joined or "보험" in joined:
        return "insurance"
    if source_type.startswith("legal") or item.get("law_name") or "law.go.kr" in joined or "road traffic act" in joined or "법" in joined:
        return "legal"
    return "general"


def _family_label(item: dict[str, Any]) -> str:
    family_key = _family_key(item)
    if family_key == "knia":
        return "KNIA 기준"
    if family_key == "legal":
        return "법률 근거"
    if family_key == "insurance":
        return "보험 처리 근거"
    return "참고 근거"


def _scenario_label(value: str) -> str:
    labels = {
        "rear_end_collision": "후미추돌 사고",
        "intersection_signal_violation": "교차로 신호 사고",
        "lane_change_collision": "차선변경 사고",
        "pedestrian_crosswalk_accident": "보행자 사고",
        "bicycle_collision": "자전거 관련 사고",
        "parking_or_stopped_vehicle_accident": "정차 차량 관련 사고",
    }
    return labels.get(value, "교통사고")


def _level_label(value: Any) -> str:
    return {"high": "높음", "medium": "보통", "low": "낮음"}.get(str(value), _safe_text(value, "보통"))


def _safe_list(value: Any, limit: int) -> list[str]:
    if isinstance(value, list):
        source = value
    elif value:
        source = [value]
    else:
        source = []
    return [_safe_text(item, "") for item in source if _safe_text(item, "")][:limit]


def _safe_text(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if not text or text in {"unknown", "null", "None"}:
        return fallback
    for token in ("chunk_id", "cache_key", "model_info"):
        text = text.replace(token, "")
    return " ".join(text.split()) or fallback


def _number(value: Any) -> int | None:
    try:
        return round(float(value))
    except (TypeError, ValueError):
        return None
