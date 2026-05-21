# LawCompass 시스템 구성 명세서

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
| `apps/frontend/src/views/*.vue` | 로그인, 대시보드, 케이스 생성/상세/결과, KNIA 화면 |
| `apps/frontend/src/components/chat/*` | AI 사고 상담 패널, 메시지, 초안 케이스, KNIA 매칭 카드 |
| `apps/frontend/src/components/knia/*` | KNIA 순위, 기준, 미디어, JSON 검색 UI |
| `apps/frontend/src/components/easy/*` | 고령자 친화 리포트 표시 컴포넌트 |

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
| `apps/gateway/src/lib/report-composer.ts` | 분석 결과를 클라이언트 리포트/쉬운 리포트 형태로 조립 |
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
| `apps/agent/app/routers/internal.py` | 내부 전용 `/internal/v1/*` API 라우터 |
| `apps/agent/app/schemas.py` | Pydantic 요청/응답 모델 |
| `apps/agent/app/services/orchestrator.py` | 사고 분석 파이프라인 총괄 |
| `apps/agent/app/services/claim_evidence_validator.py` | Agent 분석 결과의 주요 판단과 근거 문서를 연결하고 근거 누락 판단을 `evidence_audit`에 반영 |
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
| `apps/gateway/src/main.ts` | Fastify API entrypoint/controller | 공개 API 대부분과 인증, rate limit, idempotency, DB/Redis/Agent 연동을 담당한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/routes/chat.ts` | Fastify chat router | 채팅 세션 생성, 메시지 조회/전송, 빠른 상담 API를 등록한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/services/chatService.ts` | Chat domain service | 채팅 세션/메시지를 DB에 저장하고 Agent 채팅 API를 호출한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/lib/internal-client.ts` | Internal HTTP client | Gateway에서 Agent 내부 POST API를 timeout/retry 포함해 호출한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/lib/errors.ts` | Gateway error formatter | `error.code/message/trace_id` 표준 응답을 만들고 Fastify validation 오류를 400 응답으로 정규화한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/storage/provider.ts` | Storage abstraction | 로컬 영상 업로드 저장을 구현하고 S3 provider 인터페이스를 남겨둔다 | 저장소 내 명시 없음 |
| `apps/agent/app/main.py` | FastAPI app entrypoint | Agent 앱을 생성하고 internal router를 등록한다 | 저장소 내 명시 없음 |
| `apps/agent/app/routers/internal.py` | FastAPI internal router/controller | Gateway/Worker 전용 분석, 법률, KNIA, 채팅, 캐시 내부 API를 제공한다 | 저장소 내 명시 없음 |
| `apps/agent/app/schemas.py` | Pydantic DTO schema | 분석 요청/응답과 근거 item 모델을 정의한다 | 저장소 내 명시 없음 |
| `apps/agent/app/services/orchestrator.py` | Analysis orchestration service | 사고 분석 전체 파이프라인을 조립하고 최종 `AnalysisOutput` payload를 만든다 | 저장소 내 명시 없음 |
| `apps/agent/app/services/legal_api_clients.py` | External legal/public API client | 국가법령정보센터와 공공데이터포털 교통 API 검색 결과를 내부 근거 형식으로 변환한다 | 저장소 내 명시 없음 |
| `apps/worker/worker/main.py` | Redis Streams worker | 영상 전처리, 프레임 추출, 영상 분석 job 실행, DB 상태 갱신을 수행한다 | 저장소 내 명시 없음 |
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
| `apps/agent/app/routers/internal.py` | `_check_internal_token` | `x_internal_token` | 없음 또는 401 | `INTERNAL_SERVICE_TOKEN`과 요청 헤더 비교 |
| `apps/agent/app/routers/internal.py` | `analyze_text`, `analyze_video`, `analyze_scenario_endpoint` | Pydantic/dict payload | `AnalysisOutput` | orchestrator 분석 함수를 호출해 표준 분석 응답 반환 |
| `apps/agent/app/routers/internal.py` | `legal_ingest`, `legal_rebuild_embeddings`, `legal_retrieval_test` | token/query | ingest/rebuild/search 결과 | 법률 KB 적재, 벡터 생성, 검색 테스트 수행 |
| `apps/agent/app/routers/internal.py` | `knia_*` endpoints | token, chart/query/import payload | KNIA 수집/검색/추정 결과 | KNIA collector, matcher, repository, vectorizer, JSON loader 호출 |
| `apps/agent/app/schemas.py` | `AnalyzeTextRequest` | 텍스트 분석 요청 JSON | Pydantic model | 케이스/사용자/설명/구조화 사실/키워드 유효성 정의 |
| `apps/agent/app/schemas.py` | `AnalyzeVideoRequest` | 영상 분석 요청 JSON | Pydantic model | 업로드 ID, 전처리 요약, 영상 metadata 포함 요청 정의 |
| `apps/agent/app/schemas.py` | `AnalysisOutput` | 분석 결과 dict | Pydantic response | 법률/과실/보험/형사/근거/KNIA/쉬운 리포트 응답 규격 정의 |
| `apps/agent/app/services/orchestrator.py` | `analyze_case` | description, facts, keywords, profile | analysis dict | 텍스트 입력을 `_analyze_core`로 전달 |
| `apps/agent/app/services/orchestrator.py` | `analyze_video_case` | preprocessed summary, video metadata | analysis dict | 영상 요약과 metadata를 `_analyze_core`로 전달 |
| `apps/agent/app/services/orchestrator.py` | `_analyze_core` | normalized accident inputs | final analysis dict | 입력 정규화, 시나리오 분류, KNIA/법률 근거 검색, 분석가 함수 실행, 리포트 조립 |
| `apps/agent/app/services/orchestrator.py` | `_knia_estimate_to_evidence`, `_knia_refs_to_evidence` | KNIA 추정/참조 데이터 | evidence list | 과실 기본값, 가감요소, 관련 법규/사례를 evidence item으로 변환 |
| `apps/agent/app/services/legal_api_clients.py` | `fetch_law_search` | query, limit | evidence-like rows | 국가법령정보센터 `lawSearch.do`에서 법령/판례 검색 |
| `apps/agent/app/services/legal_api_clients.py` | `fetch_data_go_traffic` | query, limit | evidence-like rows | 공공데이터포털 교통사고 API 응답을 내부 근거 형식으로 변환 |
| `apps/worker/worker/main.py` | `init_group` | 없음 | 없음 | Redis Stream consumer group 생성 |
| `apps/worker/worker/main.py` | `probe_video` | storage_path | video metadata dict | `ffprobe`로 codec, duration, resolution, fps, size 추출 |
| `apps/worker/worker/main.py` | `extract_frames` | storage_path, caseId, uploadId, duration | frame path list | `ffmpeg`로 4개 시점 프레임 추출 |
| `apps/worker/worker/main.py` | `process_job` | job_id, job_type | DB/Redis side effect | `video_preprocess`와 `video_analyze`를 분기 처리 |
| `apps/worker/worker/main.py` | `mark_failed`, `main_loop` | job/error 또는 없음 | 없음 | 실패 상태 갱신 및 Redis Stream 무한 소비 루프 |

#### 파일별 호출 관계 및 리소스

| 파일 | Caller | Callee / Imports | Configuration | Data Storage / External Resource | MSA Context |
| --- | --- | --- | --- | --- | --- |
| `compose.yaml` | 운영자, Docker Compose CLI | 각 서비스 Dockerfile, `.env`, volume/network | `.env`, Compose substitution | Docker volumes `postgres_data`, `redis_data`, `caddy_data`, bind mount `storage`, `logs`, `config`, `scripts` | 전체 서비스 정의. host `80/443`, 내부 `3000/8000/5173/5432/6379` |
| `infra/caddy/Caddyfile` | `edge` container | `frontend:5173`, `gateway:3000` | Caddy global email | HTTP reverse proxy, 보안 header | `edge` 서비스, host `80/443` |
| `infra/postgres/migrations/001_init.sql` | `postgres` init, `db-migrate` profile | PostgreSQL extensions | `POSTGRES_*`는 compose/env에서 주입 | `users`, `cases`, `uploads`, `jobs`, `analysis_results`, `kb_*`, `audit_logs`, `idempotency_keys` | `postgres` 서비스 내부 `5432` |
| `apps/frontend/src/main.ts` | Browser | Vue, Pinia, Router, `App.vue` | Vite env 간접 사용 | DOM mount `#app` | `frontend` 서비스 내부 `5173` |
| `apps/frontend/src/router/index.ts` | Vue app | `vue-router`, `session` store, view components | 없음 | Browser history, session state | Browser -> frontend |
| `apps/frontend/src/api/client.ts` | Vue views/components/stores | Fetch API, `import.meta.env.VITE_API_BASE_URL` | `VITE_API_BASE_URL` | Gateway `/api/v1/*`, cookie credentials | Browser -> `edge`/`gateway` |
| `apps/frontend/src/stores/session.ts` | Router, Login/Logout UI | Pinia, `api` client | 없음 | `localStorage` key `lawcompass:user`, auth cookies는 Gateway가 관리 | Browser state layer |
| `apps/gateway/src/main.ts` | `node dist/main.js`, `tsx watch` | Fastify plugins, `pg`, `ioredis`, `bcryptjs`, internal libs | `DATABASE_URL`, `REDIS_URL`, `JWT_*`, `INTERNAL_AGENT_URL`, `INTERNAL_SERVICE_TOKEN`, `INTERNAL_ADMIN_TOKEN`, timeout/storage env | PostgreSQL 업무 테이블, Redis `rl:v1:*`, Redis Stream `jobs:v1:stream`, local storage | `gateway` 서비스 내부 `3000` |
| `apps/gateway/src/routes/chat.ts` | `apps/gateway/src/main.ts` | `chatService`, chat schemas | route option으로 Agent URL/token 전달 | `chat_sessions`, `chat_messages`는 service가 접근 | `gateway` 서비스 내부 route |
| `apps/gateway/src/services/chatService.ts` | `routes/chat.ts` | `callInternalAgent` | options의 `agentUrl`, `internalToken`, timeout/retry | `chat_sessions`, `chat_messages`, `chat_safety_logs`, Agent `/internal/v1/chat/message` | `gateway` -> `agent:8000` |
| `apps/gateway/src/lib/internal-client.ts` | Gateway routes/services | Fetch API, `randomUUID` | call option으로 수신 | Agent internal HTTP | `gateway` -> `agent:8000` |
| `apps/gateway/src/storage/provider.ts` | Upload routes in `main.ts` | Node fs/path/stream | `LOCAL_STORAGE_ROOT`는 생성자에서 전달 | `storage/uploads/{caseId}/{uploadId}/original.ext` | `gateway` container local/bind volume |
| `apps/agent/app/main.py` | Uvicorn | FastAPI, internal router | 없음 | 없음 | `agent` 서비스 내부 `8000` |
| `apps/agent/app/routers/internal.py` | Gateway, Worker | orchestrator, legal, KNIA, chat, cache services | `INTERNAL_SERVICE_TOKEN`, `DATABASE_URL` | KB/KNIA/semantic cache DB 테이블, Agent service 함수 | `agent` 내부 `/internal/v1/*` |
| `apps/agent/app/schemas.py` | `internal.py`, tests | Pydantic | 없음 | 없음 | Agent DTO layer |
| `apps/agent/app/services/orchestrator.py` | `internal.py`, tests | classifier, analysts, RAG, KNIA, report composer, OpenAI flag | `OPENAI_API_KEY` 존재 여부 | 법률 RAG, KNIA DB/Redis 검색은 하위 service에서 접근 | Agent domain service |
| `apps/agent/app/services/legal_api_clients.py` | legal ingestion/retrieval 계열 service/script | `httpx` | `LAW_API_OC`, `LAW_API_BASE`, `LAW_API_TARGETS`, `DATA_GO_*` | `law.go.kr`, `apis.data.go.kr` 외부 HTTP | Agent egress |
| `apps/worker/worker/main.py` | Worker container process | Redis, psycopg, ffmpeg/ffprobe, urllib | `REDIS_URL`, `REDIS_STREAM_KEY`, `REDIS_STREAM_GROUP`, `DATABASE_URL`, `INTERNAL_AGENT_URL`, `INTERNAL_SERVICE_TOKEN`, `LOCAL_STORAGE_ROOT` | `jobs`, `uploads`, `cases`, `analysis_results`, Redis stream/status key, local frames | `worker` service, no public port |

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
| `apps/agent/app/schemas.py` | `AnalyzeTextRequest` | Agent internal API request | 텍스트 분석 요청 검증 |
| `apps/agent/app/schemas.py` | `AnalyzeVideoRequest` | Agent internal API request | 영상 분석 요청 검증 |
| `apps/agent/app/schemas.py` | `EvidenceItem` | Agent internal API response | 법률/KNIA 근거 item 규격 |
| `apps/agent/app/schemas.py` | `AnalysisOutput` | Agent internal API response | 최종 분석 결과 표준 응답 |
| `apps/agent/app/services/claim_evidence_validator.py` | `claim_evidence` dict | Agent internal API response 일부 | 법규, 과실비율, 형사책임, 보험 안내, 행동계획의 주요 claim별 연결 근거와 지원 수준 |

