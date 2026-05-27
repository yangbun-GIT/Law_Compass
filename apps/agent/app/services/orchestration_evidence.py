from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.knia.knia_fault_adjuster import estimate_knia_fault
from app.services.knia.knia_matcher import (
    _is_centerline_primary_mismatch,
    is_knia_match_compatible_with_scenario,
    match_knia_charts,
)
from app.services.knia.knia_report_adapter import build_knia_evidence
from app.services.knia.knia_repository import KniaRepository
from app.services.orchestration_context import CaseContext
from app.services.rag.two_stage_cache import search_knia_json_cached
from app.services.rag_client import retrieve_for_scenario
from app.services.scenario_search_terms import evidence_query_payload


@dataclass
class EvidenceBundle:
    knia_result: dict[str, Any]
    knia_matches: list[dict[str, Any]]
    evidence_query: dict[str, Any]
    knia_json_result: dict[str, Any]
    knia_json_evidence: list[dict[str, Any]]
    knia_fault_estimate: dict[str, Any] | None
    knia_reference_evidence: list[dict[str, Any]]
    knia_evidence: list[dict[str, Any]]
    retrieval: dict[str, Any]
    legal_evidence: list[dict[str, Any]]
    evidence: list[dict[str, Any]]


def collect_evidence_stage(context: CaseContext, video_metadata: dict[str, Any] | None) -> EvidenceBundle:
    normalized = context.normalized
    scenario = context.scenario
    knia_result = match_knia_charts(
        description_text=normalized["description_text"],
        structured_facts=normalized["structured_facts"],
        selected_keywords=normalized["selected_keywords"],
        scenario_type=scenario["scenario_type"],
        accident_party_type=scenario.get("accident_party_type"),
        limit=5,
    )
    scenario_tags = scenario.get("scenario_tags") or []
    knia_matches = _filter_primary_knia_evidence(knia_result.get("items") or [], scenario_tags, scenario.get("scenario_type"))
    knia_matches = _filter_pedestrian_target_mismatch(knia_matches, normalized["structured_facts"], scenario.get("accident_party_type"))
    evidence_query = evidence_query_payload(
        description_text=normalized["description_text"],
        facts=normalized["structured_facts"],
        selected_keywords=normalized["selected_keywords"],
        scenario_type=scenario.get("scenario_type"),
        scenario_tags=scenario.get("scenario_tags"),
        accident_party_type=scenario.get("accident_party_type"),
    )
    knia_json_result = search_knia_json_cached(
        evidence_query["query_text"],
        accident_party_type=scenario.get("accident_party_type"),
        scenario_type=scenario.get("scenario_type"),
        limit=5,
    )
    knia_json_evidence = _filter_primary_knia_evidence(knia_json_result.get("items") or [], scenario_tags, scenario.get("scenario_type"))
    knia_json_evidence = _filter_pedestrian_target_mismatch(knia_json_evidence, normalized["structured_facts"], scenario.get("accident_party_type"))
    knia_fault_estimate: dict[str, Any] | None = None
    knia_reference_evidence: list[dict[str, Any]] = []
    if knia_matches:
        primary = knia_matches[0]
        try:
            knia_fault_estimate = estimate_knia_fault(
                chart_no=primary.get("chart_no"),
                chart_type=primary.get("chart_type") or "1",
                description_text=normalized["description_text"],
                selected_keywords=normalized["selected_keywords"],
                structured_facts=normalized["structured_facts"],
                video_metadata=video_metadata or {},
                scenario_type=scenario.get("scenario_type"),
                accident_party_type=scenario.get("accident_party_type"),
            )
            knia_reference_evidence.extend(_knia_estimate_to_evidence(knia_fault_estimate))
            refs = KniaRepository().get_chart_references(primary.get("chart_no"), primary.get("chart_type") or "1")
            knia_reference_evidence.extend(_knia_refs_to_evidence(primary, refs))
        except Exception:
            knia_fault_estimate = None

    knia_evidence = normalize_evidence_items(
        [*build_knia_evidence(knia_matches), *knia_reference_evidence, *knia_json_evidence],
        default_source="과실비율정보포털",
    )
    knia_evidence = _filter_pedestrian_target_mismatch(knia_evidence, normalized["structured_facts"], scenario.get("accident_party_type"))
    retrieval = retrieve_for_scenario(
        scenario_type=scenario["scenario_type"],
        scenario_tags=scenario["scenario_tags"],
        description_text=normalized["description_text"],
        facts={**normalized["structured_facts"], "accident_party_type": scenario.get("accident_party_type")},
        selected_keywords=normalized["selected_keywords"],
        video_context=context.video_context,
        limit=8,
    )
    legal_evidence = normalize_evidence_items(retrieval["items"], default_source="법률 근거")
    legal_evidence = _filter_primary_knia_evidence(legal_evidence, scenario_tags, scenario.get("scenario_type"))
    legal_evidence = _filter_pedestrian_target_mismatch(legal_evidence, normalized["structured_facts"], scenario.get("accident_party_type"))
    return EvidenceBundle(
        knia_result=knia_result,
        knia_matches=knia_matches,
        evidence_query=evidence_query,
        knia_json_result=knia_json_result,
        knia_json_evidence=knia_json_evidence,
        knia_fault_estimate=knia_fault_estimate,
        knia_reference_evidence=knia_reference_evidence,
        knia_evidence=knia_evidence,
        retrieval=retrieval,
        legal_evidence=legal_evidence,
        evidence=[*knia_evidence, *legal_evidence],
    )


