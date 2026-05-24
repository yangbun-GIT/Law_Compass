# LawCompass 프로젝트 변화 기록

작성일: 2026-05-24  
비교 기준: `docs/PROJECT_BASELINE_2026-05-21.md`  
현재 기준: `SYSTEM_OVERVIEW.md`, `docs/OPERATIONS.md`, `docs/OPERATING_RISK_ROADMAP.md`, `git log 97cdc92..HEAD`

이 문서는 2026-05-21 인수 직전 베이스라인과 2026-05-24 현재 프로젝트 상태를 비교하기 위한 변화 기록이다. `docs/PROJECT_BASELINE_2026-05-21.md`는 과거 기준점으로 유지하고, 이후 개발로 바뀐 내용은 이 문서와 `SYSTEM_OVERVIEW.md`에 누적한다.

## 1. 변화 요약

| 항목 | 2026-05-21 베이스라인 | 2026-05-24 현재 |
| --- | --- | --- |
| 전체 방향 | 교통사고 AI 분석 MVP의 기본 서비스 구조와 화면이 존재 | Agent 신뢰 골격, 영상 관찰값 계약, 근거 검증, 사용자 결과 카드, 운영 검증 루틴이 크게 보강됨 |
| 변경 규모 | 인수 직전 스냅샷 | 기준 커밋 이후 94개 커밋, 172개 파일 변경 |
| 구조 보강 | Gateway route와 Agent orchestrator에 책임 집중이 남아 있음 | Gateway route, Agent internal route, Agent orchestration, Worker job 처리, Frontend case workspace가 책임별로 분리됨 |
| Agent 판단 | 텍스트/영상 요약 기반 분석과 KNIA/RAG가 있으나 최종성·근거 품질 gate가 약함 | judgment contract, evidence audit, claim-evidence audit, reflection loop, source resilience, quality packet으로 판단 안전성이 강화됨 |
| 영상 처리 | ffprobe/ffmpeg 대표 프레임 4장, 영상 원본 직접 vision 분석 없음 | 대표 프레임 추출, 선택적 OpenAI Responses API 프레임 분석, 영상-사용자 사실 중재, 보류/충돌/반영 표시까지 연결됨 |
| 사용자 결과 | 쉬운 리포트와 근거 표시가 기본 구현 | 결론, 보완 질문, 과실 참고 범위, 영상 사실, 근거 신뢰도, Agent 과정, 전문가 안내, 재분석 변화 카드가 분리됨 |
| 검증 | 제한적 테스트와 운영 스모크 중심 | core verification, Agent regression, Worker contract, Gateway report tests, reference guidance/evidence/calibration 평가 도구가 추가됨 |
| 운영 리스크 | S3, 외부 API, 영상 AI 고도화, route/test 정리가 미완성으로 남음 | OpenAI 비용, fallback 의존, 원문 DB 부족, S3 전환, API quota, UI 수용성 로드맵이 별도 문서화됨 |

## 2. 기준 문서 체계 변화

| 문서 | 변화 |
| --- | --- |
| `DEVELOPMENT_PROMPT.md` | Agentic Design 원칙, 단일 책임 원칙, 법률 가이드 한계, 운영 리스크 로드맵 참조, 문서 언어 통일 기준이 추가됐다. |
| `SYSTEM_OVERVIEW.md` | 기존 구조 명세를 넘어 실제 개발 단계, 완료 범위, 테스트 결과, 남은 리스크가 누적되는 중심 인수인계 문서가 됐다. |
| `docs/OPERATIONS.md` | 실행 방법 중심에서 Agent/영상/프레임 분석/fixture/reference 평가/관리자 진단까지 포함한 운영 체크리스트로 확장됐다. |
| `docs/OPERATING_RISK_ROADMAP.md` | 신규 문서다. OpenAI 사용량, 정적 fallback, 원문 DB, S3, API 제한, UI 수용성 리스크를 제품 완성 로드맵으로 분류한다. |
| `tests/fixtures/video_accuracy/reference_hardening_minimal/*` | 신규 synthetic fixture다. 실제 영상과 변호사 의견 원문 없이 reference 평가 gate를 재현한다. |

