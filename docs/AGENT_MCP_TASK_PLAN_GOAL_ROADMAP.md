# Agent/MCP Task-Plan-Goal 구조 보강 로드맵

작성일: 2026-05-31

이 문서는 LawCompass를 원래 목표였던 **MCP 기반 도구 경계**, **Task-Plan-Goal 실행 구조**, **역할별 전문 Agent**, **근거 검증 중심 판단 파이프라인**으로 단계적으로 끌어올리기 위한 작업 기준이다.

현재 프로젝트는 MSA 형태의 서비스 분리는 갖추고 있지만, 표준 MCP 서버/클라이언트와 독립 Agent들이 각자 goal을 제출하는 구조는 아직 완성되어 있지 않다. 현재 구현은 **통제된 전문 분석 파이프라인 + 내부 tool registry + 판단 계약/품질 패킷/영상 입력 계약**에 가깝다.

앞으로 이 구조를 보강하는 작업은 반드시 이 문서를 기준으로 진행한다. 작업 중 새롭게 필요한 작업이 발견되면 해당 내용을 이 문서의 가장 알맞은 단계에 추가하고, 기존 단계의 목적과 충돌하지 않게 순서를 조정한다.

## 1. 작업 원칙

- 이 문서는 Agent/MCP/Task-Plan-Goal 구조 보강 작업의 진행 기준이다.
- 특정 테스트 영상, 특정 문장, 특정 사고 케이스에 맞춘 임시 규칙을 만들지 않는다.
- 모든 판단 구조는 실제 사용자 입력과 미래의 새로운 사고 영상에도 일반화되어야 한다.
- 영상/텍스트/KNIA/법령/판례/보험 판단은 서로 오염되지 않도록 후보, 확인, 확정, 참고 상태를 분리한다.
- LLM은 근거 없는 판단을 확정하지 않는다. 법령, KNIA, 판례, 영상 관찰값, 사용자 입력, 불확실성 상태를 분리해 사용한다.
- 구조 개선, Agent 고도화, 리팩터링은 현재 정상 동작 중인 사용자 흐름과 결과 품질을 깨지 않는 범위에서 진행한다. public API/DTO, 저장 경로, DB/Redis 계약, 관리자/사용자 결과 payload, 기존 회귀 샘플의 판단 품질이 의도 없이 나빠지면 해당 단계는 완료로 보지 않는다.
- 작업을 완료했다고 보고하려면 해당 단계의 검증 항목을 실제로 수행해야 한다.
- 각 단계 또는 하위 작업을 마친 뒤에는 목적 부합성 점검을 반드시 수행한다.
- 목적 부합성 점검에서는 원래 단계 목표, 서비스 책임 경계, Agent/MCP/Task-Plan-Goal 계약, 근거 검증 원칙, 영상/입력 오염 방지 원칙, 사용자 요청 범위와 실제 구현이 맞는지 확인한다.
- 점검 결과 목적과 맞지 않는 구현, 책임 침범, 특정 테스트 케이스에만 맞춘 로직, 불명확한 출력 계약, 검증 부족이 발견되면 완료로 처리하지 않고 해당 단계 안에 수정 작업을 추가한 뒤 재작업한다.
- 수행하지 못한 검증은 완료로 말하지 않고 남은 작업으로 기록한다.
- `.env`, API key, NAS 계정, 사용자 비밀번호, 원본 사고 영상, AI-Hub 원천 데이터, YOLO 모델 가중치, 로그 대용량 산출물은 Git에 올리지 않는다.

## 2. 현재 구조와 목표 구조의 차이

| 영역 | 현재 상태 | 목표 상태 |
| --- | --- | --- |
| MCP | Agent 내부 `app/mcp` tool registry/executor 수준 | 도구 schema, 권한, 실행 로그, 실패 관찰값이 명확한 내부 MCP 계층. 필요 시 표준 MCP Host/Client/Server로 확장 가능 |
| Task-Plan-Goal | `planner.py`는 있으나 실제 orchestration 흐름에서 거의 사용되지 않음 | 입력마다 task plan이 생성되고, 각 task의 goal, 상태, 관찰값, 결과가 trace와 quality packet에 남음 |
| Agent 역할 | specialist/persona 이름과 일부 analyst 모듈은 있으나 독립 결과 계약은 약함 | 법률, KNIA, 과실비율, 형사, 보험, 증거감사, 영상관찰 Agent가 명확한 입력/출력 계약을 가짐 |
| 판단 흐름 | `orchestrator.py` 중심의 고정 stage pipeline | 고정 stage를 유지하되 각 stage가 Task-Plan-Goal packet으로 실행되고 필요 시 제한적 재계획 수행 |
| 영상 처리 | OpenAI/YOLO 관찰값과 후보/확정 guard가 존재 | 사고 기점, 직접 사고대상, 신호, 차선, 정차, 유발 객체, 충돌 순서가 오염 없이 Agent 입력 계약으로 연결 |
| 근거 검증 | judgment contract, evidence guard, KNIA filter가 존재 | 각 주장마다 근거 출처, 직접성, 부족 항목, 조건부 결과, finality가 일관되게 표시 |
| 관측성 | agent_trace, agent_quality_packet 존재 | MCP tool call, task run, specialist result, evidence decision, 영상 관찰값이 하나의 trace id로 추적됨 |

## 3. 단계별 작업 계획

### P0. 기준선 확정과 차이 고정

목적: 현재 구조를 정확히 고정하고, 앞으로 보강할 기준을 흔들리지 않게 만든다.

#### P0-1. 용어와 성공 기준 확정

- `Task`, `Plan`, `Goal`, `Observation`, `Tool Call`, `Agent Result`, `Judgment Contract`, `Quality Packet`, `MCP Tool`, `Specialist Agent`의 의미를 프로젝트 기준으로 정의한다.
- "표준 MCP"와 "내부 MCP-like tool registry"를 명확히 구분한다.
- "독립 Agent"와 "역할 기반 analyzer"를 구분한다.
- 현재 단계에서 표준 MCP 전체 도입이 필요한지, 내부 MCP 계층 강화가 먼저인지 결정 기준을 문서화한다.
- 발표/문서/코드 주석에서 과장된 표현이 생기지 않도록 현재 상태 표현을 정리한다.

P0-1 확정 정의:

| 용어 | LawCompass 기준 의미 | 성공 기준 |
| --- | --- | --- |
| Task | 하나의 사고 분석 흐름 안에서 단일 책임을 갖는 실행 단위. 예: 입력 정규화, 영상 관찰값 정리, KNIA 매칭, 법률 근거 검색, 과실비율 산정 | `task_id`, `task_type`, `goal`, `status`, `input_refs`, `result_ref`, 실패 또는 보류 사유가 trace/quality packet에 남는다 |
| Plan | 하나의 사고 입력을 처리하기 위해 필요한 Task의 순서와 조건을 묶은 실행 계획 | 텍스트만, 영상만, 텍스트+영상, 보완 답변 재분석, 관리자 진단 흐름별 plan이 생성되며 정적 stage 흐름을 깨지 않고 추적 가능해야 한다 |
| Goal | Task 또는 Agent가 달성해야 하는 검증 가능한 결과 조건. 사용자의 최종 희망 결과가 아니라 시스템 내부의 판정 목표다 | 성공, 보류, 차단, 실패가 근거와 함께 구분되고 최종 report에 직접 섞이기 전에 aggregator를 거친다 |
| Observation | tool, 영상 처리, 검색, 입력 정규화, 검증 stage가 만든 관찰값 또는 실패/부족 관찰값 | 확정 사실, 후보, 확인 필요, 참고, 실패를 구분하며 원본 비밀값이나 원본 영상/라벨을 노출하지 않는다 |
| Tool Call | 내부 또는 외부 기능을 제한된 schema, 권한, timeout, trace id로 호출하는 실행 단위 | 호출 입력/출력 요약, 권한 scope, 성공/실패, 실패 관찰값이 기록된다 |
| Agent Result | 전문 Agent 또는 analyzer가 자기 책임 범위 안에서 만든 구조화 결과 | `role_id`, `goal`, `claims`, `evidence_used`, `unsupported_claims`, `uncertainties`, `finality`를 포함한다 |
| Judgment Contract | 최종 판단에 넣어도 되는 주장과 보류해야 하는 주장을 가르는 정책 계약 | 근거 부족, 사고축 불일치, 영상/입력 충돌, KNIA mismatch가 있으면 reference-only 또는 추가 확인 필요로 제한한다 |
| Quality Packet | 분석 신뢰도, 경고, trace, 근거 직접성, 영상 관찰 상태, 도구 실행 상태를 담는 안전한 품질 메타데이터 | 사용자 화면에는 안전 요약만 노출하고 내부 점검에는 trace 가능한 근거를 남긴다 |
| MCP Tool | 현재 코드에서는 `apps/agent/app/mcp`의 내부 MCP-like tool registry/executor에 등록된 도구 | 표준 MCP 서버/클라이언트 구현으로 표현하지 않는다. tool schema, 권한, 실패 packet, 실행 로그가 정리되면 내부 MCP 계층 강화로 본다 |
| Specialist Agent | 법률, KNIA, 과실비율, 형사, 보험, 증거감사, 영상관찰처럼 명확한 역할과 결과 계약을 가진 분석 주체 | 현재는 일부 analyst/persona/analyzer 모듈로 분산되어 있으며, 목표 상태에서는 각 역할이 독립 결과 계약과 handoff 규칙을 가진다 |

표준 MCP와 내부 MCP-like tool registry의 구분:

| 구분 | 현재 LawCompass 적용 여부 | 판단 기준 |
| --- | --- | --- |
| 내부 MCP-like tool registry | 적용 중 | Agent 내부에서 허용된 도구를 registry/executor로 호출하고, 도구 경계와 실패 관찰값을 남기는 구조 |
| 표준 MCP Host/Client/Server | 미적용 | 외부 MCP client 호환, 별도 tool server, transport, protocol-level permission, cross-host tool reuse가 필요한 경우에만 도입 검토 |

독립 Agent와 역할 기반 analyzer의 구분:

| 구분 | 현재 상태 | 목표 또는 보류 기준 |
| --- | --- | --- |
| 역할 기반 analyzer | 현재 구현의 중심 | `orchestrator.py` stage 안에서 analyst module, persona, guard가 실행된다. 독립 lifecycle이나 별도 goal 제출 구조는 약하다 |
| Specialist Agent | 목표 구조 | 각 역할이 입력 계약, evidence 계약, 판단 권한, 금지 판단, 결과 계약, handoff 대상을 가진다 |
| 완전 독립 Agent process | 현재 보류 | 별도 프로세스/큐/자율 재계획은 운영 복잡도가 크므로 Task-Plan-Goal 계약이 안정된 뒤 필요할 때만 검토한다 |

표준 MCP 도입 판단 기준:

| 내부 MCP 강화 우선 조건 | 표준 MCP 도입 검토 조건 |
| --- | --- |
| 도구가 Agent 내부 서비스와 같은 배포 단위에서 동작한다 | 외부 도구 서버 또는 표준 MCP client와 연결해야 한다 |
| 도구 수가 적고 allowlist/권한을 코드 레벨에서 통제할 수 있다 | 도구 수와 소유자가 늘어나 protocol-level 권한, 격리, audit가 필요하다 |
| 현재 문제의 핵심이 판단 오염, 근거 검증, 영상 관찰 품질이다 | cross-host reuse, 외부 connector, 독립 tool lifecycle이 제품 요구가 된다 |
| 2인 팀과 마감 일정상 운영 복잡도를 줄이는 것이 더 중요하다 | 표준 도입 이득이 설정, 보안, 테스트, 운영 비용보다 명확하게 크다 |

P0-1 문서 점검 결과:

- `DEVELOPMENT_PROMPT.md`는 현재 구조를 표준 MCP가 아닌 Agent 내부 MCP-like tool registry/executor로 표현한다.
- `SYSTEM_OVERVIEW.md`는 `apps/agent/app/mcp/*`를 내부 tool registry/executor로 기록하고, 표준 MCP는 후속 안정화/확장 항목으로 둔다.
- `docs/STACK_DECISION_REVIEW.md`는 현재 구현이 외부 표준 MCP 서버/클라이언트 전체 구현이 아니라고 명시한다.
- 검색 결과 기준으로 "표준 MCP 구현 완료"처럼 현재 구현을 과장하는 문구는 확인되지 않았다.

검증:

- `DEVELOPMENT_PROMPT.md`, `SYSTEM_OVERVIEW.md`, `docs/STACK_DECISION_REVIEW.md`의 MCP/Agent 표현이 서로 충돌하지 않는지 확인한다.
- 표준 MCP가 구현되지 않았는데 구현된 것처럼 표현된 문구가 없는지 검색한다.

#### P0-2. 현재 구현 inventory 작성

- Agent 진입점, Gateway 호출 경로, Worker 영상 처리 경로, MCP tool registry, specialist/persona 파일, evidence/KNIA/fault 판단 모듈을 목록화한다.
- 각 파일이 맡는 책임과 실제 호출 관계를 확인한다.
- `planner.py`가 실제로 어디서 사용되는지 확인한다.
- `execute_tool`을 타는 도구와 직접 service를 호출하는 경로를 분리한다.
- specialist가 실제 분석 결과를 만드는지, 추천 이름만 전달되는지 구분한다.

검증:

- `rg`로 `build_task_plan`, `execute_tool`, `register_tool`, `recommended_specialists`, `agent_quality_packet`, `agent_trace` 사용 위치를 확인한다.
- inventory 결과를 이 문서 또는 `SYSTEM_OVERVIEW.md`에 반영한다.

P0-2 inventory 결과 (2026-05-31):

#### Agent 진입점과 본선 분석 흐름

| 구간 | 파일 | 현재 책임 | 실제 호출 관계 |
| --- | --- | --- | --- |
| Agent app bootstrap | `apps/agent/app/main.py` | FastAPI app 생성, `/internal/v1` router 연결, startup 시 KNIA bootstrap 시도 | `app.include_router(internal_router)`로 내부 API만 연결 |
| Internal router | `apps/agent/app/routers/internal.py` | health, analysis, jobs, legal, chat, KNIA, cache, mobile demo route를 `/internal/v1` 아래 묶음 | 각 `internal_routes/*` router를 include |
| Analysis endpoints | `apps/agent/app/routers/internal_routes/analysis.py` | `/analyze/text`, `/analyze/video`, `/analyze/scenario` 진입점 | `analyze_case`, `analyze_video_case`, `analyze_scenario`를 직접 호출 |
| Orchestrator | `apps/agent/app/services/orchestrator.py` | 사고 분석 본선 stage 조립 | `build_case_context` -> `collect_evidence_stage` -> `run_analysis_stage` -> `run_reflection_requery_stage` -> `build_judgment_contract` -> `compose_analysis_output` -> `enrich_analysis_output` |
| Context stage | `apps/agent/app/services/orchestration_context.py` | 영상 context 요약, 입력 정규화, 사고유형 분류, 입력 요구사항/질문 생성 | `normalize_analysis_input`, `classify_scenario`, `build_input_requirements`, `build_dynamic_questionnaire` 직접 호출 |
| Evidence stage | `apps/agent/app/services/orchestration_evidence.py` | KNIA match, KNIA JSON RAG, 법률 RAG, KNIA 과실 추정, 근거 필터 | `match_knia_charts`, `search_knia_json_cached`, `retrieve_for_scenario`, `estimate_knia_fault` 직접 호출. 현재 MCP executor를 타지 않음 |
| Analysis stage | `apps/agent/app/services/orchestration_analysis.py` | 법규, 과실비율, 형사, 보험, 행동, 근거감사, claim-evidence 검증 실행 | `services/analysts/*`, KNIA adjustment registry, claim validator를 직접 호출 |
| Output enrichment | `apps/agent/app/services/orchestration_output.py` | judgment contract 적용, reflection, questionnaire, expert guidance, trace, quality packet, 쉬운 리포트 부착 | `build_agent_execution_trace`, `build_agent_quality_packet`, `build_elderly_friendly_report` 호출 |

현재 결론:

- Agent 본선은 Task-Plan-Goal runtime이 아니라 고정 stage pipeline이다.
- `planner.py`의 `build_task_plan()`은 현재 production 분석 흐름에서 호출되지 않는다.
- trace와 quality packet은 존재하지만, task 단위 실행 상태가 아니라 stage 요약 metadata에 가깝다.

#### Gateway 호출 경로

| 구간 | 파일 | 현재 책임 | 실제 호출 관계 |
| --- | --- | --- | --- |
| Text analysis | `apps/gateway/src/routes/analysis.ts` | `POST /api/v1/cases/:caseId/analyze-text` 처리 | `callInternalAgent("/internal/v1/analyze/text")` 후 `insertAnalysisResult`로 DB 저장 |
| Video analysis job enqueue | `apps/gateway/src/routes/analysis.ts` | `POST /api/v1/cases/:caseId/analyze-video` 처리 | 기존 결과/활성 job 확인 후 `jobs(type='video_analyze')` insert, Redis stream `xadd` |
| Reanalysis | `apps/gateway/src/routes/analysis.ts` | `POST /api/v1/cases/:caseId/reanalyze` 처리 | follow-up 답변과 최신 upload metadata를 합쳐 `/internal/v1/analyze/text` 재호출 |
| Upload route | `apps/gateway/src/routes/uploads.ts` | local upload, complete, upload 조회/download/view-url | `completeLocalUpload`로 업로드 검증 및 preprocess enqueue |
| Upload service | `apps/gateway/src/services/uploadService.ts` | storage reference 정규화, upload DB insert, video_preprocess job enqueue | `enqueueVideoPreprocessJob`가 `jobs(type='video_preprocess')` insert 후 Redis stream `xadd` |
| Analysis service | `apps/gateway/src/services/analysisService.ts` | progress payload, report context, analysis_result insert | Agent result를 `analysis_results`에 저장하고 `persona_outputs`에는 `recommended_specialists`만 저장 |
| Admin diagnostics | `apps/gateway/src/routes/agent-diagnostics.ts` | Agent trace/video preprocess 진단 조회 | DB에 저장된 metadata/result를 관리자 화면용으로 재구성 |

현재 결론:

- Gateway는 Agent 호출과 DB 저장을 담당하며, Task/Plan/Goal 단위 orchestration을 만들지는 않는다.
- 영상 분석은 Gateway가 직접 Agent를 호출하지 않고 Worker job으로 넘기는 경로가 중심이다.

#### Worker 영상 처리 경로

| 구간 | 파일 | 현재 책임 | 실제 호출 관계 |
| --- | --- | --- | --- |
| Redis consumer | `apps/worker/worker/main.py` | Redis Streams group consumer, stale pending reclaim, job ack/fail status cache | `process_job(job_id, job_type, redis_client)` 호출 |
| Job dispatcher | `apps/worker/worker/job_processor.py` | `video_preprocess`, `video_analyze` 분기 | DB job row 조회 후 `_process_video_preprocess` 또는 `_process_video_analyze` 실행 |
| Preprocess | `apps/worker/worker/job_processor.py` | storage materialize, ffprobe, frame extraction, YOLO, OpenAI frame analysis, observation merge, frame persistence | `probe_video`, `extract_event_frames`, `analyze_frames_with_yolo`, `analyze_frames_with_openai`, `_merge_frame_observations` |
| Frame extraction | `apps/worker/worker/video_preprocess.py` | ffprobe metadata, 대표/event frame 추출, dense fallback | `extract_event_frames`가 processed frame 후보 생성 |
| OpenAI frame analysis | `apps/worker/worker/frame_analysis.py` | 선택 frame 기반 OpenAI vision observation 생성 | `select_openai_frames`와 usage 기록을 사용 |
| YOLO frame analysis | `apps/worker/worker/yolo_frame_analysis.py` | 차량/사람/자전거/이륜차 객체 후보, event window, small target crop hint 생성 | 사고 판단 모델이 아니라 frame ranking 및 객체 후보 보조 |
| Video analyze | `apps/worker/worker/job_processor.py` | preprocess metadata와 case 입력을 Agent video request로 조립 | `POST {INTERNAL_AGENT_URL}/internal/v1/analyze/video`, 응답을 `analysis_results`에 저장 |

현재 결론:

- Worker는 영상 사실 후보를 생성하지만 최종 사고 판단은 Agent로 넘긴다.
- YOLO/OpenAI 관찰값은 candidate/확인/확정 상태를 유지해야 하며, 현재도 직접 과실 판단 모델로 쓰지 않는다.

#### MCP tool registry와 실제 사용 위치

| 항목 | 파일 | 현재 상태 |
| --- | --- | --- |
| Registry | `apps/agent/app/mcp/tool_registry.py` | `register_tool`, `get_tool`, `list_tools`, `bootstrap_tools`만 가진 단순 registry |
| Executor | `apps/agent/app/mcp/tool_executor.py` | tool 호출 전 bootstrap, 호출 결과 또는 실패를 `mcp_tool_calls`에 best-effort 기록 |
| 등록 tool | `apps/agent/app/mcp/tools/*.py` | `legal_rag_search_tool`, `import_knia_json_tool`, `get_knia_myaccident_pages_tool`, `get_knia_menu_tree_tool`, `search_knia_json_rag_tool`, `get_knia_media_by_query_tool`, `evidence_guard_tool`, `invalidate_cache_tool` |
| Production executor caller | `apps/agent/app/routers/internal_routes/knia.py` | 현재 production route 중 확인된 `execute_tool` 사용은 `/knia/media/search`의 `get_knia_media_by_query_tool` |
| Script caller | `apps/agent/scripts/test_mcp_knia_json_tools.py` | MCP tool 동작 확인용 스크립트 |

현재 결론:

- 분석 본선의 법률 RAG, KNIA match, KNIA fault estimate, evidence guard는 대부분 직접 service 호출이다.
- 내부 MCP-like registry는 존재하지만 아직 본선 Agent tool boundary로 일관되게 쓰이지 않는다.
- P3에서 tool schema, 권한 scope, 실패 packet, 본선 호출 경계 정리가 필요하다.

#### Specialist/persona/party analyzer inventory

| 구분 | 파일 | 현재 역할 | 독립 Agent 여부 |
| --- | --- | --- | --- |
| Specialist 추천 목록 | `apps/agent/app/services/specialists.py` | profile별 role id 추천과 display metadata 제공 | 독립 실행하지 않음. `recommended_specialists`로 output/DB에 남는 추천 목록 |
| Persona specs | `apps/agent/app/personas/traffic_law_personas.py` | persona id, role, focus, output field, prompt 정의 | 본선에서 독립 agent로 실행되는 구조는 약함 |
| Scenario persona hints | `apps/agent/app/personas/accident_scenario_personas.py` | scenario_type별 persona/profile hint 추가 | 추천/표시 성격 |
| Party agents | `apps/agent/app/services/party_agents/*` | 차대차/차대사람/자전거/이륜차/기물/단독 대분류와 직접 사고대상 guard | deterministic analyzer로 실제 입력 정규화에 사용됨. Specialist Agent 결과 계약은 아님 |
| Analyst modules | `apps/agent/app/services/analysts/*` | traffic law, fault ratio, criminal liability, insurance, action plan, evidence audit 결과 생성 | 실제 결과 생성 모듈이지만 공통 Specialist Agent result schema는 아직 없음 |
| KNIA adjustment agent | `apps/agent/app/services/knia/knia_adjustment_agent.py` | KNIA 가감요소 적용/미적용을 deterministic packet으로 부착 | 이름은 agent지만 독립 process가 아니라 service function |

현재 결론:

- “전문가 Agent”라는 사용자 목표에 가장 가까운 실제 결과 생산자는 `services/analysts/*`와 `knia_adjustment_agent.py`다.
- `specialists.py`와 persona 파일은 현재 추천/프롬프트 metadata 성격이 강하다.
- P1/P4에서 Specialist Agent 결과 계약과 persona/role profile 계약을 실제 analyst output에 연결해야 한다.

#### Evidence/KNIA/fault 판단 모듈 inventory

| 영역 | 주요 파일 | 현재 책임 |
| --- | --- | --- |
| 입력 정규화/영상 계약 | `input_normalizer.py`, `video_input_contract*.py`, `fact_arbitration.py` | 사용자 입력과 영상 관찰값을 fact 후보/확정/충돌로 정리 |
| 사고유형 분류 | `scenario_classifier.py`, `scenario_search_terms.py`, `party_agents/*` | scenario_type, accident_party_type, 검색어 축 결정 |
| 법률/RAG | `rag_client.py`, `services/legal/*`, `services/rag/*` | 법률/KNIA JSON retrieval, cache, rerank/gate |
| KNIA | `services/knia/*`, `services/knia/adjustments/*` | KNIA 수집, 저장, 매칭, 과실 계산, 가감요소 적용, party guard |
| 과실/법률/보험 | `services/analysts/fault_ratio_analyst.py`, `traffic_law_analyst.py`, `criminal_liability_analyst.py`, `insurance_analyst.py`, `action_plan_analyst.py` | 근거 기반 결과 생성. LLM 사용 가능 시 guarded LLM 결과를 쓰고 아니면 deterministic fallback |
| 검증/표시 정책 | `claim_evidence_validator.py`, `judgment_contract.py`, `evidence_quality_gate.py`, `expert_guidance_sections.py`, `elderly_friendly/*` | 주장-근거 연결, finality, 사용자 표시 안전화 |

P0-2 검증 결과:

- `build_task_plan`: `apps/agent/app/services/planner.py`에만 정의되어 있고 production caller는 확인되지 않았다.
- `execute_tool`: production에서는 `apps/agent/app/routers/internal_routes/knia.py`의 `/knia/media/search`에서만 확인되며, 분석 본선은 직접 service 호출이다.
- `register_tool`: `apps/agent/app/mcp/tools/*`에서 8개 tool을 등록한다.
- `recommended_specialists`: `orchestrator.py`에서 profile/hint 기반으로 생성되고 Gateway/Worker 저장값의 `persona_outputs.analysts`로 남는다. 독립 실행 결과는 아니다.
- `agent_trace`/`agent_quality_packet`: `orchestration_output.py`에서 최종 output에 부착되고 schema, tests, Gateway report/diagnostics에서 소비된다.

P0-2에서 확정한 차이:

- 현재 구현은 "전문 Agent들이 각자 goal을 제출"하는 구조가 아니라, deterministic/guarded analyzer들을 고정 stage에서 호출하는 구조다.
- 현재 MCP는 "분석 본선 tool boundary"가 아니라 일부 route/script 중심의 내부 registry다.
- 다음 P1/P2/P3/P4 작업은 이 inventory를 기준으로 실제 task packet, tool boundary, Specialist Agent result schema를 추가해야 한다.

