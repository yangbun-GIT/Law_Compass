# Project Baseline Snapshot

작성일: 2026-05-21  
기준 경로: `C:/Users/yangbun/Documents/OSS/Law_Compass`

이 문서는 LawCompass 프로젝트의 개발 인수 직전 상태를 기록한 베이스라인 스냅샷이다. 기존 `SYSTEM_OVERVIEW.md`가 구조와 파일 역할을 설명하는 명세서라면, 이 문서는 이후 개발을 진행한 뒤 “초기 상태와 비교해 무엇이 바뀌었는지” 판단하기 위한 기준 자료다.

민감 정보는 기록하지 않는다. `.env`, API key, JWT secret, 내부 서비스 토큰, 사용자 비밀번호 등은 실제 값 대신 환경변수 이름과 역할만 기록한다.

## 1. 베이스라인 요약

| 항목 | 현재 상태 |
| --- | --- |
| 프로젝트 성격 | 교통사고 AI 분석 MVP |
| 구조 | 단일 저장소 모노레포, Docker Compose 기반 경량 MSA형 구성 |
| 주요 서비스 | `frontend`, `gateway`, `agent`, `worker`, `postgres`, `redis`, `edge` |
| 외부 진입점 | Caddy `edge`가 host `80/443`에서 Frontend/Gateway로 reverse proxy |
| 기본 실행 | `docker compose --env-file .env up --build` |
| 브라우저 접속 | `http://localhost` |
| 주요 저장소 | PostgreSQL + pgvector, Redis, local volume `storage/` |
| 운영 전 주요 미완성 | S3 direct upload, 영상 AI 분석 고도화, route/test 정리, 외부 API 상태 검증, 오류 UX 정리 |

## 2. 기준 문서 상태

현재 기준 문서 체계는 다음과 같다.

| 파일 | 역할 |
| --- | --- |
| `AGENTS.md` | 작업 전 `DEVELOPMENT_PROMPT.md`, `SYSTEM_OVERVIEW.md`를 먼저 읽도록 안내하는 에이전트 진입 지침 |
| `DEVELOPMENT_PROMPT.md` | LawCompass 전담 Principal Software Architect 역할, 개발 원칙, 검증, 보안, 문서 동기화 기준 |
| `SYSTEM_OVERVIEW.md` | 프로젝트 구조, 핵심 파일, 리소스 연동, 완성도, To-Do 명세 |
| `docs/STACK_DECISION_REVIEW.md` | 초기 스택 계획과 현재 적용 스택 비교, 향후 도입 후보 판단 |
| `docs/OPERATIONS.md` | 운영 절차, 외부 API 점검, E2E 스모크 테스트 안내 |
| `docs/api/openapi.yaml` | 공개 API 명세 |

이 문서(`docs/PROJECT_BASELINE_2026-05-21.md`)는 위 문서들과 달리 “현재 구현 상태를 비교용으로 고정 기록”하는 역할이다.

## 3. 현재 적용 스택

| 영역 | 실제 적용 스택 |
| --- | --- |
| Frontend | Vue 3, Vite, TypeScript, Pinia, Vue Router |
| Gateway | Node 22, Fastify 5, TypeScript, `pg`, `ioredis`, `bcryptjs`, Fastify cookie/JWT/multipart |
| Agent | Python 3.12, FastAPI, Pydantic, httpx, psycopg, Redis, BeautifulSoup |
| Worker | Python 3.12, Redis Streams, psycopg, tenacity, ffmpeg/ffprobe |
| DB | PostgreSQL 16 + pgvector image |
| Cache/Queue | Redis 7.2 Alpine |
| Edge | Caddy 2.8 |
| Storage | Local volume 중심. `storage/uploads`, `storage/frames` |
| AI/LLM | OpenAI API를 공식 SDK 없이 `httpx` 직접 호출 |

현재 미적용 또는 부분 적용 스택:

| 항목 | 상태 |
| --- | --- |
| Capacitor | 설치/적용되지 않음 |
| AWS S3 direct upload | SDK dependency는 있으나 provider 미구현 |
| Firebase ML Kit / Google ML Kit | 미적용 |
| 표준 MCP 서버/클라이언트 | 미적용. Agent 내부 tool registry만 존재 |
| LangChain | 미적용 |
| OpenAI Responses API | 미적용. 현재 Chat Completions/Embeddings 직접 호출 |