## 3. 서비스별 변화

### Frontend

초기 상태에서는 로그인/회원가입, 대시보드, 케이스 생성/상세/결과, 영상 업로드, KNIA 조회, AI 채팅이 기본 구현되어 있었다.

현재 변화:

- 대시보드와 메인 화면 비율, 인증 폼, 케이스 진행 UI가 정리됐다.
- 케이스 입력, 업로드, 분석, 요약, 헤더가 `components/case/*`와 `useCaseWorkspace.ts`로 분리됐다.
- 결과 화면에 `TopConclusionCard`, `MissingInfoCard`, `VideoFactExplanationCard`, `EvidenceReliabilityCard`, `AgentProcessCard`, `ExpertGuidanceCard`, `AnalysisChangeCard`가 추가되어 사용자에게 판단 상태를 나눠 보여준다.
- 영상 관찰값 0개, 확인 필요, 일부 반영, 충돌, 참고 관찰 상태가 사용자 안전 문구로 표시된다.
- 추적용 raw payload, token, 내부 id, evidence chunk id가 일반 화면에 노출되지 않도록 sanitizer와 Gateway composer가 함께 보강됐다.
- tracked generated `.js` source가 제거되고 TypeScript/Vue source 중심으로 정리됐다.

남은 점:

- Capacitor/mobile native packaging은 여전히 미적용이다.
- 화면별 정식 UI 자동화 테스트는 아직 제한적이다.
- 사용자 수용성 검증은 5개 reference 샘플 기준의 문구/흐름 점검이 다음 과제다.

### Gateway

초기 상태에서는 `apps/gateway/src/main.ts`에 route가 과도하게 집중되어 있었고 validation/error UX가 약했다.

현재 변화:

- `main.ts`는 composition root에 가까워졌고, auth, cases, uploads, analysis, KNIA, KNIA admin, legal admin, agent diagnostics route로 분리됐다.
- 공통 환경 설정, 오류 응답, request guard, followup normalizer, report composer 책임이 분리됐다.
- 재분석 시 이전 결과와 새 결과를 비교해 `analysis_change_card`를 만든다.
- 관리자 전용 Agent trace 진단 API가 추가됐다. 이 API는 raw user text, secret, token, raw evidence id를 숨기고 stage/count/status 중심으로 보여준다.
- easy-report composer가 Agent judgment, evidence reliability, video input contract, expert guidance, missing info, reanalysis delta를 사용자용 카드로 변환한다.

남은 점:

- 사용자별 quota와 OpenAI 사용량 기반 제한은 아직 없다.
- S3 provider는 여전히 비활성 상태다.
- 큰 route module은 향후 기능이 더 늘면 추가 분리 대상이다.

### Agent

초기 상태에서는 FastAPI 내부 API, 사고 분석 orchestrator, 법률 RAG, KNIA 수집/검색/매칭, optional LLM 분석가가 있었다. 다만 근거 품질, 최종성, 입력 부족, 영상-사용자 충돌 처리의 안전 장치가 현재보다 약했다.

현재 변화:

- Agent 판단 결과에 `judgment_contract`가 적용되어 근거 부족 또는 입력 부족 시 확정 판단처럼 보이지 않게 됐다.
- `claim_evidence_validator`, `evidence_quality_gate`, `evidence_source_status`, `agent_quality_packet`이 추가되어 근거 충족도와 fallback 상태를 추적한다.
- `input_requirements`가 추가되어 결론을 좌우하는 누락 정보와 보완 질문을 구조화한다.
- `reflection_loop`가 1회 제한 재검색/복구 경로를 제공한다.
- `agent_execution_trace`가 안전한 stage-level trace를 남긴다.
- `llm_policy`가 LLM 사용 허용/차단/실패/fallback 이유를 명시한다.
- 전문가 안내는 법률 관점 예상, 보험 처리 예상, 근거, 추가 확인 항목으로 나뉘어 `expert_guidance_sections`와 사용자 카드로 전달된다.
- Agent orchestration은 context, evidence, analysis, output stage module로 분리됐다.
- internal route도 analysis, cache, chat, health, jobs, KNIA, legal route로 분리됐다.

