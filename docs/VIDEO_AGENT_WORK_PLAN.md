# 영상·입력 사실 추출 및 Agent 판단 보강 작업 계획

이 문서는 사용자 영상과 입력에서 오염되지 않은 사고 사실을 추출하고 Agent 판단 계약으로 연결하기 위한 임시 실행 계획이다. 작업 중 단계가 흔들리지 않도록 모든 관련 개발은 이 문서를 먼저 확인한 뒤 진행한다.

이 문서는 영구 인수인계 문서가 아니다. 아래 단계가 모두 완료되고 `SYSTEM_OVERVIEW.md`에 최종 상태가 반영되면 이 문서는 삭제한다.

## 운영 규칙

1. 작업 시작 전 `DEVELOPMENT_PROMPT.md`, `SYSTEM_OVERVIEW.md`, `docs/GITHUB_COLLABORATION_WORKFLOW.md`, 그리고 이 문서를 확인한다.
2. 각 단계는 아래 순서대로 진행한다. 단, 현재 단계의 완료를 위해 반드시 선행되어야 하는 작업이 발견되면 이 문서의 가장 알맞은 위치에 새 항목으로 추가한 뒤 이어서 진행한다.
3. 새 항목을 추가할 때는 특정 샘플 사고에만 맞춘 해결책이 아니라 다른 사고에도 적용 가능한 일반 판단 축으로 적는다.
4. 영상 원본, 큰 로그, 외부 참고 영상, AI Hub 원본 데이터, API 키, 사용자 비밀번호, 토큰은 커밋하지 않는다.
5. 한문철TV 등 공개 영상·변호사 해설 자료는 공식 판례나 법률 근거가 아니라 테스트용 reference 또는 calibration 자료로만 다룬다. 무단 다운로드, 무단 스크래핑, 원문 복제, 학습 데이터 편입은 기본 개발 경로로 삼지 않는다.
6. 각 단계 완료 시 검증 결과와 남은 위험을 짧게 기록하고, 구조·계약·실행 방법·환경변수·known issue가 바뀌면 `SYSTEM_OVERVIEW.md`를 함께 갱신한다.

## 핵심 원칙

- 객체 또는 배경의 존재만으로 사고 유형을 확정하지 않는다.
- 사고 대상, 직접 충돌 대상, 사고 원인, 도로 환경, 법적 쟁점을 분리한다.
- 영상 관찰값은 프레임 근거와 confidence가 부족하면 확정하지 않고 보류 또는 확인 후보로 남긴다.
- 사용자 입력은 보완 정보이지만 부정확할 수 있다. 영상 관찰값과 충돌하면 충돌·보류·확인 필요 상태로 Agent에 전달한다.
- Agent 결과는 최종 판결이 아니라 실제 판례, 법령, KNIA/보험 기준을 확인한 참고 가이드로 표현한다.

## 오염 방지 예시

| 관찰 또는 입력 | 잘못된 승격 | 올바른 처리 |
| --- | --- | --- |
| 횡단보도 또는 사람이 보임 | 차대사람 사고 확정 | 직접 충돌 대상이 사람인지 별도 확인 |
| 자전거가 보임 | 차대자전거 직접 충돌 확정 | 직접 충돌 대상인지, 비접촉 유발 요인인지 분리 |
| 앞차가 보임 | 단순 후미추돌 확정 | 앞차 정차 이유, 내 차/뒤차 역할, 충돌 방향 확인 |
| 중앙선이 보임 | 중앙선 침범 가해 확정 | 침범 주체, 침범 사유, 도로 장애물, 대향 차량 반응 분리 |
| 신호등이 보임 | 신호위반 사고 확정 | 내 신호와 상대 신호의 가시성 및 진입 시점 분리 |
| 주차·정차 차량이 보임 | 주정차 사고 확정 | 직접 충돌 대상인지, 도로 장애물인지, 시야/등화/위치 확인 |
| 낙하물·장애물이 보임 | 장애물 충돌 사고 확정 | 실제 충돌 대상인지, 회피 원인인지, 단순 배경인지 구분 |

## 단계별 계획

### P0-1. 사고 오염 유형 목록화

