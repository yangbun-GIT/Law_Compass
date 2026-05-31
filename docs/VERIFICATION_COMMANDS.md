# LawCompass 검증 명령 기준

작성일: 2026-05-31

이 문서는 LawCompass 개발 단계별 검증 명령을 한곳에서 확인하기 위한 기준 문서다. 실제 비밀값, 원본 사고 영상, AI-Hub 원천 데이터, YOLO 모델 가중치, 대용량 로그는 Git에 올리지 않는다.

## 1. 공통 사전 점검

작업 시작 전 최신 `main`과 최근 병합을 확인한다.

```powershell
git checkout main
git fetch origin
git status --short --branch
git log --oneline --decorate -5
```

커밋 전에는 변경 범위와 민감 파일 포함 여부를 확인한다.

```powershell
git status --short
git diff --stat
git diff --check
```

아래 항목은 커밋하지 않는다.

- `.env`, `.env.dev`, `.env.prod`
- 실제 API key, JWT secret, internal token, NAS 계정 비밀번호
- `storage/`, `logs/`, 원본 사고 영상, AI-Hub 원천 데이터
- YOLO 모델 가중치, `node_modules/`, `dist/`, `__pycache__/`

## 2. 문서만 변경한 경우

문서만 바뀌었고 코드, API 계약, 실행 명령, 환경변수, 서비스 책임 경계가 바뀌지 않았다면 최소 검증은 아래로 충분하다.

```powershell
git diff --check
rg -n "API_KEY=|JWT_SECRET=|NAS_PASSWORD=|PRIVATE KEY|BEGIN .*KEY" . --glob "!node_modules/**" --glob "!logs/**" --glob "!storage/**"
```

문서가 실행 명령이나 경로를 새로 언급하면 실제 파일 존재 여부도 확인한다.

```powershell
rg --files docs scripts apps infra .github
```

## 3. 로컬 빠른 검증

코드 변경 범위가 작고 Docker 전체 재빌드가 필요하지 않을 때 사용한다.

### Gateway

```powershell
cd apps/gateway
npm test
npm run build
```

특정 route나 report composer만 바꿨다면 관련 테스트를 먼저 좁혀 실행한 뒤 필요하면 전체 테스트로 넓힌다.

```powershell
cd apps/gateway
npm test -- --run analysis-routes.test.ts report-composer.test.ts
npm run build
```

### Frontend

```powershell
cd apps/frontend
npm run build
npm run test:display
npm run test:chat
```

### Worker

```powershell
cd apps/worker
python -m unittest discover -s tests
python -m compileall worker tests
```

### Reference 평가

실제 영상과 외부 API 없이 영상 reference 계약만 확인할 때 사용한다.

```powershell
python scripts\validate_reference_case_manifest.py `
  --manifest tests\fixtures\video_accuracy\reference_metrics_manifest.json `
  --output logs\video_accuracy\reference_metrics_manifest_preflight.json

python scripts\evaluate_video_reference_metrics.py `
  --reference-manifest tests\fixtures\video_accuracy\reference_metrics_manifest.json `
  --batch-aggregate tests\fixtures\video_accuracy\reference_metrics_batch_aggregate.json `
  --output logs\video_accuracy\reference_metrics_fixture_eval.json `
  --fail-on-threshold

python -m pytest tests\test_evaluate_video_reference_metrics.py tests\test_reference_case_manifest_policy.py tests\test_validate_video_accuracy_manifest.py -q
```

## 4. Docker 기반 검증

Agent는 로컬 Python 버전과 의존성 차이가 있을 수 있으므로 Docker 컨테이너 검증을 우선한다.

```powershell
docker compose up --build -d
Invoke-WebRequest -UseBasicParsing http://localhost/health
```

Agent 핵심 회귀만 확인한다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_agent_regression.ps1 -SkipDockerBuild
```

프로젝트 핵심 회귀를 확인한다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_core.ps1 -SkipDockerBuild
```

