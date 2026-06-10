# OSS 후속 구조 전환 메모

상태: future/reference
작성 기준: 2026-05-31
마지막 정리일: 2026-06-10

이 문서는 대회 직전 안정화 범위가 아니라, OSS 과제 제출까지 시간이 남았을 때 검토할 후속 구조 전환 메모다. 현재 동작 중인 서비스와 결과 품질을 깨지 않는 것을 우선 원칙으로 둔다.

## 1. 현재 판단

현재 LawCompass는 완전한 대규모 MSA나 표준 MCP 기반 Multi-Agent 시스템이라기보다, Docker Compose 기반 경량 MSA형 모노레포와 Agent 내부 MCP-like tool registry/executor를 결합한 구조다.

현재 구조는 대회 제출과 발표에는 충분히 설명 가능하지만, OSS 과제에서 구조 완성도를 더 높이려면 다음 세 가지를 후속 과제로 분리해 진행하는 것이 적절하다.

1. MSA 경계 명확화
2. 표준 MCP 도입 여부 재검토 및 단계적 분리
3. Specialist Agent 역할과 페르소나 고도화

## 2. MSA 후속 전환 방향

현재는 `frontend`, `gateway`, `agent`, `worker`, `postgres`, `redis`, `edge`가 컨테이너 단위로 분리되어 있으나, 엄밀한 MSA의 독립 배포와 독립 데이터 소유권까지 완성된 상태는 아니다.

후속 작업에서는 먼저 "서비스를 더 쪼갤지"보다 "현재 분리된 서비스의 책임과 계약을 더 명확히 할지"를 우선 검토한다.

### 우선 보강할 항목

| 항목 | 보강 방향 |
| --- | --- |
| Gateway | 인증, 사용자 API, DB 저장, Agent 호출 조율 책임을 유지하되 route/service/helper 책임 경계를 더 얇게 유지한다. |
| Agent | 사고 판단, 근거 검색, 과실비율, 법률/보험/형사 안내를 Agent 내부 계약으로 분리한다. |
| Worker | 영상 파일 처리, 프레임 추출, YOLO/OpenAI 관찰값 생성, Agent 전달 전 관찰값 정리를 담당한다. |
| 데이터 소유권 | 당장 DB를 서비스별로 쪼개기보다 table 접근 책임과 write owner를 문서화한다. |
| 장애 격리 | Agent/Worker 실패가 사용자 흐름 전체를 막지 않도록 fallback, retry, status payload를 명확히 한다. |

### 바로 하지 않는 것이 나은 항목

- Agent별 독립 컨테이너 분리
- 서비스별 DB 완전 분리
- Kubernetes 전환
- 대규모 service mesh 또는 복잡한 message broker 도입

위 항목은 현재 프로젝트 규모에서는 운영 복잡도가 더 크다.

## 3. MCP 후속 전환 방향

현재는 표준 MCP Host/Client/Server가 아니라 Agent 내부 `app/mcp` tool registry/executor가 사용된다. 이 구조는 현재 프로젝트에는 적절하지만, OSS 과제에서 "MCP 구조"를 명확히 보여주려면 다음 순서가 적합하다.

### 단계적 적용 순서

1. 내부 MCP-like tool registry 문서와 코드 계약을 정리한다.
2. read-only tool부터 표준 MCP adapter 가능성을 검증한다.
3. `search_knia_json_rag_tool` 또는 `legal_rag_search_tool`을 pilot 대상으로 삼는다.
4. 표준 MCP를 붙이더라도 기존 executor를 즉시 제거하지 않고 adapter 계층으로 공존시킨다.
5. write side effect가 있는 tool은 마지막에 검토한다.

### 표준 MCP 도입 Trigger

- 외부 tool server를 3개 이상 붙여야 하는 경우
- 다른 host, IDE, runtime에서 같은 tool을 재사용해야 하는 경우
- 독립 process 격리와 protocol-level permission이 실제 요구사항이 되는 경우
- 현재 내부 executor의 권한 모델이나 trace 모델로 한계가 생기는 경우

