# LawCompass 시스템 구성 명세서

## 2026-05-22 P1 근거 검색 품질 보강

P1의 `Evidence/search quality` 첫 단계를 진행했다. DB/외부 API 수집 상태가 부족해도 대표 사고 유형의 법률·KNIA 근거 품질 게이트가 최소한의 직접 관련 근거를 확보할 수 있도록 Agent 내부 검색어 확장과 정적 보조 근거 fixture를 보강했다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/scenario_search_terms.py` | `structured_facts` 값 기반 검색어 확장을 추가했다. `opponent_behavior=rear_collision`, `lane_change_actor=user/opponent`, 상대 신호위반, 적색신호, 후방 범퍼 파손, 어린이 피해, 자전거 통행 위치 같은 사실을 검색어로 변환한다. |
| `apps/agent/app/services/static_legal_fallback.py` | 차선변경, 보행자·횡단보도, 어린이보호구역 사고에 대한 과실비율 참고 기준 fixture를 추가했다. 이 fixture들은 외부 API 실패나 로컬 DB 수집 부족 시에도 `knia` family 보조 근거로 품질 게이트에 반영된다. |
| `apps/agent/tests/test_scenario_search_terms.py` | 사고 사실값 기반 검색어 확장 테스트를 추가했다. |
| `apps/agent/tests/test_static_scenario_support.py` | 차선변경, 보행자, 스쿨존 정적 보조 근거가 `family:knia` 부족을 해소하고 사고 유형 직접 근거로 잡히는지 검증한다. |

이 변경은 DB schema, Redis key, storage path, 환경 변수, 외부 API 계약을 변경하지 않는다. 실제 KNIA 원문 상세 기준이 DB에 들어오면 기존 KNIA 매칭 결과가 우선 활용되고, 정적 fixture는 검색 실패 또는 보조 근거 역할로만 사용된다.

## 2026-05-22 Agent Reflection Loop 근거 보강 표시 개선

Agent의 bounded reflection/requery 단계가 사고 유형별 한국어 검색어와 사용자용 복구 문장을 생성하도록 보강했다. 후방추돌, 차선변경, 교차로 신호위반, 보행자/스쿨존/자전거 사고 등 대표 시나리오에서 근거 부족이 감지되면 일반 영문 키워드 대신 KNIA/도로교통법 기준에 맞춘 한국어 검색어를 추가한다. 재검색 후에도 확정 조건이 남으면 `reference_only` 상태와 함께 보완 입력 또는 근거 보강 방향을 명시한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/reflection_loop.py` | `build_requery_plan()`이 `scenario_type`, `description_text`를 받아 사고 유형별 한국어 `query_terms`, `user_message`, `recovery_suggestions`를 만든다. `build_reflection_loop_result()`는 최종 상태에 맞는 사용자용 설명과 초기 재검색어를 보존한다. |
| `apps/agent/app/services/orchestration_analysis.py` | reflection requery 단계에 현재 사고 유형과 입력 설명을 전달해 재검색어가 사고 맥락을 반영하도록 연결했다. |
| `apps/gateway/src/lib/report-composer.ts` | `reflection_loop`의 내부 키를 그대로 노출하지 않고 `agent_process_card.decision_notes`로 보완 입력 항목, 부족한 근거 조건, 복구 제안을 한국어 라벨로 변환한다. |
| `apps/frontend/src/components/easy/AgentProcessCard.vue` | Agent 판단 검증 카드에서 `decision_notes`를 별도 목록으로 표시한다. |
| `apps/agent/tests/test_reflection_loop.py`, `apps/gateway/test/report-composer.test.ts` | 사고 유형별 재검색어 생성, 참고용 상태 설명, 사용자 안전 카드 변환을 검증한다. |

이 변경은 DB schema, Redis key, storage path, 환경 변수, 외부 API 계약을 변경하지 않는다. 공개 easy-report payload에는 기존 `agent_process_card` 안에 `decision_notes`가 추가된다.

## 2026-05-22 P0 보강 완료 판정

프로젝트 골격 보강 중 P0로 분류했던 Agent 신뢰성·근거 검증·실행 추적·SRP·핵심 회귀 검증 항목을 완료 상태로 정리했다. P0 완료 기준은 “새 기능 확장 전 반드시 막아야 하는 판단 신뢰성 위험을 자동 검증할 수 있고, 부족한 근거/입력은 확정 결과처럼 보이지 않게 제어되며, 사용자 화면에는 내부 trace/packet/raw key가 노출되지 않는 상태”다.

| P0 항목 | 완료 근거 |
| --- | --- |
| Agent regression automation | `scripts/verify_agent_regression.ps1`, `scripts/verify_core.ps1`, `.github/workflows/ci.yml`이 대표 사고 회귀, 내부 route contract, frontend/gateway/worker checks를 실행한다. |
| Agent execution trace | `agent_trace`, `video_input_contract`, `fact_arbitration`, `evidence_audit`, `agent_judgment`, `presentation_policy`가 결과에 남고, 관리자 진단 API와 사용자용 안전 카드가 분리되어 있다. |
| Reflection/reverification loop | 근거 부족 시 1회 bounded requery를 수행하고, 이후 `finalize`, `request_missing_input`, `present_reference_only`, `manual_review`로 상태를 분리한다. 사고 유형별 한국어 재검색어와 사용자용 복구 문장도 생성한다. |
| Agent SRP | `orchestrator.py`는 stage sequencing 중심으로 유지하고, 입력 정규화, 근거 수집, 분석 실행, reflection requery, 출력 보강은 전용 stage/service 모듈이 담당한다. |
| 실제 영상 기반 E2E smoke | `scripts/video_agent_e2e.py --video-path "C:/Users/yangbun/Downloads/car_accident_1.mp4" --timeout-sec 240` 실행 기준으로 업로드, 전처리, video_analyze job, easy-report, `agent_process_card` 안전성까지 통과했다. 기본 설정상 `ENABLE_OPENAI_FRAME_ANALYSIS=0`이므로 OpenAI 관찰값 필수 검증은 별도 옵션을 켤 때 수행한다. |

P0 이후 개발은 아래 “Reinforce Next”의 P1 항목부터 진행한다. 특화 영상 모델 교체, S3 전환, 개발자 페이지 확장, 비용 대시보드, 표준 MCP 도입은 P0 완료 범위가 아니라 후속 안정화/확장 단계다.

## 2026-05-22 실제 영상 기반 Agent E2E 점검 스크립트

실제 사고 영상을 저장소에 넣지 않고 로컬 경로로만 전달해 영상 업로드, ffmpeg 전처리, 자동 `video_analyze` job, Agent 결과, `agent_process_card` 노출 안전성까지 확인하는 E2E 스크립트를 추가했다. 사용자가 제공한 사고 영상은 테스트 실행에만 사용하고 Git에는 포함하지 않는다.

| Path | 변경 내용 |
| --- | --- |
| `scripts/video_agent_e2e.py` | 임시 로컬 계정을 생성하고 케이스 생성, `/uploads/local` 업로드, `/uploads/complete`, job polling, `/cases/{caseId}/easy-report` 검증을 수행한다. `agent_process_card`가 존재하고 raw `agent_trace`, `reflection_loop`, `packet`, 내부 step id, `next_action`이 노출되지 않는지 검사한다. `--require-frame-observations` 옵션을 사용하면 OpenAI 프레임 분석이 켜져 있고 오류 없이 1개 이상의 관찰값을 반환해야 통과한다. `--require-agent-video-facts` 옵션을 사용하면 Agent `video_input_contract`가 관찰값을 수용하고 `fact_arbitration`이 영상 기반 사실을 실제 적용해야 통과한다. |
| `docs/OPERATIONS.md` | 실제 영상 기반 E2E 실행 방법과 `ENABLE_OPENAI_FRAME_ANALYSIS=0`일 때 프레임은 추출되지만 GPT 관찰값은 0개일 수 있다는 주의 사항을 추가했다. OpenAI 관찰값 및 Agent 영상 사실 적용 필수 검증 명령도 함께 기록했다. |

실행 예시는 `python scripts/video_agent_e2e.py --video-path "C:/path/to/accident.mp4" --timeout-sec 240`이다. 이 스크립트는 DB schema, Redis key, storage path, 환경 변수, 외부 API 계약을 변경하지 않는다.

## 2026-05-22 Agent 판단 검증 상태 화면 연결

Agent P1에서 생성한 `agent_trace`와 `reflection_loop`를 일반 결과 화면에서 직접 JSON으로 노출하지 않고, Gateway가 사용자 안전 요약 카드인 `agent_process_card`로 변환해 내려주도록 보강했다. 목적은 Agent가 입력 정리, 사실 중재, 근거 검색, 주장-근거 검증, 판단 계약, 근거 보강 루프를 어떤 상태로 통과했는지 확인 가능하게 하되, raw packet, evidence id, 내부 stage id, 모델 메타데이터, 사용자 원문 입력은 일반 화면에 섞이지 않게 하는 것이다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | `composeAgentProcessCard()`를 추가했다. `agent_trace`, `reflection_loop`, `agent_judgment`를 기반으로 다음 처리 상태, 근거 재검색 여부, 추가 근거 수, 검증 단계 수, 단계별 사용자 라벨을 생성한다. `sanitizeEasyReport()`의 기술 필드 필터도 `agent_trace`, `reflection_loop`, trace packet 관련 키를 숨기도록 확장했다. |
| `apps/frontend/src/components/easy/AgentProcessCard.vue` | 결과 화면에 표시되는 Agent 판단 검증 카드다. Gateway가 만든 `agent_process_card`만 렌더링하며 raw JSON이나 내부 packet은 표시하지 않는다. |
| `apps/frontend/src/components/easy/EasyReportView.vue` | `EvidenceReliabilityCard` 다음에 `AgentProcessCard`를 표시하도록 연결했다. |
| `apps/frontend/src/utils/displaySanitizer.ts` | 일반 화면 sanitize 단계에서 raw `agent_trace`, `reflection_loop`, 재검색 내부 키가 노출되지 않도록 필터를 확장했다. |
| `apps/gateway/test/report-composer.test.ts` | `agent_process_card`가 사용자 안전 라벨만 포함하고 raw trace packet, 내부 step id, `next_action` 같은 내부 키를 노출하지 않는지 검증하는 테스트를 추가했다. |

이 변경은 DB schema, Redis key, storage path, 환경 변수, 외부 API 계약을 바꾸지 않는다. `/api/v1/cases/:caseId/easy-report` 응답의 사용자용 report payload에 `agent_process_card`가 추가된다.

## 2026-05-22 Agent P1 영상/사용자 사실 중재 계층

영상 프레임 분석 결과가 Agent 판단에 들어올 때 사용자 입력과 단순 병합하지 않고 `agent-fact-arbitration-v1` 계약으로 출처와 우선순위를 기록하도록 보강했다. 목적은 사용자가 주관적으로 잘못 입력할 수 있는 물리적 사고 사실은 고신뢰 영상 관찰값을 우선하고, 사용자가 직접 알고 있는 사고 유형/부상/보험 상태 같은 문맥 정보는 사용자 입력을 우선해 Agent 판단의 입력 근거를 명확히 남기는 것이다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/fact_arbitration.py` | 신규 `agent-fact-arbitration-v1` 모듈이다. `stopped`, `opponent_behavior`, `lane_change_actor`, 신호/횡단보도/스쿨존/손상 정도처럼 프레임에서 관찰 가능한 물리적 사실은 `video_primary`로 분류한다. `accident_type`, `injury`, 치료/보험/운전자 역할 정보는 `user_primary`로 분류한다. 충돌 시 승자, 원래 사용자 값, 영상 값, confidence, frame_refs를 `conflicts`와 `requires_confirmation`에 기록한다. |
| `apps/agent/app/services/input_normalizer.py` | 기존 `video_fact_patch + user_facts` 단순 병합을 중단하고 `arbitrate_facts()`를 거쳐 `structured_facts`를 만든다. Agent 분석 텍스트에는 영상 입력 계약과 별도로 사실 중재 계약 요약을 포함해 어떤 값이 영상에서 채택됐는지 추적할 수 있게 했다. |
| `apps/agent/app/services/report_composer.py`, `apps/agent/app/schemas.py` | Agent 결과에 `fact_arbitration`을 top-level과 `model_info.fact_arbitration`으로 포함한다. 사용자 표시용 `structured_facts`에는 `_fact_arbitration`, `_fact_sources`를 숨김 추적 정보로 함께 보관한다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | 사실 중재 계약의 내부 필드가 일반 사용자용 쉬운 보고서/프론트 화면에 원문 JSON으로 노출되지 않도록 기술 필드 필터에 추가했다. |
| `apps/agent/tests/test_fact_arbitration.py`, `apps/agent/tests/test_video_input_contract.py` | 영상 우선 물리 사실 충돌, 사용자 우선 문맥 정보 충돌, 사용자/영상 일치값 확인 처리를 검증하는 테스트 케이스를 추가했다. |

현재 정책상 정차 여부처럼 영상에서 확인 가능한 사실은 `ENABLE_OPENAI_FRAME_ANALYSIS=1`로 추출된 고신뢰 관찰값이 사용자 입력과 충돌해도 Agent 입력에서 우선된다. 반대로 부상 여부는 영상으로 정확히 판단하기 어렵기 때문에 사용자 입력이 우선된다. 이 변경은 DB schema, Redis key, storage path, 외부 API 계약을 변경하지 않으며 Agent 응답 DTO에 `fact_arbitration` 메타데이터만 추가한다.

## 2026-05-22 Worker P1 이벤트 프레임 추출 및 GPT 프레임 분석

영상 업로드 후 고정 4장만 뽑던 전처리를 짧은 사고 영상에 맞는 시간순 이벤트 프레임 추출로 보강하고, 선택적으로 OpenAI 이미지 입력 분석을 실행해 관측 가능한 사고 사실을 `observations`로 저장하도록 확장했다. GPT API는 과실비율이나 법률 판단을 하지 않고, 프레임에서 보이는 물리적 사실 후보만 JSON으로 추출한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/worker/worker/video_preprocess.py` | `frame_times_for_duration()`과 `extract_event_frames()`를 추가했다. 5초 이하는 0.5초 간격, 10초 이하는 0.75초 간격, 그 이상은 길이에 맞춰 시간순 프레임을 추출하고 최대 장수로 균등 선별한다. 추출 프레임은 `representative_frame_details`에 time_sec/role/path와 함께 저장한다. |
| `apps/worker/worker/frame_analysis.py` | `analyze_frames_with_openai()`를 추가했다. `ENABLE_OPENAI_FRAME_ANALYSIS=1`이고 `OPENAI_API_KEY`가 있을 때만 OpenAI Responses API에 프레임 이미지를 base64 data URL로 전달한다. 결과는 `openai_frame_analysis`와 `observations`에 저장하며 worker 로그에도 모델명, 프레임 수, 관측값 요약을 한 번 출력한다. |
| `apps/agent/app/services/video_input_contract.py` | OpenAI 프레임 분석 결과의 `frame_refs`와 `reason`을 Agent 영상 입력 계약에 보존한다. `source=frame_analysis:openai`는 기존 `frame_analysis` 계열 source로 처리되어 confidence 기준을 통과해야만 facts로 승격된다. |
| `compose.yaml` | worker에 `ENABLE_OPENAI_FRAME_ANALYSIS`, `OPENAI_API_KEY`, `OPENAI_VISION_MODEL`, `OPENAI_FRAME_ANALYSIS_MAX_FRAMES`, `OPENAI_FRAME_ANALYSIS_DETAIL`, `OPENAI_TIMEOUT_SEC` 환경변수 전달을 추가했다. 기본값은 비용 방지를 위해 `ENABLE_OPENAI_FRAME_ANALYSIS=0`이다. |

OpenAI 프레임 분석은 공식 OpenAI Images/Vision 및 Responses API 문서 기준의 이미지 입력 흐름을 사용한다. 이미지 입력은 비용이 발생하므로 기본은 꺼져 있으며, 활성화 시 기본 `detail=low`, 최대 8프레임으로 제한한다. 향후 교통사고 특화 모델을 도입할 경우 `analyze_frames_with_openai()` 위치를 `VideoAnalyzerProvider` 추상화로 분리해 OpenAI, ML Kit, TFLite, 사고 특화 모델을 교체 가능하게 만드는 것이 다음 구조화 단계다.

## 2026-05-22 Agent P1 영상 전처리 입력 계약 연결

영상 전처리 결과가 Agent의 일반 `video_metadata` 문자열로만 합쳐지던 흐름을 `agent-video-input-contract-v1` 계약으로 정규화했다. 현재 worker 전처리는 ffprobe/ffmpeg 기반 기술 메타데이터와 대표 프레임 추출까지 수행하므로, Agent는 이 기술 메타데이터를 사고 사실로 직접 승격하지 않는다. 향후 영상 분석/프레임 분석기가 `observations` 형태의 명시적 관측값을 넣으면, 출처와 신뢰도 기준을 통과한 항목만 `structured_facts`에 병합된다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/video_input_contract.py` | `agent-video-input-contract-v1`을 추가했다. `duration_sec`, 해상도, fps, codec, 대표 프레임 개수 같은 기술 메타데이터와 `observations` 기반 사고 관측값을 분리한다. `frame_analysis`, `vision_model`, `manual_video_review` 등 명시적 source와 `0.75` 이상의 confidence 또는 verified flag가 있는 관측값만 `fact_patch`로 승격한다. |
| `apps/agent/app/services/input_normalizer.py` | Agent 입력 정규화 시 영상 계약을 생성하고, 영상 `fact_patch`를 사용자 `structured_facts`와 병합한다. 사용자 입력 facts가 있으면 영상 추출값보다 우선한다. LLM/분석 텍스트에는 raw 영상 metadata 대신 정규화된 영상 입력 계약 요약을 포함한다. |
| `apps/agent/app/services/report_composer.py`, `apps/agent/app/schemas.py` | Agent 결과에 `video_input_contract`를 포함하고 `model_info.video_input_contract`에도 기록한다. 일반 사용자용 `structured_facts`에는 `_video_input_contract`로 숨김 메타데이터를 남겨 추적 가능성을 확보했다. |
| `apps/worker/worker/main.py` | worker 전처리 산출물에 `worker-video-preprocess-v1` 버전을 남기고, `/internal/v1/analyze/video` 호출 시 업로드 metadata와 payload video metadata를 함께 전달한다. |
| `apps/gateway/src/main.ts` | `/api/v1/cases/:caseId/analyze-video`에서 전달된 `video_metadata`를 video analyze job payload에 보존한다. |
| `docs/api/openapi.yaml` | `/cases/{caseId}/analyze-video` 요청 body에 `video_metadata`를 명시해 영상 전처리/프레임 분석 관측값 전달 계약을 문서화했다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | `video_input_contract`, 관측값 목록, `fact_patch` 같은 내부 계약 필드가 사용자 화면에 원시 JSON으로 노출되지 않도록 필터링한다. |
| `apps/agent/tests/test_video_input_contract.py`, `apps/agent/tests/test_orchestrator.py` | 고신뢰 영상 관측값이 `structured_facts`로 병합되는지, 저신뢰 관측값은 보류되는지, 순수 기술 메타데이터는 사고 사실로 승격되지 않는지 검증한다. |

현재 계약에서 사고 사실로 승격 가능한 대표 필드는 `stopped`, `sudden_brake`, `opponent_behavior`, `lane_change_actor`, `turn_signal`, `user_signal`, `opponent_signal`, `opponent_signal_violation`, `crosswalk_nearby`, `school_zone`, `injury`, `damage_level` 등이다. 이 작업은 DB schema, Redis key, 환경 변수, 외부 기관/API 연동을 변경하지 않는다. 공개 API 문서는 선택적 `video_metadata` 전달을 반영하도록 보강했다. 다음 Agent P1 작업은 이 계약을 기반으로 실제 프레임/비전 분석 모듈을 붙일지, 또는 현재 로컬 ffmpeg 전처리만 유지하고 사용자 보완 입력 중심으로 갈지 결정하는 단계다.

## 2026-05-22 Agent P1 보완 질문 루프 고도화

보완 질문 답변을 프론트 임시 매핑에만 의존하지 않고 Gateway에서 서버 기준으로 정규화하며, Agent가 재분석 반복 상태와 종료 사유를 결과에 남기도록 보강했다. 이 변경은 기존 `/api/v1/cases/:caseId/reanalyze` 흐름을 확장하며 DB schema, Redis key, 환경 변수, 외부 API 계약은 변경하지 않는다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/followup-normalizer.ts` | 사용자 보완 답변을 canonical `structured_facts` patch로 변환한다. 예: `다친 사람 없음 -> injury=false`, `상대 차량 -> opponent_lane_change=true`, `적색 -> red`, `확인 중 -> unresolved field`로 정규화한다. `_followup_iteration`, `_followup_answered_fields`, `_followup_unresolved_fields` 메타데이터도 함께 생성한다. |
| `apps/gateway/src/main.ts` | `/api/v1/cases/:caseId/reanalyze`에서 `followup_answers`를 받아 서버 정규화 결과를 기존 케이스 facts와 병합한 뒤 Agent에 전달한다. 기존 `structured_facts` payload도 계속 허용한다. |
| `apps/frontend/src/api/client.ts`, `apps/frontend/src/views/CaseResultView.vue` | 결과 화면의 보완 답변 제출 시 기존 `structured_facts`와 함께 원본 `followup_answers`도 Gateway에 전달해 서버 정규화가 항상 실행되도록 했다. |
| `apps/agent/app/services/input_requirements.py` | `agent-followup-loop-v1`을 추가했다. 남은 blocking/optional 질문 수, 반복 횟수, 답변/미확인 필드, `complete`, `waiting_for_input`, `continue`, `optional_followup_available`, `stopped` 상태와 종료 사유를 산정한다. 후방추돌 문맥에서 `정차`, `뒤에서 추돌`이 문장에 있으면 정차 여부와 상대 행동을 반복 질문하지 않도록 만족 판정을 보강했다. |
| `apps/agent/app/services/orchestrator.py`, `apps/agent/app/services/report_composer.py`, `apps/agent/app/schemas.py` | Agent 최종 결과에 `followup_loop`를 포함하고 `model_info.followup_loop`에도 기록한다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | `followup_loop` 내부 메타데이터가 일반 사용자 리포트에 원시 필드로 노출되지 않도록 필터링한다. |
| `apps/gateway/test/followup-normalizer.test.ts`, `apps/agent/tests/test_input_requirements.py` | 보완 답변 정규화, 미확인 답변 처리, 반복 횟수 증가, blocking 질문 해소/최대 반복 도달 상태를 검증한다. |