#### P0-3. 회귀 기준선 고정

- 현재 통과해야 하는 Agent/Worker/Gateway/Frontend 테스트 명령을 정리한다.
- 사고 1~5, synthetic fixture, AI-Hub label reference, 공개 reference manifest를 어떤 용도로 쓰는지 분리한다.
- 영상 원본과 라벨이 추론 입력으로 섞이지 않는지 검증 기준을 다시 확인한다.
- 현재 실패하거나 flaky한 테스트가 있다면 "현 상태 known risk"로 기록한다.

검증:

- Python unit/regression, Gateway build/test, Frontend build, Worker frame analysis contract 중 해당 작업 범위에 필요한 최소 검증을 실행한다.
- 실행하지 못한 항목은 이유와 다음 작업을 기록한다.

P0-3 기준선 (2026-05-31):

| 구분 | 기준 명령/자료 | 용도 |
| --- | --- | --- |
| 작업 시작 상태 | `git fetch origin`, `git status --short --branch`, `git log --oneline --decorate -8` | 최신 `main`과 팀원 병합 여부 확인 |
| 핵심 회귀 | `powershell -ExecutionPolicy Bypass -File scripts/verify_core.ps1 -SkipDockerBuild` | Gateway test/build, Frontend build/display/chat, reference hardening fixture, 선택적 Docker/Agent 회귀 |
| Agent 회귀 | `powershell -ExecutionPolicy Bypass -File scripts/verify_agent_regression.ps1 -SkipDockerBuild` | Agent compile, 내부 route contract, 대표 사고 회귀, 근거 검색 품질, 품질 packet |
| 최종 readiness | `powershell -ExecutionPolicy Bypass -File scripts/verify_final_readiness.ps1 -SkipDockerBuild` | 발표/인수인계 전 최소 end-to-end readiness |
| Gateway 단독 | `cd apps/gateway; npm test; npm run build` | route, report composer, upload/storage contract, TypeScript build |
| Frontend 단독 | `cd apps/frontend; npm run build; npm run test:display; npm run test:chat` | Vue build, 사용자 표시 안전성, chat 표시 안전성 |
| Agent 단독 | `cd apps/agent; $env:PYTHONPATH='.'; python -m pytest tests` | Agent service, KNIA, evidence, judgment contract, video input contract 단위 회귀 |
| Worker 단독 | `cd apps/worker; $env:PYTHONPATH='.'; python -m pytest tests` | frame extraction, OpenAI/YOLO observation contract, storage adapter |
| Reference hardening | `python scripts/verify_reference_hardening_fixture.py` | 실제 영상 없이 synthetic fixture로 보완 재분석, evidence alignment, calibration gate 확인 |
| Reference manifest | `python scripts/validate_reference_case_manifest.py --manifest tests/fixtures/video_accuracy/reference_case_manifest.example.json` | 공개/수동 reference case manifest 구조 확인 |
| Video accuracy manifest | `python scripts/validate_video_accuracy_manifest.py --manifest config/video_accuracy_samples.example.json --allow-missing-files` | 로컬 원본 영상 없이 manifest shape와 필수 metadata 확인 |
| Video reference metrics | `python scripts/evaluate_video_reference_metrics.py --reference-manifest <reference_manifest> --batch-aggregate <batch_aggregate>` | OpenAI+YOLO 실제/샘플 batch 결과와 reference 기대축 비교 |

테스트 자산 분리:

| 자산 | 위치 | 사용 목적 | 추론 입력 혼입 금지 기준 |
| --- | --- | --- | --- |
| 사고 영상 1~5 | 로컬 사용자 제공 경로 또는 `sample_data`/로컬 테스트 폴더 | 관리자/Worker/Agent E2E 회귀 및 시연 확인 | 영상 자체와 변호사 의견은 Git에 올리지 않고, 특정 영상에 맞춘 규칙을 코드에 넣지 않는다 |
| Synthetic fixture | `tests/fixtures/video_accuracy/reference_hardening_minimal/*` | 비용 없이 충돌/보완 재분석/evidence alignment 재현 | fixture 기대값은 회귀 기준이며 production 판단 shortcut으로 쓰지 않는다 |
| AI-Hub label reference | `datasets/aihub597/labels` 또는 정리 manifest | 사고유형/대상/도로환경 label과 관찰값 비교 | 라벨은 검증/평가용이다. 분석 요청 payload나 Agent 입력 fact로 직접 주입하지 않는다 |
| AI-Hub 원천 영상 | 로컬 비공개 데이터 폴더 | 필요 시 다양한 영상 유형의 관찰값 회귀 측정 | 원천 영상은 Git, 로그, 문서 원문에 포함하지 않는다 |
| 공개 reference manifest | `tests/fixtures/video_accuracy/reference_case_manifest.example.json`, `config/video_accuracy_samples.example.json` | 외부/공개 reference의 구조와 출처 metadata 점검 | 링크/요약/평가축만 보존하고 원본 영상 복제나 설명란 원문 편입을 기본 경로로 삼지 않는다 |
| Logs | `logs/video_accuracy/*`, `logs/operating_risk_summary.json` | 실행 결과 추적 | Git에 올리지 않는다. 필요한 내용은 요약만 문서화한다 |

P0-3 실행 기록:

- 2026-05-31에 최신 `main` 확인 후 문서 작업을 진행했다. 로컬 `main`은 `origin/main`과 동일했고, 기존 문서 변경이 작업 중 상태로 남아 있었다.
- `python scripts/verify_reference_hardening_fixture.py` 실행 결과 `reference_hardening_fixture=passed`를 확인했다.
- `python scripts/validate_reference_case_manifest.py --manifest tests\fixtures\video_accuracy\reference_case_manifest.example.json --output logs\video_accuracy\reference_case_manifest_validation_p0_20260531.json` 실행 결과 `status=passed`, `case_count=3`을 확인했다.
- `python scripts/validate_video_accuracy_manifest.py --manifest config\video_accuracy_samples.example.json --allow-missing-files --output logs\video_accuracy\video_accuracy_manifest_validation_p0_20260531.json` 실행 결과 `status=passed`, `sample_count=1`을 확인했다.
- 이번 P0-3은 기준선 문서화 작업이므로 Gateway/Frontend/Docker 전체 빌드는 실행하지 않았다. P1에서 코드 계약을 변경하는 순간 `verify_core.ps1` 또는 해당 서비스 단독 검증을 실행해야 한다.

Known risk:

- 과거 `SYSTEM_OVERVIEW.md` 기록상 일부 broader orchestrator 회귀에서 기존 분류/과실 범위 테스트 2건이 별도 이슈로 분리된 적이 있다. P1에서 Agent contract를 변경하기 전 관련 테스트 실패가 현재도 남아 있는지 먼저 확인한다.
- OpenAI+YOLO 실제 영상 batch는 API 비용, timeout, 로컬 영상 존재 여부에 영향을 받는다. 비용이 드는 batch는 작은 샘플로 제한하고, batch aggregate는 reference metrics로 평가한다.

#### P0-4. 작업 진행 문서 연결

- Agent/MCP/Task-Plan-Goal 구조 작업을 시작할 때 이 문서를 먼저 확인하도록 `DEVELOPMENT_PROMPT.md`와 `AGENTS.md`에 연결한다.
- 새 작업이 생기면 어느 단계에 추가할지 결정하는 규칙을 명시한다.
- 작업 완료 후 해당 단계의 상태를 갱신하는 방식을 정한다.

검증:

- 새 문서가 작업 시작 규칙에서 참조되는지 확인한다.

P0-4 연결 결과 (2026-05-31):

- `AGENTS.md`는 Agent architecture, MCP/tool execution, Task-Plan-Goal flow, specialist personas, evidence routing, video observations, judgment contracts를 다루는 작업에서 이 문서를 4번째 선행 문서로 읽도록 연결했다.
- `DEVELOPMENT_PROMPT.md`는 Agent/MCP/Task-Plan-Goal 구조 보강 작업에서 이 문서를 우선 확인하고, 새 선행 작업이 생기면 이 문서의 올바른 단계에 추가하도록 연결했다.
- `SYSTEM_OVERVIEW.md`는 이 문서를 Agent/MCP/Task-Plan-Goal restructuring roadmap으로 문서 inventory에 기록했다.
- 단계 완료 후에는 이 문서의 `진행 상태 기록`과 `바로 다음 작업`을 갱신한다.
- 구조 개선 중 기존 동작 또는 결과 품질이 악화되면 새 기능으로 넘어가지 않고 해당 P단계의 보정 작업으로 먼저 처리한다.

### P1. 핵심 계약 설계

목적: Task-Plan-Goal과 전문 Agent 결과를 코드에 넣기 전에 공통 데이터 계약을 먼저 확정한다.

#### P1-1. Agent 실행 packet 계약 정의

- `AgentTask` 계약을 정의한다.
  - `task_id`
  - `task_type`
  - `goal`
  - `input_refs`
  - `required_tools`
  - `required_evidence`
  - `status`
  - `blocking_reasons`
  - `result_ref`
- `AgentPlan` 계약을 정의한다.
  - `plan_id`
  - `case_id`
  - `trace_id`
  - `tasks`
  - `execution_order`
  - `replan_policy`
  - `created_by`
- `AgentGoalResult` 계약을 정의한다.
  - `goal`
  - `status`
  - `claims`
  - `evidence_refs`
  - `confidence`
  - `uncertainties`
  - `next_required_inputs`
- Python Pydantic schema 또는 TypedDict 중 현재 코드와 맞는 방식을 선택한다.
- Gateway/Frontend에 노출할 안전 필드와 내부 전용 필드를 분리한다.

검증:

- schema 단위 테스트를 추가한다.
- raw user text, secret, prompt 원문이 public payload로 나가지 않는지 확인한다.

#### P1-2. Specialist Agent 결과 계약 정의

- 교통사고 전문 변호사형 분석 Agent 결과 계약을 정의한다.
- KNIA 기준 Agent 결과 계약을 정의한다.
- 과실비율 Agent 결과 계약을 정의한다.
- 형사책임 Agent 결과 계약을 정의한다.
- 보험처리 Agent 결과 계약을 정의한다.
- 증거감사 Agent 결과 계약을 정의한다.
- 영상관찰 Agent 결과 계약을 정의한다.
- 각 Agent 결과는 다음을 공통으로 포함한다.
  - `role_id`
  - `goal`
  - `input_facts_used`
  - `evidence_used`
  - `claims`
  - `unsupported_claims`
  - `uncertainties`
  - `recommended_next_action`
  - `finality`
- 각 Agent의 persona/role profile 계약을 함께 정의한다.
  - `role_id`
  - `role_name`
  - `professional_identity`
  - `primary_responsibility`
  - `decision_authority`
  - `must_not_decide`
  - `required_evidence_types`
  - `allowed_tools`
  - `handoff_targets`
  - `output_tone`
  - `safety_constraints`
- persona는 단순 말투 설정이 아니라 해당 Agent가 무엇을 판단할 수 있고 무엇을 판단하면 안 되는지를 제한하는 실행 계약으로 다룬다.

검증:

- 각 Agent 결과가 빈 문자열 summary만 반환하지 않고 구조화된 claim/evidence를 포함하는지 테스트한다.
- 각 persona/role profile이 결과 계약과 충돌하지 않는지 확인한다.
- Agent가 자기 책임 밖 결론을 반환하려 할 때 schema 또는 validator가 막는지 확인한다.

#### P1-3. MCP Tool 계약 정의

- 모든 내부 tool의 입력 schema와 출력 schema를 정의한다.
- tool별 권한 scope를 정의한다.
  - `knia.read`
  - `legal.read`
  - `evidence.audit`
  - `cache.write`
  - `storage.read`
  - `video.observe`
- tool 실패 시 반환할 공통 error packet을 정의한다.
- tool 실행 결과가 `mcp_tool_calls` 또는 trace에 남는 방식을 정한다.
- 표준 MCP로 확장할 때 필요한 필드와 현재 내부 executor에만 필요한 필드를 분리한다.

검증:

- 등록된 tool 목록과 schema 목록이 일치하는지 테스트한다.
- 없는 tool 호출, 잘못된 payload, 권한 없는 tool 호출 실패 테스트를 추가한다.

P1 통합 계약 정의 결과 (2026-05-31):

| 구분 | 구현 파일 | 내용 |
| --- | --- | --- |
| Agent 실행 packet | `apps/agent/app/services/agent_contracts.py` | `AgentInputRef`, `EvidenceRequirement`, `AgentClaim`, `AgentTask`, `AgentPlan`, `AgentGoalResult` Pydantic 계약을 추가했다. 기존 orchestration caller는 변경하지 않고 additive schema로만 추가했다. |
| Specialist Agent/persona | `apps/agent/app/services/agent_contracts.py` | `SpecialistRoleProfile`, `SpecialistAgentResult`, `validate_specialist_result_against_profile`을 추가했다. persona는 말투가 아니라 판단 권한, 금지 판단, 필요 근거, handoff 제약으로 다루도록 고정했다. |
| MCP Tool 계약 | `apps/agent/app/services/agent_contracts.py` | `MCPToolSpec`, `MCPToolErrorPacket`, `P1_INTERNAL_TOOL_SPECS`, `build_tool_error_packet`을 추가했다. 현재 내부 registry에 등록되는 8개 tool의 계약 metadata를 P1 기준으로 고정했다. |
| 검증 | `apps/agent/tests/test_agent_contracts.py` | packet ordering, public raw text/secret 차단, specialist structured result 강제, role/profile mismatch 차단, 등록 tool과 spec 목록 일치, tool error packet 계약을 검증한다. |

