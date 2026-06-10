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
    "docs/README.md",
    "docs/GITHUB_COLLABORATION_WORKFLOW.md",
    "docs/AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md",
    "docs/archive/AGENT_MCP_TASK_PLAN_GOAL_COMPLETION_LOG_2026-05.md",
    "docs/FUTURE_MSA_MCP_AGENT_EVOLUTION.md",
    "docs/STANDARD_MCP_DECISION.md",
    "docs/STANDARD_MCP_PILOT_DESIGN.md",
    "docs/PRESENTATION_ARCHITECTURE_NOTES.md",
    "docs/PROJECT_PRINCIPLE_COMPLIANCE_BACKLOG.md",
    "docs/AGENT_EXECUTION_QUALITY_CHECK.md",
    "docs/USER_VALUE_READINESS_CHECK.md",
    "docs/BUILD_AND_RUN_GUIDE.md",
    "docs/OPERATIONS.md",
    "docs/VERIFICATION_COMMANDS.md",
    "scripts/check_markdown_links.py",
    "scripts/check_principle_compliance.py",
    "scripts/check_agent_execution_quality.ps1",
    "scripts/check_srp_file_sizes.py",
    "scripts/check_staged_safety.py",
    "scripts/check_user_value_readiness.ps1",
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
        "path": "docs/README.md",
        "snippets": [
            "문서 선택 가이드",
            "PROJECT_PRINCIPLE_COMPLIANCE_BACKLOG.md",
            "AGENT_MCP_TASK_PLAN_GOAL_COMPLETION_LOG_2026-05.md",
            "STANDARD_MCP_DECISION.md",
            "check_principle_compliance.py",
        ],
    },
    {
        "path": "docs/AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md",
        "snippets": ["상태: active/reference", "완료된 구조 보강 요약", "FUTURE_MSA_MCP_AGENT_EVOLUTION.md"],
    },
    {
        "path": "docs/archive/AGENT_MCP_TASK_PLAN_GOAL_COMPLETION_LOG_2026-05.md",
        "snippets": ["P0-1", "P12-3", "Agent/MCP Task-Plan-Goal 구조 보강 로드맵"],
    },
    {
        "path": "docs/PROJECT_PRINCIPLE_COMPLIANCE_BACKLOG.md",
        "snippets": ["P0. 문서 시작점", "P1. SRP 위험 파일", "2026-06-10"],
    },
    {
        "path": "docs/STANDARD_MCP_DECISION.md",
        "snippets": ["상태: active/reference", "FUTURE_MSA_MCP_AGENT_EVOLUTION.md", "docs/architecture/"],
    },
    {
        "path": "docs/FUTURE_MSA_MCP_AGENT_EVOLUTION.md",
        "snippets": ["OSS 후속 구조 전환 메모", "Specialist Agent 페르소나", "표준 MCP 도입 Trigger"],
    },
    {
        "path": "docs/VERIFICATION_COMMANDS.md",
        "snippets": ["check_principle_compliance.py", "check_staged_safety.py"],
    },
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