보완 루프 상태 의미:

| 상태 | 의미 |
| --- | --- |
| `waiting_for_input` | 첫 보완 답변을 기다리는 상태 |
| `continue` | 필수 질문이 아직 남아 추가 보완이 필요한 상태 |
| `optional_followup_available` | 확정 판단을 막는 필수 질문은 해소됐고 선택 보완 질문만 남은 상태 |
| `complete` | 남은 보완 질문이 없는 상태 |
| `stopped` | 최대 보완 반복 횟수에 도달해 더 이상 질문을 늘리지 않는 상태 |

현재 최대 반복 횟수는 Agent 내부 상수 `MAX_FOLLOWUP_ITERATIONS=3`이다.

## 2026-05-22 Agent P1 LLM/fallback 책임 분리

Agent P1 첫 단계로 LLM이 판단 수치나 근거 존재 여부를 임의로 결정하지 못하도록 섹션별 LLM 사용 정책을 추가했다. 이 변경은 외부 도구를 새로 도입하지 않고 기존 `OPENAI_API_KEY`, `ENABLE_OPENAI_ANALYSTS` 기반 호출 흐름에 정책 게이트와 결과 메타데이터를 더하는 방식이다. DB schema, Redis key, 환경 변수 이름, 외부 API 계약은 변경하지 않았다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/llm_policy.py` | `llm-policy-v1`을 추가했다. traffic law, fault ratio, criminal liability, insurance, action plan, final report 섹션별로 LLM 허용 조건, 필요한 근거군, LLM이 생성해도 되는 출력, 결정론적 로직이 우선하는 출력 필드를 정의한다. |
| `apps/agent/app/services/analysts/traffic_law_analyst.py` | 법률 근거가 있을 때만 LLM 보조 해석을 허용하고, 적용 법규와 판단 상태는 근거/guard가 우선하도록 `llm_usage`와 `analysis_source`를 남긴다. |
| `apps/agent/app/services/analysts/fault_ratio_analyst.py` | KNIA 근거가 없으면 과실비율 LLM 호출을 차단한다. 과실 수치, 사용자 관점 변환, KNIA 산정값은 결정론적 로직과 KNIA 산정기가 우선한다. |
| `apps/agent/app/services/analysts/criminal_liability_analyst.py` | 법률 근거가 있을 때만 형사책임 체크리스트 보조 생성을 허용하고, 신고 필요 여부와 위험도는 guard와 입력 사실 중심으로 유지한다. |
| `apps/agent/app/services/analysts/insurance_analyst.py`, `apps/agent/app/services/analysts/action_plan_analyst.py` | LLM은 절차 안내와 행동 목록 보조에만 사용하고, 보상금액이나 책임 확정 표현을 생성하는 역할로 쓰지 않는다. |
| `apps/agent/app/services/report_composer.py` | 최종 리포트 LLM 호출도 요약 전용 정책을 통과할 때만 실행한다. `model_info.llm_policy`에 섹션별 LLM 허용/사용/차단 사유를 기록한다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | `llm_usage`, `llm_policy`, `analysis_source` 등 내부 정책 필드가 일반 사용자 화면에 원시 JSON으로 노출되지 않도록 필터링한다. |
| `apps/agent/tests/test_llm_policy.py`, `apps/agent/tests/test_orchestrator.py` | KNIA 근거가 없는 과실비율 LLM 호출 차단, 법률 근거가 있는 법률 분석 허용, Agent 결과의 `model_info.llm_policy` 포함 여부를 검증한다. |

정책의 핵심은 다음과 같다.

| 섹션 | LLM 허용 범위 | 결정론적 우선 영역 |
| --- | --- | --- |
| 법률 분석 | 검색된 법률 근거의 쉬운 해석, 위험 플래그, 추가 확인 사실 정리 | 적용 법규 존재 여부, 근거 ID, 판단 상태 |
| 과실비율 | KNIA 근거가 있을 때 설명과 key factor 보조 | `my/other` 수치, KNIA 기준 매칭, 사용자 차량 역할, KNIA 가감요소 산정 |
| 형사책임 | 법률 근거 기반 체크리스트 보조 | 신고 필요 여부, 형사 리스크 등급, 판단 상태 |
| 보험 안내/행동 계획 | 절차 안내와 필요 서류, 행동 순서 보조 | 보상금액 확정, 책임 확정, 과실 판단 |
| 최종 리포트 | 이미 검증된 섹션을 쉬운 문장으로 요약 | 과실, 법률책임, 근거, Agent 판단 계약 |

현재 LLM은 `ENABLE_OPENAI_ANALYSTS=1`이고 `OPENAI_API_KEY`가 있을 때만 후보가 되며, 각 섹션의 필수 근거군이 부족하면 deterministic fallback으로 내려간다. 이 단계 이후 P1의 다음 작업은 보완 질문 답변을 반복 분석 루프에서 정규화하고 종료 조건을 명확히 하는 것이다.

## 2026-05-21 Agent P0 판단 골격 보강

Agent 레이어의 P0 골격을 보강하여 “입력 부족”, “근거 부족”, “KNIA 기준 부족”, “확정 판단 불가”가 하나의 `needs_review` 상태로 뭉개지지 않도록 판단 계약을 세분화했다. 이 변경은 Agent/Gateway/Frontend 표시 필터와 테스트만 수정하며, DB schema, Redis key, 환경 변수, 외부 API 계약은 변경하지 않았다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/judgment_contract.py` | 판단 계약 버전을 `agent-judgment-contract-v2`로 올리고 `decision_blockers`, `decision_readiness`, `knia_basis`, `knia_fault_basis` stage를 추가했다. 사고 유형별 KNIA 필요 여부, 대표 KNIA 기준, 기본과실/최종과실 존재 여부, 적용/제외된 가감요소 수, 누락 사유를 추적한다. |
| `apps/agent/app/services/orchestrator.py` | KNIA 매칭 결과와 KNIA 과실 산정 결과를 판단 계약 생성 단계에 전달해 Agent 최종 결과의 판단 가능 여부가 KNIA 기준 상태까지 반영하도록 연결했다. |
| `apps/gateway/src/lib/report-composer.ts` | 재분석 비교 카드가 KNIA 기본과실, 가감 후 과실, 적용된 가감요소 수, 추가/제외된 가감요소를 사용자용 문구로 비교하도록 확장했다. 새 내부 계약 필드(`decision_blockers`, `decision_readiness`, `knia_basis`)는 일반 리포트에 노출하지 않는다. |
| `apps/frontend/src/utils/displaySanitizer.ts` | 새 Agent 내부 계약 필드가 화면에 원시 JSON이나 내부 코드로 노출되지 않도록 기술 필드 목록에 추가했다. |
| `apps/agent/tests/test_judgment_contract.py` | 입력 부족, 근거 부족, KNIA 기준 부족이 각각 별도 blocker category로 기록되는지와 KNIA 가감요소 basis가 계약에 포함되는지 검증한다. |
| `apps/gateway/test/report-composer.test.ts` | 재분석 비교 카드가 KNIA 가감요소 변화를 표시하면서 내부 판단 계약과 raw evidence id를 노출하지 않는지 검증한다. |

새 판단 계약의 핵심 필드는 다음과 같다.

| 필드 | 의미 |
| --- | --- |
| `agent_judgment.decision_blockers` | 판단을 보류하거나 확정 표시를 막는 사유 목록. category는 `input_missing`, `evidence_missing`, `knia_missing`, `claim_unsupported`, `stage_unsupported`, `stage_review`로 구분한다. |
| `agent_judgment.decision_readiness` | 사용자에게 보여줄 수 있는 판단 준비 상태. `판단 가능`, `추가 확인 필요`, `확정 판단 불가` 중 하나의 label과 blocker category 요약을 포함한다. |
| `agent_judgment.knia_basis` | KNIA 기준 필요 여부, 대표 기준번호, 기본/최종 과실, 적용/제외 가감요소 수, KNIA 누락 사유를 포함한다. |
| `stage_statuses[].name = knia_fault_basis` | KNIA 과실 산정 근거가 Agent 판단 단계에서 별도 stage로 추적된다. |

현재 이 단계는 Agent 판단 구조를 단단히 만드는 P0 작업이며, 이후 P1에서는 LLM/fallback 책임 분리, 보완 질문 루프 고도화, 영상 분석 입력 계약 연결을 진행할 수 있다.

## 2026-05-21 재분석 전후 판단 비교 카드 추가

보완 입력이 실제 Agent 판단에 어떤 변화를 만들었는지 추적하기 위해, 직전 분석 결과와 새 재분석 결과를 Gateway에서 비교해 사용자용 `analysis_change_card`를 생성하도록 보강했다. 이 변경은 기존 `analysis_results.elderly_friendly_report` JSON에 비교 카드를 저장하는 방식이며, DB schema, Redis key, 환경 변수, 외부 API 연동은 변경하지 않았다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | `composeReanalysisChangeCard(previous, next)`를 추가했다. 사고 유형, 과실비율, 근거 충족도, 판단 상태, 남은 보완 질문 수를 직전 분석과 새 분석 기준으로 비교하고, 내부 `agent_judgment` 원문 값은 사용자 화면에 노출하지 않는 한국어 요약 카드로 변환한다. |
| `apps/gateway/src/main.ts` | `/api/v1/cases/:caseId/reanalyze`가 재분석 전 최신 `analysis_results.result`를 조회한 뒤 새 Agent 결과와 비교하여 `analysis_change_card`를 포함한 easy report를 저장 및 반환하도록 변경했다. |
| `apps/frontend/src/components/easy/AnalysisChangeCard.vue` | 결과 화면에 재분석 비교 카드 UI를 추가했다. 현재 과실비율, 근거 충족도, 남은 질문 수, 변경된 판단 항목을 보여준다. |
| `apps/frontend/src/components/easy/EasyReportView.vue` | easy report에 `analysis_change_card`가 있으면 상단 결론과 근거 검증 카드 사이에 표시하도록 연결했다. |
| `apps/gateway/test/report-composer.test.ts` | 재분석 비교 카드가 과실비율과 남은 질문 수 변화를 표시하면서 내부 판단 상태 원문을 노출하지 않는지 검증한다. |

2026-05-21 추가 보강: `analysis_change_card`는 대표 KNIA 기준, 전체/관련/KNIA 근거 수, 법률/KNIA/기타 근거 구성, 부족한 근거 조건 수까지 함께 비교한다. 또한 직전 분석 대비 새로 반영된 근거와 이번 결과에서 빠진 근거를 사용자용 제목, 출처 라벨, 근거 유형 라벨 기준으로 보여준다. Frontend의 `AnalysisChangeCard.vue`는 긴 KNIA 기준명도 깨지지 않도록 반응형 통계 그리드, 근거 메모 목록, 근거 변경 목록을 표시한다.

이 단계부터 보완 입력 후 결과 화면은 “답변을 반영했다”에서 끝나지 않고, 직전 분석 대비 무엇이 달라졌는지와 근거/KNIA 기반이 얼마나 보강됐는지 함께 확인할 수 있다. Agent 판단 검증 체계 관점에서는 이후 동일 카드에 KNIA 가감요소 적용 변화까지 확장할 수 있다.

작성 기준: `C:/Users/yangbun/Desktop/프로젝트 정리.txt`의 5개 분석 항목을 기준으로, 현재 저장소의 파일 구조와 소스 코드를 역분석한 초안이다. 민감 정보는 실제 값이 아니라 환경변수 이름만 기록한다.

## 1. 기본 식별 정보

### 프로젝트 개요

| 항목 | 내용 |
| --- | --- |
| 프로젝트명 | LawCompass |
| 목적 | 교통사고 상황을 입력받아 법률 근거, 과실비율, 보험/형사 리스크, 행동 가이드를 제공하는 AI 분석 MVP |
| 구조 | 단일 저장소 모노레포 |
| 실행 기준 | Docker Compose 기반 단일 서버 배포 |
| 주요 런타임 | Vue 3, Vite, Fastify, FastAPI, Redis, PostgreSQL, pgvector |
| 최초/현재 담당자 | 저장소 내 명시 정보 없음 |

### 기준 문서 체계

| 파일 | 역할 |
| --- | --- |
| `AGENTS.md` | 에이전트가 개발/점검/문서 작업 전에 우선 읽는 진입 지침. `DEVELOPMENT_PROMPT.md`와 `SYSTEM_OVERVIEW.md`를 먼저 참조하도록 안내 |
| `DEVELOPMENT_PROMPT.md` | 개발 요청 처리 전 우선 읽는 LawCompass 전담 Principal Software Architect 작업 원칙 문서. 역할, 작업 순서, 보안, 검증, 문서 동기화 규칙을 정의 |
| `SYSTEM_OVERVIEW.md` | 프로젝트 구조, 핵심 파일, 리소스 연동, 완성도, To-Do를 기록하는 인수인계 기준 문서 |
| `README.md` | 프로젝트 요약과 빠른 시작 절차 |
| `docs/OPERATIONS.md` | 운영 절차, 외부 API 점검, E2E 스모크 테스트 안내 |
| `docs/api/openapi.yaml` | 공개 API 명세 |
| `docs/STACK_DECISION_REVIEW.md` | 초기 기술 스택 계획안과 현재 적용 스택을 비교하고 향후 도입 판단 기준을 기록한 기술 의사결정 참고 문서 |
| `docs/PROJECT_BASELINE_2026-05-21.md` | 2026-05-21 기준 인수 직전 구현 상태를 고정 기록한 베이스라인 스냅샷. 이후 개발 변화 비교의 기준 |

문서 최신화 원칙:

1. 개발로 인해 서비스 구조, API route, DTO, DB schema, Redis key, storage path, 외부 API, 환경변수, 실행 방법, known issue가 바뀌면 `SYSTEM_OVERVIEW.md`를 함께 업데이트한다.
2. 개발 원칙, 검증 방식, 문서 동기화 규칙, 서비스 책임 경계, 보안 기준이 바뀌면 `DEVELOPMENT_PROMPT.md`를 업데이트한다.
3. `.env`, API key, JWT secret, 내부 서비스 토큰, 사용자 비밀번호 등 민감값은 문서에 실제 값으로 기록하지 않는다.
4. 외부 도구, 모듈, SDK, AI 모델, 영상 분석 도구, 공공/기관 API를 새로 도입하거나 교체할 때는 2026-05-20 이후의 최신 공식 근거, 유지보수 상태, 비용, 라이선스, 리소스 사용량, 프로젝트 적합성을 확인한다.

### 상위 폴더 역할

| 경로 | 역할 및 목적 |
| --- | --- |
| `apps/frontend` | 사용자 웹 화면. 로그인, 케이스 생성, 영상 업로드, 분석 결과, KNIA 기준 조회, AI 채팅 UI 제공 |
| `apps/gateway` | 외부 API 게이트웨이. 인증/세션, 케이스/업로드/분석 API, DB 접근, Redis rate limit, Agent 호출 담당 |
| `apps/agent` | 내부 AI 분석 서비스. 사고 분석, 법률 RAG, KNIA 매칭, 채팅 오케스트레이션, 외부 법률/공공 API 호출 담당 |
| `apps/worker` | 비동기 작업 처리. Redis Streams에서 영상 전처리/분석 작업을 소비하고 ffmpeg/ffprobe 및 Agent 호출 수행 |
| `infra/postgres/migrations` | PostgreSQL, pgvector, 업무 테이블, 인덱스, 트리거 정의 |
| `infra/caddy` | Caddy reverse proxy 및 보안 헤더 설정 |
| `config` | KNIA 수집 범위 등 실행 설정 JSON |
| `scripts` | 로컬 E2E, KNIA 스크래핑/JSON 자료, 보조 스크립트 |
| `docs` | 운영 절차 및 OpenAPI 문서 |
| `storage` | 로컬 업로드 파일, 프레임 추출 결과, 테스트 산출물 저장소 |
| `sample_data` | 샘플 영상/사고 JSON |
| `docs/STACK_DECISION_REVIEW.md` | 초기 설계 스택과 현재 적용 스택의 차이, 향후 도입 후보, 기술 선택 판단 기준 문서 |
| `docs/PROJECT_BASELINE_2026-05-21.md` | 인수 직전 현재 구현 상태를 고정 기록한 비교용 베이스라인 문서 |

### 서비스 구성