- 목표: 사고를 잘못 인식하는 오염 패턴을 먼저 표로 고정한다.
- 범위: 사람 등장 오염, 자전거 등장 오염, 신호등 오염, 중앙선 오염, 정차 차량 오염, 장애물 오염, 앞차/뒤차 역할 오염, 차선/진행방향 오염.
- 산출물: `contamination_risk_matrix` 형태의 문서 또는 fixture.
- ReAct 적용: 필수, 1회.
- 이유: 구현 전 판단 축을 고정하지 않으면 특정 테스트 케이스에 과적합될 위험이 크다.
- 상태: 완료. `docs/VIDEO_CONTAMINATION_RISK_MATRIX.md`와 `tests/fixtures/video_accuracy/contamination_risk_matrix.json`에 범용 오염 유형, 분리 필드, guard 기준, 우선 확인 질문을 정리했다.

### P0-2. 사고 1~5 영상 기준선 재측정

- 목표: 현재 파이프라인이 각 영상에서 어떤 사고 시점, 충돌 대상, 관찰값을 뽑는지 확인한다.
- 확인 항목: 사고 시점 후보, 직접 충돌 대상, 보조 환경, 잘못 승격된 사고유형, 관찰값 0개 여부, 차대차/차대사람 오염 여부.
- 산출물: 로컬 로그와 평가 요약. 원본 영상과 큰 로그는 Git에 포함하지 않는다.
- ReAct 적용: 필수, 2회.
- 이유: 영상 판단은 고위험 영역이며 실제 결과를 보고 재검토해야 한다.

### P0-3. 사고 대상·환경 분리 계약 강화

- 목표: `collision_partner_type`, `direct_collision_partner_type`, `road_context`, `trigger_actor`, `legal_issue_context`를 명확히 분리한다.
- 예시: 자전거는 직접 충돌 대상일 수도 있고 비접촉 유발 요인일 수도 있다.
- ReAct 적용: 필수, 최대 3회.
- 이유: Agent 판단 정확도와 근거 검색 적합도에 직접 영향을 준다.
- 상태: 완료. `scripts/evaluate_video_observation_merge.py`로 P0-2 OpenAI 프레임 관찰값과 YOLO 후보 관찰값을 병합해 Agent 입력 계약과 fact arbitration을 재측정했다. YOLO의 사람·신호등·차량 객체 후보는 13개 모두 `uncertain`으로 남고, `accepted/fact_patch/applied/confirmed`로 승격되지 않았다. `apps/agent/tests/test_video_input_contract.py`에 같은 계약을 회귀 테스트로 고정했다.

### P0-4. 오염 방지 guard 확장

- 목표: 횡단보도 외에도 자전거, 신호등, 중앙선, 정차 차량, 장애물, 진행방향, 앞차/뒤차 역할 오염을 막는 범용 guard를 추가한다.
- 원칙: 특정 사고 1~5에 맞춘 규칙이 아니라 `객체 존재 != 사고 유형 확정` 원칙으로 구현한다.
- ReAct 적용: 필수, 최대 3회.
- 이유: guard가 잘못되면 사고유형 전체가 틀어질 수 있다.
- 상태: 완료. `video_input_contract_guards.py`에 자전거/장애물 직접 충돌 근거 요구, 신호위반 확정 전 신호 상태·전환 근거 요구, 중앙선 침범 확정 전 침범 사유·도로 맥락 요구, 무등화 정차 차량/앞차 정차/비접촉 유발의 맥락 guard를 추가했다. YOLO의 `*_candidate` 충돌 대상은 확정 fact로 승격하지 않도록 고정했다.

### P0-5. 관찰값 0개 fallback 보강

- 목표: 프레임은 충분한데 판단 반영 관찰값이 0개인 상황을 방치하지 않는다.
- 처리: 프레임 재선택, YOLO 객체 후보, OpenAI 재분석, 확인 필요 후보 생성.
- ReAct 적용: 필수, 최대 3회.
- 이유: 영상 처리의 핵심 실패 케이스다.
- 상태: 완료. `analysis_recovery`에 `retry_plan`과 `confirmation_prompts`를 추가해 프레임 재선택, OpenAI 재분석, YOLO 후보 검토, 사용자 확인 질문 생성을 구조화했다. 사고 시점 후보가 있는 frame-rich 영상은 `accident_event_candidate`와 `visual_evidence_limited`를 supporting observation으로 남기며, 보류 관찰값만 있는 경우 `frame_rich_uncertain_observations_only`로 구분한다. 내부 실패가 최종 pass로 보이지 않도록 `scripts/verify_agent_regression.ps1`의 하위 명령 exit code 처리도 보강했다.

