from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from app.services.knia.taxonomy import infer_display_tags, party_actions, party_label

BASE_URL = "https://accident.knia.or.kr"
BLACKLIST_TEXTS = {
    "홈으로", "메뉴열기", "카카오톡", "개인정보처리방침", "검색", "본문 바로가기", "사이트맵",
    "과실비율의 이해", "과실비율 인정기준", "과실비율 분쟁심의위원회", "자동차사고 과실비율 분쟁심의위원회",
}
URL_RE = re.compile(r"https?://[^\s'\"<>]+")
CHART_RE = re.compile(r"(?:chartNo=)?([차보자기단]\s*\d{1,3}\s*-\s*\d{1,3}|\b\d{3}\b)")

PARTY_LABELS = {
    "car_vs_car": "차대차 사고",
    "car_vs_person": "차대사람 사고",
    "car_vs_bicycle": "차대자전거 사고",
    "car_vs_motorcycle": "차대이륜차 사고",
    "car_vs_object": "차대기물 사고",
    "single_vehicle": "차량단독 사고",
    "unknown": "사고유형 확인 필요",
}


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def infer_myaccident_no(url: str) -> int | None:
    text = url or ""
    m = re.search(r"myaccident(\d)", text)
    if m:
        return int(m.group(1))
    return None


def infer_accident_party_type(text: str, url: str = "", headings: list[Any] | None = None) -> dict[str, Any]:
    hay = " ".join([text or "", url or "", " ".join(map(str, headings or []))]).lower()
    def has(words: list[str]) -> bool:
        return any(w.lower() in hay for w in words)
    if has(["보행자", "사람", "횡단보도", "무단횡단", "어린이보호구역", "어린이"]):
        pt = "car_vs_person"
    elif has(["자전거", "자전거도로", "자전거 운전자"]):
        pt = "car_vs_bicycle"
    elif has(["이륜차", "오토바이", "원동기"]):
        pt = "car_vs_motorcycle"
    elif has(["기물", "시설물", "가드레일", "전봇대", "중앙분리대", "벽", "기둥", "낙하물"]):
        pt = "car_vs_object"
    elif has(["단독", "혼자", "전복", "미끄러짐", "도로 이탈", "빗길", "눈길"]):
        pt = "single_vehicle"
    elif has(["자동차", "차량", "후미추돌", "차선변경", "진로변경", "교차로", "신호위반", "좌회전", "우회전"]):
        pt = "car_vs_car"
    else:
        no = infer_myaccident_no(url)
        pt = {1: "car_vs_person", 2: "car_vs_car", 3: "car_vs_bicycle", 4: "car_vs_motorcycle", 5: "single_vehicle"}.get(no, "unknown")
    return {"accident_party_type": pt, "accident_party_label": PARTY_LABELS.get(pt, party_label(pt)), "display_tags": infer_display_tags(text)}


def extract_chart_no(text: str, href: str | None = None) -> dict[str, str] | None:
    combined = " ".join([text or "", href or ""])
    parsed = urlparse(href or "")
    qs = parse_qs(parsed.query)
    chart_no = (qs.get("chartNo") or [None])[0]
    chart_type = (qs.get("chartType") or ["1"])[0]
    if not chart_no:
        m = CHART_RE.search(combined)
        if m:
            chart_no = re.sub(r"\s+", "", m.group(1))
    if not chart_no:
        return None
    return {"chart_no": chart_no, "chart_type": chart_type or "1"}


def _iter_visible_items(page_data: dict[str, Any]):
    snap = page_data.get("initial_snapshot") or {}
    for item in snap.get("visible_items") or []:
        yield "initial", page_data.get("start_url"), item
    for idx, snap in enumerate(page_data.get("snapshots") or []):
        label = snap.get("label") or f"snapshot-{idx}"
        for item in snap.get("visible_items") or []:
            yield label, snap.get("url") or page_data.get("start_url"), item
    for idx, snap in enumerate(page_data.get("clicked_pages") or []):
        label = snap.get("label") or f"clicked-{idx}"
        for item in snap.get("visible_items") or []:
            yield label, snap.get("url") or page_data.get("start_url"), item


def _should_skip_label(label: str) -> bool:
    if not label or label in BLACKLIST_TEXTS:
        return True
    if len(label) < 2 or len(label) > 110:
        return True
    if label.startswith("http"):
        return True
    if re.fullmatch(r"[\W_]+", label):
        return True
    return False



def _page_html(page_data: dict[str, Any]) -> str:
    chunks: list[str] = []
    for payload in page_data.get("network_payloads") or []:
        if isinstance(payload, dict) and payload.get("text"):
            chunks.append(str(payload.get("text")))
    return "\n".join(chunks)


