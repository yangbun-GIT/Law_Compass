from app.services.legal import legal_ingestion_service as ingestion
from app.services.legal.legal_chunker import chunk_legal_document


def test_collect_traffic_law_documents_prefers_law_detail_articles(monkeypatch):
    monkeypatch.setenv("LAW_API_OC", "dummy")
    monkeypatch.setattr(
        ingestion,
        "fetch_road_traffic_law_articles",
        lambda limit=80: [
            {
                "law_name": "도로교통법",
                "article_no": "19",
                "article_title": "안전거리 확보",
                "article_text": "제19조(안전거리 확보) 운전자는 앞차와 충돌을 피할 수 있는 거리를 확보해야 한다.",
                "source_url": "https://www.law.go.kr/법령/도로교통법",
                "source_family": "legal_db_article",
                "retrieval_note": "law_api_detail",
            }
        ],
    )

    docs, provider = ingestion.collect_traffic_law_documents()
    chunks = chunk_legal_document(docs[0])

    assert provider == "law_api_detail"
    assert docs[0].metadata["law_name"] == "도로교통법"
    assert chunks[0]["article_no"] == "19"
    assert chunks[0]["law_name"] == "도로교통법"
    assert chunks[0]["source_url"] == "https://www.law.go.kr/법령/도로교통법"
    assert chunks[0]["metadata"]["source_family"] == "legal_db_article"


def test_collect_traffic_law_documents_falls_back_to_search_snippets(monkeypatch):
    monkeypatch.setenv("LAW_API_OC", "dummy")
    monkeypatch.setattr(ingestion, "fetch_road_traffic_law_articles", lambda limit=80: [])
    monkeypatch.setattr(
        ingestion,
        "fetch_law_search",
        lambda query, limit=5: [
            {
                "title": "도로교통법",
                "snippet": "운전자는 앞차와 충돌을 피할 수 있는 거리를 확보해야 한다.",
                "source_url": "https://www.law.go.kr/법령/도로교통법",
                "source_family": "law_api_search",
            }
        ],
    )

    docs, provider = ingestion.collect_traffic_law_documents()

    assert provider == "law_api"
    assert docs
    assert docs[0].metadata["source_family"] == "law_api_search"
