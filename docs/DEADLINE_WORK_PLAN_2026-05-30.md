# 2026-05-30 데드라인 작업 순서

이 문서는 다음날 새벽 데드라인 전까지 작업 범위가 흔들리지 않도록 고정하는 임시 실행 계획이다. 작업 중 더 먼저 처리해야 하는 문제가 발견되면 해당 P 단계의 올바른 위치에 추가하고, 현재 단계 밖의 작업으로 임의 이동하지 않는다.

## P0: 실행 흐름 차단 해소

### P0-1. 관리자 테스트 흐름 문제 해결

- 상태: 완료
- 목표: 관리자 테스트 페이지에서 영상 전처리 결과를 확인한 뒤 `Agent 분석 계속 실행`을 눌러 사고 상황 정리와 과실비율 산정까지 이어갈 수 있게 한다.
- 현재 원인: 영상 전처리 직후 `/easy-report`를 먼저 읽어 placeholder report가 생기고, 이 값 때문에 `Agent 분석 계속 실행` 버튼 조건이 막힌다.
- 작업 범위:
  - 영상 전처리만 완료된 상태에서는 결과 리포트를 불러오지 않는다.
  - `video_analyze`가 완료된 뒤에만 easy report를 불러온다.
  - 수동 새로고침을 눌러도 Agent 분석 전 버튼이 사라지지 않게 한다.
- 완료 내용:
  - `hasCompletedVideoAnalysis` 기준을 추가해 `video_analyze` 성공 전에는 계속 실행 버튼을 유지한다.
  - `refreshOutputs()`는 영상 모드에서 `video_analyze` 성공 전까지 `/easy-report`를 읽지 않는다.
  - `video_analyze` 성공 상태 판정은 `succeeded`, `completed`, `success`, `done`, `finished`를 허용한다.
- 검증:
  - 완료: Frontend build
  - 완료: Gateway build
  - 완료: `git diff --check`

### P0-2. 영상+입력 Agent E2E 확인

- 상태: 완료
- 목표: 관리자 페이지에서 영상+입력으로 `video_preprocess -> video_analyze -> easy-report`가 끝까지 이어지는지 확인한다.
- 최소 샘플: 사고 1~3 중 1개 이상, 가능하면 사고 2 포함.
- 완료 내용:
  - 사고 1 입력+영상 E2E에서 중앙선 장애물 회피/대향 차량 충돌 구조가 `centerline_obstacle_collision`으로 유지되는지 확인했다.
  - 사고 1 저장 결과에서 영상 관찰값 `centerline_crossed`, `opposing_vehicle_present`, `collision_point_visible`, `pedestrian_visible=false`가 Agent 입력 계약과 저장 결과에 반영되는지 확인했다.
  - 사고 2 입력+영상 E2E에서 좌회전 황색-적색 전환, 상대 신호 미확인 조건부 결과, 차대차 사고 대상 유지, 보행자 오염 방지가 동작하는지 확인했다.
  - 사고 2 기준 근거 카드에 보행자/후방추돌 계열 근거가 일부 섞이는 문제는 P1 근거 적합도 보강 대상으로 남긴다.
- 검증:
  - 완료: Agent 중앙선/영상 입력 계약 단위 테스트
  - 완료: Agent regression scenario script
  - 완료: Docker `agent`, `worker`, `gateway` rebuild
  - 완료: 사고 1 `scripts/video_agent_e2e.py`
  - 완료: 사고 2 `scripts/video_agent_e2e.py`

## P1: 결과 품질 보강

### P1-1. 사고 대상 오염/조건부 결과 보강

- 상태: 완료
- 목표: 차대차 사고에서 보행자·횡단보도·후방추돌·자전거 근거가 사고 대상처럼 섞이지 않게 하고, 신호 불명확 사고는 조건별 결과를 중복 없이 표시한다.
- 완료 내용:
  - Agent evidence 단계에서 차대차 직접 충돌 맥락과 보행자/후방추돌/자전거 target 근거를 분리하는 `_filter_target_context_mismatch`를 추가했다.
  - `fault_ratio`가 이미 사고별 조건부 결과를 만든 경우 KNIA 조정 registry의 일반 조건부 결과가 중복으로 붙지 않도록 병합 규칙을 보강했다.
  - 전문가 안내 basis 생성 시 `excluded_knia_party_types`, video contract 같은 메타 필드가 실제 사고 사실처럼 컨텍스트에 들어가 근거 문구를 오염시키지 않도록 제외했다.
  - 사고 2 E2E에서 조건부 결과는 2개로 유지되고, basis는 `신호 전환과 CCTV 확인 기준`, `도로교통법 신호 준수 의무`만 남는 것을 확인했다.
- 검증:
  - 완료: P1-1 Agent 단위 테스트 3건
  - 완료: Agent regression scenario script
  - 완료: Docker `agent`, `worker`, `gateway` rebuild
  - 완료: 사고 2 `scripts/video_agent_e2e.py`
  - 로그: `logs/video_accuracy/p1_1_accident2_target_schema_e2e_20260530_r2.json` (`logs/`는 Git에 포함하지 않음)

### P1-2. 과실비율/KNIA 근거 싱크 점검

- 상태: 대기
- 목표: 사고 대분류와 다른 KNIA/법률 근거가 표시되지 않게 확인한다.

## P2: 제출 전 점검

### P2-1. 사용자 화면 문구와 기술 문자열 정리

- 상태: 대기
- 목표: 영어, raw key, 내부 진단 문구가 일반 사용자 화면에 노출되지 않게 확인한다.

### P2-2. Docker 실행과 시연 경로 확인

- 상태: 대기
- 목표: `http://localhost`, `http://localhost/admin/agent-test`가 정상 동작하는지 확인한다.
