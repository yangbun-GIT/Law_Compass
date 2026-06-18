"""Report broken local Markdown links.

The default mode is advisory so existing historical docs do not block unrelated
work. Use ``--strict`` when a task moves or adds documentation links.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".git",
    ".local",
    ".pytest_cache",
    "__pycache__",
    "cache",
    "dist",
    "logs",
    "node_modules",
    "storage",
    "수정디자인패턴",
    "venv",
    ".venv",
}
SKIP_FILES = {"project_overview.md"}
LINK_RE = re.compile(r"!?\[[^\]]*]\(([^)]+)\)")
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def iter_markdown_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*.md"):
        if path.name in SKIP_FILES:
            continue
        if any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
            continue
        files.append(path)
    return sorted(files)


def clean_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    elif " " in target:
        target = target.split(" ", 1)[0]
    target = target.strip().strip("'\"")
    if "#" in target:
        target = target.split("#", 1)[0]
    if "?" in target:
        target = target.split("?", 1)[0]
    return unquote(target.strip())


def is_external_or_anchor(target: str) -> bool:
    return (
        not target
        or target.startswith("#")
        or target.startswith("//")
        or SCHEME_RE.match(target) is not None
    )


def resolve_target(source: Path, target: str) -> Path:
    if target.startswith("/"):
        return ROOT / target.lstrip("/")
    return source.parent / target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Exit 1 when broken links are found.")
    args = parser.parse_args()

    checked_links = 0
    skipped_links = 0
    broken_links: list[dict[str, str]] = []

    for md_file in iter_markdown_files():
        text = md_file.read_text(encoding="utf-8", errors="replace")
        text = FENCED_CODE_RE.sub("", text)
        for match in LINK_RE.finditer(text):
            raw_target = match.group(1)
            target = clean_target(raw_target)
            if is_external_or_anchor(target):
                skipped_links += 1
                continue
            checked_links += 1
            resolved = resolve_target(md_file, target)
            if not resolved.exists():
                broken_links.append(
                    {
                        "source": str(md_file.relative_to(ROOT)),
                        "target": raw_target.strip(),
                        "resolved": str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved),
                    }
                )

    status = "passed" if not broken_links else "failed" if args.strict else "warning"
    result = {
        "status": status,
        "strict": args.strict,
        "markdown_files": len(iter_markdown_files()),
        "checked_links": checked_links,
        "skipped_links": skipped_links,
        "broken_count": len(broken_links),
        "broken_links": broken_links[:100],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.strict and broken_links else 0


if __name__ == "__main__":
    sys.exit(main())
