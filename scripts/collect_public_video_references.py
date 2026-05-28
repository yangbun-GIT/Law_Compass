"""Collect public accident-video reference metadata into a safe manifest.

This script collects links and public metadata only. It never downloads video
files and marks every collected case as evaluation-only, not Agent input.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
DEFAULT_FOCUS = [
    "pedestrian_context_pollution",
    "traffic_signal_presence_pollution",
    "text_keyword_override_pollution",
]
DEFAULT_MUST_NOT_PROMOTE = [
    "pedestrian_crosswalk_accident",
    "opponent_signal_violation_when_not_visible",
    "vehicle_collision_without_collision_event",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect public accident-video links into a reference manifest."
    )
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="YouTube search query. Requires YOUTUBE_API_KEY unless --api-key-env is changed.",
    )
    parser.add_argument(
        "--urls",
        nargs="*",
        default=[],
        help="Public video URLs to add without downloading the original media.",
    )
    parser.add_argument(
        "--channel-id",
        default="",
        help="Optional YouTube channel id to limit search results.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Maximum YouTube results per query. Capped to 25.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output manifest path. Use a non-committed path for real working manifests.",
    )
    parser.add_argument(
        "--api-key-env",
        default="YOUTUBE_API_KEY",
        help="Environment variable containing a YouTube Data API key.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to an existing manifest instead of replacing it.",
    )
    return parser.parse_args()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def read_json_url(url: str, params: dict[str, str]) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{url}?{encoded}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_youtube_video_id(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower()
    if host.endswith("youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]
        return video_id or None
    if "youtube.com" in host:
        if parsed.path == "/watch":
            video_id = urllib.parse.parse_qs(parsed.query).get("v", [""])[0]
            return video_id or None
        match = re.match(r"^/(shorts|embed)/([^/?#]+)", parsed.path)
        if match:
            return match.group(2)
    return None


def safe_slug(text: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:80] or fallback


def reference_id_for_url(url: str, title: str = "") -> str:
    video_id = extract_youtube_video_id(url)
    if video_id:
        return f"yt_{safe_slug(video_id, 'video')}"
    parsed = urllib.parse.urlparse(url)
    seed = f"{parsed.netloc}_{parsed.path}_{title}"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"public_{safe_slug(seed, digest)}_{digest}"


def description_excerpt(text: str, limit: int = 450) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "..."


def build_case(
    *,
    url: str,
    title: str,
    description: str = "",
    platform_video_id: str = "",
    channel_title: str = "",
    published_at: str = "",
    query: str = "",
    collected_at: str = "",
) -> dict[str, Any]:
    collected_at = collected_at or utc_now()
    summary = description_excerpt(description, 220) or (
        "공개 영상 reference 후보입니다. 사고 상황 요약은 수동 검토 후 보강해야 합니다."
    )
    notes = [
        "자동 수집은 원본 영상을 다운로드하지 않고 공개 메타데이터와 링크만 기록합니다.",
        "사고 상황, 전문가 의견, 실제 처리 결과는 수동 검토 후 reference expectations에 반영합니다.",
        "이 reference는 Agent 입력 사실이 아니라 오염 탐지와 calibration 평가에만 사용합니다.",
    ]
    return {
        "id": reference_id_for_url(url, title),
        "title": title or "Public accident video reference candidate",
        "source_type": "public_reference_link",
        "source_url": url,
        "source_metadata": {
            "platform": "youtube" if extract_youtube_video_id(url) else "public_web",
            "platform_video_id": platform_video_id or extract_youtube_video_id(url) or "",
            "channel_title": channel_title,
            "published_at": published_at,
            "description_excerpt": description_excerpt(description),
            "collection_query": query,
            "collected_at": collected_at,
            "collection_status": "candidate_requires_manual_review",
        },
        "scenario_summary": summary,
        "reference_notes": notes,
        "reference_expectations": {
            "direct_collision_partner_type": "unknown",
            "accident_event_required": True,
            "expected_context": [],
            "must_not_promote": DEFAULT_MUST_NOT_PROMOTE,
        },
        "evaluation_focus": DEFAULT_FOCUS,
        "usage_policy": {
            "agent_input_allowed": False,
            "raw_video_commit_allowed": False,
            "notes": "Public reference links are collected for evaluation planning only. Do not commit raw video files or inject commentary as user facts.",
        },
    }


def youtube_search(api_key: str, query: str, channel_id: str, max_results: int) -> list[str]:
    params = {
        "part": "snippet",
        "type": "video",
        "q": query,
        "maxResults": str(min(max(max_results, 1), 25)),
        "key": api_key,
    }
    if channel_id:
        params["channelId"] = channel_id
    data = read_json_url(f"{YOUTUBE_API_BASE}/search", params)
    video_ids: list[str] = []
    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        if video_id:
            video_ids.append(video_id)
    return video_ids


def youtube_video_details(api_key: str, video_ids: list[str]) -> list[dict[str, Any]]:
    if not video_ids:
        return []
    params = {
        "part": "snippet",
        "id": ",".join(video_ids),
        "key": api_key,
    }
    data = read_json_url(f"{YOUTUBE_API_BASE}/videos", params)
    return data.get("items", [])


def collect_from_queries(args: argparse.Namespace) -> list[dict[str, Any]]:
    if not args.query:
        return []
    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        raise SystemExit(
            f"{args.api_key_env} is required for --query collection. "
            "Put the key in .env or the local shell environment, not in Git."
        )
    cases: list[dict[str, Any]] = []
    collected_at = utc_now()
    seen: set[str] = set()
    for query in args.query:
        video_ids = youtube_search(api_key, query, args.channel_id, args.max_results)
        for item in youtube_video_details(api_key, video_ids):
            video_id = item.get("id", "")
            if not video_id or video_id in seen:
                continue
            seen.add(video_id)
            snippet = item.get("snippet", {})
            url = f"https://www.youtube.com/watch?v={video_id}"
            cases.append(
                build_case(
                    url=url,
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    platform_video_id=video_id,
                    channel_title=snippet.get("channelTitle", ""),
                    published_at=snippet.get("publishedAt", ""),
                    query=query,
                    collected_at=collected_at,
                )
            )
    return cases


def collect_from_urls(urls: list[str]) -> list[dict[str, Any]]:
    collected_at = utc_now()
    cases: list[dict[str, Any]] = []
    for url in urls:
        normalized = url.strip()
        if not normalized:
            continue
        video_id = extract_youtube_video_id(normalized) or ""
        title = f"YouTube reference candidate {video_id}" if video_id else "Public reference candidate"
        cases.append(
            build_case(
                url=normalized,
                title=title,
                platform_video_id=video_id,
                collected_at=collected_at,
            )
        )
    return cases


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "version": dt.date.today().isoformat(),
            "purpose": "Public reference candidates for video observation contamination checks. Do not inject reference notes into Agent user-case payloads.",
            "cases": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def merge_cases(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {case["id"]: case for case in existing}
    for case in incoming:
        by_id[case["id"]] = case
    return list(by_id.values())


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    incoming = collect_from_urls(args.urls) + collect_from_queries(args)
    manifest = load_manifest(output) if args.append else {
        "version": dt.date.today().isoformat(),
        "purpose": "Public reference candidates for video observation contamination checks. Do not inject reference notes into Agent user-case payloads.",
        "cases": [],
    }
    manifest["cases"] = merge_cases(manifest.get("cases", []), incoming)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(incoming)} collected cases to {output}")
    print("raw videos were not downloaded; review scenario_summary and reference_expectations before evaluation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
