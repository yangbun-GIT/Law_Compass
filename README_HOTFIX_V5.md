# KNIA 502 Hotfix v5

## 원인
`knia_report_adapter.py`에서 `_repository_display_fallback_candidates(...)`를 호출하지만 함수 정의가 누락되어 Agent 분석 중 `NameError`가 발생할 수 있었습니다. 이 때문에 Gateway는 `/analyze-text`에서 502를 반환합니다.

또한 `knia_fault_charts.accident_party_type` 값이 잘못 들어간 row가 있어 `차41-1` 같은 차량 대 차량 기준이 `car_vs_person`으로 저장되어 있었습니다.

## 수정 파일
- `apps/agent/app/services/knia/knia_report_adapter.py`
- `apps/agent/app/services/knia/knia_repository.py`

## 적용 후 확인
```powershell
docker compose --env-file .env up -d --build agent gateway frontend
docker compose logs --tail=200 agent
```

```powershell
docker compose exec agent python -c "from app.services.knia.knia_repository import KniaRepository; rows=KniaRepository().display_link_candidates('car_vs_car', 10); print([(r.get('chart_no'), r.get('accident_party_type'), r.get('title'), r.get('video_url')) for r in rows[:10]])"
```

그 다음 기존 케이스를 재분석하세요.
