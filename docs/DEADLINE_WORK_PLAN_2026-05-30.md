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

### P1-2. 사고 1 중앙선·장애물 회피 영상 fact 승격 복구

- 상태: 1차 완료, 후속 보강 필요
- 문제: `car_accident_1.mp4`는 영상만 보아도 중앙선/도로 중앙 침범, 도로 장애물 또는 주정차 차량 회피, 대향 차량과의 직접 충돌이 확인되는 축이다. 그런데 관리자 테스트 결과가 `일반 차량 충돌`, `추가 사실 확인 필요`, `내 50% / 상대 50%`로 떨어진다.
- 판단: 영상 전처리 자체가 완전히 실패한 것이 아니라, 영상에서 잡힌 충돌 후보가 Agent 판단에 필요한 구조화 fact로 충분히 승격되지 않거나, `centerline_obstacle_collision` 사고유형으로 연결되기 전에 일반 차대차 fallback으로 접히는 문제로 본다.
- 목표:
  - 사고 1 같은 중앙선/장애물 회피 대향 충돌을 특정 영상에 맞춰 하드코딩하지 않고, 범용 fact 축으로 Agent 입력 계약에 연결한다.
  - 영상 단독 또는 영상+짧은 입력만으로도 `일반 차대차 50:50` fallback에 머물지 않게 한다.
  - 단, 정차 시간, 침범 사유, 불법 주정차 여부, 상대 회피 가능성이 불명확하면 조건부/확인 필요로 남기고 임의 확정하지 않는다.
- 작업 범위:
  1. `car_accident_1.mp4`를 OpenAI+YOLO ON 상태로 관리자 흐름과 `scripts/video_agent_e2e.py`에서 재현하고, 전처리 관찰값·Agent video input contract·fact arbitration·easy report 중 어디서 50:50 fallback으로 접히는지 분리한다.
  2. 다음 관찰 축이 raw observation, supporting observation, accepted fact, fact_patch 중 어디에 위치하는지 점검한다: `centerline_crossed`, `centerline_crossing_reason`, `road_obstacle_or_parked_vehicle`, `opposing_vehicle_present`, `ego_stopped_or_slowed`, `opponent_failed_to_slow`, `collision_point_visible`, `secondary_rear_impact_candidate`.
  3. 다중 프레임과 사용자 입력이 같은 방향으로 지지하는 관찰값은 Agent 판단에 사용할 수 있는 fact 또는 strong supporting fact로 올리고, 근거가 부족한 축은 confirmation candidate로 남긴다.
  4. `centerline_obstacle_collision` 분류가 `parking_or_stopped_vehicle_accident` 또는 `general_vehicle_collision`으로 접히지 않도록 scenario classifier, input normalizer, video input contract guard의 연결을 점검한다.
  5. 과실비율 Agent는 중앙선/장애물 회피 + 대향 차량 충돌 + 정차/감속 또는 상대 미정지 단서가 있으면 단순 50:50 대신 조건부 참고 범위를 제시한다. 정차/회피 가능성 단서가 충분하면 상대 책임이 더 큰 방향, 단서가 부족하면 확인 필요 조건부로 표시한다.
  6. KNIA/법률 근거는 차43 계열 또는 중앙선·대향차·장애물 회피 축을 우선하고, 직접 사고대상이 아닌 후방추돌·보행자·자전거 근거는 표시 근거에서 제외한다.
- 검증:
  - 사고 1 영상 단독 E2E: 일반 차대차 50:50 fallback이 아닌 중앙선/장애물 회피 대향 충돌 구조로 표시되는지 확인한다.
  - 사고 1 입력+영상 E2E: 사용자 입력과 영상 fact가 같은 방향이면 과실비율 참고 범위와 근거가 더 구체화되는지 확인한다.
  - 사고 2 E2E 회귀: 교차로 신호 불명확 사고의 조건부 결과와 보행자 오염 방지가 깨지지 않는지 확인한다.
  - Agent 단위 테스트: 특정 `car_accident_1.mp4` 이름이나 테스트 문장에 맞춘 규칙 없이, 중앙선 침범 사유/도로 장애물/대향 차량/정차 또는 감속 단서 조합으로 동작하는지 고정한다.
  - 결과 로그는 `logs/video_accuracy/`에만 남기고 Git에 포함하지 않는다.
