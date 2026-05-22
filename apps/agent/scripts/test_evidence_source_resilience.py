from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.services.rag_client as rag_client
from app.services.evidence_source_status import build_evidence_source_status
from app.services.orchestration_evidence import EvidenceBundle


def main() -> None:
    original = rag_client.retrieve_legal_evidence
    try:
        rag_client.retrieve_legal_evidence = _raise_retrieval_error
        retrieval = rag_client.retrieve_for_scenario(
            scenario_type="rear_end_collision",
            scenario_tags=["rear_end", "safe_distance"],
            description_text="정차 중 뒤에서 추돌당한 사고입니다.",
            facts={"stopped": True, "opponent_behavior": "rear_collision"},
            selected_keywords=[],
            limit=4,
        )
    finally:
        rag_client.retrieve_legal_evidence = original

    assert retrieval["fallback_used"] is True
    assert retrieval["static_support_count"] > 0
    assert retrieval["retrieval_error"]["type"] == "RuntimeError"
    assert all(item.get("retrieval_note") == "static_fallback" for item in retrieval["items"])

    bundle = EvidenceBundle(
        knia_result={"items": [], "lookup_error": {"type": "OperationalError", "message": "KNIA chart lookup failed"}},
        knia_matches=[],
        evidence_query={"query_text": "정차 후방 추돌"},
        knia_json_result={"items": [], "cache": {"disabled_reason": "DATABASE_URL missing"}},
        knia_json_evidence=[],
        knia_fault_estimate=None,
        knia_reference_evidence=[],
        knia_evidence=[],
        retrieval=retrieval,
        legal_evidence=retrieval["items"],
        evidence=retrieval["items"],
    )
    status = build_evidence_source_status(bundle)
    assert status["version"] == "evidence-source-status-v1"
    assert status["overall_status"] in {"partial", "degraded"}
    assert status["sources"]["legal_rag"]["status"] == "degraded_with_fallback"
    assert status["sources"]["knia_chart_match"]["status"] == "unavailable"
    assert status["sources"]["knia_json_detail"]["disabled_reason"] == "DATABASE_URL missing"
    assert "refresh_or_rebuild_legal_kb" in status["recovery_actions"]
    assert "configure_database_url" in status["recovery_actions"]
    print("evidence_source_resilience=passed")


def _raise_retrieval_error(**_: object) -> dict[str, object]:
    raise RuntimeError("simulated retrieval failure")


if __name__ == "__main__":
    main()