def _filter_primary_knia_evidence(
    items: list[dict[str, Any]],
    scenario_tags: list[str],
    scenario_type: str | None = None,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for item in items:
        if _is_centerline_primary_mismatch(scenario_tags, item):
            continue
        if scenario_type and not is_knia_match_compatible_with_scenario(item, scenario_type):
            continue
        filtered.append(item)
    return filtered


def _filter_pedestrian_target_mismatch(
    items: list[dict[str, Any]],
    facts: dict[str, Any],
    accident_party_type: str | None,
) -> list[dict[str, Any]]:
    partner = str(facts.get("collision_partner_type") or "").strip().lower()
    direct_partner = str(facts.get("direct_collision_partner_type") or "").strip().lower()
    vehicle_context = accident_party_type == "car_vs_car" or partner in {"vehicle", "car", "truck", "bus", "van"} or direct_partner in {"vehicle", "car", "truck", "bus", "van"}
    if not vehicle_context:
        return items
    filtered: list[dict[str, Any]] = []
    for item in items:
        text = " ".join(
            str(item.get(key) or "")
            for key in ("title", "article_title", "plain_summary", "related_reason", "accident_summary", "law_name", "source_type")
        ).lower()
        party = str(item.get("accident_party_type") or "").strip().lower()
        tags = " ".join(str(tag).lower() for tag in (item.get("scenario_tags") or item.get("display_tags") or []))
        pedestrian_target = (
            party == "car_vs_person"
            or "pedestrian_crosswalk_accident" in text
            or "school_zone_child_accident" in text
            or any(token in text for token in ("보행자 사고", "보행자 보호", "pedestrian protection", "child protection"))
            or ("pedestrian" in tags and "vehicle" not in tags and "intersection" not in tags and "rear" not in tags)
        )
        if not pedestrian_target:
            filtered.append(item)
    return filtered


def normalize_evidence_items(items: list[dict[str, Any]], *, default_source: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("article_title") or item.get("law_name") or "교통사고 관련 근거"
        source = item.get("source") or item.get("source_label") or default_source
        normalized.append({**item, "title": str(title), "source": str(source)})
    return normalized


def merge_evidence_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = str(item.get("chunk_id") or item.get("source_url") or item.get("title") or "")
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        merged.append(item)
    return merged


def _knia_estimate_to_evidence(estimate: dict[str, Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    source_chart = estimate.get("source_chart") or {}
    base = estimate.get("base_fault") or {}
    if base:
        evidence.append(
            {
                "source_type": "knia_base_fault",
                "title": f"KNIA 원문 기본과실 A{base.get('A')}:B{base.get('B')}",
                "plain_summary": "KNIA 상세 기준에서 수집한 기본과실을 사용했습니다.",
                "source_url": source_chart.get("source_detail_url"),
                "used_for": "과실비율 기본값",
            }
        )
    for item in estimate.get("selected_adjustments") or []:
        effect = item.get("applied_effect") or {}
        evidence.append(
            {
                "source_type": "knia_adjustment_factor",
                "title": f"가감요소: {item.get('label')}",
                "plain_summary": f"A {effect.get('A', 0):+d}, B {effect.get('B', 0):+d}로 반영했습니다.",
                "related_reason": ", ".join(item.get("matched_by") or []),
                "source_url": item.get("source_detail_url") or source_chart.get("source_detail_url"),
                "used_for": "과실비율 가감요소",
            }
        )
    return evidence


def _knia_refs_to_evidence(primary: dict[str, Any], refs: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    source_url = primary.get("source_detail_url") or primary.get("source_url")
    evidence: list[dict[str, Any]] = []
    for item in (refs.get("adjustment_explanations") or [])[:3]:
        evidence.append(
            {
                "source_type": "knia_adjustment_explanation",
                "title": item.get("title") or "KNIA 수정요소해설",
                "plain_summary": item.get("body"),
                "source_url": item.get("source_detail_url") or source_url,
                "used_for": "가감요소 적용 취지",
            }
        )
    for item in (refs.get("related_laws") or [])[:3]:
        evidence.append(
            {
                "source_type": "knia_related_law",
                "title": item.get("law_title") or "KNIA 관련법규",
                "law_name": item.get("law_title"),
                "plain_summary": item.get("law_text"),
                "source_url": item.get("source_detail_url") or source_url,
                "used_for": "관련 법규 근거",
            }
        )
    for item in (refs.get("case_references") or [])[:2]:
        evidence.append(
            {
                "source_type": "knia_case_reference",
                "title": item.get("case_title") or "KNIA 판례·조정사례",
                "plain_summary": item.get("decision_summary") or item.get("case_body"),
                "source_url": item.get("source_detail_url") or source_url,
                "used_for": "유사 사례 근거",
            }
        )
    return evidence
