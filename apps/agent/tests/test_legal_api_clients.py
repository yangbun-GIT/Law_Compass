from app.services import legal_api_clients as clients


def test_law_api_base_accepts_root_or_search_endpoint(monkeypatch):
    monkeypatch.setattr(clients, "LAW_API_BASE", "https://www.law.go.kr/DRF")
    assert clients._law_search_url() == "https://www.law.go.kr/DRF/lawSearch.do"
    assert clients._law_service_url() == "https://www.law.go.kr/DRF/lawService.do"

    monkeypatch.setattr(clients, "LAW_API_BASE", "https://www.law.go.kr/DRF/lawSearch.do")
    assert clients._law_search_url() == "https://www.law.go.kr/DRF/lawSearch.do"
    assert clients._law_service_url() == "https://www.law.go.kr/DRF/lawService.do"


def test_law_api_missing_key_is_safe(monkeypatch):
    monkeypatch.setattr(clients, "LAW_API_OC", "")

    assert clients.fetch_law_search("도로교통법") == []
    assert clients.fetch_law_detail_from_search_row({"title": "도로교통법"})["articles"] == []
    assert clients.get_external_api_status()["law_api"]["reason"] == "missing_api_key"


def test_law_detail_articles_preserve_source_metadata():
    articles = clients._extract_law_articles(
        {
            "법령": {
                "조문": [
                    {
                        "조문번호": "19",
                        "조문제목": "안전거리 확보",
                        "조문내용": "모든 차의 운전자는 같은 방향으로 가는 앞차와의 충돌을 피할 수 있는 거리를 확보해야 한다.",
                    }
                ]
            }
        },
        {
            "title": "도로교통법",
            "law_name": "도로교통법",
            "mst": "12345",
            "source_url": "https://www.law.go.kr/법령/도로교통법?MST=12345",
        },
    )

    assert articles[0]["law_name"] == "도로교통법"
    assert articles[0]["article_no"] == "19"
    assert articles[0]["article_title"] == "안전거리 확보"
    assert articles[0]["source_family"] == "legal_db_article"
    assert articles[0]["retrieval_note"] == "law_api_detail"