## 4. 서비스별 구현 상태

### Frontend

현재 구현:

- 로그인/회원가입 화면
- 인증 guard 기반 라우팅
- 대시보드, 케이스 생성/상세/결과 화면
- 영상 업로드 UI
- 텍스트 분석/영상 분석 요청 UI
- 쉬운 리포트/근거 표시 컴포넌트
- KNIA ranking/chart/json/media 조회 UI
- AI 채팅 floating panel 및 채팅 store

주요 파일:

- `apps/frontend/src/main.ts`
- `apps/frontend/src/router/index.ts`
- `apps/frontend/src/api/client.ts`
- `apps/frontend/src/stores/session.ts`
- `apps/frontend/src/stores/chatStore.ts`
- `apps/frontend/src/views/*.vue`
- `apps/frontend/src/components/chat/*`
- `apps/frontend/src/components/knia/*`
- `apps/frontend/src/components/easy/*`

현재 주의점:

- `apps/frontend/src/api/client.ts`의 일부 오류 메시지 문자열이 깨져 보인다.
- Capacitor/mobile native packaging은 아직 없다.
- 프론트 테스트는 script 기반 간접 테스트 중심이며 화면별 단위 테스트 체계는 약하다.
- 일부 화면 텍스트에는 S3 설명이 남아 있으나 현재 실제 업로드는 local storage 중심이다.

### Gateway

현재 구현:

- Fastify 기반 API Gateway
- 이메일 기반 회원가입/로그인
- JWT access cookie, refresh token DB 저장/회전
- 사용자 인증 hook
- 관리자 권한 검사: user role `admin` 또는 `x-admin-token`
- Redis 기반 rate limit
- idempotency key 처리
- 케이스 CRUD 일부
- local multipart upload
- 업로드 완료 및 video job 등록
- 텍스트 분석 Agent 호출
- 영상 분석 job 연계
- 분석 결과/리포트/easy-report/evidence 조회
- KNIA ranking/chart/match/fault estimate/json/media/admin route
- 채팅 session/message/quick route

주요 파일:

- `apps/gateway/src/main.ts`
- `apps/gateway/src/routes/chat.ts`
- `apps/gateway/src/services/chatService.ts`
- `apps/gateway/src/lib/internal-client.ts`
- `apps/gateway/src/lib/report-composer.ts`
- `apps/gateway/src/lib/security.ts`
- `apps/gateway/src/lib/ai-router.ts`
- `apps/gateway/src/storage/provider.ts`

현재 주의점:

- `apps/gateway/src/main.ts`에 route가 과도하게 집중되어 있다.
- S3 SDK는 있으나 `S3StorageProvider.putUpload()`는 `S3_STORAGE_NOT_ENABLED`를 반환한다.
- 로그인은 `email` 형식만 받는다. 별도 `username`, `login_id` 컬럼/스키마는 없다.
- validation error가 사용자에게 명확한 원인으로 전달되지 않는 경우가 있다.
- Gateway route별 테스트 커버리지는 제한적이다.

### Agent

현재 구현:

- FastAPI 내부 API `/internal/v1/*`
- 내부 토큰 검증 `x-internal-token`
- 텍스트 사고 분석
- 영상 전처리 요약 기반 사고 분석
- 구조화 시나리오 분석
- 사고 유형/당사자 유형 분류
- 교통법규/과실/형사책임/보험/행동계획 분석 모듈
- 법률 RAG
- KNIA 수집, 파싱, 저장, 매칭, 과실 추정
- KNIA JSON import, menu tree, media search
- AI 채팅 의도 분류/응답/초안 케이스 생성
- OpenAI API 직접 호출 기반 optional LLM 분석가
- OpenAI API key가 없을 때 deterministic embedding fallback

주요 파일:

