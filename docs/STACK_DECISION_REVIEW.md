# Stack Decision Review

작성 기준일: 2026-05-20

이 문서는 LawCompass의 초기 기술 스택 계획안과 현재 저장소에 실제 적용된 스택을 비교하고, 차이가 있는 항목에 대해 어떤 선택이 더 적절한지 기록한 기술 의사결정 참고 문서다.

이 문서는 구현 지시서가 아니다. 향후 기능 고도화, 모바일 앱 전환, 영상 분석 개선, 운영 배포 준비 시 기술 선택의 맥락을 빠르게 확인하기 위한 자료다.

## 요약

| 영역 | 초기 계획 | 현재 적용 | 판단 |
| --- | --- | --- | --- |
| Frontend | Vue 3 + Capacitor | Vue 3 + Vite + TypeScript + Pinia + Vue Router | Vue 3 유지 적절. Capacitor는 모바일 앱 출시 시점에 도입 검토 |
| API Gateway | Node.js Express/Fastify | Node 22 + Fastify 5 + TypeScript | Fastify 선택 적절. Express로 전환할 이유 없음 |
| AI Agent | FastAPI + Python + Docker | FastAPI + Python 3.12 + Pydantic + httpx | 적절. LangChain 등 무거운 추상화는 현재 필수 아님 |
| DB/Cache/Storage | PostgreSQL pgvector + Redis + AWS S3 | PostgreSQL pgvector + Redis + local storage. S3 SDK만 존재 | DB/Redis 적절. S3는 운영 전환 시 구현 후보 |
| Video Pipeline | Firebase ML Kit | ffmpeg/ffprobe + Agent 텍스트/메타데이터 분석 | 차이 큼. Firebase ML Kit 대신 Google ML Kit/TFLite/프레임 분석 구조로 재검토 필요 |
| Security/Integration | MCP | Agent 내부 `app/mcp` tool registry/executor | 표준 MCP는 아님. 현재는 내부 tool registry 수준으로 충분 |

## 1. Frontend

### 초기 계획

- Vue 3
- Capacitor

### 현재 적용

`apps/frontend/package.json` 기준:

- `vue`
- `vue-router`
- `pinia`
- `vite`
- `typescript`
- `vue-tsc`
- `@vitejs/plugin-vue`

Capacitor는 현재 설치되어 있지 않다.

### 판단

현재 웹 MVP와 대시보드 중심 구조에서는 Vue 3 + Vite + TypeScript 조합이 적절하다. Capacitor는 iOS/Android 앱 배포가 실제 요구사항으로 확정되는 시점에 도입하는 것이 더 낫다.

Capacitor를 지금 추가하면 Android/iOS native project, 앱 권한, 빌드/서명, 앱스토어 배포, native plugin 호환성을 함께 관리해야 하므로 현재 단계에서는 부담이 크다.

### 권고

- 단기: Vue 3 + Vite 유지
- 모바일 앱 출시 단계: Capacitor 도입 검토
- 영상/카메라/파일 접근을 모바일 단말에서 직접 처리해야 하는 요구가 생기면 Capacitor native bridge 또는 plugin 검토

## 2. API Gateway

### 초기 계획

- Node.js
- Express 또는 Fastify

### 현재 적용

`apps/gateway/package.json` 기준:

- Fastify 5
- TypeScript
- `@fastify/cookie`
- `@fastify/cors`
- `@fastify/jwt`
- `@fastify/multipart`
- `pg`
- `ioredis`
- `bcryptjs`
- `uuid`
- `zod`
- AWS S3 SDK

### 판단

Fastify 선택은 적절하다. 현재 Gateway는 Fastify hook, schema validation, cookie/JWT, multipart upload, Redis rate limit, idempotency 흐름으로 이미 구성되어 있다.

Express로 전환하면 실질적 이득보다 리팩토링 비용과 회귀 위험이 크다.

### 권고

- Fastify 유지
- `apps/gateway/src/main.ts`에 많은 route가 집중되어 있으므로 기능이 더 커질 경우 route module 분리 검토
- 인증, 업로드, 분석, KNIA, admin route를 점진적으로 별도 route 파일로 분리할 수 있음

## 3. AI Agent

### 초기 계획

- FastAPI
- Python
- Docker
- LangChain 등 Python AI 생태계 활용 가능성

### 현재 적용

`apps/agent/requirements.txt` 기준:

- `fastapi`
- `uvicorn`
- `pydantic`
- `httpx`
- `psycopg[binary]`
- `redis`
- `python-dotenv`
- `beautifulsoup4`

OpenAI 공식 SDK는 사용하지 않고 `httpx`로 직접 OpenAI HTTP API를 호출한다.

### 판단

