"""Block common secret and large/generated file mistakes before commit."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCKED_PATH_PATTERNS = [
    re.compile(r"(^|/)\.env($|\.)"),
    re.compile(r"(^|/)(storage|logs|node_modules|dist|cache|__pycache__|\.pytest_cache)(/|$)"),
    re.compile(r"\.(mp4|mov|avi|mkv|webm|zip|7z|tar|gz|pt|onnx|weights)$", re.IGNORECASE),
]
SECRET_PATTERNS = [
    re.compile(r"\b(?:OPENAI_API_KEY|LAW_API_OC|JWT_SECRET|INTERNAL_TOKEN|SERVICE_KEY|API_KEY|PASSWORD)\s*[:=]\s*['\"]?[A-Za-z0-9_\-./+=]{12,}", re.IGNORECASE),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
]


def decode_git_output(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def run_git(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True)


def staged_paths() -> list[str]:
    completed = run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMRT", "-z"])
    if completed.returncode != 0:
        raise RuntimeError(decode_git_output(completed.stderr).strip() or "git diff --cached failed")
    if not completed.stdout:
        return []
    return [decode_git_output(path) for path in completed.stdout.split(b"\0") if path]


def staged_content(path: str) -> str:
    completed = run_git(["show", f":{path}"])
    if completed.returncode != 0:
        return ""
    return decode_git_output(completed.stdout)


def main() -> int:
    blocked_paths: list[str] = []
    secret_hits: list[dict[str, str]] = []
    paths = staged_paths()

    for path in paths:
        normalized = path.replace("\\", "/")
        if any(pattern.search(normalized) for pattern in BLOCKED_PATH_PATTERNS):
            blocked_paths.append(path)
            continue

        content = staged_content(path)
        if not content:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                secret_hits.append({"path": path, "pattern": pattern.pattern})
                break

    status = "passed" if not blocked_paths and not secret_hits else "failed"
    result = {
        "status": status,
        "staged_count": len(paths),
        "blocked_paths": blocked_paths,
        "secret_hits": secret_hits,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
