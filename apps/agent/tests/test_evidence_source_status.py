from types import SimpleNamespace

from app.services.evidence_source_status import build_evidence_source_status


def test_evidence_source_status_counts_original_and_static_sources():
    bundle = SimpleNamespace(
        retrieval={"fallback_used": True, "static_support_count": 1},
        legal_evidence=[
            {
                "title": "static legal guide",
                "retrieval_note": "static fallback",
            },
            {
                "title": "linked legal source",
                "source_quality": "collected_original",
                "source_url": "https://www.law.go.kr/법령/도로교통법",
            },
        ],
        knia_result={},
        knia_matches=[
            {"title": "curated KNIA chart"},
        ],
        knia_json_result={"cache": {}},
        knia_json_evidence=[
            {
                "title": "KNIA original detail",
                "source_url": "https://accident.knia.or.kr/example",
            }
        ],
    )

    status = build_evidence_source_status(bundle)

    assert status["version"] == "evidence-source-status-v2"
    assert status["overall_status"] == "degraded"
    assert status["source_quality_totals"]["collected_original"] == 2
    assert status["source_quality_totals"]["static_support"] == 1
    assert status["original_or_collected_count"] == 2
    assert status["static_support_count"] == 1
    assert "expand_original_source_collection" in status["recovery_actions"]
    assert status["sources"]["legal_rag"]["coverage_status"] == "mixed_with_static_support"
    assert status["sources"]["knia_json_detail"]["coverage_status"] == "original_source_ready"


def test_evidence_source_status_marks_reference_only_gap():
    bundle = SimpleNamespace(
        retrieval={},
        legal_evidence=[],
        knia_result={},
        knia_matches=[{"title": "chart without original url"}],
        knia_json_result={"cache": {"disabled_reason": "DATABASE_URL missing"}},
        knia_json_evidence=[],
    )

    status = build_evidence_source_status(bundle)

    assert status["overall_status"] == "partial"
    assert status["sources"]["knia_chart_match"]["coverage_status"] == "reference_only"
    assert "add_original_sources_for_knia_chart_match" in status["recovery_actions"]
    assert "configure_database_url" in status["recovery_actions"]