남은 점:

- 실제 KNIA/법령/판례 원문 DB coverage는 제품 기준으로 더 확장해야 한다.
- 정적 fallback은 보조 안전장치이며 최종 근거 DB를 대체하지 않는다.
- OpenAI analyst token usage는 아직 DB에 영속화되지 않는다.
- 사고 2 신호 전환 샘플은 근거 선택과 보완 질문 우선순위가 아직 미흡하다.

### Worker

초기 상태에서는 Worker가 Redis Streams job 처리, ffprobe metadata, ffmpeg 대표 프레임 4장 추출, Agent video analyze 호출을 수행했다.

현재 변화:

- `main.py`의 책임이 줄고 `job_processor.py`, `video_preprocess.py`, `frame_analysis.py`로 책임이 분리됐다.
- 대표 프레임 추출은 짧은 사고 영상의 전후 맥락을 살리도록 개선됐다.
- `ENABLE_OPENAI_FRAME_ANALYSIS=1`일 때 OpenAI Responses API 이미지 입력으로 선별 프레임을 분석해 관찰값을 생성한다.
- OpenAI 프레임 분석은 비용 방지를 위해 기본 비활성화이며, 최대 프레임, 출력 토큰, detail, timeout이 환경변수와 코드 상한으로 제한된다.
- fixture 모드가 추가되어 `rear_end`, `held_quality`, `conflict_stopped` 같은 흐름을 실제 OpenAI 비용 없이 검증할 수 있다.
- Worker contract tests가 추가됐다.

남은 점:

- S3 object 입력 처리는 아직 없다.
- 교통사고 특화 비전 모델은 아직 도입되지 않았다.
- 실제 영상 데이터가 더 쌓이면 field별 confidence threshold 튜닝이 필요하다.

## 4. Agent/영상 정확도 평가 체계 변화

초기 베이스라인에서는 영상 전문 분석이 미구현 또는 전처리 요약 중심이었다. 현재는 “제품 정확도 보장”이 아니라 “정확도 평가 골격”이 완성된 상태다.

추가된 주요 흐름:

- `scripts/video_agent_e2e.py`: 실제 영상 업로드, 전처리, video analyze, easy-report, expert guidance까지 확인한다.
- `scripts/video_accuracy_batch.py`: 여러 사고 영상 manifest를 기준으로 batch 평가를 수행한다.
- `scripts/reference_guidance_eval.py`: 영상 관찰값과 전문가 reference 쟁점이 근거 대조 단계로 넘어갈 수 있는지 평가한다.
- `scripts/reference_evidence_alignment_eval.py`: 근거 family와 title/reason이 reference 쟁점에 맞는지 평가한다.
- `scripts/reference_guidance_calibration_eval.py`: 과실 범위, 보완 질문 우선순위, 사용자 흐름이 reference와 맞는지 평가한다.
- `scripts/validate_video_accuracy_manifest.py`: 실제 OpenAI 호출 전 manifest 사전 검증을 수행한다.
- `scripts/verify_reference_hardening_fixture.py`: 민감정보 없는 synthetic fixture로 reference gate를 재현한다.

현재 최신 OpenAI ON 재측정 결과:

| 항목 | 결과 |
| --- | --- |
| 대상 | 사고 영상 1~5번 |
| 모델/정책 | `gpt-4.1-mini`, `detail=low`, 초기 측정은 최대 6프레임/현재 운영 기본은 최대 10프레임, 출력 900토큰 기준 |
| batch pipeline | 5개 모두 통과 |
| 관찰값 흐름 | 전체 20개, 수용 8, 보류 6, 참고 5 |
| 판단 반영 | 4개 |
| 기존 입력 확인 | 2개 |
| 충돌 | 2개 |
| readiness | 사고 1, 2, 4는 근거 대조 준비. 사고 3, 5는 충돌 해소 필요 |
| 잔여 이슈 | 사고 2 신호 전환 샘플에서 근거 카드와 첫 질문이 신호/CCTV보다 급정거/후방추돌 쪽으로 치우침 |

