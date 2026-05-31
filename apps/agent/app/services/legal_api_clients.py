from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

import httpx

LAW_API_OC = os.getenv("LAW_API_OC", "")
LAW_API_BASE = os.getenv("LAW_API_BASE", "https://www.law.go.kr/DRF")
LAW_API_TARGETS = [x.strip() for x in os.getenv("LAW_API_TARGETS", "law,prec").split(",") if x.strip()]
DATA_GO_SERVICE_KEY = os.getenv("DATA_GO_SERVICE_KEY", "")
DATA_GO_TRAFFIC_URL = os.getenv("DATA_GO_TRAFFIC_URL", "https://apis.data.go.kr/B552061/AccidentDeath/getRestTrafficAccidentDeath")
DATA_GO_SEARCH_YEAR = os.getenv("DATA_GO_SEARCH_YEAR", "2024")
DATA_GO_SIDO = os.getenv("DATA_GO_SIDO", "11")
DATA_GO_GUGUN = os.getenv("DATA_GO_GUGUN", "680")

_LAST_STATUS: dict[str, dict[str, Any]] = {
    "law_api": {"ok": None, "message": "not_called"},
    "data_go": {"ok": None, "message": "not_called"},
}


def _law_search_url(base: str | None = None) -> str:
    root = (base or LAW_API_BASE or "https://www.law.go.kr/DRF").strip()
    if root.endswith("/lawSearch.do"):
        return root
    return f"{root.rstrip('/')}/lawSearch.do"


def _law_service_url(base: str | None = None) -> str:
    root = (base or LAW_API_BASE or "https://www.law.go.kr/DRF").strip()
    if root.endswith("/lawSearch.do"):
        root = root[: -len("/lawSearch.do")]
    if root.endswith("/lawService.do"):
        return root
    return f"{root.rstrip('/')}/lawService.do"


def _first_value(node: dict[str, Any], keys: list[str]) -> Any:
    lowered = {str(k).lower(): v for k, v in node.items()}
    for key in keys:
        if key in node and node[key] not in (None, ""):
            return node[key]
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return value
    return None


def _law_source_url(title: str, *, mst: str = "", law_id: str = "") -> str:
    if mst:
        return f"https://www.law.go.kr/법령/{quote(title)}?MST={quote(str(mst))}"
    if law_id:
        return f"https://www.law.go.kr/법령/{quote(title)}?ID={quote(str(law_id))}"
    return f"https://www.law.go.kr/법령/{quote(title)}"


def get_external_api_status() -> dict[str, dict[str, Any]]:
    return {
        "law_api": dict(_LAST_STATUS["law_api"]),
        "data_go": dict(_LAST_STATUS["data_go"]),
    }


def fetch_law_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    if not LAW_API_OC:
        _LAST_STATUS["law_api"] = {"ok": False, "message": "LAW_API_OC missing", "reason": "missing_api_key"}
        return []

    rows: list[dict[str, Any]] = []
    last_error = "호출 시도 전"

    def walk(node: Any, target: str):
        nonlocal rows
        if isinstance(node, dict):
            keys = {str(k).lower() for k in node.keys()}
            if any(k in keys for k in {"법령명한글", "법령명", "lawname", "판례명", "사건명", "precname"}):
                title = str(
                    node.get("법령명한글")
                    or node.get("법령명")
                    or node.get("lawName")
                    or node.get("판례명")
                    or node.get("사건명")
                    or node.get("precName")
                    or "법령/판례"
                )
                mst = str(_first_value(node, ["법령일련번호", "MST", "mst"]) or "")
                law_id = str(_first_value(node, ["법령ID", "법령id", "lawId", "ID", "id"]) or "")
                prec_id = str(_first_value(node, ["판례일련번호", "판례ID", "precId"]) or "")
                item_id = mst or law_id or prec_id or title
                snippet = str(
                    node.get("제개정구분명")
                    or node.get("법령구분명")
                    or node.get("lawType")
                    or node.get("판시사항")
                    or node.get("사건종류명")
                    or title
                )
                source_name = "국가법령정보센터 OPEN API(법령)" if target == "law" else "국가법령정보센터 OPEN API(판례)"
                source_uri = node.get("source_uri") or node.get("source_url")
                if not source_uri:
                    source_uri = _law_source_url(title, mst=mst, law_id=law_id) if target == "law" else f"https://www.law.go.kr/판례/{quote(title)}"
                rows.append(
                    {
                        "chunk_id": f"law:{target}:{item_id}",
                        "title": title,
                        "source": source_name,
                        "source_uri": source_uri,
                        "source_url": source_uri,
                        "snippet": snippet,
                        "score": 0.46 if target == "law" else 0.44,
                        "target": target,
                        "law_name": title if target == "law" else "",
                        "law_id": law_id,
                        "mst": mst,
                        "prec_id": prec_id,
                        "source_family": "law_api_search",
                        "retrieval_note": "law_api_search",
                        "raw": node,
                    }
                )
            for v in node.values():
                walk(v, target)
        elif isinstance(node, list):
            for x in node:
                walk(x, target)

    for target in LAW_API_TARGETS or ["law"]:
        params = {
            "OC": LAW_API_OC,
            "target": target,
            "type": "JSON",
            "query": query,
            "display": min(max(limit, 1), 20),
        }
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(_law_search_url(), params=params)
                if resp.status_code >= 400:
                    last_error = f"HTTP {resp.status_code}"
                    continue
                data = resp.json()
        except Exception as exc:
            last_error = f"network_error:{exc}"
            continue

        if isinstance(data, dict) and data.get("result") and str(data.get("result")).strip().lower() != "success":
            last_error = str(data.get("msg") or data.get("result"))
            continue
        last_error = "정상 응답이나 검색 결과 0건"
        walk(data, target)

    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        dedup[row["chunk_id"]] = row
    out = list(dedup.values())[:limit]
    if out:
        _LAST_STATUS["law_api"] = {"ok": True, "message": f"ok:{len(out)}", "targets": LAW_API_TARGETS}
    else:
        _LAST_STATUS["law_api"] = {"ok": False, "message": last_error, "targets": LAW_API_TARGETS}
    return out


