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
  - `OPENAI_TIMEOUT_SEC` (영상 프레임 실제 분석 권장 `45`; 너무 낮으면 긴 프레임 묶음에서 read timeout 가능)
  - `OPENAI_FRAME_ANALYSIS_MAX_FRAMES` (코드 기본 `18`, 코드 상한 `18`; `.env`에 값이 있으면 해당 값이 우선)
  - `OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS` (기본 `2200`, 코드 상한 `3000`)
  - `OPENAI_FRAME_ANALYSIS_ZERO_OBSERVATION_RETRY` (기본 `1`; 프레임은 충분하지만 관찰값이 0개일 때 1회 재시도)
  - `OPENAI_FRAME_ANALYSIS_ERROR_RETRY` (기본 `1`; timeout 같은 일시 오류에서 1회 재시도)
  - `OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES` (기본 `6`; 재시도 최소 프레임 수)
  - `VIDEO_EVENT_WINDOW_CLUSTER_GAP_SEC` (기본 `3.0`; scene-change 이벤트를 같은 사고 후보 구간으로 묶는 최대 간격)
  - `VIDEO_EVENT_WINDOW_MAX_CANDIDATES` (기본 `6`; Worker가 프레임에 표시할 사고 후보 구간 수 상한)
  - `OPENAI_FRAME_ANALYSIS_DETAIL` (기본 `high`)
  - `OPENAI_FRAME_ANALYSIS_REASONING_EFFORT` (기본 `minimal`, GPT-5 계열 전용)
  - `LAW_API_OC`, `LAW_API_TARGETS`
  - `DATA_GO_SERVICE_KEY`, `DATA_GO_TRAFFIC_URL`

현재 MVP의 업로드 저장소는 `STORAGE_PROVIDER=local`과 `LOCAL_STORAGE_ROOT` 기반 로컬 볼륨이다. `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`는 S3 전환 작업을 진행할 때만 설정한다.

OpenAI 사용량, 정적 fallback 의존, KNIA/법령/판례 원문 coverage, S3 전환, API 사용량 제한, UI 수용성 점검은 `docs/OPERATING_RISK_ROADMAP.md`를 기준으로 추적한다. OpenAI/LLM/영상 분석, evidence source, storage, rate limit, 관리자 진단을 변경하는 작업은 이 로드맵의 현재 책임 경계와 충돌하지 않는지 확인한다.

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
- 이미지 상세도: `high`
- 최대 분석 프레임: `18`장, 코드 상한 `18`장
- 최대 출력 토큰: `2200`, 코드 상한 `3000`
- 저장 정책: Responses API 요청에 `store=false`를 전달

OpenAI 공식 문서 기준으로 `gpt-4.1-mini`는 이미지 입력을 지원하는 저비용 비추론 모델입니다. 이 프로젝트의 프레임 분석은 사고 법률 판단이 아니라 관찰 가능한 물리 사실을 JSON으로 짧게 추출하는 작업이므로, reasoning 토큰이 필요한 GPT-5 계열보다 비추론 모델을 기본으로 둡니다. 다만 교차로 신호·충돌 대상·상대 차량 진행 방향처럼 작은 화면 단서가 중요한 사고 영상 검증에서는 `detail=high`와 18장 프레임을 기본 검증값으로 사용합니다. 비용 제한이 더 중요할 때만 `OPENAI_FRAME_ANALYSIS_DETAIL=low` 또는 프레임 수 축소를 일시 적용합니다.

2026-05-22 로컬 검증에서는 같은 영상/프레임 조건에서 `gpt-5-nano`는 관찰값을 반환하지 않았고, `gpt-5-mini`는 출력 토큰 한도에서 중단되었습니다. `gpt-4.1-mini`는 관찰값 생성 및 Agent 영상 사실 반영 E2E를 통과했으므로 현재 기본값으로 유지합니다.

```bash
docker compose up -d --build worker
docker compose logs worker --tail=100
```