현재 구조가 2GB RAM 환경에는 더 적합하다. LangChain 같은 범용 agent framework는 빠른 개발에는 편할 수 있지만, 의존성 증가와 추상화 비용이 있다.

현재 Agent는 다음 구조로 명시적이고 가볍게 구성되어 있다.

- `orchestrator.py`
- `analysts/*`
- `legal/*`
- `knia/*`
- `chat/*`
- `mcp/*`

### 권고

- FastAPI + 명시적 service 구조 유지
- LangChain은 당장 추가하지 않음
- 외부 도구 연동이나 복잡한 multi-step agent가 실제로 필요해질 때만 재검토

## 4. DB, Cache, Storage

### 초기 계획

- PostgreSQL + pgvector
- Redis
- AWS S3 direct upload

### 현재 적용

현재 적용:

- PostgreSQL 16 + pgvector Docker image
- PostgreSQL extensions: `vector`, `pgcrypto`, `citext`
- Redis 7.2 Alpine
- Local storage: `storage/uploads`, `storage/frames`
- AWS S3 SDK dependency는 Gateway에 존재
- `S3StorageProvider`는 현재 `S3_STORAGE_NOT_ENABLED` 오류를 반환

### 판단

PostgreSQL + pgvector + Redis 선택은 현재 프로젝트에 적절하다. 법률/KNIA 근거 검색과 일반 업무 데이터를 같은 DB에서 관리할 수 있어 운영 부담이 낮다.

S3는 초기 설계 방향이 맞지만 아직 구현되지 않았다. MVP/로컬 개발 단계에서는 local storage가 단순하고 빠르다. 다만 운영에서 대용량 블랙박스 영상이 많아지면 Gateway 서버를 거치지 않는 S3 presigned direct upload가 필요하다.

### 권고

- 단기: local storage 유지
- 운영 준비: S3 presigned upload 구현
- 개발환경에서 S3 호환 테스트가 필요하면 MinIO를 별도 profile로 검토
- 단, 2GB 환경에서는 MinIO를 기본 서비스로 상시 구동하지 않는 편이 낫다

## 5. Video Pipeline

### 초기 계획

- Firebase ML Kit

### 현재 적용

현재 Worker는 다음 방식으로 동작한다.

- `ffprobe`로 영상 metadata 추출
- `ffmpeg`로 영상 길이에 맞춘 시간순 이벤트 프레임 추출
- `ENABLE_OPENAI_FRAME_ANALYSIS=1`일 때 OpenAI Responses API 이미지 입력으로 선별 프레임을 분석해 `observations`를 생성
- Agent는 영상 원본을 직접 분석하지 않고, 전처리 요약, 케이스 설명, 구조화 입력, 선택 키워드, 검증된 영상 관측값을 기반으로 분석

현재 구조는 “통짜 영상 직접 AI 비전 분석”이 아니라 “영상 metadata/event frame preprocessing + 선택적 프레임 이미지 분석 + 텍스트/구조화 입력 기반 Agent 분석”이다.

### 판단

초기 계획과 현재 구현 차이가 가장 큰 영역이다.

Firebase ML Kit이라는 명칭은 현재 기준으로 재검토가 필요하다. Google 문서 기준, 기존 Firebase ML Kit on-device API는 standalone ML Kit SDK로 분리되었고, 새 구현은 Firebase ML Kit이 아니라 Google ML Kit 또는 TensorFlow Lite 기반으로 검토하는 편이 적절하다.

또한 ML Kit 기본 모델만으로 “차선 변경, 충돌, 사고 상황”을 안정적으로 추출하기는 어렵다. 일반 object detection/tracking, image labeling은 가능하지만 교통사고 특화 판단에는 custom model 또는 별도 rule/LLM 결합이 필요하다.

### 권고

- 단기: 현재 ffmpeg/ffprobe 기반 전처리와 OpenAI 프레임 분석을 제한적으로 사용
- 중기: `VideoAnalyzerProvider` 같은 추상화 계층 도입 검토
- 후보 provider:
  - `FfmpegMetadataAnalyzer`
  - `OpenAIVisionFrameAnalyzer`
  - `GoogleMLKitMobileAnalyzer`
  - `TFLiteAccidentAnalyzer`
- 모바일 앱을 도입할 때:
  - Capacitor + native ML Kit bridge
  - standalone Google ML Kit
  - custom TensorFlow Lite model
  를 함께 검토
- 서버에서 YOLO/OpenCV 기반 무거운 모델을 상시 구동하는 방식은 2GB 환경에 부적합

## 6. Security and Integration

### 초기 계획

- MCP(Model Context Protocol)

### 현재 적용

현재 `apps/agent/app/mcp`에는 다음 구조가 있다.

