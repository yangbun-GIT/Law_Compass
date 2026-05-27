# LawCompass KNIA 회귀/502 핫픽스 v6

## 교체 경로

프로젝트 루트 기준으로 아래 파일을 덮어쓰세요.

1. `apps/agent/app/services/knia/knia_matcher.py`
2. `apps/agent/app/services/orchestration_evidence.py`
3. `apps/agent/app/services/knia/knia_report_adapter.py`
4. `apps/agent/app/services/knia/knia_repository.py`

## 수정 이유

최근 KNIA 링크 카드 수정 후 Agent 회귀 테스트와 `/analyze-text`에서 문제가 발생했습니다.

확인된 문제:
- `knia_report_adapter.py`에서 `_repository_display_fallback_candidates()`를 호출하지만 보조 함수 일부가 누락되어 Agent 예외/502가 발생할 수 있었습니다.
- `knia_fault_charts.accident_party_type` 값이 잘못 저장된 row가 있어 `car_vs_car` 필터에서 `차41-1`, `차43-*`, `차12-*`가 빠질 수 있었습니다.
- `intersection_signal_violation` 검색이 보행자/자전거 신호위반 기준인 `보1`, `거1-2`를 반환했습니다.
- `lane_change_collision` 검색이 `차43-2` 대신 `차16-1`을 primary로 잡았습니다.
- 법률 근거에도 KNIA scenario compatibility filter가 적용되어 `bicycle_collision`의 legal evidence가 제거되고 coverage가 low로 떨어졌습니다.

## 핵심 변경

- KNIA match cache key를 `knia:match:v7`로 올려 기존 오염 캐시를 회피합니다.
- `_hybrid_lookup()`의 party filter가 `accident_party_type`뿐 아니라 `chart_no` prefix도 사용합니다.
  - `차%`: car_vs_car
  - `보%`: car_vs_person
  - `자%`, `거%`: car_vs_bicycle
  - `기%`: car_vs_object
  - `단%`: single_vehicle
- `intersection_signal_violation`은 차량 대 차량 기준인 `차12*`만 primary로 허용합니다.
- `lane_change_collision`은 `차43*` 또는 명시적 진로변경 텍스트만 primary로 허용합니다.
- `rear_end_collision`은 `차41/차42` 후미추돌 기준을 우선합니다.
- `orchestration_evidence.py`에서 KNIA compatibility filter는 KNIA evidence에만 적용하고 legal evidence는 제거하지 않습니다.
- `knia_report_adapter.py`의 누락 fallback helper들을 추가했습니다.

## 적용 후 실행

```powershell
docker compose --env-file .env up -d --build agent gateway frontend
```

## 확인 명령

```powershell
docker compose exec agent python -c "from app.services.knia.knia_matcher import match_knia_charts; print(match_knia_charts(description_text='상대 차량이 적색신호를 위반하고 교차로에 진입해 직진 중인 내 차와 충돌했습니다.', structured_facts={}, selected_keywords=[], scenario_type='intersection_signal_violation', accident_party_type='car_vs_car', limit=5))"
```

위 결과는 `보1`, `거1-2`가 아니라 `차12*` 계열이거나 비어 있어야 합니다.

```powershell
docker compose exec agent python scripts/test_agent_regression_scenarios.py
```