| 서비스 | 컨테이너/포트 | 주요 책임 |
| --- | --- | --- |
| `edge` | Caddy, host `80/443` | `/api/*`, `/health`, `/ready`를 gateway로 프록시하고 나머지는 frontend로 프록시 |
| `frontend` | 내부 `5173` | Vite preview 서버로 정적 프론트 제공 |
| `gateway` | 내부 `3000` | 공개 API, 인증, DB/Redis 접근, Agent 내부 호출 |
| `agent` | 내부 `8000` | `/internal/v1/*` 분석/수집/검색 내부 API 제공 |
| `worker` | 포트 없음 | Redis Stream 기반 백그라운드 작업 처리 |
| `postgres` | 내부 `5432` | 업무 데이터와 벡터 검색 데이터 저장 |
| `redis` | 내부 `6379` | rate limit, 작업 큐, 작업 상태 캐시 |

## 2. 기능 및 로직 명세

### Frontend

핵심 파일:

| 파일 | 역할 |
| --- | --- |
| `apps/frontend/src/main.ts` | Vue 앱, Pinia, Router 부트스트랩 |
| `apps/frontend/src/router/index.ts` | 로그인 필요 화면 보호 및 라우팅 |
| `apps/frontend/src/api/client.ts` | Gateway API 호출 래퍼와 프론트 DTO 정의 |
| `apps/frontend/src/stores/session.ts` | 세션 부트스트랩, 로그인 상태 관리 |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | 케이스 상세 화면의 입력, 업로드, 분석 요청, job polling 상태 관리 |
| `apps/frontend/src/views/*.vue` | 로그인, 대시보드, 케이스 생성/상세/결과, KNIA 화면 |
| `apps/frontend/src/components/chat/*` | AI 사고 상담 패널, 메시지, 초안 케이스, KNIA 매칭 카드 |
| `apps/frontend/src/components/knia/*` | KNIA 순위, 기준, 미디어, JSON 검색 UI |
| `apps/frontend/src/components/easy/*` | 고령자 친화 리포트 표시 컴포넌트 |
| `apps/frontend/src/components/easy/EvidenceReliabilityCard.vue` | Agent 판단과 근거 문서의 연결 상태를 사용자용 카드로 표시 |

주요 화면 라우트:

| 경로 | 컴포넌트 | 인증 |
| --- | --- | --- |
| `/` | `DashboardView` | 필요 |
| `/login` | `LoginView` | 불필요 |
| `/signup` | `SignupView` | 불필요 |
| `/cases/new` | `CaseCreateView` | 필요 |
| `/cases/:caseId` | `CaseDetailView` | 필요 |
| `/cases/:caseId/wizard` | `AccidentWizardView` | 필요 |
| `/cases/:caseId/result` | `CaseResultView` | 필요 |
| `/evidence/:chunkId` | `EvidenceDetailView` | 필요 |
| `/knia/ranking` | `KniaRankingView` | 필요 |
| `/knia/charts/:chartNo` | `KniaChartView` | 필요 |

프론트 주요 DTO:

| DTO | 필드 요약 |
| --- | --- |
| `User` | `id`, `email`, `role`, `display_name` |
| `AccidentFacts` | 사고 유형, 어린이보호구역, 보행자/자전거/차대차, 신호, 차선 변경, 날씨, 피해 정도 등 |
| `CaseItem` | `id`, `title`, `description_text`, `status`, `structured_facts`, `selected_keywords`, `analysis_mode`, `created_at` |
| `UploadItem` | `id`, `file_name`, `content_type`, `file_size_bytes`, `status`, `storage_provider`, `metadata`, `created_at` |

### Gateway

핵심 파일:

| 파일 | 역할 |
| --- | --- |
| `apps/gateway/src/main.ts` | Fastify 앱 엔트리포인트. 인증, 케이스, 업로드, 분석, KNIA, 관리자 API 대부분을 정의 |
| `apps/gateway/src/routes/chat.ts` | AI 채팅 세션/메시지/빠른 상담 API |
| `apps/gateway/src/services/chatService.ts` | 채팅 세션 저장, Agent 채팅 호출, 메시지 저장 |
| `apps/gateway/src/lib/internal-client.ts` | 내부 Agent POST 호출 및 재시도 |
| `apps/gateway/src/lib/errors.ts` | 표준 오류 응답 envelope, validation 오류 정규화 |
| `apps/gateway/src/lib/report-composer.ts` | 분석 결과를 클라이언트 리포트/쉬운 리포트 형태로 조립하고 `claim_evidence`를 사용자용 근거 연결 상태 카드로 요약 |
| `apps/gateway/src/lib/security.ts` | 민감값 마스킹, 해시 유틸리티 |
| `apps/gateway/src/lib/ai-router.ts` | 영상 분석용 AI 라우팅 결정 |
| `apps/gateway/src/storage/provider.ts` | 로컬 업로드 저장소 구현. S3 저장소 인터페이스는 있으나 현재 미활성 |

공개 API 책임:

| API 그룹 | 대표 경로 | 책임 |
| --- | --- | --- |
| 상태 | `GET /health`, `GET /ready` | 프로세스, DB, Redis 준비 상태 확인 |
| 인증 | `/api/v1/auth/signup`, `/login`, `/refresh`, `/logout`, `/me` | 이메일 기반 회원가입/로그인, JWT access cookie, refresh token 회전 |
| 케이스 | `/api/v1/cases` | 사고 케이스 생성, 조회, 수정 |
| 업로드 | `/api/v1/uploads/*` | 로컬 영상 업로드, 완료 처리, 조회, 재생/다운로드 URL |
| 분석 | `/api/v1/cases/:caseId/analyze-text`, `/analyze-video`, `/result`, `/report`, `/easy-report` | Agent 호출 또는 작업 큐 등록, 분석 결과 조회 |
| 증거 | `/api/v1/cases/:caseId/evidence`, `/api/v1/legal/evidence/:chunkId` | 법률 근거 chunk 조회 |
| KNIA | `/api/v1/knia/*` | 과실비율 순위, 기준 상세, 매칭, 추정, JSON/미디어 검색 |
| 관리자 | `/api/v1/admin/*` | 법률 KB 적재, 임베딩 재생성, KNIA 수집/임포트/캐시 무효화 |
| 채팅 | `/api/v1/chat/*` | AI 사고 상담 세션 및 메시지 |

Gateway 주요 로직:

| 로직 | 설명 |
| --- | --- |
| 인증 | `lc_at`, `lc_rt` HTTP-only cookie 사용. access token은 JWT, refresh token은 DB에 해시 저장 |
| 권한 | 일반 API는 `requireUser`, 관리자 API는 `requireAdmin` 사용. 관리자 권한은 사용자 role `admin` 또는 `INTERNAL_ADMIN_TOKEN` 헤더 매칭 |
| rate limit | Redis에 분 단위 route key를 기록해 90회 초과 시 제한 |
| idempotency | `Idempotency-Key`를 해시해 중복 POST/PATCH/DELETE 응답 재사용 |
| Agent 호출 | `INTERNAL_AGENT_URL`, `INTERNAL_SERVICE_TOKEN`으로 내부 FastAPI 호출 |
| 업로드 | `LocalStorageProvider`가 `storage/uploads/{caseId}/{uploadId}/original.ext`에 영상 저장 |

### Agent

핵심 파일:

| 파일 | 역할 |
| --- | --- |
| `apps/agent/app/main.py` | FastAPI 앱 엔트리포인트 |
| `apps/agent/app/routers/internal.py` | 내부 전용 `/internal/v1/*` API composition router |
| `apps/agent/app/routers/internal_auth.py` | 내부 API `INTERNAL_SERVICE_TOKEN` guard |
| `apps/agent/app/routers/internal_routes/analysis.py` | `/analyze/*` text/video/scenario analysis routes |
| `apps/agent/app/routers/internal_routes/jobs.py` | `/jobs/process` worker job route |
| `apps/agent/app/routers/internal_routes/legal.py` | `/legal/*` legal KB ingest/rebuild/retrieval test routes |
| `apps/agent/app/routers/internal_routes/chat.py` | `/chat/message` accident consultation route |
| `apps/agent/app/routers/internal_routes/knia.py` | `/knia/*` collection, matching, fault estimate, JSON/search routes |
| `apps/agent/app/routers/internal_routes/cache.py` | `/cache/invalidate` semantic cache invalidation route |
| `apps/agent/app/routers/internal_routes/health.py` | unauthenticated `/health` route |
| `apps/agent/app/schemas.py` | Pydantic 요청/응답 모델 |
| `apps/agent/app/services/orchestrator.py` | 사고 분석 파이프라인 총괄 |
| `apps/agent/app/services/analyst_output_contracts.py` | 법률/과실/형사/보험 분석가 출력의 Pydantic 계약 모델 |
| `apps/agent/app/services/analyst_output_guard.py` | 법률/과실/형사/보험 분석가 출력에 근거 충분성, caveat, 신뢰도 상한을 적용하는 공통 가드 |
| `apps/agent/app/services/claim_evidence_validator.py` | Agent 분석 결과의 주요 판단과 근거 문서를 연결하고 근거 누락 판단을 `evidence_audit`에 반영 |
| `apps/agent/app/services/elderly_friendly/plain_language_agent.py` | 쉬운 리포트 문장 생성. analyst 근거 상태가 약하면 과실/법률/보험 문장을 확정 표현 대신 추가 확인 표현으로 완화 |
| `apps/agent/app/services/scenario_classifier.py` | 사고 유형 및 당사자 유형 분류 |
| `apps/agent/app/services/analysts/*` | 과실비율, 형사 책임, 보험, 행동 계획, 법규 분석 |
| `apps/agent/app/services/legal/*` | 법률 문서 수집, chunking, vectorizing, evidence retrieval |
| `apps/agent/app/services/knia/*` | KNIA 수집, 파싱, 저장소, 매칭, 벡터화, JSON import |
| `apps/agent/app/services/chat/*` | AI 사고 상담 의도 분류, 응답 생성, 초안 케이스 생성 |
| `apps/agent/app/mcp/*` | 내부 tool registry/executor 및 KNIA/RAG/cache 도구 |

Agent 내부 API:

| 경로 | 책임 |
| --- | --- |
| `GET /internal/v1/health` | Agent 상태 확인 |
| `POST /internal/v1/analyze/text` | 텍스트 사고 분석 |
| `POST /internal/v1/analyze/video` | 영상 전처리 요약 기반 사고 분석 |
| `POST /internal/v1/analyze/scenario` | 구조화 시나리오 분석 |
| `POST /internal/v1/legal/ingest` | 교통 법률 KB 수집/적재 |
| `POST /internal/v1/legal/rebuild-embeddings` | KB chunk 임베딩 생성 |
| `GET /internal/v1/legal/retrieval-test` | 법률 검색 테스트 |
| `POST /internal/v1/chat/message` | AI 사고 상담 처리 |
| `POST /internal/v1/knia/*` | KNIA 수집, 매칭, 과실 추정, JSON import, 임베딩 재생성 |
| `POST /internal/v1/cache/invalidate` | KNIA JSON 캐시 무효화 |

Agent 주요 DTO:

| 모델 | 필드 요약 |
| --- | --- |
| `AnalyzeTextRequest` | `case_id`, `user_id`, `description_text`, `structured_facts`, `selected_keywords`, `analysis_mode`, `ai_profile`, `specialist_roles` |
| `AnalyzeVideoRequest` | `case_id`, `user_id`, `upload_id`, `preprocessed_summary`, `video_metadata`, `structured_facts`, `selected_keywords`, `analysis_mode` |
| `EvidenceItem` | `chunk_id`, `title`, `source`, `score`, `snippet`, `law_name`, `article_title`, `plain_summary`, `source_url`, `source_type` |
| `AnalysisOutput` | 사고 요약, 시나리오, 법률 분석, 과실비율, 보험/형사 가이드, 근거, KNIA 매칭, 불확실성, 후속 질문, 모델 정보, 쉬운 리포트 |
| Analyst output contracts | `TrafficLawAnalysisOutput`, `FaultRatioAnalysisOutput`, `CriminalLiabilityAnalysisOutput`, `InsuranceAnalysisOutput`. 각 analyst 결과를 Pydantic으로 정규화하고 공통 guard fields를 포함 |
| Analyst output guard fields | `legal_analysis`, `fault_ratio`, `legal_liability`, `insurance_guide` 내부의 `evidence_support_level`, `judgment_status`, `required_evidence_family`, `evidence_count`, `evidence_ids`, `used_evidence_ids`, `caveats`. 직접 근거 부족 시 확정 표현을 피하도록 경고하고 과실비율 `confidence`를 제한 |
| `claim_evidence` | Agent 주요 판단별 근거 연결 상태, 지원 수준, 미지원 판단, 근거 커버리지 |

### Worker

핵심 파일:

| 파일 | 역할 |
| --- | --- |
| `apps/worker/worker/main.py` | Redis Streams Consumer Group 기반 작업 루프 |

작업 흐름:

1. `jobs:v1:stream`에서 `video_preprocess`, `video_analyze` 작업 수신
2. `video_preprocess`에서 `ffprobe`로 영상 메타데이터 확인
3. `ffmpeg`로 대표 프레임 4장을 `storage/frames/{caseId}/{uploadId}`에 추출
4. 업로드 상태를 `processing`에서 `ready`로 갱신
5. 후속 `video_analyze` job을 DB와 Redis Stream에 등록
6. `video_analyze`에서 Agent `/internal/v1/analyze/video` 호출
7. `analysis_results`에 결과 저장 후 `cases.latest_result_id`, `cases.status` 갱신

### 핵심 파일 상세 명세

이 섹션은 인수인계 시 코드를 직접 열어보지 않아도 주요 파일의 역할, 입출력, 호출 관계, 리소스 접근 범위를 빠르게 파악하기 위한 파일 단위 명세다. 작성자/담당자는 저장소 내 명시 정보가 없어 `저장소 내 명시 없음`으로 기록한다.

#### 핵심 파일 식별 정보

