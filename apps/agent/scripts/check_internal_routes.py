from __future__ import annotations

import sys
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parents[1]
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from app.main import app

REQUIRED_PATHS = [
    "/internal/v1/health",
    "/internal/v1/analyze/text",
    "/internal/v1/analyze/video",
    "/internal/v1/analyze/scenario",
    "/internal/v1/jobs/process",
    "/internal/v1/legal/ingest",
    "/internal/v1/legal/rebuild-embeddings",
    "/internal/v1/legal/retrieval-test",
    "/internal/v1/chat/message",
    "/internal/v1/knia/collect/menu-pages",
    "/internal/v1/knia/collect/ranking",
    "/internal/v1/knia/collect/charts",
    "/internal/v1/knia/collect/ranking-details",
    "/internal/v1/knia/fault/estimate",
    "/internal/v1/knia/charts/{chart_no}/adjustments",
    "/internal/v1/knia/charts/{chart_no}/references",
    "/internal/v1/knia/rebuild-embeddings",
    "/internal/v1/knia/match",
    "/internal/v1/knia/retrieval-test",
    "/internal/v1/knia/import-json",
    "/internal/v1/knia/json/rebuild-embeddings",
    "/internal/v1/knia/myaccident-pages",
    "/internal/v1/knia/myaccident/{myaccident_no}/tree",
    "/internal/v1/knia/json/search",
    "/internal/v1/knia/media/search",
    "/internal/v1/cache/invalidate",
]


def main() -> None:
    registered_paths = {route.path for route in app.routes}
    missing = [path for path in REQUIRED_PATHS if path not in registered_paths]
    if missing:
        raise SystemExit(f"missing internal routes: {', '.join(missing)}")

    print(f"agent_internal_routes=passed required={len(REQUIRED_PATHS)} total={len(registered_paths)}")


if __name__ == "__main__":
    main()
