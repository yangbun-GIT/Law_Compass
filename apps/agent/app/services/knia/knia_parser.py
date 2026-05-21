from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from typing import Any
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup
from app.services.knia.taxonomy import classify_knia_accident_party_type

ATTRIBUTION = "출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털"
KNOWN_CHART_TITLES = {
    "차41-1": "양 차량 주행 중 후방 추돌",
    "차43-2": "후행 직진 대 선행 진로변경",
    "차12-1": "교차로 신호위반 충돌",
}


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html or "", "html.parser")


def _clean(text: str | None) -> str:
    text = unescape(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_main_text(html: str) -> dict[str, Any]:
    soup = _soup(html)
    for bad in soup(["script", "style", "noscript"]):
        bad.decompose()
    title = _clean((soup.find("h1") or soup.find("h2") or soup.title).get_text(" ") if (soup.find("h1") or soup.find("h2") or soup.title) else "과실비율정보포털")
    candidates = []
    for selector in ["main", ".content", "#content", ".container", "body"]:
        node = soup.select_one(selector)
        if node:
            candidates.append(_clean(node.get_text(" ")))
    content = max(candidates, key=len) if candidates else _clean(soup.get_text(" "))
    return {"title": title[:240], "content_text": content[:30000], "plain_summary": content[:800]}


def _abs(base_url: str, value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().strip('"\'')
    if not value or value.startswith("data:"):
        return None
    return urljoin(base_url, value)


def _extract_chart_no(text: str) -> str | None:
    m = re.search(r"[\uCC28\uBCF4\uAC70]\s*\d{1,3}(?:-\d+)?", text or "")
    return re.sub(r"\s+", "", m.group(0)) if m else None


def _extract_percent_pair(text: str) -> tuple[int | None, int | None]:
    nums = [int(x) for x in re.findall(r"(?<!\d)(\d{1,3})\s*%", text or "") if 0 <= int(x) <= 100]
    if len(nums) >= 2:
        return nums[0], nums[1]
    m = re.search(r"(\d{1,3})\s*[:：]\s*(\d{1,3})", text or "")
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if 0 <= a <= 100 and 0 <= b <= 100:
            return a, b
    return None, None


def parse_ranking(html: str, base_url: str) -> list[dict[str, Any]]:
    soup = _soup(html)
    items: list[dict[str, Any]] = []
    text = _clean(soup.get_text(" "))
    rows = soup.select("tr, li, .ranking-list li, .rank-list li, .card, .list-item")
    for row in rows:
        row_text = _clean(row.get_text(" "))
        chart_no = _extract_chart_no(row_text)
        if not chart_no:
            continue
        rank_match = re.search(r"(?<!\d)(\d{1,2})(?:위|\.)?", row_text)
        rank_no = int(rank_match.group(1)) if rank_match else len(items) + 1
        link = row.find("a")
        href = _abs(base_url, link.get("href") if link else None) or f"{base_url.rstrip('/')}/myaccident-content?chartNo={chart_no}&chartType=1&arrayItem="
        img = row.find("img")
        percentage_match = re.search(r"(\d+(?:\.\d+)?)\s*%", row_text)
        count_match = re.search(r"([\d,]{4,})", row_text)
        title = row_text
        title = re.sub(r"^\d{1,2}\s*(위|\.)?", "", title).strip()
        if len(title) > 120:
            title = title[:120]
        items.append({
            "rank_no": rank_no,
            "chart_no": chart_no,
            "chart_type": "1",
            "title": title or f"KNIA \uACFC\uC2E4\uBE44\uC728 \uAE30\uC900 {chart_no}",
            "search_count": int(count_match.group(1).replace(",", "")) if count_match else None,
            "percentage": float(percentage_match.group(1)) if percentage_match else None,
            "source_url": href,
            "thumbnail_url": _abs(base_url, img.get("src") if img else None),
        })
    if not items:
        for idx, chart_no in enumerate(dict.fromkeys(re.findall(r"[\uCC28\uBCF4\uAC70]\d{1,3}(?:-\d+)?", text))):
            items.append({
                "rank_no": idx + 1,
                "chart_no": chart_no,
                "chart_type": "1",
                "title": f"KNIA 과실비율 기준 {chart_no}",
                "search_count": None,
                "percentage": None,
                "source_url": f"{base_url.rstrip('/')}/myaccident-content?chartNo={chart_no}&chartType=1&arrayItem=",
                "thumbnail_url": None,
            })
    enriched = []
    for item in items[:100]:
        party = classify_knia_accident_party_type(item)
        enriched.append({**item, **party})
    return enriched


def _node_text(soup: BeautifulSoup, selector: str) -> str | None:
    node = soup.select_one(selector)
    return _clean(node.get_text(" ") if node else "") or None


def _parse_int(value: Any) -> int:
    try:
        text = str(value or "").replace("+", "").replace(",", "").strip()
        return int(text) if re.fullmatch(r"-?\d+", text) else 0
    except Exception:
        return 0


def _score_from_node(soup: BeautifulSoup, selector: str, prefix: str) -> int | None:
    node = soup.select_one(selector)
    if not node:
        return None
    data_score = node.get("data-score")
    if data_score is not None and str(data_score).strip().lstrip("+-").isdigit():
        return int(data_score)
    text = _clean(node.get_text(" "))
    m = re.search(rf"{re.escape(prefix)}\s*(\d{{1,3}})", text, flags=re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d{1,3})", text)
    return int(m.group(1)) if m else None


def _extract_base_fault_from_dom(soup: BeautifulSoup) -> tuple[int | None, int | None]:
    row = soup.select_one("#default_accident")
    if row:
        a_node = row.select_one(".red")
        b_node = row.select_one(".orange")
        a = _parse_int(re.sub(r"[^0-9-]", "", _clean(a_node.get_text(" ") if a_node else ""))) if a_node else None
        b = _parse_int(re.sub(r"[^0-9-]", "", _clean(b_node.get_text(" ") if b_node else ""))) if b_node else None
        if a is not None and b is not None:
            return a, b
    return _extract_percent_pair(_clean(soup.get_text(" ")))


def _extract_accident_situation_lines(soup: BeautifulSoup) -> list[str]:
    container = soup.select_one("#caracdsittn")
    if not container:
        return []
    lines = [_clean(node.get_text(" ")) for node in container.select("._fnct_, td, div")]
    dedup: list[str] = []
    for line in lines:
        if line and line not in dedup and not line.startswith("사고상황"):
            dedup.append(line)
    return dedup[:12]


def _extract_adjustment_factors(soup: BeautifulSoup, chart_no: str, chart_type: str, source_detail_url: str) -> list[dict[str, Any]]:
    factors: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int, str]] = set()
    scope = soup.select_one("#applcscore") or soup.select_one("#macont01") or soup
    for idx, box in enumerate(scope.select(".checkbox"), start=1):
        if not (box.get("data-a") is not None or box.get("data-b") is not None):
            continue
        row = box.find_parent("tr") or box.find_parent("div") or box.parent
        label_node = None
        if row:
            label_node = row.find("label")
        label = _clean(label_node.get_text(" ") if label_node else "")
        if not label:
            row_text = _clean(row.get_text(" ") if row else box.get_text(" "))
            label = re.sub(r"[-+]?\d+\s*$", "", row_text).strip()
        if not label or label in {"가감요소", "A", "B"}:
            continue
        input_node = box.find("input")
        source_case_id = str(box.get("id") or "case1")
        delta_a = _parse_int(box.get("data-a"))
        delta_b = _parse_int(box.get("data-b"))
        key = (label, delta_a, delta_b, str(input_node.get("value") if input_node else ""))
        if key in seen:
            continue
        seen.add(key)
        party_side = "A" if delta_a else ("B" if delta_b else "")
        factors.append({
            "chart_no": chart_no,
            "chart_type": chart_type,
            "source_case_id": source_case_id,
            "factor_order": len(factors) + 1,
            "label": label,
            "condition_code": str(box.get("data-cnd") or ""),
            "checkbox_value": str(input_node.get("value") if input_node else ""),
            "party_side": party_side,
            "delta_a": delta_a,
            "delta_b": delta_b,
            "source_detail_url": source_detail_url,
            "raw": {
                "data_cnd": box.get("data-cnd"),
                "data_a": box.get("data-a"),
                "data_b": box.get("data-b"),
                "html": str(row)[:2000] if row else str(box)[:1000],
            },
        })
    return factors


