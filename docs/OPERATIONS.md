# LawCompass Quick Ops

## 0) 환경값 준비
- 기본 실행 파일: `.env`
- 공유용 템플릿: `env.example`
- 개발용 로컬 참고 파일인 `.env.dev`는 Git에 올리지 않는다.
- 아래 값 확인
  - `OPENAI_API_KEY` (실제 키)
  - `OPENAI_MODEL` (기본 `gpt-4.1-mini`)
  - `ENABLE_OPENAI_FRAME_ANALYSIS` (영상 프레임 GPT 분석 사용 시 `1`)
  - `OPENAI_VISION_MODEL` (기본 `gpt-4.1-mini`)
  - `OPENAI_FRAME_ANALYSIS_MAX_FRAMES` (기본 `6`, 코드 상한 `8`)
  - `OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS` (기본 `900`, 코드 상한 `1400`)
  - `OPENAI_FRAME_ANALYSIS_DETAIL` (기본 `low`)
  - `OPENAI_FRAME_ANALYSIS_REASONING_EFFORT` (기본 `minimal`, GPT-5 계열 전용)
  - `LAW_API_OC`, `LAW_API_TARGETS`
  - `DATA_GO_SERVICE_KEY`, `DATA_GO_TRAFFIC_URL`

현재 MVP의 업로드 저장소는 `STORAGE_PROVIDER=local`과 `LOCAL_STORAGE_ROOT` 기반 로컬 볼륨이다. `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`는 S3 전환 작업을 진행할 때만 설정한다.

## 1) 개발 기동
```bash
docker compose --env-file .env up --build
```

## 2) KB 샘플 적재
```bash
docker compose exec agent python scripts/ingest_kb.py
```

## 2-1) 외부 법률 API 기반 KB 적재(선택)
사전 조건:
- `.env`에 `LAW_API_OC` 설정(국가법령정보센터 OPEN API 사용자 OC)
- 필요 시 `DATA_GO_SERVICE_KEY`, `DATA_GO_TRAFFIC_URL` 설정

```bash
docker compose exec agent python scripts/ingest_legal_apis.py
```

## 2-2) 외부 API 키/권한 점검
```bash
docker compose exec -T agent sh -lc "PYTHONPATH=/app python scripts/check_external_apis.py"
```

주의:
- 국가법령정보센터 OPEN API는 호출 서버의 IP/도메인 등록이 맞지 않으면 `사용자 정보 검증 실패`가 반환됩니다.
- 공공데이터포털 API는 활용신청 승인 상태/엔드포인트별 권한/요청 파라미터가 맞지 않으면 `Forbidden` 또는 `Unexpected errors`가 반환될 수 있습니다.

## 3) E2E 스모크 테스트
PowerShell:
```powershell
./scripts/smoke_e2e.ps1 -BaseUrl http://localhost
```

## 3-0) 핵심 회귀 검증 일괄 실행
Gateway 테스트/빌드, Frontend 빌드/표시 안전 테스트, Docker 기반 Agent 컴파일/대표 사고 회귀 검증, `/health` 확인을 한 번에 실행합니다.

GitHub에서는 `.github/workflows/ci.yml`이 push/PR마다 Frontend, Gateway, Worker 계약, Agent 계약/회귀 검증을 실행합니다. 실제 외부 API 키나 Docker E2E가 필요한 검증은 아직 CI에 포함하지 않았습니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify_core.ps1
```

이미 Docker 컨테이너가 실행 중이라 이미지 재빌드가 필요 없으면 아래처럼 실행할 수 있습니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify_core.ps1 -SkipDockerBuild
```

