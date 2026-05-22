from __future__ import annotations

from typing import Any

from app.services.agent_quality_packet import (
    VERSION as AGENT_QUALITY_PACKET_VERSION,
    build_agent_quality_packet,
)
from app.services.agent_execution_trace import (
    VERSION as AGENT_TRACE_VERSION,
    build_agent_execution_trace,
)
from app.services.elderly_friendly.report_simplifier import build_elderly_friendly_report
from app.services.evidence_source_status import (
    VERSION as EVIDENCE_SOURCE_STATUS_VERSION,
    build_evidence_source_status,
)
from app.services.judgment_contract import apply_judgment_contract_to_output
from app.services.orchestration_analysis import AnalysisBundle
from app.services.orchestration_context import CaseContext
from app.services.orchestration_evidence import EvidenceBundle
from app.services.reflection_loop import VERSION as REFLECTION_LOOP_VERSION


def enrich_analysis_output(
    *,
    output: dict[str, Any],
    context: CaseContext,
    evidence_bundle: EvidenceBundle,
    analysis_bundle: AnalysisBundle,
    judgment_contract: dict[str, Any],
    reflection_loop: dict[str, Any],
) -> dict[str, Any]:
    output = apply_judgment_contract_to_output(output, judgment_contract)
    output["reflection_loop"] = reflection_loop
    output["model_info"]["reflection_loop_version"] = REFLECTION_LOOP_VERSION
    output["claim_evidence"] = analysis_bundle.claim_evidence
    output["knia_json_evidence"] = evidence_bundle.knia_json_evidence
    _attach_knia_fault_estimate(output, evidence_bundle, analysis_bundle)
    output["related_knia_source_links"] = [
        x.get("source_url") for x in evidence_bundle.knia_json_evidence if x.get("source_url")
    ]
    output["model_info"]["retrieval"] = _build_retrieval_model_info(evidence_bundle)
    output["model_info"]["scenario_classifier"] = context.scenario
    output["model_info"]["evidence_source_status"] = build_evidence_source_status(evidence_bundle)
    output["model_info"]["evidence_source_status_version"] = EVIDENCE_SOURCE_STATUS_VERSION
    output["agent_trace"] = build_agent_execution_trace(output)
    output["model_info"]["agent_trace_version"] = AGENT_TRACE_VERSION
    output["agent_quality_packet"] = build_agent_quality_packet(output)
    output["model_info"]["agent_quality_packet_version"] = AGENT_QUALITY_PACKET_VERSION
    output["elderly_friendly_report"] = build_elderly_friendly_report(output)
    return output


def _attach_knia_fault_estimate(
    output: dict[str, Any],
    evidence_bundle: EvidenceBundle,
    analysis_bundle: AnalysisBundle,
) -> None:
    if not evidence_bundle.knia_fault_estimate:
        return

    estimate = evidence_bundle.knia_fault_estimate
    output["knia_base_fault"] = estimate.get("base_fault")
    output["knia_final_fault"] = estimate.get("final_fault")
    output["knia_applied_adjustments"] = estimate.get("selected_adjustments") or []
    output["knia_rejected_adjustments"] = estimate.get("rejected_adjustments") or []
    output["knia_calculation_steps"] = estimate.get("calculation_steps") or []
    output["knia_adjustment_evidence"] = estimate.get("evidence_used") or []
    output["knia_reference_evidence"] = evidence_bundle.knia_reference_evidence
    output.setdefault("elderly_friendly_report", {})["knia_fault_adjustment_card"] = {
        "title": "KNIA 원문 근거 및 가감요소 적용",
        "base_fault": estimate.get("base_fault"),
        "final_fault": estimate.get("final_fault"),
        "user_fault": {
            "my": analysis_bundle.fault_ratio.get("my"),
            "other": analysis_bundle.fault_ratio.get("other"),
            "role": analysis_bundle.fault_ratio.get("user_vehicle_role"),
            "role_label": analysis_bundle.fault_ratio.get("user_vehicle_role_label"),
        },
        "applied_adjustments": estimate.get("selected_adjustments") or [],
        "rejected_adjustments": (estimate.get("rejected_adjustments") or [])[:5],
        "calculation_steps": estimate.get("calculation_steps") or [],
        "notice": estimate.get("notice"),
    }


def _build_retrieval_model_info(evidence_bundle: EvidenceBundle) -> dict[str, Any]:
    return {
        "cache_hit": evidence_bundle.retrieval.get("cache_hit"),
        "cache_key": evidence_bundle.retrieval.get("cache_key"),
        "knia_cache_hit": evidence_bundle.knia_result.get("cache_hit"),
        "knia_cache_key": evidence_bundle.knia_result.get("cache_key"),
        "knia_json_cache": evidence_bundle.knia_json_result.get("cache"),
        "query_expansion_terms": evidence_bundle.retrieval.get("query_expansion_terms")
        or evidence_bundle.evidence_query.get("query_terms"),
        "knia_query_expansion_terms": evidence_bundle.knia_result.get("query_expansion_terms") or [],
    }