P1 제한 사항:

- P1은 계약 정의 단계이므로 `orchestrator.py`, `planner.py`, `tool_executor.py`의 production 실행 흐름은 변경하지 않았다.
- P2에서 실제 연결할 때도 기존 `agent_trace`, `agent_quality_packet`, `judgment_contract`, `video_input_contract`와 호환되는 additive 방식으로 시작한다.
- P3 전까지 MCP tool 실행 강제 권한 검사는 metadata와 테스트 기준으로만 존재한다. 실제 executor 권한 enforcement는 P3 작업이다.

P1 검증 결과:

- Agent 컨테이너에 테스트 실행용 `pytest==9.0.3`을 설치한 뒤 `docker compose exec -T agent python -m pytest tests/test_agent_contracts.py`를 실행했고 5건 모두 통과했다.
- 기존 trace/judgment/video input 계약 비회귀 확인을 위해 `docker compose exec -T agent python -m pytest tests/test_orchestrator.py tests/test_judgment_contract.py tests/test_video_input_contract.py`를 실행했고 50건 모두 통과했다.
- 로컬 Python 3.14에서는 `psycopg-binary==3.2.6` wheel 미지원으로 Agent requirements 전체 설치가 막혔다. Agent 검증은 Docker 컨테이너 기준으로 수행한다.

### P2. Task-Plan-Goal 런타임 연결

목적: 현재 고정 orchestration을 유지하되, 실제 실행 단위가 plan/task/goal로 기록되도록 만든다.

#### P2-1. `planner.py` 실사용 전환

- `build_task_plan`을 현재 accident analysis 입력 구조와 연결한다.
- 입력 모드별 plan을 생성한다.
  - 텍스트만
  - 영상만
  - 텍스트+영상
  - 보완 답변 재분석
  - 관리자 진단
- plan은 현재 stage 순서를 무너뜨리지 않고 stage 앞에 붙는 실행 계약으로 시작한다.
- plan 생성 결과를 `agent_trace`와 `agent_quality_packet`에 포함한다.

검증:

- 기존 결과 payload가 깨지지 않는지 확인한다.
- plan이 생성되지 않으면 분석이 조용히 계속되지 않고 safe observation을 남기는지 확인한다.

P2-1 실행 계획 연결 결과 (2026-05-31):

| 구분 | 구현 파일 | 내용 |
| --- | --- | --- |
| 실행 계획 생성 | `apps/agent/app/services/planner.py` | `build_task_plan`이 텍스트만, 영상만, 텍스트+영상, 보완 답변 재분석, 관리자 진단 입력 모드별 `AgentPlan`을 생성한다. 계획에는 raw user text를 넣지 않고 입력 존재 여부, fact 수, 영상 frame/observation 수 같은 안전 metadata만 남긴다. |
| Orchestrator 연결 | `apps/agent/app/services/orchestrator.py`, `apps/agent/app/routers/internal_routes/analysis.py` | 기존 stage 순서를 바꾸지 않고 분석 시작 시 `agent_plan`을 생성해 최종 output에 additive하게 연결한다. 내부 route는 `case_id`, `upload_id`를 plan 식별자에 넘긴다. |
| Trace/Quality packet | `apps/agent/app/services/agent_execution_trace.py`, `apps/agent/app/services/agent_quality_packet.py`, `apps/agent/app/schemas.py` | `agent_trace.task_plan`에 plan 요약을 포함하고, `agent_quality_packet`의 required packet에 `agent_plan`을 추가했다. `AnalysisOutput`에도 `agent_plan` 필드를 추가했다. |
| 실패 안전성 | `apps/agent/app/services/planner.py` | plan 생성 실패 시 분석 전체를 중단하지 않고 `safe_fallback` plan과 `agent_plan_creation_failed` observation을 남긴다. |
| 검증 | `apps/agent/tests/test_planner.py`, `apps/agent/tests/test_orchestrator.py` | Docker Agent 컨테이너에서 `python -m pytest tests/test_planner.py tests/test_agent_contracts.py tests/test_orchestrator.py tests/test_judgment_contract.py tests/test_video_input_contract.py`를 실행했고 60건이 모두 통과했다. |

P2-1 제한 사항:

- 아직 각 stage의 실제 실행 상태를 task packet으로 업데이트하지 않는다. 이 작업은 P2-2에서 진행한다.
- public UI에 task raw payload를 직접 노출하지 않는 정책은 유지한다. `agent_plan`은 API payload에 포함되지만 raw user text, prompt, secret, token을 포함하지 않는다.

#### P2-2. Stage별 task packet 연결

- input normalization stage를 task로 감싼다.
- video input contract stage를 task로 감싼다.
- fact arbitration stage를 task로 감싼다.
- scenario classification stage를 task로 감싼다.
- evidence retrieval stage를 task로 감싼다.
- KNIA matching stage를 task로 감싼다.
- fault ratio stage를 task로 감싼다.
- criminal/insurance/action guidance stage를 task로 감싼다.
- presentation policy stage를 task로 감싼다.
- 각 task는 `pending`, `running`, `succeeded`, `needs_review`, `blocked`, `failed` 중 하나의 상태를 남긴다.

검증:

- trace에 task 개수, 실패 task, blocked task가 표시되는지 확인한다.
- public UI에는 내부 task raw payload가 노출되지 않는지 확인한다.

P2-2 stage task packet 연결 결과 (2026-05-31):

| 구분 | 구현 파일 | 내용 |
| --- | --- | --- |
| Runtime task packet | `apps/agent/app/services/agent_task_packets.py` | 기존 stage 실행 결과를 `input_normalization`, `video_observation`, `fact_arbitration`, `scenario_classification`, `evidence_retrieval`, `knia_matching`, `fault_ratio`, `criminal_liability`, `insurance_guidance`, `action_guidance`, `presentation_policy` task packet으로 변환한다. |
| 상태 반영 | `apps/agent/app/services/agent_task_packets.py` | `agent_plan.tasks[*].status`, `result_ref`, `blocking_reasons`를 실제 stage 결과 기준으로 갱신한다. 상태는 `succeeded`, `needs_review`, `blocked`, `failed` 중 하나로 표현한다. |
| Trace/Quality 연결 | `apps/agent/app/services/orchestration_output.py`, `agent_execution_trace.py`, `agent_quality_packet.py` | `agent_task_packets`를 output에 추가하고 `agent_trace.task_packets`, `agent_quality_packet` required packet과 guardrail check에 연결했다. |
| 안전성 | `apps/agent/app/services/agent_contracts.py` | `AgentTaskRuntimePacket` 계약을 추가했다. packet/observation metadata에 raw user text, prompt, secret, token이 들어가면 validation에서 실패한다. |
| 검증 | `apps/agent/tests/test_agent_task_packets.py`, `apps/agent/tests/test_orchestrator.py` | Docker Agent 컨테이너에서 `python -m pytest tests/test_agent_task_packets.py tests/test_planner.py tests/test_agent_contracts.py tests/test_orchestrator.py tests/test_judgment_contract.py tests/test_video_input_contract.py`를 실행했고 62건이 모두 통과했다. |

P2-2 제한 사항:

- 아직 task result를 최종 report에 직접 병합하지 않는다. 이 작업은 P2-3의 goal aggregator에서 진행한다.
- `agent_task_packets`는 내부 진단/관리자용 metadata이며 public UI에 raw diagnostic payload로 노출하지 않는다.

#### P2-3. Goal 결과 병합 정책 구현

- 각 task result를 최종 report에 직접 붙이지 않고 goal aggregator를 거치게 한다.
- 법률 근거와 과실비율이 서로 다른 사고축을 쓰면 `blocked_for_consistency` 상태로 보류한다.
- 영상 fact와 사용자 fact가 충돌하면 확정하지 않고 질문 또는 조건부 결과로 넘긴다.
- specialist 결과가 서로 충돌하면 conflict packet을 남긴다.

검증:

- 후방추돌, 교차로 신호 불명확, 중앙선 장애물 회피, 보행자 배경 오염, 자전거 비접촉 유발 fixture에서 goal 병합이 오염 없이 동작하는지 확인한다.

P2-3 goal 결과 병합 정책 구현 결과 (2026-05-31):

| 구분 | 구현 파일 | 내용 |
| --- | --- | --- |
| Goal aggregator | `apps/agent/app/services/agent_goal_aggregator.py` | `agent_task_packets`, `agent_judgment`, `fact_arbitration`, KNIA primary match를 병합해 `agent_goal_result`를 생성한다. |
| 사고축 불일치 차단 | `apps/agent/app/services/agent_goal_aggregator.py` | 법률/KNIA 근거축과 사고 대분류가 다르면 `law_fault_axis_mismatch` conflict packet을 남기고 `blocked_for_consistency`로 확정 판단을 막는다. |
| 영상/입력 충돌 보류 | `apps/agent/app/services/agent_goal_aggregator.py` | 영상 observation이 사용자 입력과 충돌하거나 보류된 경우 `video_user_fact_conflict`를 남기고 `reference_only`로 제한한다. |
| Trace/Quality 연결 | `apps/agent/app/services/orchestration_output.py`, `agent_execution_trace.py`, `agent_quality_packet.py` | `agent_goal_result`를 output, trace summary, quality required packet, guardrail check에 연결했다. |
| Schema/검증 | `apps/agent/app/schemas.py`, `apps/agent/tests/test_agent_goal_aggregator.py`, `apps/agent/tests/test_orchestrator.py` | Docker Agent 컨테이너에서 `python -m pytest tests/test_agent_goal_aggregator.py tests/test_agent_task_packets.py tests/test_planner.py tests/test_agent_contracts.py tests/test_orchestrator.py tests/test_judgment_contract.py tests/test_video_input_contract.py`를 실행했고 65건이 모두 통과했다. |

P2-3 제한 사항:

- `agent_goal_result`는 최종 병합/보류 metadata이며 public 화면의 문구를 직접 바꾸지 않는다.
- evidence 부족이나 mismatch를 발견해도 새 task를 자동 생성하지 않는다. 이 작업은 P2-4에서 제한된 replan으로 다룬다.

#### P2-4. 제한적 재계획 도입

- evidence 부족, KNIA mismatch, 영상 candidate 불확실, 사용자 입력 충돌 상황에서만 replan을 허용한다.
- 재계획 횟수는 명시적으로 제한한다.
- 재계획 이유와 추가 task를 trace에 남긴다.
- 재계획 후에도 부족하면 reference-only 또는 추가 확인 필요로 종료한다.

검증:

- 무한 루프가 없는지 테스트한다.
- replan이 과실비율을 임의로 확정하지 않는지 확인한다.

P2-4 제한적 재계획 도입 결과 (2026-05-31):

| 구분 | 구현 파일 | 내용 |
| --- | --- | --- |
| Bounded replan | `apps/agent/app/services/agent_replan.py` | `agent_judgment`, `agent_goal_result`, `fact_arbitration`, `reflection_loop`를 읽어 허용된 blocker만 replan 후보로 변환한다. |
| 허용 reason | `apps/agent/app/services/agent_replan.py` | evidence 부족, KNIA basis 부족/불일치, 영상 fact 보류/충돌, 필수 입력 부족만 허용한다. 그 외 unsupported claim 등은 자동 재계획하지 않는다. |
| 반복 제한 | `apps/agent/app/services/agent_replan.py` | `MAX_REPLAN_ITERATIONS=1`로 제한한다. 이미 1회 requery가 사용되면 `exhausted_reference_only`로 종료한다. |
| Trace/Quality 연결 | `apps/agent/app/services/orchestration_output.py`, `agent_execution_trace.py`, `agent_quality_packet.py` | `agent_replan`을 output, `agent_plan.replan_summary`, trace summary, quality required packet과 guardrail check에 연결했다. |
| 검증 | `apps/agent/tests/test_agent_replan.py`, `apps/agent/tests/test_orchestrator.py` | Docker Agent 컨테이너에서 `python -m pytest tests/test_agent_replan.py tests/test_agent_goal_aggregator.py tests/test_agent_task_packets.py tests/test_planner.py tests/test_agent_contracts.py tests/test_orchestrator.py tests/test_judgment_contract.py tests/test_video_input_contract.py`를 실행했고 68건이 모두 통과했다. |

P2-4 제한 사항:

- 현재 단계는 다음 iteration 후보를 안전 metadata로 제안한다. 실제 비동기 task 실행이나 MCP tool 재호출 orchestration은 P3 이후 tool layer와 연결해 확장한다.
- replan은 기존 분석 결과를 자동으로 뒤집지 않는다. 근거가 부족하면 계속 reference-only 또는 추가 확인 필요 상태를 유지한다.

### P3. 내부 MCP 계층 강화

목적: 현재 tool registry를 실제 MCP-like 실행 계층으로 정리하고, 표준 MCP 도입 전에도 도구 경계를 신뢰할 수 있게 만든다.

#### P3-1. Tool registry schema화

