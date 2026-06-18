# Agent/MCP Task-Plan-Goal 구조 보강 로드맵

상태: active/reference
용도: Agent/MCP-like/Task-Plan-Goal 구조 작업을 재개할 때 확인하는 현재 기준 문서
마지막 정리일: 2026-05-31

이 문서는 LawCompass의 Agent 구조를 다시 수정할 때 지켜야 하는 현재 기준만 남긴 문서다. P0~P12의 상세 구현 기록과 검증 로그는 [archive 완료 기록](../archive/AGENT_MCP_TASK_PLAN_GOAL_COMPLETION_LOG_2026-05.md)으로 분리했다.

## 1. 현재 결론

| 항목 | 현재 기준 |
| --- | --- |
| 구조 표현 | 완전한 표준 MCP 서버/클라이언트나 독립 Multi-Agent 프로세스가 아니라, Agent 서비스 내부의 role-based specialist pipeline + MCP-like tool registry/executor + Task-Plan-Goal packet 구조로 설명한다. |
| P0~P12 상태 | 2026-05-31 기준 전체 보강과 점검은 완료 상태다. 상세 완료 기록은 archive 문서를 참조한다. |
| 표준 MCP | 즉시 도입 보류. 내부 MCP-like registry/executor를 유지하되, 외부 tool server, cross-host 재사용, 표준 MCP client 요구가 생기면 재검토한다. |
| 독립 Agent | 현재는 역할 기반 specialist/analyzer 구조다. 완전 독립 Agent process는 OSS 후속 작업에서 검토한다. |
| 우선 보존할 품질 | 영상/입력 오염 방지, 사고축 근거 routing, 조건부 판단, finality 표시, 사용자 payload와 관리자 payload 분리, trace/usage/failure 관측성. |
| 금지 사항 | 특정 테스트 영상이나 특정 사고 문장에만 맞춘 규칙, 근거 없는 확정 판단, 표준 MCP 구현 완료처럼 과장된 표현, secret/원본 영상/AI-Hub 원천 데이터/GPU 모델 가중치 커밋. |

## 2. 관련 문서 우선순위

| 목적 | 먼저 볼 문서 |
| --- | --- |
| 전체 문서 지도 | [README.md](../README.md) |
| P0~P12 상세 완료 기록 | [archive 완료 기록](../archive/AGENT_MCP_TASK_PLAN_GOAL_COMPLETION_LOG_2026-05.md) |
| 현재 프로젝트 구조 | [SYSTEM_OVERVIEW.md](../../SYSTEM_OVERVIEW.md) |
| 개발 원칙과 검증 정책 | [DEVELOPMENT_PROMPT.md](../../DEVELOPMENT_PROMPT.md) |
| 표준 MCP 도입 보류 결정 | [STANDARD_MCP_DECISION.md](../architecture/STANDARD_MCP_DECISION.md) |
| 표준 MCP pilot 설계 | [STANDARD_MCP_PILOT_DESIGN.md](../architecture/STANDARD_MCP_PILOT_DESIGN.md) |
| 발표용 아키텍처 표현 | [PRESENTATION_ARCHITECTURE_NOTES.md](../architecture/PRESENTATION_ARCHITECTURE_NOTES.md) |
| Agent 실행 품질 점검 | [AGENT_EXECUTION_QUALITY_CHECK.md](AGENT_EXECUTION_QUALITY_CHECK.md) |
| 사용자 가치 점검 | [USER_VALUE_READINESS_CHECK.md](USER_VALUE_READINESS_CHECK.md) |
| OSS 후속 MSA/MCP/Agent 전환 메모 | [FUTURE_MSA_MCP_AGENT_EVOLUTION.md](../architecture/FUTURE_MSA_MCP_AGENT_EVOLUTION.md) |

## 3. 작업 원칙

