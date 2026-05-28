from __future__ import annotations

from app.services.knia.knia_json_loader import validate_knia_json
from app.services.knia.knia_json_parser import build_rag_chunks_from_document, normalize_document


def test_legacy_knia_json_without_charts_still_validates():
    data = {
        "metadata": {"title": "legacy"},
        "pages": [],
        "rag_documents": [
            {
                "doc_id": "legacy-doc",
                "title": "후미추돌 기준",
                "text": "정차 중 뒤차가 추돌한 사고의 안전거리와 전방주시의무 설명입니다. " * 6,
            }
        ],
    }

    assert validate_knia_json(data) == []
    normalized = normalize_document(data["rag_documents"][0])
    chunks = build_rag_chunks_from_document(data["rag_documents"][0])

    assert normalized["id"] == "legacy-doc"
    assert normalized["content"]
    assert chunks