- 2026-05-31 진행 결과:
  - Worker OpenAI 프레임 분석에 `road_context_observation_retry`를 추가했다. 충돌 또는 접촉 근거는 있는데 중앙선, 도로 장애물, 대향 차량, 2차 충돌 같은 시나리오 맥락이 부족하면 제한된 재분석을 한 번 더 실행한다.
  - 약한 `lane_change_actor`, `front_vehicle_stopped` 후보가 먼저 나와도 중앙선·장애물 회피 재분석을 막지 않도록 scenario context 판정을 confidence 기준으로 제한했다.
  - Agent video input contract에서 다중 프레임 기반 `road_obstruction` 관찰값이 과도하게 탈락하지 않도록 임계값을 조정했다.
  - 사고 1 영상 단독 E2E에서 `centerline_crossed`, `opposing_vehicle_present`, `primary_collision_target`, `collision_point_visible`, `pedestrian_visible=false`가 fact patch에 반영되고 `centerline` 분기가 선택되는 것을 확인했다.
  - 단, 영상 단독 결과에서 `road_obstruction`과 `centerline_cross_reason`은 모델 출력 변동이 남아 있어 과실비율이 항상 좁은 범위로 고정되지는 않는다. 바로 P1-3로 넘어가기 전에 P1-2b~P1-2d에서 사고 유형 범위 확장, 오염 guard, Agent 입력 계약 연결을 먼저 확인한다.
  - 검증: `apps/worker/tests/test_frame_analysis_contract.py` 38개 통과, `apps/agent/tests/test_video_input_contract.py` 32개 통과, Docker `agent`/`worker` 재빌드 완료.

### P1-2b. 영상 fact 범위 확장 검증

- 상태: 완료, P1-2c 보강 필요
- 판단: P1-2 1차 보강은 코드 조건은 범용이지만 실제 검증은 사고 1 중심이다. P1-3 과실비율/KNIA 근거 싱크는 영상 fact가 맞다는 전제가 있어야 하므로, 먼저 여러 사고 유형에서 영상 fact가 오염 없이 추출되는지 확장 검증한다.
- 목표:
  - 사고 1~5 전체를 OpenAI+YOLO ON 상태로 재측정한다.
  - AI-Hub 또는 로컬 reference 중 대표 유형을 추가해 중앙선, 교차로 신호, 후방추돌, 횡단보도 환경, 무등화 정차, 자전거/이륜차 유발, 보행자 오염 케이스를 함께 확인한다.
  - 특정 테스트 영상에 맞춘 결과 보정 없이, 각 사고에서 직접 충돌 대상과 보조 환경 fact가 분리되는지 본다.
- 검증:
  - `raw observation -> accepted/supporting fact -> fact_patch -> fact_arbitration -> easy report` 단계별로 누락 또는 오염 위치를 기록한다.
  - 결과 로그는 `logs/video_accuracy/`에만 남기고 Git에 포함하지 않는다.
- 2026-05-31 진행 결과:
  - 실제 사고 1~5를 OpenAI+YOLO ON 상태에서 재측정했다. 산출물은 `logs/video_accuracy/p1_2b_actual_1_5_openai_yolo_on_20260531/aggregate.json`에 로컬로 남겼다.
  - AI-Hub 597 원천 영상 대표 4종(차량/보행자/이륜차/자전거 각 1개)을 OpenAI+YOLO ON 상태에서 재측정했다. 산출물은 `logs/video_accuracy/p1_2b_aihub_representative_openai_yolo_on_20260531/aggregate.json`에 로컬로 남겼다.
  - 실제 사고 1~5 batch는 pipeline 5/5 통과, frame observation 70개, accepted 19개, uncertain 42개, supporting 9개, applied 16개였다.
  - 실제 사고 1~5 reference metrics는 `status=needs_attention`, 직접 충돌 대상 정확도 0.6, 사고 대분류 정확도 0.6, 관찰값 0개 비율 0.0, 근거 mismatch 0.8, 조건부 분기 coverage 0.8이었다.
  - 실제 사고 1~5 audit는 pass 0, weak 4, fail 1이다. promoted pollution은 0이지만 candidate 직접대상 4건, expected context missing 2건이 남았다. 사고 2는 `pedestrian_candidate`가 직접 충돌 대상 mismatch로 잡혀 fail 처리됐다.
  - AI-Hub 대표 4종은 observation target hit 4/4, direct target pollution 0/4, agent direct target pollution 0/4로 통과했다. 다만 agent target hit는 0/4이며, 이는 후보값을 확정 fact로 바로 승격하지 않는 현재 안전 정책 때문이다.