## 5. 테스트/검증 체계 변화

| 영역 | 초기 상태 | 현재 상태 |
| --- | --- | --- |
| 핵심 검증 | 제한적 스모크와 수동 확인 중심 | `scripts/verify_core.ps1`로 Gateway, Frontend, Agent, Worker, reference fixture를 묶어 확인 |
| Agent 회귀 | 일부 스크립트/테스트 | `scripts/verify_agent_regression.ps1`와 다수 Agent unit/script 테스트 추가 |
| Gateway report | 제한적 | `report-composer.test.ts`, `followup-normalizer.test.ts`, `agent-diagnostics.test.ts`, route test 추가 |
| Worker | 제한적 | frame analysis, job processor contract test 추가 |
| 영상 평가 | 개별 E2E 중심 | batch, reference guidance, evidence alignment, calibration, manifest preflight로 확장 |
| CI | 명확한 baseline 부족 | GitHub Actions workflow로 deterministic checks 추가. 실제 OpenAI/외부 API/Docker E2E는 로컬 운영 검증으로 유지 |

## 6. 초기 미완성 항목의 변화 상태

| 베이스라인 미완성 항목 | 현재 변화 |
| --- | --- |
| S3 direct upload | 아직 미구현. 운영 리스크 로드맵 P2로 재분류됐다. |
| 모바일 앱/Capacitor | 아직 미적용. 현 단계에서는 웹 MVP 우선이다. |
| 영상 전문 분석 | OpenAI 프레임 분석과 평가 골격까지 보강됨. 교통사고 특화 모델은 후속 검토다. |
| 표준 MCP | 아직 미적용. 현재는 내부 tool registry와 deterministic Agent pipeline을 우선한다. |
| Gateway route 구조 | 큰 폭으로 개선됨. route module 분리 완료. |
| Gateway validation UX | 오류 UX와 form validation이 개선됨. 세부 route별 추가 정리는 유지관리 대상이다. |
| 프론트 오류 문구 | 주요 깨짐/모호한 문구가 개선됨. |
| 로그인 식별자 | email-only 유지. username/login_id는 도입하지 않음. |
| 외부 API/fallback 표시 | fallback과 evidence source 상태가 trace/report/evaluation에 반영됨. |
| 테스트 커버리지 | Agent/Gateway/Worker/영상 평가 중심으로 크게 확장됨. |
| 배포 관측성 | health, core verification, admin trace diagnostics가 보강됨. 메트릭/알림은 아직 없음. |
| 저장소 산출물 정리 | 프론트 generated JS 제거, `.gitignore`와 fixture/log 분리 정책 보강. |

## 7. 현재 완료로 볼 수 있는 보강

- Agent P0 신뢰 골격: 완료
- Agent judgment contract/finality policy: 완료
- 근거 품질 gate와 claim-evidence audit: 완료
- bounded reflection/reverification loop: 완료
- Agent trace와 관리자 진단 API: 완료
- Gateway/Agent/Worker 주요 SRP split: 완료
- 영상 관찰값 입력 계약과 사실 중재: 완료
- 영상 보류/충돌 보완 질문과 재분석 연결: 완료
- 전문가 안내 카드와 사용자 안전 표시: 완료
- reference 평가 fixture와 batch 평가 도구: 완료
- 최신 OpenAI ON 재측정 및 문서 반영: 완료

## 8. 현재 남은 주요 과제

