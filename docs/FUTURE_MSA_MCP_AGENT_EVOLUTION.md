# OSS 후속 MSA/MCP/Agent 전환 메모

상태: future/reference
작성일: 2026-06-10

이 문서는 현재 LawCompass Agent 구조를 당장 바꾸기 위한 작업 지시가 아니라, OSS 후속 작업에서 MSA/MCP/Agent 구조를 더 분리해야 할 때 확인할 기준을 남긴 메모다.

## 현재 기준

- 현재 Agent는 표준 MCP 서버/클라이언트가 아니라 Agent 서비스 내부의 MCP-like tool registry/executor를 사용한다.
- 현재 전문 Agent는 독립 프로세스가 아니라 role-based specialist pipeline과 deterministic analyzer 모듈에 가깝다.
- Task-Plan-Goal은 분석 품질과 trace를 안정화하기 위한 packet/goal aggregation 구조로 연결되어 있다.
- 지금 구조가 정상 사용자 흐름, KNIA/RAG 근거 품질, 영상 관찰값 오염 방지, finality 표시를 유지한다면 무리하게 분리하지 않는다.

## 전환 검토 트리거

| 트리거 | 검토 방향 |
| --- | --- |
| 외부 tool server나 표준 MCP client 연동이 실제 요구가 됨 | `STANDARD_MCP_DECISION.md`의 보류 결정을 재검토하고 pilot 범위를 새로 잡는다. |
| specialist가 장시간 실행되거나 별도 scale 단위가 필요함 | Agent role adapter를 queue/process 단위로 분리할지 검토한다. |
| Gateway/Agent/Worker 간 계약이 복잡해져 장애 격리가 필요함 | DTO, Redis job, DB 저장 경계를 먼저 문서화한 뒤 service split을 검토한다. |
| RAG/KNIA import와 분석 runtime이 서로 영향을 줌 | import/indexing job과 runtime retrieval을 별도 운영 경계로 나눈다. |
| 관리자 진단과 사용자 결과 표시 요구가 충돌함 | public payload와 diagnostics payload를 더 엄격히 분리한다. |

## 전환 시 지켜야 할 원칙

- API route, DTO, DB schema, Redis key, storage path를 바꾸면 `SYSTEM_OVERVIEW.md`를 함께 갱신한다.
- 개발 원칙, 검증 기준, 보안 기준, 책임 경계를 바꾸면 `DEVELOPMENT_PROMPT.md`를 함께 갱신한다.
- 표준 MCP를 도입했다고 표현하려면 실제 Host/Client/Server, transport, permission, audit 경계가 있어야 한다.
- LLM이나 vision 결과는 근거 없는 최종 판단으로 승격하지 않는다.
- secret, 원본 영상, AI-Hub 원천 데이터, 모델 가중치, 대용량 로그는 Git에 포함하지 않는다.

## 관련 문서

- [Agent/MCP Task-Plan-Goal 구조 보강 로드맵](AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md)
- [표준 MCP 도입 결정](STANDARD_MCP_DECISION.md)
- [표준 MCP pilot 설계](STANDARD_MCP_PILOT_DESIGN.md)
- [검증 명령 기준](VERIFICATION_COMMANDS.md)
