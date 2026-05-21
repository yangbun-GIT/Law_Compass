from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

from app.services.knia.knia_client import KniaClient
from app.services.knia.knia_parser import discover_ranking_ajax_paths, extract_main_text, infer_tags_keywords, parse_fault_chart, parse_ranking, parse_ranking_items
from app.services.knia.knia_repository import KniaRepository
from app.services.knia.taxonomy import classify_knia_accident_party_type

DEFAULT_MENU_PAGES = [
    ("과실비율의 이해", "과실비율이란?", "/baseInfo"),
    ("과실비율의 이해", "과실상계 절차와 근거", "/process"),
    ("과실비율의 이해", "과실분쟁해결 이야기", "/story"),
    ("과실비율의 이해", "과실비율 FAQ", "/faq"),
    ("과실비율의 이해", "과실비율 용어해설", "/dictionary"),
    ("과실비율 인정기준", "과실비율 인정기준이란?", "/standard-content"),
    ("과실비율 인정기준", "나의 과실비율 알아보기", "/myaccident"),
    ("과실비율 인정기준", "과실비율 검색순위", "/ranking"),
    ("과실비율 인정기준", "비정형 과실비율", "/atypical"),
]

STATIC_FALLBACK_CHARTS = [
    {
        "chart_no": "차41-1",
        "chart_type": "1",
        "title": "정차 또는 서행 중 후방 추돌",
        "vehicle_a_label": "앞 차량",
        "vehicle_b_label": "뒤 차량",
        "category_path": ["자동차 대 자동차", "후미추돌"],
        "accident_summary": "앞 차량이 정차 또는 서행 중일 때 뒤 차량이 추돌한 사고 유형입니다.",
        "applicable_text": "신호대기, 정체, 서행 등으로 앞 차량이 멈추거나 속도를 줄인 상황에서 뒤 차량이 추돌한 경우 참고할 수 있습니다.",
        "non_applicable_text": "앞 차량의 급정거, 끼어들기 직후 사고, 후진 사고 등은 별도 기준 검토가 필요합니다.",
        "basic_fault_text": "일반적으로 뒤 차량의 안전거리 미확보와 전방주시 태만이 중요한 판단 요소입니다.",
        "base_fault_a": 0,
        "base_fault_b": 100,
        "source_url": "https://accident.knia.or.kr/myaccident-content?chartNo=차41-1&chartType=1&arrayItem=",
        "thumbnail_url": None,
        "video_url": None,
    },
    {
        "chart_no": "차43-2",
        "chart_type": "1",
        "title": "후행 직진 차량과 선행 진로변경 차량 사고",
        "vehicle_a_label": "후행 직진 차량",
        "vehicle_b_label": "선행 진로변경 차량",
        "category_path": ["자동차 대 자동차", "진로변경"],
        "accident_summary": "앞 차량이 차로를 변경하고 뒤 차량이 직진하던 중 충돌한 사고 유형입니다.",
        "applicable_text": "진로변경 차량의 방향지시등, 진입 거리, 후행 차량의 속도와 전방주시 여부를 함께 봅니다.",
        "non_applicable_text": "완전히 진로변경이 끝난 뒤 상당 시간이 지난 경우는 별도 판단이 필요합니다.",
        "basic_fault_text": "차선을 바꾸는 차량의 주의의무가 중요한 기준입니다.",
        "base_fault_a": 30,
        "base_fault_b": 70,
        "source_url": "https://accident.knia.or.kr/myaccident-content?chartNo=차43-2&chartType=1&arrayItem=",
        "thumbnail_url": None,
        "video_url": None,
    },
    {
        "chart_no": "차12-1",
        "chart_type": "1",
        "title": "교차로 신호위반 충돌",
        "vehicle_a_label": "정상 신호 차량",
        "vehicle_b_label": "신호위반 차량",
        "category_path": ["자동차 대 자동차", "교차로"],
        "accident_summary": "교차로에서 한 차량이 신호를 위반해 충돌한 사고 유형입니다.",
        "applicable_text": "신호등 색, 진입 시점, 블랙박스 영상, 목격자 진술이 핵심입니다.",
        "basic_fault_text": "신호를 위반한 차량의 책임이 크게 검토될 수 있습니다.",
        "base_fault_a": 0,
        "base_fault_b": 100,
        "source_url": "https://accident.knia.or.kr/myaccident-content?chartNo=차12-1&chartType=1&arrayItem=",
        "thumbnail_url": None,
        "video_url": None,
    },
    {
        "chart_no": "보1-1",
        "chart_type": "1",
        "title": "횡단보도 보행자 접촉 사고",
        "vehicle_a_label": "차량",
        "vehicle_b_label": "보행자",
        "category_path": ["자동차 대 사람", "횡단보도"],
        "accident_summary": "횡단보도 또는 보행자 통행 구역에서 차량과 보행자가 접촉한 사고 유형입니다.",
        "applicable_text": "보행자 신호, 횡단보도 위치, 운전자 전방주시와 감속 여부를 함께 확인합니다.",
        "basic_fault_text": "보행자 보호의무와 인명피해 여부가 중요한 판단 요소입니다.",
        "base_fault_a": None,
        "base_fault_b": None,
        "source_url": "https://accident.knia.or.kr/myaccident",
        "thumbnail_url": None,
        "video_url": None,
    },
    {
        "chart_no": "자1-1",
        "chart_type": "1",
        "title": "차량과 자전거 충돌 사고",
        "vehicle_a_label": "차량",
        "vehicle_b_label": "자전거",
        "category_path": ["자동차 대 자전거", "자전거 충돌"],
        "accident_summary": "차량과 자전거 운전자가 충돌한 사고 유형입니다.",
        "applicable_text": "자전거 진행 방향, 자전거도로 여부, 우회전 또는 측면 충돌 여부를 확인합니다.",
        "basic_fault_text": "자전거 운전자 부상 여부와 양측 진행 방향이 중요한 판단 요소입니다.",
        "base_fault_a": None,
        "base_fault_b": None,
        "source_url": "https://accident.knia.or.kr/myaccident",
        "thumbnail_url": None,
        "video_url": None,
    },
    {
        "chart_no": "기1-1",
        "chart_type": "1",
        "title": "차량과 시설물 또는 기물 충돌 사고",
        "vehicle_a_label": "차량",
        "vehicle_b_label": "시설물",
        "category_path": ["자동차 대 기물", "시설물 충돌"],
        "accident_summary": "차량이 가드레일, 전봇대, 중앙분리대, 주차장 기둥 등 시설물과 충돌한 사고 유형입니다.",
        "applicable_text": "시설물 파손 사진, 사고 위치, 관리기관 여부, 노면 상태를 확인합니다.",
        "basic_fault_text": "시설물 파손과 단독/대물 보험 접수 여부가 중요한 판단 요소입니다.",
        "base_fault_a": None,
        "base_fault_b": None,
        "source_url": "https://accident.knia.or.kr/myaccident",
        "thumbnail_url": None,
        "video_url": None,
    },
    {
        "chart_no": "단1-1",
        "chart_type": "1",
        "title": "빗길 미끄러짐 등 차량단독 사고",
        "vehicle_a_label": "사고 차량",
        "vehicle_b_label": "없음",
        "category_path": ["차량단독", "혼자 난 사고"],
        "accident_summary": "빗길, 눈길, 졸음, 운전미숙 등으로 다른 차량 없이 혼자 발생한 사고 유형입니다.",
        "applicable_text": "운전자와 동승자 부상 여부, 2차 사고 위험, 노면 상태와 사고 위치를 확인합니다.",
        "basic_fault_text": "단독사고 접수와 2차 사고 방지가 중요합니다.",
        "base_fault_a": None,
        "base_fault_b": None,
        "source_url": "https://accident.knia.or.kr/myaccident",
        "thumbnail_url": None,
        "video_url": None,
    },
]


