from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.agent_contracts import (
    AgentClaim,
    AgentInputRef,
    SpecialistAgentResult,
    validate_specialist_result_against_profile,
)
from app.services.specialist_role_definitions import get_specialist_role_profile


VERSION = "specialist-agent-runners-v1"


@dataclass(frozen=True)
class SpecialistRunInput:
    role_id: str
    goal: str
    source_paths: tuple[str, ...]
    claim_type: str
    claim_text: str
    missing_uncertainty: str


SPECIALIST_RUN_INPUTS: tuple[SpecialistRunInput, ...] = (
    SpecialistRunInput(
        role_id="video_observation_agent",
        goal="영상 관찰값을 후보, 확인 필요, 반영 가능 상태로 분리한다.",
        source_paths=("video_input_contract",),
        claim_type="video_observation_contract",
        claim_text="영상 관찰값은 후보와 확정 가능 상태로 분리되어 Agent 입력 계약에 연결됩니다.",
        missing_uncertainty="영상 관찰 계약이 없어 영상 기반 사실은 판단에 직접 반영할 수 없습니다.",
    ),
    SpecialistRunInput(
        role_id="fact_arbitration_agent",
        goal="사용자 입력과 영상 관찰값의 충돌, 보류, 반영 상태를 분리한다.",
        source_paths=("fact_arbitration",),
        claim_type="fact_arbitration",
        claim_text="사용자 입력과 영상 관찰값은 충돌, 보류, 반영 가능 상태로 분리됩니다.",
        missing_uncertainty="입력과 영상 관찰값을 중재한 결과가 없어 충돌 여부를 추가 확인해야 합니다.",
    ),
    SpecialistRunInput(
        role_id="traffic_law_agent",
        goal="확인된 사고 사실과 근거 문서 범위에서 교통법률 쟁점을 안내한다.",
        source_paths=("legal_analysis",),
        claim_type="traffic_law_guidance",
        claim_text="교통법률 쟁점은 확인된 사고 사실과 검색된 근거 문서 범위에서만 안내됩니다.",
        missing_uncertainty="교통법률 분석 결과가 없어 법률 쟁점은 참고 수준으로만 볼 수 있습니다.",
    ),
    SpecialistRunInput(
        role_id="knia_fault_standard_agent",
        goal="사고축과 맞는 KNIA 과실비율 인정기준 후보를 분리한다.",
        source_paths=("knia_match_summary", "knia_primary_match", "knia_matches"),
        claim_type="knia_fault_standard",
        claim_text="KNIA 기준은 사고축과 직접 관련된 후보만 참고 근거로 사용됩니다.",
        missing_uncertainty="사고축에 맞는 KNIA 기준 후보가 충분하지 않아 기준 확정은 보류됩니다.",
    ),
    SpecialistRunInput(
        role_id="fault_ratio_agent",
        goal="KNIA, 법률 근거, 확인된 사실 범위에서 참고 과실비율을 산정한다.",
        source_paths=("fault_ratio",),
        claim_type="fault_ratio_reference",
        claim_text="참고 과실비율은 확인된 사실과 사고축에 맞는 근거 범위에서만 산정됩니다.",
        missing_uncertainty="과실비율 산정 결과가 없어 참고 비율을 제시할 수 없습니다.",
    ),
    SpecialistRunInput(
        role_id="criminal_liability_agent",
        goal="형사책임 가능성과 신고, 조치 필요성을 조건부로 안내한다.",
        source_paths=("legal_liability",),
        claim_type="criminal_liability_guidance",
        claim_text="형사책임 가능성은 확인된 사실과 법률 근거 범위에서 조건부로 안내됩니다.",
        missing_uncertainty="형사책임 분석 결과가 없어 신고와 조치 필요성을 추가 확인해야 합니다.",
    ),
    SpecialistRunInput(
        role_id="insurance_claim_agent",
        goal="보험 접수, 증빙 보전, 분쟁 대응 절차를 안내한다.",
        source_paths=("insurance_guide",),
        claim_type="insurance_claim_guidance",
        claim_text="보험 처리 안내는 확인된 사고 사실과 제출 가능한 증빙 범위에서 제시됩니다.",
        missing_uncertainty="보험 처리 분석 결과가 없어 접수와 증빙 준비 항목을 추가 확인해야 합니다.",
    ),
    SpecialistRunInput(
        role_id="evidence_audit_agent",
        goal="주장과 근거의 직접성, 부족 근거, unsupported claim을 검증한다.",
        source_paths=("evidence_audit", "claim_evidence"),
        claim_type="evidence_audit",
        claim_text="주장과 근거의 직접성, 부족 근거, 미지원 주장은 별도 감사 결과로 분리됩니다.",
        missing_uncertainty="근거 감사 결과가 없어 주장의 직접성을 확인할 수 없습니다.",
    ),
    SpecialistRunInput(
        role_id="action_guidance_agent",
        goal="검증된 판단 범위에서 다음 대응 순서를 안내한다.",
        source_paths=("action_plan",),
        claim_type="action_guidance",
        claim_text="대응 안내는 검증된 분석 결과와 남은 확인 항목을 기준으로 정렬됩니다.",
        missing_uncertainty="대응 안내 결과가 없어 다음 조치 순서를 별도로 확인해야 합니다.",
    ),
    SpecialistRunInput(
        role_id="presentation_policy_agent",
        goal="사용자에게 표시할 finality, 조건부 결과, 불확실성을 안전하게 정리한다.",
        source_paths=("agent_judgment", "presentation_policy", "elderly_friendly_report"),
        claim_type="presentation_policy",
        claim_text="사용자 표시 문구는 새 사실을 추가하지 않고 finality와 불확실성을 분리합니다.",
        missing_uncertainty="표현 정책 결과가 없어 사용자 표시 finality를 추가 확인해야 합니다.",
    ),
)