- Agent/MCP/Task-Plan-Goal 관련 변경은 이 문서와 상세 완료 기록을 먼저 확인한 뒤 진행한다.
- 현재 정상 동작 중인 사용자 흐름, 관리자 테스트 흐름, Agent 결과 품질을 깨지 않는다.
- public API/DTO, DB schema, Redis key, storage path, 외부 API, Docker Compose 서비스 경계를 바꾸는 경우 `SYSTEM_OVERVIEW.md`를 함께 업데이트한다.
- 개발 원칙, 검증 방식, 역할 정의, 보안 기준, service responsibility boundary를 바꾸는 경우 `DEVELOPMENT_PROMPT.md`를 함께 업데이트한다.
- 판단 구조는 실제 사용자 입력과 미래의 새로운 사고 영상에도 일반화되어야 한다.
- 영상/텍스트/KNIA/법령/판례/보험 판단은 후보, 확인, 확정, 참고 상태를 분리한다.
- LLM은 근거 없는 판단을 확정하지 않는다. 법령, KNIA, 판례, 영상 관찰값, 사용자 입력, 불확실성 상태를 분리해 사용한다.
- 각 작업이 끝나면 목적 부합성 점검을 수행하고, 실패하면 해당 단계 안에 보정 작업을 추가한다.
- 수행하지 못한 검증은 완료로 말하지 않고 남은 작업으로 기록한다.

## 4. 완료된 구조 보강 요약

| 단계 | 상태 | 현재 의미 | 상세 기록 |
| --- | --- | --- | --- |
| P0 기준선 확정 | 완료 | 용어, 성공 기준, 구현 inventory, 회귀 기준선, 작업 문서 연결을 고정했다. | archive P0 |
| P1 핵심 계약 설계 | 완료 | Agent 실행 packet, Specialist Agent 결과, MCP Tool 계약을 additive schema로 정의했다. | archive P1 |
| P2 Task-Plan-Goal 연결 | 완료 | planner 실사용, stage별 task packet, goal 병합, 제한적 replan metadata를 연결했다. | archive P2 |
| P3 내부 MCP 계층 강화 | 완료 | tool registry schema, executor 권한/검증, route boundary, 표준 MCP gate를 정리했다. | archive P3 |
| P4 전문 Agent 역할 독립화 | 완료 | role profile, specialist adapter, persona/prompt version, consensus/conflict packet을 정리했다. | archive P4 |
| P5 영상 사실 추출 계약 | 완료 | 사고 기점, 직접 사고대상, 핵심 정량 fact 상태, reference 평가 경계를 정리했다. | archive P5 |
| P6 근거/판단 계약 | 완료 | 사고축 기반 evidence routing, 조건부 판단, 과실비율 결과 계약, 근거 표시 품질을 보강했다. | archive P6 |
| P7 표시 계약 | 완료 | 사용자 payload와 관리자 payload, 보완 질문, 결과 finality 표시를 분리했다. | archive P7 |
| P8 관측성/운영 리스크 | 완료 | trace id, LLM/vision usage, failure observation을 표준화했다. | archive P8 |
| P9 테스트/평가 체계 | 완료 | 단위/E2E/reference/CI 검증 명령을 확장했다. | archive P9 |
| P10 표준 MCP 판단 | 완료 | 표준 MCP 요구사항 재평가, pilot 설계, 도입 보류 결정을 문서화했다. | archive P10 |
| P11 문서/인수인계 | 완료 | 문서 동기화, 발표 설명, 팀원 인수인계 기준을 정리했다. | archive P11 |
| P12 최종 점검 | 완료 | 문서-코드 일치, Agent 실행 품질, 사용자 가치 점검을 수행했다. | archive P12 |

## 5. 현재 구조를 설명할 때의 기준 문장

- LawCompass는 Docker Compose 기반 경량 MSA형 모노레포다.
- 현재 Agent는 완전 독립 Multi-Agent process가 아니라 Agent 서비스 내부의 role-based specialist pipeline이다.
- 현재 MCP는 표준 MCP server/client가 아니라 내부 MCP-like tool registry/executor다.
- Task-Plan-Goal은 분석 흐름을 추적하고 품질을 점검하기 위한 packet/trace/goal aggregation 구조로 연결되어 있다.
- 영상 분석은 YOLO/OpenAI frame observation을 사고 판단의 직접 결론으로 쓰지 않고, Agent 입력 계약의 후보/확인/확정/충돌/무시 상태로 전달한다.
- 최종 사용자 결과는 법령, KNIA, 판례/근거, 영상 관찰값, 사용자 입력, 불확실성을 분리해 조건부 또는 참고 판단으로 표시해야 한다.