- `register_tool(name, fn)`만 있는 구조를 `ToolSpec` 기반으로 확장한다.
- 각 tool에 다음 metadata를 추가한다.
  - `name`
  - `description`
  - `input_schema`
  - `output_schema`
  - `scope`
  - `timeout_ms`
  - `safe_for_public_trace`
  - `side_effect`
- 기존 tool을 새 spec으로 이관한다.

검증:

- bootstrapping 후 모든 tool에 schema와 scope가 있는지 테스트한다.

P3-1 Tool registry schema화 결과 (2026-05-31):

| 구분 | 구현 파일 | 내용 |
| --- | --- | --- |
| Tool spec 확장 | `apps/agent/app/services/agent_contracts.py` | `MCPToolSpec`에 `safe_for_public_trace`, `side_effect` metadata를 추가했다. |
| Registry schema화 | `apps/agent/app/mcp/tool_registry.py` | `_REGISTRY`와 `_TOOL_SPECS`를 함께 관리하고, spec이 없는 tool 등록을 거부한다. |
| Metadata 조회 | `apps/agent/app/mcp/tool_registry.py` | `get_tool_spec`, `list_tool_specs`, `list_tool_metadata`, `validate_registry_specs`를 추가했다. |
| 검증 | `apps/agent/tests/test_mcp_tool_registry.py`, `apps/agent/tests/test_agent_contracts.py` | Docker Agent 컨테이너에서 `python -m pytest tests/test_mcp_tool_registry.py tests/test_agent_contracts.py`를 실행했고 8건이 모두 통과했다. |

P3-1 제한 사항:

- 아직 executor 단계에서 payload validation, scope validation, timeout 강제는 하지 않는다. 이 작업은 P3-2에서 진행한다.

#### P3-2. Tool executor 권한/검증 추가

- tool 실행 전 payload validation을 수행한다.
- tool 실행 전 scope validation을 수행한다.
- tool timeout과 실패 packet을 표준화한다.
- 실패를 숨기지 않고 observation으로 반환한다.
- raw exception이 public payload로 나가지 않도록 sanitization한다.

검증:

- 잘못된 payload, timeout, 내부 예외, 권한 없는 호출 테스트를 추가한다.

P3-2 Tool executor 권한/검증 추가 결과 (2026-05-31):

| 구분 | 구현 파일 | 내용 |
| --- | --- | --- |
| Payload validation | `apps/agent/app/mcp/tool_executor.py` | `MCPToolSpec.input_schema.required`와 기본 타입을 실행 전에 검증한다. |
| Scope validation | `apps/agent/app/mcp/tool_executor.py` | `granted_scopes`가 주어진 경우 `required_scopes` 충족 여부를 확인한다. 기존 내부 호출은 scope 인자를 생략해 기존 흐름을 유지한다. |
| Failure packet | `apps/agent/app/mcp/tool_executor.py` | payload 오류, 권한 부족, timeout, 내부 예외를 `MCPToolErrorPacket` 형태로 반환한다. raw exception 문자열은 public payload에 노출하지 않는다. |
| Timeout 표준화 | `apps/agent/app/mcp/tool_executor.py` | sync tool을 강제 중단하지는 않지만, 실행 시간이 spec timeout을 넘으면 `tool_timeout` packet으로 표준화한다. |
| 검증 | `apps/agent/tests/test_mcp_tool_executor.py` | Docker Agent 컨테이너에서 `python -m pytest tests/test_mcp_tool_executor.py tests/test_mcp_tool_registry.py tests/test_agent_contracts.py tests/test_agent_replan.py tests/test_agent_goal_aggregator.py tests/test_agent_task_packets.py tests/test_orchestrator.py`를 실행했고 31건이 모두 통과했다. |

P3-2 제한 사항:

- 아직 모든 DB/RAG/KNIA service 호출을 executor 경유로 강제하지 않는다. 호출 경계 정리는 P3-3에서 선별한다.
- timeout은 실행 후 감지 방식이다. hard timeout interrupt가 필요하면 별도 worker/process 격리가 필요하다.

#### P3-3. 직접 service 호출 경로 정리

- KNIA/법령/RAG/evidence guard 중 tool 경계가 필요한 호출을 선별한다.
- 모든 호출을 무조건 tool executor로 보내지 말고, 다음 기준으로 나눈다.
  - 내부 pure function: 직접 호출 유지 가능
  - 외부 API/DB/RAG/검색/캐시/권한 영향: tool executor 경유 우선
- 우선순위:
  1. legal RAG
  2. KNIA search/matching
  3. evidence guard
  4. cache invalidation
  5. future public API connectors

검증:

- `mcp_tool_calls` 로그가 주요 tool 호출에 남는지 확인한다.
- 기존 API 응답 payload가 깨지지 않는지 확인한다.

P3-3 직접 service 호출 경로 정리 결과 (2026-05-31):

| 구분 | 구현 파일 | 내용 |
| --- | --- | --- |
| Cache boundary | `apps/agent/app/routers/internal_routes/cache.py` | cache invalidate route를 `invalidate_cache_tool` executor 경유로 전환했다. |
| KNIA JSON boundary | `apps/agent/app/routers/internal_routes/knia.py` | KNIA JSON import, myaccident pages/tree, JSON search, media search route를 executor 경유로 전환했다. |
| Spec 정합성 | `apps/agent/app/services/agent_contracts.py` | `get_knia_menu_tree_tool` 입력을 `myaccident_no`, `invalidate_cache_tool` 입력을 `scope`로 실제 payload와 맞췄다. |
| 유지 경계 | `apps/agent/app/services/orchestration_evidence.py` 등 | pure filtering/normalization, collector, vectorizer rebuild, repository reference 조회는 이번 단계에서 직접 호출을 유지한다. 대용량 수집/재빌드는 별도 운영 통제가 필요하다. |
| 검증 | `apps/agent/tests/test_mcp_route_boundaries.py` | Docker Agent 컨테이너에서 `python -m pytest tests/test_mcp_route_boundaries.py tests/test_mcp_tool_executor.py tests/test_mcp_tool_registry.py tests/test_agent_contracts.py`를 실행했고 15건이 모두 통과했다. |

P3-3 제한 사항:

- 실제 `mcp_tool_calls` DB insert는 `DATABASE_URL`이 있는 실행 환경에서만 기록된다. 로컬 테스트는 route가 executor로 들어가는 계약을 검증했다.
- core 분석 pipeline의 RAG/KNIA 호출은 아직 직접 service 호출을 일부 유지한다. 이 경계는 P4 이후 Agent 분리 과정에서 다시 선별한다.

#### P3-4. 표준 MCP 도입 판단 gate

- 표준 MCP Host/Client/Server를 바로 도입하지 않고 판단 gate를 둔다.
- 도입 조건:
  - 외부 tool/agent가 3개 이상 늘어남
  - tool 권한 분리가 현재 executor로 부족함
  - 다른 host에서 같은 tool을 재사용해야 함
  - 표준 MCP client와 연결해야 함
  - tool isolation/security가 독립 프로세스를 요구함
- 조건 충족 전에는 내부 MCP-like 계층을 유지한다.

검증:

- 도입 여부가 감정적 결정이 아니라 조건표로 판단되는지 문서화한다.

P3-4 완료 기록:

- `apps/agent/app/mcp/standard_mcp_gate.py`에 `evaluate_standard_mcp_adoption()`을 추가했다.
- 표준 MCP 도입 조건은 외부 tool/agent 합계 3개 이상, 내부 executor 권한 분리 부족, cross-host reuse, 표준 MCP client 필요, 독립 process 격리 필요로 고정했다.
- 조건이 충족되지 않으면 현재 내부 MCP-like registry/executor를 유지하고 hardening을 계속한다.
- 이번 단계는 판단 gate만 추가했으며 표준 MCP runtime, transport, 외부 server/client, 기존 tool 실행 동작은 변경하지 않았다.
- 검증은 `tests/test_standard_mcp_gate.py`와 기존 P3 MCP registry/executor/route boundary 회귀 테스트로 수행한다.

### P4. 전문 Agent 역할 독립화

목적: persona 이름만 있는 구조를 벗어나, 각 전문 Agent가 독립 결과를 만들고 합의/충돌을 남기게 한다.

#### P4-0. Persona/role 고도화 기준 정리

- 현재 존재하는 `personas`, `specialists`, `llm_client` prompt, analyst module의 역할 정의를 모두 inventory로 정리한다.
- 각 역할을 다음 세 그룹으로 분리한다.
  - 판단 책임 Agent: 법률, KNIA, 과실비율, 형사책임, 보험처리처럼 실제 분석 결과를 제출하는 Agent.
  - 관찰/검증 Agent: 영상관찰, fact arbitration, evidence audit처럼 입력과 근거의 신뢰도를 평가하는 Agent.
  - 표현/안내 Agent: presentation policy, 사용자 요약, 행동 가이드처럼 검증된 결과를 사용자에게 전달하는 Agent.
- "AI 교통사고 전문 변호사형 분석관"은 전체 결론을 임의로 확정하는 상위 권한자가 아니라, 법률/판례/KNIA 근거와 다른 전문 Agent 결과를 종합해 예상 법률 쟁점과 대응 방향을 제시하는 역할로 정의한다.
- 보험 Agent는 법률 판단을 대신하지 않고 보험 접수, 대인/대물, 증빙, 분쟁심의 가능성, 손해사정 관점만 담당한다.
- 형사책임 Agent는 민사 과실비율을 확정하지 않고 12대 중과실, 인명피해, 신고/조치의무, 형사 리스크 가능성을 담당한다.
- 영상관찰 Agent는 사고 판단을 확정하지 않고 사고 기점, 객체 후보, 신호/차선/정차/충돌 위치 같은 정량 관찰값과 신뢰도만 제출한다.
- evidence audit Agent는 각 Agent의 주장과 근거가 직접 연결되는지 검사하며, 근거 부족 주장을 final output에서 제한한다.
- persona는 전문성을 높이기 위해 실제 직업에 가까운 역할 이름을 사용하되, 특정 실존 인물의 말투나 브랜드를 모방하지 않는다.
- 각 persona에는 다음을 반드시 적는다.
  - 전문적 관점.
  - 사용할 수 있는 근거.
  - 사용할 수 없는 근거.
  - 확정 금지 항목.
  - 다른 Agent에 넘겨야 하는 항목.
  - 사용자에게 말할 때의 표현 원칙.

검증:

- 현재 specialist/persona 정의와 실제 analyst output이 같은 역할 체계를 쓰는지 확인한다.
- 하나의 Agent가 법률, 보험, 형사, 영상 판단을 모두 섞어서 반환하지 않는지 확인한다.
- prompt가 길어졌다는 이유로 근거 검증, finality, safety constraint가 약해지지 않는지 확인한다.

P4-0 완료 기록:

- `apps/agent/app/services/specialist_role_inventory.py`를 추가해 현재 analyst/persona/specialist/report composer와 목표 Specialist Agent 역할의 mapping을 inventory로 고정했다.
- 역할 group을 판단 책임 Agent, 관찰·검증 Agent, 표현·안내 Agent로 나누었다.
- `no_agent_final_verdict`, `evidence_first`, `video_candidate_guard`, `role_handoff_required`, `presentation_cannot_add_facts`를 P4 이후 공통 role boundary rule로 기록했다.
- 기존 orchestrator 실행 순서, public API/DTO, DB schema, Redis key, storage path, 외부 API 종류, LLM 호출 정책은 변경하지 않았다.
- 검증은 `tests/test_specialist_role_inventory.py`와 기존 Agent contract/orchestrator 회귀 테스트로 수행한다.

#### P4-1. Agent 역할 재정의

- 최소 Agent 역할을 다음으로 고정한다.
  - `video_observation_agent`
  - `fact_arbitration_agent`
  - `traffic_law_agent`
  - `knia_fault_standard_agent`
  - `fault_ratio_agent`
  - `criminal_liability_agent`
  - `insurance_claim_agent`
  - `evidence_audit_agent`
  - `presentation_policy_agent`
- 각 Agent의 책임 밖 항목을 명시한다.
- 한 Agent가 다른 Agent의 책임을 침범하지 못하도록 출력 schema를 제한한다.
- P4-0에서 정리한 persona/role profile을 각 Agent 역할 정의에 연결한다.

검증:

- Agent별 책임표가 `SYSTEM_OVERVIEW.md`와 충돌하지 않는지 확인한다.
- Agent별 persona/role profile이 P1-2 결과 계약과 연결되는지 확인한다.

P4-1 완료 기록:

- `apps/agent/app/services/agent_contracts.py`에 `STANDARD_SPECIALIST_ROLE_IDS`, `SPECIALIST_ROLE_ALIASES`, `canonical_specialist_role_id()`를 추가해 새 표준 role id와 기존 alias를 함께 허용했다.
- `apps/agent/app/services/specialist_role_definitions.py`를 추가해 10개 Specialist Agent의 책임, 판단 권한, 금지 판단, 필요 근거, handoff 대상, safety constraint를 코드 계약으로 고정했다.
- `apps/agent/app/services/specialist_role_inventory.py`의 목표 role id를 표준 role id로 정리하고, 기존 alias는 validation 호환층으로 유지했다.
- 이번 단계는 역할 profile과 validation 기준을 고정하는 additive 변경이며, 기존 orchestrator 실행 순서, public API/DTO, DB schema, Redis key, storage path, 외부 API 종류, LLM 호출 정책은 변경하지 않았다.
- 검증은 `tests/test_specialist_role_definitions.py`, `tests/test_specialist_role_inventory.py`, 기존 `tests/test_agent_contracts.py`, `tests/test_orchestrator.py`로 수행한다.