인수인계 또는 발표 전 최소 readiness를 확인한다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_final_readiness.ps1 -SkipDockerBuild
```

Docker Desktop을 사용할 수 없는 환경에서는 `-SkipDockerChecks`를 붙여 Node/Vite 계층만 먼저 확인하고, Docker 검증 미수행 사유를 작업 기록에 남긴다.

## 5. OpenAI/YOLO ON 실제 영상 검증

실제 영상 처리 품질을 완료로 말하려면 OpenAI 프레임 분석과 YOLO 보조 관찰이 모두 켜진 상태에서 확인한다.

필수 조건:

- `.env`에 `OPENAI_API_KEY`가 설정되어 있어야 한다.
- `ENABLE_OPENAI_FRAME_ANALYSIS=1`
- `FRAME_ANALYSIS_FIXTURE_MODE=` 빈 값
- `ENABLE_YOLO_FRAME_ANALYSIS=1`
- `YOLO_MODEL_PATH`가 유효한 로컬 모델 파일을 가리켜야 한다.

Worker를 재기동한다.

```powershell
docker compose up -d --force-recreate worker
docker compose logs worker --tail=100
```

단일 영상 E2E를 확인한다.

```powershell
python scripts\video_agent_e2e.py `
  --video-path "C:\path\to\accident.mp4" `
  --timeout-sec 240 `
  --require-frame-observations `
  --require-agent-video-facts
```

여러 영상을 배치로 측정할 때는 먼저 manifest를 검증한다.

```powershell
python scripts\validate_video_accuracy_manifest.py `
  --manifest logs\video_accuracy\lawyer_reference_manifest.json `
  --min-samples 5 `
  --require-reference `
  --output logs\video_accuracy\manifest_preflight.json
```

그 다음 배치 측정과 reference metrics를 실행한다.

```powershell
python scripts\video_accuracy_batch.py `
  --manifest logs\video_accuracy\lawyer_reference_manifest.json `
  --output-dir logs\video_accuracy\openai_yolo_on_YYYYMMDD

python scripts\evaluate_video_reference_metrics.py `
  --reference-manifest tests\fixtures\video_accuracy\reference_metrics_manifest.json `
  --batch-aggregate logs\video_accuracy\openai_yolo_on_YYYYMMDD\aggregate.json `
  --output logs\video_accuracy\openai_yolo_on_YYYYMMDD_metrics.json `
  --fail-on-threshold
```

실행 후 관리자 진단 또는 DB metadata에서 아래를 확인한다.

- `openai_frame_analysis.enabled=true`
- `yolo_frame_analysis.enabled=true`
- YOLO `summary.class_counts` 또는 `observations` 존재
- merged `metadata.observations`에 OpenAI/YOLO 관찰값이 함께 포함

## 6. 비용 발생 검증

아래 작업은 비용, 네트워크 사용량, 긴 실행 시간이 발생할 수 있다.

- `ENABLE_OPENAI_FRAME_ANALYSIS=1` 상태의 실제 영상 분석
- `scripts/video_accuracy_batch.py` 실제 영상 배치
- AI-Hub 원천 영상 다운로드
- 공개 영상 reference 수집

비용 발생 검증 원칙:

1. 먼저 manifest preflight와 fixture 평가를 실행한다.
2. 실제 영상은 소량 샘플로 시작한다.
3. 출력은 `logs/` 아래에만 저장한다.
4. 실패하거나 기준 미달이면 성공으로 보고하지 않고 현재 단계의 남은 작업에 기록한다.
5. API key, 원본 영상 경로, 원본 라벨, 대용량 산출물은 커밋하지 않는다.

## 7. GitHub CI 확인

push 후에는 GitHub `main` 체크가 모두 성공했는지 확인한다. 현재 CI 필수 흐름은 다음 4개다.

- `LawCompass CI / Frontend`
- `LawCompass CI / Gateway`
- `LawCompass CI / Worker Contracts`
- `LawCompass CI / Agent Contracts`

로컬에서 GitHub check run을 확인할 때는 아래 명령을 사용할 수 있다.

```powershell
$sha = (git rev-parse HEAD).Trim()
$headers = @{ Accept = "application/vnd.github+json" }
$runs = (Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/yangbun-GIT/Law_Compass/commits/$sha/check-runs").check_runs
$runs | Select-Object name,status,conclusion,html_url | ConvertTo-Json -Depth 4
```

하나라도 실패하면 다음 단계로 넘어가기 전에 실패 로그를 확인하고 수정 커밋을 추가한다.

## 8. 실패 기록 기준

검증이 실패하거나 실행하지 못한 경우 완료로 기록하지 않는다. 아래를 현재 작업 문서 또는 `docs/AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md` 진행 기록에 남긴다.

- 실패한 명령
- 실패 원인 또는 추정 원인
- 영향받는 서비스
- 다음에 수행할 수정 작업
- 비용이나 환경 문제로 보류한 경우의 재실행 조건

검증 기준이 새로 바뀌면 이 문서와 `DEVELOPMENT_PROMPT.md`의 verification policy를 함께 확인한다.
