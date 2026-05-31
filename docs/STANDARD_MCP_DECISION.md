# 표준 MCP 도입 결정 기록

작성일: 2026-05-31

## 1. 결정

현재 LawCompass는 표준 MCP Host/Client/Server를 도입하지 않는다. Agent 내부 MCP-like tool registry/executor를 계속 유지한다.

이 결정은 “MCP가 필요 없다”가 아니라, 현재 문제를 해결하는 데 표준 MCP runtime을 즉시 추가하는 이득이 운영 복잡도보다 크지 않다는 의미다.

## 2. 근거

| 평가 항목 | 판단 |
| --- | --- |
| 외부 tool/server 수 | 별도 외부 tool server 또는 외부 Agent host와 연결해야 하는 요구가 아직 없다. |
| 다중 host 재사용 | 같은 tool을 다른 host/runtime에서 재사용해야 하는 요구가 아직 없다. |
| 보안 격리 | 현재 tool은 Agent 내부 신뢰 경계 안에서 실행된다. untrusted code나 독립 process 격리 요구가 없다. |
| 권한 모델 | 내부 executor가 `MCPToolSpec`, scope validation, timeout/failure packet, safe trace metadata를 제공한다. |
| 운영 비용 | 표준 MCP server/client/transport를 추가하면 auth, secret, health, logging, network failure, CI, 배포 단위가 늘어난다. |
| 프로젝트 우선순위 | 현재 품질 핵심은 영상 관찰값 오염 방지, 사고축 근거 routing, 조건부 판단, 사용자 표시 finality다. |

## 3. Pilot 결과 해석

P10-2 pilot은 `search_knia_json_rag_tool`을 대상으로 future standard MCP adapter mapping이 가능한지 확인했다.

확인된 점:

- 내부 `MCPToolSpec`으로 tool name, description, input/output schema, scope, timeout, side-effect, trace 안전성을 표현할 수 있다.
- future adapter는 같은 schema를 표준 MCP tool schema로 mapping할 수 있다.
- adapter 실패는 기존 `MCPToolErrorPacket`으로 흡수할 수 있다.
- 내부 executor를 source of truth로 유지할 수 있다.

그러나 이 pilot은 “표준 MCP runtime이 지금 필요하다”는 근거는 아니다. 현재는 adapter compatibility 가능성만 확인됐고, 표준 MCP가 내부 executor 대비 해결하는 구체적 운영 문제는 아직 없다.

## 4. 향후 도입 Trigger

아래 조건 중 하나가 실제 요구로 확정되면 표준 MCP 도입을 다시 검토한다.

- 외부 tool 또는 외부 Agent가 3개 이상으로 늘어난다.
- 다른 host, IDE, runtime이 같은 tool을 재사용해야 한다.
- 표준 MCP client와 연결해야 하는 제품 또는 인프라 요구가 생긴다.
- 내부 executor의 scope 모델로 권한 분리가 부족해진다.
- 보안, 장애 격리, untrusted code 처리 때문에 독립 process 경계가 필요해진다.

## 5. 미래 Migration 순서

도입 trigger가 충족될 경우에도 전체 전환은 하지 않는다. 아래 순서로 작은 read-only tool부터 검증한다.

1. `search_knia_json_rag_tool`
   - read-only이고 사고 근거 품질과 직접 연결된다.
2. `legal_rag_search_tool`
   - 법령/RAG 검색과 연결되지만 evidence source dependency가 더 넓다.
3. `evidence_guard_tool`
   - deterministic guard라 안전하지만 외부 tool protocol 이득은 작다.
4. write side effect tool
   - `import_knia_json_tool`, `invalidate_cache_tool` 같은 write tool은 마지막까지 보류한다.

## 6. 발표/인수인계 표현

사용 가능한 표현:

- “Agent 내부 MCP-like tool registry/executor를 구현했다.”
- “표준 MCP 도입은 판단 gate와 pilot 설계까지 진행했고, 현재는 보류했다.”
- “도구 schema, scope, failure packet, trace metadata는 내부 executor에서 관리한다.”

피해야 할 표현:

- “표준 MCP 구현 완료”
- “MCP 서버/클라이언트 도입 완료”
- “외부 MCP 생태계와 연동 완료”

## 7. 다음 작업

P11에서는 이 결정이 `SYSTEM_OVERVIEW.md`, `docs/STACK_DECISION_REVIEW.md`, 발표/인수인계 설명과 충돌하지 않는지 다시 확인한다.