def load_scope() -> dict[str, Any]:
    here = Path(__file__).resolve()
    parent_candidates = [p / "config" / "knia_collect_scope.json" for p in here.parents]
    candidates = [
        Path(os.getenv("KNIA_COLLECT_SCOPE", "")) if os.getenv("KNIA_COLLECT_SCOPE") else None,
        Path("/app/config/knia_collect_scope.json"),
        Path.cwd() / "config" / "knia_collect_scope.json",
        *parent_candidates,
    ]
    for path in candidates:
        if path and path.exists():
            return json.loads(path.read_text(encoding="utf-8-sig"))
    return {"base_url": "https://accident.knia.or.kr", "priority_chart_nos": ["차41-1", "차43-2"], "rate_limit": {"max_charts_per_run": 50}}


class KniaCollector:
    def __init__(self, client: KniaClient | None = None, repo: KniaRepository | None = None):
        self.scope = load_scope()
        self.client = client or KniaClient()
        self.repo = repo or KniaRepository()
        self.base_url = self.scope.get("base_url") or "https://accident.knia.or.kr"

    def collect_menu_pages(self) -> dict[str, Any]:
        collected = 0
        errors: list[str] = []
        for group, name, path in DEFAULT_MENU_PAGES:
            url = self.client.absolute_url(path)
            try:
                parsed = extract_main_text(self.client.get(url))
            except Exception as exc:
                errors.append(f"{name}: {exc}")
                parsed = {"title": name, "content_text": f"{name} 관련 KNIA 과실비율정보포털 안내 페이지입니다. 원문은 {url}에서 확인할 수 있습니다.", "plain_summary": f"{name} 안내입니다."}
            self.repo.upsert_menu_page({
                "menu_group": group,
                "menu_name": name,
                "page_url": url,
                "title": parsed.get("title") or name,
                "content_text": parsed.get("content_text"),
                "plain_summary": parsed.get("plain_summary"),
                "source_url": url,
                "metadata": {"provider": "knia", "errors": errors[-1:] if errors else []},
            })
            collected += 1
        return {"collected_menu_pages": collected, "errors": errors}

    def collect_ranking(self) -> dict[str, Any]:
        url = self.client.absolute_url("/ranking")
        source_categories: list[tuple[str, str]] = [
            ("\uc804\uccb4", "all"),
            ("\ucc28\ub300\ucc28", "car_vs_car"),
            ("\ucc28\ub300\uc0ac\ub78c", "car_vs_person"),
            ("\ucc28\ub300\uc790\uc804\uac70", "car_vs_bicycle"),
        ]
        party_map = {source: party for source, party in source_categories}
        errors: list[str] = []
        counts: dict[str, int] = {}
        all_items: list[dict[str, Any]] = []
        try:
            ranking_html = self.client.get(url)
        except Exception as exc:
            ranking_html = ""
            errors.append(f"ranking_page: {exc}")
        ajax_paths = discover_ranking_ajax_paths(ranking_html)
        if "/selectRankList" not in ajax_paths:
            ajax_paths.insert(0, "/selectRankList")
        for category, party_type in source_categories:
            parsed: list[dict[str, Any]] = []
            # KNIA ranking page uses POST /selectRankList with CODENM equal to the button value.
            try:
                direct_payload = self.client.post("/selectRankList", data={"CODENM": category})
                parsed = parse_ranking_items(direct_payload, self.base_url, category)
            except Exception as exc:
                errors.append(f"selectRankList:{category}: {exc}")
            if not parsed and party_type == "all" and ranking_html:
                parsed = parse_ranking_items(ranking_html, self.base_url, category)
            if not parsed:
                for payload in self._fetch_ranking_category_payloads(category, ajax_paths):
                    parsed = parse_ranking_items(payload, self.base_url, category)
                    if parsed:
                        break
            for item in parsed:
                item["source_category"] = category
                item["accident_party_type"] = party_map[category]
                item["source_url"] = "https://accident.knia.or.kr/ranking"
                item["chart_type"] = str(item.get("chart_type") or "1")
                item.setdefault("source_detail_url", f"{self.base_url.rstrip('/')}/myaccident-content?chartNo={item['chart_no']}&chartType={item['chart_type']}&arrayItem=")
                item.setdefault("local_chart_url", f"/knia/charts/{item['chart_no']}?chartType={item['chart_type']}")
                item.setdefault("source_onclick", f"checkChartNo('{item['chart_no']}','{item['chart_type']}')")
                item["chart_url"] = item["local_chart_url"]
                item.setdefault("raw", {})
                item["raw"] = {**item.get("raw", {}), "source_category": category}
            counts[category] = len(parsed)
            all_items.extend(parsed)
        inserted = self.repo.upsert_ranking_items(all_items)
        # Preserve the legacy table for older screens, but only with the source "all" ranking.
        legacy_rows = [
            {
                "rank_no": x["rank"], "chart_no": x["chart_no"], "chart_type": "1", "title": x["title"],
                "search_count": x.get("search_count"), "percentage": x.get("percentage"),
                "source_url": x["source_url"], "thumbnail_url": None,
                "accident_party_type": x["accident_party_type"],
                "accident_party_label": category_label(x["accident_party_type"]), "display_tags": [],
            }
            for x in all_items if x.get("source_category") == "\uc804\uccb4"
        ]
        if legacy_rows:
            self.repo.insert_rankings(legacy_rows)
        detail_link_count = sum(1 for x in all_items if x.get("source_detail_url") and x.get("source_detail_url") != "https://accident.knia.or.kr/ranking")
        return {"ok": len(all_items) > 0, "ranking_count": len(all_items), "inserted": inserted, "detail_link_count": detail_link_count, "detail_link_failed": max(len(all_items) - detail_link_count, 0), "categories": counts, "errors": errors, "source_url": url}

    def _fetch_ranking_category_payloads(self, category: str, ajax_paths: list[str]) -> list[str]:
        payloads: list[str] = []
        param_candidates = [
            {"CODENM": category},
            {"searchType": category},
            {"rankType": category},
            {"rankingType": category},
            {"acdSrhCodeNm": category},
            {"acdNttySeCode": category},
            {"category": category},
            {"type": category},
            {"gubun": category},
        ]
        for path in ajax_paths[:12]:
            for params in param_candidates:
                try:
                    payload = self.client.get(path, params=params)
                    if payload and len(payload.strip()) > 20:
                        payloads.append(payload)
                except Exception:
                    pass
                try:
                    payload = self.client.post(path, data=params)
                    if payload and len(payload.strip()) > 20:
                        payloads.append(payload)
                except Exception:
                    pass
        return payloads

    def collect_chart_detail(self, chart_no: str, chart_type: str = "1") -> dict[str, Any]:
        encoded_chart_no = quote(str(chart_no), safe="")
        encoded_chart_type = quote(str(chart_type or "1"), safe="")
        source_url = f"{self.base_url.rstrip('/')}/myaccident-content?chartNo={encoded_chart_no}&chartType={encoded_chart_type}&arrayItem="
        html = self.client.get(source_url)
        chart = parse_fault_chart(html, source_url, chart_no=chart_no, chart_type=chart_type or "1")
        tags, keywords = infer_tags_keywords(" ".join([
            chart.get("title") or "",
            chart.get("accident_summary") or "",
            chart.get("accident_explanation") or "",
            chart.get("basic_fault_text") or "",
        ]))
        chart.setdefault("scenario_tags", tags)
        chart.setdefault("keywords", keywords)
        chart.setdefault("media_provider", "external_url")
        chart.setdefault("license_status", "source_link_only")
        chart.setdefault("attribution", "출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털")
        chart.update({k: v for k, v in classify_knia_accident_party_type(chart).items() if not chart.get(k)})
        chart_id = self.repo.upsert_chart(chart)
        return {
            "ok": True,
            "chart_id": chart_id,
            "chart_no": chart.get("chart_no"),
            "chart_type": chart.get("chart_type") or "1",
            "base_fault_a": chart.get("base_fault_a"),
            "base_fault_b": chart.get("base_fault_b"),
            "adjustment_factor_count": len(chart.get("adjustment_factors") or []),
            "reference_section_count": len(chart.get("adjustment_explanations") or []) + len(chart.get("related_laws") or []) + len(chart.get("case_references") or []),
            "related_law_count": len(chart.get("related_laws") or []),
            "case_reference_count": len(chart.get("case_references") or []),
            "source_detail_url": source_url,
        }

    def collect_ranking_chart_details(self, limit: int | None = None, force: bool = False) -> dict[str, Any]:
        targets = self.repo.ranking_chart_targets(limit=limit, force=force)
        collected = 0
        adjustment_factor_count = 0
        reference_section_count = 0
        sections = {"adjustment_explanation": 0, "related_law": 0, "case_reference": 0}
        failed: list[dict[str, Any]] = []
        for target in targets:
            try:
                result = self.collect_chart_detail(str(target["chart_no"]), str(target.get("chart_type") or "1"))
                collected += 1
                adjustment_factor_count += int(result.get("adjustment_factor_count") or 0)
                reference_section_count += int(result.get("reference_section_count") or 0)
                # Re-read references counts from result detail keys when available.
                sections["related_law"] += int(result.get("related_law_count") or 0)
                sections["case_reference"] += int(result.get("case_reference_count") or 0)
                sections["adjustment_explanation"] += max(int(result.get("reference_section_count") or 0) - int(result.get("related_law_count") or 0) - int(result.get("case_reference_count") or 0), 0)
            except Exception as exc:
                failed.append({"chart_no": target.get("chart_no"), "chart_type": target.get("chart_type") or "1", "error": str(exc)})
        return {
            "ok": collected > 0 and not failed,
            "target_count": len(targets),
            "collected_count": collected,
            "adjustment_factor_count": adjustment_factor_count,
            "reference_section_count": reference_section_count,
            "sections": sections,
            "failed": failed,
        }

    def collect_fault_charts(self, chart_nos: list[str] | None = None, max_charts: int | None = None) -> dict[str, Any]:
        max_charts = max_charts or int(os.getenv("KNIA_COLLECT_MAX_CHARTS", str(self.scope.get("rate_limit", {}).get("max_charts_per_run", 50))))
        candidates = chart_nos or self._candidate_chart_nos()
        if not candidates:
            candidates = [c["chart_no"] for c in STATIC_FALLBACK_CHARTS]
        collected = 0
        errors: list[str] = []
        for chart_no in candidates[:max_charts]:
            try:
                self.collect_chart_detail(chart_no, "1")
                collected += 1
                continue
            except Exception as exc:
                errors.append(f"{chart_no}: {exc}")
                chart = next((x.copy() for x in STATIC_FALLBACK_CHARTS if x["chart_no"] == chart_no), None)
                if not chart:
                    source_url = f"{self.base_url.rstrip('/')}/myaccident-content?chartNo={quote(chart_no, safe='')}&chartType=1&arrayItem="
                    tags, keywords = infer_tags_keywords(chart_no)
                    chart = {
                        "chart_no": chart_no,
                        "chart_type": "1",
                        "title": f"KNIA 과실비율 인정기준 {chart_no}",
                        "accident_summary": "원문 사이트에서 상세 내용을 확인할 수 있는 KNIA 과실비율 기준입니다.",
                        "source_url": source_url,
                        "thumbnail_url": None,
                        "video_url": None,
                        "base_fault_a": None,
                        "base_fault_b": None,
                        "scenario_tags": tags,
                        "keywords": keywords,
                    }
            tags, keywords = infer_tags_keywords(" ".join([chart.get("title") or "", chart.get("accident_summary") or "", chart.get("basic_fault_text") or ""]))
            chart.setdefault("scenario_tags", tags)
            chart.setdefault("keywords", keywords)
            chart.setdefault("media_provider", "external_url")
            chart.setdefault("license_status", "source_link_only")
            chart.setdefault("attribution", "출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털")
            chart.update({k: v for k, v in classify_knia_accident_party_type(chart).items() if not chart.get(k)})
            self.repo.upsert_chart(chart)
            collected += 1
        return {"collected_charts": collected, "errors": errors}

    def _candidate_chart_nos(self) -> list[str]:
        priority = self.scope.get("priority_chart_nos") or []
        candidates: list[str] = []
        if isinstance(priority, dict):
            for values in priority.values():
                if isinstance(values, list):
                    candidates.extend([str(x) for x in values if _looks_like_chart_no(str(x))])
        elif isinstance(priority, list):
            candidates.extend([str(x) for x in priority if _looks_like_chart_no(str(x))])
        try:
            candidates.extend([str(x.get("chart_no")) for x in self.repo.latest_ranking(limit=200) if x.get("chart_no")])
        except Exception:
            pass
        candidates.extend([c["chart_no"] for c in STATIC_FALLBACK_CHARTS])
        return list(dict.fromkeys([x for x in candidates if _looks_like_chart_no(x)]))


def _looks_like_chart_no(value: str) -> bool:
    if not value or " " in value:
        return False
    return any(value.startswith(prefix) for prefix in ["차", "보", "자", "기", "단"])


def category_label(accident_party_type: str) -> str:
    return {
        "all": "\uc804\uccb4",
        "car_vs_car": "\ucc28\ub300\ucc28",
        "car_vs_person": "\ucc28\ub300\uc0ac\ub78c",
        "car_vs_bicycle": "\ucc28\ub300\uc790\uc804\uac70",
    }.get(accident_party_type, "\uc804\uccb4")