## 6. 앞으로 다시 열어야 하는 경우

다음 조건 중 하나가 생기면 이 문서를 기준으로 새 단계를 추가한다.

| 조건 | 처리 방향 |
| --- | --- |
| 외부 tool server, 표준 MCP client, cross-host tool 재사용이 실제 요구가 됨 | P10 이후 표준 MCP 도입 검토 단계를 새로 추가 |
| Specialist Agent가 별도 프로세스나 큐로 분리되어야 함 | OSS 후속 MSA/MCP 전환 문서와 함께 Agent lifecycle 설계 추가 |
| 영상 관찰값이 다시 보행자/자전거/환경 요소 오염을 일으킴 | P5/P6 기준을 참조해 사고대상, 환경, 원인, 근거축을 분리하는 보정 단계 추가 |
| 과실비율이 근거 없이 50:50 fallback으로 회귀함 | P6-2/P6-3 기준으로 조건부 판단과 결과 계약 회귀 테스트 추가 |
| 사용자 화면에 raw JSON, 영어 fallback, 내부 key, provider error가 노출됨 | P7/P8 기준으로 표시 계약과 sanitizer 회귀 테스트 추가 |
| 문서와 코드 경로, route, job type이 어긋남 | P12-1 문서-코드 일치 점검을 다시 실행하고 문서 업데이트 |

## 7. 새 작업 추가 규칙

1. 현재 문제와 가장 가까운 P단계를 고른다.
2. 기존 완료 기록을 수정하기보다 새 하위 단계 또는 보정 기록으로 추가한다.
3. 왜 기존 계약으로 부족했는지, 어떤 책임 경계를 바꾸는지, 어떤 회귀를 막는지 적는다.
4. 작업 후 검증 명령과 실패 시 남은 위험을 기록한다.
5. 상세 완료 기록이 길어지면 active 문서가 아니라 archive/reference 문서에 남긴다.

## 8. 작업 후 목적 부합성 점검

각 Agent/MCP/Task-Plan-Goal 관련 작업 후 아래 항목을 확인한다.

- 원래 목표와 실제 변경이 일치하는가?
- Frontend, Gateway, Agent, Worker, DB, Infra의 책임 경계를 침범하지 않았는가?
- 특정 테스트 케이스에만 맞춘 if/keyword 규칙이 생기지 않았는가?
- 영상 관찰값과 사용자 입력이 후보/확인/확정/충돌/참고 상태로 분리되는가?
- 법령/KNIA/판례/보험/형사 판단이 근거 없이 확정되지 않는가?
- 일반 사용자 payload와 관리자 payload가 분리되어 있는가?
- secret, API key, 원본 영상, AI-Hub 원천 데이터, YOLO 가중치, 대용량 로그가 Git에 들어가지 않았는가?
- 변경 범위에 맞는 검증을 실제로 수행했는가?

## 9. 검증 기준

문서만 변경한 경우에는 최소한 다음을 수행한다.

```powershell
git diff --check
rg -n "AGENT_MCP_TASK_PLAN_GOAL|COMPLETION_LOG|STANDARD_MCP|MCP-like" docs SYSTEM_OVERVIEW.md DEVELOPMENT_PROMPT.md
```

코드 변경이 포함되면 [VERIFICATION_COMMANDS.md](../VERIFICATION_COMMANDS.md)의 변경 범위별 명령을 따른다. Agent 실행 품질은 [AGENT_EXECUTION_QUALITY_CHECK.md](AGENT_EXECUTION_QUALITY_CHECK.md), 사용자 가치 점검은 [USER_VALUE_READINESS_CHECK.md](USER_VALUE_READINESS_CHECK.md)를 우선한다.

## 10. 문서 위치 정리 기준

- 이 문서는 Agent/MCP/Task-Plan-Goal 현행 기준이므로 `docs/agent/AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md`로 둔다.
- 완료 기록과 날짜별 상세 로그는 현재 작업 기준과 섞이지 않도록 `docs/archive/`에 둔다.
- 표준 MCP, 아키텍처 표현, 후속 MSA/MCP 전환 메모는 `docs/architecture/`에서 관리한다.
