# LawCompass Build and Run Guide

작성일: 2026-05-25  
대상: 프로젝트를 이어받는 팀원이 로컬에서 실행, 빌드, 기본 검증을 재현하기 위한 문서입니다.

실제 API 키, 사용자 비밀번호, JWT secret, 내부 토큰 값은 이 문서에 적지 않습니다. 필요한 값은 `.env`에만 둡니다.

## 1. 준비물

- Docker Desktop
- Git
- PowerShell
- Node.js 22 이상. Docker만 사용할 경우 필수는 아니지만, 로컬 프론트/게이트웨이 개발 시 필요합니다.
- Python 3.12 이상. Docker만 사용할 경우 필수는 아니지만, 로컬 Agent/Worker 테스트 시 필요합니다.

## 2. 처음 받은 뒤 확인할 문서

개발이나 디버깅을 시작하기 전 아래 순서로 읽습니다.

1. `DEVELOPMENT_PROMPT.md`
2. `SYSTEM_OVERVIEW.md`
3. `docs/HANDOFF_CHANGE_SUMMARY_2026-05-25.md`
4. `docs/OPERATIONS.md`

## 3. 환경 파일 준비

루트에 `.env`를 준비합니다. 템플릿이 필요한 경우 팀원에게 공유받은 안전한 예시를 기준으로 만듭니다.

필수 확인 항목:

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET`
- `INTERNAL_SERVICE_TOKEN`
- `STORAGE_PROVIDER=local`
- `LOCAL_STORAGE_ROOT`

선택 항목:

- `OPENAI_API_KEY`
- `ENABLE_OPENAI_ANALYSTS`
- `ENABLE_OPENAI_FRAME_ANALYSIS`
- `OPENAI_VISION_MODEL`
- `LAW_API_OC`
- `DATA_GO_SERVICE_KEY`
- `ENABLE_YOLO_FRAME_ANALYSIS`
- `YOLO_MODEL_PATH`
- `YOLO_DEVICE`

기본 운영에서는 비용 방지를 위해 아래 값을 권장합니다.

```env
ENABLE_OPENAI_FRAME_ANALYSIS=0
ENABLE_YOLO_FRAME_ANALYSIS=0
```

실제 영상 프레임 분석 테스트를 할 때만 `ENABLE_OPENAI_FRAME_ANALYSIS=1`로 바꾸고 worker를 재시작합니다.

## 4. Docker로 전체 실행

루트에서 실행합니다.

```powershell
docker compose up --build -d
```

상태 확인:

```powershell
docker compose ps
Invoke-WebRequest -UseBasicParsing http://localhost/health
```

접속 주소:

- 사용자 서비스: `http://localhost`
- 관리자 Agent 테스트 페이지: `http://localhost/admin/agent-test`
- Gateway health: `http://localhost/health`

로그 확인:

```powershell
docker compose logs gateway --tail=100
docker compose logs agent --tail=100
docker compose logs worker --tail=100
```

중지:

```powershell
docker compose down
```

DB/Redis volume까지 완전히 지우는 명령은 기존 데이터를 삭제하므로 인수인계 중에는 사용하지 않습니다.

## 5. DB migration

초기 DB 또는 migration 재적용이 필요하면 아래 명령을 사용합니다.

```powershell
docker compose --profile migrate run --rm db-migrate
```

이미 정상 실행 중인 환경에서는 무리하게 반복 실행하지 말고, `docker compose ps`와 `/health`를 먼저 확인합니다.

## 6. 로컬 개발 실행

Docker 전체 실행이 기본입니다. 개별 서비스만 수정할 때는 아래처럼 실행할 수 있습니다.

Frontend:

```powershell
cd apps/frontend
npm install
npm run dev
```

Gateway:

```powershell
cd apps/gateway
npm install
npm run dev
```

Agent:

