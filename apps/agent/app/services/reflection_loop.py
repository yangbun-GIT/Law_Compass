from __future__ import annotations

from typing import Any

VERSION = "agent-reflection-loop-v1"
MAX_REQUERY_ATTEMPTS = 1

REQUERYABLE_REQUIREMENTS = {
    "total_evidence",
    "scenario_relevant_evidence",
    "average_score",
    "family:legal",
    "family:knia",
}

REQUERY_TERMS: dict[str, tuple[str, ...]] = {
    "total_evidence": ("교통사고 법률 근거", "교통사고 과실비율 기준", "교통사고 책임 근거"),
    "scenario_relevant_evidence": ("동일 사고 유형 과실비율", "사고 유형별 과실 기준", "교통사고 과실비율 인정기준"),
    "average_score": ("도로교통법 주의의무", "교통사고 적용 기준", "공식 법률 근거"),
    "family:legal": ("도로교통법 안전거리", "도로교통법 사고 후 조치", "교통사고 법적 책임"),
    "family:knia": ("KNIA 과실비율 인정기준", "과실비율 인정기준 기본과실", "자동차사고 과실비율 기준"),
}

SCENARIO_REQUERY_TERMS: dict[str, tuple[str, ...]] = {
    "rear_end_collision": ("후방추돌 과실비율", "정차 중 후미추돌 안전거리", "추돌사고 기본과실"),
    "lane_change_collision": ("차선변경 사고 과실비율", "진로변경 사고 기본과실", "방향지시등 차선변경 과실"),
    "intersection_signal_violation": ("교차로 신호위반 사고 과실비율", "교차로 진입 신호위반 책임", "신호위반 사고 기본과실"),
    "pedestrian_crosswalk_accident": ("횡단보도 보행자 사고 과실비율", "보행자 보호의무 사고", "횡단보도 사고 법률 근거"),
    "school_zone_child_accident": ("어린이보호구역 사고 법률", "민식이법 어린이 사고", "스쿨존 보행자 사고 책임"),
    "bicycle_collision": ("자전거 교통사고 과실비율", "자전거 충돌 사고 책임", "자전거 사고 과실 기준"),
}


def build_requery_plan(
    *,
    evidence_audit: dict[str, Any],
    input_requirements: dict[str, Any],
    scenario_type: str | None = None,
    description_text: str | None = None,
    attempt: int = 0,
) -> dict[str, Any]:
    coverage = evidence_audit.get("scenario_evidence_coverage") or {}
    missing_requirements = list(coverage.get("missing_requirements") or [])
    blocking_fields = list(input_requirements.get("blocking_fields") or [])
    requery_reasons = [item for item in missing_requirements if item in REQUERYABLE_REQUIREMENTS]
    should_requery = bool(requery_reasons) and attempt < MAX_REQUERY_ATTEMPTS

    return {
        "version": VERSION,
        "attempt": attempt,
        "max_attempts": MAX_REQUERY_ATTEMPTS,
        "should_requery": should_requery,
        "requery_reasons": requery_reasons,
        "missing_requirements": missing_requirements,
        "blocking_fields": blocking_fields,
        "query_terms": _query_terms(requery_reasons, scenario_type=scenario_type, description_text=description_text),
        "user_message": _user_message(
            blocking_fields=blocking_fields,
            missing_requirements=missing_requirements,
            should_requery=should_requery,
        ),
        "recovery_suggestions": _recovery_suggestions(missing_requirements, blocking_fields),
        "next_action": "requery_evidence" if should_requery else _next_action(blocking_fields, coverage),
    }


def build_reflection_loop_result(
    *,
    initial_plan: dict[str, Any],
    final_evidence_audit: dict[str, Any],
    input_requirements: dict[str, Any],
    followup_loop: dict[str, Any],
    judgment_contract: dict[str, Any],
    requery_attempted: bool,
    requery_added_count: int,
) -> dict[str, Any]:
    coverage = final_evidence_audit.get("scenario_evidence_coverage") or {}
    blocking_fields = list(input_requirements.get("blocking_fields") or [])
    finality = judgment_contract.get("presentation_policy", {}).get("finality") or judgment_contract.get("finality")
    if judgment_contract.get("overall_status") == "evidence_supported" and coverage.get("decision_ready"):
        status = "resolved"
        next_action = "finalize"
    elif blocking_fields:
        status = "waiting_for_input"
        next_action = "request_missing_input"
    elif finality in {"reference_only", "blocked_for_final"} or judgment_contract.get("must_not_present_as_final"):
        status = "reference_only"
        next_action = "present_reference_only"
    else:
        status = "needs_review"
        next_action = "manual_review"

    return {
        "version": VERSION,
        "status": status,
        "max_iterations": MAX_REQUERY_ATTEMPTS,
        "iterations_used": 1 if requery_attempted else 0,
        "requery_attempted": requery_attempted,
        "requery_added_evidence_count": requery_added_count,
        "initial_requery_reasons": list(initial_plan.get("requery_reasons") or []),
        "initial_query_terms": list(initial_plan.get("query_terms") or []),
        "final_missing_requirements": list(coverage.get("missing_requirements") or []),
        "blocking_fields": blocking_fields,
        "remaining_question_count": followup_loop.get("remaining_question_count", 0),
        "next_action": next_action,
        "finality": finality,
        "user_message": _final_user_message(
            status=status,
            requery_attempted=requery_attempted,
            requery_added_count=requery_added_count,
            blocking_fields=blocking_fields,
            missing_requirements=list(coverage.get("missing_requirements") or []),
        ),
        "recovery_suggestions": _recovery_suggestions(
            list(coverage.get("missing_requirements") or []),
            blocking_fields,
        ),
    }