def _paired_title_text_items(container: Any, title_selector: str = ".macont_exp_txtitle", text_selector: str = ".macont_exp_txt") -> list[tuple[str, str, str]]:
    if not container:
        return []
    items: list[tuple[str, str, str]] = []
    pending_title = ""
    pending_html = ""
    for exp in container.select(".macont_exp"):
        title_node = exp.select_one(title_selector)
        text_node = exp.select_one(text_selector)
        if title_node:
            pending_title = _clean(title_node.get_text(" "))
            pending_html = str(exp)
        if text_node:
            body = _clean(text_node.get_text(" "))
            if body:
                items.append((pending_title, body, (pending_html + str(exp))[:5000]))
                pending_title = ""
                pending_html = ""
    if not items:
        titles = [_clean(x.get_text(" ")) for x in container.select(title_selector)]
        texts = [_clean(x.get_text(" ")) for x in container.select(text_selector)]
        for idx, body in enumerate(texts):
            if body:
                items.append((titles[idx] if idx < len(titles) else "", body, ""))
    return items


def _extract_adjustment_explanations(soup: BeautifulSoup, source_detail_url: str) -> list[dict[str, Any]]:
    container = soup.select_one("#macont02")
    if not container:
        return []
    items: list[dict[str, Any]] = []
    # KNIA often stores all numbered explanations in one macont_exp block.
    for idx, text_node in enumerate(container.select(".macont_exp_txt"), start=1):
        body = _clean(text_node.get_text(" "))
        if not body or len(body) < 10:
            continue
        title = ""
        prev = text_node.find_previous_sibling()
        while prev:
            classes = prev.get("class") or []
            if "macont_exp_no" in classes:
                no = _clean(prev.get_text(" "))
                title = f"수정요소해설 {no}" if no else f"수정요소해설 {idx}"
                break
            prev = prev.find_previous_sibling()
        items.append({
            "section_type": "adjustment_explanation",
            "title": title or f"수정요소해설 {idx}",
            "body": body,
            "item_order": len(items) + 1,
            "source_detail_url": source_detail_url,
            "raw": {"html": str(text_node.find_parent(".macont_exp") or text_node)[:5000]},
        })
    if items:
        return items
    for idx, exp in enumerate(container.select(".macont_exp"), start=1):
        body = _clean(exp.get_text(" "))
        if body and len(body) >= 10:
            items.append({
                "section_type": "adjustment_explanation",
                "title": f"수정요소해설 {idx}",
                "body": body,
                "item_order": idx,
                "source_detail_url": source_detail_url,
                "raw": {"html": str(exp)[:5000]},
            })
    return items


