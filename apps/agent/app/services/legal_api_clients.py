from __future__ import annotations

import os
from typing import Any

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


def get_external_api_status() -> dict[str, dict[str, Any]]:
    return {
        "law_api": dict(_LAST_STATUS["law_api"]),
        "data_go": dict(_LAST_STATUS["data_go"]),
    }


def fetch_law_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    if not LAW_API_OC:
        _LAST_STATUS["law_api"] = {"ok": False, "message": "LAW_API_OC 미설정"}
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
                item_id = str(
                    node.get("법령일련번호")
                    or node.get("법령id")
                    or node.get("법령ID")
                    or node.get("lawId")
                    or node.get("판례일련번호")
                    or node.get("판례ID")
                    or node.get("precId")
                    or title
                )
                snippet = str(
                    node.get("제개정구분명")
                    or node.get("법령구분명")
                    or node.get("lawType")
                    or node.get("판시사항")
                    or node.get("사건종류명")
                    or title
                )
                source_name = "국가법령정보센터 OPEN API(법령)" if target == "law" else "국가법령정보센터 OPEN API(판례)"
                rows.append(
                    {
                        "chunk_id": f"law:{target}:{item_id}",
                        "title": title,
                        "source": source_name,
                        "snippet": snippet,
                        "score": 0.46 if target == "law" else 0.44,
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
                resp = client.get(f"{LAW_API_BASE}/lawSearch.do", params=params)
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
