# KNIA 링크 카드 중복 표시 및 URL fallback 수정 코드

아래 파일을 프로젝트 루트 기준 동일 경로에 덮어쓰세요.

## 덮어쓸 파일

1. `apps/agent/app/services/knia/knia_report_adapter.py`
2. `apps/gateway/src/lib/report-composer.ts`
3. `apps/frontend/src/components/knia/KniaVideoLinkCard.vue`
4. `apps/frontend/src/components/knia/RelatedVideoCard.vue`

## 핵심 수정

- KNIA 후보에 `chart_no`만 있어도 Agent에서 `knia_fault_charts` 상세 row를 최대 3개까지 보강 조회합니다.
- 사용자 표시용 KNIA 카드는 `related_knia_video_card`를 canonical field로 사용합니다.
- `related_video`에 같은 KNIA 카드가 들어와 중복 표시되는 문제를 Gateway에서 제거합니다.
- `video_url`이 있으면 `KNIA 관련 영상 보기`, 없고 `source_detail_url/source_url`이 있으면 `KNIA 원문 기준 보기` 버튼을 표시합니다.
- URL 없는 안내 문구는 URL 있는 후보가 없을 때만 1회 표시되도록 구성했습니다.
- iframe, video 태그, 기본 로고 썸네일 이미지는 렌더링하지 않습니다.

## 실행 및 검증

직접 실행하지 않았습니다. 아래는 사용자가 로컬에서 실행할 명령입니다.

```powershell
cd apps/agent
PYTHONPATH=. python -m pytest tests/test_knia_report_integration.py
PYTHONPATH=. python -m pytest tests/test_orchestrator.py
```

```powershell
cd apps/gateway
npm test
npm run build
```

```powershell
cd apps/frontend
npm run build
npm run test:display
```

```powershell
docker compose --env-file .env up -d --build
docker compose ps
```


## v2 추가 수정

Gateway TypeScript build 오류를 수정했습니다.

오류:
`src/lib/report-composer.ts(...): error TS2339: Property 'related_knia_video_card' does not exist on type '{}'.`

원인:
`composeKniaLinkCards()`가 URL 후보가 없을 때 `{}`를 반환하면서 TypeScript가 반환 타입을 `{}` union으로 추론했습니다.

수정:
- `composeKniaLinkCards(...): AnyRecord` 반환 타입 명시
- `const kniaLinkCards: AnyRecord = ...` 로컬 타입 명시


## v3 추가 수정

현재 화면에 `수집된 KNIA 원문 링크가 없습니다`가 계속 표시되는 원인은,
Agent가 표시 카드 후보를 만들 때 `chart_no` 없이 `후미추돌 과실비율 참고 기준` 같은 시나리오 라벨만 가진 KNIA 후보를 선택했기 때문입니다.
이 경우 기존 `chart_no -> knia_fault_charts.get_chart()` 보강이 실행되지 못합니다.

v3는 다음을 추가합니다.

- `KniaRepository.display_link_candidates()` 추가
- Agent `knia_report_adapter.py`가 URL 없는 후보만 있을 때 scenario_type과 후보 텍스트로 `knia_fault_charts`의 URL 보유 row를 bounded fallback 조회
- 후미추돌, 교차로 신호, 차선변경, 중앙선/장애물, 보행자, 자전거 등 주요 scenario_type에 대해 일반화된 검색 term 적용
- 차41-1 같은 특정 chart_no 하드코딩 없이 DB row 중 가장 관련성 높은 URL 보유 KNIA 기준을 선택
- Gateway 카드에 `button_url` 보존

덮어쓴 뒤 새 분석 또는 재분석이 필요합니다. 기존 analysis_results에는 새 카드가 자동으로 소급 적용되지 않습니다.


## v4 추가 수정

현재 DB에서 `knia_fault_charts.accident_party_type` 값이 신뢰할 수 없는 상태였습니다.
예를 들어 `차41-1`은 차량 대 차량 후미추돌 기준이지만 `accident_party_type=car_vs_person`으로 저장되어 있어
`display_link_candidates('car_vs_car', ...)`가 빈 배열을 반환했습니다.

v4는 다음을 보강합니다.

- `KniaRepository.display_link_candidates()`가 `accident_party_type`만 믿지 않고 `chart_no` prefix도 함께 사용합니다.
  - `차*` → car_vs_car 후보
  - `보*` → car_vs_person 후보
  - `자*`, `거*` → car_vs_bicycle/two_wheeler 후보
  - `단*` → single_vehicle 후보
- party filter 결과가 비어 있으면 Agent adapter가 전체 URL 보유 row에서 한 번 더 bounded fallback 검색합니다.
- DB schema migration 없이 동작합니다.

적용 후 아래 명령으로 확인할 수 있습니다.

```powershell
docker compose exec agent python -c "from app.services.knia.knia_repository import KniaRepository; rows=KniaRepository().display_link_candidates('car_vs_car', 10); print([(r.get('chart_no'), r.get('accident_party_type'), r.get('title'), r.get('video_url')) for r in rows[:10]])"
```

`차41-1` 또는 `차*` 후보가 포함되어야 합니다.