### P1-1. 사고 시점 후보 추출 개선

- 목표: 영상 초반 장면이나 배경을 사고로 착각하지 않도록 전체 흐름에서 사고 직전, 충돌, 사고 직후 후보를 잡는다.
- 고려: 긴 영상, 휴대폰으로 촬영한 블랙박스 화면, 5~10초 짧은 영상.
- ReAct 적용: 필수, 최대 3회.
- 이유: 사고 시점이 틀리면 이후 분석이 모두 흔들린다.
- 상태: 완료. Worker 전처리에서 scene-change 이벤트를 사고 후보 구간으로 클러스터링하고, 대표 프레임마다 `event_candidate_id`, `event_phase`, `event_window_*` 메타데이터를 남기도록 보강했다. scene-change가 없는 짧은 영상이나 부드러운 영상은 시간대별 fallback 후보 구간을 생성한다. OpenAI/YOLO 분석 입력에도 같은 후보 구간 메타데이터를 전달해 여러 후보를 비교한 뒤 실제 충돌 전후 흐름을 보도록 했다. Worker 전체 테스트, Agent 입력 계약 테스트, Docker 회귀 검증을 통과했다.

### P1-2. 사용자 입력과 영상 관찰값 중재

- 목표: 사용자가 잘못 입력했거나 영상이 애매할 때 충돌, 보류, 확인 필요 상태로 분리한다.
- 원칙: 영상은 객관 정보지만 불완전할 수 있으므로 무조건 우선하지 않는다.
- ReAct 적용: 필수, 2회.
- 이유: 실제 사용자 입력은 부정확할 가능성이 크다.
- 상태: 완료. `fact_arbitration`이 확정 영상 fact뿐 아니라 보류 영상 관찰값도 함께 중재하도록 보강했다. 보류 영상 후보가 사용자 입력과 충돌하면 사용자 값을 유지하되 `pending_video_confirmations`와 `confirmation_fields`로 확인 질문에 넘긴다. 사용자 입력이 비어 있으면 missing fact 확인 후보로 남기고, 사용자 입력과 같은 방향이면 `tentatively_supported_fields`로 참고 보강만 표시한다. Gateway 결과 카드와 missing_info 질문도 이 계약을 사용하도록 연결했다. Agent/Gateway/Frontend 빌드 및 Docker 회귀 검증을 통과했다.

### P1-3. 애매한 사고의 분기형 결과

- 목표: 상대 신호 미확인처럼 결론이 갈리는 상황은 가능한 결과를 나누어 설명한다.
- 예시: 상대 신호가 녹색이면 한 방향, 상대 신호가 적색이면 다른 방향으로 판단 범위가 달라질 수 있음을 근거 기반으로 제시한다.
- ReAct 적용: 권장, 2회.
- 이유: 판단 로직보다 출력 정책에 가깝지만 사용자 신뢰에 큰 영향을 준다.
- 상태: 완료. Gateway 결과 조립에서 조건별 결과 카드를 신호 미확인에만 묶지 않고 사고 대상, 중앙선 침범 사유, 정차/후방추돌 사유까지 확장했다. `missing_info`, 영상 보류 관찰값, `fact_arbitration` 확인 필요 필드가 결론을 갈라놓는 경우 사용자 화면에 가능한 판단 방향과 먼저 확보할 자료를 표시한다. 우회전/직진 같은 진행 방향 단어만으로 신호 분기가 과잉 생성되지 않도록 감지 조건도 좁혔다. Gateway `report-composer` 테스트 38개를 통과했다.

### P2-1. 외부 참고 케이스 manifest

