# 영상 reference 지표 평가 절차

이 문서는 P2-2 단계에서 고정한 영상/입력 사실 추출 품질 지표와 실행 절차를 정리한다. 목적은 사고 영상 1~5, 공개 reference 후보, AI Hub 샘플을 분석할 때 “좋아진 것 같다”가 아니라 같은 기준으로 전후 결과를 비교하는 것이다.

## 평가 대상

- `scripts/video_accuracy_batch.py`가 생성한 `aggregate.json`
- `tests/fixtures/video_accuracy/reference_case_manifest.schema.json` 형식의 reference case manifest
- 실제 영상 원본, 공개 영상 원본, AI Hub 원본 데이터, API key는 평가 산출물에 포함하지 않는다.

## 고정 지표

| 지표 | 의미 | 기본 기준 |
| --- | --- | --- |
| `direct_collision_target_accuracy` | reference의 직접 충돌 대상과 분석 결과의 직접 충돌 대상이 맞는 비율 | `0.8` 이상 |
| `accident_party_accuracy` | 차대차, 차대사람, 차대자전거 같은 사고 대분류가 기대 대상과 맞는 비율 | `0.8` 이상 |
| `context_pollution_rate` | `must_not_promote`에 적은 금지 사고유형/오염 키워드가 결과에 섞인 비율 | `0.0` 이하 |
| `zero_observation_rate` | 프레임은 처리됐지만 영상 관찰값이 0개인 샘플 비율 | `0.2` 이하 |
| `evidence_mismatch_rate` | 기대 context가 근거 카드에 연결되지 않거나 금지 context가 근거에 섞인 비율 | `0.2` 이하 |
| `conditional_branch_coverage` | 분기형 판단이 필요한 reference에서 조건별 결과 카드가 생성된 비율 | `0.8` 이상 |

이 기준은 제품 최종 정확도 기준이 아니라 회귀 감지용 시작 기준이다. 실제 reference가 늘어나면 수치 기준은 별도 검토 후 조정한다.

## 실행 순서

먼저 reference manifest가 안전한지 확인한다.

```powershell
py -3 scripts\validate_reference_case_manifest.py `
  --manifest tests\fixtures\video_accuracy\reference_metrics_manifest.json `
  --output logs\video_accuracy\reference_metrics_manifest_preflight.json
```

그 다음 batch aggregate와 reference manifest를 연결해 지표를 계산한다.

```powershell
py -3 scripts\evaluate_video_reference_metrics.py `
  --reference-manifest tests\fixtures\video_accuracy\reference_metrics_manifest.json `
  --batch-aggregate tests\fixtures\video_accuracy\reference_metrics_batch_aggregate.json `
  --output logs\video_accuracy\reference_metrics_fixture_eval.json `
  --fail-on-threshold
```

실제 사고 영상 1~5 또는 공개 reference 후보를 평가할 때는 `--reference-manifest`와 `--batch-aggregate`만 해당 로컬 산출물로 바꾼다. 로컬 영상 경로와 큰 로그는 Git에 올리지 않는다.

## 해석 기준

- `status=passed`: 현재 threshold 기준으로 즉시 확인할 회귀 신호가 없다.
- `status=needs_attention`: 하나 이상의 지표가 기준을 벗어났다. 해당 sample의 `context_pollution_hits`, `missing_expected_context`, `zero_observations`, `conditional_branch_present`를 먼저 본다.
- `reference_matched_rate < 1.0`: batch sample 이름이나 `reference_case_id`가 reference manifest case id와 연결되지 않았다. 지표 해석 전에 manifest 연결을 먼저 수정한다.

## 주의 사항

- 전문가 의견이나 실제 결과는 `reference_outcome`에 남길 수 있지만 Agent 사용자 입력으로 넣지 않는다.
- 이 지표는 영상 분석 모델의 정답률 전체를 의미하지 않는다. 사고 대상 오염, 관찰값 누락, 근거 부적합, 분기형 안내 누락을 잡는 회귀 지표다.
- 공개 영상 후보는 `review_status=reviewed_for_evaluation`이 되기 전까지 정량 평가 기준으로 사용하지 않는다.