def _root_labels_from_visible_items(page_data: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for _snapshot_label, _url, item in _iter_visible_items(page_data):
        label = _norm(item.get("text"))
        if _should_skip_label(label):
            continue
        top = int(item.get("top") or 0)
        left = int(item.get("left") or 0)
        depth = int(item.get("depth") or 0)
        if left <= 240 and top >= 600 and depth <= 5 and label not in labels:
            labels.append(label)
    return labels


def _extract_script_menu_nodes(page_data: dict[str, Any]) -> list[dict[str, Any]]:
    html = _page_html(page_data)
    if "myaccident-content" not in html:
        return []
    page_url = page_data.get("start_url") or ""
    page_party = infer_accident_party_type("", page_url)
    root_ids: list[str] = []
    for m in re.finditer(r"var\s+_([A-Za-z0-9]+)\s*=\s*document\.getElementById\('([^']+)'\)", html):
        rid = m.group(2)
        if rid not in root_ids:
            root_ids.append(rid)
    root_labels = _root_labels_from_visible_items(page_data)
    nodes: list[dict[str, Any]] = []
    id_to_label: dict[str, str] = {}
    id_to_client: dict[str, str] = {}
    order = 0
    for idx, rid in enumerate(root_ids):
        label = root_labels[idx] if idx < len(root_labels) else rid
        party = infer_accident_party_type(label, page_url)
        if party["accident_party_type"] == "unknown":
            party = page_party
        client_id = f"root:{rid}"
        id_to_label[rid] = label
        id_to_client[rid] = client_id
        nodes.append({
            "client_id": client_id,
            "parent_client_id": None,
            "depth": 0,
            "display_order": order,
            "label": label,
            "normalized_label": label.lower(),
            "category_path": [label],
            "accident_party_type": party["accident_party_type"],
            "accident_party_label": party["accident_party_label"],
            "chart_no": None,
            "chart_type": None,
            "source_url": page_url,
            "source_snapshot_label": "script-root",
            "metadata": {"source": "script_root", "html_id": rid},
        })
        order += 1

    category_re = re.compile(
        r"var\s+_([A-Za-z0-9]+)_li\s*=\s*document\.createElement\('li'\);.*?" 
        r"_\1_li\.innerHTML\s*=\s*'(?P<html>.*?)';.*?" 
        r"var\s+_\1\s*=\s*document\.createElement\('ul'\);.*?" 
        r"_(?P<parent>[A-Za-z0-9]+)\.appendChild\(_\1_li\)",
        re.S,
    )
    chart_re = re.compile(
        r"var\s+_([A-Za-z0-9]+)_li\s*=\s*document\.createElement\('li'\);.*?" 
        r"var\s+_\1_chartNo\s*=\s*\"(?P<chart>[^\"]+)\";.*?" 
        r"href=\"(?P<href>[^\"]+)\".*?</span>(?P<label>.*?)</a>.*?" 
        r"_(?P<parent>[A-Za-z0-9]+)\.appendChild\(_\1_li\)",
        re.S,
    )
    events: list[tuple[int, str, Any]] = []
    for m in category_re.finditer(html):
        events.append((m.start(), "category", m))
    for m in chart_re.finditer(html):
        events.append((m.start(), "chart", m))
    events.sort(key=lambda x: x[0])

    def parent_path(parent_id: str) -> list[str]:
        parent_client = id_to_client.get(parent_id)
        if not parent_client:
            return []
        for n in nodes:
            if n["client_id"] == parent_client:
                return list(n.get("category_path") or [n["label"]])
        return []

    for _pos, kind, m in events:
        node_id = m.group(1)
        parent_id = m.group("parent")
        parent_client = id_to_client.get(parent_id)
        if not parent_client:
            continue
        if kind == "category":
            html_label = m.group("html")
            label_match = re.search(r'<span class="txt">(.*?)</span>', html_label)
            label = _norm(re.sub(r"<.*?>", "", label_match.group(1) if label_match else html_label))
            chart = None
            source_url = page_url
        else:
            chart_no = _norm(m.group("chart"))
            label = _norm(re.sub(r"<.*?>", "", m.group("label")))
            href = m.group("href")
            source_url = urljoin(BASE_URL, href)
            chart = extract_chart_no(label + " " + chart_no, source_url) or {"chart_no": chart_no, "chart_type": "1"}
        if _should_skip_label(label):
            continue
        path = parent_path(parent_id) + [label]
        party = infer_accident_party_type(" ".join(path), source_url)
        if party["accident_party_type"] == "unknown":
            party = page_party
        client_id = f"script:{node_id}:{order}"
        id_to_label[node_id] = label
        id_to_client[node_id] = client_id
        nodes.append({
            "client_id": client_id,
            "parent_client_id": parent_client,
            "depth": max(1, len(path) - 1),
            "display_order": order,
            "label": label,
            "normalized_label": label.lower(),
            "category_path": path,
            "accident_party_type": party["accident_party_type"],
            "accident_party_label": party["accident_party_label"],
            "chart_no": chart.get("chart_no") if chart else None,
            "chart_type": chart.get("chart_type") if chart else None,
            "source_url": source_url,
            "source_snapshot_label": "network-script",
            "metadata": {"source": "network_script", "html_id": node_id},
        })
        order += 1
    return nodes


def parse_visible_items_to_menu_nodes(page_data: dict[str, Any]) -> list[dict[str, Any]]:
    script_nodes = _extract_script_menu_nodes(page_data)
    if script_nodes:
        return script_nodes
    items = list(_iter_visible_items(page_data))
    depths = [int((it[2] or {}).get("depth") or 0) for it in items]
    min_depth = min(depths or [0])
    seen: set[str] = set()
    nodes: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = []
    page_url = page_data.get("start_url") or ""
    page_party = infer_accident_party_type("", page_url)
    for order, (snapshot_label, url, item) in enumerate(items):
        label = _norm(item.get("text"))
        if _should_skip_label(label):
            continue
        href = item.get("href") or url or page_url
        if href and href.startswith("/"):
            href = urljoin(BASE_URL, href)
        raw_depth = int(item.get("depth") or 0)
        depth = max(0, min(5, (raw_depth - min_depth) // 8))
        key = f"{label}|{href}|{depth}"
        if key in seen:
            continue
        seen.add(key)
        chart = extract_chart_no(label, href)
        party = infer_accident_party_type(label, href or page_url)
        if party["accident_party_type"] == "unknown":
            party = page_party
        while stack and stack[-1]["depth"] >= depth:
            stack.pop()
        category_path = [n["label"] for n in stack] + [label]
        node = {
            "client_id": _hash(key)[:24],
            "parent_client_id": stack[-1]["client_id"] if stack else None,
            "depth": depth,
            "display_order": order,
            "label": label,
            "normalized_label": label.lower(),
            "category_path": category_path,
            "accident_party_type": party["accident_party_type"],
            "accident_party_label": party["accident_party_label"],
            "chart_no": chart.get("chart_no") if chart else None,
            "chart_type": chart.get("chart_type") if chart else None,
            "source_url": href or page_url,
            "source_snapshot_label": snapshot_label,
            "metadata": {"tag": item.get("tag"), "class_name": item.get("class_name")},
        }
        nodes.append(node)
        stack.append(node)
    return nodes


def _keywords(text: str) -> list[str]:
    candidates = ["후미추돌", "정차", "차선변경", "진로변경", "교차로", "신호위반", "횡단보도", "보행자", "자전거", "이륜차", "오토바이", "가드레일", "단독", "빗길", "어린이보호구역"]
    return [x for x in candidates if x in text]


def _quality_score(text: str, source_url: str) -> float:
    if len(text) < 50:
        return 0.3
    if "myaccident-content" in source_url:
        return 0.9
    if re.search(r"myaccident[1-5]", source_url):
        return 0.75
    return 0.65


def _clean_doc_text(text: str) -> str:
    lines = []
    seen = set()
    for raw in (text or "").splitlines():
        line = _norm(raw)
        if _should_skip_label(line):
            continue
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return "\n".join(lines)


def build_rag_chunks_from_document(doc: dict[str, Any]) -> list[dict[str, Any]]:
    title = _norm(doc.get("title") or doc.get("label") or "KNIA 과실비율 기준")
    source_url = doc.get("source_url") or BASE_URL
    headings = doc.get("headings") or []
    text = _clean_doc_text(doc.get("text") or "")
    if len(text) < 50:
        return []
    party = infer_accident_party_type(" ".join([title, text]), source_url, headings)
    my_no = infer_myaccident_no(source_url)
    prefix = "\n".join([title, *[str(h) for h in headings[:5] if h]])
    body = f"{prefix}\n{text}".strip()
    chunks: list[dict[str, Any]] = []
    size = 1100
    overlap = 120
    start = 0
    idx = 0
    while start < len(body):
        chunk_text = body[start:start + size].strip()
        if len(chunk_text) >= 80:
            kws = _keywords(chunk_text)
            chunks.append({
                "chunk_index": idx,
                "chunk_type": "rag",
                "chunk_text": chunk_text,
                "plain_summary": chunk_text[:220].replace("\n", " "),
                "source_url": source_url,
                "myaccident_no": my_no,
                "accident_party_type": party["accident_party_type"],
                "accident_party_label": party["accident_party_label"],
                "scenario_tags": kws,
                "keywords": kws,
                "display_tags": party.get("display_tags") or kws[:5],
                "content_hash": _hash(chunk_text),
                "evidence_quality_score": _quality_score(chunk_text, source_url),
            })
            idx += 1
        start += size - overlap
    return chunks


def normalize_document(doc: dict[str, Any]) -> dict[str, Any]:
    source_url = doc.get("source_url") or BASE_URL
    title = _norm(doc.get("title") or doc.get("label") or "KNIA 과실비율 기준")
    text = _clean_doc_text(doc.get("text") or "")
    headings = doc.get("headings") or []
    party = infer_accident_party_type(" ".join([title, text]), source_url, headings)
    doc_id = doc.get("doc_id") or _hash(source_url + title)
    return {
        "id": doc_id,
        "source": doc.get("source") or "KNIA 자동차사고 과실비율 정보포털",
        "source_url": source_url,
        "title": title,
        "label": doc.get("label") or title,
        "headings": headings,
        "content": text,
        "content_hash": _hash(text),
        "myaccident_no": infer_myaccident_no(source_url),
        "accident_party_type": party["accident_party_type"],
        "accident_party_label": party["accident_party_label"],
        "metadata": doc.get("metadata") or {},
    }