#### 테스트 및 유지보수 상태 매핑

| 파일/영역 | Progress State | Test Status | Known Issues / Review Notes |
| --- | --- | --- | --- |
| `apps/frontend/src/api/client.ts` | 구현 완료 | `apps/frontend/scripts/test-display.mjs`, `apps/frontend/scripts/test-chat.mjs`에서 간접 검증 | 네트워크/JSON/API 오류를 사용자 문구로 정규화하고 Gateway validation detail을 로그인, 회원가입, 케이스 생성, 케이스 상세 주요 액션에서 필드별 안내로 표시한다. 결과/근거 화면은 로딩, 결과 없음, 오류 상태를 구분하고 일반 사용자 화면에서는 내부 근거 식별자와 원문 덤프를 숨긴다. 인증 폼은 데모 기본값 없이 email 형식과 8자 이상 비밀번호를 선제 검증한다 |
| `apps/frontend/src/router/index.ts` | 구현 완료 | 전용 단위 테스트 없음 | 인증 bootstrap가 route guard마다 실행되므로 초기 진입 지연 가능성은 관찰 대상 |
| `apps/frontend/src/stores/session.ts` | 구현 완료 | 전용 단위 테스트 없음 | localStorage 사용자 정보와 cookie 세션 불일치 시 refresh 흐름에 의존 |
| `apps/gateway/src/main.ts` | 구현 완료, 라우트 규모 큼 | `apps/gateway/test/error-format.test.ts`, `npm test` | validation 오류는 400 `VALIDATION_ERROR`로 정규화된다. 한 파일에 인증/케이스/업로드/분석/KNIA/admin 라우트가 집중되어 유지보수 비용이 높다 |
| `apps/gateway/src/routes/chat.ts` | 구현 완료 | Gateway test에서 직접 매핑 확인 필요 | 일부 route는 `requireUser`를 명시적으로 강제하지 않고 익명 세션도 허용하는 구조다 |
| `apps/gateway/src/services/chatService.ts` | 구현 완료 | 전용 단위 테스트 없음 | Agent 장애 시 Gateway route에서 502로 변환된다 |
| `apps/gateway/src/storage/provider.ts` | 로컬 provider 구현, S3 provider 미구현 | 전용 단위 테스트 없음 | `S3StorageProvider`는 현재 의도적으로 비활성 상태 |
| `apps/agent/app/routers/internal.py` | 구현 완료 | `apps/agent/scripts/test_*.py`에서 경로별 간접 검증 | 내부 token 누락/불일치 시 401 |
| `apps/agent/app/schemas.py` | 구현 완료 | `apps/agent/tests/test_orchestrator.py` 및 scripts에서 간접 검증 | 응답 모델이 크므로 프론트 표시 필드와 동기화 관리 필요 |
| `apps/agent/app/services/orchestrator.py` | 구현 완료, 핵심 복합 로직 | `apps/agent/tests/test_orchestrator.py`, `apps/agent/scripts/test_legal_rag.py`, `test_knia_*`, `test_chat_*` 간접 검증 | KNIA/RAG/분석가 로직이 한 파이프라인에 결합되어 있어 입력 케이스별 회귀 테스트가 중요 |
| `apps/agent/app/services/claim_evidence_validator.py` | 구현 완료, Agent 신뢰도 보강 로직 | `apps/agent/tests/test_claim_evidence_validator.py`, `apps/agent/tests/test_orchestrator.py` | 주요 판단별 근거 연결 상태를 산출하므로 향후 Analyst별 claim 형식이 바뀌면 함께 갱신 필요 |
| `apps/agent/app/services/legal_api_clients.py` | 구현 완료, 외부 권한 의존 | `apps/agent/scripts/check_external_apis.py` | 국가법령정보센터 IP/도메인 검증, 공공데이터포털 활용신청 권한 상태에 따라 실패 가능 |
| `apps/worker/worker/main.py` | 구현 완료 | `apps/worker/tests/test_keys.py`, E2E smoke에서 간접 검증 | ffmpeg/ffprobe 설치와 로컬 파일 경로 접근 권한에 의존 |
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