#### P4-2. Agent 실행 함수 분리

- 현재 orchestration 내부에 섞인 분석 함수를 Agent별 service로 분리한다.
- 각 Agent는 `run(input_packet) -> AgentResult` 형태를 가진다.
- Agent 내부에서 사용하는 tool은 MCP executor 또는 명시된 service를 통해 호출한다.
- Agent는 raw report 문장을 직접 조립하지 않고 claim/evidence/result 구조를 반환한다.

검증:

- Agent별 단위 테스트를 만든다.
- orchestrator는 stage sequencing과 result aggregation만 담당하는지 확인한다.

P4-2 완료 기록:

- `apps/agent/app/services/specialist_agent_runners.py`를 추가해 기존 분석 결과를 10개 Specialist Agent의 `SpecialistAgentResult` adapter 결과로 감싼다.
- `attach_specialist_agent_results()`를 `orchestration_output.py`에 연결해 `agent_trace`와 `agent_quality_packet` 생성 전에 `specialist_agent_results` packet을 붙인다.
- `agent_execution_trace.py`와 `agent_quality_packet.py`가 specialist result count, role id, safe metadata 여부를 추적한다.
- `AnalysisOutput`에 `specialist_agent_results`를 additive 필드로 추가했다. 기존 `legal_analysis`, `fault_ratio`, `legal_liability`, `insurance_guide`, `action_plan`, `evidence_audit` payload는 변경하지 않았다.
- 검증은 `tests/test_specialist_agent_runners.py`, 기존 Specialist role/contract/orchestrator/task/goal 회귀 테스트로 수행한다.

#### P4-3. Persona/prompt 버전 관리

- LLM을 쓰는 Agent와 deterministic Agent를 구분한다.
- LLM Agent prompt에는 다음을 명시한다.
  - 실제 판결 확정 금지
  - 근거 없는 법률/판례 생성 금지
  - 입력에 없는 사실 생성 금지
  - 영상 candidate를 확정 fact로 승격 금지
  - 조건부 결과와 불확실성 표시
- prompt 버전과 model 정보를 trace에 남긴다.
- persona prompt는 "전문가처럼 보이는 문장"보다 "전문 Agent가 어떤 근거로 어떤 범위까지 판단할 수 있는지"를 우선한다.
- prompt에는 역할별 handoff 규칙을 포함한다.
  - 법률 Agent가 보험 절차를 확정하지 않는다.
  - 보험 Agent가 민형사 책임을 확정하지 않는다.
  - 영상관찰 Agent가 과실비율을 확정하지 않는다.
  - 과실비율 Agent가 영상 후보를 확정 fact로 승격하지 않는다.
  - presentation Agent가 내부 불확실성을 숨기지 않는다.
- prompt와 deterministic rule이 충돌하면 deterministic rule과 evidence/judgment contract를 우선한다.

검증:

- prompt injection fixture에서 사용자가 "근거 없이 확정하라"고 해도 final judgment가 나오지 않는지 확인한다.
- persona별 prompt snapshot 또는 version id가 trace/quality packet에서 확인 가능한지 확인한다.
- 같은 사고 입력에서 persona 고도화 전후 결과가 더 전문적으로 보이더라도 근거 없는 확정이 늘지 않았는지 확인한다.

P4-3 완료 기록:

- `apps/agent/app/services/specialist_prompt_registry.py`를 추가해 10개 표준 Specialist role의 실행 종류, prompt version, guardrail version, 출력 section, handoff 대상, 금지 규칙을 안전 metadata로 고정했다.
- `apps/agent/app/services/llm_client.py`의 공통 JSON 생성 system prompt에 LLM guardrail version을 붙이고, 최종 판결/확정 과실/유죄·무죄 확정, 근거 없는 법률·판례 생성, 입력에 없는 사실 생성, 영상 candidate의 확정 fact 승격을 금지했다.
- `orchestration_output.py`는 `specialist_agent_results` 이후 `specialist_prompt_registry`를 연결하고 `model_info.specialist_prompt_registry_version`을 기록한다.
- `agent_execution_trace.py`와 `agent_quality_packet.py`가 prompt registry coverage, guardrail ids, safe metadata 여부를 추적한다. prompt 원문, secret, API key, token 값은 기록하지 않는다.
- `AnalysisOutput`에 `specialist_prompt_registry`를 additive 필드로 추가했다. 기존 public route, DB schema, Redis key, storage path, 외부 API 종류는 변경하지 않았다.
- 검증은 `tests/test_specialist_prompt_registry.py`, 기존 Specialist runner/role/contract/orchestrator/LLM policy/task/goal 회귀 테스트로 수행한다.

#### P4-4. Agent 합의/충돌 처리

- Agent 결과 간 충돌 유형을 정의한다.
  - 사고 대상 충돌
  - 사고 유형 충돌
  - 신호 상태 충돌
  - KNIA 기준 충돌
  - 과실 방향 충돌
  - 형사/민사 판단 충돌
- 충돌 시 우선순위를 정한다.
  - 확정 영상 fact
  - 사용자 명시 입력
  - KNIA/법령/판례 근거
  - LLM 요약
  - fallback
- 충돌이 해결되지 않으면 조건부 결과 또는 추가 질문으로 넘긴다.

검증:

- 충돌 fixture에서 50:50 fallback으로 바로 도망가지 않고 조건부 결과 또는 질문이 생성되는지 확인한다.

P4-4 완료 기록:

- `apps/agent/app/services/specialist_consensus.py`를 추가해 Agent 결과와 기존 goal/fact arbitration 충돌을 `accident_target_conflict`, `accident_type_conflict`, `signal_status_conflict`, `knia_standard_conflict`, `fault_direction_conflict`, `civil_criminal_conflict` taxonomy로 분류한다.
- 합의 우선순위는 `confirmed_video_fact`, `explicit_user_fact`, `direct_evidence`, `llm_summary`, `fallback` 순서로 기록한다.
- 조건부 과실 분기나 신호 불확실성이 있으면 `needs_conditionals`와 `present_conditional_results_before_fault_ratio` answer policy로 남기고, 충돌이 있으면 flat 50:50 fallback을 금지하는 metadata를 남긴다.
- `orchestration_output.py`는 prompt registry 이후 `specialist_consensus`를 연결하고 `model_info.specialist_consensus_version`을 기록한다.
- `agent_execution_trace.py`와 `agent_quality_packet.py`가 consensus status, conflict count, conditional conflict count, answer policy, safe metadata 여부를 추적한다.
- `AnalysisOutput`에 `specialist_consensus`를 additive 필드로 추가했다. 기존 public route, DB schema, Redis key, storage path, 외부 API 종류는 변경하지 않았다.
- 검증은 `tests/test_specialist_consensus.py`, 기존 prompt/runner/goal/contract/orchestrator/task/replan 회귀 테스트로 수행한다.

### P5. 영상 사실 추출과 Agent 입력 계약 고도화

목적: 영상 처리 결과가 Agent 판단에 필요한 정량 사실로 연결되게 하되, 오염된 사실은 확정하지 않게 한다.

#### P5-1. 사고 기점 탐지 강화

- YOLO 객체 변화, optical/scene 변화, OpenAI frame observation을 결합해 사고 후보 구간을 잡는다.
- 첫 등장 객체를 사고로 오인하지 않도록 전체 프레임 또는 후보 구간 전체를 확인한다.
- 긴 영상에서는 사고 가능 구간을 먼저 좁히고 해당 구간을 dense frame으로 재분석한다.
- 휴대폰으로 블랙박스 화면을 촬영한 영상의 UI/오버레이/방송 진행자/자막 잡음을 분리한다.

검증:

- 사고 전 보행자/횡단보도/자막이 직접 사고대상으로 승격되지 않는지 확인한다.

P5-1 완료 기록:

- `apps/worker/worker/yolo_frame_analysis.py`의 event candidate summary에 `accident_window_quality`, `event_target_detection_count`, `target_phase_counts`를 추가해 단순 객체 등장과 사고 후보 구간을 분리했다.
- `object_presence_only` 후보는 OpenAI 프레임 선택을 위한 YOLO 1순위 사고 후보 ranking에서 제외한다.
- event phase에 실제 mobile target이 잡힌 경우와 pre/event/post 문맥이 있는 경우에만 후보 점수가 올라가고, event phase 대상 감지가 없는 후보는 감점한다.
- 이 변경은 YOLO/OpenAI/frame observation의 확정 fact 승격 정책을 바꾸지 않고, 프레임 선택 후보의 품질 metadata를 보강하는 additive 변경이다.
- 검증은 Worker 컨테이너에서 `python -m unittest discover -s tests -p 'test_yolo_frame_analysis_contract.py'`, `test_video_preprocess_contract.py`, `test_frame_analysis_contract.py`, `test_job_processor_contract.py`로 수행했다. Worker 컨테이너에는 pytest가 없어 unittest discovery로 검증했다.

#### P5-2. 직접 사고대상 추출 강화

- `vehicle`, `pedestrian`, `bicycle`, `motorcycle`, `object`, `unknown`을 구분한다.
- 단순 화면 등장과 직접 충돌 대상을 분리한다.
- 후보가 여럿이면 candidate list로 유지하고 확정하지 않는다.
- 사용자 입력의 사고 대분류와 영상 후보가 충돌하면 질문을 생성한다.

검증:

- 차대차 영상에 보행자가 보여도 차대사람으로 오염되지 않는지 확인한다.
- 차대보행자 영상에서 보행자가 직접 충돌 대상이면 누락되지 않는지 확인한다.

#### P5-3. 핵심 정량 fact 추출

- 신호등 유무와 색상.
- 내 차량 신호와 상대 차량 신호의 가시성 분리.
- 차선, 중앙선, 차선변경, 역주행, 갓길, 도로 장애물.
- 정차 여부와 정차 사유 후보.
- 전방/후방/측면 충돌 방향.
- 2차 충돌 여부.
- 자전거/이륜차/보행자 비접촉 유발 여부.
- 속도는 영상으로 확정하지 않고 가능성/질문으로만 처리한다.

검증:

- 각 fact가 `confirmed`, `candidate`, `needs_confirmation`, `conflict`, `ignored` 중 하나의 상태를 갖는지 확인한다.

#### P5-4. AI-Hub/공개 reference 평가 연결

- AI-Hub 라벨은 추론 입력이 아니라 사후 평가 reference로만 사용한다.
- 원천 영상은 필요한 소량만 내려받고 Git에 올리지 않는다.
- 라벨 기반 평가와 영상 기반 평가를 분리한다.
- 공개 영상/한문철 영상은 링크/설명/의견을 calibration reference로만 사용하고, 사용자 case fact로 주입하지 않는다.

검증:

- reference 라벨이 case input JSON에 들어가면 validator가 실패하는지 확인한다.

### P6. 근거 검색/판단 계약 고도화

목적: 영상/입력 fact가 법령, KNIA, 판례, 보험 처리 안내와 같은 사고축을 쓰도록 만든다.

#### P6-1. 사고축 기반 evidence routing

- 사고 대분류와 직접 사고대상을 먼저 결정한다.
- 보행자/횡단보도/자전거/신호/차선변경/후방추돌/중앙선/무등화 정차차량은 사고축과 환경축을 분리한다.
- 사고축과 맞지 않는 evidence는 직접 근거가 아니라 참고 또는 제외로 표시한다.

검증:

- 차대차 사고에 차대사람 KNIA 기준이 primary로 나오지 않는지 확인한다.

#### P6-2. 조건부 판단 강화

- 상대 신호가 보이지 않는 교차로 사고는 상대 신호별 조건부 결과를 만든다.
- 중앙선 침범 사유가 불명확하면 장애물 회피/불법침범 조건을 나눈다.
- 정차 사유가 불명확하면 정당한 정차/급정차/이유 없는 정차 조건을 나눈다.
- 속도, 무등화, 시야 확보, 2차 충돌, 비접촉 유발도 조건부 결과로 처리한다.

검증:

- 애매한 사고에서 50:50 단일 fallback 대신 조건부 결과가 표시되는지 확인한다.

#### P6-3. 과실비율 결과 계약 강화

- 과실비율은 단일 숫자보다 기본 범위, 조정 가능성, 확인 필요 요소를 우선한다.
- `내 책임 50 / 상대 50` fallback은 정말 근거가 부족할 때만 사용한다.
- 근거가 충분한 경우에는 사고축에 맞는 기준 범위를 제시한다.
- 법원/보험/분쟁심의 결과가 달라질 수 있음을 표시하되, 무의미하게 넓은 범위로 회피하지 않는다.

검증:

- 사고 1처럼 중앙선 장애물 회피와 대향 차량 충돌 구조가 잡히면 일반 50:50으로 접히지 않는지 확인한다.

#### P6-4. 근거 표시 품질 강화

- 한국인 사용자 화면에는 한국어 법령/KNIA/판례 카드만 기본 표시한다.
- 영어 fallback title이나 technical label이 사용자 카드에 나오지 않게 한다.
- 근거가 fallback이면 fallback임을 숨기지 않는다.
- 썸네일이 없으면 깨진 이미지 대신 링크 버튼만 표시한다.

검증:

- 사용자 화면과 관리자 화면의 근거 카드가 사고축과 일치하는지 확인한다.

### P7. Gateway/Frontend 표시 계약 정리

목적: Agent 내부 구조가 정리되어도 사용자 화면에 raw diagnostic이나 오해 가능한 표현이 나오지 않게 한다.

#### P7-1. 사용자 payload와 관리자 payload 분리

- 사용자 payload는 쉬운 설명, 조건부 결과, 확인 필요 항목, 근거 카드 중심으로 제한한다.
- 관리자 payload는 trace, task, tool call, 영상 관찰값, candidate 상태를 볼 수 있게 한다.
- 관리자 진단은 기존 사용자 flow에 영향을 주지 않는다.

검증:

- 사용자 화면에서 raw JSON, internal key, English technical label이 보이지 않는지 확인한다.

#### P7-2. 보완 질문 UX 정리

- 질문 field와 answer key가 서로 영향을 주지 않게 한다.
- 같은 field를 쓰는 질문도 독립적으로 선택되게 한다.
- 질문 문장은 짧고 명확하게 작성한다.
- 영상에서 확인된 후보, 사용자 입력 충돌, 근거 부족 질문을 구분해 표시한다.

검증:

- 하나의 select 변경이 다른 질문 선택값을 바꾸지 않는지 확인한다.

#### P7-3. 결과 표시 finality 정리

- 확정, 참고, 조건부, 추가 확인 필요를 UI에서 명확히 구분한다.
- "추가 확인 필요"가 항상 무의미한 결론처럼 보이지 않게, 이미 확인된 사실과 부족한 사실을 함께 보여준다.
- 과실비율이 참고 범위인지, 조건부 결과인지, 근거 부족 fallback인지 표시한다.

검증:

- 영상만/입력만/입력+영상 세 모드에서 결과 문구가 일관되는지 확인한다.

### P8. 관측성, 비용, 운영 리스크

목적: Agent가 어떤 도구와 근거를 사용했는지, 비용과 실패가 어디서 발생했는지 확인 가능하게 만든다.

#### P8-1. Trace id 통합

- Gateway 요청, Worker job, Agent analysis, MCP tool call, DB report가 같은 trace id로 연결되게 한다.
- 관리자 화면에서 trace id 기준으로 분석 경로를 확인할 수 있게 한다.

검증:

- 하나의 분석 요청에서 upload/job/agent/tool log를 연결할 수 있는지 확인한다.

#### P8-2. LLM/vision 사용량 기록

- OpenAI model, frame count, retry count, token usage when available, latency, fallback reason을 기록한다.
- YOLO model path, frame count, class counts, error state를 기록한다.
- 비용 계산이 어렵다면 최소 사용량 metadata만 남긴다.

검증:

- OpenAI/YOLO ON 분석에서 사용량 metadata가 비어 있지 않은지 확인한다.

#### P8-3. 실패 관찰값 표준화

- 외부 API 실패.
- OpenAI JSON parsing 실패.
- YOLO model load 실패.
- KNIA 검색 실패.
- DB 저장 실패.
- Redis job 실패.
- 각 실패가 사용자에게는 안전한 메시지로, 관리자에게는 진단 가능한 observation으로 남게 한다.

검증:

- 강제 실패 fixture에서 fallback이 조용히 성공처럼 보이지 않는지 확인한다.

### P9. 테스트와 평가 체계

목적: 구조 보강이 특정 샘플에 맞춘 땜질이 아니라는 것을 반복 검증한다.

#### P9-1. 단위 테스트 확장

- Task/Plan schema 테스트.
- MCP tool schema/executor 테스트.
- Specialist Agent result schema 테스트.
- Video input contract 테스트.
- Evidence routing 테스트.
- Fault ratio branch 테스트.
- Presentation sanitization 테스트.

#### P9-2. E2E 테스트 확장

- 텍스트만.
- 영상만.
- 텍스트+영상.
- 보완 답변 후 재분석.
- KNIA 기준 있음.
- KNIA 기준 없음.
- OpenAI/YOLO ON.
- OpenAI/YOLO OFF fallback.

#### P9-3. Reference 평가 확장

- 사고 1~5.
- AI-Hub label reference.
- 공개 영상 metadata reference.
- synthetic contamination fixture.
- 보행자 배경 오염.
- 신호 불확실성.
- 중앙선 장애물 회피.
- 자전거/이륜차 작은 대상.
- 무등화 정차차량.

#### P9-4. CI/검증 명령 정리

- 로컬 빠른 검증.
- Docker 기반 검증.
- OpenAI/YOLO ON 실제 검증.
- 비용 발생 검증.
- 문서만 변경 검증.

검증:

- 각 검증 명령을 문서화하고, 실패 시 다음 작업에 남긴다.

### P10. 표준 MCP 도입 준비 또는 보류 결정

목적: 내부 MCP-like 구조를 충분히 강화한 뒤, 실제 표준 MCP가 필요한지 결정한다.

#### P10-1. 표준 MCP 요구사항 재평가

- 외부 tool 수.
- 보안 격리 필요성.
- 다중 host 필요성.
- 팀 개발 복잡도.
- 배포/운영 비용.
- 현재 내부 executor로 해결 가능한지.

#### P10-2. 표준 MCP pilot 설계

- pilot 대상 tool 하나를 고른다.
- 후보:
  - KNIA search tool
  - legal RAG search tool
  - evidence guard tool
- Agent는 기존 내부 executor와 표준 MCP adapter를 동시에 지원할 수 있게 한다.
- pilot은 기능 전체 전환이 아니라 compatibility 검증으로 제한한다.

#### P10-3. 도입/보류 결정

- pilot 결과가 복잡도 대비 이득이 없으면 표준 MCP는 계속 보류한다.
- 이득이 명확하면 tool별 migration 순서를 정한다.

검증:

- "MCP를 도입했기 때문에 좋아졌다"가 아니라 어떤 문제를 해결했는지 근거를 남긴다.

### P11. 문서, 인수인계, 발표 정합성

목적: 코드 구조와 문서/발표 설명이 어긋나지 않게 한다.

#### P11-1. 문서 동기화

- `SYSTEM_OVERVIEW.md`에 실제 구조를 반영한다.
- `DEVELOPMENT_PROMPT.md`에 새 작업 원칙을 반영한다.
- `docs/STACK_DECISION_REVIEW.md`의 MCP/Agent 판단을 최신화한다.
- 팀원용 실행/검증 문서에 새 구조를 반영한다.

#### P11-2. 발표 설명 정리

- 현재 구현된 것과 추후 적용할 것을 구분한다.
- "표준 MCP 구현 완료"처럼 과장된 표현을 피한다.
- 현재 강점은 다음처럼 설명한다.
  - MSA 서비스 분리.
  - Agent 판단 계약.
  - 영상 관찰값 오염 방지.
  - 근거 기반 finality 제어.
  - 내부 MCP-like tool registry.
  - Task-Plan-Goal로 확장 가능한 trace/packet 구조.

#### P11-3. 팀원 인수인계

- 어떤 파일을 건드리면 충돌 위험이 큰지 정리한다.
- 팀원이 웹 디자인을 수정할 때 Agent/Worker 변경과 충돌하지 않게 branch/merge 기준을 정리한다.
- 민감 파일과 대용량 파일 제외 기준을 다시 확인한다.

### P12. 최종 구조 점검

목적: 전체 단계가 끝난 뒤 목표 구조에 도달했는지 확인한다.

#### P12-1. 1차 점검: 문서와 코드 일치

- 문서에 적힌 구조가 실제 코드와 맞는지 확인한다.
- 존재하지 않는 파일, 사라진 endpoint, 오래된 실행 명령이 없는지 확인한다.

#### P12-2. 2차 점검: Agent 실행 품질

- 영상/텍스트 입력이 오염 없이 fact로 정리되는지 확인한다.
- Agent별 결과가 독립적으로 남는지 확인한다.
- 충돌과 불확실성이 final result에 올바르게 반영되는지 확인한다.

#### P12-3. 3차 점검: 사용자 가치

- 사용자가 실제로 사고 대응에 필요한 정보를 얻는지 확인한다.
- 단순히 "확인 필요"만 반복하지 않는지 확인한다.
- 근거가 실제 사고축과 맞는지 확인한다.
- 조건부 결과가 이해 가능한지 확인한다.

## 4. 새 작업 추가 규칙

작업 중 새 문제가 발견되면 다음 순서로 처리한다.

1. 현재 진행 단계의 목표와 직접 관련이 있는지 판단한다.
2. 관련이 있으면 해당 단계의 하위 작업으로 추가한다.
3. 선행되어야 하는 작업이면 현재 단계보다 앞에 `Px-y 추가` 형식으로 삽입한다.
4. 관련은 있지만 후순위면 해당 P단계의 마지막에 추가한다.
5. 현재 목표와 무관한 개선이면 `보류 항목`에 넣고 즉시 구현하지 않는다.
6. 추가한 작업은 이유, 기대 산출물, 검증 기준을 함께 적는다.

## 5. 작업 후 목적 부합성 점검 규칙

각 단계 또는 하위 작업이 끝나면 다음 항목을 확인한다.

1. 원래 단계의 목적을 실제로 달성했는가.
2. 구현이 Agent, MCP, Task-Plan-Goal, Gateway, Worker, Frontend, DB의 책임 경계를 침범하지 않았는가.
3. 특정 사고 영상, 특정 fixture, 특정 사용자 문장에만 맞춘 예외 규칙이 들어가지 않았는가.
4. 영상 후보와 확정 fact, 사용자 입력, KNIA/법령/판례 근거가 서로 오염되지 않았는가.
5. 근거 부족, 충돌, 불확실성을 final처럼 숨기지 않았는가.
6. schema, trace, quality packet, tool call log, specialist result 계약이 깨지지 않았는가.
7. 사용자 화면에 raw diagnostic, technical key, 영어 fallback, 내부 판단 근거가 잘못 노출되지 않았는가.
8. 실행한 검증이 해당 작업의 위험도에 충분한가.
9. 실행하지 못한 검증과 남은 리스크를 기록했는가.
10. 문서 동기화가 필요한 변경을 누락하지 않았는가.

위 항목 중 하나라도 실패하면 해당 단계는 완료가 아니다. 실패 원인을 같은 P단계의 보정 작업으로 추가하고, 보정 후 다시 목적 부합성 점검을 수행한다.

## 6. 진행 상태 기록

| 단계 | 상태 | 메모 |
| --- | --- | --- |
| P0 | 완료 | P0-1 용어/성공 기준, P0-2 구현 inventory, P0-3 회귀 기준선, P0-4 작업 문서 연결 완료. 이후 단계는 기존 동작과 결과 품질 비회귀 기준을 유지해야 함 |
| P1 | 완료 | Agent 실행 packet, Specialist Agent/persona, MCP Tool 계약을 additive schema와 단위 테스트로 고정 |
| P2 | 완료 | P2-1 planner 실사용 전환, P2-2 stage별 task packet, P2-3 Goal 병합, P2-4 제한적 재계획 metadata 연결 완료 |
| P3 | 완료 | 내부 MCP tool registry schema, executor 권한/검증, route boundary, 표준 MCP 도입 판단 gate 완료 |
| P4 | 완료 | P4-0 role inventory, P4-1 role profile, P4-2 Specialist Agent 실행 adapter, P4-3 persona/prompt version registry, P4-4 Agent consensus/conflict packet 완료 |
| P5 | 완료 | P5-1 사고 기점 탐지, P5-2 직접 사고대상 오염 방지, P5-3 핵심 정량 fact 상태 계약, P5-4 reference 평가 경계 완료 |
| P6 | 완료 | P6-1 사고축 기반 evidence routing, P6-2 조건부 판단 강화, P6-3 과실비율 결과 계약, P6-4 근거 표시 품질 강화 완료 |
| P7 | 완료 | P7-1 사용자 payload와 관리자 payload 분리, P7-2 보완 질문 payload 정리, P7-3 결과 표시 finality 정리 완료 |
| P8 | 진행 중 | 다음은 P8-1 trace id 통합 |
| P9 | 대기 | 테스트/평가 체계 |
| P10 | 대기 | 표준 MCP 도입 판단 |
| P11 | 대기 | 문서/인수인계/발표 정합성 |
| P12 | 대기 | 최종 구조 점검 |

## 7. 바로 다음 작업

다음 개발은 **P8-1. Trace id 통합**부터 진행한다.

P8-1을 시작할 때는 Gateway 요청, Worker job, Agent analysis, MCP tool call, DB report가 같은 trace id로 연결되는지 확인하고, 관리자 화면 또는 진단 payload에서 분석 경로를 추적할 수 있게 정리한다.

## 2026-05-31 진행 기록 보강

