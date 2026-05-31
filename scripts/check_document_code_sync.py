"""Check that critical documentation references still match repository files.

This is a lightweight guard for P12-1. It intentionally checks only curated
high-signal paths and route/job strings to avoid noisy false positives from all
Markdown backticks.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_PATHS = [
    "DEVELOPMENT_PROMPT.md",
    "SYSTEM_OVERVIEW.md",
    "AGENTS.md",
    "compose.yaml",
    "env.example",
    "docs/GITHUB_COLLABORATION_WORKFLOW.md",
    "docs/AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md",
    "docs/STANDARD_MCP_DECISION.md",
    "docs/STANDARD_MCP_PILOT_DESIGN.md",
    "docs/PRESENTATION_ARCHITECTURE_NOTES.md",
    "docs/BUILD_AND_RUN_GUIDE.md",
    "docs/OPERATIONS.md",
    "docs/VERIFICATION_COMMANDS.md",
    "scripts/verify_core.ps1",
    "scripts/verify_agent_regression.ps1",
    "scripts/verify_final_readiness.ps1",
    "scripts/smoke_e2e.ps1",
    "scripts/validate_reference_case_manifest.py",
    "scripts/evaluate_video_reference_metrics.py",
    ".github/workflows/ci.yml",
    "apps/frontend/src/router/index.ts",
    "apps/frontend/src/views/AdminAgentTestView.vue",
    "apps/frontend/src/api/client.ts",
    "apps/gateway/src/main.ts",
    "apps/gateway/src/routes/analysis.ts",
    "apps/gateway/src/routes/uploads.ts",
    "apps/gateway/src/services/uploadService.ts",
    "apps/gateway/src/services/analysisService.ts",
    "apps/agent/app/routers/internal_routes/analysis.py",
    "apps/agent/app/routers/internal_routes/health.py",
    "apps/agent/app/mcp/standard_mcp_pilot.py",
    "apps/agent/app/mcp/tool_executor.py",
    "apps/agent/app/services/orchestrator.py",
    "apps/agent/app/services/agent_goal_aggregator.py",
    "apps/agent/app/services/video_input_contract.py",
    "apps/worker/worker/job_processor.py",
    "apps/worker/worker/video_preprocess.py",
    "apps/worker/worker/frame_analysis.py",
    "apps/worker/worker/yolo_frame_analysis.py",
]


REQUIRED_SNIPPETS = [
    {
        "path": "apps/frontend/src/router/index.ts",
        "snippets": ["/admin/agent-test"],
    },
    {
        "path": "apps/frontend/src/api/client.ts",
        "snippets": ["/api/v1/uploads/local", "/api/v1/cases/${caseId}/result"],
    },
    {
        "path": "apps/gateway/src/main.ts",
        "snippets": ['app.get("/health"', 'app.get("/ready"'],
    },
    {
        "path": "apps/gateway/src/routes/analysis.ts",
        "snippets": ["/internal/v1/analyze/text", "video_analyze"],
    },
    {
        "path": "apps/gateway/src/services/uploadService.ts",
        "snippets": ["video_preprocess", "storage_driver"],
    },
    {
        "path": "apps/agent/app/routers/internal_routes/analysis.py",
        "snippets": ['"/analyze/text"', '"/analyze/video"', '"/analyze/scenario"'],
    },
    {
        "path": "apps/agent/app/routers/internal_routes/health.py",
        "snippets": ['"/health"'],
    },
    {
        "path": "apps/worker/worker/job_processor.py",
        "snippets": ["video_preprocess", "video_analyze", "/internal/v1/analyze/video"],
    },
    {
        "path": "docs/AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md",
        "snippets": ["P12-1. 1차 점검: 문서와 코드 일치", "P12-2. 2차 점검: Agent 실행 품질"],
    },
    {
        "path": "docs/STANDARD_MCP_DECISION.md",
        "snippets": ["표준 MCP Host/Client/Server를 도입하지 않는다", "Agent 내부 MCP-like tool registry/executor"],
    },
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    missing_paths = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    missing_snippets: list[dict[str, str]] = []

    for item in REQUIRED_SNIPPETS:
        path = ROOT / item["path"]
        if not path.exists():
            missing_snippets.append({"path": item["path"], "snippet": "<file missing>"})
            continue
        text = read_text(path)
        for snippet in item["snippets"]:
            if snippet not in text:
                missing_snippets.append({"path": item["path"], "snippet": snippet})

    status = "passed" if not missing_paths and not missing_snippets else "failed"
    result = {
        "status": status,
        "required_path_count": len(REQUIRED_PATHS),
        "required_snippet_group_count": len(REQUIRED_SNIPPETS),
        "missing_paths": missing_paths,
        "missing_snippets": missing_snippets,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
