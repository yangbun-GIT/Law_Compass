# Agent 실행 품질 점검 기준

작성일: 2026-05-31

이 문서는 Agent/MCP/Task-Plan-Goal 로드맵의 P12-2 단계에서 사용하는 Agent 실행 품질 점검 기준이다. P12-2는 이전 단계 일부가 아니라 P0~P11 전체 Agent 실행 구조가 의도한 계약을 유지하는지 확인한다.

## 점검 범위

| 점검 영역 | 확인 기준 | 대표 검증 |
| --- | --- | --- |
| 영상/텍스트 fact 정리 | 텍스트만, 영상만, 텍스트+영상, 보완 답변 흐름에서 입력이 오염 없이 fact 후보/확정/충돌/보류 상태로 정리되는지 확인한다. | 전체 Agent 테스트 |
| 사고 대상 오염 방지 | 보행자, 횡단보도, 자전거, 이륜차, 주변 차량이 보인다는 이유만으로 직접 충돌 대상이나 사고 대분류가 바뀌지 않는지 확인한다. | 전체 Agent 테스트 |
| Agent별 독립 결과 | 영상 관찰 Agent, fact arbitration Agent, 법률/KNIA/과실/형사/보험/행동 Agent가 자기 권한 밖 판단을 확정하지 않는지 확인한다. | 전체 Agent 테스트 |
| 충돌/불확실성 반영 | 상대 신호, 중앙선 침범 사유, 정차 사유, 무등화/속도/시야, 비접촉 유발, 2차 충돌처럼 결론이 갈리는 상황을 단일 확정값으로 숨기지 않는지 확인한다. | 전체 Agent 테스트 |
| 근거축 분리 | 사고 대분류와 직접 사고대상에 맞는 근거만 primary로 두고, 환경축 근거는 secondary 또는 excluded로 분리하는지 확인한다. | 전체 Agent 테스트 |
| 소스 컴파일 | Agent app, scripts, tests가 Python syntax 기준으로 깨지지 않는지 확인한다. | `compileall app scripts tests` |

## 실행 명령

Agent 의존성은 로컬 Python보다 Docker 컨테이너 기준이 안정적이다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_agent_execution_quality.ps1 -SkipDockerBuild
```

Docker 컨테이너가 실행 중이 아니거나 이미지 변경까지 함께 확인해야 한다면 `-SkipDockerBuild`를 빼고 실행한다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_agent_execution_quality.ps1
```

## 2026-05-31 P12 전체 범위 재점검 결과

사용자 확인에 따라 P12-2는 선택 테스트 묶음이 아니라 P0~P11 전체 Agent 테스트와 source compile을 실행하도록 재정의했다.

검증 결과:

- Agent 전체 테스트: `340 passed`
- Agent source compile: 통과
- 실패가 발견되면 P12-2 완료로 처리하지 않고 같은 단계의 보정 작업으로 남긴다.

## 완료 기준

- 위 명령이 실패 없이 종료되어야 한다.
- 실패한 테스트가 있으면 P12-2 완료로 처리하지 않고 같은 단계의 보정 작업으로 남긴다.
- 특정 테스트 영상이나 특정 문장에만 맞춘 예외 규칙으로 실패를 우회하지 않는다.
- 제품 코드, API route, DTO, DB schema, Redis key, storage path, 외부 API를 변경하는 작업은 별도 개발 단계로 분리한다.