- 목표: 한문철TV 등 공개 참고 사례를 테스트 reference 또는 calibration 자료로만 관리한다.
- 저장 가능 항목: 링크, 수동 요약, 전문가 의견 요지, 실제 결과 여부, 평가 focus.
- 금지: 공식 근거, 정답 데이터, 학습 데이터, 무단 다운로드 산출물로 사용.
- ReAct 적용: 간단 적용, 1회.
- 이유: 데이터 사용 경계만 지키면 구현 위험은 낮다.
- 상태: 완료. Reference case schema에 `reference_role`, `review_status`, `reference_outcome`을 추가해 공개 영상/전문가 의견/실제 결과를 Agent 입력 사실이 아닌 evaluation·calibration 자료로만 구분하게 했다. `scripts/validate_reference_case_manifest.py`를 추가해 manifest의 필수 필드, 직접 충돌 대상 기대값, 오염 방지 항목, raw video commit 금지, Agent 입력 금지, private local path 노출 여부를 검사한다. 공개 링크 수집 스크립트도 새 계약을 생성하도록 맞췄고, 예시 manifest와 수집 smoke manifest preflight를 통과했다.

### P2-2. 평가 지표 고정

- 목표: 정확도 향상이 감으로 진행되지 않도록 지표화한다.
- 지표: 사고 대상 정확도, 직접 충돌 대상 정확도, 보조 환경 오염률, 관찰값 0개 비율, 근거 부적합률, 분기형 판단 생성 여부.
- ReAct 적용: 필수, 2회.
- 이유: 이후 개발이 좋아졌는지 나빠졌는지 판단 기준이 필요하다.
- 상태: 완료. `scripts/evaluate_video_reference_metrics.py`를 추가해 reference case manifest와 `video_accuracy_batch.py`의 aggregate 결과를 연결하고, 직접 충돌 대상 정확도, 사고 대분류 정확도, context 오염률, 관찰값 0개 비율, 근거 부적합률, 분기형 판단 coverage를 계산하도록 했다. `tests/fixtures/video_accuracy/reference_metrics_manifest.json`과 `reference_metrics_batch_aggregate.json` synthetic fixture를 추가해 지표 계산을 재현 가능하게 고정했다. `docs/VIDEO_REFERENCE_METRICS.md`에 실행 순서와 해석 기준을 문서화했다.

### P2-3. Agent 근거 검색·표시 정합성

- 목표: 사고유형이 맞게 잡힌 뒤 KNIA, 법령, 판례 근거도 같은 사고축으로 검색되게 보강한다.
- 예시: 차대차 사고에 보행자 기준이 섞이지 않게 필터링한다.
- ReAct 적용: 필수, 최대 3회.
- 이유: 사용자 신뢰와 결과 품질에 직접 영향을 준다.

### P3. 전체 회귀 테스트와 문서 동기화

- 목표: 사고 1~5, synthetic fixture, 외부 reference manifest를 기준으로 전체 흐름을 점검한다.
- 산출물: 검증 결과 요약, 남은 리스크, `SYSTEM_OVERVIEW.md` 최신화.
- ReAct 적용: 권장, 2회.
- 이유: 제품 완성도 확인 단계다.

## 완료 조건

아래 조건을 모두 만족하면 이 문서를 삭제한다.

- P0~P3 단계가 완료됐다.
- 영상 원본과 큰 로그가 Git에 포함되지 않았다.
- `SYSTEM_OVERVIEW.md`에 최종 구조, 검증 결과, 남은 리스크가 반영됐다.
- 필요한 경우 `DEVELOPMENT_PROMPT.md`에 지속 적용해야 할 원칙이 반영됐다.
- 팀원이 이어서 볼 수 있는 실행/검증 방법이 최신 상태다.

## 2026-05-29 P0-2a 추가 완료: reference 데이터 수집/사용 정책

P0-2 기준선 재측정 전에 외부 사고 영상과 사고 설명이 함께 있는 자료를 어떻게 테스트 reference로 사용할지 고정했다.