def fetch_law_detail_from_search_row(row: dict[str, Any]) -> dict[str, Any]:
    if not LAW_API_OC:
        _LAST_STATUS["law_api"] = {"ok": False, "message": "LAW_API_OC missing", "reason": "missing_api_key"}
        return {"ok": False, "reason": "LAW_API_OC_MISSING", "detail_fetch_failed": True, "articles": []}

    raw = row.get("raw") if isinstance(row.get("raw"), dict) else row
    title = str(row.get("law_name") or row.get("title") or _first_value(raw, ["법령명한글", "법령명", "lawName"]) or "")
    mst = str(row.get("mst") or _first_value(raw, ["법령일련번호", "MST", "mst"]) or "")
    law_id = str(row.get("law_id") or _first_value(raw, ["법령ID", "법령id", "lawId", "ID", "id"]) or "")
    params: dict[str, Any] = {"OC": LAW_API_OC, "target": "law", "type": "JSON"}
    if mst:
        params["MST"] = mst
    elif law_id:
        params["ID"] = law_id
    elif title:
        params["query"] = title
    else:
        return {"ok": False, "reason": "LAW_DETAIL_ID_MISSING", "detail_fetch_failed": True, "articles": []}

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(_law_service_url(), params=params)
            if resp.status_code >= 400:
                return {"ok": False, "reason": f"HTTP_{resp.status_code}", "detail_fetch_failed": True, "articles": []}
            data = resp.json()
    except Exception as exc:
        return {"ok": False, "reason": f"network_error:{exc.__class__.__name__}", "detail_fetch_failed": True, "articles": []}

    articles = _extract_law_articles(data, row)
    if not articles:
        return {"ok": False, "reason": "ARTICLE_NOT_FOUND", "detail_fetch_failed": True, "articles": []}
    _LAST_STATUS["law_api"] = {"ok": True, "message": f"detail_ok:{len(articles)}", "targets": ["law"]}
    return {"ok": True, "articles": articles, "law_name": title, "source_url": _law_source_url(title or "법령", mst=mst, law_id=law_id)}


def fetch_road_traffic_law_articles(limit: int = 80) -> list[dict[str, Any]]:
    search_rows = fetch_law_search("도로교통법", limit=5)
    law_rows = [
        row for row in search_rows
        if str(row.get("target") or "law") == "law" and "도로교통법" in str(row.get("title") or row.get("law_name") or "")
    ] or [row for row in search_rows if str(row.get("target") or "law") == "law"]

    for row in law_rows[:2]:
        detail = fetch_law_detail_from_search_row(row)
        if detail.get("ok") and detail.get("articles"):
            return list(detail["articles"])[:limit]

    fallback: list[dict[str, Any]] = []
    for row in law_rows:
        fallback.append({
            **row,
            "article_text": str(row.get("snippet") or row.get("title") or ""),
            "article_no": "",
            "article_title": str(row.get("title") or "도로교통법"),
            "law_name": str(row.get("law_name") or row.get("title") or "도로교통법"),
            "detail_fetch_failed": True,
            "retrieval_note": "law_search_snippet_fallback",
            "source_family": "law_api_search",
        })
    return fallback[:limit]