## 4. Specialist Agent 페르소나 고도화 방향

현재 Agent 페르소나는 역할명, 책임, 금지 판단, handoff 대상은 정의되어 있으나 실제 전문가처럼 판단하기 위한 세부 기준은 더 보강할 여지가 있다.

### 고도화해야 할 내용

| Agent | 보강할 페르소나 기준 |
| --- | --- |
| 영상 관찰 Agent | 직접 충돌 대상, 배경 객체, 사고 원인, 도로 환경을 분리하는 구체 기준 |
| 사실 중재 Agent | 사용자 입력과 영상 관찰값이 충돌할 때 우선순위와 보류 기준 |
| 교통사고 법률 Agent | 민사/형사/행정 쟁점 분리, 법령/판례 직접성 판단 기준 |
| KNIA 기준 Agent | 사고축 mismatch, reference-only, primary basis 채택 기준 |
| 과실비율 Agent | 기본 과실, 가감 요소, 조건부 분기, 50:50 fallback 제한 기준 |
| 형사책임 Agent | 12대 중과실, 인명피해, 신고의무, 사망사고 리스크 분기 |
| 보험 처리 Agent | 대인/대물, 접수, 분쟁심의, 증빙 보전 흐름 |
| 근거 감사 Agent | unsupported claim 차단, 근거 직접성 점수, finality 제한 기준 |
| 대응 안내 Agent | 사용자가 바로 해야 할 행동과 추가 확인 질문 우선순위 |
| 표현 정책 Agent | 확정/참고/조건부/확인 필요 표현 기준과 과장 방지 |

### 페르소나 작성 원칙

- 역할 설명만 쓰지 말고 입력, 판단권한, 금지 판단, 근거 우선순위, 출력 형식, 예외 상황을 함께 둔다.
- 특정 테스트 영상이나 특정 사고 사례에 맞춘 문구를 넣지 않는다.
- 실제 판결 확정처럼 표현하지 않고 유사 근거 기반의 참고 판단임을 유지한다.
- 영상 관찰값은 확정 fact가 아니라 후보, 확인 필요, 반영 가능 상태를 구분한다.

## 5. 후속 작업 전 점검 질문

OSS 과제 단계에서 이 작업을 다시 시작할 때는 아래 질문을 먼저 확인한다.

1. 현재 목표가 발표 안정화인지, 구조 고도화인지 구분했는가?
2. Agent별 독립 process가 정말 필요한가, 아니면 현재 Agent 내부 계약 강화로 충분한가?
3. 표준 MCP를 붙이면 해결되는 구체적인 문제가 있는가?
4. 현재 사용자 결과 품질을 깨지 않고 전환할 수 있는가?
5. 변경 후 `SYSTEM_OVERVIEW.md`, `DEVELOPMENT_PROMPT.md`, 실행/검증 문서가 함께 업데이트되는가?

## 6. 권장 결론

OSS 과제 후속 개발에서는 완전한 재작성보다 다음 순서를 권장한다.

1. 현재 MSA형 서비스 책임과 데이터 접근 책임을 문서로 고정한다.
2. Specialist Agent 페르소나와 입출력 계약을 먼저 고도화한다.
3. 내부 MCP-like tool registry를 더 명확히 정리한다.
4. 표준 MCP는 read-only tool pilot부터 검토한다.
5. 독립 Agent process 분리는 마지막에 판단한다.

이 순서가 현재 프로젝트의 안정성과 구조 완성도를 동시에 지키는 방향이다.

## 7. 관련 문서

- [Agent/MCP Task-Plan-Goal 구조 보강 로드맵](AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md)
- [표준 MCP 도입 결정](STANDARD_MCP_DECISION.md)
- [표준 MCP pilot 설계](STANDARD_MCP_PILOT_DESIGN.md)
- [검증 명령 기준](VERIFICATION_COMMANDS.md)
