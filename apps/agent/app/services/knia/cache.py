from __future__ import annotations

import hashlib
import json
import os
from typing import Any

import redis


_REDIS_CLIENT: Any = None
_REDIS_DISABLED = object()


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))


def cache_digest(value: Any, length: int = 32) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()[:length]


def _client() -> Any:
    global _REDIS_CLIENT
    if _REDIS_CLIENT is _REDIS_DISABLED:
        return None
    if _REDIS_CLIENT is not None:
        return _REDIS_CLIENT
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        _REDIS_CLIENT = _REDIS_DISABLED
        return None
    try:
        _REDIS_CLIENT = redis.Redis.from_url(redis_url, decode_responses=True)
    except Exception:
        _REDIS_CLIENT = _REDIS_DISABLED
        return None
    return _REDIS_CLIENT


def get_json_cache(key: str) -> Any | None:
    client = _client()
    if not client:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def set_json_cache(key: str, value: Any, ttl_seconds: int) -> None:
    client = _client()
    if not client or ttl_seconds <= 0:
        return
    try:
        client.setex(key, ttl_seconds, stable_json(value))
    except Exception:
        return
