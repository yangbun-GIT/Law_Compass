"""Run lightweight project principle compliance checks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_check(label: str, command: list[str]) -> dict[str, object]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    parsed_output: object
    try:
        parsed_output = json.loads(completed.stdout)
    except json.JSONDecodeError:
        parsed_output = completed.stdout.strip()
    return {
        "label": label,
        "command": command,
        "returncode": completed.returncode,
        "status": "passed" if completed.returncode == 0 else "failed",
        "stdout": parsed_output,
        "stderr": completed.stderr.strip(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict-links", action="store_true", help="Fail when local Markdown links are broken.")
    parser.add_argument("--fail-on-srp-warning", action="store_true", help="Fail when SRP watchlist warnings exist.")
    parser.add_argument("--skip-staged", action="store_true", help="Skip staged file safety checks.")
    args = parser.parse_args()

    checks: list[tuple[str, list[str]]] = [
        ("document_code_sync", [sys.executable, "scripts/check_document_code_sync.py"]),
        (
            "markdown_links",
            [sys.executable, "scripts/check_markdown_links.py"] + (["--strict"] if args.strict_links else []),
        ),
        (
            "srp_file_sizes",
            [sys.executable, "scripts/check_srp_file_sizes.py"]
            + (["--fail-on-warning"] if args.fail_on_srp_warning else []),
        ),
    ]
    if not args.skip_staged:
        checks.append(("staged_safety", [sys.executable, "scripts/check_staged_safety.py"]))

    results = [run_check(label, command) for label, command in checks]
    failed = [result for result in results if result["returncode"] != 0]
    summary = {
        "status": "passed" if not failed else "failed",
        "check_count": len(results),
        "failed_count": len(failed),
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