def _extract_related_laws(soup: BeautifulSoup, source_detail_url: str) -> list[dict[str, Any]]:
    container = soup.select_one("#relatelrg") or soup.select_one("#macont03")
    items: list[dict[str, Any]] = []
    for idx, (law_title, law_text, raw_html) in enumerate(_paired_title_text_items(container), start=1):
        if not (law_title or law_text):
            continue
        items.append({
            "section_type": "related_law",
            "law_title": law_title,
            "law_text": law_text,
            "item_order": idx,
            "source_detail_url": source_detail_url,
            "raw": {"html": raw_html, "source": "KNIA 관련법규"},
        })
    return items


def _extract_case_references(soup: BeautifulSoup, source_detail_url: str) -> list[dict[str, Any]]:
    container = soup.select_one("#referprcdnt") or soup.select_one("#macont04")
    items: list[dict[str, Any]] = []
    for idx, (case_title, case_body, raw_html) in enumerate(_paired_title_text_items(container), start=1):
        if not (case_title or case_body):
            continue
        decision_summary = case_body[:260] + ("..." if len(case_body) > 260 else "")
        items.append({
            "section_type": "case_reference",
            "case_title": case_title or f"판례·조정사례 {idx}",
            "case_body": case_body,
            "decision_summary": decision_summary,
            "item_order": idx,
            "source_detail_url": source_detail_url,
            "raw": {"html": raw_html, "source": "KNIA 판례·조정사례"},
        })
    return items