Docker Desktop을 사용할 수 없는 환경에서 Node/Vite 계층만 확인하려면 아래 옵션을 사용합니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify_core.ps1 -SkipDockerChecks
```

Agent 계층만 빠르게 확인하려면 아래 명령을 사용합니다. 이 명령은 Agent Python 컴파일, `/internal/v1/*` 라우트 계약, 대표 사고 판단 회귀 시나리오, 근거 검색 품질, 근거 소스 복구력, Agent 품질 패킷 계약을 확인합니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify_agent_regression.ps1
```

Docker 없이 `apps/agent` 폴더에서 Agent 스크립트를 직접 실행할 때는 앱 루트를 Python 경로에 포함해야 합니다.

```powershell
cd apps/agent
$env:PYTHONPATH='.'
python -m unittest tests.test_knia_cache_fallback
python scripts/check_internal_routes.py
python scripts/test_agent_regression_scenarios.py
python scripts/test_evidence_search_quality.py
python scripts/test_evidence_source_resilience.py
python scripts/test_agent_quality_report.py
```

이미 Docker 컨테이너가 실행 중이면 재빌드 없이 실행할 수 있습니다.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify_agent_regression.ps1 -SkipDockerBuild
```

Worker job payload/result 계약만 빠르게 확인하려면 아래 명령을 사용합니다. PostgreSQL, Redis, ffmpeg, OpenAI 키 없이 로컬 순수 함수 계약을 검증합니다.

```powershell
cd apps/worker
python -m unittest discover -s tests
python -m compileall worker tests
```

## 3-1) 영상 프레임 분석 점검
프레임 분석은 비용 방지를 위해 기본 비활성화되어 있습니다. 사용하려면 `.env`에서 `ENABLE_OPENAI_FRAME_ANALYSIS=1`로 설정한 뒤 worker를 재시작합니다.

현재 기본 비용 정책:
- 모델: `gpt-4.1-mini`
- 이미지 상세도: `low`
- 최대 분석 프레임: `6`장, 코드 상한 `8`장
- 최대 출력 토큰: `900`, 코드 상한 `1400`
- 저장 정책: Responses API 요청에 `store=false`를 전달

OpenAI 공식 문서 기준으로 `gpt-4.1-mini`는 이미지 입력을 지원하는 저비용 비추론 모델입니다. 이 프로젝트의 프레임 분석은 사고 법률 판단이 아니라 관찰 가능한 물리 사실을 JSON으로 짧게 추출하는 작업이므로, reasoning 토큰이 필요한 GPT-5 계열보다 비추론 모델을 기본으로 둡니다. 이미지 입력은 `detail=low`일 때 프레임당 고정 저해상도 토큰 예산을 사용하므로 짧은 사고 영상의 관찰값 추출 검증에는 이 설정을 우선 사용합니다. 품질 비교가 필요할 때만 `OPENAI_VISION_MODEL=gpt-5-mini` 또는 `OPENAI_FRAME_ANALYSIS_DETAIL=high`로 일시 상향합니다.

2026-05-22 로컬 검증에서는 같은 영상/프레임 조건에서 `gpt-5-nano`는 관찰값을 반환하지 않았고, `gpt-5-mini`는 출력 토큰 한도에서 중단되었습니다. `gpt-4.1-mini`는 관찰값 생성 및 Agent 영상 사실 반영 E2E를 통과했으므로 현재 기본값으로 유지합니다.

```bash
docker compose up -d --build worker
docker compose logs worker --tail=100
```

worker 로그의 `openai_frame_analysis` 항목에서 분석 모델, 프레임 수, `observations`를 확인할 수 있습니다. 이 출력에는 API 키를 포함하지 않습니다.

프레임 분석 결과에는 `observation_quality_summary`가 함께 기록됩니다. 품질 확인 시 아래 값을 우선 봅니다.
- `observation_count`: 모델/fixture가 반환한 관찰값 수
- `no_frame_reference_count`: 프레임 근거가 없어 Agent 사실 승격에서 보류될 가능성이 큰 관찰값 수
- `single_frame_observation_count`: 짧은 영상에서 보강 입력으로는 쓸 수 있지만, 사용자 입력과 충돌하면 우선권을 갖기 어려운 관찰값 수
- `multi_frame_observation_count`: 여러 프레임에서 뒷받침된 관찰값 수

Agent의 `video_input_contract.observation_quality_summary`도 함께 확인합니다. 프레임 분석 계열 source는 최소 1개 frame ref가 있어야 사실로 승격되며, 신호위반/횡단보도/스쿨존 같은 고위험 필드는 일반 물리 사실보다 높은 confidence 기준을 적용합니다.

OpenAI 비용 없이 계약 흐름만 검증하려면 로컬 fixture 모드를 사용할 수 있습니다. 이 모드는 실제 모델 판단이 아니라, 프레임 관찰값이 worker metadata, Agent `video_input_contract`, `fact_arbitration`, easy-report 안전 카드까지 전달되는지 확인하는 용도입니다.

```powershell
$env:ENABLE_OPENAI_FRAME_ANALYSIS="1"
$env:FRAME_ANALYSIS_FIXTURE_MODE="rear_end"
docker compose up -d --force-recreate worker
python scripts/video_agent_e2e.py --video-path "C:/path/to/accident.mp4" --timeout-sec 240 --require-frame-observations --require-agent-video-facts
```

품질 보류 관찰값이 보완 질문과 재분석으로 이어지는 흐름은 `held_quality` fixture로 비용 없이 확인할 수 있습니다.

```powershell
$env:ENABLE_OPENAI_FRAME_ANALYSIS="1"
$env:FRAME_ANALYSIS_FIXTURE_MODE="held_quality"
docker compose up -d --force-recreate worker
python scripts/video_agent_e2e.py --video-path "C:/path/to/accident.mp4" --timeout-sec 240 --require-frame-observations --exercise-held-observation-followup
```

fixture 점검 후 기본 모드로 되돌리려면 아래처럼 worker를 재기동합니다.

```powershell
$env:ENABLE_OPENAI_FRAME_ANALYSIS="0"
$env:FRAME_ANALYSIS_FIXTURE_MODE=""
docker compose up -d --force-recreate worker
```

## 3-2) 실제 영상 기반 Agent E2E 점검
로컬에 있는 사고 영상을 저장소에 복사하지 않고 경로로만 넘겨 업로드, 전처리, 영상 분석 job, 결과 리포트의 Agent 검증 카드까지 확인합니다.

```bash
python scripts/video_agent_e2e.py --video-path "C:/path/to/accident.mp4" --timeout-sec 240
```

OpenAI 프레임 분석까지 실제 모델로 필수 검증하려면 `FRAME_ANALYSIS_FIXTURE_MODE`를 비우고, worker를 `ENABLE_OPENAI_FRAME_ANALYSIS=1` 및 유효한 `OPENAI_API_KEY`가 있는 상태로 재기동한 뒤 아래처럼 실행합니다.

```bash
python scripts/video_agent_e2e.py --video-path "C:/path/to/accident.mp4" --timeout-sec 240 --require-frame-observations --require-agent-video-facts
```

영상 관찰값이 품질 기준 때문에 보류된 경우, 그 보류 항목이 보완 질문으로 생성되고 재분석에 반영되는지까지 검증하려면 아래 옵션을 추가합니다. 이 옵션은 `missing_info.questions` 안에 품질 보류 질문이 없으면 실패합니다.

```bash
python scripts/video_agent_e2e.py --video-path "C:/path/to/accident.mp4" --timeout-sec 240 --exercise-held-observation-followup
```

검증 항목:
- `/uploads/local` 로컬 영상 업로드
- `/uploads/complete` 후 `video_preprocess` job 성공
- worker가 자동 등록한 `video_analyze` job 성공
- `/cases/{caseId}/easy-report`에 `agent_process_card` 존재
- `agent_process_card`에 raw `agent_trace`, `reflection_loop`, `packet`, 내부 step id가 노출되지 않음
- `--require-frame-observations` 사용 시 OpenAI 프레임 분석이 켜져 있고, 오류 없이 1개 이상의 관찰값을 반환함
- `--require-agent-video-facts` 사용 시 Agent의 `video_input_contract`가 프레임 관찰값을 수용하고 `fact_arbitration`이 영상 기반 사실을 실제 적용함
- `--exercise-held-observation-followup` 사용 시 품질 보류 영상 관찰값 질문에 답변을 제출하고, `/reanalyze` 응답에 `analysis_change_card`가 생성됨
- E2E 출력의 `frame_analysis.observation_quality_summary`와 `agent_video_input.observation_quality_summary`에서 프레임 근거 누락, 단일 프레임 관찰값, Agent 승격/보류 수를 확인함

`ENABLE_OPENAI_FRAME_ANALYSIS=0`이면 프레임은 추출되지만 GPT 프레임 관찰값(`observations`)은 0개일 수 있습니다. 이 상태에서도 영상 전처리와 Agent 입력 계약 연결은 확인할 수 있습니다.

## 3-3) 관리자용 Agent trace 진단
일반 결과 화면에는 raw `agent_trace`와 `reflection_loop`를 노출하지 않습니다. 내부 점검이 필요할 때는 관리자 계정 또는 `x-admin-token`이 있는 로그인 세션으로 아래 API를 호출해 안전한 메타데이터 요약만 확인합니다.

```bash
GET /api/v1/admin/cases/{caseId}/agent-trace
GET /api/v1/admin/cases/{caseId}/agent-trace?version=2
```

응답에는 단계별 status, packet 요약, 영상 입력 계약 카운트, 사실 중재 카운트, 근거 충족도, 판단 계약, reflection 상태가 포함됩니다. 사용자 원문, 비밀번호, 토큰, API 키, raw evidence chunk id는 포함하지 않습니다.

## 4) 프론트에서 기능 확인
1. 회원가입
2. 로그인
3. 케이스 생성
4. 영상 업로드(local upload -> complete)
5. 텍스트 분석
6. 영상 분석 큐 등록 후 작업 상태 자동 갱신
7. 결과 리포트/근거 펼쳐보기
8. 업로드 영상 재생 URL/다운로드 URL 발급

## 5) 재배포 루틴(단일 서버)
1. 새 이미지 빌드
2. `docker compose pull` 또는 `up --build`
3. `docker compose up -d --remove-orphans`
4. `docker compose ps` + `/ready` 확인
5. 장애 시 이전 이미지 태그로 롤백

## 6) 보안 주의
- `OPENAI_API_KEY`는 절대 외부에 공개하지 말고 서버 환경변수로만 관리
- 키가 노출되었으면 즉시 OpenAI 콘솔에서 회전(재발급) 권장