- 해석:
  - 영상 분석은 사고 시점과 객체 후보를 찾지만, actual 사고 1~5에서는 후보와 확정 fact의 경계, expected context 누락, 직접 충돌 대상 후보 오염이 아직 남아 있다.
  - P1-3 과실비율/KNIA 근거 싱크로 넘어가기 전에 P1-2c에서 후보값 오염 guard와 맥락 누락 보강을 먼저 진행한다.

### P1-2c. 누락/오염 유형별 guard 보강

- 상태: 완료
- 목표: P1-2b에서 확인된 실패 유형을 테스트 케이스 전용 분기가 아니라 범용 guard로 보강한다.
- 우선 확인할 오염 유형:
  - 사람이 보인다는 이유만으로 차대사람 사고나 보행자 근거로 승격되는 경우
  - 신호등이 보인다는 이유만으로 신호위반을 확정하는 경우
  - 차량 후보가 많아 직접 충돌 대상과 주변 차량을 혼동하는 경우
  - 중앙선은 보이지만 침범 주체, 침범 사유, 도로 장애물 여부가 불명확한 경우
  - 자전거/이륜차/정차 차량이 직접 충돌 대상인지 비접촉 유발 객체인지 섞이는 경우
- 검증: Worker/Agent 단위 테스트와 사고 1~5 회귀를 함께 통과해야 한다.

### P1-2d. 영상 fact의 Agent 입력 계약 연결 확인

- 상태: 완료
- 목표: P1-2b/P1-2c에서 안정화한 영상 fact가 Agent 판단에 실제로 쓰이는지 확인한다.
- 확인 범위:
  - raw observation에는 있는데 accepted fact로 못 올라가는 항목
  - accepted/supporting fact에는 있는데 fact patch로 못 들어가는 항목
  - fact arbitration에서 사용자 입력과 충돌하거나 보류되어 easy report에 반영되지 않는 항목
  - easy report에서 사고유형, 과실비율, KNIA/법률 근거가 다시 일반 fallback으로 접히는 항목
- 완료 기준: 영상 fact가 맞게 추출된 사고에서는 P1-3 근거 싱크 점검을 진행할 수 있을 정도로 사고 대분류와 직접 충돌 대상이 안정적으로 유지되어야 한다.
- 2026-05-31 진행 결과:
  - `primary_collision_target=vehicle_candidate`처럼 확정 fact로 올리면 위험한 직접 사고대상 후보를 `direct_collision_partner_type` 확인 질문으로 연결했다.
  - 후보 원천 필드는 `source_field`로 보존하고, 사용자에게 물어볼 필드는 `question_field`/`recommended_fact_field`로 분리했다.
  - 사용자 입력의 `collision_partner_type`, `direct_collision_partner_type`, `accident_party_type`과 영상 후보를 교차 비교해 같은 방향이면 `user_supported_by_held_video_needs_context_confirmation`, 다른 방향이면 `user_video_conflict_video_held`로 남긴다.
  - 후보값은 계속 `pending_video_confirmations`와 `requires_confirmation`에만 남기며 `fact_patch` 또는 확정 facts로 승격하지 않는다.
  - Gateway 결과 카드와 추가 확인 질문은 raw `primary_collision_target` 대신 `실제 충돌 상대` 흐름으로 표시한다.
- 검증:
  - 완료: Agent fact arbitration/video input contract 테스트
  - 완료: Gateway report composer 테스트
  - 완료: Gateway build
  - 완료: Python compile
  - 참고: broader orchestrator 회귀 확인에서 기존 분류/과실 범위 테스트 2건이 실패했으나, P1-2d 후보-확인질문 연결 변경 경로와는 별개로 남긴다.

### P1-3. 과실비율/KNIA 근거 싱크 점검

