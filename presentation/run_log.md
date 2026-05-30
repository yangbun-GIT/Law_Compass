# LawCompass 발표 자료 생성 로그

생성일: 2026-05-30

## 1. 사전 문서 확인

확인한 파일:

- `AGENTS.md`
- `DEVELOPMENT_PROMPT.md`
- `SYSTEM_OVERVIEW.md`
- `docs/GITHUB_COLLABORATION_WORKFLOW.md`
- `README.md`
- `compose.yaml`
- `scripts/video_agent_e2e.py`
- `apps/agent/scripts/run_sample_scenarios.py`
- `apps/agent/scripts/test_agent_regression_scenarios.py`

## 2. Git 상태 확인

확인 결과:

- 현재 브랜치: `main`
- 원격 추적: `origin/main`
- 기존 로컬 수정: `project_overview.md`

주의:

- `project_overview.md`는 이번 작업에서 생성한 파일이 아니므로 수정하거나 스테이징하지 않습니다.

## 3. test.mp4 확인

확인 결과:

- 경로: `storage/test.mp4`
- 존재 여부: 존재
- 크기: 5,451,338 bytes
- 마지막 수정 시각: 2026-05-28 18:43:56

## 4. Docker 상태 확인

실행 명령:

```powershell
docker compose --env-file .env ps
```

결과:

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
The system cannot find the file specified.
```

해석:

- Docker Desktop Linux engine이 실행 중이 아니었습니다.
- 전체 Docker 스택이 필요하므로 `storage/test.mp4` 업로드부터 분석 결과 조회까지의 E2E는 이번 세션에서 실행할 수 없었습니다.

## 5. Agent 샘플 시나리오 실행

실행 명령:

```powershell
cd apps/agent
$env:PYTHONPATH='.'
python scripts/run_sample_scenarios.py
```

확인된 주요 결과:

- 교차로 신호위반: 내 0%, 상대 100%, 조건부 결과 포함
- 차로변경 사고: 내 20%, 상대 80%, KNIA 차43-2, 방향지시등 미사용 조정
- 후미추돌: 내 0%, 상대 100%, KNIA 차41-1
- 어린이보호구역 보행자 사고: 내 70%, 상대 30%, 보행자 기준과 법규 근거 포함

## 6. Agent 회귀 시나리오 실행

실행 명령:

```powershell
cd apps/agent
$env:PYTHONPATH='.'
$env:PYTHONIOENCODING='utf-8'
python scripts/test_agent_regression_scenarios.py
```

결과:

```text
PASS rear_end_victim scenario=rear_end_collision fault=0:100 role=front_vehicle knia=차41-1 judgment=evidence_supported evidence_coverage=high
PASS video_rear_end_overrides_conflicting_user_fact scenario=rear_end_collision fault=0:100 role=front_vehicle knia=차41-1 judgment=needs_review evidence_coverage=high
PASS opponent_lane_change scenario=lane_change_collision fault=30:70 role=straight_vehicle knia=차43-2 judgment=needs_review evidence_coverage=medium
PASS user_lane_change scenario=lane_change_collision fault=70:30 role=lane_changing_vehicle knia=차43-2 judgment=needs_review evidence_coverage=medium
PASS opponent_signal_violation scenario=intersection_signal_violation fault=0:100 role=signal_compliant_vehicle knia=None judgment=needs_review evidence_coverage=medium
PASS user_bicycle_collision scenario=bicycle_collision fault=60:40 role=bicycle knia=거9-1 judgment=needs_review evidence_coverage=medium
```

## 7. 다음에 실행할 전체 E2E

Docker Desktop을 시작한 뒤 아래 순서로 실행합니다.

```powershell
docker compose --env-file .env up -d --build --force-recreate
python scripts/video_agent_e2e.py
```

성공 시 확인할 항목:

- 로그인 및 케이스 생성
- `storage/test.mp4` 업로드
- Worker 분석 완료
- Easy report 반환
- top conclusion
- fault ratio
- KNIA 기준 카드
- related video card
- action items

## 8. 민감정보 처리

이번 발표 산출물에는 아래 정보를 포함하지 않았습니다.

- `.env` 실제값
- API key
- NAS 비밀번호
- JWT secret
- refresh token
- 사용자 개인정보
- 원본 raw payload
