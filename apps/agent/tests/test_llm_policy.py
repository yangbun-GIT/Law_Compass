from app.services.analysts.fault_ratio_analyst import analyze_fault_ratio
from app.services.analysts.traffic_law_analyst import analyze_traffic_law
from app.services.llm_policy import evaluate_llm_usage, summarize_case_llm_policy


def test_llm_policy_blocks_fault_ratio_without_knia_evidence(monkeypatch):
    monkeypatch.setenv("ENABLE_OPENAI_ANALYSTS", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    usage = evaluate_llm_usage(
        section="fault_ratio_analysis",
        evidence=[{"chunk_id": "law-1", "law_name": "도로교통법"}],
        facts={},
    )

    assert usage["provider_enabled"] is True
    assert usage["allowed"] is False
    assert usage["reason"] == "required_knia_evidence_missing"


def test_llm_policy_allows_traffic_law_with_legal_evidence(monkeypatch):
    monkeypatch.setenv("ENABLE_OPENAI_ANALYSTS", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    usage = evaluate_llm_usage(
        section="traffic_law_analysis",
        evidence=[{"chunk_id": "law-1", "law_name": "도로교통법"}],
        facts={},
    )

    assert usage["allowed"] is True
    assert usage["mode"] == "evidence_bound_interpretation"
    assert "applicable_rules" in usage["deterministic_authority"]


def test_analyst_result_records_deterministic_fallback_when_llm_blocked(monkeypatch):
    monkeypatch.setenv("ENABLE_OPENAI_ANALYSTS", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    result = analyze_fault_ratio(
        scenario_type="rear_end_collision",
        facts={},
        evidence=[{"chunk_id": "law-1", "law_name": "도로교통법"}],
        text="정차 중 뒤에서 추돌당했습니다.",
    )

    assert result["analysis_source"] == "deterministic_fallback"
    assert result["llm_usage"]["used"] is False
    assert result["llm_usage"]["reason"] == "required_knia_evidence_missing"


def test_case_llm_policy_summary_counts_used_and_blocked_sections(monkeypatch):
    monkeypatch.setenv("ENABLE_OPENAI_ANALYSTS", "0")

    legal = analyze_traffic_law(
        scenario_type="rear_end_collision",
        facts={},
        evidence=[{"chunk_id": "law-1", "law_name": "도로교통법"}],
        text="정차 중 뒤에서 추돌당했습니다.",
    )
    fault = analyze_fault_ratio(
        scenario_type="rear_end_collision",
        facts={},
        evidence=[],
        text="정차 중 뒤에서 추돌당했습니다.",
    )
    summary = summarize_case_llm_policy({
        "traffic_law_analysis": legal,
        "fault_ratio_analysis": fault,
    })

    assert summary["version"] == "llm-policy-v1"
    assert summary["provider_enabled"] is False
    assert "traffic_law_analysis" in summary["blocked_sections"]
    assert "fault_ratio_analysis" in summary["blocked_sections"]