worker 로그의 `openai_frame_analysis` 항목에서 분석 모델, 프레임 수, `observations`를 확인할 수 있습니다. 이 출력에는 API 키를 포함하지 않습니다. OpenAI 응답에 `usage`가 포함되면 worker 결과의 안전 메타데이터에 token usage가 함께 남습니다.

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
이 옵션은 보완 질문 생성뿐 아니라 답변 제출 후 새 분석 버전 생성, `analysis_change_card.question_flow`, 케이스 `structured_facts`의 답변 상태 기록, 최신 easy-report의 변화 카드 보존 여부까지 확인합니다.

```powershell
$env:ENABLE_OPENAI_FRAME_ANALYSIS="1"
$env:FRAME_ANALYSIS_FIXTURE_MODE="held_quality"
docker compose up -d --force-recreate worker
python scripts/video_agent_e2e.py --video-path "C:/path/to/accident.mp4" --timeout-sec 240 --require-frame-observations --exercise-held-observation-followup
```

영상 관찰값과 사용자 입력이 충돌한 뒤 보완 질문 답변으로 재분석되는 흐름은 `conflict_stopped` fixture로 확인합니다. 기본 E2E 케이스는 `stopped=true`를 포함하고, fixture는 `stopped=false` 관찰값을 반환하므로 `/reanalyze`가 최신 영상 메타데이터를 다시 Agent에 전달하는지 확인하기에 적합합니다.

```powershell
$env:ENABLE_OPENAI_FRAME_ANALYSIS="1"
$env:FRAME_ANALYSIS_FIXTURE_MODE="conflict_stopped"
docker compose up -d --force-recreate worker
python scripts/video_agent_e2e.py --video-path "C:/path/to/accident.mp4" --timeout-sec 240 --require-frame-observations --exercise-conflict-followup
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

여러 사고 영상 샘플을 같은 기준으로 반복 측정하려면 배치 측정 스크립트를 사용합니다. 이 스크립트는 `video_agent_e2e.py`를 샘플별로 실행하고, 각 결과와 `aggregate.json`을 `logs/video_accuracy/` 아래에 저장합니다. `logs/`는 Git에 올라가지 않으므로 실제 영상 측정 결과와 로컬 경로가 저장소에 노출되지 않습니다.

실제 OpenAI 프레임 분석 배치를 실행하기 전에는 manifest preflight를 먼저 실행합니다. 이 검사는 OpenAI API를 호출하지 않고, 샘플 수, 중복 이름, 영상 파일 경로, `case_json`, `reference.purpose=evaluation_only_not_agent_input`, reference 정보가 case 입력에 섞였는지를 확인합니다.

```bash
python scripts/validate_video_accuracy_manifest.py \
  --manifest logs/video_accuracy/lawyer_reference_manifest.json \
  --min-samples 5 \
  --require-reference \
  --output logs/video_accuracy/manifest_preflight.json
```

문서 예시처럼 로컬 영상 파일이 없는 manifest의 구조만 확인하려면 `--allow-missing-files`를 추가합니다. 실제 측정 manifest에서는 이 옵션을 쓰지 않고 모든 영상과 case JSON이 존재하는 상태에서 통과시킵니다.

```bash
python scripts/video_accuracy_batch.py --manifest config/video_accuracy_samples.example.json --output-dir logs/video_accuracy
```

실제 OpenAI 분석 기준으로 측정하려면 먼저 worker를 `ENABLE_OPENAI_FRAME_ANALYSIS=1`, `FRAME_ANALYSIS_FIXTURE_MODE=` 상태로 재시작해야 합니다. 기대값이 틀린 샘플도 측정 결과로 남기려면 기본 실행을 사용하고, 기대값 불일치를 실패로 처리하려면 `--fail-on-mismatch`를 추가합니다. 샘플별 입력 케이스는 `case_json`으로 지정할 수 있으며, 파일은 `case` 객체를 포함하거나 케이스 payload 자체를 포함할 수 있습니다.

`aggregate.json`에는 전체 통과/불일치 수 외에 `video_flow_summary`, `question_priority_summary`, `field_summary`, `calibration_readiness`, `recommendations`가 포함됩니다. `video_flow_summary`는 전체 프레임 관찰값이 Agent에서 반영, 확인, 보류, 참고 관찰, 충돌 중 어디로 흘렀는지 비율로 보여줍니다. `question_priority_summary`는 결과 화면에서 가장 먼저 떠오른 보완 질문 라벨과 우선순위 분포를 보여줍니다. `field_summary`는 필드별 프레임 관찰 수, Agent fact 반영 수, 사용자 확인 수, 충돌 수, 기대값 통과율을 보여줍니다. `calibration_readiness=collect_more_samples`이면 threshold를 조정하지 말고 실제 사고 영상 샘플을 더 모아야 합니다. `keep_conservative_thresholds`, `prioritize_conflict_questions`, `review_conflict_gate`, `inspect_field_mismatch` 추천이 나오면 prompt나 threshold를 바꾸기 전에 원본 프레임, 사용자 입력, Agent 충돌 정책, 보완 질문 순서를 먼저 확인합니다.

`visual_evidence_limited`가 참고 관찰로 표시되면 OpenAI가 프레임과 bounded retry를 실행했지만 직접 판단에 반영할 물리 사실을 충분히 찾지 못했다는 의미입니다. 이 값은 과실 판단 fact가 아니며, 어두운 야간 영상·충돌 순간 미포착·재촬영 화면처럼 추가 자료 또는 사용자 보완 입력이 필요한 경우를 표시하는 품질 신호로만 사용합니다.

2026-05-24 최신 OpenAI ON 재측정은 아래 흐름으로 수행했다. 실제 OpenAI 호출 후에는 반드시 worker를 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=`로 되돌린다.

