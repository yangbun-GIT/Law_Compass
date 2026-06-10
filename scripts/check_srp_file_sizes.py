"""Warn when known SRP-risk files keep growing.

This check is intentionally advisory by default. A large file is not an
automatic failure, but the warning helps reviewers decide whether a touched
feature should be split into a smaller module.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WATCHLIST = {
    "apps/gateway/src/lib/report-composer.ts": 900,
    "apps/gateway/src/routes/analysis.ts": 900,
    "apps/gateway/src/routes/knia.ts": 900,
    "apps/frontend/src/composables/useCaseWorkspace.ts": 700,
    "apps/frontend/src/views/AdminAgentTestView.vue": 900,
    "apps/frontend/src/data/caseWorkspaceGuidanceData.ts": 900,
    "apps/agent/app/services/input_normalizer.py": 900,
    "apps/agent/app/services/scenario_classifier.py": 900,
    "apps/agent/app/services/fact_arbitration.py": 900,
    "apps/agent/app/services/knia/knia_matcher.py": 900,
    "apps/agent/app/services/knia/knia_json_repository.py": 900,
    "apps/worker/worker/frame_analysis.py": 900,
    "apps/worker/worker/yolo_frame_analysis.py": 900,
}


def count_lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fail-on-warning", action="store_true", help="Exit 1 when a watchlist file exceeds threshold.")
    args = parser.parse_args()

    warnings: list[dict[str, object]] = []
    missing: list[str] = []
    measurements: list[dict[str, object]] = []

    for relative_path, threshold in WATCHLIST.items():
        path = ROOT / relative_path
        if not path.exists():
            missing.append(relative_path)
            continue
        line_count = count_lines(path)
        measurement = {
            "path": relative_path,
            "line_count": line_count,
            "threshold": threshold,
            "over_threshold": line_count > threshold,
        }
        measurements.append(measurement)
        if line_count > threshold:
            warnings.append(measurement)

    status = "passed" if not warnings else "failed" if args.fail_on_warning else "warning"
    result = {
        "status": status,
        "fail_on_warning": args.fail_on_warning,
        "watchlist_count": len(WATCHLIST),
        "warning_count": len(warnings),
        "missing_count": len(missing),
        "warnings": warnings,
        "missing": missing,
        "measurements": measurements,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if args.fail_on_warning and warnings else 0


if __name__ == "__main__":
    sys.exit(main())
