# LawCompass

교통사고 설명과 블랙박스 영상을 바탕으로 사고 대분류, KNIA 과실비율 기준, 가감요소, 추가 확인 질문을 정리하는 AI 사고 분석 보조 서비스입니다.

## 현재 배포 사이트

LawCompass는 현재 JCloud VM에 배포되어 있으며, 일반 사용자는 아래 주소로 바로 접속하면 됩니다.

- 배포 URL: http://113.198.66.75:19232
- 주요 기능: 회원가입/로그인, 케이스 생성, 사고 설명 입력, 블랙박스 영상 업로드, AI 분석, 결과 화면, KNIA 검색순위
- 결과 화면의 업로드 영상 다시보기는 Gateway가 짧게 만료되는 HMAC 링크를 발급한 뒤 재생합니다.

> GitHub Pages는 정적 프론트엔드 배포에만 사용할 수 있습니다. 영상 업로드, AI 분석, 로그인, DB 저장, Redis job, KNIA/RAG 검색까지 실제로 동작하려면 현재 JCloud처럼 Gateway, Agent, Worker, PostgreSQL, Redis가 함께 실행되는 서버가 필요합니다.

## 프로젝트 구성

- Frontend: Vue 3 + TypeScript + Vite
- Gateway: Fastify + TypeScript
- Agent: FastAPI + OpenAI API 연동
- Worker: Redis Streams Consumer Group
- DB: PostgreSQL + pgvector
- Cache/Queue: Redis
- Edge: Caddy
- Storage: StorageAdapter 기반 `local`, 비활성 legacy `s3`, `nas_sftp` 드라이버. NAS는 앱/DB 실행 위치가 아니라 영상, 프레임, 리포트, DB 백업 파일 저장소로만 사용합니다.

## 서버 운영자용 실행 방법

현재 JCloud 서버에서는 저장소를 최신화한 뒤 Docker Compose로 서비스를 재시작합니다.

```bash
cd /home/ubuntu/lawcompass
git pull --ff-only origin main
docker compose -f compose.yaml -f compose.jcloud.yaml up -d --build
docker compose -f compose.yaml -f compose.jcloud.yaml ps
```

운영 상태 확인:

```bash
docker compose -f compose.yaml -f compose.jcloud.yaml ps
docker compose -f compose.yaml -f compose.jcloud.yaml logs --tail=100 gateway
docker compose -f compose.yaml -f compose.jcloud.yaml logs --tail=100 worker
```

JCloud 배포는 `compose.jcloud.yaml`을 기준으로 하며, 2GB RAM 환경에 맞춰 Worker timeout, YOLO CPU 설정, PostgreSQL/Redis 리소스 제한을 낮춘 구성을 사용합니다.

## 로컬 개발 실행

로컬에서 전체 스택을 다시 띄워 개발하려면 `.env`가 필요합니다. 실제 secret 값은 README나 Git에 기록하지 않습니다.

```powershell
Copy-Item env.example .env
# .env 안의 OPENAI_API_KEY, JWT secret, DB/Redis, STORAGE_DRIVER 값을 로컬 환경에 맞게 채웁니다.
docker compose --env-file .env up --build
```

접속:

- Frontend/Edge: http://localhost
- Gateway health: http://localhost/health

초기 지식 데이터 또는 KNIA JSON을 다시 적재해야 하는 경우에는 운영 문서를 먼저 확인한 뒤 필요한 import 명령만 실행합니다.

```powershell
docker compose exec agent python scripts/ingest_kb.py
python apps/agent/scripts/import_knia_fault_ratio_json.py --path scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_review.json --rebuild-embeddings
```

## 검증 명령

작업 범위별 최소 검증:

```powershell
cd apps/frontend
npm run build
npm run test:display
npm run test:chat
```

```powershell
cd apps/gateway
npm test
npm run build
```

Agent/Worker 또는 전체 흐름을 건드린 경우:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_final_readiness.ps1 -SkipDockerBuild
```

## 문서

- 운영 절차: `docs/OPERATIONS.md`
- 로컬 빌드/실행: `docs/BUILD_AND_RUN_GUIDE.md`
- Oracle Cloud Free Tier 운영: `ORACLE_CLOUD_FREE_TIER_DEPLOYMENT.md`
- JCloud/저사양 VM 설정 기준: `compose.jcloud.yaml`, `SYSTEM_OVERVIEW.md`
- 문서 선택 가이드: `docs/README.md`