| 우선순위 | 과제 | 이유 |
| --- | --- | --- |
| P0 | 사고 2 신호 전환 샘플의 근거 검색/카드 선택/보완 질문 우선순위 보강 | 최신 OpenAI ON 평가에서 `needs_user_flow_calibration`으로 남은 직접 잔여 이슈 |
| P0 | OpenAI/LLM/vision 사용량 이벤트 Phase A | 비용과 사용량을 추적할 안전한 메타데이터 원장이 아직 없다 |
| P1 | KNIA/법령/판례 원문 DB coverage 확장 | 정적 fallback 의존을 줄이고 실제 근거 기반성을 높여야 한다 |
| P1 | UI 수용성 점검 | 일반 사용자가 예상/참고/보류/추가 확인을 이해하는지 확인해야 한다 |
| P1 | 사용자/API quota 설계 | OpenAI와 외부 API 사용량 증가에 대비해야 한다 |
| P2 | S3 direct upload | 운영 배포와 대용량 영상 처리 전 필요하다 |
| P2 | 교통사고 특화 비전 모델 후보 검토 | OpenAI 프레임 분석의 한계가 확인된 뒤 교체 가능 구조로 확장한다 |
| P2 | 관리자 비용/품질 대시보드 | usage event 저장 이후 확장한다 |

## 9. 이후 비교 질문에 대한 현재 답

| 질문 | 현재 답 |
| --- | --- |
| 서비스 수나 Docker Compose 구조가 바뀌었는가? | 서비스 종류는 유지됐다. worker OpenAI frame env, compose/검증 환경값은 보강됐다. |
| Gateway route가 분리되었는가? | 예. auth/cases/uploads/analysis/KNIA/admin/legal/diagnostics로 분리됐다. |
| 인증 방식이 바뀌었는가? | 아니오. email-only 유지다. |
| S3 direct upload가 구현되었는가? | 아니오. 아직 local storage 중심이다. |
| Worker가 S3 object도 처리하는가? | 아니오. local file 기준이다. |
| Agent가 영상 원본/프레임을 직접 분석하는 구조로 바뀌었는가? | 영상 원본 통짜 분석은 아니다. Worker가 프레임을 추출하고, 선택적으로 OpenAI 이미지 입력으로 프레임 관찰값을 만든 뒤 Agent가 구조화 입력으로 활용한다. |
| OpenAI 호출 방식이 바뀌었는가? | Worker 프레임 분석은 Responses API 이미지 입력을 사용한다. Agent LLM은 여전히 `httpx` 기반 guarded client 중심이다. |
| KNIA/법률 RAG 근거 품질 표시가 강화되었는가? | 예. evidence quality, source status, expert basis, reference alignment 평가가 추가됐다. |
| DB migration이 추가되었는가? | 이 변화 구간의 핵심 보강은 대부분 코드/문서/테스트이며, 비용 event DB 영속화는 아직 후속이다. |
| Redis key/queue 정책이 바뀌었는가? | 핵심 queue 구조는 유지됐다. Worker 처리 모듈과 job payload 검증이 보강됐다. |
| 테스트와 E2E 검증 범위가 넓어졌는가? | 예. Agent/Gateway/Worker/영상/reference 평가가 크게 확장됐다. |
| `SYSTEM_OVERVIEW.md`가 실제 변경을 반영하는가? | 예. 다만 파일이 매우 길어졌으므로 앞으로는 변화 요약 문서를 함께 보는 것이 효율적이다. |

## 10. 이 문서의 사용 방법

앞으로 “초기 상태에 비해 지금은 어떻게 바뀌었는가”를 확인할 때는 다음 순서로 보면 된다.

1. `docs/PROJECT_BASELINE_2026-05-21.md`에서 인수 직전 상태를 확인한다.
2. 이 문서에서 2026-05-24 현재까지의 변화 요약을 확인한다.
3. 세부 파일 역할과 최신 개발 기록은 `SYSTEM_OVERVIEW.md`를 확인한다.
4. 운영 리스크와 제품 완성 로드맵은 `docs/OPERATING_RISK_ROADMAP.md`를 확인한다.

이 문서는 2026-05-24 현재의 변화 비교 기준이다. 이후 추가 개발이 진행되면 이 문서를 수정하거나 새 날짜의 변화 기록 문서를 추가해 비교 기준을 이어간다.