| Path | Name & Type | Purpose Overview | Owner/Author |
| --- | --- | --- | --- |
| `compose.yaml` | Docker Compose 서비스 정의 | 전체 MSA 구성, 네트워크, 볼륨, 헬스체크, 환경변수 주입 규칙을 정의한다 | 저장소 내 명시 없음 |
| `infra/caddy/Caddyfile` | Edge reverse proxy 설정 | `/api/*`, `/health`, `/ready`를 Gateway로 전달하고 프론트 정적 서비스를 프록시한다 | 저장소 내 명시 없음 |
| `infra/postgres/migrations/001_init.sql` | DB 초기 스키마 | 인증, 케이스, 업로드, 작업, 분석 결과, KB, 감사/멱등성의 기본 테이블과 확장을 만든다 | 저장소 내 명시 없음 |
| `apps/frontend/src/main.ts` | Frontend bootstrap | Vue 앱에 Pinia와 Router를 연결해 화면 앱을 시작한다 | 저장소 내 명시 없음 |
| `apps/frontend/src/router/index.ts` | Frontend router/guard | 화면 라우팅과 인증 필요 페이지 접근 제어를 담당한다 | 저장소 내 명시 없음 |
| `apps/frontend/src/api/client.ts` | Frontend API client/DTO | Gateway API 호출 함수와 프론트 타입 정의를 제공한다 | 저장소 내 명시 없음 |
| `apps/frontend/src/stores/session.ts` | Pinia session store | 사용자 세션 복원, 로그인, 로그아웃, refresh 흐름을 관리한다 | 저장소 내 명시 없음 |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | Vue case workspace composable | 케이스 상세 화면의 API 상태, 입력 저장, 업로드, 전처리, 분석 요청, job polling을 관리한다 | 저장소 내 명시 없음 |
| `apps/frontend/src/views/CaseDetailView.vue` | Frontend case workspace view | 케이스 상세 화면의 페이지 흐름을 조립하고 상태 composable과 섹션 컴포넌트를 연결한다 | 저장소 내 명시 없음 |
| `apps/frontend/src/components/case/*.vue` | Frontend case workspace components | 케이스 헤더, 요약, 사고 입력, 영상 업로드, 분석 요청 섹션을 표시 전용 책임으로 분리한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/main.ts` | Fastify API entrypoint/controller | 공개 API 대부분과 인증, rate limit, idempotency, DB/Redis/Agent 연동을 담당한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/routes/chat.ts` | Fastify chat router | 채팅 세션 생성, 메시지 조회/전송, 빠른 상담 API를 등록한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/services/chatService.ts` | Chat domain service | 채팅 세션/메시지를 DB에 저장하고 Agent 채팅 API를 호출한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/lib/internal-client.ts` | Internal HTTP client | Gateway에서 Agent 내부 POST API를 timeout/retry 포함해 호출한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/lib/errors.ts` | Gateway error formatter | `error.code/message/trace_id` 표준 응답을 만들고 Fastify validation 오류를 400 응답으로 정규화한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/storage/provider.ts` | Storage abstraction | 로컬 영상 업로드 저장을 구현하고 S3 provider 인터페이스를 남겨둔다 | 저장소 내 명시 없음 |
| `apps/agent/app/main.py` | FastAPI app entrypoint | Agent 앱을 생성하고 internal router를 등록한다 | 저장소 내 명시 없음 |
| `apps/agent/app/routers/internal.py` | FastAPI internal router composition root | `/internal/v1` prefix를 가진 domain router들을 조립한다 | 저장소 내 명시 없음 |
| `apps/agent/app/routers/internal_auth.py` | FastAPI internal auth helper | 내부 token guard를 라우터별로 공유한다 | 저장소 내 명시 없음 |
| `apps/agent/app/routers/internal_routes/*.py` | FastAPI domain route modules | 분석, job, 법률, KNIA, 채팅, 캐시, health 내부 API를 책임별 파일로 제공한다 | 저장소 내 명시 없음 |
| `apps/agent/app/schemas.py` | Pydantic DTO schema | 분석 요청/응답과 근거 item 모델을 정의한다 | 저장소 내 명시 없음 |
| `apps/agent/app/services/orchestrator.py` | Analysis orchestration service | 사고 분석 전체 파이프라인을 조립하고 최종 `AnalysisOutput` payload를 만든다 | 저장소 내 명시 없음 |
| `apps/agent/app/services/orchestration_output.py` | Analysis output enrichment service | 판단 계약, 재검증 루프, 실행 trace, KNIA 계산 메타데이터, 사용자용 리포트를 최종 출력에 부착한다 | 저장소 내 명시 없음 |
| `apps/agent/app/services/analyst_output_contracts.py` | Analyst output contract schema | 분석가별 출력 모델을 Pydantic으로 정의하고 LLM/fallback 결과의 타입을 정규화한다 | 저장소 내 명시 없음 |
| `apps/agent/app/services/analyst_output_guard.py` | Analyst output guard service | 분석가별 LLM/fallback 출력을 근거 충분성 기준으로 보강하고 직접 근거 부족 시 caveat와 confidence 상한을 적용한다 | 저장소 내 명시 없음 |
| `apps/agent/app/services/legal_api_clients.py` | External legal/public API client | 국가법령정보센터와 공공데이터포털 교통 API 검색 결과를 내부 근거 형식으로 변환한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/routes/knia-admin.ts` | Fastify KNIA admin router | KNIA 수집, 상세 수집, 임베딩 재생성, JSON import, cache invalidation 관리자 API를 등록한다 | 저장소 내 명시 없음 |
| `apps/worker/worker/main.py` | Redis Streams worker entrypoint | Redis consumer group을 유지하고 job 실행 성공/실패 상태 캐시를 갱신한다 | 저장소 내 명시 없음 |
| `apps/worker/worker/job_processor.py` | Worker job processor | `video_preprocess`, `video_analyze` job의 DB 상태 전이, Agent 호출, 분석 결과 저장을 수행한다 | 저장소 내 명시 없음 |
| `apps/worker/worker/video_preprocess.py` | Video preprocessing service | ffprobe 영상 metadata 확인, 이벤트 프레임 시간 선택, ffmpeg 프레임 추출을 수행한다 | 저장소 내 명시 없음 |
| `apps/worker/worker/frame_analysis.py` | Optional frame analysis provider | OpenAI 이미지 입력을 이용해 프레임에서 관측 가능한 사고 사실 후보를 추출한다 | 저장소 내 명시 없음 |
| `AGENTS.md` | Agent entry instruction document | 에이전트가 작업 전 `DEVELOPMENT_PROMPT.md`와 `SYSTEM_OVERVIEW.md`를 먼저 읽도록 안내한다 | 저장소 내 명시 없음 |
| `DEVELOPMENT_PROMPT.md` | Development guidance document | 개발 전 참조하는 LawCompass 전담 Principal Software Architect 역할, 작업 순서, 검증, 보안, 문서 동기화 기준을 정의한다 | 저장소 내 명시 없음 |
| `SYSTEM_OVERVIEW.md` | Project handoff/spec document | 프로젝트 구조와 현재 구현 상태를 추적하는 기준 문서다 | 저장소 내 명시 없음 |
| `docs/STACK_DECISION_REVIEW.md` | Stack decision review document | 초기 스택 계획안과 현재 적용 스택을 비교하고 S3, Capacitor, 영상 분석, MCP, OpenAI API 전환 판단 기준을 기록한다 | 저장소 내 명시 없음 |
| `docs/PROJECT_BASELINE_2026-05-21.md` | Baseline snapshot document | 2026-05-21 인수 시점 구현 상태, 미완성 영역, 이후 변화 비교 질문을 기록한다 | 저장소 내 명시 없음 |

#### 주요 함수 및 입출력

| 파일 | Key Methods | Input | Output | Core Logic |
| --- | --- | --- | --- | --- |
| `apps/frontend/src/router/index.ts` | `router.beforeEach` | 대상 route | redirect 또는 `true` | `session.bootstrap()` 후 인증 필요 route에서 미로그인 사용자를 `/login`으로 이동 |
| `apps/frontend/src/api/client.ts` | `request<T>`, `formatApiError` | API path, `RequestInit`, API 오류 객체 | typed JSON response 또는 사용자 표시용 오류 문구 | `fetch`에 cookie 포함, JSON 파싱, 오류 객체 정규화, Gateway validation detail을 화면 표시용 필드 안내로 변환 |
| `apps/frontend/src/api/client.ts` | `api.login`, `api.createCase`, `api.analyzeText`, `api.searchKniaJson` 등 | 화면 DTO | Gateway 응답 DTO | `/api/v1/*` 공개 API 호출을 함수 단위로 래핑 |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | `useCaseWorkspace` | `caseId` | 화면 refs/actions | 케이스 상세 화면에서 쓰는 입력값, 업로드 목록, 영상 URL, 분석 job, easy report, polling lifecycle을 하나의 composable로 제공 |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | `statusLabel`, `statusClass`, `prettySize`, `formatDate` | status/size/date | 표시용 문자열/class | 케이스, 업로드, job 상태 표시 포맷을 CaseDetailView와 분리 |
| `apps/frontend/src/components/case/*.vue` | `CaseWorkspaceHeader`, `CaseSummaryCard`, `CaseInputStep`, `CaseUploadStep`, `CaseAnalysisStep` | props/events | Vue section markup | 케이스 상세 화면의 헤더, 요약, 입력, 업로드, 분석 요청 UI를 표시 단위로 분리하고 상태 변경은 상위 view/composable로 emit |
| `apps/frontend/src/stores/session.ts` | `restoreLocal` | 없음 | 없음 | `localStorage`의 `lawcompass:user`를 읽어 세션 상태 복원 |
| `apps/frontend/src/stores/session.ts` | `bootstrap` | 없음 | 없음 | `/auth/me` 실패 시 `/auth/refresh` 재시도 후 사용자 상태 갱신 |
| `apps/frontend/src/stores/session.ts` | `login`, `logout` | 이메일/비밀번호 또는 없음 | 없음 | Gateway 인증 API 호출 후 Pinia 상태와 localStorage 동기화. App logout 액션은 세션 정리 후 `/login`으로 이동 |
| `apps/gateway/src/main.ts` | `requireUser` | Fastify request/reply | boolean | JWT 검증 결과가 없으면 401 표준 오류 반환 |
| `apps/gateway/src/main.ts` | `requireAdmin` | Fastify request/reply | boolean | 사용자 role `admin` 또는 `x-admin-token`을 검사해 관리자 API 보호 |
| `apps/gateway/src/main.ts` | `rateLimit` | Fastify request/reply | 없음 또는 429 | Redis minute key를 증가시켜 분당 90회 초과 요청 차단 |
| `apps/gateway/src/main.ts` | `idempotency` | Fastify request/reply | cached reply 가능 | `Idempotency-Key`와 request hash로 중복 요청 응답 재사용 |
| `apps/gateway/src/lib/errors.ts` | `errorPayload`, `validationErrorPayload`, `requestErrorPayload` | code/message/trace 또는 Fastify error | 표준 오류 envelope | Gateway 오류 응답을 `error.code`, `error.message`, `error.trace_id` 형식으로 통일하고 validation detail을 정규화 |
| `apps/gateway/src/main.ts` | Auth routes | `email`, `password`, `display_name` | user, token, trace_id | 이메일 계정 생성, bcrypt 검증, JWT/refresh cookie 발급 |
| `apps/gateway/src/main.ts` | Case/upload/analyze routes | case/upload/analysis payload | case, upload, job, result | DB에 업무 데이터를 저장하고 Redis job 또는 Agent 분석 호출 수행 |
| `apps/gateway/src/routes/chat.ts` | `registerChatRoutes` | Fastify instance, options | route registration | `/chat/sessions`, `/chat/quick`, 메시지 API를 Gateway에 등록 |
| `apps/gateway/src/services/chatService.ts` | `createChatSession` | userId, caseId, title, context | chat session row | `chat_sessions`에 상담 세션 생성 |
| `apps/gateway/src/services/chatService.ts` | `getChatSessionForAccess` | sessionId, userId | session 또는 forbidden/null | 채팅 세션 소유권 검사 |
| `apps/gateway/src/services/chatService.ts` | `listChatMessages` | sessionId | sanitized messages | `chat_messages` 조회 후 내부 기술 필드 제거 |
| `apps/gateway/src/services/chatService.ts` | `sendChatMessage` | sessionId, userId, message, context, traceId | assistant reply payload | 사용자 메시지 저장, Agent 호출, assistant 메시지/안전 로그 저장 |
| `apps/gateway/src/lib/internal-client.ts` | `callInternalAgent` | internal path, payload, traceId, options | Agent JSON | timeout과 retry를 적용해 Agent POST API 호출 |
| `apps/gateway/src/storage/provider.ts` | `LocalStorageProvider.putUpload` | caseId, uploadId, fileName, contentType, stream | `StoredObject` | video MIME 검사 후 로컬 `storage/uploads`에 파일 저장 |
| `apps/gateway/src/storage/provider.ts` | `S3StorageProvider.putUpload` | upload input | error | 현재 `S3_STORAGE_NOT_ENABLED` 오류를 발생시키는 미구현 provider |
| `apps/agent/app/routers/internal_auth.py` | `check_internal_token` | `x_internal_token` | 없음 또는 401 | `INTERNAL_SERVICE_TOKEN`과 요청 헤더 비교 |
| `apps/agent/app/routers/internal_routes/analysis.py` | `analyze_text`, `analyze_video`, `analyze_scenario_endpoint` | Pydantic/dict payload | `AnalysisOutput` | orchestrator 분석 함수를 호출해 표준 분석 응답 반환 |
| `apps/agent/app/routers/internal_routes/legal.py` | `legal_ingest`, `legal_rebuild_embeddings`, `legal_retrieval_test` | token/query | ingest/rebuild/search 결과 | 법률 KB 적재, 벡터 생성, 검색 테스트 수행 |
| `apps/agent/app/routers/internal_routes/knia.py` | `knia_*` endpoints | token, chart/query/import payload | KNIA 수집/검색/추정 결과 | KNIA collector, matcher, repository, vectorizer, JSON loader 호출 |
| `apps/agent/app/schemas.py` | `AnalyzeTextRequest` | 텍스트 분석 요청 JSON | Pydantic model | 케이스/사용자/설명/구조화 사실/키워드 유효성 정의 |
| `apps/agent/app/schemas.py` | `AnalyzeVideoRequest` | 영상 분석 요청 JSON | Pydantic model | 업로드 ID, 전처리 요약, 영상 metadata 포함 요청 정의 |
| `apps/agent/app/schemas.py` | `AnalysisOutput` | 분석 결과 dict | Pydantic response | 법률/과실/보험/형사/근거/KNIA/쉬운 리포트 응답 규격 정의 |
| `apps/agent/app/services/orchestrator.py` | `analyze_case` | description, facts, keywords, profile | analysis dict | 텍스트 입력을 `_analyze_core`로 전달 |
| `apps/agent/app/services/orchestrator.py` | `analyze_video_case` | preprocessed summary, video metadata | analysis dict | 영상 요약과 metadata를 `_analyze_core`로 전달 |
| `apps/agent/app/services/orchestrator.py` | `_analyze_core` | normalized accident inputs | final analysis dict | 입력 context, 근거 수집, 분석가 실행, 재검색, 출력 보강 단계를 순서대로 연결 |
| `apps/agent/app/services/orchestration_context.py` | `build_case_context` | 사고 입력, 영상 metadata | `CaseContext` | 영상 계약, 입력 정규화, 시나리오 분류, 차량 역할 추론, 보완 질문 상태 생성 |
| `apps/agent/app/services/orchestration_evidence.py` | `collect_evidence_stage` | `CaseContext`, 영상 metadata | `EvidenceBundle` | KNIA 매칭/JSON 검색/과실 산정 근거와 법률 RAG 근거를 수집 |
| `apps/agent/app/services/orchestration_evidence.py` | `_knia_estimate_to_evidence`, `_knia_refs_to_evidence` | KNIA 추정/참조 데이터 | evidence list | 과실 기본값, 가감요소, 관련 법규/사례를 evidence item으로 변환 |
| `apps/agent/app/services/orchestration_analysis.py` | `run_analysis_stage`, `run_reflection_requery_stage` | `CaseContext`, `EvidenceBundle` | `AnalysisBundle`/`ReflectionStageResult` | 분석가 실행, KNIA 과실 적용, 근거 감사, claim-evidence 검증, 1회 bounded requery 수행 |
| `apps/agent/app/services/orchestration_output.py` | `enrich_analysis_output` | composed output, context, evidence/analysis bundles, judgment/reflection contract | final analysis dict | 판단 계약 적용 후 reflection loop, execution trace, 쉬운 리포트, KNIA 계산/검색 metadata를 최종 출력에 부착 |
| `apps/agent/app/services/analyst_output_contracts.py` | `validate_*_output` | analyst result dict | normalized analyst result dict | 문자열/배열/숫자/불리언 필드를 Pydantic 계약에 맞춰 정규화하고 extra context는 보존 |
| `apps/agent/app/services/analyst_output_guard.py` | `guard_*_output` | analyst result, evidence list | guarded analyst result | 법률/KNIA/일반 근거 family를 판별해 `evidence_support_level`, `judgment_status`, `used_evidence_ids`, `caveats`를 부여하고 과실비율 confidence를 직접 근거 수준에 맞게 제한 |
| `apps/agent/app/services/elderly_friendly/plain_language_agent.py` | `make_headline`, `make_summary`, `make_fault_explanation`, `make_legal_explanation`, `make_insurance_explanation` | final analysis dict | elderly-friendly report sections | `judgment_status` 또는 `evidence_support_level`이 약하면 사용자 문장을 "확정"이 아닌 "추가 확인 필요" 표현으로 완화 |
| `apps/agent/app/services/legal_api_clients.py` | `fetch_law_search` | query, limit | evidence-like rows | 국가법령정보센터 `lawSearch.do`에서 법령/판례 검색 |
| `apps/agent/app/services/legal_api_clients.py` | `fetch_data_go_traffic` | query, limit | evidence-like rows | 공공데이터포털 교통사고 API 응답을 내부 근거 형식으로 변환 |
| `apps/worker/worker/main.py` | `init_group`, `main_loop` | 없음 | 없음 | Redis Stream consumer group 생성, job 메시지 소비, 성공/실패 status cache 갱신 |
| `apps/worker/worker/job_processor.py` | `process_job` | job_id, job_type, redis client | DB/Redis side effect | `video_preprocess`와 `video_analyze` job을 분기하고 DB transaction을 관리 |
| `apps/worker/worker/job_processor.py` | `_process_video_preprocess`, `_enqueue_video_analyze_job` | job row, payload | uploads/jobs 갱신 | 영상 metadata/프레임/관측값을 저장하고 후속 `video_analyze` job을 큐에 등록 |
| `apps/worker/worker/job_processor.py` | `_process_video_analyze`, `_insert_analysis_result` | job row, payload | analysis result row | Agent `/internal/v1/analyze/video` 호출 후 `analysis_results`와 case latest result를 갱신 |
| `apps/worker/worker/job_processor.py` | `mark_failed` | job_id, error | DB side effect | 실패 job 상태, error_info, 재시도 시간을 저장 |
| `apps/worker/worker/video_preprocess.py` | `probe_video` | storage_path | video metadata dict | `ffprobe`로 codec, duration, resolution, fps, size 추출 |
| `apps/worker/worker/video_preprocess.py` | `frame_times_for_duration`, `extract_event_frames`, `extract_frames` | storage path, case/upload ids, duration | frame descriptors/list | 짧은 사고 영상에 맞춰 시간순 대표 프레임을 추출 |
| `apps/worker/worker/frame_analysis.py` | `analyze_frames_with_openai` | frame details, context | observation result dict | OpenAI Responses API 이미지 입력을 선택적으로 호출하고 관측값 JSON을 정규화 |

#### 파일별 호출 관계 및 리소스

| 파일 | Caller | Callee / Imports | Configuration | Data Storage / External Resource | MSA Context |
| --- | --- | --- | --- | --- | --- |
| `compose.yaml` | 운영자, Docker Compose CLI | 각 서비스 Dockerfile, `.env`, volume/network | `.env`, Compose substitution | Docker volumes `postgres_data`, `redis_data`, `caddy_data`, bind mount `storage`, `logs`, `config`, `scripts` | 전체 서비스 정의. host `80/443`, 내부 `3000/8000/5173/5432/6379` |
| `infra/caddy/Caddyfile` | `edge` container | `frontend:5173`, `gateway:3000` | Caddy global email | HTTP reverse proxy, 보안 header | `edge` 서비스, host `80/443` |
| `infra/postgres/migrations/001_init.sql` | `postgres` init, `db-migrate` profile | PostgreSQL extensions | `POSTGRES_*`는 compose/env에서 주입 | `users`, `cases`, `uploads`, `jobs`, `analysis_results`, `kb_*`, `audit_logs`, `idempotency_keys` | `postgres` 서비스 내부 `5432` |
| `apps/frontend/src/main.ts` | Browser | Vue, Pinia, Router, `App.vue` | Vite env 간접 사용 | DOM mount `#app` | `frontend` 서비스 내부 `5173` |
| `apps/frontend/src/router/index.ts` | Vue app | `vue-router`, `session` store, view components | 없음 | Browser history, session state | Browser -> frontend |
| `apps/frontend/src/api/client.ts` | Vue views/components/stores | Fetch API, `import.meta.env.VITE_API_BASE_URL` | `VITE_API_BASE_URL` | Gateway `/api/v1/*`, cookie credentials | Browser -> `edge`/`gateway` |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | `CaseDetailView.vue` | Vue refs/lifecycle, `api`, `formatApiError` | 없음 | Gateway case/upload/analysis/job/easy-report APIs | Browser -> Gateway via API client |
| `apps/frontend/src/stores/session.ts` | Router, Login/Logout UI | Pinia, `api` client | 없음 | `localStorage` key `lawcompass:user`, auth cookies는 Gateway가 관리 | Browser state layer |
| `apps/gateway/src/main.ts` | `node dist/main.js`, `tsx watch` | Fastify plugins, `pg`, `ioredis`, `bcryptjs`, internal libs | `DATABASE_URL`, `REDIS_URL`, `JWT_*`, `INTERNAL_AGENT_URL`, `INTERNAL_SERVICE_TOKEN`, `INTERNAL_ADMIN_TOKEN`, timeout/storage env | PostgreSQL 업무 테이블, Redis `rl:v1:*`, Redis Stream `jobs:v1:stream`, local storage | `gateway` 서비스 내부 `3000` |
| `apps/gateway/src/routes/chat.ts` | `apps/gateway/src/main.ts` | `chatService`, chat schemas | route option으로 Agent URL/token 전달 | `chat_sessions`, `chat_messages`는 service가 접근 | `gateway` 서비스 내부 route |
| `apps/gateway/src/services/chatService.ts` | `routes/chat.ts` | `callInternalAgent` | options의 `agentUrl`, `internalToken`, timeout/retry | `chat_sessions`, `chat_messages`, `chat_safety_logs`, Agent `/internal/v1/chat/message` | `gateway` -> `agent:8000` |
| `apps/gateway/src/lib/internal-client.ts` | Gateway routes/services | Fetch API, `randomUUID` | call option으로 수신 | Agent internal HTTP | `gateway` -> `agent:8000` |
| `apps/gateway/src/storage/provider.ts` | Upload routes in `main.ts` | Node fs/path/stream | `LOCAL_STORAGE_ROOT`는 생성자에서 전달 | `storage/uploads/{caseId}/{uploadId}/original.ext` | `gateway` container local/bind volume |
| `apps/agent/app/main.py` | Uvicorn | FastAPI, internal router | 없음 | 없음 | `agent` 서비스 내부 `8000` |
| `apps/agent/app/routers/internal.py` | `apps/agent/app/main.py` | `internal_routes` package | 없음 | 없음 | `agent` 내부 `/internal/v1/*` composition |
| `apps/agent/app/routers/internal_routes/*.py` | Gateway, Worker via `internal.py` | orchestrator, legal, KNIA, chat, cache services | `INTERNAL_SERVICE_TOKEN`, `DATABASE_URL` | KB/KNIA/semantic cache DB 테이블, Agent service 함수 | `agent` 내부 `/internal/v1/*` |
| `apps/agent/app/schemas.py` | `internal.py`, tests | Pydantic | 없음 | 없음 | Agent DTO layer |
| `apps/agent/app/services/orchestrator.py` | `internal.py`, tests | orchestration stage modules, judgment contract, report composer, OpenAI flag | `OPENAI_API_KEY` 존재 여부 | 법률 RAG, KNIA DB/Redis 검색은 하위 stage service에서 접근 | Agent domain service |
| `apps/agent/app/services/orchestration_output.py` | `orchestrator.py` | execution trace, judgment contract output policy, elderly-friendly report, stage bundle DTOs | 없음 | 입력 bundle에 포함된 KNIA/RAG metadata만 최종 출력에 복사 | Agent domain output layer |
| `apps/agent/app/services/analyst_output_contracts.py` | `analyst_output_guard.py`, tests | Pydantic | 없음 | 없음 | Agent DTO guard layer |
| `apps/agent/app/services/analyst_output_guard.py` | Agent analyst modules | 없음 | 없음 | 입력 evidence list만 사용 | Agent domain guard |
| `apps/agent/app/services/legal_api_clients.py` | legal ingestion/retrieval 계열 service/script | `httpx` | `LAW_API_OC`, `LAW_API_BASE`, `LAW_API_TARGETS`, `DATA_GO_*` | `law.go.kr`, `apis.data.go.kr` 외부 HTTP | Agent egress |
| `apps/worker/worker/main.py` | Worker container process | Redis, `job_processor` | `REDIS_URL`, `REDIS_STREAM_KEY`, `REDIS_STREAM_GROUP` | Redis stream/status key | `worker` service, no public port |
| `apps/worker/worker/job_processor.py` | `main.py` | psycopg, `video_preprocess`, `frame_analysis`, Agent HTTP helper | `DATABASE_URL`, `INTERNAL_AGENT_URL`, `INTERNAL_SERVICE_TOKEN`, `LOCAL_STORAGE_ROOT`, `REDIS_STREAM_KEY` | `jobs`, `uploads`, `cases`, `analysis_results`, Redis Stream follow-up enqueue, local frames | Worker domain service |
| `apps/worker/worker/video_preprocess.py` | `job_processor.py`, tests/scripts | ffprobe/ffmpeg subprocess | 없음 | local original video, `storage/frames/{caseId}/{uploadId}` | Worker video service |
| `apps/worker/worker/frame_analysis.py` | `job_processor.py` | OpenAI Responses API via `urllib` | `ENABLE_OPENAI_FRAME_ANALYSIS`, `OPENAI_API_KEY`, `OPENAI_VISION_MODEL`, `OPENAI_TIMEOUT_SEC`, `OPENAI_FRAME_ANALYSIS_MAX_FRAMES`, `OPENAI_FRAME_ANALYSIS_DETAIL` | OpenAI external HTTP, local frame images | Worker optional vision provider |

#### 데이터 모델 및 DTO 매핑

| 위치 | 모델/타입 | 외부 노출 여부 | 용도 |
| --- | --- | --- | --- |
| `apps/frontend/src/api/client.ts` | `User` | 프론트 내부/서버 응답 | 로그인 사용자 표시와 권한 판별 |
| `apps/frontend/src/api/client.ts` | `AccidentFacts` | 프론트 입력/서버 요청 | 사고 구조화 입력 |
| `apps/frontend/src/api/client.ts` | `CaseItem` | 프론트 입력/서버 응답 | 케이스 목록/상세 표시 |
| `apps/frontend/src/api/client.ts` | `UploadItem` | 서버 응답 | 업로드 파일 상태 표시 |
| `apps/gateway/src/storage/provider.ts` | `StoredObject`, `StorageProvider` | Gateway 내부 | 업로드 저장 결과 및 provider 추상화 |
| `apps/gateway/src/lib/internal-client.ts` | `AgentCallOptions` | Gateway 내부 | Agent 호출 timeout/retry/token 옵션 |
| `apps/gateway/src/services/chatService.ts` | `ChatServiceOptions` | Gateway 내부 | 채팅 service가 DB/Agent 설정을 받는 규격 |
| `apps/gateway/src/lib/report-composer.ts` | `evidence_reliability_card` | Gateway public report response 일부 | raw `claim_evidence`를 숨기고 근거 연결률, 판단 수, 근거 부족 수, 주의 문구를 일반 사용자용 카드로 요약 |
| `apps/agent/app/schemas.py` | `AnalyzeTextRequest` | Agent internal API request | 텍스트 분석 요청 검증 |
| `apps/agent/app/schemas.py` | `AnalyzeVideoRequest` | Agent internal API request | 영상 분석 요청 검증 |
| `apps/agent/app/schemas.py` | `EvidenceItem` | Agent internal API response | 법률/KNIA 근거 item 규격 |
| `apps/agent/app/schemas.py` | `AnalysisOutput` | Agent internal API response | 최종 분석 결과 표준 응답 |
| `apps/agent/app/services/analyst_output_contracts.py` | Analyst Pydantic contracts | Agent internal API response 일부 | `legal_analysis`, `fault_ratio`, `legal_liability`, `insurance_guide` dict의 내부 출력 계약 |
| `apps/agent/app/services/analyst_output_guard.py` | `evidence_support_level`, `judgment_status`, `used_evidence_ids`, `caveats`, `evidence_count`, `evidence_ids` | Agent internal API response 일부 | 분석가별 판단이 직접 근거, 간접 근거, 근거 부족 중 어디에 속하는지 표시하고 확정 판단 방지를 위한 주의 문구를 제공 |
| `apps/agent/app/services/elderly_friendly/plain_language_agent.py` | 쉬운 리포트 섹션 dict | Gateway public report response 일부 | 근거 부족 상태를 사용자 친화적인 경고/주의 문장으로 반영 |
| `apps/agent/app/services/claim_evidence_validator.py` | `claim_evidence` dict | Agent internal API response 일부 | 법규, 과실비율, 형사책임, 보험 안내, 행동계획의 주요 claim별 연결 근거와 지원 수준 |

#### 테스트 및 유지보수 상태 매핑

| 파일/영역 | Progress State | Test Status | Known Issues / Review Notes |
| --- | --- | --- | --- |
| `apps/frontend/src/api/client.ts`, `apps/frontend/src/components/easy/*`, `apps/frontend/src/composables/useCaseWorkspace.ts` | 구현 완료 | `apps/frontend/scripts/test-display.mjs`, `apps/frontend/scripts/test-chat.mjs`에서 간접 검증 | 네트워크/JSON/API 오류를 사용자 문구로 정규화하고 Gateway validation detail을 로그인, 회원가입, 케이스 생성, 케이스 상세 주요 액션에서 필드별 안내로 표시한다. 결과/근거 화면은 로딩, 결과 없음, 오류 상태를 구분하고 일반 사용자 화면에서는 내부 근거 식별자와 원문 덤프를 숨긴다. 쉬운 리포트는 `evidence_reliability_card`로 Agent 판단의 근거 연결 상태를 표시한다. 인증 폼은 데모 기본값 없이 email 형식과 8자 이상 비밀번호를 선제 검증한다. 케이스 상세 화면의 입력/업로드/분석/job polling 로직은 `useCaseWorkspace` composable로 분리했다. |
| `apps/frontend/src/router/index.ts` | 구현 완료 | 전용 단위 테스트 없음 | 인증 bootstrap가 route guard마다 실행되므로 초기 진입 지연 가능성은 관찰 대상 |
| `apps/frontend/src/stores/session.ts` | 구현 완료 | 전용 단위 테스트 없음 | localStorage 사용자 정보와 cookie 세션 불일치 시 refresh 흐름에 의존 |
| `apps/gateway/src/main.ts` | 구현 완료, Gateway composition root | `apps/gateway/test/error-format.test.ts`, `npm test`, `npm run build` | validation 오류는 400 `VALIDATION_ERROR`로 정규화된다. 신규 API 동작은 route module에 추가해야 한다 |
| `apps/gateway/src/lib/report-composer.ts` | 구현 완료, 리포트 안전화 로직 | `apps/gateway/test/report-composer.test.ts`, `npm test` | raw Agent 결과를 일반 사용자 화면용 리포트로 변환하므로 내부 식별자/점수/claim 세부 구조가 노출되지 않도록 테스트 유지 필요 |
| `apps/gateway/src/routes/chat.ts` | 구현 완료 | Gateway test에서 직접 매핑 확인 필요 | 일부 route는 `requireUser`를 명시적으로 강제하지 않고 익명 세션도 허용하는 구조다 |
| `apps/gateway/src/services/chatService.ts` | 구현 완료 | 전용 단위 테스트 없음 | Agent 장애 시 Gateway route에서 502로 변환된다 |
| `apps/gateway/src/storage/provider.ts` | 로컬 provider 구현, S3 provider 미구현 | 전용 단위 테스트 없음 | `S3StorageProvider`는 현재 의도적으로 비활성 상태 |
| `apps/agent/app/routers/internal.py`, `apps/agent/app/routers/internal_routes/*` | 구현 완료 | `apps/agent/scripts/check_internal_routes.py`, `scripts/verify_agent_regression.ps1`, `apps/agent/scripts/test_*.py` | 내부 token 누락/불일치 시 401. Route split 후에도 기존 `/internal/v1/*` path contract를 유지해야 한다. |
| `apps/agent/app/schemas.py` | 구현 완료 | `apps/agent/tests/test_orchestrator.py` 및 scripts에서 간접 검증 | 응답 모델이 크므로 프론트 표시 필드와 동기화 관리 필요 |
| `apps/agent/app/services/orchestrator.py` | 구현 완료, stage sequencing 중심 | `apps/agent/tests/test_orchestrator.py`, `apps/agent/scripts/test_legal_rag.py`, `test_knia_*`, `test_chat_*` 간접 검증 | 신규 stage 책임은 context/evidence/analysis/output 모듈에 추가하고 orchestrator는 순서 조립에 집중해야 한다 |
| `apps/agent/app/services/orchestration_output.py` | 구현 완료, 최종 출력 보강 로직 | `apps/agent/tests/test_orchestrator.py`, `apps/agent/scripts/test_agent_regression_scenarios.py` 간접 검증 | 사용자 화면에 raw trace/내부 식별자가 노출되지 않도록 Gateway/Frontend sanitizer와 함께 유지해야 한다 |
| `apps/agent/app/services/analyst_output_contracts.py` | 구현 완료, Analyst 출력 계약 | `apps/agent/tests/test_analyst_output_guard.py`, `apps/agent/tests/test_orchestrator.py` | LLM이 예외적인 JSON 타입을 반환해도 가능한 범위에서 정규화하되, 신규 analyst 추가 시 계약 모델을 함께 추가해야 함 |
| `apps/agent/app/services/analyst_output_guard.py` | 구현 완료, Analyst 신뢰도 가드 | `apps/agent/tests/test_analyst_output_guard.py`, `apps/agent/tests/test_orchestrator.py` | 신규 analyst 출력 필드가 프론트 일반 화면에 기술 문자열로 노출되지 않도록 Gateway/Frontend sanitizer와 함께 관리 필요 |
| `apps/agent/app/services/elderly_friendly/plain_language_agent.py` | 구현 완료, 근거 상태 기반 문장 완화 | `apps/agent/tests/test_elderly_report_support_language.py`, `apps/agent/tests/test_orchestrator.py` | 쉬운 리포트 문장은 내부 코드가 아니라 사용자 표시 문구만 포함해야 하며, 근거 부족 시 확정 표현을 피해야 함 |
| `apps/agent/app/services/claim_evidence_validator.py` | 구현 완료, Agent 신뢰도 보강 로직 | `apps/agent/tests/test_claim_evidence_validator.py`, `apps/agent/tests/test_orchestrator.py` | 주요 판단별 근거 연결 상태를 산출하고 analyst의 `used_evidence_ids`가 있으면 claim별 evidence ref 선정에 우선 사용한다. 향후 Analyst별 claim 형식이 바뀌면 함께 갱신 필요 |
| `apps/agent/app/services/legal_api_clients.py` | 구현 완료, 외부 권한 의존 | `apps/agent/scripts/check_external_apis.py` | 국가법령정보센터 IP/도메인 검증, 공공데이터포털 활용신청 권한 상태에 따라 실패 가능 |
| `apps/worker/worker/main.py`, `apps/worker/worker/job_processor.py`, `apps/worker/worker/video_preprocess.py`, `apps/worker/worker/frame_analysis.py` | 구현 완료, Worker 책임 분리 적용 | `python -m compileall worker`, `apps/worker/tests/test_keys.py`, E2E smoke에서 간접 검증 | ffmpeg/ffprobe 설치와 로컬 파일 경로 접근 권한에 의존. OpenAI 프레임 분석은 기본 비활성이고 환경변수로 켜야 한다 |
| `infra/postgres/migrations/*.sql` | 초기/증분 migration 구현 | Compose init, `db-migrate` profile, E2E smoke | `db-migrate` 명령은 일부 migration glob을 명시 적용하므로 신규 migration 추가 시 compose 명령 확인 필요 |

## 3. 의존성

### 패키지 의존성

| 영역 | 주요 의존성 |
| --- | --- |
| Frontend | `vue`, `vue-router`, `pinia`, `vite`, `typescript`, `vue-tsc`, `@vitejs/plugin-vue` |
| Gateway | `fastify`, `@fastify/cookie`, `@fastify/cors`, `@fastify/jwt`, `@fastify/multipart`, `pg`, `ioredis`, `bcryptjs`, `uuid`, `zod`, AWS S3 SDK |
| Agent | `fastapi`, `uvicorn`, `pydantic`, `httpx`, `psycopg[binary]`, `redis`, `python-dotenv`, `beautifulsoup4` |
| Worker | `redis`, `psycopg[binary]`, `boto3`, `tenacity`, 시스템 바이너리 `ffmpeg`, `ffprobe` |
| Infra | Docker Compose, Caddy, PostgreSQL 16 + pgvector, Redis 7.2 |

### 내부 모듈 연결성

| 호출 주체 | 대상 | 방식 |
| --- | --- | --- |
| Browser/Frontend | Gateway | HTTP `/api/v1/*`, cookie 세션 포함 |
| Gateway | PostgreSQL | `pg.Pool` 직접 SQL |
| Gateway | Redis | rate limit, 작업 큐, 상태 캐시 |
| Gateway | Agent | 내부 HTTP + `x-internal-token` |
| Gateway | Storage | 로컬 파일 저장. S3 SDK 의존성 존재 |
| Worker | Redis | `xreadgroup`, `xadd`, `xack`, `setex` |
| Worker | PostgreSQL | job/upload/case/result 상태 갱신 |
| Worker | Agent | 내부 HTTP + `x-internal-token` |
| Agent | PostgreSQL | KB, KNIA, 임베딩, 분석 근거 조회/저장 |
| Agent | 외부 API | `httpx` 기반 법령/공공/KNIA 호출 |

### 주요 환경변수

| 영역 | 환경변수 |
| --- | --- |
| 공통 | `DATABASE_URL`, `REDIS_URL`, `NODE_ENV`, `PYTHONPATH` |
| Gateway 인증 | `JWT_ACCESS_SECRET`, `JWT_REFRESH_SECRET`, `JWT_ACCESS_TTL_SEC`, `JWT_REFRESH_TTL_SEC`, `INTERNAL_ADMIN_TOKEN` |
| 내부 통신 | `INTERNAL_AGENT_URL`, `AGENT_BASE_URL`, `INTERNAL_SERVICE_TOKEN`, `REQUEST_TIMEOUT_MS`, `ANALYZE_TIMEOUT_MS`, `RETRY_COUNT` |
| 저장소 | `STORAGE_PROVIDER`, `LOCAL_STORAGE_ROOT`, `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| OpenAI | `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`, `OPENAI_TIMEOUT_SEC`, `ENABLE_OPENAI_ANALYSTS` |
| 법률/공공 API | `LAW_API_OC`, `LAW_API_BASE`, `LAW_API_TARGETS`, `DATA_GO_SERVICE_KEY`, `DATA_GO_TRAFFIC_URL`, `DATA_GO_SEARCH_YEAR`, `DATA_GO_SIDO`, `DATA_GO_GUGUN` |
| KNIA | `KNIA_BASE_URL`, `KNIA_REQUEST_DELAY_MS`, `KNIA_TIMEOUT_SEC`, `KNIA_COLLECT_MAX_CHARTS`, `KNIA_FAULT_RATIO_JSON_PATH` |

## 4. 리소스 연동

### 데이터베이스

기본 DB는 PostgreSQL이며 `vector`, `pgcrypto`, `citext` 확장을 사용한다.

| 테이블 그룹 | 대표 테이블 | 목적 |
| --- | --- | --- |
| 인증 | `users`, `auth_refresh_tokens` | 이메일 계정, role, refresh token hash |
| 케이스 | `cases`, `uploads`, `jobs`, `analysis_results` | 사고 케이스, 영상 업로드, 비동기 작업, 분석 결과 |
| 감사/멱등성 | `audit_logs`, `idempotency_keys`, `prompt_policy_versions` | 추적, 중복 요청 방지, 프롬프트 정책 버전 |
| 법률 KB | `kb_sources`, `kb_documents`, `kb_chunks`, `kb_embeddings`, `legal_rules`, `scenario_legal_mappings`, `kb_ingest_runs` | 법령/판례/규칙 문서 및 벡터 근거 |
| 채팅 | `chat_sessions`, `chat_messages`, `chat_safety_logs` | AI 상담 세션 및 안전 로그 |
| KNIA | `knia_sources`, `knia_menu_pages`, `knia_fault_charts`, `knia_fault_chart_chunks`, `knia_fault_rankings`, `knia_media_assets`, `knia_ranking_items` | 손해보험협회 과실비율 기준 데이터 |
| KNIA JSON | `knia_json_import_runs`, `knia_myaccident_pages`, `knia_menu_nodes`, `knia_reference_documents`, `knia_reference_chunks`, `knia_json_media_assets` | JSON 기반 과실비율 자료 import 및 검색 |
| 캐시/도구 | `semantic_query_cache`, `mcp_tool_calls` | 의미 검색 캐시, 내부 도구 호출 로그 |

### Redis

| 사용처 | 키/스트림 |
| --- | --- |
| Rate limit | `rl:v1:{user}:{route}:{minute}` |
| 작업 큐 | `jobs:v1:stream` |
| Consumer group | `worker-group` |
| 작업 상태 캐시 | `job:v1:{job_id}:status` |

### 파일/오브젝트 저장소

| 저장소 | 현재 동작 |
| --- | --- |
| 로컬 저장소 | `storage/uploads/{caseId}/{uploadId}/original.ext`에 업로드 영상 저장 |
| 프레임 저장소 | `storage/frames/{caseId}/{uploadId}/frame_*.jpg`에 대표 프레임 저장 |
| S3 | README와 환경변수에는 AWS S3 사용 전제가 있으나, Gateway의 `S3StorageProvider.putUpload()`는 현재 `S3_STORAGE_NOT_ENABLED`를 반환하는 상태 |

### 외부 API 및 기관

| 연동명 | 기관/사이트 | 코드상 목적 |
| --- | --- | --- |
| OpenAI API | OpenAI | 분석 모델 및 임베딩 모델 호출 |
| 국가법령정보센터 OPEN API | `https://www.law.go.kr/DRF` | 법령/판례 검색. `lawSearch.do`, target 기본값 `law,prec` |
| 공공데이터포털 교통 API | `https://apis.data.go.kr/B552061/AccidentDeath/getRestTrafficAccidentDeath` | 사망교통사고정보 조회 계열 API |
| KNIA 과실비율정보포털 | `https://accident.knia.or.kr` | 과실비율 기준, 순위, 차트, 관련 문서/미디어 수집 및 매칭 |
| 손해보험협회 웹 리소스 | `www.knia.or.kr` 계열 링크 | KNIA 자료 내 PDF/미디어 링크 보조 참조 |

### 보안 및 토큰 사용

민감값은 `.env` 계열 파일과 실행 환경변수로 주입된다. 문서에는 실제 키 값을 기록하지 않는다.

| 항목 | 사용 방식 |
| --- | --- |
| 사용자 로그인 | 이메일 + 비밀번호. 비밀번호는 `bcrypt` hash로 저장 |
| Access token | JWT, `lc_at` HTTP-only cookie |
| Refresh token | 원문은 cookie, DB에는 SHA-256 hash 저장 및 회전 |
| 내부 서비스 토큰 | Gateway/Worker가 Agent 호출 시 `x-internal-token` 헤더 사용 |
| 관리자 토큰 | `INTERNAL_ADMIN_TOKEN`이 설정된 경우 `x-admin-token`으로 관리자 API 접근 가능 |
| API 키 | OpenAI, 국가법령정보센터, 공공데이터포털, AWS 키는 환경변수 사용 |

## 5. 완성도 및 To-Do

### 구현 완료로 보이는 영역

| 영역 | 상태 |
| --- | --- |
| Docker Compose 구동 | `edge`, `frontend`, `gateway`, `agent`, `worker`, `postgres`, `redis` 서비스 정의 완료 |
| 기본 인증 | 이메일 회원가입/로그인/refresh/logout/me 구현 |
| 케이스 관리 | 생성, 목록, 상세, 수정 구현 |
| 로컬 영상 업로드 | multipart 업로드, 로컬 저장, 재생/다운로드 URL 구현 |
| 영상 비동기 처리 | Redis Stream 작업 큐, ffprobe/ffmpeg 전처리, Agent 분석 연계 구현 |
| 텍스트 분석 | Gateway에서 Agent 내부 API 호출 후 결과 저장 구현 |
| 법률 RAG | KB 테이블, 임베딩 테이블, 적재/검색/재빌드 경로 구현 |
| KNIA 연동 | 수집, ranking, chart, JSON import, 매칭, media search 경로 구현 |
| AI 채팅 | 세션, 메시지, 빠른 상담, 초안 케이스 반환 흐름 구현 |
| 운영 문서 | README, `docs/OPERATIONS.md`, OpenAPI 문서 존재 |

### 코드상 확인된 미완성/주의 지점

| 항목 | 근거 및 상태 |
| --- | --- |
| S3 업로드 구현 | Gateway에 AWS SDK 의존성은 있으나 `S3StorageProvider.putUpload()`가 `S3_STORAGE_NOT_ENABLED`를 던진다. 현재 실제 업로드 경로는 로컬 저장소 중심이다 |
| 로그인 식별자 | DB와 API 스키마는 `email`만 로그인 식별자로 사용한다. 별도 `username` 또는 `login_id` 컬럼/입력은 보이지 않는다. 프론트 로그인/회원가입 화면도 email-only 정책을 따르며 기본 데모 계정값을 자동 입력하지 않는다 |
| 오류 응답 UX | Gateway validation 오류와 프론트 API client 오류 문구가 정규화되었고 로그인, 회원가입, 케이스 생성, 케이스 상세의 저장/업로드/분석 주요 액션에서 field별 안내 문구를 표시한다. 결과/근거 화면은 로딩, 결과 없음, 오류 상태를 구분하며 내부 근거 식별자와 원문 덤프는 debug 모드에서만 표시한다. KNIA 검색순위/상세/JSON 근거 검색 화면은 API 실패, 검색 결과 없음, 미수집 상태, 상세 기준 수집 필요 상태를 구분해 표시한다. 검색순위에는 있으나 상세 기준이 아직 수집되지 않은 항목은 ranking placeholder 상세 화면을 표시하고, 관리자에게 해당 기준만 수집하는 액션을 제공한다 |
| 외부 API 권한 의존 | `docs/OPERATIONS.md`에 국가법령정보센터 IP/도메인 검증, 공공데이터포털 활용신청/권한 이슈 가능성이 명시되어 있다 |
| Agent fallback | 법률 API 또는 KB 적재가 부족할 때 정적 fallback 근거를 반환하는 코드가 존재한다 |
| 테스트 산출물/캐시 파일 | `__pycache__`, `dist`, `storage` 내 테스트/실행 산출물이 저장소에 존재한다 |

### 테스트 및 검증 경로

| 영역 | 파일/명령 |
| --- | --- |
| Frontend build | `apps/frontend/package.json`의 `npm run build` |
| Frontend 표시 테스트 | `npm run test:display`, `npm run test:chat` |
| Gateway test | `apps/gateway/test/error-format.test.ts`, `npm test` |
| Agent 테스트 스크립트 | `apps/agent/tests/test_orchestrator.py`, `apps/agent/scripts/test_*.py` |
| Worker 테스트 | `apps/worker/tests/test_keys.py` |
| E2E 스모크 | `scripts/smoke_e2e.ps1` |
| 외부 API 점검 | `docker compose exec -T agent sh -lc "PYTHONPATH=/app python scripts/check_external_apis.py"` |

### 현재 기준 실행 절차

```bash
docker compose --env-file .env up --build
docker compose exec agent python scripts/ingest_kb.py
```

브라우저 접속 기준은 `http://localhost`이다.

### 문서 유지 시 우선 확인 대상

1. `compose.yaml` 서비스/환경변수 변경 여부
2. `AGENTS.md` 에이전트 진입 지침 변경 여부
3. `DEVELOPMENT_PROMPT.md` 개발 원칙/검증/문서 동기화 규칙 변경 여부
4. `docs/STACK_DECISION_REVIEW.md` 기술 스택 도입/전환 판단 변경 여부
5. `docs/PROJECT_BASELINE_2026-05-21.md`는 과거 기준점이므로 원칙적으로 변경하지 않되, 기준일 상태 오기재만 수정
6. `apps/gateway/src/main.ts` 공개 API 및 인증 흐름 변경 여부
7. `apps/agent/app/routers/internal.py` 내부 분석 API 변경 여부
8. `infra/postgres/migrations` 테이블/인덱스 변경 여부
9. `apps/frontend/src/api/client.ts` 프론트 DTO 및 API 호출 변경 여부

## 2026-05-21 Agent 검색 품질 보강 기록

Agent 레이어의 판례/법률 RAG, KNIA 기준 매칭, 추천 키워드가 서로 다른 검색어 기준을 쓰면 같은 사고 입력이라도 근거 검색 품질이 흔들릴 수 있어 공통 검색어 보강 모듈을 추가했다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/scenario_search_terms.py` | 시나리오, 태그, 사고 당사자 유형, 구조화 사실을 표준 검색어로 확장하는 공통 모듈 |
| `apps/agent/app/services/rag_client.py` | 법률 근거 검색 전에 시나리오 검색어를 붙이고 `query_expansion_terms`를 retrieval 메타데이터에 기록 |
| `apps/agent/app/services/knia/knia_matcher.py` | KNIA FTS/vector/tag 검색 쿼리에 시나리오별 표준 검색어를 반영하고 `knia_query_expansion_terms` 추적 가능 |
| `apps/agent/app/services/keyword_recommender.py` | 추천 키워드와 후속 입력 안내를 공통 검색어 기준으로 정리 |
| `apps/agent/tests/test_scenario_search_terms.py` | 검색어 확장, 추천 키워드, 주정차 분류 회귀 테스트 |

DB schema, Redis key, 외부 API, 환경 변수 변경은 없다. Agent 최종 응답의 `model_info.retrieval`에는 `query_expansion_terms`, `knia_query_expansion_terms`가 추가된다. 실제 근거 품질은 DB에 적재된 법률 KB/KNIA 원문 상세 기준의 충실도에 계속 의존하므로 다음 Agent 단계에서는 직접 관련성 점수 하한과 시나리오별 필수 근거군 검증을 보강해야 한다.
## 2026-05-21 후미추돌 사용자 관점 및 근거 표시 보정

정차 중 뒤에서 추돌당한 사고에서 KNIA `A:B` 기준을 사용자 관점으로 변환하지 않아 `A차량=뒤차/추돌차량`의 100% 과실이 그대로 `내 책임`으로 표시되는 문제가 있었다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/accident_perspective.py` | 후미추돌 문장에서 사용자가 앞차/피추돌 차량인지 뒤차/추돌 차량인지 판별하고 KNIA A/B 과실을 사용자 기준 `my/other`로 변환 |
| `apps/agent/app/services/analysts/fault_ratio_analyst.py` | KNIA가 없을 때도 후미추돌 사용자 역할에 따라 앞차는 내 책임 0%, 뒤차는 내 책임 100%로 기본 추정 |
| `apps/agent/app/services/orchestrator.py` | KNIA 최종 A/B 산정값을 바로 `my/other`에 넣지 않고 사용자 차량 역할 기준으로 변환 |
| `apps/agent/app/services/static_legal_fallback.py` | 영어 fallback 근거 제목/요약을 한국어 법률 근거 카드로 교체하고, 검색어가 맞는 fallback 근거를 우선 표시 |
| `apps/agent/app/services/knia/knia_matcher.py` | `차/보/자/기/단` 기준번호 접두어로 KNIA 사고 당사자 유형 보정 |
| `apps/frontend/src/components/easy/EasyReportView.vue` | KNIA A/B 원문값과 별도로 사용자 기준 내 책임/상대 책임 표시 |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | `following` 같은 일반 영문 단어 안의 `low`가 `낮음`으로 치환되지 않도록 수준값 치환을 단독 값에만 적용 |
| `apps/agent/tests/test_rear_end_user_perspective.py` | 후미추돌 사용자 역할 판별, A/B 과실 변환, 한국어 fallback 근거 회귀 테스트 |

DB schema, Redis key, 외부 API, 환경 변수 변경은 없다. 기존 KNIA 원문 A/B 값은 보존하되, 사용자 화면의 `내 책임/상대방 책임`은 `user_vehicle_role` 판별 결과를 기준으로 표시한다.

## 2026-05-21 KNIA 사용자 관점 매핑 확장 및 시나리오 매칭 보정

후미추돌에 한정되어 있던 KNIA A/B 기준의 사용자 관점 변환을 Agent 레이어에서 차선변경, 교차로 신호위반, 보행자, 자전거, 시설물, 단독 사고 유형으로 확장했다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/accident_perspective.py` | 사고 문장과 구조화 입력에서 사용자의 역할을 판별한다. 후미추돌은 앞차/뒤차, 차선변경은 직진차/진로변경차, 신호위반은 정상 신호차/신호위반차, 보행자·자전거 사고는 사용자 역할을 KNIA A/B 기준으로 변환한다. |
| `apps/agent/app/services/analysts/fault_ratio_analyst.py` | KNIA 기준이 없을 때도 사용자 역할을 반영해 차선변경과 신호위반 fallback 과실비율을 산정한다. |
| `apps/agent/app/services/knia/knia_matcher.py` | 교차로 신호위반 시나리오에서 신호위반 기준이 아닌 후미추돌/차선변경 기준이 1순위로 붙지 않도록 strict mismatch 필터를 추가했다. 매칭 점수 조정 이후 기존 Redis 캐시를 피하기 위해 `knia:match:v4` 캐시 키를 사용한다. |
| `apps/agent/tests/test_knia_user_perspective_mapping.py` | 차선변경, 신호위반, 자전거 사고에서 사용자 역할과 A/B 과실 변환을 검증한다. |
| `apps/agent/tests/test_knia_matcher_scoring.py` | 신호위반 기준 점수 보정, 관련 없는 후미추돌 기준 배제, chart 번호 기반 사고 당사자 라벨 보정을 검증한다. |

현재 로컬 DB에는 `차12-1` 교차로 신호위반 KNIA 차트가 수집되어 있지 않고 `차41-1`, `차43-2`만 확인된다. 따라서 신호위반 사고에서는 관련 KNIA 차트가 없으면 잘못된 기준을 억지로 붙이지 않고, Agent fallback 과실 추정으로 내려간다. 이후 KNIA 상세 기준 수집 또는 JSON import로 `차12-1` 계열 기준이 들어오면 해당 기준을 우선 매칭하도록 동작한다.

## 2026-05-21 Agent 판단 계약 및 근거 검증 게이트 보강

Agent 레이어의 개별 결과값을 단순 출력하지 않고, 시나리오 분류부터 근거 검색, 법률 분석, 과실 산정, 형사책임, 보험 안내, 행동 계획까지 단계별 판단 상태를 `agent_judgment` 계약으로 묶어 추적하도록 보강했다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/judgment_contract.py` | Agent 판단 단계별 상태를 `evidence_supported`, `needs_review`, `unsupported`로 표준화한다. claim coverage, 누락 입력, unsupported stage를 종합해 `overall_status`, `must_not_present_as_final`, `blocking_reasons`를 생성한다. |
| `apps/agent/app/services/orchestrator.py` | claim evidence 검증 이후 `agent_judgment` 계약을 생성하고 최종 분석 결과에 포함한다. 확정 표현이 부적절한 경우 disclaimer와 uncertainty reason을 보강한다. |
| `apps/agent/app/services/claim_evidence_validator.py` | claim 검증이 근거 목록 존재 여부만 보지 않고 각 analyst의 `evidence_support_level`도 반영한다. analyst가 `insufficient`로 판정한 항목은 근거 후보가 있더라도 unsupported claim으로 처리한다. |
| `apps/agent/app/schemas.py` | `AnalysisOutput`에 `agent_judgment` 필드를 추가했다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | `agent_judgment`와 내부 판단 계약 필드를 일반 사용자용 리포트에 노출하지 않는 기술 필드로 등록했다. |
| `apps/agent/tests/test_judgment_contract.py` | analyst support level이 claim evidence에 반영되는지, unsupported claim이 최종 판단 계약에서 확정 표현 차단 상태로 이어지는지 검증한다. |

DB schema, Redis key, 외부 API, 환경 변수 변경은 없다. 이 변경은 Agent 판단 구조와 근거 검증 체계의 내부 계약을 강화하는 작업이며, 사용자 화면은 기존 쉬운 리포트와 근거 연결 카드 중심으로 유지된다.

## 2026-05-21 Agent 대표 시나리오 회귀 검증 추가

Agent 판단 구조가 사고 유형, 사용자 관점, KNIA 기준 매칭, 최종 판단 계약을 함께 유지하는지 확인하기 위해 대표 사고 시나리오 스모크 검증을 추가했다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/scripts/test_agent_regression_scenarios.py` | 후방추돌 피해자, 상대 차선변경, 사용자 차선변경, 상대 신호위반, 사용자 자전거 사고를 `analyze_case()`로 실행하고 `scenario_type`, 사용자 기준 과실비율, `user_vehicle_role`, KNIA 1순위 기준, `agent_judgment` 계약 존재 여부를 검증한다. `pytest` 없이 컨테이너에서 직접 실행 가능한 회귀 스크립트다. |
| `apps/agent/app/services/knia/knia_matcher.py` | 보행자, 어린이보호구역, 자전거, 시설물, 단독 사고 시나리오에서 사고 당사자 유형이 맞지 않는 KNIA 기준을 엄격히 배제한다. 자전거 사고가 차대차 차선변경 기준(`차43-2`)에 잘못 연결되는 문제를 막기 위해 KNIA 매칭 캐시 키를 `knia:match:v5`로 갱신했다. |
| `apps/agent/tests/test_knia_strict_party_matching.py` | 자전거/보행자 시나리오가 관련 없는 차대차 기준을 거부하고 올바른 기준번호 계열은 허용하는지 단위 테스트로 고정했다. |

DB schema, Redis key 구조, 환경 변수, 외부 API 계약 변경은 없다. Redis KNIA 매칭 캐시 prefix만 `knia:match:v5`로 변경되어 기존 잘못된 매칭 캐시를 재사용하지 않는다.

## 2026-05-21 Agent 최종 출력 정책 게이트 보강

Agent 판단 계약이 단순 메타데이터로만 남지 않도록 최종 출력 섹션에 표시 정책을 직접 반영했다. 근거가 부족한 섹션은 확정 판단처럼 보이지 않도록 `presentation_status`, `finality_notice`, 신뢰도 상한, caveat를 적용한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/judgment_contract.py` | `agent_judgment` 계약을 적용할 때 법률 판단, 과실비율, 형사책임, 보험 안내 섹션별 상태를 확인하고 `review_required` 또는 `blocked_for_final` 표시 정책을 적용한다. 전체 판단 상태는 `presentation_policy.finality`로 요약한다. |
| `apps/agent/app/services/orchestrator.py` | 판단 계약 적용 후 쉬운 리포트를 다시 생성해 보수적으로 보정된 섹션 상태가 사용자용 설명에도 반영되도록 했다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | `presentation_policy`, `presentation_status` 등 내부 표시 정책 키가 일반 리포트에 원시 필드로 노출되지 않도록 기술 필드 목록에 추가했다. |
| `apps/agent/tests/test_judgment_contract.py` | unsupported/needs_review 섹션이 최종 출력에서 확정 표현 차단 상태와 신뢰도 상한을 받는지 검증한다. |

DB schema, Redis key, 환경 변수, 외부 API 계약 변경은 없다. 이 변경은 Agent 레이어의 최종 답변 안전장치이며, 근거가 부족한 판단을 사용자에게 결론처럼 제시하지 않기 위한 내부 출력 정책이다.

## 2026-05-21 Agent 근거 검색 품질 게이트 보강

Agent 레이어가 법률/KNIA 근거의 개수만 보고 검색 품질을 판단하지 않도록, 사고 유형별 근거 관련성 점검 게이트를 추가했다. 이 변경은 RAG/KNIA 검색 결과가 실제 사고 시나리오와 맞는지 확인하기 위한 골격 보강이며, DB schema, Redis key, 환경 변수, 외부 API 계약은 변경하지 않았다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/evidence_quality_gate.py` | 사고 유형별 근거 프로필을 정의하고, 검색 근거의 family(`legal`, `knia`, `general`), 사고 관련 tag/keyword/text match, 관련 근거 수, 누락 family, 약점을 산정한다. |
| `apps/agent/app/services/analysts/evidence_auditor.py` | 기존 근거 개수/평균 점수 기반 audit에 `scenario_evidence_coverage`를 추가하고, 기본 품질과 시나리오 관련성 품질 중 더 보수적인 값을 `evidence_quality`로 사용한다. |
| `apps/agent/scripts/test_agent_regression_scenarios.py` | 대표 사고 회귀 검증에서 `scenario_evidence_coverage` 필드 존재와 coverage level을 함께 확인한다. |
| `apps/agent/tests/test_evidence_quality_gate.py` | 후방 추돌 관련 근거, 신호위반 사고에 무관한 차선변경 근거, 근거 없음 상태를 단위 검증한다. |

현재 품질 게이트는 Agent 최종 판단을 즉시 차단하는 목적보다, `evidence_audit.scenario_evidence_coverage`와 `agent_judgment`가 근거 관련성 부족을 보수적으로 드러내도록 하는 목적에 가깝다. 대표 시나리오 회귀 기준은 이 필드가 항상 존재하고 `agent_judgment`와 함께 추적되는지를 검증한다.

## 2026-05-21 Agent 필수 근거 충족 기준 보강

Agent 근거 검색 품질 게이트를 한 단계 강화하여, 단순히 검색 결과가 존재하는 상태와 확정 판단에 가까운 상태를 분리했다. 사고 유형별로 필요한 근거군, 최소 전체 근거 수, 최소 사고 관련 근거 수, 평균 점수 기준을 `required_evidence`로 노출하고, 부족한 조건은 `missing_requirements`로 기록한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/evidence_quality_gate.py` | `EvidenceProfile`에 `required_families`, `min_total`, `min_relevant`, `min_average_score`를 추가했다. 후방추돌, 차선변경, 신호위반, 보행자, 어린이보호구역, 자전거 사고는 법령/판례 계열 근거와 KNIA 계열 근거를 모두 요구하며, 조건이 모두 충족될 때만 `decision_ready=true`와 `coverage_level=high`가 된다. |
| `apps/agent/app/services/judgment_contract.py` | evidence retrieval 단계가 `coverage_level=high`와 `decision_ready=true`일 때만 supported가 되도록 변경했다. `medium` 또는 `low` 근거는 결과가 존재하더라도 `needs_review`로 남기며, stage summary에 quality, coverage, missing requirement 수를 기록한다. |
| `apps/agent/tests/test_evidence_quality_gate.py` | 완전한 후방추돌 근거가 high coverage가 되는 경우와, 일부 근거만 있는 경우가 medium에 머무르는 경우를 검증한다. |
| `apps/agent/tests/test_judgment_contract.py` | scenario coverage가 medium이면 evidence retrieval stage가 supported가 아니라 needs_review로 남는지 검증한다. |

대표 회귀 시나리오 검증 결과 후방추돌, 차선변경, 신호위반은 `medium` coverage와 `needs_review` 상태를 유지한다. 자전거 사고는 직접 관련 근거가 부족해 `low` coverage로 낮아지며, 확정 판단 대신 추가 확인이 필요한 참고 결과로 남는다.

## 2026-05-21 Agent 취약 시나리오 정적 근거 보강

자전거, 보행자, 어린이보호구역 사고처럼 DB/KNIA 수집 상태에 따라 직접 관련 근거가 부족해질 수 있는 시나리오에 대해 정적 법률 보조 근거를 추가했다. 이 변경은 외부 API, DB schema, Redis key를 바꾸지 않고 Agent 내부 fallback 근거 품질을 높이는 작업이다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/static_legal_fallback.py` | 기존 후방추돌, 신호위반, 차선변경, 부상 관련 정적 근거에 `scenario_tags`를 추가했다. 신규로 자전거 주의의무, 자전거 과실비율 참고, 보행자·횡단보도, 어린이보호구역 정적 근거를 추가했다. |
| `apps/agent/app/services/rag_client.py` | DB 법률 검색 결과가 있더라도 정적 시나리오 보조 근거를 병합하도록 변경했다. 중복 근거는 `chunk_id`/URL/제목 기준으로 제거하고, 기존 limit보다 최대 3건까지만 보조 근거를 추가한다. |
| `apps/agent/tests/test_static_scenario_support.py` | 자전거 사고 입력에서 정적 근거가 자전거 관련 근거로 반환되고, evidence quality gate의 `scenario_relevant_evidence` 부족이 해소되는지 검증한다. |
| `apps/agent/scripts/test_agent_regression_scenarios.py` | 사용자 자전거 사고 회귀 시나리오에서 coverage가 `medium` 이상이고 관련 근거가 2건 이상인지 검증한다. |

검증 결과 자전거 사고는 기존 `low` coverage에서 `medium` coverage로 올라갔다. 보행자와 어린이보호구역 사고도 정적 시나리오 근거가 병합되어 직접 관련 근거를 확보한다. 다만 간단한 자연어 입력에서는 사고 세부 사실이 부족해 `required_input_fields` 또는 평균 점수 조건 때문에 `needs_review`가 유지된다.

## 2026-05-21 Agent 필수 입력 질문 계약 보강

간단한 자연어 사고 설명만으로는 `required_input_fields`가 남아 Agent 판단이 `needs_review`에 머무르지만, 기존 출력은 어떤 정보를 왜 보완해야 하는지 구조화하지 못했다. 필수 입력 부족을 사용자 보완 질문으로 연결하기 위해 Agent 내부에 `input_requirements` 계약을 추가했다. 이 변경은 DB schema, Redis key, 외부 API, 환경 변수는 변경하지 않고 Agent 결과 JSON과 사용자용 리포트 구성만 보강한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/input_requirements.py` | 사고 유형, 현재 structured facts, 자연어 설명, 누락 필드를 기준으로 `blocking_fields`, `optional_fields`, `questions`, `question_texts`를 생성하는 입력 요구사항 계약을 추가했다. 후방추돌, 차선변경, 신호위반, 보행자, 어린이보호구역, 자전거 사고별 핵심 보완 질문과 선택지를 정의했다. |
| `apps/agent/app/services/orchestrator.py` | 시나리오 분류 직후 `input_requirements`를 생성하고, 판단을 막는 필드만 evidence audit과 `agent_judgment.blocking_reasons`에 반영하도록 연결했다. |
| `apps/agent/app/services/analysts/evidence_auditor.py`, `apps/agent/app/services/keyword_recommender.py` | 기존의 `field 정보를 입력해 주세요`식 문구 대신 `input_requirements`의 사용자 질문을 `followup_questions`, `suggested_next_inputs`로 사용한다. |
| `apps/agent/app/services/report_composer.py`, `apps/agent/app/schemas.py` | Agent 최종 출력에 `input_requirements`와 `required_input_questions`를 포함한다. `structured_facts`에는 기존 `missing_fields`와 별도로 `required_input_fields`, `optional_input_fields`를 기록한다. |
| `apps/agent/app/services/judgment_contract.py` | `agent_judgment.input_requirements`에 입력 계약 버전, 판단 차단 필드, 선택 보완 필드, 질문 개수, 요약을 기록한다. |
| `apps/agent/app/services/elderly_friendly/plain_language_agent.py` | 쉬운 리포트의 `missing_info`가 raw field key 대신 사용자에게 바로 물어볼 수 있는 한국어 질문을 우선 표시하도록 변경했다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | Gateway fallback 리포트도 `required_input_questions`를 반영하고, 입력 계약 내부 필드는 일반 화면에 원시 기술 필드로 노출되지 않도록 필터링한다. |
| `apps/agent/tests/test_input_requirements.py` | 후방추돌 자연어 입력에서 사고 유형/상대 행동은 문맥으로 충족 처리하고, 인명피해 등 실제 필요한 보완 질문만 남는지 검증한다. |

예를 들어 `정차 중 뒤에서 추돌당했습니다.` 입력은 `accident_type`과 `opponent_behavior`를 다시 묻지 않고, `다친 사람이 있나요?`처럼 판단에 필요한 보완 질문을 우선 제시한다. 손상 정도나 신호 상태처럼 해당 사고에서 확정 판단을 직접 막지 않는 항목은 optional 또는 낮은 우선순위로 처리한다.

## 2026-05-21 결과 화면 보완 입력 및 재분석 흐름 추가

Agent의 `input_requirements` 계약을 실제 사용자 흐름에 연결하기 위해 결과 화면에서 보완 질문에 답하고 즉시 재분석할 수 있는 경로를 추가했다. 이 변경은 DB schema, Redis key, 외부 API, 환경 변수는 변경하지 않는다. 기존 `analysis_results.result` JSON과 `elderly_friendly_report.missing_info.questions`를 통해 질문 메타데이터를 전달하고, Gateway의 기존 `/api/v1/cases/:caseId/reanalyze` API를 확장해 보완 입력을 케이스와 새 분석 결과에 반영한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/elderly_friendly/elderly_report_schema.py` | `missing_info`에 사용자용 질문 메타데이터 `questions`를 추가했다. |
| `apps/agent/app/services/elderly_friendly/plain_language_agent.py` | `required_input_questions`를 `missing_info.questions`로 변환해 field, label, question, input_type, options를 사용자용 리포트에 싣는다. |
| `apps/gateway/src/main.ts` | `/api/v1/cases/:caseId/reanalyze`가 `structured_facts`, `selected_keywords`, `analysis_mode`를 받아 기존 케이스 입력과 병합하고 케이스 상태/최신 분석 결과를 갱신하도록 확장했다. 응답에는 `result`, `report`도 함께 반환한다. |
| `apps/gateway/src/lib/report-composer.ts` | `missing_info.questions`의 field/options를 사용자 입력 폼에서 쓸 수 있도록 안전하게 보존하고, 내부 `input_requirements` 원문은 계속 숨긴다. |
| `apps/frontend/src/api/client.ts` | `reanalyzeText` API 래퍼와 보완 입력용 `AccidentFacts` 필드를 추가했다. |
| `apps/frontend/src/components/easy/MissingInfoCard.vue` | 보완 질문 목록을 select/input 폼으로 표시하고 답변 제출 이벤트를 발생시키도록 확장했다. |
| `apps/frontend/src/components/easy/EasyReportView.vue` | `MissingInfoCard`의 답변 제출 이벤트를 결과 화면으로 전달한다. |
| `apps/frontend/src/views/CaseResultView.vue` | 케이스 정보와 리포트를 함께 불러오고, 보완 답변을 `structured_facts` patch로 변환해 `reanalyzeText`를 호출한 뒤 새 리포트를 즉시 표시한다. |
| `apps/gateway/test/report-composer.test.ts` | sanitize 후에도 사용자용 질문 field가 유지되고 내부 입력 계약 원문은 노출되지 않는지 검증한다. |

현재 보완 답변은 결과 화면에서 새 분석을 생성하는 흐름까지 연결되어 있다. 다음 단계에서는 재분석 후 `agent_judgment`와 근거 coverage가 실제로 개선됐는지 사용자에게 전후 비교로 보여주는 UX를 추가할 수 있다.

## 2026-05-22 SRP Refactor Baseline

This section records the first SRP cleanup pass so future changes can compare module boundaries against this baseline.

| Path | Responsibility after this pass |
| --- | --- |
| `apps/worker/worker/main.py` | Redis Stream consumer group setup, stream polling, ack, and short-lived job status cache updates. |
| `apps/worker/worker/job_processor.py` | Worker DB job orchestration, upload row loading, DB status/result updates, follow-up job enqueueing, and Agent submission coordination. |
| `apps/worker/worker/video_preprocess.py` | Owns `worker-video-preprocess-v1`, ffprobe video metadata probing, event frame time selection, ffmpeg frame extraction, and extracted frame descriptors. |
| `apps/worker/worker/frame_analysis.py` | Owns optional OpenAI image/frame observation calls, frame selection for cost control, response JSON parsing, and observation normalization. |
| `apps/gateway/src/config/env.ts` | Owns Gateway runtime environment defaults and cookie secure mode. |
| `apps/gateway/src/lib/request-guards.ts` | Owns route key generation plus user/admin request guard behavior. |
| `apps/gateway/src/routes/auth.ts` | Owns signup, login, refresh, logout, and current-user session routes. |
| `apps/gateway/src/routes/cases.ts` | Owns basic case CRUD routes: create case, list cases, read case detail, and patch editable case fields. |
| `apps/gateway/src/routes/uploads.ts` | Owns local upload routes, upload completion verification, local video content delivery, and video preprocess job enqueueing. |
| `apps/gateway/src/routes/analysis.ts` | Owns case analysis and report routes: text analysis, video analysis job enqueueing, result/report/easy-report lookup, reanalysis, job listing, and evidence lookup. |
| `apps/gateway/src/routes/knia.ts` | Owns KNIA public lookup/search routes and public KNIA Agent proxy routes. |
| `apps/gateway/src/routes/knia-admin.ts` | Owns KNIA admin collection/detail collection, embedding rebuild, JSON import, and cache invalidation routes. |
| `apps/gateway/src/routes/legal-admin.ts` | Owns legal/admin routes: legal KB ingest, legal embedding rebuild, and legal retrieval smoke test proxy. |
| `apps/agent/app/routers/internal.py` | Owns only `/internal/v1` router composition and includes domain-specific internal route modules. |
| `apps/agent/app/routers/internal_auth.py` | Owns the shared internal service token check for Agent internal routes. |
| `apps/agent/app/routers/internal_routes/analysis.py` | Owns text, video, and structured scenario analysis endpoint handlers. |
| `apps/agent/app/routers/internal_routes/jobs.py` | Owns the internal worker job processing endpoint. |
| `apps/agent/app/routers/internal_routes/legal.py` | Owns legal KB ingest, embedding rebuild, and retrieval-test internal endpoints. |
| `apps/agent/app/routers/internal_routes/knia.py` | Owns KNIA collection, matching, fault estimate, JSON/search, media-search, and embedding internal endpoints. |
| `apps/agent/app/routers/internal_routes/chat.py` | Owns the internal accident consultation chat endpoint. |
| `apps/agent/app/routers/internal_routes/cache.py` | Owns Agent semantic cache invalidation endpoint behavior. |
| `apps/agent/app/routers/internal_routes/health.py` | Owns the unauthenticated Agent health endpoint. |
| `apps/frontend/src/views/CaseDetailView.vue` | Owns case workspace page assembly, composable wiring, and high-level report placement only. |
| `apps/frontend/src/components/case/CaseWorkspaceHeader.vue` | Owns case workspace title/status and navigation actions. |
| `apps/frontend/src/components/case/CaseSummaryCard.vue` | Owns case status summary and workspace count metrics. |
| `apps/frontend/src/components/case/CaseInputStep.vue` | Owns accident description, structured fact inputs, analysis mode, and keyword input rendering. |
| `apps/frontend/src/components/case/CaseUploadStep.vue` | Owns local upload, selected upload, upload list, and video preview rendering. |
| `apps/frontend/src/components/case/CaseAnalysisStep.vue` | Owns text/video analysis action controls, status message, and analysis job list rendering. |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | Owns case workspace state and actions: case load/save, upload, preprocessing, analysis requests, job polling, report loading, and display formatting helpers. |
| `apps/frontend/tsconfig.json` | Sets `noEmit` so TypeScript source remains the only frontend source of truth under `apps/frontend/src`. |
| `.gitignore` | Prevents generated JavaScript from being tracked beside TypeScript source under `apps/frontend/src`. |

Remaining SRP debt to handle in later iterations:

- `apps/gateway/src/main.ts` is now a Gateway composition root with shared hooks, health checks, route-module registration, audit logging, and centralized error handling. Keep new API behavior inside route modules unless it changes shared Gateway lifecycle hooks.
- `apps/agent/app/services/orchestrator.py` now delegates context, evidence, analysis, reflection, and output enrichment to stage modules. Keep future stage-specific logic out of the orchestrator unless it only changes stage ordering.
- `apps/agent/app/routers/internal.py` is now thin; keep new internal endpoint behavior inside `apps/agent/app/routers/internal_routes/*`.
- `apps/worker/worker/main.py` is now a Redis consumer entrypoint; keep video preprocessing, vision analysis, DB persistence, and Agent submission in Worker service modules.
- `apps/frontend/src/views/CaseDetailView.vue` now delegates workspace state/actions to `useCaseWorkspace` and visual subsections to `apps/frontend/src/components/case/*`; keep future case workspace UI additions inside the owning section component unless they change page-level flow.
- KNIA parser/repository files are functionally cohesive but large; split only when adding new KNIA collection or persistence behavior.

## 2026-05-22 Frontend Case Workspace SRP Split

The case detail workspace was reduced so the Vue view owns page assembly while the API state machine lives in a composable and visual sections live in dedicated case components. This is behavior-preserving and does not alter public API routes, DTOs, DB schema, Redis keys, storage paths, environment variables, or external integrations.

| Path | Responsibility |
| --- | --- |
| `apps/frontend/src/views/CaseDetailView.vue` | Wires `useCaseWorkspace`, case section components, and `EasyReportView`; keeps only page-level layout. |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | Owns `useCaseWorkspace(caseId)`, including case load/save, preset handling, local upload, upload completion, video URL issuance, text/video analysis requests, job polling, easy-report loading, and display helpers. |
| `apps/frontend/src/components/case/CaseWorkspaceHeader.vue` | Renders title/status and refresh/result navigation actions. |
| `apps/frontend/src/components/case/CaseSummaryCard.vue` | Renders case status, description, keyword/upload/job counts. |
| `apps/frontend/src/components/case/CaseInputStep.vue` | Renders description, analysis mode, structured fact inputs, and keyword chips through props/events. |
| `apps/frontend/src/components/case/CaseUploadStep.vue` | Renders local upload controls, selected upload list, view/download actions, and video preview. |
| `apps/frontend/src/components/case/CaseAnalysisStep.vue` | Renders text/video analysis controls, user message, and job list. |
| `apps/frontend/scripts/test-display.mjs` | Includes the split case header component in display safety contract checks. |

Verification:

- `npm run build` in `apps/frontend`
- `npm run test:display` in `apps/frontend`
- `npm run test:chat` in `apps/frontend`

## 2026-05-22 Worker Job Processor SRP Split

Worker runtime responsibilities were separated so `apps/worker/worker/main.py` only owns Redis Stream consumption and status cache updates. Job-specific DB transitions, video preprocessing orchestration, Agent submission, and analysis result persistence now live in `apps/worker/worker/job_processor.py`. Existing video preprocessing and optional OpenAI frame analysis remain in `video_preprocess.py` and `frame_analysis.py`.

This change is behavior-preserving and does not alter API routes, DB schema, Redis key names, storage paths, environment variables, or external API contracts.

| Path | Responsibility |
| --- | --- |
| `apps/worker/worker/main.py` | Redis consumer group setup, stream polling, ack, and `job:v1:{jobId}:status` cache updates. |
| `apps/worker/worker/job_processor.py` | `video_preprocess`/`video_analyze` job processing, DB state changes, follow-up job enqueueing, Agent video analysis call, `analysis_results` insertion, and pure contract builders for worker tests. |
| `apps/worker/worker/video_preprocess.py` | ffprobe metadata probing and ffmpeg event-frame extraction. |
| `apps/worker/worker/frame_analysis.py` | Optional OpenAI frame observation provider and observation normalization. |
| `apps/worker/tests/test_job_processor_contract.py` | Tests canonical `video_analyze` payload, Agent video request payload, and analysis result value shaping without requiring DB/Redis. |

Verification:

- `python -m unittest discover -s tests` in `apps/worker`
- `python -m compileall worker tests` in `apps/worker`
- `docker compose exec -T worker python -m compileall worker`

## 2026-05-22 Worker Job Processor Contract Tests

Worker job payload/result shaping now has local tests that run without PostgreSQL, Redis, ffmpeg, or OpenAI credentials. The DB-facing worker functions still perform the same side effects, but canonical payload assembly was extracted into pure helpers so future changes to video providers or Agent input contracts can be checked quickly.

| Path | Change |
| --- | --- |
| `apps/worker/worker/job_processor.py` | Adds `build_video_analyze_payload()`, `build_agent_video_request()`, and `build_analysis_result_values()`. `process_job()` and `mark_failed()` now import `psycopg` lazily, and the retry decorator has a no-op fallback for local contract tests when `tenacity` is not installed. |
| `apps/worker/tests/test_job_processor_contract.py` | Verifies auto-enqueued video analysis payloads, Agent request metadata/summary preservation, used evidence ID extraction, risk flag fallback, and analyst output persistence shape. |

This change does not alter API routes, DB schema, Redis key names, storage paths, environment variables, external API calls, or public report payloads.

## 2026-05-22 GitHub Actions CI Baseline

The repository now has a hosted CI baseline for fast deterministic checks on `main` pushes and pull requests. It does not require real secrets, DB, Redis, Docker services, OpenAI calls, or public API credentials.

| Path | Change |
| --- | --- |
| `.github/workflows/ci.yml` | Adds separate Frontend, Gateway, Worker Contracts, and Agent Contracts jobs. Frontend runs build/display/chat checks, Gateway runs tests/build, Worker runs local unittest/compile checks, and Agent runs requirements install, compile, internal route contract check, and deterministic regression scenarios with LLM disabled. |
| `apps/agent/app/services/rag/two_stage_cache.py` | Degrades KNIA JSON cache/search to an empty result with `disabled_reason` when `DATABASE_URL` is unavailable, allowing deterministic Agent contract checks without DB services. |
| `apps/agent/tests/test_knia_cache_fallback.py` | Verifies the no-DB KNIA cache fallback using stdlib unittest so CI can run it without pytest. |

Deferred CI work: full Docker E2E and actual external API smoke checks should only be added after CI secrets, service health timing, and cost controls are explicitly configured.

## 2026-05-22 Frontend TypeScript Source Hygiene

The frontend source tree is now TypeScript-only for source modules. Previously tracked generated JavaScript mirrors under `apps/frontend/src` were removed because `tsconfig.json` already uses `noEmit`, and the app imports the `.ts`/`.vue` sources directly through Vite.

| Path | Change |
| --- | --- |
| `apps/frontend/src/**/*.js` | Removed tracked generated JavaScript duplicates for API clients, router, stores, types, main entry, and display sanitizer. |
| `.gitignore` | Adds `apps/frontend/src/**/*.js` so emitted JavaScript cannot be reintroduced beside TypeScript source. |
| `apps/frontend/scripts/test-display.mjs` | Reads `src/utils/displaySanitizer.ts` instead of the removed JavaScript mirror. |

Verification:

- `npm run build` in `apps/frontend`
- `npm run test:display` in `apps/frontend`
- `npm run test:chat` in `apps/frontend`

## 2026-05-22 Agent Regression Guard Update

This update strengthens the Agent fault judgment regression guard around user perspective and video-derived facts.

| Path | Change |
| --- | --- |
| `apps/agent/app/services/accident_perspective.py` | Rear-end role inference now treats strong structured facts (`stopped=True`, `opponent_behavior=rear_collision`, and no sudden brake) as higher priority than conflicting natural-language role phrases. This prevents a stopped rear-end victim from being mapped as the following/striking vehicle when video-derived facts indicate otherwise. |
| `apps/agent/scripts/test_agent_regression_scenarios.py` | Added `video_rear_end_overrides_conflicting_user_fact`, which runs `analyze_video_case()` with high-confidence frame observations and conflicting user text. It verifies video fact arbitration, conflict recording, front-vehicle role mapping, and final 0:100 user-perspective fault mapping. |

Verification command:

`docker compose exec -T agent python scripts/test_agent_regression_scenarios.py`

Additional syntax verification:

`docker compose exec -T agent python -m compileall app scripts`

Route contract verification:

`docker compose exec -T agent python scripts/check_internal_routes.py`

Combined Agent verification command:

`powershell -ExecutionPolicy Bypass -File scripts/verify_agent_regression.ps1`

## 2026-05-22 Agent Internal Route SRP Split

Agent internal API handlers were moved out of the large `apps/agent/app/routers/internal.py` file into responsibility-specific modules under `apps/agent/app/routers/internal_routes/`. This change preserves existing `/internal/v1/*` paths, request/response DTOs, DB schema, Redis keys, storage paths, environment variables, and external integrations.

| Path | Responsibility |
| --- | --- |
| `apps/agent/app/routers/internal.py` | Keeps only the `/internal/v1` `APIRouter` and includes domain route modules. |
| `apps/agent/app/routers/internal_auth.py` | Shares internal token verification across protected internal routes. |
| `apps/agent/app/routers/internal_routes/analysis.py` | Text, video, and structured scenario analysis endpoints. |
| `apps/agent/app/routers/internal_routes/jobs.py` | Worker job processing endpoint. |
| `apps/agent/app/routers/internal_routes/legal.py` | Legal KB ingest, embedding rebuild, and retrieval smoke endpoint. |
| `apps/agent/app/routers/internal_routes/knia.py` | KNIA collection, ranking/detail, matching, fault estimate, JSON/search, media-search, and embedding endpoints. |
| `apps/agent/app/routers/internal_routes/chat.py` | Chat consultation endpoint. |
| `apps/agent/app/routers/internal_routes/cache.py` | Cache invalidation endpoint. |
| `apps/agent/app/routers/internal_routes/health.py` | Agent health endpoint. |
| `apps/agent/scripts/check_internal_routes.py` | Verifies that the required internal route paths are still registered after router refactors. |
| `scripts/verify_agent_regression.ps1` | Runs Docker-based Agent compile check, internal route contract check, and representative Agent regression scenarios. |

## 2026-05-22 Completion Priority Backlog

This backlog separates trust-critical reinforcement from deferred enhancements. Use it to decide future development order before adding new features.

### P0 Completed

| Priority | Area | Current State | Remaining Work |
| --- | --- | --- | --- |
| P0 | Agent regression automation | `scripts/verify_agent_regression.ps1` now runs compile, internal route contract, and representative judgment regression scenarios. `scripts/verify_core.ps1` calls this guard during Docker checks. `.github/workflows/ci.yml` runs frontend, gateway, worker contract, and Agent contract/regression checks on push/PR. | 완료. CI에서 secret/service dependency가 필요한 실제 영상 full E2E는 로컬 운영 검증으로 유지한다. |
| P0 | Agent execution trace | Outputs include `video_input_contract`, `fact_arbitration`, `evidence_audit`, `agent_judgment`, and `presentation_policy`. A safe admin diagnostic API now exposes stage and packet summaries without raw user text. Public easy-report uses sanitized cards only. | 완료. 개발자 페이지 확장은 local-only P1/P2 보조 도구로만 다룬다. |
| P0 | Reflection/reverification loop | `reflection_loop` now performs one bounded evidence requery when requeryable evidence requirements are missing, records next action, builds scenario-specific Korean requery terms, and exposes safe `agent_process_card.decision_notes`. | 완료. 향후 개선은 검색 품질 튜닝이며 P1로 분류한다. |
| P0 | Agent SRP | `orchestrator.py` now delegates input context, evidence collection, analyst execution, reflection requery, and final output enrichment to dedicated stage modules. | 완료. 이후 Agent 변경은 소유 stage module과 테스트 안에서 진행한다. |

### Reinforce Next

| Priority | Area | Current State | Needed Work |
| --- | --- | --- | --- |
| P1 | Gateway SRP | `gateway/src/main.ts` remains the composition root. Auth/session, case CRUD, upload, analysis/report, public KNIA, KNIA admin, and legal/admin routes live under `apps/gateway/src/routes/`. | Keep new API behavior in route modules; split large route modules only when they grow further. |
| P1 | Worker SRP | `main.py` now only consumes Redis Stream messages and delegates DB job processing to `job_processor.py`; ffprobe/ffmpeg preprocessing and OpenAI frame analysis live in dedicated modules. Local Worker contract tests now cover video analyze payload, Agent video request payload, and analysis result value shaping. | Add DB/Redis integration tests only when expanding queue persistence or video provider behavior. |
| P1 | Frontend source hygiene | `apps/frontend/src` is now TypeScript-only for source files; tracked generated `.js` duplicates were removed and `.gitignore` blocks them from returning. | Keep new frontend source in `.ts`/`.vue` files and avoid committing emitted JavaScript beside source. |
| P1 | Evidence/search quality | Structured fact 기반 검색어 확장과 차선변경/보행자/스쿨존 정적 과실비율 fixture를 추가했다. P0 guard는 unsupported result가 final로 보이지 않게 유지한다. | 실제 KNIA/법률 DB 수집량이 늘어난 뒤 매칭 품질 회귀를 추가하고, 필요한 시나리오에 한해 query term을 더 튜닝한다. |
| P1 | Video observation validation | Upload/preprocess/video_analyze/easy-report smoke passes with OpenAI frame analysis disabled by default. | When API cost/key policy is ready, run `video_agent_e2e.py` with `--require-frame-observations --require-agent-video-facts` and tune observation mapping. |

### Defer Until Core Trust Is Stable

| Area | Why Deferred |
| --- | --- |
| UI polish/layout | Useful, but less important than judgment correctness and evidence traceability. |
| Developer page expansion | Local-only diagnostic aid; should not block service logic. |
| Full multi-agent process orchestration | Current analyst modules can support MVP; process-level agents add complexity. |
| Standard MCP adoption | Current internal registry is enough for MVP; standard MCP needs stronger security/tool isolation design. |
| Token/cost dashboard | LLM use is already gated; detailed billing UI can come after core loops. |
| S3/direct upload migration | Local storage works for current MVP and collaboration constraints. |
| Specialized traffic-accident video model | Desired later; current frame extraction plus optional OpenAI observation path is enough for next stabilization. |

## 2026-05-22 Agent Execution Trace Update

This update addresses the lecture-derived gap around Agent pipeline observability, packet-style data flow, and production guardrails. It adds a safe execution trace to each Agent analysis result without exposing raw user text or secrets.

| Path | Change |
| --- | --- |
| `apps/agent/app/services/agent_execution_trace.py` | Adds `agent-execution-trace-v1`, a safe metadata-only trace builder covering input normalization, fact arbitration, scenario classification, evidence retrieval, analyst execution, claim validation, judgment contract, and follow-up loop stages. |
| `apps/agent/app/services/orchestrator.py` | Adds `agent_trace` to final Agent output after the judgment contract is applied, and records `agent_trace_version` in `model_info`. |
| `apps/agent/app/schemas.py` | Adds `agent_trace` to `AnalysisOutput` so downstream Gateway/frontend consumers can safely inspect the Agent pipeline state. |
| `apps/agent/tests/test_orchestrator.py` | Adds contract assertions for trace version, safe metadata policy, stage IDs, video contract presence, video observation counts, and raw-text exclusion. |

The trace intentionally records counts, statuses, confidence-related state, and missing requirements rather than hidden chain-of-thought or raw user descriptions. This keeps the Agent debuggable while preserving privacy and output safety.

## 2026-05-22 Agent Reflection Loop Update

This update makes the Agent recovery path explicit when evidence coverage, KNIA/legal basis, or required inputs are insufficient.

| Path | Change |
| --- | --- |
| `apps/agent/app/services/reflection_loop.py` | Adds `agent-reflection-loop-v1`, a bounded recovery contract. It decides whether one evidence requery should be attempted, records missing requirements and blocking input fields, and resolves the final next action as `finalize`, `request_missing_input`, `present_reference_only`, or `manual_review`. |
| `apps/agent/app/services/orchestrator.py` | Runs one conservative legal evidence requery when requeryable evidence requirements are missing, merges newly found evidence, reruns analysts/audit/claim validation, then attaches `reflection_loop` to the final output. |
| `apps/agent/app/services/agent_execution_trace.py` | Adds a `reflection_loop` trace stage with requery attempt status, added evidence count, iteration count, and next action. |
| `apps/agent/app/schemas.py` | Adds `reflection_loop` to `AnalysisOutput`. |
| `apps/agent/tests/test_orchestrator.py` | Adds assertions for reflection loop version, next action, trace stage, and video-case compatibility. |

The loop is deliberately bounded to one requery attempt to avoid uncontrolled cost or latency. If evidence remains insufficient, the judgment contract and presentation policy keep the result as reference-only or request user-supplied missing facts.

## 2026-05-22 Video Fact Explanation Card

This update makes video-derived fact arbitration visible to users in safe Korean copy. When frame observations conflict with user input or are applied to Agent facts, the public report explains which physical fact was reflected without exposing raw contracts such as `video_input_contract`, `fact_arbitration`, frame-analysis provider strings, raw value keys, or internal reasons.

| Path | Change |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | Converts Agent video contracts into `video_fact_explanation_card`, including applied video facts, user-input comparison items, deferred observations, confidence labels, and representative frame counts. |
| `apps/frontend/src/components/easy/VideoFactExplanationCard.vue` | Renders the video fact explanation card with Korean labels and safe summaries only. |
| `apps/frontend/src/components/easy/EasyReportView.vue` | Places the video fact card after the Agent process card and before the fault ratio card. |
| `apps/gateway/test/report-composer.test.ts` | Verifies that the card is generated and raw arbitration/source/reason/value keys are not exposed. |

No DB schema, Redis key, storage path, environment variable, or external API contract changed. Public easy-report responses may now include `video_fact_explanation_card`.

## 2026-05-22 Video Conflict Follow-Up Questions

This update connects video/user fact conflicts to the existing follow-up and reanalysis loop. When `fact_arbitration.conflicts` contains a safe input field such as `lane_change_actor`, Gateway now adds a Korean single-choice question to `missing_info.questions`. The frontend already submits those answers through `MissingInfoCard` and `/api/v1/cases/:caseId/reanalyze`, so no new API route or DB schema was required.

| Path | Change |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | Adds `composeVideoConflictQuestions()` and merges safe video conflict questions into `missing_info.questions` while avoiding duplicates. |
| `apps/gateway/test/report-composer.test.ts` | Verifies that a video/user conflict generates a usable follow-up question with the canonical field preserved and safe Korean options. |

The question field is preserved only for known safe follow-up fields so the existing reanalysis normalizer can update structured facts. Raw video contracts and internal arbitration metadata remain hidden from public report rendering.

## 2026-05-22 Reanalysis Judgment Delta Card

This update strengthens the existing reanalysis comparison card so users can understand what changed after follow-up answers are submitted. The Gateway now passes the normalized follow-up answer summary into `composeReanalysisChangeCard()`, and the card includes safe decision notes for answered fields, unresolved fields, ignored fields, judgment status transition, and whether the bounded evidence requery ran.

| Path | Change |
| --- | --- |
| `apps/gateway/src/main.ts` | Passes `normalizedFollowup` into `composeReanalysisChangeCard()` after `/api/v1/cases/:caseId/reanalyze`. |
| `apps/gateway/src/lib/report-composer.ts` | Adds safe `decision_notes` and a reflected-answer count to `analysis_change_card`. |
| `apps/frontend/src/components/easy/AnalysisChangeCard.vue` | Renders `decision_notes` under a judgment-change summary section. |
| `apps/gateway/test/report-composer.test.ts` | Verifies reflected answer counts and safe Korean field labels in the reanalysis comparison card. |

No new API route, DB schema, Redis key, storage path, environment variable, or external integration was added. The existing reanalysis response payload now carries richer user-safe comparison metadata.

## 2026-05-22 Core Verification Entry Point

This update converts the manually run project checks into a repeatable PowerShell entry point for local regression verification. It does not change service APIs, DB schema, Redis keys, storage paths, environment variables, or external integrations.

| Path | Change |
| --- | --- |
| `scripts/verify_core.ps1` | Runs Gateway tests/build, Frontend build/display/chat checks, optional Docker compose build/start, the Agent regression guard script, and Gateway `/health` through the edge service. |
| `scripts/verify_agent_regression.ps1` | Runs Agent compile check, internal route contract verification, and representative Agent regression scenarios in Docker. |
| `apps/agent/scripts/check_internal_routes.py` | Fails fast when required `/internal/v1/*` paths are not registered after Agent router refactors. |
| `docs/OPERATIONS.md` | Documents the one-command verification flow plus `-SkipDockerBuild` and `-SkipDockerChecks` options. |
| `DEVELOPMENT_PROMPT.md` | Adds the core regression command to the verification policy for changes that affect Agent judgment, Gateway report composition, Frontend result display, video facts, or follow-up/reanalysis flows. |

Primary command:

`powershell -ExecutionPolicy Bypass -File scripts/verify_core.ps1`

Use this before committing trust-critical changes so rear-end, lane-change, signal-violation, bicycle/pedestrian, and video/user-conflict scenarios remain covered by the Agent regression script.

## 2026-05-22 Admin Agent Trace Diagnostic API

This update adds an administrator-only diagnostic API for Agent pipeline observability. It keeps the existing public report sanitization intact and exposes only safe metadata summaries for developers or operators.

| Path | Change |
| --- | --- |
| `apps/gateway/src/lib/agent-diagnostics.ts` | Adds `agent-trace-diagnostic-v1`, which summarizes Agent trace steps, packet metadata, judgment contract, reflection state, video input contract counts, fact arbitration counts, evidence coverage, and presentation policy while filtering raw user text, secrets, tokens, emails, and raw evidence ids. |
| `apps/gateway/src/routes/agent-diagnostics.ts` | Registers `GET /api/v1/admin/cases/:caseId/agent-trace`, guarded by login plus admin role or `x-admin-token`. The route returns the latest result or a specified `version`. |
| `apps/gateway/src/main.ts` | Wires the diagnostics route module without adding the route body directly to the composition root. |
| `apps/gateway/test/agent-diagnostics.test.ts` | Verifies that packet summaries remain useful while raw text, email, token, and chunk id-like values are filtered. |
| `docs/api/openapi.yaml`, `docs/OPERATIONS.md` | Documents the admin trace diagnostic endpoint and its safety constraints. |

The endpoint is intended for internal project inspection, not normal user UI. It does not change DB schema, Redis keys, storage paths, environment variables, external API contracts, or public easy-report behavior.

## 2026-05-22 Gateway KNIA Route Split

Gateway KNIA routes were moved out of `apps/gateway/src/main.ts` into route modules as part of the SRP cleanup. Public KNIA lookup/search routes stay in `apps/gateway/src/routes/knia.ts`; administrator collection, embedding, JSON import, and cache invalidation routes now live in `apps/gateway/src/routes/knia-admin.ts`. This change does not alter API paths, DB schema, Redis keys, storage paths, or external Agent endpoints.

| Path | Responsibility |
| --- | --- |
| `apps/gateway/src/routes/knia.ts` | Registers KNIA ranking, chart detail, adjustment/reference, match, fault estimate, myaccident menu/tree, JSON search, and media search routes. |
| `apps/gateway/src/routes/knia-admin.ts` | Registers admin KNIA collection, ranking detail collection, embedding rebuild, JSON import, JSON embedding rebuild, and cache invalidation routes. |
| `apps/gateway/src/routes/legal-admin.ts` | Registers legal/admin ingest, legal embedding rebuild, and legal retrieval-test routes. It preserves the existing Agent internal endpoints and admin guard behavior. |
| `apps/gateway/src/main.ts` | Keeps shared Fastify plugin setup, trace/auth/rate-limit/idempotency/audit/error hooks, health checks, and route-module registration. |

Verification:

- `npm run build` in `apps/gateway`

## 2026-05-22 Agent Orchestrator SRP Stage Split

This update reduces `apps/agent/app/services/orchestrator.py` to stage sequencing and final stage handoff. Input normalization, evidence collection, analyst execution, bounded reflection requery, and output enrichment are now delegated to dedicated modules. The change is behavior-preserving and does not alter public API DTOs, DB schema, Redis keys, storage paths, environment variables, or external integrations.

| Path | Responsibility |
| --- | --- |
| `apps/agent/app/services/orchestration_context.py` | Builds `CaseContext`: video context, normalized input, scenario classification, user vehicle role inference, party action guide, input requirements, and follow-up loop state. |
| `apps/agent/app/services/orchestration_evidence.py` | Builds `EvidenceBundle`: KNIA chart matching, KNIA JSON search, KNIA fault/reference evidence, legal retrieval, evidence normalization, and duplicate merging helpers. |
| `apps/agent/app/services/orchestration_analysis.py` | Builds `AnalysisBundle` and `ReflectionStageResult`: analyst outputs, evidence audit, claim-evidence audit, KNIA fault application, and one bounded evidence requery. |
| `apps/agent/app/services/orchestration_output.py` | Enriches the composed output with judgment contract effects, reflection loop, execution trace, elderly-friendly report, KNIA calculation metadata, and retrieval/scenario model metadata. |
| `apps/agent/app/services/orchestration_stages.py` | Lightweight export facade for the stage functions and dataclasses. |
| `apps/agent/app/services/orchestrator.py` | Keeps request entry points and orchestrates stage order, judgment contract creation, reflection loop creation, report composition, and output enrichment handoff. |

Verification focus remains the same: Agent compile check and representative regression scenarios must pass after future changes to these stage modules.

## 2026-05-22 Agent Output Enrichment SRP Split

The final Agent output enrichment step now lives in `apps/agent/app/services/orchestration_output.py`. This keeps `orchestrator.py` from accumulating KNIA/report/trace metadata assembly whenever the response contract grows. The public `AnalysisOutput` shape, API routes, DB schema, Redis keys, storage paths, environment variables, and external integrations are unchanged.

| Path | Responsibility |
| --- | --- |
| `apps/agent/app/services/orchestration_output.py` | Owns `enrich_analysis_output()`, `_attach_knia_fault_estimate()`, and `_build_retrieval_model_info()` for final response metadata assembly. |
| `apps/agent/app/services/orchestration_stages.py` | Re-exports `enrich_analysis_output()` with the other stage helpers. |
| `apps/agent/app/services/orchestrator.py` | Calls `enrich_analysis_output()` after composing the base analysis payload. |

Verification focus:

- `docker compose exec -T agent python -m compileall app scripts`
- `docker compose exec -T agent python scripts/test_agent_regression_scenarios.py`