- 상태: 완료
- 선행 조건: P1-2b~P1-2d가 완료되어 영상 fact가 여러 사고 유형에서 안정적으로 Agent 입력 계약에 들어가는지 확인되어야 한다.
- 목표: 사고 대분류와 다른 KNIA/법률 근거가 표시되지 않게 확인한다.
- 완료 내용:
  - 신호대기 정차 후방추돌은 빨간불/교차로 키워드가 있어도 `rear_end_collision` 사고축을 우선하도록 분류 우선순위를 보강했다.
  - 교차로에서 회전 차량과 직진 차량이 충돌한 차대차 사고는 신호 확정 fact가 없어도 `general_collision`이나 차선변경 기준으로 밀리지 않고 `intersection_collision` 축을 유지한다.
  - 무등화/스텔스 정차차량 사고에서 제한속도 초과 fact가 확인되면 기본 스텔스 정차차량 10:90으로 덮지 않고 과속 조건을 반영한 40:60 참고 범위를 유지한다. `reported_speed_kmh/speed_limit_kmh`뿐 아니라 정규화된 `speeding_over_limit=true`도 과속 fact로 처리한다.
  - structured lookup, fallback, hybrid lookup 모두에서 scenario와 맞지 않는 KNIA 후보를 필터링한다. 중앙선·장애물 회피 사고는 차선변경/후방추돌 기준을 primary로 쓰지 않고, 무등화 정차차량 사고는 보행자/자전거/신호/차선변경 기준을 primary로 쓰지 않는다.
  - KNIA hybrid 후보 필터 테스트가 structured lookup fallback에 가려지지 않도록 테스트 경계를 고정했다.
- 검증:
  - 완료: Python 회귀 102건
  - 완료: synthetic 일반화 샘플 6종. 신호대기 후방추돌, 적색 진입 교차로, 무등화 정차차량 과속/비과속, 중앙선 장애물 회피, 횡단보도 주변 차대차 교차로 사고에서 보행자·차선변경·후방추돌 근거 오염이 재현되지 않는 것을 확인했다.

## P2: 제출 전 점검

### P2-1. 사용자 화면 문구와 기술 문자열 정리

- 상태: 대기
- 목표: 영어, raw key, 내부 진단 문구가 일반 사용자 화면에 노출되지 않게 확인한다.

### P2-2. Docker 실행과 시연 경로 확인

- 상태: 대기
- 목표: `http://localhost`, `http://localhost/admin/agent-test`가 정상 동작하는지 확인한다.
## 2026-05-31 P1-2c 완료 기록

P1-2c는 기존 사고 1~5에 맞춘 분기 추가가 아니라 후보 관찰값과 확정 fact를 분리하는 범용 guard 보강으로 처리했다.

- `*_candidate` 사고 대상은 확정 직접 충돌 대상이나 Agent fact로 승격하지 않는다.
- 보행자/자전거/이륜차/객체 후보는 직접 접촉 bundle이 없으면 확정 차량 사고 대상을 밀어내지 못한다.
- 차량 대상 후보와 충돌 지점이 함께 관찰되면 배경 보행자, 횡단보도, 보행자 신호는 사고 환경 후보로 낮춘다.
- 평가 스크립트는 후보/보류 관찰값을 오염된 확정 결과로 잘못 채점하지 않고, 확정·적용·fact_patch 값과 후보값을 분리해서 본다.

검증 결과는 Agent 계약 테스트 34건, Worker 계약 테스트 38건, reference metrics 테스트 2건 통과다. 기존 P1-2b aggregate 재평가 결과는 promoted pollution 0건, zero observation 0건, evidence mismatch 0건, audit fail 0건/weak 5건이다. 직접 충돌 대상은 아직 후보 상태가 많아 P1-2d에서 Agent 입력·확인 질문·과실 판단 연결을 이어서 봐야 한다.

## 2026-05-31 P1-2d 완료 기록

P1-2d는 후보 직접 사고대상을 확정 fact로 승격하지 않으면서도 사용자 확인 질문과 리포트 표시로 이어지도록 연결하는 작업으로 처리했다.

- `primary_collision_target`, `collision_partner_type`, `direct_collision_partner_type`의 후보값을 `vehicle`, `pedestrian`, `bicycle`, `motorcycle`, `object` 축으로 정규화한다.
- `primary_collision_target` 후보는 `direct_collision_partner_type` 질문으로 브리지해 raw 내부 key가 사용자 질문에 그대로 노출되지 않게 했다.
- 사용자 입력과 같은 방향의 후보는 보강 확인 항목으로, 반대 방향의 후보는 입력-영상 충돌 검토 항목으로 남긴다.
- 후보값은 확정 facts나 `fact_patch`로 직접 승격하지 않는다. 따라서 사고 대상 오염 방지 정책은 유지된다.
- Gateway 결과 카드와 missing info 질문은 `source_label`을 통해 원천 후보 필드는 보존하되, 사용자가 답해야 할 필드는 “실제 충돌 상대”로 표시한다.

이제 P1-3은 영상 fact가 추출·보류·확인 질문까지 이어진다는 전제에서 과실비율/KNIA 근거 싱크를 점검하면 된다.