- `docs/VIDEO_REFERENCE_DATA_POLICY.md`를 추가해 기존 사고 1~5, AI Hub 샘플, 공개 영상 링크, 공식 근거 자료의 사용 목적과 금지 항목을 분리했다.
- `scripts/collect_public_video_references.py`와 `docs/PUBLIC_VIDEO_REFERENCE_COLLECTION.md`를 추가해 사용자가 영상을 직접 올리지 않아도 공개 링크/메타데이터 reference 후보를 수집할 수 있게 했다.
- `tests/fixtures/video_accuracy/reference_case_manifest.schema.json`을 추가해 reference case의 구조를 고정했다.
- `tests/fixtures/video_accuracy/reference_case_manifest.example.json`을 추가해 로컬 사용자 제공 영상, 공개 reference 링크, AI Hub 샘플의 안전한 manifest 예시를 제공했다.
- 공개 영상과 전문가 의견은 Agent 입력 사실이 아니라 평가와 calibration reference로만 사용한다.
- 원본 영상, AI Hub 원본 데이터, API key, 개인 로컬 경로가 포함된 실제 manifest는 Git에 커밋하지 않는다.

P0-2는 이 정책을 기준으로 기존 사고 1~5를 먼저 재측정하고, 외부 reference는 수집 스크립트로 링크/메타데이터 후보를 만든 뒤 요약/기대 관찰값을 검토한다. 로컬 영상 파일이 합법적으로 준비된 경우에만 영상 파이프라인에 포함한다.
## 2026-05-29 런타임 재검증 정정

이 문서의 P2-1은 외부 참고 케이스 manifest와 사용 정책을 고정한 단계이므로 다시 진행할 필요는 없다. 다만 P2-2 이후의 “영상 기준선 측정”, “reference metrics”, “정확도 고도화”는 실제 영상 처리 검증에 해당하므로 OpenAI 프레임 분석과 YOLO가 모두 켜진 런타임에서 다시 측정해야 한다.

이전 P2-2 결과 중 fixture/synthetic aggregate, manifest schema, guard 계약 검증은 유효하다. 그러나 실제 관리자 업로드 흐름에서 YOLO가 꺼져 있던 상태의 결과는 “OpenAI-only 또는 계약 검증”으로 분류하고, OpenAI+YOLO ON 재측정 결과와 분리해 기록한다.

재측정 시작 조건:

- `ENABLE_OPENAI_FRAME_ANALYSIS=1`
- `FRAME_ANALYSIS_FIXTURE_MODE=`
- `ENABLE_YOLO_FRAME_ANALYSIS=1`
- `YOLO_MODEL_PATH` 유효
- 새 업로드 metadata에서 `openai_frame_analysis.enabled=true`, `yolo_frame_analysis.enabled=true`, YOLO `summary.class_counts`, merged `observations` 확인
## 2026-05-29 P2-2 OpenAI+YOLO ON 재측정 결과

P2-2는 OpenAI 프레임 분석과 YOLO 보조 관찰을 모두 켠 상태에서 다시 실행했다.

- 실행 결과: `logs/video_accuracy/p2_2_openai_yolo_on_20260529/aggregate.json`
- Reference metrics: `logs/video_accuracy/p2_2_openai_yolo_on_reference_metrics_20260529.json`
- 런타임 조건: `ENABLE_OPENAI_FRAME_ANALYSIS=1`, `FRAME_ANALYSIS_FIXTURE_MODE=`, `ENABLE_YOLO_FRAME_ANALYSIS=1`, `YOLO_MODEL_PATH=/models/yolo/yolo11n.pt`
- DB 확인: 사고 1~5 모두 OpenAI/Yolo enabled, YOLO error 없음, YOLO class_counts와 merged observations 존재
- Batch 결과: 5개 샘플 pipeline pass, frame observation 44개, accepted 16개, uncertain 27개, applied 10개, conflict 2개
- Metrics 결과: direct collision target accuracy 1.0, accident party accuracy 1.0, context pollution rate 0.0, zero observation rate 0.0, evidence mismatch rate 0.2, conditional branch coverage 0.2

판정은 `needs_attention`이다. 직접 충돌 대상과 대분류 오염은 현재 기준을 만족하지만, 조건별 결과 설명이 필요한 사고 5개 중 1개만 분기형 결과가 잡혔다. 다음 작업은 P2-3 성격의 근거 검색/표시 적합도 보강과 함께 조건별 결과 카드 coverage를 높이는 방향으로 진행한다.
## 2026-05-29 P2-2 후속 보강 단계

