from __future__ import annotations

from app.services.knia.knia_json_parser import build_rag_chunks_from_document, normalize_document


def test_rag_document_metadata_is_preserved_on_document_and_chunks():
    doc = {
        "doc_id": "knia-2023-06-차43-accident_situation",
        "title": "진로변경 사고",
        "chart_no": "차43",
        "major_party_type": "car_vs_car",
        "scenario_type": "lane_change_collision",
        "scenario_subtype": "vehicle_lane_change",
        "chunk_type": "accident_situation",
        "page_start_pdf": 372,
        "page_end_pdf": 374,
        "review_required": True,
        "body": "진로변경 차량과 후행 직진 차량의 충돌 상황을 설명한다. " * 8,
    }

    normalized = normalize_document(doc)
    chunks = build_rag_chunks_from_document(doc)

    assert normalized["chart_no"] == "차43"
    assert normalized["major_party_type"] == "car_vs_car"
    assert normalized["scenario_type"] == "lane_change_collision"
    assert normalized["chunk_type"] == "accident_situation"
    assert normalized["page_start"] == 372
    assert normalized["page_end"] == 374
    assert normalized["review_required"] is True
    assert chunks
    assert all(chunk["chart_no"] == "차43" for chunk in chunks)
    assert all(chunk["major_party_type"] == "car_vs_car" for chunk in chunks)
    assert all(chunk["scenario_type"] == "lane_change_collision" for chunk in chunks)
    assert all(chunk["chunk_type"] == "accident_situation" for chunk in chunks)