```powershell
cd apps/agent
python -m pip install -r requirements.txt
$env:PYTHONPATH='.'
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Worker:

```powershell
cd apps/worker
python -m pip install -r requirements.txt
$env:PYTHONPATH='.'
python -m worker.main
```

로컬 개발 실행은 Docker의 PostgreSQL/Redis와 연결되도록 `.env` 값을 맞춘 뒤 사용합니다.

## 7. 기본 검증

빠른 핵심 검증:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_core.ps1 -SkipDockerBuild
```

Agent 회귀 검증:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_agent_regression.ps1 -SkipDockerBuild
```

최종 준비 상태 검증:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_final_readiness.ps1 -SkipDockerBuild
```

Docker를 사용할 수 없는 환경에서 Node/Vite 계층만 확인:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_final_readiness.ps1 -SkipDockerChecks
```

## 8. 영상 분석 테스트

OpenAI 비용 없이 계약 흐름만 확인할 때는 fixture mode를 사용합니다.

```powershell
$env:ENABLE_OPENAI_FRAME_ANALYSIS="1"
$env:FRAME_ANALYSIS_FIXTURE_MODE="rear_end"
docker compose up -d --force-recreate worker
python scripts/video_agent_e2e.py --video-path "C:/path/to/accident.mp4" --timeout-sec 240 --require-frame-observations --require-agent-video-facts
```

실제 OpenAI 프레임 분석을 사용할 때:

```powershell
$env:ENABLE_OPENAI_FRAME_ANALYSIS="1"
$env:FRAME_ANALYSIS_FIXTURE_MODE=""
docker compose up -d --force-recreate worker
python scripts/video_agent_e2e.py --video-path "C:/path/to/accident.mp4" --timeout-sec 240 --require-frame-observations --require-agent-video-facts
```

테스트 후 비용 방지를 위해 다시 끕니다.

```powershell
$env:ENABLE_OPENAI_FRAME_ANALYSIS="0"
$env:FRAME_ANALYSIS_FIXTURE_MODE=""
docker compose up -d --force-recreate worker
```

YOLO 로컬 검증은 `docs/YOLO_LOCAL_SETUP.md`를 따릅니다. 현재 YOLO는 기본 비활성이고, 사고 판단이 아니라 객체 후보 관찰용 보조 모델입니다.

## 9. 로컬 테스트 산출물 정리

웹에서 영상을 반복 업로드하면 아래 폴더 용량이 빠르게 커집니다.

- `storage/uploads/`
- `storage/frames/`
- `logs/`

인수인계 전에는 필요한 테스트 결과만 따로 기록하고, 업로드 원본과 추출 프레임은 삭제해도 됩니다. 삭제 전에는 경로가 반드시 프로젝트 루트 아래인지 확인합니다.

PowerShell 예시:

```powershell
$root = (Resolve-Path .).Path
$targets = @("storage\uploads", "storage\frames")
foreach ($target in $targets) {
  if (Test-Path -LiteralPath $target) {
    $resolved = (Resolve-Path -LiteralPath $target).Path
    if (-not $resolved.StartsWith($root)) {
      throw "Refusing to clean outside repository: $resolved"
    }
    Get-ChildItem -LiteralPath $resolved -Recurse -Force | Remove-Item -Recurse -Force
  }
}
```

실제 사고 영상 샘플 원본은 저장소 밖에 보관하고, Git에는 올리지 않습니다.

## 10. 인수인계 체크리스트

- `git status --short` 확인
- `.env`, API 키, 동영상 원본, AI Hub 데이터, YOLO 모델 가중치가 staging에 없는지 확인
- `docker compose ps`와 `/health` 확인
- `scripts\verify_final_readiness.ps1 -SkipDockerBuild` 실행
- 변경 사항을 커밋하고 GitHub에 push
- 팀원에게 `docs/HANDOFF_CHANGE_SUMMARY_2026-05-25.md`, `docs/BUILD_AND_RUN_GUIDE.md`, `SYSTEM_OVERVIEW.md` 위치 안내
