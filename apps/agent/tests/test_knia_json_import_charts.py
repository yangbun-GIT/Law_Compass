from __future__ import annotations

from pathlib import Path

from app.services.knia.knia_json_loader import load_knia_json_file, validate_knia_json


ROOT = Path(__file__).resolve().parents[3]
REVIEW_JSON = ROOT / "scripts" / "knia_fault_ratio" / "knia_fault_ratio_2023_06.codex_review.json"


def test_codex_review_json_loads_charts():
    data = load_knia_json_file(str(REVIEW_JSON))

    assert data["charts"]
    assert data["rag_documents"]
    assert data["_validation_warnings"] is not None


def test_car_vs_car_core_charts_exist():
    data = load_knia_json_file(str(REVIEW_JSON))
    charts = {item["chart_no"]: item for item in data["charts"]}

    for chart_no in ("차41", "차42", "차43"):
        assert chart_no in charts
        assert charts[chart_no]["major_party_type"] == "car_vs_car"


def test_validation_warnings_do_not_abort_import_shape_checks():
    data = {
        "metadata": {},
        "pages": [],
        "rag_documents": [{"doc_id": "bad-doc", "title": "누락 문서", "body": "본문"}],
        "charts": [{"chart_no": "차99"}],
    }

    warnings = validate_knia_json(data)

    assert warnings
    assert any(item["section"] == "charts" for item in warnings)
    assert any(item["section"] == "rag_documents" for item in warnings)