```bash
python scripts/video_accuracy_batch.py \
  --manifest logs/video_accuracy/lawyer_reference_manifest.json \
  --output-dir logs/video_accuracy/stage4_openai_latest_20260524 \
  --timeout-sec 300

python scripts/reference_guidance_eval.py \
  --manifest logs/video_accuracy/lawyer_reference_manifest.json \
  --batch-output logs/video_accuracy/stage4_openai_latest_20260524/aggregate.json \
  --output logs/video_accuracy/reference_guidance_eval_stage4_latest_20260524.json

python scripts/reference_evidence_alignment_eval.py \
  --reference-eval logs/video_accuracy/reference_guidance_eval_stage4_latest_20260524.json \
  --batch-output logs/video_accuracy/stage4_openai_latest_20260524/aggregate.json \
  --output logs/video_accuracy/reference_evidence_alignment_stage4_latest_20260524.json

python scripts/reference_guidance_calibration_eval.py \
  --manifest logs/video_accuracy/lawyer_reference_manifest.json \
  --batch-output logs/video_accuracy/stage4_openai_latest_20260524/aggregate.json \
  --reference-eval logs/video_accuracy/reference_guidance_eval_stage4_latest_20260524.json \
  --output logs/video_accuracy/reference_guidance_calibration_stage4_latest_20260524.json
```

이 재측정에서 5개 샘플의 pipeline은 모두 통과했지만, 사고 2 신호 전환 샘플은 근거 카드와 첫 보완 질문이 신호/CCTV 쟁점보다 급정거/후방추돌 쪽으로 치우쳐 `needs_user_flow_calibration`으로 남았다. 이 상태는 threshold 문제가 아니라 신호 전환 사고의 근거 검색, 카드 선택, 질문 우선순위 보강 항목으로 분류한다.

전문 변호사 의견, 경찰/보험 처리 결과, 실제 분쟁 결과가 있는 경우에는 manifest의 `reference` 메타데이터에만 기록합니다. 이 값은 배치 결과 JSON에 보존되지만 Agent 입력 payload로 전달되지 않습니다. 실제 사용자는 전문적인 법률 의견을 입력하지 못할 수 있으므로 `case_json`에는 일반 사용자가 작성할 법한 짧은 사고 설명과 확인 가능한 사실만 넣고, `reference`는 결과 비교와 캘리브레이션 판단에만 사용합니다.

전문가 참고 의견 샘플이 실제 안내 품질 기준에 얼마나 가까운지 보려면 `reference_guidance_eval.py`를 실행합니다. 이 스크립트는 영상 관찰값의 성공 여부만 보지 않고, manifest의 `evaluation_focus`별로 사용자 입력 fact, 영상 관찰값, 충돌 여부, 다음에 필요한 KNIA/법령/판례/보험 근거 확인 항목을 분리합니다. 결과는 `logs/video_accuracy/reference_guidance_eval.json`에 저장하는 것을 권장합니다.

