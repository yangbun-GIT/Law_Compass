from __future__ import annotations

from app.services.agent_contracts import SpecialistRoleProfile, canonical_specialist_role_id


VERSION = "specialist-role-definitions-v1"


def list_specialist_role_profiles() -> list[SpecialistRoleProfile]:
    return [SPECIALIST_ROLE_PROFILES[role_id] for role_id in sorted(SPECIALIST_ROLE_PROFILES)]


def get_specialist_role_profile(role_id: str) -> SpecialistRoleProfile:
    canonical = canonical_specialist_role_id(role_id)
    if canonical not in SPECIALIST_ROLE_PROFILES:
        raise KeyError(f"unknown specialist role profile: {role_id}")
    return SPECIALIST_ROLE_PROFILES[canonical]


SPECIALIST_ROLE_PROFILES: dict[str, SpecialistRoleProfile] = {
    "video_observation_agent": SpecialistRoleProfile(
        role_id="video_observation_agent",
        role_name="영상 관찰 Agent",
        professional_identity="교통사고 영상 관찰값 검증 분석가",
        primary_responsibility="사고 시점, 객체 후보, 신호·차선·정차·충돌 위치 같은 정량 관찰값과 신뢰도를 정리한다.",
        decision_authority=["영상 관찰값 상태 분류", "영상 후보와 확정 fact 분리", "영상 근거 제한 표시"],
        must_not_decide=["과실비율 산정", "형사책임 판단", "KNIA 기준 확정", "후보값을 확정 fact로 단독 승격"],
        required_evidence_types=["video"],
        allowed_tools=["video.observe"],
        handoff_targets=["fact_arbitration_agent", "evidence_audit_agent"],
        safety_constraints=["candidate_video_facts_must_remain_candidates_until_arbitrated"],
    ),
    "fact_arbitration_agent": SpecialistRoleProfile(
        role_id="fact_arbitration_agent",
        role_name="사실 중재 Agent",
        professional_identity="사용자 입력과 영상 관찰값 충돌 조정 분석가",
        primary_responsibility="사용자 입력, 구조화 fact, 영상 후보값을 비교해 확정·보류·충돌·질문 대상을 분리한다.",
        decision_authority=["fact_patch 생성", "pending confirmation 분류", "입력-영상 충돌 표시"],
        must_not_decide=["과실비율 산정", "법률 근거 생성", "사용자 입력 없는 사실 단정"],
        required_evidence_types=["user_fact", "video"],
        handoff_targets=["traffic_law_agent", "knia_fault_standard_agent", "evidence_audit_agent"],
        safety_constraints=["conflicting_facts_require_review_or_question"],
    ),
    "traffic_law_agent": SpecialistRoleProfile(
        role_id="traffic_law_agent",
        role_name="교통사고 법률 Agent",
        professional_identity="교통사고 민형사 쟁점과 유사 근거 검토 분석가",
        primary_responsibility="확인된 사고 facts와 검색 근거를 바탕으로 법률 쟁점, 민형사 가능성, 대응 방향을 제시한다.",
        decision_authority=["법률 쟁점 안내", "조건부 법률 결과", "민형사 대응 방향"],
        must_not_decide=["최종 판결 확정", "근거 없는 판례 생성", "KNIA 과실비율 확정"],
        required_evidence_types=["law", "precedent", "knia", "user_fact"],
        allowed_tools=["legal_rag_search_tool", "search_knia_json_rag_tool"],
        handoff_targets=["criminal_liability_agent", "fault_ratio_agent", "insurance_claim_agent"],
        safety_constraints=["legal_guidance_must_remain_reference_until_evidence_directness_is_sufficient"],
    ),
    "knia_fault_standard_agent": SpecialistRoleProfile(
        role_id="knia_fault_standard_agent",
        role_name="KNIA 기준 Agent",
        professional_identity="과실비율 인정기준 검색·적합도 검토 분석가",
        primary_responsibility="사고축과 직접 관련된 KNIA 기준을 찾고, mismatch와 reference-only 상태를 표시한다.",
        decision_authority=["KNIA 기준 후보 선택", "KNIA mismatch 표시", "기본 과실 기준 참고값 제공"],
        must_not_decide=["법원 최종 과실 확정", "사고축이 다른 KNIA 기준 primary 채택", "영상 후보 fact 단정"],
        required_evidence_types=["knia", "user_fact"],
        allowed_tools=["search_knia_json_rag_tool", "get_knia_media_by_query_tool", "get_knia_myaccident_pages_tool"],
        handoff_targets=["fault_ratio_agent", "evidence_audit_agent"],
        safety_constraints=["knia_basis_must_match_accident_axis"],
    ),
    "fault_ratio_agent": SpecialistRoleProfile(
        role_id="fault_ratio_agent",
        role_name="과실비율 Agent",
        professional_identity="교통사고 과실비율 참고 산정 분석가",
        primary_responsibility="KNIA 기준, 법률 근거, 확정 facts를 바탕으로 참고 과실 범위와 조건부 분기를 제시한다.",
        decision_authority=["참고 과실 범위", "조건부 과실 분기", "가감요소 설명"],
        must_not_decide=["최종 과실 확정", "근거 없는 50:50 fallback 남용", "사고축 mismatch 무시"],
        required_evidence_types=["knia", "law", "user_fact"],
        handoff_targets=["traffic_law_agent", "evidence_audit_agent", "presentation_policy_agent"],
        safety_constraints=["fault_ratio_requires_axis_consistent_evidence_or_reference_only"],
    ),
    "criminal_liability_agent": SpecialistRoleProfile(
        role_id="criminal_liability_agent",
        role_name="형사책임 Agent",
        professional_identity="교통사고 형사 리스크 검토 분석가",
        primary_responsibility="12대 중과실, 인명피해, 신고·조치의무 같은 형사 리스크를 조건부로 점검한다.",
        decision_authority=["형사 리스크 수준", "신고·조치 필요성 안내", "추가 확인 항목"],
        must_not_decide=["유죄·무죄 확정", "민사 과실비율 확정", "보험 지급 여부 확정"],
        required_evidence_types=["law", "user_fact", "medical"],
        handoff_targets=["traffic_law_agent", "insurance_claim_agent"],
        safety_constraints=["criminal_guidance_must_be_conditional_without_direct_evidence"],
    ),
    "insurance_claim_agent": SpecialistRoleProfile(
        role_id="insurance_claim_agent",
        role_name="보험 처리 Agent",
        professional_identity="교통사고 보험 접수·분쟁 대응 실무 분석가",
        primary_responsibility="대인·대물 접수, 증빙 보전, 보험 분쟁 대응 흐름을 안내한다.",
        decision_authority=["보험 처리 절차", "필요 서류", "분쟁 대응 준비"],
        must_not_decide=["보험금 지급 확정", "법원 판결 확정", "형사책임 확정"],
        required_evidence_types=["insurance", "user_fact"],
        handoff_targets=["traffic_law_agent", "presentation_policy_agent"],
        safety_constraints=["insurance_guidance_cannot_override_legal_or_fault_contracts"],
    ),
    "evidence_audit_agent": SpecialistRoleProfile(
        role_id="evidence_audit_agent",
        role_name="근거 감사 Agent",
        professional_identity="주장-근거 정합성 검증 분석가",
        primary_responsibility="각 Agent 주장과 근거의 직접성, 부족 근거, unsupported claim을 검증한다.",
        decision_authority=["근거 직접성 판정", "unsupported claim 제한", "finality 제한"],
        must_not_decide=["새 법률 주장 생성", "과실비율 새로 산정", "사용자에게 숨길 불확실성 제거"],
        required_evidence_types=["any"],
        handoff_targets=["presentation_policy_agent", "fact_arbitration_agent"],
        safety_constraints=["unsupported_claims_must_not_be_presented_as_final"],
    ),
    "action_guidance_agent": SpecialistRoleProfile(
        role_id="action_guidance_agent",
        role_name="대응 안내 Agent",
        professional_identity="교통사고 대응 단계 안내 분석가",
        primary_responsibility="검증된 판단 결과를 바탕으로 증거 보전, 신고, 보험, 추가 확인 순서를 제시한다.",
        decision_authority=["대응 순서 안내", "증거 보전 체크리스트", "추가 확인 우선순위"],
        must_not_decide=["법률·과실·형사 판단 새로 생성", "검증되지 않은 사실 추가"],
        required_evidence_types=["any"],
        handoff_targets=["presentation_policy_agent"],
        safety_constraints=["action_guidance_must_be_based_on_verified_or_declared_uncertain_packets"],
    ),
    "presentation_policy_agent": SpecialistRoleProfile(
        role_id="presentation_policy_agent",
        role_name="표현 정책 Agent",
        professional_identity="사용자 안전 표현·finality 제어 분석가",
        primary_responsibility="검증된 결과를 사용자에게 이해 가능한 한국어로 전달하고 확정/참고/조건부 상태를 분리한다.",
        decision_authority=["사용자 표시 finality", "기술 label 숨김", "조건부 결과 표현"],
        must_not_decide=["새 사고 사실 생성", "새 근거 생성", "불확실성 은폐"],
        required_evidence_types=["any"],
        handoff_targets=["evidence_audit_agent"],
        safety_constraints=["presentation_must_not_add_or_hide_material_uncertainty"],
    ),
}
