from app.services.agent_contracts import STANDARD_SPECIALIST_ROLE_IDS
from app.services.llm_client import ANALYST_PROMPT_GUARDRAIL_VERSION, COMMON_ANALYST_SYSTEM_GUARDRAIL
from app.services.specialist_prompt_registry import (
    PROMPT_GUARDRAIL_VERSION,
    PROMPT_GUARDRAILS,
    VERSION,
    attach_specialist_prompt_registry,
    build_specialist_prompt_registry,
)


def test_specialist_prompt_registry_covers_all_standard_roles(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ENABLE_OPENAI_ANALYSTS", "0")

    registry = build_specialist_prompt_registry()
    roles = {item["role_id"]: item for item in registry["roles"]}

    assert registry["version"] == VERSION
    assert registry["guardrail_version"] == PROMPT_GUARDRAIL_VERSION
    assert registry["coverage_complete"] is True
    assert set(roles) == STANDARD_SPECIALIST_ROLE_IDS
    assert roles["video_observation_agent"]["execution_kind"] == "deterministic"
    assert roles["traffic_law_agent"]["execution_kind"] == "llm_guarded"
    assert roles["traffic_law_agent"]["provider_enabled"] is False


def test_prompt_guardrails_block_common_authority_leaks():
    assert "no_final_verdict" in PROMPT_GUARDRAILS
    assert "no_fabricated_law_or_precedent" in PROMPT_GUARDRAILS
    assert "no_video_candidate_promotion" in PROMPT_GUARDRAILS
    assert ANALYST_PROMPT_GUARDRAIL_VERSION == PROMPT_GUARDRAIL_VERSION
    assert "최종 판결" in COMMON_ANALYST_SYSTEM_GUARDRAIL
    assert "영상 후보 관찰값" in COMMON_ANALYST_SYSTEM_GUARDRAIL


def test_specialist_prompt_registry_is_safe_metadata():
    output: dict = {}
    attach_specialist_prompt_registry(output)

    registry = output["specialist_prompt_registry"]
    assert registry["safe_metadata_only"] is True
    assert "OPENAI_API_KEY" not in str(registry)
    assert "api_key" not in str(registry).lower()
