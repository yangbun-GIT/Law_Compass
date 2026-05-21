from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class KniaClientConfig:
    base_url: str = os.getenv("KNIA_BASE_URL", "https://accident.knia.or.kr")
    delay_ms: int = int(os.getenv("KNIA_REQUEST_DELAY_MS", "500"))
    timeout_sec: float = float(os.getenv("KNIA_TIMEOUT_SEC", "15"))
    user_agent: str = os.getenv(
        "KNIA_USER_AGENT",
        "LawCompassBot/0.1 (+local admin collection; contact: lawcompass.local)",
    )


class KniaClient:
    """Admin/batch crawler client. Never call this from user request paths."""

    def __init__(self, config: KniaClientConfig | None = None):
        self.config = config or KniaClientConfig()
        self._last_request_at = 0.0

    def absolute_url(self, path_or_url: str) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        path = path_or_url if path_or_url.startswith("/") else f"/{path_or_url}"
        return self.config.base_url.rstrip("/") + path

    def get(self, path_or_url: str, params: dict[str, Any] | None = None) -> str:
        elapsed = time.time() - self._last_request_at
        wait = max(0.0, self.config.delay_ms / 1000 - elapsed)
        if wait:
            time.sleep(wait)
        url = self.absolute_url(path_or_url)
        headers = {"user-agent": self.config.user_agent, "accept": "text/html,application/xhtml+xml"}
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=self.config.timeout_sec, follow_redirects=True) as client:
                    res = client.get(url, params=params, headers=headers)
                    res.raise_for_status()
                    self._last_request_at = time.time()
                    if not res.encoding:
                        res.encoding = "utf-8"
                    return res.text
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.8 * (attempt + 1))
        raise RuntimeError(f"KNIA request failed: {url}: {last_error}")
    def post(self, path_or_url: str, data: dict[str, Any] | None = None, json_body: dict[str, Any] | None = None) -> str:
        elapsed = time.time() - self._last_request_at
        wait = max(0.0, self.config.delay_ms / 1000 - elapsed)
        if wait:
            time.sleep(wait)
        url = self.absolute_url(path_or_url)
        headers = {
            "user-agent": self.config.user_agent,
            "accept": "text/html,application/json,*/*",
            "referer": self.absolute_url("/ranking"),
            "x-requested-with": "XMLHttpRequest",
        }
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=self.config.timeout_sec, follow_redirects=True) as client:
                    res = client.post(url, data=data, json=json_body, headers=headers)
                    res.raise_for_status()
                    self._last_request_at = time.time()
                    if not res.encoding:
                        res.encoding = "utf-8"
                    return res.text
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.8 * (attempt + 1))
        raise RuntimeError(f"KNIA POST failed: {url}: {last_error}")