P2-2 OpenAI+YOLO ON 재측정은 실행됐지만 최종 평가는 `needs_attention`이다. 직접 충돌 대상 정확도와 context 오염률은 기준을 만족했으나, 사고 2와 사고 5에서 영상 정량 관찰값이 부족했고 조건별 분기 coverage가 낮았다. 아래 단계는 특정 테스트 영상에 답을 맞추기 위한 작업이 아니라, 실제 사용자 영상에서도 같은 유형의 오염과 누락을 줄이기 위한 범용 보강 순서다.

P2-2a부터는 기존 사고 1~5 외에 HanmoonchulTV 공개 영상 후보를 로컬 calibration reference로 사용할 수 있다. 원본 파일은 `.local/public-video-references/hanmoonchul/` 아래에만 두고 Git, NAS 공유, 클라우드 업로드, 배포 패키지에 포함하지 않는다. edited 영상은 3분 이하로 자르고, 파일명은 `hanmoonchul_accident_001_edited.mp4` 형식을 따른다. 영상 설명이나 변호사 의견은 Agent 입력 사실로 주입하지 않고, 모델 출력 이후 오류 분석 기준으로만 사용한다.

### P2-2a. 영상 관찰값 감사 리포트 고정

- 목적: 영상별로 “실제 프레임에서 보이는 사실”과 “OpenAI/YOLO/Agent가 추출한 값”을 같은 표로 비교한다.
- 산출물: 사고별 accepted/uncertain/supporting 관찰값, YOLO class_counts, 대표 프레임 후보, 불일치 유형 요약.
- 완료 기준: 사고 1~5 각각에 대해 맞음/부분 맞음/틀림/보류를 구분한 리포트를 만들고, 다음 보강 항목이 어떤 오류를 줄이는지 추적할 수 있어야 한다.

P2-2a 상태: 완료. `scripts/audit_video_observation_report.py`를 추가했고, 기존 OpenAI+YOLO ON 배치 결과와 로컬 reference manifest를 비교해 `logs/video_accuracy/p2_2a_observation_audit_20260529.json` 및 `.md` 리포트를 생성했다. 5개 샘플 모두 직접 충돌 대상 오염이나 관찰값 0개 문제는 없었지만, 전부 `weak`로 남았다. 주요 원인은 사고 1의 대향/2차 충돌 맥락 누락, 사고 2의 신호 전환 정량 관찰 부족, 사고 5의 비접촉 유발-정차-후방추돌 시퀀스 부족, 조건별 분기 결과 명시 부족이다.

### P2-2b. 오버레이와 방송 UI 잡음 제거

- 목적: 한문철 영상 진행자, 방송 자막, 워터마크, 플레이어 UI가 `person`, `object`, `traffic light` 후보로 섞여 사고 객체를 오염시키는 문제를 줄인다.
- 적용 방향: 고정 화면 영역 반복 객체, 프레임 가장자리/상단 오버레이, 자막/로고 영역은 사고 객체 후보 confidence를 낮추거나 supporting/ignored로 분리한다.
- 완료 기준: YOLO `person` 감지가 있어도 직접 충돌 대상이나 보행자 사고로 승격되지 않고, 보류 질문 노이즈도 줄어야 한다.
- 상태: 완료. Worker YOLO payload에서 raw detection과 filtered detection을 분리하고, 3프레임 이상 같은 가장자리 위치에 반복되는 `person` 감지는 `ignored_detections`로 남긴다. 중앙 도로 영역의 사람 감지는 계속 후보로 유지하는 회귀 테스트를 추가했다.

### P2-2c. 시간 순서 기반 사고 시퀀스 관찰값 추출

- 목적: 단일 프레임 객체 감지가 아니라 “등장 -> 정지/감속 -> 충돌/회피 -> 사후 위치” 흐름을 관찰값으로 만든다.
- 적용 대상: 사고 2의 좌회전/신호 전환/측면 충돌, 사고 5의 자전거 비접촉 유발/트럭 정지/후방 버스 추돌.
- 후보 관찰값: `trigger_actor_type`, `trigger_actor_contact`, `ego_maneuver`, `ego_stop_reason`, `rear_collision_sequence`, `opponent_path`, `signal_phase_visible`, `signal_phase_unknown`.
- 완료 기준: 사고 2와 사고 5에서 0개 또는 객체 후보 위주의 관찰값이 아니라 판단에 쓸 수 있는 시퀀스 관찰값이 생성되어야 한다.