def attach_specialist_agent_results(output: dict[str, Any]) -> dict[str, Any]:
    results = [run_specialist_agent(item, output).model_dump() for item in SPECIALIST_RUN_INPUTS]
    output["specialist_agent_results"] = {
        "version": VERSION,
        "result_count": len(results),
        "role_ids": [item["role_id"] for item in results],
        "results": results,
        "safe_metadata_only": True,
    }
    return output


def run_specialist_agent(run_input: SpecialistRunInput, output: dict[str, Any]) -> SpecialistAgentResult:
    profile = get_specialist_role_profile(run_input.role_id)
    refs = _source_refs(run_input.source_paths, output)
    if refs:
        result = SpecialistAgentResult(
            role_id=profile.role_id,
            goal=run_input.goal,
            input_facts_used=_input_refs(output),
            evidence_used=refs,
            claims=[
                AgentClaim(
                    claim_type=run_input.claim_type,
                    text=run_input.claim_text,
                    evidence_refs=refs,
                    support_level="partial",
                )
            ],
            finality="needs_review",
            summary=run_input.claim_text,
        )
    else:
        result = SpecialistAgentResult(
            role_id=profile.role_id,
            goal=run_input.goal,
            input_facts_used=_input_refs(output),
            uncertainties=[run_input.missing_uncertainty],
            finality="needs_review",
            summary=run_input.missing_uncertainty,
        )
    return validate_specialist_result_against_profile(result, profile)


def _source_refs(source_paths: tuple[str, ...], output: dict[str, Any]) -> list[AgentInputRef]:
    refs: list[AgentInputRef] = []
    for path in source_paths:
        value = output.get(path)
        if _has_value(value):
            refs.append(AgentInputRef(ref_type=_ref_type_for_path(path), field_path=path, visibility="internal"))
    return refs


def _input_refs(output: dict[str, Any]) -> list[AgentInputRef]:
    refs = [
        AgentInputRef(ref_type="structured_fact", field_path="structured_facts", visibility="internal"),
    ]
    if output.get("video_input_contract"):
        refs.append(AgentInputRef(ref_type="video_observation", field_path="video_input_contract", visibility="internal"))
    return refs


def _ref_type_for_path(path: str) -> str:
    if path in {"video_input_contract"}:
        return "video_observation"
    if path in {"knia_match_summary", "knia_primary_match", "knia_matches"}:
        return "evidence"
    if path in {"evidence_audit", "claim_evidence"}:
        return "agent_result"
    return "agent_result"


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True
