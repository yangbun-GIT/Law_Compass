# 영상·입력 사고 오염 위험 매트릭스

이 문서는 `docs/VIDEO_AGENT_WORK_PLAN.md`의 P0-1 산출물이다. 목적은 사고 영상과 사용자 입력에서 특정 객체나 배경 정보가 보인다는 이유만으로 사고 유형이 잘못 승격되는 문제를 일반화해 고정하는 것이다.

이 문서는 특정 샘플 사고 1~5에 맞춘 정답표가 아니다. 이후 영상 분석, `video_input_contract`, `fact_arbitration`, `scenario_classifier`, KNIA/법령 근거 검색, 프론트 보완 질문을 보강할 때 참조해야 하는 범용 오염 방지 기준이다.

## 공통 판단 축

| 축 | 의미 | 확정 조건 |
| --- | --- | --- |
| `observed_object` | 영상이나 입력에 등장한 객체 | 단순 존재만으로 사고 대상이 되지 않는다. |
| `direct_collision_partner_type` | 실제 접촉 또는 충돌 대상 | 충돌 순간, 손상 위치, 접촉 경로, 사용자 명시 입력 중 하나 이상의 고신뢰 근거가 필요하다. |
| `collision_partner_type` | 넓은 사고 상대 분류 | 직접 충돌 대상이 명확하면 이를 우선하고, 불명확하면 확인 후보로 남긴다. |
| `trigger_actor_type` | 비접촉 유발 또는 회피 원인 | 직접 충돌 대상과 분리한다. 예: 자전거 때문에 정지했지만 뒤차가 추돌. |
| `road_context` | 도로 환경 | 횡단보도, 신호등, 중앙선, 고속도로, 주정차 차량, 장애물 등은 기본적으로 보조 맥락이다. |
| `legal_issue_context` | 법적 쟁점 후보 | 신호, 중앙선, 안전거리, 회피 가능성, 과속, 등화 여부처럼 법적 판단에 영향을 주는 쟁점이다. |
| `confirmation_required` | 결론을 바꿀 수 있는 미확인 요소 | 영상에서 안 보이거나 confidence가 낮으면 사용자 질문 또는 reference-only 출력으로 남긴다. |

## 오염 위험 매트릭스