def parse_fault_chart(html: str, source_url: str, chart_no: str | None = None, chart_type: str = "1") -> dict[str, Any]:
    soup = _soup(html)
    warnings: list[str] = []
    raw_html_hash = hashlib.sha256((html or "").encode("utf-8", errors="ignore")).hexdigest()
    for bad in soup(["script", "style", "noscript"]):
        bad.extract()
    body_text = _clean(soup.get_text(" "))
    found_chart = chart_no or _extract_chart_no(body_text) or "미확인"
    title_node = soup.select_one(".sub_cont_title, .macont_title, h1, h2, h3") or soup.title
    title = _clean(title_node.get_text(" ") if title_node else "")
    if found_chart in KNOWN_CHART_TITLES:
        title = KNOWN_CHART_TITLES[found_chart]
    if not title or len(title) < 3 or "분쟁심의위원회" in title:
        title = KNOWN_CHART_TITLES.get(found_chart, f"KNIA 과실비율 인정기준 {found_chart}")
        warnings.append("title_fallback")
    img = soup.find("img")
    thumb = _abs(source_url, img.get("src") if img else None)
    video_url = None
    embed_url = None
    video = soup.find("video")
    if video:
        video_url = _abs(source_url, video.get("src"))
        source = video.find("source")
        if not video_url and source:
            video_url = _abs(source_url, source.get("src"))
    iframe = soup.find("iframe")
    if iframe:
        embed_url = _abs(source_url, iframe.get("src"))
        video_url = video_url or embed_url
    if not video_url:
        m = re.search(r"https?://[^\s'\"]+\.(?:mp4|m3u8|webm)(?:\?[^\s'\"]*)?", html or "", flags=re.I)
        if m:
            video_url = m.group(0)
    base_a, base_b = _extract_base_fault_from_dom(soup)
    applied_a = _score_from_node(soup, "#case1_a_score", "A")
    applied_b = _score_from_node(soup, "#case1_b_score", "B")
    if applied_a is None:
        applied_a = base_a
    if applied_b is None:
        applied_b = base_b
    accident_situation_lines = _extract_accident_situation_lines(soup)
    accident_explanation = _node_text(soup, "#macont05")
    applicable = _node_text(soup, "#macont06") or _find_section(body_text, ["적용", "해당", "사고 상황"])
    non_applicable = _find_section(body_text, ["비적용", "해당하지", "제외"])
    basic_fault = _node_text(soup, "#macont07") or _extract_basic_fault(body_text) or _find_section(body_text, ["기본", "과실", "비율"])
    adjustment_factors = _extract_adjustment_factors(soup, found_chart, chart_type, source_url)
    adjustment_explanations = _extract_adjustment_explanations(soup, source_url)
    related_laws = _extract_related_laws(soup, source_url)
    case_references = _extract_case_references(soup, source_url)
    body_for_chart = _chart_window(body_text, found_chart)
    tags, keywords = infer_tags_keywords(" ".join([title, body_for_chart, accident_explanation or "", basic_fault or ""]))
    summary = accident_explanation or _extract_accident_summary(body_for_chart) or KNOWN_CHART_TITLES.get(found_chart) or title
    chart = {
        "chart_no": found_chart,
        "chart_type": chart_type,
        "title": title[:240],
        "vehicle_a_label": "A",
        "vehicle_b_label": "B",
        "category_path": [],
        "accident_summary": summary,
        "accident_explanation": accident_explanation,
        "accident_situation_lines": accident_situation_lines,
        "applicable_text": applicable,
        "non_applicable_text": non_applicable,
        "basic_fault_text": basic_fault or (f"기본 과실은 A{base_a}:B{base_b}로 표시된 자료가 있습니다." if base_a is not None and base_b is not None else None),
        "base_fault_a": base_a,
        "base_fault_b": base_b,
        "applied_fault_a": applied_a,
        "applied_fault_b": applied_b,
        "adjustment_factors": adjustment_factors,
        "adjustment_explanations": adjustment_explanations,
        "related_laws": related_laws,
        "case_references": case_references,
        "precedents": case_references,
        "source_url": source_url,
        "source_detail_url": source_url,
        "thumbnail_url": thumb,
        "video_url": video_url,
        "media_embed_url": embed_url,
        "media_provider": "external_url",
        "license_status": "source_link_only",
        "attribution": ATTRIBUTION,
        "metadata": {"parse_warnings": warnings, "text_length": len(body_text), "tab_ids": [x.get("id") for x in soup.select(".macont_tab_frm li") if x.get("id")]},
        "raw_detail": {
            "raw_html_hash": raw_html_hash,
            "has_fault_tab": bool(soup.select_one("#macont01")),
            "has_adjustment_explanation_tab": bool(soup.select_one("#macont02")),
            "has_related_law_tab": bool(soup.select_one("#macont03")),
            "has_case_reference_tab": bool(soup.select_one("#macont04")),
            "adjustment_factor_count": len(adjustment_factors),
            "reference_section_count": len(adjustment_explanations) + len(related_laws) + len(case_references),
        },
        "raw_html_hash": raw_html_hash,
        "scenario_tags": tags,
        "keywords": keywords,
    }
    return {**chart, **classify_knia_accident_party_type(chart)}

