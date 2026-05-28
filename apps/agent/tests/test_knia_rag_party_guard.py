from __future__ import annotations

from app.services.knia.knia_json_repository import get_rag_documents_by_chart_no
from app.services.knia.party_guard import reject_mismatched_knia_items


def test_chart_no_rag_documents_are_limited_to_selected_chart():
    docs = get_rag_documents_by_chart_no("차43")

    assert docs
    assert all(doc.get("chart_no") == "차43" for doc in docs)
    assert all(doc.get("major_party_type") == "car_vs_car" for doc in docs)


def test_party_guard_rejects_other_major_party_rag_items():
    kept, rejected = reject_mismatched_knia_items(
        [
            {"chart_no": "차43", "major_party_type": "car_vs_car", "title": "진로변경"},
            {"chart_no": "보1", "major_party_type": "car_vs_person", "title": "보행자"},
            {"chart_no": "거41", "major_party_type": "car_vs_bicycle", "title": "자전거"},
        ],
        "car_vs_car",
    )

    assert [item["chart_no"] for item in kept] == ["차43"]
    assert {item["chart_no"] for item in rejected} == {"보1", "거41"}