| ID | 오염 위험 | 잘못된 승격 | 올바른 분리 기준 | 우선 확인 질문 |
| --- | --- | --- | --- | --- |
| `pedestrian_context_pollution` | 횡단보도, 사람, 보행자 신호가 보임 | 차대사람 사고, 보행자 보호의무 중심 근거 | `direct_collision_partner_type=pedestrian` 근거가 없으면 `road_context=crosswalk_nearby`, `pedestrian_context`로만 보관 | 실제 충돌 대상이 보행자인가, 차량인가? |
| `bicycle_presence_pollution` | 자전거가 화면에 보이거나 입력에 등장 | 차대자전거 직접 충돌 | 접촉이 없으면 `trigger_actor_type=bicycle`, `non_contact_trigger=true`로 분리 | 자전거와 직접 부딪혔나, 자전거 때문에 멈추거나 피했나? |
| `traffic_signal_presence_pollution` | 신호등 또는 신호 단어가 있음 | 신호위반 사고 | 내 신호, 상대 신호, 진입 시점, 충돌 시점 신호를 분리한다. 상대 신호가 안 보이면 추정하지 않는다. | 내 신호와 상대 신호는 각각 무엇이었나? |
| `centerline_presence_pollution` | 중앙선, 황색 실선, 차로 경계가 보임 | 중앙선 침범 가해 확정 | 침범 주체, 침범 사유, 장애물 회피, 대향 차량 반응을 분리한다. | 누가 중앙선을 넘었고 왜 넘었나? |
| `parked_vehicle_presence_pollution` | 주차·정차 차량이 보임 | 주정차 사고 또는 정차 차량 충돌 확정 | 직접 충돌 대상인지, 도로 장애물인지, 시야 방해물인지, 비접촉 원인인지 분리한다. | 해당 차량과 직접 충돌했나, 회피 원인이었나? |
| `road_obstacle_presence_pollution` | 낙하물, 시설물, 장애물, 중앙분리대가 보임 | 차대기물 사고 확정 | 실제 충돌 대상인지, 상대 차량 회피 원인인지, 단순 배경인지 분리한다. | 내 차가 물체와 부딪혔나, 물체 때문에 다른 차량과 부딪혔나? |
| `front_rear_role_pollution` | 앞차, 뒤차, 정차, 추돌 단어가 있음 | 내 과실 후미추돌 또는 상대 100% 후방추돌로 단정 | `rear_end_role`, `collision_role`, `front_vehicle_stopped`, `rear_vehicle_collision`, `secondary_collision`을 분리한다. | 내 차가 앞차를 들이받았나, 뒤차가 내 차를 들이받았나? |
| `turn_or_curve_pollution` | 화면이 휘거나 차량이 곡선 주행 | 좌회전/우회전 사고 확정 | 교차로, 진출입로, 방향지시등, 실제 회전 궤적 근거가 없으면 `road_curve_context`로만 보관한다. | 실제 교차로 회전이었나, 단순 곡선 도로였나? |
| `lane_change_presence_pollution` | 차선, 옆차, 방향지시등 단어가 있음 | 진로변경 사고 확정 | 차로 변경 주체, 변경 시작 시점, 충돌 위치, 선후행 관계를 분리한다. | 어느 차량이 차로를 바꾸고 있었나? |
| `visibility_stealth_pollution` | 야간, 어두움, 등화 미점등 정황 | 스텔스 정차 차량 사고 확정 | 직접 충돌 대상이 정차 차량인지, 단순 야간 환경인지, 시야 보조 쟁점인지 분리한다. | 등화 없는 정차 차량과 직접 충돌했나? |
| `speed_or_highway_pollution` | 고속도로, 빠른 속도, 제한속도 언급 | 과속 가해 확정 | 측정 가능한 속도, 제한속도, 회피 가능성, 사고 발생 위치를 분리한다. 영상만으로 속도를 단정하지 않는다. | 실제 속도나 제한속도 자료가 있나? |
| `secondary_collision_pollution` | 1차 사고 후 2차 충돌이 있음 | 단일 사고유형으로 합침 | `primary_collision`, `secondary_collision`, 각 충돌 상대와 원인을 분리한다. | 첫 충돌과 두 번째 충돌의 상대가 각각 누구인가? |
| `injury_damage_pollution` | 파손, 사망, 부상 정보가 있음 | 사고 유형 또는 과실비율 확정 | 손해 정도는 보험/형사 쟁점으로 분리하고 사고 대상·원인 판단을 대체하지 않는다. | 부상/사망/파손은 어느 충돌에서 발생했나? |
| `text_keyword_override_pollution` | 사용자가 부정확한 사고유형을 선택하거나 키워드가 강함 | 영상 관찰값을 무시하고 선택값으로 확정 | 사용자 선택은 `user_claim`으로 보관하고, 영상 관찰값과 충돌하면 `conflict` 또는 `requires_confirmation`으로 남긴다. | 입력 내용과 영상 중 어느 부분이 서로 다른가? |

## 구현 시 적용 기준

1. `direct_collision_partner_type`은 `collision_partner_type`보다 우선한다.
2. `direct_collision_partner_type`이 없고 객체 존재만 있는 경우 사고 유형을 확정하지 않는다.
3. `pedestrian_visible`, `bicycle_visible`, `traffic_signal_visible` 같은 존재 관찰값은 기본적으로 `supporting_observations` 또는 `uncertain_observations`에 둔다.
4. 부정 관찰값은 오분류를 막는 데만 사용한다. 예: `pedestrian_visible=false`는 보행자 사고 근거 검색을 강화하는 키워드가 아니다.
5. 법적 쟁점은 사고 대상과 분리한다. 예: 횡단보도는 차대차 후미추돌에서도 정차 사유 또는 환경 맥락일 수 있다.
6. 영상과 사용자 입력이 충돌하면 한쪽을 덮어쓰지 않고 `fact_arbitration.conflicts`에 남긴다.
7. 확정할 수 없는 경우 사용자에게 묻는 질문은 “무엇이 직접 충돌했는가”, “누가 어떤 방향으로 움직였는가”, “보이지 않는 신호/속도/위치 정보가 있는가”처럼 결론을 바꾸는 필드부터 묻는다.

## 다음 단계 연결

- P0-2: 사고 영상 1~5 기준선 재측정에서 각 사고가 위 오염 ID 중 어디에 걸리는지 기록한다.
- P0-3: 위 공통 판단 축을 Agent 입력 계약 필드로 정리한다.
- P0-4: 위 오염 ID를 guard 테스트와 회귀 fixture로 전환한다.
- P2-2: 오염률, 직접 충돌 대상 정확도, 관찰값 0개 비율을 평가 지표로 만든다.
