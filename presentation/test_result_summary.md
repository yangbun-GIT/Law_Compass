# LawCompass 실행 결과 요약

생성일: 2026-05-30

## 확인 범위

- 실제 저장소 문서와 코드 기준으로 아키텍처를 확인했습니다.
- `storage/test.mp4` 파일은 존재합니다.
- Docker 데몬이 실행 중이 아니어서 `test.mp4` 기반 전체 컨테이너 E2E는 이번 세션에서 실행하지 못했습니다.
- 대신 Agent의 로컬 샘플 시나리오 4개와 회귀 시나리오 6개를 실행해 결과를 정리했습니다.

## Docker E2E 상태

`docker compose --env-file .env ps` 실행 시 Docker Desktop Linux engine 파이프가 없어 연결에 실패했습니다. 따라서 `scripts/video_agent_e2e.py`가 요구하는 `http://localhost` 전체 스택이 준비되지 않았고, 실제 영상 업로드부터 결과 조회까지의 E2E는 보류되었습니다.

재현 및 실행 순서:

```powershell
docker compose --env-file .env up -d --build --force-recreate
python scripts/video_agent_e2e.py
```

## 실행된 시나리오 결과

### 샘플 시나리오

| 시나리오 | 판정 유형 | 과실비율 | KNIA 기준 | 결과 요약 |
|---|---:|---:|---|---|
| 교차로 신호위반 | intersection_signal_violation | 내 0 / 상대 100 | 직접 매칭 없음 | 신호 사실 확인에 따라 조건부 결과를 제시합니다. |
| 차로변경 사고 | lane_change_collision | 내 20 / 상대 80 | 차43-2 | 상대 차로변경과 방향지시등 미사용이 반영됩니다. |
| 후미추돌 | rear_end_collision | 내 0 / 상대 100 | 차41-1 | 사용자를 앞차로 매핑해 후방 추돌 기준을 적용합니다. |
| 어린이보호구역 보행자 사고 | pedestrian_accident | 내 70 / 상대 30 | 보21 | 보행자 사고 기준과 법규 근거를 함께 수집합니다. |

### 회귀 시나리오

| 시나리오 | 판정 유형 | 과실비율 | 역할 | KNIA 기준 | 근거 커버리지 |
|---|---:|---:|---|---|---|
| rear_end_victim | rear_end_collision | 0:100 | front_vehicle | 차41-1 | high |
| video_rear_end_overrides_conflicting_user_fact | rear_end_collision | 0:100 | front_vehicle | 차41-1 | high |
| opponent_lane_change | lane_change_collision | 30:70 | straight_vehicle | 차43-2 | medium |
| user_lane_change | lane_change_collision | 70:30 | lane_changing_vehicle | 차43-2 | medium |
| opponent_signal_violation | intersection_signal_violation | 0:100 | signal_compliant_vehicle | 없음 | medium |
| user_bicycle_collision | bicycle_collision | 60:40 | bicycle | 거9-1 | medium |

## 현재 결론

LawCompass는 단일 프론트엔드 앱이 아니라, Vue 프론트엔드, Fastify Gateway, FastAPI Agent, Redis Stream Worker, PostgreSQL pgvector, Redis를 묶은 MSA 형태입니다. Agent는 영상 및 입력 사실을 사고 유형으로 정리하고, KNIA 기준과 법률 근거를 검색한 뒤 사용자 친화 리포트로 변환합니다.

이번 세션에서 실제 컨테이너 E2E는 Docker 미실행으로 막혔지만, 샘플 및 회귀 시나리오 기준으로 후미추돌, 차로변경, 신호위반, 보행자, 자전거 충돌까지 핵심 사고군의 결과 생성 경로가 확인되었습니다.

## 보안 및 표시 정책

- 실제 `.env`, API key, NAS 비밀번호, JWT secret, refresh token은 출력하지 않았습니다.
- 원본 payload 또는 raw trace 대신 발표용으로 정리한 요약만 포함했습니다.
- 표준 MCP를 적용한 시스템이라고 표현하지 않았습니다. 현재 구조는 내부 API, Redis Stream, Worker, Agent orchestration 중심으로 설명했습니다.