- P5-2 직접 사고대상 추출 강화 완료: YOLO/OpenAI 병합 단계에서 보행자·자전거·이륜차 같은 `*_candidate` 객체 후보가 있다는 이유만으로 OpenAI의 다중 프레임 차량 직접 충돌 관찰을 낮추지 않도록 수정했다.
- 단순 화면 등장/객체 후보는 candidate로 유지하고, 직접 충돌 대상은 `direct_collision_partner_type`, `collision_partner_type`, `primary_collision_target`의 직접 근거가 있을 때만 확정 흐름에 남긴다.
- 차대차 사고에서 보행자가 화면에 보이거나 횡단보도가 있어도 직접 충돌 대상이 차량이면 차대사람 Agent로 오염되지 않는 회귀 테스트를 추가했다.
- 실제 보행자 직접 충돌이 구조화된 직접 대상 값으로 들어오면 기존처럼 차대사람 Agent로 라우팅되는 회귀 테스트를 함께 유지했다.
- 다음 개발은 P5-3 핵심 정량 fact 추출이다. 신호등 유무·색상, 내 차량/상대 차량 신호의 가시성, 차선·중앙선·정차·2차 충돌·충돌 방향 같은 핵심 정량 fact가 `confirmed`, `candidate`, `needs_confirmation`, `conflict`, `ignored` 중 하나의 상태를 갖도록 정리한다.

## 2026-05-31 진행 기록 보강 2

- P5-3 핵심 정량 fact 추출 완료: 영상 관찰값과 fact arbitration 결과에 `confirmed`, `candidate`, `needs_confirmation`, `conflict`, `ignored` 상태를 명시하는 additive contract를 추가했다.
- `video_input_contract`는 `observation_states`와 `observation_state_summary`를 반환한다. 신호 가시성, 신호 색상, 중앙선 침범, 충돌 대상 후보처럼 판단에 쓰이는 물리 fact가 어떤 상태인지 관리자/테스트 화면에서 추적할 수 있다.
- `fact_arbitration`은 `fact_states`와 `fact_state_summary`를 반환한다. 사용자 입력과 영상 fact가 일치하면 `confirmed`, 보완 질문이 필요하면 `needs_confirmation`, 실제 충돌이면 `conflict`로 구분한다.
- 다음 개발은 P5-4 AI-Hub/공개 reference 평가 연결이다. AI-Hub 라벨/공개 영상 설명은 실제 사용자 case fact로 주입하지 않고, 영상 추출 정확도 검증용 reference로만 분리해 사용해야 한다.

### 2026-05-31 P5-4 진행 기록

- P5-4 AI-Hub/공개 reference 평가 연결 완료: reference manifest가 `structured_facts`, `case_json`, `agent_payload`, `user_facts`, `video_metadata` 같은 Agent 입력 payload 필드를 포함하면 검증 실패하도록 했다.
- AI-Hub 597 라벨 변환 결과는 `calibration_reference_only` 정책을 유지하며, 원천 라벨/공개 reference 설명을 Agent 판단 입력으로 직접 주입하지 않는 것을 테스트로 고정했다.
- 검증은 `python -m pytest tests/test_reference_case_manifest_policy.py tests/test_validate_video_accuracy_manifest.py tests/test_evaluate_video_reference_metrics.py`와 reference manifest preflight로 완료했다.
- 다음 개발은 P6-1 사고축 기반 evidence routing이다. 사고 대분류와 직접 사고대상을 먼저 고정하고, 보행자·횡단보도·자전거·신호·차선변경 같은 환경축 근거가 사고축과 맞지 않을 때 1차 근거로 섞이지 않도록 정리한다.

### 2026-05-31 P5-2~P5-4 문서 정합성 재점검

- 사용자 지적에 따라 P5-2 이후 완료 기록을 다시 점검했다. P5-2, P5-3, P5-4 구현과 `SYSTEM_OVERVIEW.md` 기록은 존재하지만, 이 문서의 오래된 상태표와 `바로 다음 작업` 문구가 P5-1 기준으로 남아 있어 혼동 가능성이 있었다.
- 현재 유효한 상태는 `P5 완료`이다. 완료 범위는 P5-1 사고 기점 후보 품질, P5-2 직접 사고대상 오염 방지, P5-3 핵심 정량 fact 상태 계약, P5-4 AI-Hub/공개 reference 평가 경계다.
- 재검증은 `docker compose exec -T worker python -m unittest discover -s tests -p 'test_job_processor_contract.py'`, `docker compose exec -T agent python -m pytest tests/test_video_input_contract.py tests/test_fact_arbitration.py tests/test_party_router_direct_collision_priority.py`, `python -m pytest tests/test_reference_case_manifest_policy.py tests/test_validate_video_accuracy_manifest.py tests/test_evaluate_video_reference_metrics.py`로 완료했다.
- 현재 유효한 바로 다음 작업은 **P6-1 사고축 기반 evidence routing**이다. 오래된 상태표의 P5-1 기준 다음 작업 문구보다 이 기록을 우선한다.

### 2026-05-31 P6-1 진행 기록

- P6-1 사고축 기반 evidence routing 완료: `evidence_axis_router`가 근거별 사고축 상태를 `primary`, `secondary`, `excluded`로 분류한다.
- Agent evidence stage는 사고 대분류와 직접 사고대상에 맞는 근거만 직접 근거로 남기고, 횡단보도·보행자·자전거·신호 같은 환경축 근거는 secondary 또는 excluded audit으로 분리한다.
- Reflection requery로 추가된 legal evidence도 같은 라우팅을 거친다. `model_info.evidence_axis_routing`과 `secondary_evidence`에서 왜 직접 근거가 아닌지 확인할 수 있다.
- 중앙선 사고에서 `차43` 전체를 무조건 제거하던 기존 필터를 보정해, 실제 진로/차선변경 축인 `차43`만 제외하도록 했다.
- 검증은 `tests/test_evidence_axis_router.py`, `tests/test_fault_knia_axis_generalization.py`, `tests/test_orchestration_evidence_filter.py`, `tests/test_orchestrator.py`, `tests/test_judgment_contract.py`, `tests/test_evidence_quality_gate.py`, `tests/test_evidence_source_status.py`, `tests/test_agent_task_packets.py`, `tests/test_agent_goal_aggregator.py`, `tests/test_specialist_agent_runners.py`, `tests/test_specialist_role_definitions.py`와 compileall로 완료했다.
- 다음 개발은 **P6-2 조건부 판단 강화**다. 상대 신호, 중앙선 침범 사유, 정차 사유, 속도·무등화·2차 충돌처럼 결론이 조건부로 갈리는 상황을 단일 50:50 fallback이 아니라 조건부 결과로 분리한다.

### 2026-05-31 P6-2 진행 기록

- P6-2 조건부 판단 강화 완료: `conditional_judgment` 모듈을 추가해 상대 신호, 중앙선 침범 사유, 정차 사유, 무등화·시야·속도, 비접촉 유발, 2차 충돌을 조건부 결과와 확인 필요 fact로 분리한다.
- `fault_ratio_analyst`는 기존 과실 산정 결과를 유지하면서 `conditional_outcomes`, `conditional_judgment`, `conditional_required_facts`를 additive로 붙인다. 일반 50:50 fallback이 필요한 경우에도 조건부 분기가 있으면 `conditional_fact_gap`으로 구분한다.
- 특정 사고 영상에 맞춘 hard-coded 결과가 아니라, 사고축과 미확인 fact 조합에 따라 범용적으로 조건부 결과를 만든다.
- 검증은 `tests/test_conditional_judgment.py`, `tests/test_fault_knia_axis_generalization.py`, `tests/test_orchestrator.py`, `tests/test_judgment_contract.py`와 compileall로 완료했다.
- 다음 개발은 **P6-3 과실비율 결과 계약 강화**다. 단일 숫자보다 기본 범위, 조정 가능성, 확인 필요 요소, 근거 부족 fallback 여부가 일관되게 표시되도록 결과 계약을 정리한다.
### 2026-05-31 P6-3 진행 기록

- P6-3 과실비율 결과 계약 강화 완료: `fault_ratio_result_contract`를 추가해 과실 결과를 `supported_range`, `conditional_range`, `fallback_needs_evidence`로 구분한다.
- Agent 분석 stage는 KNIA 기본과실과 가감요소 registry 적용 이후 `fault_result_contract`를 붙인다. 기존 `my`, `other`, `fault_range`, `conditional_outcomes` 필드는 유지한다.
- 중앙선 장애물 회피처럼 사고축 기준 범위가 잡힌 복합 사고는 일반 50:50 fallback으로 접히지 않고 `supported_range`로 남는다. 상대 신호 미확인처럼 결론 자체가 갈리는 사고는 `conditional_range`로 표시한다.
- 검증은 `tests/test_fault_ratio_result_contract.py`, `tests/test_conditional_judgment.py`, `tests/test_fault_knia_axis_generalization.py`, `tests/test_orchestrator.py`, `tests/test_judgment_contract.py`와 compileall로 완료했다.
- 다음 개발은 **P6-4 근거 표시 품질 강화**다. 사용자/관리자 화면에 한국어 근거, fallback 상태, 썸네일 실패 처리가 사고축과 맞게 표시되는지 정리한다.

### 2026-05-31 P6-4 진행 기록

- P6-4 근거 표시 품질 강화 완료: 사용자 보고서의 법률/KNIA 근거 카드에서 `Road Traffic Act`, `Fault Ratio Guide` 같은 영어 fallback title과 영어 summary/reason이 그대로 나오지 않도록 Gateway 표시 계약을 보강했다.
- `source_type: legal` 근거를 법률 family로 분류하고, 한국어 제목이 없으면 `도로교통법 관련 기준`, `과실비율 인정기준` 같은 안전한 label로 대체한다.
- KNIA 링크 카드도 영어 fallback 제목/요약을 한국어 후보 설명으로 대체하고, 기존 기본 로고/깨진 썸네일 제거 정책을 유지한다.
- 검증은 Gateway에서 `npm test -- --run report-composer.test.ts knia-link-card-composer.test.ts`와 `npm run build`로 완료했다.
- 다음 개발은 **P7-1 사용자 payload와 관리자 payload 분리**다. 일반 사용자 화면에는 raw JSON, internal key, English technical label이 보이지 않고, 관리자 테스트 화면에서는 진단 정보를 볼 수 있도록 경계를 정리한다.

### 2026-05-31 P7-1 진행 기록

- P7-1 사용자 payload와 관리자 payload 분리 완료: 공개 결과 route의 기본 응답은 쉬운 리포트 중심 `result`/`report`만 유지하고, `debug=1` payload는 관리자 권한 요청에서만 허용하도록 제한했다.
- `/api/v1/cases/:caseId/result`, `/report`, `/easy-report`에서 일반 사용자가 debug query를 붙여도 raw trace/debug payload가 내려가지 않는다.
- 관리자 진단은 기존 `/api/v1/admin/cases/:caseId/agent-trace`와 `/api/v1/admin/uploads/:uploadId/video-preprocess`를 유지한다. 사용자 흐름과 관리자 진단 흐름은 분리되어 있다.
- 검증은 Gateway에서 `npm test -- --run analysis-routes.test.ts agent-diagnostics.test.ts report-composer.test.ts`와 `npm run build`로 완료했다.
- 다음 개발은 **P7-2 보완 질문 payload 정리**다. 질문 field/answer key 독립성, raw key 제거, 짧고 명확한 질문 문구를 정리한다.

### 2026-05-31 P7-2 진행 기록

- P7-2 보완 질문 payload 정리 완료: `missing_info.questions[*].field`와 실제 답변 key인 `answer_key`를 분리해 같은 field를 쓰는 여러 질문이 서로의 선택값을 덮어쓰지 않도록 했다.
- Gateway report composer는 `field__qN` 형식의 안정적인 `answer_key`를 생성하고, 같은 field라도 질문 문장이 다르면 독립 질문으로 유지한다. raw/debug 성격의 기존 저장 질문은 더 안전한 영상 후보 질문으로 대체한다.
- Gateway follow-up normalizer는 `answer_key`를 다시 기본 field로 접되, 같은 field의 여러 답변이 서로 충돌하면 조용히 덮어쓰지 않고 unresolved로 남긴다.
- Frontend의 `MissingInfoCard`, `CaseResultView`, `caseWorkspaceFactMapping`도 같은 answer key 규칙을 사용한다.
- 검증은 Gateway에서 `npm test -- --run report-composer.test.ts followup-normalizer.test.ts`, Gateway `npm run build`, Frontend `npm run build`로 완료했다.
- 다음 개발은 **P7-3 결과 표시 finality 정리**다. 확정, 참고, 조건부, 추가 확인 필요 상태와 과실비율의 근거 수준을 사용자 화면에서 일관되게 구분한다.

### 2026-05-31 P7-3 진행 기록

- P7-3 결과 표시 finality 정리 완료: Gateway가 `finality_display_card`를 생성해 과실비율 결과를 `근거 기반 참고`, `조건부 결과`, `참고용`, `추가 확인 필요`로 구분한다.
- `fault_result_contract.display_status`를 사용자 표시용 `fault_status_label`로 변환해 `근거 기반 참고 범위`, `조건별 과실 범위`, `근거 부족 fallback`, `참고용 과실 추정`을 명확히 표시한다.
- Frontend `EasyReportView`는 일반 사용자 모드와 전문 모드 모두에서 판단 상태 카드를 표시하고, 확인된 사실과 더 확인할 사실을 분리해 보여준다.
- 이번 단계는 표시 계약만 보강했으며 Agent 판단값, Worker 영상 처리, DB schema, Redis key, storage path, 외부 API 종류는 변경하지 않았다.
- 검증은 Gateway에서 `npm test -- --run report-composer.test.ts`, Gateway `npm run build`, Frontend `npm run build`로 완료했다.
- 다음 개발은 **P8-1 Trace id 통합**이다. Gateway 요청, Worker job, Agent analysis, MCP tool call, DB report가 같은 trace id로 연결되도록 관측성을 보강한다.
