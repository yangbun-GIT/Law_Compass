from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin

from app.services.knia.knia_json_parser import URL_RE, infer_accident_party_type

BASE_URL = "https://accident.knia.or.kr"
ATTRIBUTION = "출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털"


def is_video_url(url: str) -> bool:
    lower = url.lower()
    return any(x in lower for x in [".mp4", ".webm", ".mov", "video", "vod", "movie", "youtube.com", "youtu.be", "vimeo.com"])


def is_image_url(url: str) -> bool:
    lower = url.lower()
    return any(lower.split("?")[0].endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"])


def classify_asset_type(url: str, metadata: dict[str, Any] | None = None) -> str:
    meta = json.dumps(metadata or {}, ensure_ascii=False).lower()
    if is_video_url(url) or "iframe" in meta:
        return "video"
    if is_image_url(url):
        return "image"
    return "link"


def _abs(url: str) -> str:
    if not url:
        return ""
    return urljoin(BASE_URL, url)


def _iter_urls(value: Any):
    if isinstance(value, str):
        for m in URL_RE.finditer(value):
            yield m.group(0)
    elif isinstance(value, dict):
        for key, v in value.items():
            if key in {"href", "src", "url", "source_url", "video_url", "thumbnail_url", "media_url", "embed_url"} and isinstance(v, str):
                yield v
            yield from _iter_urls(v)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_urls(item)


def _asset(url: str, *, document_id: str | None, title: str | None, party_type: str, metadata: dict[str, Any] | None = None) -> dict[str, Any] | None:
    source_url = _abs(url).strip()
    if not source_url or source_url.startswith("data:") or source_url.startswith("javascript:"):
        return None
    if any(x in source_url.lower() for x in [".css", ".js", ".woff", ".ttf"]):
        return None
    asset_type = classify_asset_type(source_url, metadata)
    if asset_type == "link" and "accident.knia.or.kr" not in source_url:
        return None
    return {
        "document_id": document_id,
        "asset_type": asset_type,
        "source_url": source_url,
        "embed_url": source_url if asset_type == "video" and any(x in source_url for x in ["youtube", "vimeo"]) else None,
        "title": title,
        "alt": (metadata or {}).get("alt") if isinstance(metadata, dict) else None,
        "mime_type": None,
        "accident_party_type": party_type,
        "attribution": ATTRIBUTION,
        "metadata": metadata or {},
    }


def extract_media_from_json(data: dict[str, Any]) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for doc in data.get("rag_documents") or []:
        doc_id = doc.get("doc_id")
        title = doc.get("title") or doc.get("label")
        party = infer_accident_party_type(" ".join([str(title or ""), str(doc.get("text") or "")]), doc.get("source_url") or "")
        meta = doc.get("metadata") or {}
        for link in meta.get("links") or []:
            href = link.get("href") if isinstance(link, dict) else str(link)
            item = _asset(href, document_id=doc_id, title=title, party_type=party["accident_party_type"], metadata=link if isinstance(link, dict) else {})
            if item and item["source_url"] not in seen:
                seen.add(item["source_url"]); assets.append(item)
        for image in meta.get("images") or []:
            src = image.get("src") if isinstance(image, dict) else str(image)
            item = _asset(src, document_id=doc_id, title=title, party_type=party["accident_party_type"], metadata=image if isinstance(image, dict) else {})
            if item and item["source_url"] not in seen:
                seen.add(item["source_url"]); assets.append(item)
    for page in data.get("pages") or []:
        party = infer_accident_party_type("", page.get("start_url") or "")
        for payload in page.get("network_payloads") or []:
            for url in _iter_urls(payload):
                item = _asset(url, document_id=None, title="KNIA 네트워크 미디어 후보", party_type=party["accident_party_type"], metadata={"from": "network_payload"})
                if item and item["source_url"] not in seen:
                    seen.add(item["source_url"]); assets.append(item)
    return assets


def build_external_media_response(asset: dict[str, Any]) -> dict[str, Any]:
    url = asset.get("embed_url") or asset.get("source_url")
    return {
        "asset_type": asset.get("asset_type", "link"),
        "source_url": asset.get("source_url"),
        "embed_url": asset.get("embed_url"),
        "display_mode": "embed" if asset.get("embed_url") else "external_link",
        "button_label": "과실비율정보포털에서 관련 영상 보기" if asset.get("asset_type") == "video" else "원문 자료 보기",
        "attribution": asset.get("attribution") or ATTRIBUTION,
        "title": asset.get("title") or "KNIA 관련 자료",
        "target_url": url,
    }
