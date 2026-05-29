from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

PAGES = [f"https://accident.knia.or.kr/myaccident{i}" for i in range(1, 6)]
OUTPUT_PATH = Path(__file__).resolve().parent / "knia_myaccident_tree.json"
CHART_RE = re.compile(r"([차보거자기단]\d{1,3})(?:-(\d+))?")


def main() -> int:
    try:
        import requests
        from bs4 import BeautifulSoup
    except Exception as exc:
        print(json.dumps({"ok": False, "reason": f"collector_dependencies_unavailable:{exc.__class__.__name__}"}, ensure_ascii=False))
        return 2

    session = requests.Session()
    nodes: list[dict[str, Any]] = []
    for page_url in PAGES:
        html = _fetch(session, page_url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        major_label = _page_label(page_url, soup)
        for element in soup.find_all(["a", "button", "li", "span", "div"]):
            text = " ".join(element.get_text(" ", strip=True).split())
            attrs = " ".join(str(value) for value in element.attrs.values())
            match = CHART_RE.search(f"{text} {attrs}")
            if not match:
                continue
            chart_no = match.group(1)
            subchart_no = f"{chart_no}-{match.group(2)}" if match.group(2) else None
            href = element.get("href") or ""
            source_url = urljoin(page_url, href) if href and not href.startswith("#") else _fallback_url(subchart_no or chart_no)
            nodes.append(
                {
                    "major_page": page_url.rsplit("/", 1)[-1],
                    "major_url": page_url,
                    "major_label": major_label,
                    "depth": _depth(element),
                    "menu_path": [major_label, text] if text else [major_label],
                    "label": text or subchart_no or chart_no,
                    "chart_no": chart_no,
                    "subchart_no": subchart_no,
                    "source_url": source_url,
                    "image_url": _first_image_url(page_url, element),
                    "raw_text": text,
                    "children_count": len(element.find_all(["li", "a", "button"])),
                }
            )
        time.sleep(0.8)

    payload = {
        "metadata": {
            "source": "https://accident.knia.or.kr/myaccident1..5",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "version": "lawcompass-knia-myaccident-tree-v1",
        },
        "nodes": _dedupe_nodes(nodes),
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "nodes": len(payload["nodes"]), "output": str(OUTPUT_PATH)}, ensure_ascii=False))
    return 0


def _fetch(session: Any, url: str) -> str:
    last_error = None
    for _ in range(2):
        try:
            response = session.get(url, timeout=12, headers={"User-Agent": "LawCompass KNIA tree collector/1.0"})
            response.raise_for_status()
            response.encoding = response.encoding or "utf-8"
            return response.text
        except Exception as exc:
            last_error = exc
            time.sleep(1.0)
    print(json.dumps({"ok": False, "url": url, "error": str(last_error)}, ensure_ascii=False))
    return ""


def _page_label(url: str, soup: Any) -> str:
    title = " ".join((soup.title.string if soup.title and soup.title.string else "").split())
    if title:
        return title
    page = url.rsplit("/", 1)[-1]
    return {
        "myaccident1": "자동차와 자동차의 사고",
        "myaccident2": "자동차와 보행자의 사고",
        "myaccident3": "자동차와 자전거의 사고",
        "myaccident4": "자동차와 이륜차의 사고",
        "myaccident5": "기타 사고",
    }.get(page, "KNIA 과실비율 인정기준")


def _depth(element: Any) -> int:
    depth = 1
    parent = element.parent
    while parent is not None:
        if getattr(parent, "name", "") in {"ul", "ol", "li"}:
            depth += 1
        parent = parent.parent
    return min(depth, 8)


def _first_image_url(base_url: str, element: Any) -> str | None:
    image = element.find("img") if hasattr(element, "find") else None
    src = image.get("src") if image else None
    return urljoin(base_url, src) if src else None


def _fallback_url(chart_no: str) -> str:
    return f"https://accident.knia.or.kr/myaccident-content?chartNo={chart_no}&chartType=1"


def _dedupe_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str | None, str]] = set()
    result: list[dict[str, Any]] = []
    for node in nodes:
        key = (str(node.get("chart_no") or ""), node.get("subchart_no"), str(node.get("source_url") or ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(node)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