- `apps/agent/app/main.py`
- `apps/agent/app/routers/internal.py`
- `apps/agent/app/schemas.py`
- `apps/agent/app/services/orchestrator.py`
- `apps/agent/app/services/llm_client.py`
- `apps/agent/app/providers/embedding.py`
- `apps/agent/app/services/legal/*`
- `apps/agent/app/services/knia/*`
- `apps/agent/app/services/chat/*`
- `apps/agent/app/mcp/*`

현재 주의점:

- 영상 원본을 직접 vision model로 분석하지 않는다.
- 현재 영상 분석은 ffmpeg/ffprobe 전처리 요약, 케이스 설명, 구조화 입력, 키워드 기반이다.
- `ENABLE_OPENAI_ANALYSTS=1`일 때만 LLM 분석가 호출이 활성화된다.
- 외부 API 권한/네트워크 상태에 따라 법률/공공 API 결과가 비거나 실패할 수 있다.
- KB 적재 부족 시 정적 fallback 근거가 사용될 수 있다.
- Agent orchestration이 여러 하위 모듈을 결합하므로 회귀 테스트가 중요하다.

### Worker

현재 구현:

- Redis Streams Consumer Group 기반 job 처리
- `video_preprocess`
  - 업로드 파일 존재 확인
  - `ffprobe`로 metadata 추출
  - `ffmpeg`로 대표 프레임 4장 추출
  - upload 상태/metadata/frame_dir 업데이트
  - 후속 `video_analyze` job 생성
- `video_analyze`
  - 케이스/업로드 metadata 조회
  - Agent `/internal/v1/analyze/video` 호출
  - `analysis_results` 저장
  - `cases.latest_result_id`, `cases.status` 갱신
- 실패 시 job 상태를 `failed` 또는 `dead`로 갱신

주요 파일:

- `apps/worker/worker/main.py`

현재 주의점:

- ffmpeg/ffprobe 설치와 로컬 파일 경로 접근에 의존한다.
- S3 remote object 처리 흐름은 아직 없다.
- Worker 전용 테스트는 제한적이다.
- `boto3`는 requirements에 있으나 현재 핵심 worker 코드에서는 직접 사용되지 않는다.

### Database / Redis / Storage

현재 구현:

- PostgreSQL extensions:
  - `vector`
  - `pgcrypto`
  - `citext`
- 주요 DB 그룹:
  - 인증: `users`, `auth_refresh_tokens`
  - 케이스: `cases`, `uploads`, `jobs`, `analysis_results`
  - KB: `kb_sources`, `kb_documents`, `kb_chunks`, `kb_embeddings`
  - 법률 규칙: `legal_rules`, `scenario_legal_mappings`
  - 채팅: `chat_sessions`, `chat_messages`, `chat_safety_logs`
  - KNIA: `knia_*`
  - 캐시/도구: `semantic_query_cache`, `mcp_tool_calls`
- Redis:
  - rate limit key: `rl:v1:{user}:{route}:{minute}`
  - stream: `jobs:v1:stream`
  - consumer group: `worker-group`
  - job status: `job:v1:{job_id}:status`
- Local storage:
  - `storage/uploads/{caseId}/{uploadId}/original.ext`
  - `storage/frames/{caseId}/{uploadId}/frame_*.jpg`

현재 주의점:

- production S3 flow가 없다.
- migration은 여러 파일로 나뉘어 있으나 `db-migrate` profile 명령이 일부 glob을 명시한다.
- 신규 migration 추가 시 compose 명령도 확인해야 한다.

## 5. 현재 완성된 것으로 볼 수 있는 영역

| 영역 | 상태 |
| --- | --- |
| Docker Compose 서비스 구성 | 완료 |
| Caddy reverse proxy | 완료 |
| Frontend 기본 화면/라우팅 | 완료 |
| 이메일 기반 인증 | 완료 |
| 케이스 생성/조회/수정 | 기본 구현 완료 |
| local 영상 업로드 | 구현 완료 |
| Redis Stream 기반 영상 job | 구현 완료 |
| 텍스트 분석 | 구현 완료 |
| 영상 전처리 요약 기반 분석 | 구현 완료 |
| 법률 RAG 기반 근거 조회 | 구현 완료 |
| KNIA 수집/검색/매칭 | 구현 완료 |
| AI 채팅 | 기본 구현 완료 |
| 기준 문서 체계 | `AGENTS.md`, `DEVELOPMENT_PROMPT.md`, `SYSTEM_OVERVIEW.md`, `STACK_DECISION_REVIEW.md` 작성 완료 |