```bash
python scripts/reference_guidance_eval.py \
  --manifest logs/video_accuracy/lawyer_reference_manifest.json \
  --batch-output logs/video_accuracy/stage4_openai_flow/aggregate.json \
  --output logs/video_accuracy/reference_guidance_eval_stage5.json
```

여러 `--batch-output`을 넘기면 같은 샘플의 재시도 결과를 병합합니다. 실패했던 샘플이 재시도에서 통과한 경우 통과 결과를 우선 사용하므로, 표시 오류 수정 후 단일 샘플만 재측정한 결과도 전체 평가에 반영할 수 있습니다. 이 평가는 판결 정답 맞추기가 아니라, “예상 안내를 만들기 전에 어떤 사실/근거 검증이 남았는가”를 찾기 위한 단계입니다.

`reference_guidance_eval.py` 출력에는 batch의 `video_flow_summary`와 `question_priority_summary`가 다시 포함됩니다. 따라서 실제 OpenAI 프레임 관찰값이 결과 화면에서 `반영`, `확인`, `보류`, `참고`, `충돌` 중 어디로 흘렀는지와, 어떤 보완 질문이 가장 먼저 올라오는지를 전문가 reference 평가와 한 번에 대조할 수 있습니다. `recommendations`는 다음 단계를 자동 결정하지 않고, 충돌 샘플 우선 확인, 근거 대조 진입 가능 샘플, 표시 계약 문제 여부를 점검하기 위한 운영 메모로 사용합니다.

검증 항목:
- `/uploads/local` 로컬 영상 업로드
- `/uploads/complete` 후 `video_preprocess` job 성공
- worker가 자동 등록한 `video_analyze` job 성공
- `/cases/{caseId}/easy-report`에 `agent_process_card` 존재
- `/cases/{caseId}/easy-report`에 `expert_guidance_card` 존재
- `agent_process_card`에 raw `agent_trace`, `reflection_loop`, `packet`, 내부 step id가 노출되지 않음
- `expert_guidance_card`에 법률 관점 과실 참고 범위, 보험 처리 예상, 확인 근거가 있고 raw `expert_guidance_sections`, `chunk_id`, cache/model metadata가 노출되지 않음
- `--require-frame-observations` 사용 시 OpenAI 프레임 분석이 켜져 있고, 오류 없이 1개 이상의 관찰값을 반환함
- `--require-agent-video-facts` 사용 시 Agent의 `video_input_contract`가 프레임 관찰값을 수용하고 `fact_arbitration`이 영상 기반 사실을 실제 적용함
- `--exercise-held-observation-followup` 사용 시 품질 보류 영상 관찰값 질문에 답변을 제출하고, `/reanalyze` 응답에 `analysis_change_card`가 생성됨
- `--exercise-conflict-followup` 사용 시 영상 관찰값과 사용자 입력이 충돌한 질문에 답변을 제출하고, `/reanalyze`가 최신 업로드 영상 메타데이터를 다시 Agent에 전달해 해당 충돌이 해소되는지 확인함
- E2E 출력의 `frame_analysis.observation_quality_summary`와 `agent_video_input.observation_quality_summary`에서 프레임 근거 누락, 단일 프레임 관찰값, Agent 승격/보류 수를 확인함

`ENABLE_OPENAI_FRAME_ANALYSIS=0`이면 프레임은 추출되지만 GPT 프레임 관찰값(`observations`)은 0개일 수 있습니다. 이 상태에서도 영상 전처리와 Agent 입력 계약 연결은 확인할 수 있습니다.

배치 manifest에서 `exercise_conflict_followup: true`를 지정하면 `video_accuracy_batch.py`가 샘플별 `conflict_followup`과 전체 `conflict_followup_summary`를 남깁니다. 이 값은 정답 판정이 아니라 “영상-사용자 충돌 질문에 답한 뒤 같은 영상 근거를 유지한 재분석이 가능한가”를 확인하는 운영 지표입니다.

