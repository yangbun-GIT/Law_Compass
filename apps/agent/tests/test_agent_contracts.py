import pytest
from pydantic import ValidationError

from app.mcp.tool_registry import bootstrap_tools, list_tools
from app.services.agent_contracts import (
    AgentClaim,
    AgentGoalResult,
    AgentInputRef,
    AgentPlan,
    AgentTask,
    EvidenceRequirement,
    MCPToolErrorPacket,
    SpecialistAgentResult,
    SpecialistRoleProfile,
    build_tool_error_packet,
    list_internal_tool_specs,
    validate_specialist_result_against_profile,
)


def test_agent_packet_contract_is_additive_and_ordered():
    evidence_ref = AgentInputRef(
        ref_type="evidence",
        ref_id="knia-43-2",
        field_path="knia_matches[0]",
        visibility="internal",
    )
    task = AgentTask(
        task_id="task-evidence-1",
        task_type="evidence_retrieval",
        goal="사고축과 맞는 KNIA/법령 근거를 찾는다.",
        input_refs=[AgentInputRef(ref_type="structured_fact", ref_id="scenario", field_path="scenario_type")],
        required_tools=["search_knia_json_rag_tool"],
        required_evidence=[EvidenceRequirement(evidence_type="knia", directness="direct")],
        status="succeeded",
        result_ref="agent_goal_results.evidence_retrieval",
    )
    plan = AgentPlan(
        plan_id="plan-1",
        case_id="case-1",
        trace_id="trace-1",
        tasks=[task],
        execution_order=["task-evidence-1"],
    )
    result = AgentGoalResult(
        goal=task.goal,
        status="succeeded",
        claims=[
            AgentClaim(
                claim_type="knia_basis",
                text="차대차 사고축과 직접 관련된 KNIA 기준을 찾았다.",
                evidence_refs=[evidence_ref],
                support_level="direct",
            )
        ],
        evidence_refs=[evidence_ref],
        confidence=0.82,
        finality="decision_ready",
    )

    assert plan.execution_order == ["task-evidence-1"]
    assert plan.tasks[0].required_tools == ["search_knia_json_rag_tool"]
    assert result.finality == "decision_ready"


def test_agent_packet_blocks_public_raw_text_or_secret_reference():
    with pytest.raises(ValidationError):
        AgentInputRef(
            ref_type="safe_summary",
            ref_id="case-1",
            field_path="raw_user_text",
            visibility="public",
            summary="raw_user_text should not be exposed",
        )

    with pytest.raises(ValidationError):
        AgentInputRef(
            ref_type="safe_summary",
            ref_id="env",
            field_path="token",
            visibility="public",
            summary="api_key",
        )


def test_specialist_result_requires_structured_claim_or_uncertainty():
    with pytest.raises(ValidationError):
        SpecialistAgentResult(
            role_id="traffic_accident_attorney",
            goal="판례 기반 예상 결과를 설명한다.",
            summary="요약만 있고 구조화된 claim이 없다.",
        )

    evidence_ref = AgentInputRef(ref_type="evidence", ref_id="law-1", visibility="internal")
    result = SpecialistAgentResult(
        role_id="traffic_accident_attorney",
        goal="판례 기반 예상 결과를 설명한다.",
        input_facts_used=[AgentInputRef(ref_type="structured_fact", ref_id="scenario", visibility="internal")],
        evidence_used=[evidence_ref],
        claims=[
            AgentClaim(
                claim_type="legal_guidance",
                text="현재 입력으로는 참고용 예상 안내가 가능하다.",
                evidence_refs=[evidence_ref],
                support_level="direct",
            )
        ],
        recommended_next_action=["CCTV와 신호체계를 확보한다."],
        finality="decision_ready",
    )
    profile = SpecialistRoleProfile(
        role_id="traffic_accident_attorney",
        role_name="AI 교통사고 전문 변호사형 분석관",
        professional_identity="교통사고 민형사/보험 쟁점 검토 역할",
        primary_responsibility="유사 판례, 법령, KNIA 기준 기반 예상 결과와 대응 방향을 제시한다.",
        decision_authority=["법률 쟁점", "민형사 대응 방향", "조건부 예상 결과"],
        must_not_decide=["확정 판결", "근거 없는 과실비율 확정"],
        required_evidence_types=["law", "knia", "precedent"],
    )

    assert validate_specialist_result_against_profile(result, profile) == result


def test_specialist_profile_rejects_out_of_scope_role_or_mismatch():
    with pytest.raises(ValidationError):
        SpecialistRoleProfile(
            role_id="random_advisor",
            role_name="unknown",
            professional_identity="unknown",
            primary_responsibility="unknown",
        )

    profile = SpecialistRoleProfile(
        role_id="knia_standard_agent",
        role_name="KNIA 기준 Agent",
        professional_identity="KNIA/보험 과실비율 기준 검토 역할",
        primary_responsibility="사고축과 맞는 KNIA 기준을 찾는다.",
        decision_authority=["KNIA 기준 적합성"],
        must_not_decide=["형사책임 확정"],
    )
    result = SpecialistAgentResult(
        role_id="fault_ratio_agent",
        goal="과실비율 참고 범위를 제시한다.",
        uncertainties=["KNIA 기준이 아직 확정되지 않았다."],
        finality="needs_review",
    )

    with pytest.raises(ValueError):
        validate_specialist_result_against_profile(result, profile)


def test_mcp_tool_specs_cover_registered_tools_and_error_packet_contract():
    bootstrap_tools()
    registered = set(list_tools())
    spec_names = {spec.name for spec in list_internal_tool_specs()}

    assert registered <= spec_names
    assert {scope for spec in list_internal_tool_specs() for scope in spec.required_scopes}
    packet = build_tool_error_packet("search_knia_json_rag_tool", "timeout", error_code="timeout", retryable=True, trace_id="trace-1")
    assert MCPToolErrorPacket.model_validate(packet).status == "failed"
    assert packet["retryable"] is True