## 6. 현재 미완성 또는 보강 필요 영역

| 항목 | 현재 상태 | 향후 비교 포인트 |
| --- | --- | --- |
| S3 direct upload | 미구현 | S3 provider, presigned upload, complete flow, local fallback 추가 여부 |
| 모바일 앱/Capacitor | 미적용 | iOS/Android packaging 추가 여부 |
| 영상 전문 분석 | 미구현 | `VideoAnalyzerProvider`, vision/frame analyzer, ML Kit/TFLite 도입 여부 |
| 표준 MCP | 미적용 | 외부 MCP 서버/클라이언트 구조 도입 여부 |
| Gateway route 구조 | `main.ts` 집중 | route module 분리 여부 |
| Gateway validation UX | 일부 오류가 모호 | schema validation error 정규화 여부 |
| 프론트 오류 문구 | 일부 깨짐 | UTF-8 문구 수정 여부 |
| 로그인 식별자 | email only | username/login_id 도입 여부 |
| 외부 API 신뢰도 표시 | fallback 가능 | 공식 API/KNIA/fallback 근거 표시 강화 여부 |
| 테스트 커버리지 | 제한적 | Gateway/Agent/Worker/Frontend 단위 및 E2E 테스트 확장 여부 |
| 배포 관측성 | 기본 로그 중심 | 로그/메트릭/헬스체크/알림 보강 여부 |
| 저장소 산출물 정리 | `dist`, `__pycache__`, `storage` 산출물 존재 | repo hygiene 개선 여부 |

## 7. 현재 개발 우선순위 메모

현재 상태 기준으로 production 완성도를 높이기 위한 우선순위는 다음 순서가 적절하다.

1. Gateway validation/error response 정리
2. 프론트 깨진 오류 문구 수정
3. 로그인/계정 정책 확정
4. E2E smoke 기준 고정
5. 외부 API/KB 적재 상태 점검 루틴 정리
6. S3 direct upload 구현 여부 결정 및 구현
7. 분석 근거 품질/fallback 표시 강화
8. Worker 실패 상태와 재시도 UX 정리
9. Gateway route 분리
10. 영상 분석 고도화를 위한 provider 추상화 설계

## 8. 이후 변화 비교 시 확인할 질문

향후 개발 후 이 문서와 비교할 때 다음 질문을 기준으로 보면 된다.

- 서비스 수나 Docker Compose 구조가 바뀌었는가?
- Frontend route, view, store, API client 구조가 바뀌었는가?
- Gateway route가 분리되었는가?
- 인증 방식이 email-only에서 변경되었는가?
- S3 direct upload가 구현되었는가?
- Worker가 local file뿐 아니라 S3 object도 처리하는가?
- Agent가 영상 원본/프레임을 직접 분석하는 구조로 바뀌었는가?
- OpenAI 호출 방식이 Chat Completions에서 Responses API 또는 SDK 기반으로 바뀌었는가?
- KNIA/법률 RAG 근거 품질 표시가 강화되었는가?
- DB migration이 추가되었는가?
- Redis key, queue, cache 정책이 바뀌었는가?
- 테스트와 E2E 검증 범위가 넓어졌는가?
- `SYSTEM_OVERVIEW.md`와 `STACK_DECISION_REVIEW.md`가 실제 변경을 반영하도록 업데이트되었는가?

## 9. 베이스라인 원칙

이 문서는 2026-05-21 현재 상태를 고정 기록한다. 이후 개발로 프로젝트가 변경되더라도 이 파일은 원칙적으로 과거 기준점으로 남긴다.

수정이 필요한 경우는 다음에 한정한다.

- 2026-05-21 기준 상태를 잘못 기록한 오류 수정
- 민감정보 제거
- 명백한 오탈자 수정

개발 이후의 변경 이력은 별도 문서 또는 `SYSTEM_OVERVIEW.md` 업데이트로 관리한다.