`reference_guidance_eval.py`는 `conflict_followup.latest_conflict_count=0`인 샘플을 `conflict_resolved_ready_for_evidence_review`로 분류합니다. 이 상태는 충돌이 완전히 사라져 바로 최종 판정한다는 뜻이 아니라, 같은 영상 근거를 유지한 재분석이 성공했으므로 다음 단계에서 KNIA 기준, 법령, 판례, 보험 처리 근거 대조로 넘어갈 수 있다는 뜻입니다. `latest_conflict_count`가 남아 있거나 `conflict_followup.present=false`이면 기존처럼 `needs_conflict_resolution_before_guidance`로 남겨 사용자 확인 질문 또는 관리자 진단을 먼저 진행합니다.

배치 측정 결과의 `expert_guidance_summary`는 샘플별 전문가 관점 결과 카드가 실제 사용자 화면 기준으로 표시 가능한지 집계합니다. `reference_guidance_eval.py`는 이 값을 다시 읽어 `expert_guidance_status_counts`를 생성합니다. `expert_guidance_ready_for_reference_review`는 법률/보험/근거 표시가 갖춰졌고 쟁점별 근거 대조로 넘어갈 수 있음을 뜻합니다. `expert_guidance_safe_with_pending_facts`는 카드가 표시되지만 충돌/보완 사실을 먼저 확인해야 함을 뜻합니다. `expert_guidance_needs_display_fix` 또는 `missing_expert_guidance_card`가 나오면 정확도 조정보다 결과 payload와 표시 계약을 먼저 고쳐야 합니다.

전문가 안내 카드의 실제 근거가 전문가 참고 쟁점과 맞는지 보려면 `reference_evidence_alignment_eval.py`를 실행합니다. 이 평가는 `reference_guidance_eval.py`에서 `ready_for_legal_knia_insurance_evidence_eval`로 분류된 샘플만 기본 대상으로 삼고, 각 쟁점별로 법률 근거, KNIA 기준, 보험 처리 안내가 사용자 화면 근거 카드에 함께 준비됐는지 확인합니다. 또한 근거 `title`과 `reason`이 쟁점별 필수 키워드 묶음과 내용상 맞는지 검사하고, 현재 사고 쟁점과 맞지 않는 추가 근거가 섞이면 `extra_basis_review`로 표시합니다.

```bash
python scripts/reference_evidence_alignment_eval.py \
  --reference-eval logs/video_accuracy/reference_guidance_eval_stage5.json \
  --sample-dir logs/video_accuracy/stage7_evidence_content_capture \
  --output logs/video_accuracy/reference_evidence_alignment_stage7.json
```

샘플별 E2E JSON 디렉터리가 없고 `video_accuracy_batch.py`의 `aggregate.json`에 상세 `expert_guidance`가 들어 있다면 `--batch-output`만으로도 평가할 수 있습니다. 충돌 보완 후 ready로 승격된 샘플을 포함하려면 Stage 10 이후의 `reference_guidance_eval` 결과를 넘깁니다.

```bash
python scripts/reference_evidence_alignment_eval.py \
  --reference-eval logs/video_accuracy/stage10_eval_fixture/reference_guidance_eval_stage11_resolved_3_5.json \
  --batch-output logs/video_accuracy/stage11_guidance_capture/aggregate.json \
  --output logs/video_accuracy/reference_evidence_alignment_stage11.json
```

`ready_for_stage8_guidance_calibration`은 법률/KNIA/보험 family와 근거 제목·본문 요약이 모두 전문가 쟁점에 맞아 다음 안내 문구/과실 범위 캘리브레이션으로 넘어갈 수 있음을 뜻합니다. `needs_evidence_family_retrieval`은 Agent 검색어 또는 fallback 근거를 보강해야 함을 뜻하고, `needs_evidence_content_fit`은 family는 있으나 근거 제목 또는 reason이 쟁점 내용과 맞지 않음을 뜻합니다. 이 스크립트는 `logs/` 아래 결과를 읽고 쓰므로 실제 영상 경로와 측정 결과가 Git에 포함되지 않습니다.

