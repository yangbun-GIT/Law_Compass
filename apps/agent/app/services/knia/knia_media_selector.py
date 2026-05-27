from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlparse

KNIA_ALLOWED_LINK_HOSTS = {"accident.knia.or.kr"}
KNIA_SOURCE_LINK_NOTICE = "영상 파일은 LawCompass 서버에 저장하지 않고, 과실비율정보포털 원본 링크로만 제공합니다."
DEFAULT_KNIA_LOGO_MARKERS = {"logo_test.jpg", "/images/common/logo_test"}


def select_media(chart: dict[str, Any] | None) -> dict[str, Any] | None:
    if not chart:
        return None
    video_url = safe_knia_url(chart.get("video_url"))
    source_detail_url = safe_knia_url(chart.get("source_detail_url"))
    source_page_url = safe_knia_url(chart.get("source_url"))
    source_url = video_url or source_detail_url or source_page_url
    if not source_url:
        return None
    return {
        "asset_type": "video" if video_url else "source_page",
        "storage_provider": "external_url",
        "source_url": source_url,
        "video_url": video_url or None,
        "source_detail_url": source_detail_url or None,
        "source_page_url": source_page_url or None,
        "embed_url": None,
        "media_embed_url": chart.get("media_embed_url"),
        "thumbnail_url": safe_knia_thumbnail_url(chart.get("thumbnail_url")) or None,
        "display_mode": "external_link",
        "button_label": "KNIA 관련 영상 보기" if video_url else "KNIA 원문 기준 보기",
        "notice": KNIA_SOURCE_LINK_NOTICE if _needs_source_link_notice(chart) else None,
        "attribution": chart.get("attribution") or "출처: 과실비율정보포털",
    }


def safe_knia_url(value: Any) -> str:
    text = str(value or "").strip()
    if not text or any(ch.isspace() for ch in text):
        return ""
    parsed = urlparse(text)
    if parsed.scheme.lower() not in {"http", "https"}:
        return ""
    host = (parsed.hostname or "").lower()
    if host not in KNIA_ALLOWED_LINK_HOSTS:
        return ""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
        return ""
    if parsed.username or parsed.password:
        return ""
    return text


def safe_knia_thumbnail_url(value: Any) -> str:
    text = safe_knia_url(value)
    if not text:
        return ""
    lowered = text.lower()
    if any(marker in lowered for marker in DEFAULT_KNIA_LOGO_MARKERS):
        return ""
    return text


def _needs_source_link_notice(chart: dict[str, Any]) -> bool:
    return chart.get("license_status") == "source_link_only" or chart.get("media_provider") == "external_url"
