from app.services.legal import legal_evidence_retriever as retriever


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    def get(self, key: str):
        return self.store.get(key)

    def setex(self, key: str, _ttl: int, value: str):
        self.store[key] = value


def test_legal_rag_uses_law_api_fallback_and_redis_cache(monkeypatch):
    fake_redis = FakeRedis()

    monkeypatch.setattr(retriever, "DB_URL", "")
    monkeypatch.setattr(retriever, "_redis_client", lambda: fake_redis)
    monkeypatch.setattr(
        retriever,
        "fetch_law_search",
        lambda query, limit=5: [
            {
                "chunk_id": "law:law:road-traffic",
                "title": "도로교통법",
                "source": "국가법령정보센터 OPEN API(법령)",
                "source_uri": "https://www.law.go.kr/법령/도로교통법",
                "snippet": "운전자는 안전거리를 확보해야 합니다.",
                "score": 0.46,
            }
        ],
    )

    first = retriever.retrieve_legal_evidence(
        scenario_type="rear_end_collision",
        scenario_tags=["rear_end", "safe_distance"],
        query="후미추돌 안전거리",
        limit=3,
    )
    second = retriever.retrieve_legal_evidence(
        scenario_type="rear_end_collision",
        scenario_tags=["rear_end", "safe_distance"],
        query="후미추돌 안전거리",
        limit=3,
    )

    assert first["fallback_source"] == "law_api"
    assert first["items"][0]["retrieval_note"] == "law_api_search_fallback"
    assert first["items"][0]["source_family"] == "law_api_search"
    assert first["items"][0]["source"] == "국가법령정보센터 OPEN API(법령)"
    assert second["cache_hit"] is True
    assert second["items"][0]["title"] == "도로교통법"