전문가 안내 카드의 과실 참고 범위와 사용자 보완 질문 우선순위가 실제 사용자 흐름에 맞는지 보려면 `reference_guidance_calibration_eval.py`를 실행합니다. 이 평가는 근거가 이미 맞는 샘플을 대상으로, `expert_guidance_card.fault_range_label`이 reference band와 겹치는지, 근거 제목/사유가 쟁점 키워드를 유지하는지, 신호 전환처럼 결론을 바꾸는 질문이 인명피해/파손 같은 후속 처리 질문보다 먼저 노출되는지 확인합니다.

```bash
python scripts/reference_guidance_calibration_eval.py \
  --manifest logs/video_accuracy/lawyer_reference_manifest.json \
  --batch-output logs/video_accuracy/stage11_guidance_capture/aggregate.json \
  --reference-eval logs/video_accuracy/stage10_eval_fixture/reference_guidance_eval_stage11_resolved_3_5.json \
  --output logs/video_accuracy/reference_guidance_calibration_eval_stage11.json
```

`--reference-eval`을 함께 넘기면 `ready_for_legal_knia_insurance_evidence_eval`이 아닌 샘플은 `blocked_by_reference_gate`로 남깁니다. 따라서 사고 3·5처럼 영상-사용자 충돌이 있었던 샘플은 확인 질문으로 충돌을 해소한 reference 평가 결과가 있어야 과실 범위/문구 캘리브레이션 대상이 됩니다. `calibrated_for_user_flow`는 과실 범위, 근거 문맥, 추가 확인 항목, 첫 보완 질문이 현재 reference 기준에서 사용자 흐름에 맞다는 뜻입니다. `needs_user_flow_calibration`이 나오면 숫자 튜닝보다 먼저 결과 화면 질문 순서와 Agent 입력 계약을 확인합니다. OpenAI 프레임 분석을 끈 상태에서 표시 계약만 확인하려면 로컬 검증 manifest에서 `require_frame_observations`를 끄고 배치를 실행할 수 있지만, 이 검증용 manifest와 결과는 반드시 `logs/` 아래에 두어 Git에 포함하지 않습니다.

정확도 고도화 12단계처럼 전체 평가 흐름을 마감 점검할 때는 같은 batch 결과로 근거 정합성, 캘리브레이션, 미해소 gate를 함께 확인합니다. 아래 명령은 OpenAI를 새로 호출하지 않고 기존 batch 결과와 reference 평가 JSON만 사용합니다.

```bash
python scripts/reference_evidence_alignment_eval.py \
  --reference-eval logs/video_accuracy/stage10_eval_fixture/reference_guidance_eval_stage11_resolved_3_5.json \
  --batch-output logs/video_accuracy/stage11_guidance_capture/aggregate.json \
  --output logs/video_accuracy/reference_evidence_alignment_stage12_final.json

python scripts/reference_guidance_calibration_eval.py \
  --manifest logs/video_accuracy/lawyer_reference_manifest.json \
  --batch-output logs/video_accuracy/stage11_guidance_capture/aggregate.json \
  --reference-eval logs/video_accuracy/stage10_eval_fixture/reference_guidance_eval_stage11_resolved_3_5.json \
  --output logs/video_accuracy/reference_guidance_calibration_eval_stage12_final.json

python scripts/reference_guidance_calibration_eval.py \
  --manifest logs/video_accuracy/lawyer_reference_manifest.json \
  --batch-output logs/video_accuracy/stage11_guidance_capture/aggregate.json \
  --reference-eval logs/video_accuracy/reference_guidance_eval_stage10_check.json \
  --output logs/video_accuracy/reference_guidance_calibration_eval_stage12_gate_check.json
```

기대 결과는 근거 정합성 5개 통과, 충돌 해소 샘플 2개, 캘리브레이션 5개 통과입니다. 마지막 gate check에서는 충돌이 해소되지 않은 사고 3·5가 `blocked_by_reference_gate`로 남아야 합니다. 이 결과가 바뀌면 숫자 보정보다 먼저 충돌 보완 질문, `/reanalyze` 영상 메타데이터 유지, reference readiness 평가를 확인합니다.