def _query_terms(reasons: list[str], *, scenario_type: str | None = None, description_text: str | None = None) -> list[str]:
    terms: list[str] = []
    if scenario_type:
        terms.extend(SCENARIO_REQUERY_TERMS.get(scenario_type, ()))
    for reason in reasons:
        terms.extend(REQUERY_TERMS.get(reason, (reason,)))
    if description_text:
        normalized = description_text.strip()
        if "정차" in normalized and ("뒤" in normalized or "후방" in normalized or "후미" in normalized):
            terms.extend(("정차 중 후방추돌 과실비율", "정차 차량 추돌 안전거리"))
        if "차선" in normalized or "진로" in normalized:
            terms.extend(("차선변경 사고 과실비율", "진로변경 과실비율 인정기준"))
        if "신호" in normalized:
            terms.extend(("신호위반 사고 과실비율", "교차로 신호 사고 법률 근거"))
    return list(dict.fromkeys(terms))[:10]


def _next_action(blocking_fields: list[str], coverage: dict[str, Any]) -> str:
    if blocking_fields or "required_input_fields" in list(coverage.get("missing_requirements") or []):
        return "request_missing_input"
    if coverage.get("decision_ready"):
        return "finalize"
    return "present_reference_only"


def _user_message(*, blocking_fields: list[str], missing_requirements: list[str], should_requery: bool) -> str:
    if blocking_fields:
        return "필수 사고 사실이 부족해 보완 입력을 먼저 확인해야 합니다."
    if should_requery:
        return "사고 유형에 맞는 법률·KNIA 근거를 한 번 더 좁혀 검색합니다."
    if missing_requirements:
        return "일부 근거 조건이 부족해 결과를 참고용으로 제한합니다."
    return "입력과 근거 조건을 확인했습니다."


def _final_user_message(
    *,
    status: str,
    requery_attempted: bool,
    requery_added_count: int,
    blocking_fields: list[str],
    missing_requirements: list[str],
) -> str:
    if status == "waiting_for_input" or blocking_fields:
        return "필수 사고 사실이 남아 있어 보완 답변을 받은 뒤 다시 판단하는 것이 안전합니다."
    if status == "reference_only":
        if requery_attempted:
            return f"근거를 한 번 더 검색했지만 확정 판단에 필요한 조건이 남아 참고용으로 표시합니다. 추가 근거 {requery_added_count}개를 확인했습니다."
        return "확정 판단에 필요한 근거 조건이 남아 참고용으로 표시합니다."
    if status == "resolved":
        if requery_attempted:
            return f"부족한 근거를 재검색해 추가 근거 {requery_added_count}개를 확인했고 판단 조건을 통과했습니다."
        return "입력, 근거, 판단 조건을 통과했습니다."
    if missing_requirements:
        return "자동 판단만으로 확정하기 어려운 근거 조건이 남아 있습니다."
    return "검토가 필요한 상태입니다."


def _recovery_suggestions(missing_requirements: list[str], blocking_fields: list[str]) -> list[str]:
    suggestions: list[str] = []
    if blocking_fields:
        suggestions.append("보완 질문에 답하면 같은 케이스에서 재분석할 수 있습니다.")
    if "family:knia" in missing_requirements:
        suggestions.append("KNIA 과실비율 기준이 부족하면 사고 유형과 기준번호를 더 좁혀 확인해야 합니다.")
    if "family:legal" in missing_requirements:
        suggestions.append("법률 근거가 부족하면 도로교통법상 주의의무와 사고 후 조치 근거를 추가 확인해야 합니다.")
    if "scenario_relevant_evidence" in missing_requirements:
        suggestions.append("현재 사고 유형과 직접 맞는 근거가 부족해 같은 유형의 기준을 우선 보강해야 합니다.")
    if "average_score" in missing_requirements:
        suggestions.append("검색 근거의 관련성이 낮아 더 구체적인 사고 사실이 필요합니다.")
    if not suggestions and missing_requirements:
        suggestions.append("부족한 근거 조건이 남아 결과를 참고용으로 확인해야 합니다.")
    return list(dict.fromkeys(suggestions))[:4]
