# 문서와 코드 정합성 점검

작성일: 2026-05-31

이 문서는 P12-1 기준으로 문서에 적힌 핵심 구조가 실제 저장소 파일과 맞는지 확인한 결과를 남긴다.

## 1. 점검 범위

반복 가능한 점검은 `scripts/check_document_code_sync.py`에서 수행한다.

점검 대상:

- 선행 참조 문서: `DEVELOPMENT_PROMPT.md`, `SYSTEM_OVERVIEW.md`, `AGENTS.md`
- 협업/운영 문서: `docs/GITHUB_COLLABORATION_WORKFLOW.md`, `docs/BUILD_AND_RUN_GUIDE.md`, `docs/OPERATIONS.md`, `docs/VERIFICATION_COMMANDS.md`
- Agent/MCP 문서: `docs/agent/AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md`, `docs/architecture/STANDARD_MCP_DECISION.md`, `docs/architecture/STANDARD_MCP_PILOT_DESIGN.md`, `docs/architecture/PRESENTATION_ARCHITECTURE_NOTES.md`
- 실행 스크립트: `scripts/verify_core.ps1`, `scripts/verify_agent_regression.ps1`, `scripts/verify_final_readiness.ps1`, `scripts/smoke_e2e.ps1`
- 핵심 코드 경로: Frontend router/API, Gateway main/routes/services, Agent internal route/MCP/service, Worker job/video/frame/yolo 처리 파일
- 핵심 route/job 문자열: `/admin/agent-test`, `/api/v1/uploads/local`, `/health`, `/ready`, `/internal/v1/analyze/text`, `/internal/v1/analyze/video`, `video_preprocess`, `video_analyze`

## 2. 실행 방법

```powershell
python scripts/check_document_code_sync.py
```

통과 기준:

- 문서가 참조하는 핵심 파일이 존재한다.
- 문서에 적힌 핵심 endpoint와 job type이 실제 코드에 남아 있다.
- 표준 MCP는 도입 완료가 아니라 내부 MCP-like registry/executor 유지와 도입 보류 결정으로 표현된다.

## 3. P12-1 점검 결과

2026-05-31 기준 점검 결과는 `passed`다.

확인된 내용:

- 사용자 서비스와 관리자 테스트 페이지 route가 실제 Frontend router/API와 일치한다.
- Gateway `/health`, `/ready`, upload, analysis route가 문서와 맞는다.
- Agent `/internal/v1/analyze/text`, `/internal/v1/analyze/video`, `/internal/v1/analyze/scenario`, `/internal/v1/health` 경로가 문서와 맞는다.
- Worker `video_preprocess`, `video_analyze` job type과 Agent video 호출 경로가 문서와 맞는다.
- 표준 MCP는 Host/Client/Server 도입 완료가 아니라 내부 MCP-like tool registry/executor 유지와 보류 결정으로 정리되어 있다.

## 4. 한계

이 스크립트는 모든 Markdown backtick 경로를 자동 파싱하지 않는다. 오래된 문서 전체를 무차별 검사하면 코드 예시, 외부 URL, 의도적 과거 기록까지 false positive가 많기 때문에, 발표/인수인계와 실행 안정성에 직접 영향을 주는 curated reference만 점검한다.