- 상태: 완료. Worker YOLO가 `temporal_sequence_summary`를 생성하고, top event window의 차량 관찰 흐름을 `vision_model:yolo_sequence` 후보로 변환한다. `accident_event_candidate`는 supporting으로, `direct_collision_partner_type`과 `collision_point_visible`은 fact threshold 아래의 확인 후보로 남겨 Agent가 바로 확정하지 않게 했다.

### P2-2d. 조건별 결과 분기 coverage 보강

- 목적: 상대 신호, 정차 사유, 중앙선 침범 사유, 비접촉 유발 여부처럼 결론을 바꾸는 사실이 불명확할 때 한쪽 결론만 내지 않는다.
- 적용 방향: 해당 축이 missing/uncertain/conflict이면 조건별 결과 카드를 생성하고, 사용자 확인 질문도 같은 축을 우선한다.
- 완료 기준: P2-2 reference metrics의 `conditional_branch_coverage`를 0.2에서 최소 0.8 이상으로 올린다.
- 상태: 완료. Gateway `report-composer`가 신호, 비접촉 유발, 중앙선 침범 사유, 정차/후방추돌 사유, 사고 대상 확인 축을 감지해 `branch_key`, `detected_branch_keys`, `secondary_branches`, `coverage` metadata를 조건별 결과 카드에 남긴다. `video_input_contract`의 confirmation group/candidate와 `fact_arbitration` 확인 필요 필드도 분기 감지에 포함했다. 비접촉 유발 전용 조건별 결과 카드를 추가했다. `scripts/evaluate_video_reference_metrics.py`는 reference ambiguous branch와 결과 `detected_branch_keys`를 비교하되, 과거 aggregate는 기존 조건부 카드 존재 여부로 fallback 평가한다. Gateway `report-composer` 테스트 41개와 fixture 기반 reference metrics 평가를 통과했다. 실제 coverage 목표 달성 여부는 P2-2e OpenAI+YOLO ON 재측정에서 확인한다.

### P2-2e. OpenAI+YOLO ON 재측정

- 목적: P2-2b~d 보강이 실제 영상 기준선에서 좋아졌는지 다시 측정한다.
- 실행 조건: `ENABLE_OPENAI_FRAME_ANALYSIS=1`, `FRAME_ANALYSIS_FIXTURE_MODE=`, `ENABLE_YOLO_FRAME_ANALYSIS=1`, 유효한 `YOLO_MODEL_PATH`.
- 완료 기준: direct collision target accuracy 1.0 유지, context pollution rate 0.0 유지, zero observation rate 0.0 유지, evidence mismatch rate 0.2 이하 유지, conditional branch coverage 0.8 이상.
- 상태: 완료. 실제 사고 영상 1~5를 OpenAI+YOLO ON 상태로 재측정했고, `scripts/video_agent_e2e.py`와 `scripts/video_accuracy_batch.py`의 출력 계약에 `conditional_outcome_card`를 보존하도록 보강했다. 최종 reference metrics는 `direct_collision_target_accuracy=1.0`, `context_pollution_rate=0.0`, `zero_observation_rate=0.0`, `evidence_mismatch_rate=0.2`, `conditional_branch_coverage=0.8`, status `passed`다. 산출물은 `logs/video_accuracy/p2_2e_openai_yolo_on_20260529/aggregate.json` 및 `logs/video_accuracy/p2_2e_openai_yolo_on_reference_metrics_20260529.json`에 로컬로만 생성되며 Git에 포함하지 않는다. 측정 후 worker는 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=`, `ENABLE_YOLO_FRAME_ANALYSIS=1` 상태로 복구했다.

P2-2e까지 통과하면 P2-3 근거 검색/표시 적합도 보강으로 넘어간다. P2-2e가 통과하지 못하면 실패 샘플을 기준으로 P2-2b~d 중 해당 원인 단계로 되돌아간다.
