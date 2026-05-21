from __future__ import annotations

import re

SUSPICIOUS_PATTERNS = [
    "ignore previous instructions",
    "system prompt",
    "developer message",
    "reveal hidden",
    "tool output raw",
]


def sanitize_input(text: str) -> tuple[str, list[str]]:
    lowered = text.lower()
    flags: list[str] = []
    sanitized = text

    for pattern in SUSPICIOUS_PATTERNS:
        if pattern in lowered:
            flags.append(f"prompt_injection:{pattern}")

    sanitized = re.sub(r"\b\d{2,3}-\d{3,4}-\d{4}\b", "[PHONE]", sanitized)
    sanitized = re.sub(r"\b\d{6}-?[1-4]\d{6}\b", "[NATIONAL_ID]", sanitized)
    sanitized = re.sub(r"\b\d{2,3}[가-힣]\s?\d{4}\b", "[PLATE]", sanitized)

    return sanitized, flags
