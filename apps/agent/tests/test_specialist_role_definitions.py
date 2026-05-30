import pytest

from app.services.agent_contracts import (
    AgentClaim,
    AgentInputRef,
    SpecialistAgentResult,
    STANDARD_SPECIALIST_ROLE_IDS,
    canonical_specialist_role_id,
    validate_specialist_result_against_profile,
)
from app.services.specialist_role_definitions import (
    VERSION,
    get_specialist_role_profile,
    list_specialist_role_profiles,
)


def test_specialist_role_profiles_cover_standard_roles():
    profiles = list_specialist_role_profiles()
    profile_ids = {profile.role_id for profile in profiles}

    assert VERSION == "specialist-role-definitions-v1"
    assert profile_ids == STANDARD_SPECIALIST_ROLE_IDS
    assert all(profile.primary_responsibility for profile in profiles)
    assert all(profile.safety_constraints for profile in profiles)


def test_legacy_role_aliases_resolve_to_canonical_profiles():
    assert canonical_specialist_role_id("traffic_accident_attorney") == "traffic_law_agent"
    assert canonical_specialist_role_id("knia_standard_agent") == "knia_fault_standard_agent"
    assert canonical_specialist_role_id("insurance_handling_agent") == "insurance_claim_agent"

    assert get_specialist_role_profile("traffic_accident_attorney").role_id == "traffic_law_agent"
    assert get_specialist_role_profile("knia_standard_agent").role_id == "knia_fault_standard_agent"
    assert get_specialist_role_profile("insurance_handling_agent").role_id == "insurance_claim_agent"


def test_observation_and_presentation_roles_do_not_expand_judgment_authority():
    video_profile = get_specialist_role_profile("video_observation_agent")
    fact_profile = get_specialist_role_profile("fact_arbitration_agent")
    presentation_profile = get_specialist_role_profile("presentation_policy_agent")

    assert any("과실비율" in item for item in video_profile.must_not_decide)
    assert any("과실비율" in item for item in fact_profile.must_not_decide)
    assert "새 사고 사실 생성" in presentation_profile.must_not_decide
    assert "불확실성 은폐" in presentation_profile.must_not_decide


def test_specialist_result_validation_accepts_legacy_alias_against_canonical_profile():
    evidence_ref = AgentInputRef(ref_type="evidence", ref_id="law-1", visibility="internal")
    result = SpecialistAgentResult(
        role_id="traffic_accident_attorney",
        goal="근거 기반 법률 쟁점을 안내한다.",
        evidence_used=[evidence_ref],
        claims=[
            AgentClaim(
                claim_type="legal_guidance",
                text="확인된 근거 범위에서 법률 쟁점을 안내한다.",
                evidence_refs=[evidence_ref],
                support_level="direct",
            )
        ],
        finality="decision_ready",
    )
    profile = get_specialist_role_profile("traffic_law_agent")

    assert validate_specialist_result_against_profile(result, profile) == result


def test_unknown_role_profile_is_rejected():
    with pytest.raises(KeyError):
        get_specialist_role_profile("unknown_role")
