from __future__ import annotations

from urllib.parse import urlparse
from typing import Any


def select_media(chart: dict[str, Any] | None) -> dict[str, Any] | None:
    if not chart:
        return None
    source_url = chart.get("video_url") or chart.get("source_url")
    if not source_url:
        return None
    embed_url = chart.get("media_embed_url") if _can_embed(chart.get("media_embed_url")) else None
    display_mode = "embed" if embed_url else "external_link"
    return {
        "asset_type": "video" if chart.get("video_url") else "source_page",
        "storage_provider": "external_url",
        "source_url": source_url,
        "embed_url": embed_url,
        "thumbnail_url": chart.get("thumbnail_url"),
        "display_mode": display_mode,
        "button_label": "과실비율정보포털에서 관련 영상 보기" if chart.get("video_url") else "과실비율정보포털에서 보기",
        "attribution": chart.get("attribution") or "출처: 과실비율정보포털",
    }


def _can_embed(url: str | None) -> bool:
    if not url:
        return False
    host = urlparse(url).netloc.lower()
    return any(domain in host for domain in ["youtube.com", "youtu.be", "vimeo.com", "accident.knia.or.kr"])