def _extract_law_articles(data: Any, search_row: dict[str, Any]) -> list[dict[str, Any]]:
    articles: list[dict[str, Any]] = []
    law_name = str(search_row.get("law_name") or search_row.get("title") or "도로교통법")
    source_url = str(search_row.get("source_url") or search_row.get("source_uri") or _law_source_url(law_name))
    mst = str(search_row.get("mst") or "")
    law_id = str(search_row.get("law_id") or "")

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            text = _first_value(node, ["조문내용", "조문내용한글", "articleText", "content", "항내용"])
            article_no = _first_value(node, ["조문번호", "조문가지번호", "articleNo", "article_no"])
            article_title = _first_value(node, ["조문제목", "articleTitle", "article_title"])
            if text:
                article_text = _article_text(node, str(text))
                articles.append({
                    "law_name": law_name,
                    "law_id": law_id,
                    "mst": mst,
                    "effective_date": _first_value(node, ["시행일자", "시행일", "effectiveDate"]) or _first_value(search_row.get("raw", {}) if isinstance(search_row.get("raw"), dict) else search_row, ["시행일자", "시행일", "effectiveDate"]),
                    "promulgation_date": _first_value(node, ["공포일자", "promulgationDate"]),
                    "article_no": str(article_no or ""),
                    "article_title": str(article_title or ""),
                    "article_text": article_text,
                    "source_url": source_url,
                    "provider": "law_api",
                    "source_family": "legal_db_article",
                    "retrieval_note": "law_api_detail",
                })
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(data)
    dedup: dict[str, dict[str, Any]] = {}
    for item in articles:
        key = f"{item.get('article_no')}|{item.get('article_title')}|{item.get('article_text')[:80]}"
        dedup[key] = item
    return list(dedup.values())


def _article_text(node: dict[str, Any], text: str) -> str:
    parts = [text]
    for key in ("항내용", "호내용", "목내용"):
        value = node.get(key)
        if isinstance(value, str) and value.strip() and value.strip() not in parts:
            parts.append(value.strip())
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    parts.append(item.strip())
                elif isinstance(item, dict):
                    nested = _first_value(item, ["항내용", "호내용", "목내용", "내용", "content"])
                    if nested:
                        parts.append(str(nested).strip())
    return " ".join(part for part in parts if part).strip()


def fetch_data_go_traffic(query: str, limit: int = 3) -> list[dict[str, Any]]:
    if not DATA_GO_SERVICE_KEY:
        _LAST_STATUS["data_go"] = {"ok": False, "message": "DATA_GO_SERVICE_KEY 미설정"}
        return []
    try:
        params = {
            "serviceKey": DATA_GO_SERVICE_KEY,
            "type": "json",
            "returnType": "json",
            "numOfRows": min(max(limit, 1), 20),
            "pageNo": 1,
            "searchYear": DATA_GO_SEARCH_YEAR,
            "searchYearCd": DATA_GO_SEARCH_YEAR,
            "siDo": DATA_GO_SIDO,
            "guGun": DATA_GO_GUGUN,
        }
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                DATA_GO_TRAFFIC_URL,
                params=params,
            )
            if resp.status_code >= 400:
                _LAST_STATUS["data_go"] = {"ok": False, "message": f"HTTP {resp.status_code}"}
                return []
            data = resp.json()
    except Exception as exc:
        _LAST_STATUS["data_go"] = {"ok": False, "message": f"network_error:{exc}"}
        return []

    rows: list[dict[str, Any]] = []
    q = (query or "").lower()

    def walk(node: Any):
        if isinstance(node, dict):
            keys = {str(k).lower() for k in node.keys()}
            if any(k in keys for k in {"title", "사고유형", "accidenttype", "spot_nm", "occrrnc_cnt", "afos_fid"}):
                title = str(node.get("title") or node.get("spot_nm") or node.get("사고유형") or "교통사고 데이터")
                snippet = str(node)[:220]
                if q and q not in snippet.lower() and q not in title.lower():
                    return
                rows.append(
                    {
                        "chunk_id": f"traffic:{title[:20]}",
                        "title": title,
                        "source": "공공데이터포털 교통 API",
                        "snippet": snippet,
                        "score": 0.34,
                    }
                )
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for x in node:
                walk(x)

    walk(data)
    out = rows[:limit]
    if out:
        _LAST_STATUS["data_go"] = {"ok": True, "message": f"ok:{len(out)}", "url": DATA_GO_TRAFFIC_URL}
    else:
        _LAST_STATUS["data_go"] = {"ok": False, "message": "정상 응답이나 추출 항목 0건", "url": DATA_GO_TRAFFIC_URL}
    return out