새 환경에서 `logs/` 산출물이 없을 때는 tracked synthetic fixture로 최소 평가 흐름을 먼저 확인합니다. 이 fixture는 실제 영상 경로, 사용자 정보, 실제 변호사 의견 원문을 포함하지 않으며, ready 샘플 1개와 reference gate에 막히는 충돌 샘플 1개만 담고 있습니다.

가장 간단한 확인 방법은 아래 smoke 스크립트입니다. 이 스크립트는 미해소 충돌 fixture와 충돌 해소 fixture를 모두 실행하고, guidance/evidence/calibration gate의 기대 카운트가 맞지 않으면 실패합니다. 출력 JSON은 `logs/video_accuracy/reference_hardening_fixture_smoke/` 아래에 저장되며 Git에는 포함되지 않습니다.

```bash
python scripts/verify_reference_hardening_fixture.py
```

```bash
python scripts/reference_guidance_eval.py \
  --manifest tests/fixtures/video_accuracy/reference_hardening_minimal/manifest.json \
  --batch-output tests/fixtures/video_accuracy/reference_hardening_minimal/batch_aggregate.json \
  --output logs/video_accuracy/reference_hardening_minimal_guidance_eval.json

python scripts/reference_evidence_alignment_eval.py \
  --reference-eval logs/video_accuracy/reference_hardening_minimal_guidance_eval.json \
  --batch-output tests/fixtures/video_accuracy/reference_hardening_minimal/batch_aggregate.json \
  --output logs/video_accuracy/reference_hardening_minimal_evidence_alignment.json

python scripts/reference_guidance_calibration_eval.py \
  --manifest tests/fixtures/video_accuracy/reference_hardening_minimal/manifest.json \
  --batch-output tests/fixtures/video_accuracy/reference_hardening_minimal/batch_aggregate.json \
  --reference-eval logs/video_accuracy/reference_hardening_minimal_guidance_eval.json \
  --output logs/video_accuracy/reference_hardening_minimal_calibration_eval.json
```

기대 결과는 guidance readiness가 `ready_for_legal_knia_insurance_evidence_eval` 1개와 `needs_conflict_resolution_before_guidance` 1개, evidence alignment가 ready 1개, calibration이 `calibrated_for_user_flow` 1개와 `blocked_by_reference_gate` 1개입니다. 이 fixture는 실제 정확도 측정이 아니라 평가 스크립트와 gate 계약의 최소 재현성 확인용입니다.

충돌 보완 답변 이후의 승격 흐름은 같은 fixture의 `batch_aggregate_conflict_resolved.json`으로 확인합니다. 이 파일은 실제 E2E 결과가 아니라 `conflict_followup.latest_conflict_count=0` 상태를 재현하는 synthetic aggregate입니다. 기대 결과는 guidance ready 2개, resolved conflict sample 1개, evidence alignment ready 2개, calibration 통과 2개입니다.

```bash
python scripts/reference_guidance_eval.py \
  --manifest tests/fixtures/video_accuracy/reference_hardening_minimal/manifest.json \
  --batch-output tests/fixtures/video_accuracy/reference_hardening_minimal/batch_aggregate_conflict_resolved.json \
  --output logs/video_accuracy/reference_hardening_minimal_guidance_eval_resolved.json

python scripts/reference_evidence_alignment_eval.py \
  --reference-eval logs/video_accuracy/reference_hardening_minimal_guidance_eval_resolved.json \
  --batch-output tests/fixtures/video_accuracy/reference_hardening_minimal/batch_aggregate_conflict_resolved.json \
  --output logs/video_accuracy/reference_hardening_minimal_evidence_alignment_resolved.json

python scripts/reference_guidance_calibration_eval.py \
  --manifest tests/fixtures/video_accuracy/reference_hardening_minimal/manifest.json \
  --batch-output tests/fixtures/video_accuracy/reference_hardening_minimal/batch_aggregate_conflict_resolved.json \
  --reference-eval logs/video_accuracy/reference_hardening_minimal_guidance_eval_resolved.json \
  --output logs/video_accuracy/reference_hardening_minimal_calibration_eval_resolved.json
```

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
