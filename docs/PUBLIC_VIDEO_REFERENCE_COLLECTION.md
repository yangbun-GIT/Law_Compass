# 공개 사고 영상 reference 자동 수집 절차

이 문서는 사고 영상과 사고 설명이 함께 있는 공개 자료를 LawCompass 영상 정확도 테스트 reference 후보로 수집하는 절차다. 수집 대상은 원본 영상 파일이 아니라 링크와 공개 메타데이터다.

## 목적

- 영상 분석이 사고 대상을 잘못 인식하는지 확인할 reference 후보를 넓힌다.
- 횡단보도, 사람, 자전거, 신호등, 중앙선, 주정차 차량 같은 환경 정보가 실제 사고 대상처럼 오염되는 사례를 찾는다.
- 한문철TV 등 공개 사고 영상의 설명과 전문가 의견은 테스트 calibration reference로만 사용한다.

## 금지 사항

- 공개 영상 원본 다운로드를 기본 흐름으로 두지 않는다.
- 원본 영상 파일, AI Hub 원본 데이터, API key, 다운로드 로그, 개인 로컬 경로를 Git에 올리지 않는다.
- 전문가 의견이나 공개 영상 설명을 Agent 사용자 입력 사실로 주입하지 않는다.
- 수집 후보를 검토하지 않고 바로 정확도 평가 정답으로 사용하지 않는다.

## 수집 명령

YouTube 검색 기반 후보 수집은 `YOUTUBE_API_KEY`가 로컬 환경 변수에 있을 때만 가능하다. 키는 `.env` 또는 개인 shell에만 둔다.

```powershell
$env:YOUTUBE_API_KEY = "<local-only-key>"
py -3 scripts\collect_public_video_references.py `
  --query "한문철 블랙박스 교차로 사고" `
  --query "한문철 중앙선 침범 사고" `
  --max-results 5 `
  --output .local\video_reference_candidates.json
```

이미 알고 있는 공개 URL만 후보로 넣을 수도 있다. 이 경우 API key가 필요 없다.

```powershell
py -3 scripts\collect_public_video_references.py `
  --urls "https://www.youtube.com/watch?v=VIDEO_ID" `
  --output .local\video_reference_candidates.json
```

기존 후보 manifest에 추가하려면 `--append`를 사용한다.

```powershell
py -3 scripts\collect_public_video_references.py `
  --query "한문철 후방추돌 사고" `
  --append `
  --output .local\video_reference_candidates.json
```

## 수집 후 검토

자동 수집 결과는 모두 `candidate_requires_manual_review` 상태다. P0-2 또는 이후 회귀 평가에 넣기 전에 아래를 수동으로 보강한다.

- `scenario_summary`: 사고 상황을 짧게 정리
- `reference_expectations.direct_collision_partner_type`: 실제 직접 충돌 대상
- `reference_expectations.expected_context`: 신호, 횡단보도, 중앙선, 주정차 차량 등 보조 환경
- `reference_expectations.must_not_promote`: 오염되면 안 되는 사고 유형
- `evaluation_focus`: 어떤 오염 유형을 검증할지

원본 영상 분석이 꼭 필요하면, 사용 가능한 범위에서 로컬 테스트 파일로만 보관하고 manifest에는 로컬 전용 경로를 둔다. 이 manifest는 Git에 올리지 않는다.

## P0-2 연결

P0-2 기준선 재측정은 기존 사고 1~5번을 우선 실행한다. 공개 reference 후보는 링크와 설명 기준의 보조 후보로 쌓고, 실제 로컬 영상 파일이 준비된 후보만 영상 파이프라인에 포함한다.
