# LawCompass 문서 선택 가이드

이 문서는 새 작업을 시작할 때 어떤 문서를 먼저 읽고, 새 문서를 어디에 두며, 어떤 점검을 함께 실행할지 정리하는 문서 허브다.

## 작업 시작 순서

1. [DEVELOPMENT_PROMPT.md](../DEVELOPMENT_PROMPT.md)를 읽고 개발 원칙, 검증 원칙, 보안 원칙을 확인한다.
2. [SYSTEM_OVERVIEW.md](../SYSTEM_OVERVIEW.md)를 읽고 현재 서비스 구조, 변경 이력, 비변경 범위를 확인한다.
3. [GITHUB_COLLABORATION_WORKFLOW.md](GITHUB_COLLABORATION_WORKFLOW.md)를 읽고 최신 `main`, 커밋, 푸시, 동료 동기화 규칙을 확인한다.
4. Agent 구조, MCP 유사 실행, Task-Plan-Goal, evidence routing, video observation, judgment contract를 건드리면 [AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md](AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md)를 추가로 읽는다.

## 문서 위치 기준

| 작업 성격 | 우선 문서 |
| --- | --- |
| 현재 시스템 구조, route, DTO, DB, Redis, storage, 외부 연동 변경 | [SYSTEM_OVERVIEW.md](../SYSTEM_OVERVIEW.md) |
| 개발 원칙, 역할 정의, 검증 정책, 보안 정책, 서비스 책임 경계 변경 | [DEVELOPMENT_PROMPT.md](../DEVELOPMENT_PROMPT.md) |
| GitHub 브랜치, PR, merge notification, 동료 동기화 규칙 변경 | [GITHUB_COLLABORATION_WORKFLOW.md](GITHUB_COLLABORATION_WORKFLOW.md) |
| Agent/MCP/Task-Plan-Goal 현행 기준 | [AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md](AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md) |
| Agent/MCP/Task-Plan-Goal 상세 완료 기록 | [archive 완료 기록](archive/AGENT_MCP_TASK_PLAN_GOAL_COMPLETION_LOG_2026-05.md) |
| 표준 MCP 도입 보류 결정 | [STANDARD_MCP_DECISION.md](STANDARD_MCP_DECISION.md) |
| 표준 MCP pilot 설계 | [STANDARD_MCP_PILOT_DESIGN.md](STANDARD_MCP_PILOT_DESIGN.md) |
| OSS 후속 MSA/MCP/Agent 전환 검토 | [FUTURE_MSA_MCP_AGENT_EVOLUTION.md](FUTURE_MSA_MCP_AGENT_EVOLUTION.md) |
| 실행, 배포, 운영, import, 장애 대응 | [OPERATIONS.md](OPERATIONS.md) |
| 로컬 실행과 빌드 방법 | [BUILD_AND_RUN_GUIDE.md](BUILD_AND_RUN_GUIDE.md) |
| 검증 명령 모음 | [VERIFICATION_COMMANDS.md](VERIFICATION_COMMANDS.md) |
| 원칙 준수 보강 백로그 | [PROJECT_PRINCIPLE_COMPLIANCE_BACKLOG.md](PROJECT_PRINCIPLE_COMPLIANCE_BACKLOG.md) |

## 새 문서 추가 규칙

- 새 문서가 실행 명령, 구조, API, DB, Redis, 외부 연동, 검증 절차를 설명하면 이 파일 또는 관련 상위 문서에서 링크한다.
- 문서에 경로를 추가하면 실제 파일이 있는지 확인한다.
- 큰 구조 변경 없이 특정 기능만 설명하는 문서는 `docs/` 아래에 기능명 중심으로 둔다.
- 완료 기록과 날짜별 상세 로그는 현행 기준 문서와 섞이지 않도록 `docs/archive/` 아래에 둔다.
- 발표용 산출물은 `docs/presentation/` 아래에 둔다.
- 원본 PDF, 원본 영상, 대용량 로그, secret 값, `.env` 값은 문서에 직접 포함하지 않는다.

## 반복 점검 명령

문서와 원칙 준수 상태를 빠르게 확인할 때:

```powershell
python scripts/check_principle_compliance.py
```

문서 링크를 엄격히 확인할 때:

```powershell
python scripts/check_markdown_links.py --strict
```

SRP 위험 파일의 라인 수 경향을 확인할 때:

```powershell
python scripts/check_srp_file_sizes.py
```

커밋 직전 staged 파일에 민감 파일이나 secret 패턴이 섞였는지 확인할 때:

```powershell
python scripts/check_staged_safety.py
```