- `tool_registry.py`
- `tool_executor.py`
- `tools/legal_rag_tools.py`
- `tools/knia_tools.py`
- `tools/cache_tools.py`
- `tools/evidence_guard_tools.py`

이는 내부 tool registry/executor 구조이며, 외부 표준 MCP 서버/클라이언트 전체 구현은 아니다.

### 판단

현재 MVP 단계에서는 내부 tool registry 구조로 충분하다. 표준 MCP를 본격 도입하려면 tool schema, 권한, 실행 격리, 외부 connector 보안 모델까지 함께 설계해야 하므로 현재 규모에서는 부담이 크다.

### 권고

- 단기: 내부 tool registry 유지
- 외부 도구/에이전트 연동이 많아질 때 표준 MCP 도입 검토
- 보안 가드레일은 우선 다음 영역에서 강화:
  - Gateway 인증/인가
  - Agent internal token 검증
  - tool allowlist
  - 민감정보 마스킹
  - 파일 업로드 검증
  - 외부 API 호출 제한

## 7. OpenAI API 사용 방식

### 현재 적용

현재 Agent는 OpenAI 공식 SDK를 쓰지 않고 `httpx`로 직접 호출한다.

사용 endpoint:

- `/v1/chat/completions`
- `/v1/embeddings`

기본 모델:

- `OPENAI_MODEL`: `gpt-4.1-mini`
- `OPENAI_EMBEDDING_MODEL`: `text-embedding-3-small`

`ENABLE_OPENAI_ANALYSTS=1`일 때만 LLM 분석가 호출이 활성화된다.

### 판단

현재 구현은 단순하고 가볍다. 다만 OpenAI 공식 문서상 신규 기능은 Responses API 중심으로 확장되는 방향이므로, 새 OpenAI 기능을 붙일 때는 Chat Completions 고정이 아니라 Responses API도 검토해야 한다.

즉시 전환은 필수는 아니다. 현재 Chat Completions는 계속 지원되고 있고, 기존 분석 흐름을 바꾸면 회귀 위험이 있다.

### 권고

- 단기: 현재 `httpx` 직접 호출 유지
- 신규 multimodal/agent/tool 기능이 필요할 때 Responses API 검토
- OpenAI SDK 도입은 필요성이 생겼을 때만 검토

## 8. 추가 도입 후보

| 우선순위 | 후보 | 도입 시점 | 이유 |
| --- | --- | --- | --- |
| 높음 | S3 presigned upload | 운영 배포 전 또는 대용량 영상 처리 전 | Gateway 서버 대역폭/메모리 보호 |
| 높음 | Video analyzer abstraction | 영상 분석 고도화 전 | ffmpeg, OpenAI vision, Google ML Kit, TFLite를 교체 가능하게 하기 위함 |
| 중간 | Capacitor | 모바일 앱 배포 확정 시 | Vue 화면/상태 로직 재사용 |
| 중간 | Google ML Kit 또는 TFLite | 모바일 단말 영상/이미지 특징 추출 필요 시 | 서버 부하를 줄이고 on-device 분석 가능 |
| 중간 | OpenAI Responses API | 신규 OpenAI multimodal/tool 기능 필요 시 | 최신 OpenAI 기능 활용 |
| 낮음 | 표준 MCP | 외부 tool/agent 연동이 많아질 때 | tool 호출 표준화와 보안 모델 확장 |

## 9. 현재 유지 권고

현재 단계에서는 다음 스택을 유지하는 것이 가장 현실적이다.

- Frontend: Vue 3 + Vite + TypeScript + Pinia + Vue Router
- Gateway: Fastify + TypeScript
- Agent: FastAPI + Pydantic + httpx
- Worker: Redis Streams + ffmpeg/ffprobe
- DB: PostgreSQL + pgvector
- Cache/Queue: Redis
- Storage: local storage, 운영 전 S3 direct upload 구현 검토

큰 기술 전환보다 우선할 작업:

1. S3 direct upload 구현 여부 결정
2. 영상 분석 고도화 요구 정의
3. `VideoAnalyzerProvider` 추상화 설계
4. Gateway route 분리와 테스트 보강
5. 문서와 실제 구현 상태 동기화

## 참고한 공식 문서

- Capacitor Documentation: https://capacitorjs.com/docs/
- Google ML Kit Migration Guide: https://developers.google.com/ml-kit/migration
- Google ML Kit Object Detection and Tracking: https://developers.google.com/ml-kit/vision/object-detection
- OpenAI Responses vs Chat Completions: https://platform.openai.com/docs/guides/responses-vs-chat-completions
- OpenAI Embeddings Guide: https://platform.openai.com/docs/guides/embeddings/embedding-models%20.class