def _find_section(text: str, words: list[str]) -> str | None:
    sentences = re.split(r"(?<=[.!?。])\s+|\n+", text or "")
    selected = [_clean(s) for s in sentences if any(w in s for w in words)]
    return " ".join(selected[:4])[:900] if selected else None


def _chart_window(text: str, chart_no: str) -> str:
    idx = (text or "").find(chart_no)
    if idx < 0:
        return (text or "")[:1600]
    start = max(0, idx - 650)
    end = min(len(text), idx + 1150)
    return (text or "")[start:end]


def _extract_accident_summary(text: str) -> str | None:
    m = re.search(r"⊙\s*([^⊙]{20,420}?사고(?:이다|입니다)\.?)", text or "")
    if m:
        return _clean(m.group(1))
    return None


def _extract_basic_fault(text: str) -> str | None:
    m = re.search(r"(?:기본과실|기본 과실|기본비율|기본 비율)[^0-9]*(\d{1,3})\s*[:：]\s*(\d{1,3})", text or "")
    if m:
        return f"기본 참고 과실비율은 A차량 {m.group(1)}%, B차량 {m.group(2)}%로 표시된 자료입니다."
    return None


def infer_tags_keywords(text: str) -> tuple[list[str], list[str]]:
    tags: set[str] = set()
    keywords: set[str] = set()
    mapping = [
        ("rear_end", ["후미", "추돌", "뒤차", "후방", "안전거리"]),
        ("lane_change", ["차선", "진로변경", "끼어", "방향지시등"]),
        ("intersection", ["교차로", "신호", "좌회전", "우회전"]),
        ("signal_violation", ["신호위반", "적색", "빨간불"]),
        ("pedestrian", ["보행자", "횡단보도"]),
        ("parking", ["주차", "정차"]),
        ("fault_ratio", ["과실", "비율", "기본"]),
    ]
    for tag, words in mapping:
        if any(w in text for w in words):
            tags.add(tag)
            keywords.update(words)
    if not tags:
        tags.add("general_collision")
    return sorted(tags), sorted(keywords)[:20]




def build_chart_links(base_url: str, chart_no: str, chart_type: str = "1") -> dict[str, str]:
    encoded_chart_no = quote(str(chart_no), safe="")
    encoded_chart_type = quote(str(chart_type or "1"), safe="")
    return {
        "source_detail_url": f"{base_url.rstrip('/')}/myaccident-content?chartNo={encoded_chart_no}&chartType={encoded_chart_type}&arrayItem=",
        "local_chart_url": f"/knia/charts/{encoded_chart_no}?chartType={encoded_chart_type}",
        "source_onclick": f"checkChartNo('{chart_no}','{chart_type or '1'}')",
    }

RANKING_CATEGORY_MAP = {
    "\uc804\uccb4": "all",
    "\ucc28\ub300\ucc28": "car_vs_car",
    "\ucc28\ub300\uc0ac\ub78c": "car_vs_person",
    "\ucc28\ub300\uc790\uc804\uac70": "car_vs_bicycle",
}


def _first_value(row: dict[str, Any], keys: list[str]) -> Any:
    lowered = {str(k).lower(): v for k, v in row.items()}
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
        value = lowered.get(key.lower())
        if value not in (None, ""):
            return value
    return None


def _ranking_rows_from_json(value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            rows.extend(_ranking_rows_from_json(item))
    elif isinstance(value, dict):
        if any(key.lower() in {"chartno", "chart_no", "rank", "rankno", "ranking", "title", "acdnttypenm", "acdntty", "acdntty2", "opencount", "percent"} for key in map(str, value.keys())):
            rows.append(value)
        for item in value.values():
            if isinstance(item, (dict, list)):
                rows.extend(_ranking_rows_from_json(item))
    return rows


def _parse_ranking_json(payload: str, base_url: str, source_category: str) -> list[dict[str, Any]]:
    try:
        data = json.loads(payload)
    except Exception:
        return []
    party = RANKING_CATEGORY_MAP.get(source_category, "all")
    items: list[dict[str, Any]] = []
    for idx, row in enumerate(_ranking_rows_from_json(data), start=1):
        chart_no_raw = _first_value(row, ["chart_no", "chartNo", "chartno", "acdNo", "acdntNo", "acdntTypeNo", "accidentNo"])
        href_raw = str(_first_value(row, ["href", "url", "link", "source_url"]) or "")
        row_text = " ".join(str(v) for v in row.values() if v is not None)
        chart_no = _extract_chart_no(str(chart_no_raw or "")) or _extract_chart_no(href_raw) or _extract_chart_no(row_text)
        if not chart_no:
            continue
        chart_type = str(_first_value(row, ["chart_type", "chartType"]) or "1")
        rank_value = _first_value(row, ["rank", "rank_no", "rankNo", "ranking", "rnk", "ord", "display_order"])
        title = _first_value(row, ["title", "name", "acdNtty2", "acdNtty", "acdntTypeNm", "acdntTyNm", "chartTitle", "accidentTitle", "label"])
        count_value = _first_value(row, ["search_count", "searchCount", "openCount", "cnt", "count", "inqireCo", "viewCount"])
        pct_value = _first_value(row, ["percentage", "percent", "rate", "ratio"])
        links = build_chart_links(base_url, chart_no, chart_type)
        items.append({
            "rank": int(str(rank_value).replace(",", "")) if str(rank_value or "").replace(",", "").isdigit() else idx,
            "rank_no": int(str(rank_value).replace(",", "")) if str(rank_value or "").replace(",", "").isdigit() else idx,
            "chart_no": chart_no,
            "chart_type": chart_type,
            "title": str(title or f"KNIA \uACFC\uC2E4\uBE44\uC728 \uAE30\uC900 {chart_no}").strip(),
            "search_count": int(str(count_value).replace(",", "")) if str(count_value or "").replace(",", "").isdigit() else None,
            "percentage": float(str(pct_value).replace("%", "")) if str(pct_value or "").replace("%", "").replace(".", "", 1).isdigit() else None,
            "source_category": source_category,
            "accident_party_type": party,
            "source_url": "https://accident.knia.or.kr/ranking",
            "source_detail_url": links["source_detail_url"],
            "local_chart_url": links["local_chart_url"],
            "source_onclick": links["source_onclick"],
            "chart_url": links["local_chart_url"],
            "thumbnail_url": _abs(base_url, str(_first_value(row, ["thumbnail_url", "thumbnailUrl", "thumb", "image", "imgUrl"]) or "")) or None,
            "raw": {**row, "source_onclick": links["source_onclick"]},
        })
    return items


def parse_ranking_items(payload: str, base_url: str, source_category: str) -> list[dict[str, Any]]:
    """Parse KNIA ranking response from either HTML or JSON-like text.

    The public page renders rows server-side for the default tab and may use Ajax for category tabs.
    This parser intentionally accepts both full HTML and partial HTML fragments.
    """
    json_items = _parse_ranking_json(payload, base_url, source_category)
    if json_items:
        return json_items
    party = RANKING_CATEGORY_MAP.get(source_category, "all")
    soup = _soup(payload or "")
    items: list[dict[str, Any]] = []
    row_candidates = soup.select("tr, li, .ranking-list li, .rank-list li, .card, .list-item, .rank_cont, .rank-item, .ranking_item")
    if not row_candidates:
        row_candidates = list(soup.find_all(["div", "li", "tr"]))
    for row in row_candidates:
        row_text = _clean(row.get_text(" "))
        if not row_text:
            continue
        chart_no = _extract_chart_no(row_text)
        if not chart_no:
            link = row.find("a")
            chart_no = _extract_chart_no(link.get("href") if link else "")
        if not chart_no:
            continue
        rank_match = re.search(r"(?<!\d)(\d{1,2})\s*?", row_text) or re.search(r"^\s*(\d{1,2})\b", row_text)
        rank_no = int(rank_match.group(1)) if rank_match else len(items) + 1
        percentage_match = re.search(r"(\d+(?:\.\d+)?)\s*%", row_text)
        count_match = re.search(r"([\d,]{3,})\s*?", row_text)
        title = row_text
        title = re.sub(r"^\s*\d{1,2}\s*?\s*", "", title)
        title = title.replace(chart_no, " ")
        title = re.sub(r"\d+(?:\.\d+)?\s*%", " ", title)
        title = re.sub(r"[\d,]{3,}\s*?", " ", title)
        title = _clean(title)
        onclick_match = re.search(r"checkChartNo\(['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\)", str(row), flags=re.I)
        chart_type = onclick_match.group(2) if onclick_match else "1"
        if onclick_match:
            chart_no = _extract_chart_no(onclick_match.group(1)) or chart_no
        links = build_chart_links(base_url, chart_no, chart_type)
        href = links["source_detail_url"]
        img = row.find("img")
        items.append({
            "rank": rank_no,
            "rank_no": rank_no,
            "chart_no": chart_no,
            "chart_type": chart_type,
            "title": title or f"KNIA \uACFC\uC2E4\uBE44\uC728 \uAE30\uC900 {chart_no}",
            "search_count": int(count_match.group(1).replace(",", "")) if count_match else None,
            "percentage": float(percentage_match.group(1)) if percentage_match else None,
            "source_category": source_category,
            "accident_party_type": party,
            "source_url": "https://accident.knia.or.kr/ranking",
            "source_detail_url": links["source_detail_url"],
            "local_chart_url": links["local_chart_url"],
            "source_onclick": links["source_onclick"],
            "chart_url": links["local_chart_url"],
            "thumbnail_url": _abs(base_url, img.get("src") if img else None),
            "raw": {"row_text": row_text, "href": href, "source_onclick": links["source_onclick"]},
        })
    dedup: dict[tuple[int, str], dict[str, Any]] = {}
    for item in sorted(items, key=lambda x: x["rank"]):
        dedup[(item["rank"], item["chart_no"])] = item
    return list(dedup.values())[:50]


def discover_ranking_ajax_paths(html: str) -> list[str]:
    paths: list[str] = []
    for m in re.finditer(r"['\"](/[^'\"]*(?:ranking|Ranking|Rank|select)[^'\"]*)['\"]", html or ""):
        path = m.group(1)
        if path not in paths and "css" not in path.lower() and "js" not in path.lower():
            paths.append(path)
    preferred = ["/selectRanking", "/ranking/select", "/ranking/list", "/selectRankingList", "/selectRankingCount"]
    for path in preferred:
        if path not in paths:
            paths.append(path)
    return paths



