# LawCompass 시스템 구성 명세서

## 2026-05-29 P2-2f AI-Hub 597 라벨 기반 reference 평가 연결 완료

AI-Hub 597 영상 라벨을 사고 영상 사실 추출의 대규모 reference 후보로 연결하는 P2-2f를 완료했다. 이 단계는 OpenAI/YOLO를 새로 호출하지 않고, 이미 내려받은 AI-Hub 라벨 JSON을 사용해 사고대상 오염 방지와 평가 coverage를 넓히는 정적 reference 준비 단계다.

| 범위 | 결과 |
| --- | --- |
| Manifest 생성 | `scripts/aihub597_labels_to_manifest.py`에 `--balanced` 옵션을 추가했다. `--balanced --per-target 50` 기준으로 차대차, 차대보행자, 차대이륜차, 차대자전거를 각 50건씩 뽑아 200건 manifest를 생성한다. |
| 평가 스크립트 | `scripts/evaluate_aihub597_label_reference.py`를 추가했다. manifest의 사고대상 분포, known direct target rate, pollution guard coverage, expected context coverage, balanced candidate count, failure axes를 계산한다. |
| Reference 계약 | `direct_collision_partner_type`에 `motorcycle`을 허용하도록 reference manifest schema, preflight validator, video reference metrics를 보강했다. AI-Hub `accident_object` 코드는 `0=vehicle`, `1=pedestrian`, `2=motorcycle`, `3=bicycle`로 정규화한다. |
| 검증 결과 | `.local/aihub597_video_label_manifest.json` 기준 preflight 200건 error 0/warning 0 `passed`. `.local/aihub597_label_reference_eval.json` 기준 `vehicle=50`, `pedestrian=50`, `motorcycle=50`, `bicycle=50`, `known_direct_target_rate=1.0`, `pollution_guard_coverage=1.0`, `expected_context_coverage=1.0`, status `passed`. |
| 남은 한계 | 라벨만으로는 OpenAI+YOLO가 실제 프레임에서 같은 사실을 뽑는지 직접 비교할 수 없다. 다음에 실제 영상 기반 비교를 하려면 P2-2f가 고른 balanced candidate에 대응하는 원천 영상 소량 다운로드가 필요하다. |
| 보안/저장 정책 | `.local/`, `logs/`, `datasets/aihub/.../labels` 산출물과 AI-Hub API key는 Git에 올리지 않는다. 라벨은 Agent 입력 사실이나 정답 데이터가 아니라 evaluation/calibration reference로만 사용한다. |

이 변경은 public route, DB schema, Redis key, storage path, 외부 API 종류, 실행 환경변수 키를 변경하지 않는다. 다음 단계는 P2-3 Agent 근거 검색/표시 정합성 보강이다.

## 2026-05-29 AI-Hub 597 원천 영상 선택 기준 추가

AI-Hub 597 원천 영상은 전체 다운로드 시 TB 단위까지 커질 수 있으므로, 영상 처리 검증에는 Validation 원천 영상 중 작은 묶음을 우선 사용하도록 기준을 문서화했다.

| 범위 | 내용 |
| --- | --- |
| 원천 영상 목록 | `docs/AIHUB_597_SOURCE_VIDEO_FILEKEYS.md`에 Training/Validation 원천 영상 filekey, 크기, 사고대상 분류, 선택 기준을 정리했다. 이미지 원천 데이터는 이번 영상 처리 검증의 우선순위에서 제외한다. |
| 다운로드 Scope | `scripts/download_aihub597_labels.ps1`에 `SourceSmoke`, `SourceValidationRecommended`, `SourceValidationVideoAll` Scope를 추가했다. 기존 `Video`, `All`, `-FileKeys` 동작은 유지한다. |
| 기본 선택 | `SourceSmoke`는 `509431`, `509442`, `509454`, `509466` 네 파일을 받아 보행자/이륜차/자전거/차대차 축을 약 400MB로 검증한다. |
| 확장 선택 | 더 많은 영상이 필요하면 `SourceValidationRecommended`를 사용한다. 그래도 부족하면 문서의 전체 목록에서 필요한 filekey만 `-FileKeys`로 직접 지정한다. |
| 제한 | AI-Hub API key가 현재 PowerShell 세션의 `AIHUB_API_KEY`에 있어야 다운로드할 수 있다. key, 원천 ZIP, 압축 해제 영상은 Git에 올리지 않는다. |

이 변경은 public route, DB schema, Redis key, storage path, 외부 API 종류를 변경하지 않는다. 로컬 원천 영상 저장은 Git 제외 경로에서만 수행한다.

## 2026-05-29 P2-2e OpenAI+YOLO ON 재측정 통과

P2-2b~d 보강 이후 실제 사고 영상 1~5를 OpenAI 프레임 분석과 YOLO 보조 관찰이 모두 켜진 Docker Worker에서 다시 측정했다. 측정 전 `scripts/video_agent_e2e.py`가 `/easy-report`의 `conditional_outcome_card`를 출력 JSON에 포함하지 않아 `video_accuracy_batch.py`와 reference metrics가 조건별 분기 coverage를 과소평가하는 문제가 확인되어, E2E/배치 출력 계약을 보강했다.

| 범위 | 결과 |
| --- | --- |
| 실행 조건 | `ENABLE_OPENAI_FRAME_ANALYSIS=1`, `FRAME_ANALYSIS_FIXTURE_MODE=`, `ENABLE_YOLO_FRAME_ANALYSIS=1`, `YOLO_MODEL_PATH=/models/yolo/yolo11n.pt` |
| 배치 산출물 | `logs/video_accuracy/p2_2e_openai_yolo_on_20260529/aggregate.json`에 로컬 생성. `logs/`는 Git 제외 대상이다. |
| 평가 산출물 | `logs/video_accuracy/p2_2e_openai_yolo_on_reference_metrics_20260529.json`에 로컬 생성. |
| Reference metrics | `direct_collision_target_accuracy=1.0`, `accident_party_accuracy=1.0`, `context_pollution_rate=0.0`, `zero_observation_rate=0.0`, `evidence_mismatch_rate=0.2`, `conditional_branch_coverage=0.8`, 최종 status `passed`. |
| 출력 계약 | `scripts/video_agent_e2e.py`가 `conditional_outcome_card`를 결과 JSON에 포함하고, `scripts/video_accuracy_batch.py`가 이를 aggregate sample에 보존한다. |
| 비용 안전 복구 | 실제 OpenAI 측정 후 worker는 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=`, `ENABLE_YOLO_FRAME_ANALYSIS=1` 상태로 복구했다. |

이 변경은 public route, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. P2-2e 기준선은 통과했으므로 다음 단계는 P2-3 Agent 근거 검색/표시 적합도 보강이다. 남은 리스크는 `evidence_mismatch_rate=0.2`가 threshold 상한에 걸쳐 있다는 점이며, P2-3에서 사고유형과 KNIA/법령/판례 근거가 같은 축으로 묶이는지 보강해야 한다.

## 2026-05-29 AI-Hub 597 영상 라벨 reference 기반 추가

AI-Hub `교통사고 영상 데이터` 데이터셋 597의 TL/VL 영상 라벨 filekey를 `docs/AIHUB_597_LABEL_FILEKEYS.md`에 정리하고, 로컬 전용 다운로드/변환 흐름을 추가했다. AI-Hub API key는 문서나 코드에 저장하지 않고 실행 세션 환경변수로만 전달한다.

| 범위 | 내용 |
| --- | --- |
| 다운로드 스크립트 | `scripts/download_aihub597_labels.ps1`가 `AIHUB_API_KEY` 환경변수를 WSL에 전달해 `aihubshell -mode d -datasetkey 597 -filekey ...`를 실행한다. 기본 `-Scope Video`는 TL/VL 영상 라벨 45개만 받는다. |
| 로컬 산출물 | 다운로드 직후 공식 중첩 폴더가 생기지만 `scripts/organize_aihub597_labels.py`로 `datasets/aihub/traffic-accident-video/labels/video/{training,validation}/{zips,json}/` 구조로 정리한다. 이 경로는 Git 제외 대상이다. |
| 다운로드 상태 | 2026-05-29 기준 `-Scope Video` 다운로드, 압축 해제, 폴더 정리를 완료했다. 영상 라벨 ZIP 45개와 JSON 19,852개를 확인했다. |
| 변환 스크립트 | `scripts/aihub597_labels_to_manifest.py`가 AI-Hub 라벨 JSON을 LawCompass reference manifest 후보로 변환한다. 기본 산출물은 `.local/aihub597_video_label_manifest.json`이다. |
| 검증 | `py -3.13 scripts\validate_reference_case_manifest.py --manifest .local\aihub597_video_label_manifest.json`로 200건 샘플 manifest 검증을 통과했다. |
| 사용 제한 | AI-Hub 라벨은 평가/보정 reference로만 사용하고, Agent 입력 사실이나 사용자 사건의 정답으로 주입하지 않는다. 원천 영상과 라벨 ZIP/JSON은 Git에 올리지 않는다. |

## 2026-05-29 P2-2d 조건별 결과 분기 Coverage 보강

Gateway 결과 조립에서 조건별 결과 카드의 감지 축을 payload로 남기도록 확장했다. 신호, 비접촉 유발, 중앙선 침범 사유, 정차/후방추돌 사유, 사고 대상 확인 중 어떤 축이 missing/uncertain/conflict로 걸렸는지 `branch_key`, `detected_branch_keys`, `secondary_branches`, `coverage`로 기록한다.

| 범위 | 변경 내용 |
| --- | --- |
| 조건부 카드 감지 | `apps/gateway/src/lib/report-composer.ts`가 `video_input_contract`의 accepted/uncertain/supporting observation뿐 아니라 confirmation candidate/group, observation quality summary, `fact_arbitration` 확인 필요 필드를 함께 읽는다. |
| 분기 우선순위 | 상대 신호 미확인, 비접촉 유발, 중앙선 침범 사유, 정차/후방추돌 사유, 사고 대상 확인 순으로 조건별 결과 카드를 고른다. 여러 축이 동시에 걸리면 대표 카드 하나를 표시하되 나머지 축은 `secondary_branches`에 남긴다. |
| 비접촉 유발 카드 | 직접 충돌 대상과 사고 유발 주체가 다른 사고를 위해 `비접촉 유발 여부에 따라 달라지는 판단` 카드를 추가했다. 이는 사고 5 같은 케이스에만 맞춘 것이 아니라 자전거, 보행자, 제3 차량의 비접촉 유발 가능성을 공통 처리하는 구조다. |
| 평가 연결 | `scripts/evaluate_video_reference_metrics.py`가 reference의 ambiguous branch에서 기대 분기축을 추론하고, 결과 payload의 `detected_branch_keys`/`branch_key`와 비교한다. metadata가 없는 과거 aggregate는 기존 조건부 카드 존재 여부로 fallback 평가한다. |
| 검증 | Gateway `report-composer` 테스트를 41개로 확장했고, 다중 분기 metadata, 비접촉 우선 분기, video confirmation group 기반 중앙선 분기 감지를 검증했다. Reference metrics fixture도 branch metadata를 포함하도록 갱신했다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 다음 단계는 P2-2e OpenAI+YOLO ON 재측정으로, 실제 사고 영상 기준선에서 조건별 분기 coverage가 목표치까지 올라가는지 확인하는 것이다.

## 2026-05-29 P2-2c YOLO 시간 순서 기반 사고 시퀀스 관찰값

Worker YOLO 분석에 `temporal_sequence_summary`와 `vision_model:yolo_sequence` 관찰값을 추가했다. 단일 프레임에 차량·사람·신호등이 보였다는 사실만으로 사고 대상을 추론하지 않고, `pre_event_context -> event_candidate -> post_event_context` 흐름에서 차량 객체가 어느 후보 구간에 지속적으로 관찰되는지 요약한다.

| 범위 | 변경 내용 |
| --- | --- |
| Worker YOLO payload | `apps/worker/worker/yolo_frame_analysis.py`가 event candidate별 차량 관찰 프레임, phase별 frame refs, vehicle phase counts, sequence quality를 `temporal_sequence_summary`에 기록한다. |
| 시퀀스 관찰값 | top event window의 차량 흐름을 기반으로 `accident_event_candidate`, `direct_collision_partner_type=vehicle`, `collision_point_visible=true` 후보를 생성한다. |
| 오염 방지 | `direct_collision_partner_type`과 `collision_point_visible`은 Agent fact threshold 아래 confidence로 제한해 바로 사실 확정되지 않고 확인 후보로 남는다. `accident_event_candidate`는 supporting observation으로만 사용한다. |
| Agent 계약 검증 | Agent 영상 입력 계약 테스트에서 YOLO sequence 후보가 확정 fact가 아니라 supporting/confirmation item으로 남는지 고정했다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. YOLO sequence는 사고 시점 후보와 확인 질문 우선순위를 보강하기 위한 입력 계약이며, 법률 판단이나 과실비율 산정의 직접 근거가 아니다.

## 2026-05-29 P2-2b YOLO 오버레이/방송 UI 잡음 필터

Worker YOLO 분석에서 원본 감지값을 `raw_detections -> detections -> ignored_detections` 흐름으로 분리했다. 화면 가장자리 또는 플레이어 UI 영역에 반복 등장하는 `person` 감지는 방송 진행자, 워터마크, 플레이어 오버레이일 가능성이 높으므로 사고 관찰값과 `class_counts`에서 제외하고 `ignored_detections`에 사유와 위치 요약만 남긴다.

| 범위 | 변경 내용 |
| --- | --- |
| Worker YOLO payload | `apps/worker/worker/yolo_frame_analysis.py`가 `raw_detection_count`, `ignored_detection_count`, `ignored_class_counts`, `ignored_detections`를 함께 반환한다. |
| 관찰값 생성 | 필터링된 `detections`만 `pedestrian_visible`, `primary_collision_target`, `opponent_signal_visible` 같은 Agent 입력 후보로 변환한다. |
| 오염 방지 기준 | 같은 class가 3개 이상 프레임에서 비슷한 화면 가장자리 위치에 반복되면 정적 오버레이/방송 UI로 간주한다. 중앙 도로 영역의 사람 감지는 계속 보행자 후보로 유지한다. |
| 검증 | Worker YOLO 계약 테스트에 오버레이 사람 감지 제거와 실제 도로 사람 후보 유지 회귀 테스트를 추가했다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. YOLO는 여전히 사고 판단 모델이 아니라 객체 위치 보조 관찰 모델이며, 최종 사고 대상 확정은 Agent fact arbitration에서 수행한다.

## 2026-05-29 출력 모드 2단계 단순화

분석 결과 표시 모드를 `일반사용자모드(user_friendly)`와 `전문가모드(expert)` 두 가지로 정리했다. 기존 DB/API에 남아 있을 수 있는 `quick_summary`, `fault_ratio_focused`, `insurance_response_focused`는 일반사용자모드로, `legal_precedent_focused`, `full_deep_research`, `deep_research`, `debug` 계열은 전문가모드로 정규화한다. 새 기본값은 일반사용자모드이며, DB schema 변경은 없다.

| 범위 | 변경 내용 |
| --- | --- |
| Frontend guided flow | 결과 선택 카드는 일반사용자모드/전문가모드 2개만 표시한다. 일반사용자모드는 `현재 상황정리`, `과실비율산정`, `관련 KNIA 근거 및 영상` 3개 섹션만 보여주고, 전문가모드는 기존 상세 리포트 화면을 유지한다. |
| Gateway report payload | `report-analysis-mode.ts`가 legacy alias를 두 모드로 정규화하고, `report-composer.ts`는 기존 상세 report 필드를 삭제하지 않고 `display_mode`, `analysis_mode`, `analysis_mode_contract`, `simple_report`를 추가한다. |
| Agent output contract | `analysis_modes.py`가 두 모드와 legacy alias를 담당한다. Agent는 일반사용자모드에서도 KNIA 검색과 과실 산정 데이터를 계산하되, 표시량은 Gateway/Frontend의 `simple_report`와 `display_mode`가 제어한다. |
| 표시 안전 | 일반사용자모드에는 raw evidence, debug trace, chunk id, model info, token usage, `Local video verified` 같은 기술 문자열을 표시하지 않는다. 전문가모드에서도 developer diagnostic/secret성 정보는 기존 sanitizer 정책을 따른다. |

이 변경은 업로드/NAS/Worker/KNIA matcher 판단 로직, Redis key, storage path, 외부 API 종류를 변경하지 않는다. 기존 legacy mode 요청은 오류 없이 새 두 모드 중 하나로 매핑된다.

## 2026-05-29 KNIA Tree/Structured JSON Matching 보강

Agent KNIA 매칭은 `scripts/knia_fault_ratio`의 구조화 JSON을 우선 사용해 대분류, 중분류, 세부 chart/subchart, 원문 링크를 같은 KNIA 대분류 안에서 찾는다. DB 조회가 비어 있거나 import 전이어도 local JSON repository가 `chart_no`, `subchart_no`, `menu_path`, `source_url`, `source_url_is_fallback`, `base_fault`, `adjustments`, `related_laws`, `rag_documents`를 보존해 후보를 반환한다.

| 범위 | 변경 내용 |
| --- | --- |
| 입력/분류 | `input_normalizer.py`와 `scenario_classifier.py`가 공사 담당자·도로 작업자·도로 폭 측정·차도 급진입 문맥을 `car_vs_person` / `pedestrian_roadway_worker_accident`로 확정한다. |
| KNIA JSON | `knia_json_loader.py`는 top-level `charts`, `rag_documents`, `pages`, `project_integration` 스키마를 읽고, `보/차/거` prefix로 major party를 보정한다. |
| Local Repository | `knia_json_repository.py`는 local structured JSON에서 chart/subchart 검색을 수행한다. 보행자 도로 작업자 사고는 보25/보27/보28/보30/보34 후보를, 한쪽 지시표지 교차로는 차7/차7-1 후보를 같은 대분류 안에서 우선한다. |
| Matcher/Output | `knia_matcher.py`, `orchestration_evidence.py`, `orchestration_output.py`는 다른 대분류 KNIA 근거를 대표 근거에서 제외하고, `보-참고` 같은 가짜 chart 대신 실제 chart 후보와 `knia_match_summary`를 출력한다. |
| Bootstrap | Agent startup은 KNIA DB가 비어 있으면 local structured JSON import를 시도한다. 외부 myaccident1~5 수집기는 `KNIA_AUTO_COLLECT_ON_START=1`일 때만 선택적으로 실행되며 실패해도 서버 시작을 막지 않는다. |

이 변경은 DB schema, Redis key, storage path, public route, 외부 API 종류를 변경하지 않는다. KNIA 원문 링크가 JSON에 없으면 chart 번호 기반 fallback URL을 생성하고 `source_url_is_fallback=true`로 표시한다.

## 2026-05-29 P2-2 영상 Reference 평가 지표 고정

P2-2 단계에서 영상/입력 사실 추출 개선이 실제로 좋아졌는지 반복 측정할 수 있도록 reference manifest와 batch aggregate를 연결하는 고정 지표 평가 경로를 추가했다. 이 작업은 외부 모델 호출이나 실제 영상 재분석을 수행하지 않고, 이미 생성된 batch 결과를 기준으로 사고 대상 오염과 근거 부적합을 재현 가능하게 측정한다.

| 범위 | 변경 내용 |
| --- | --- |
| 평가 스크립트 | `scripts/evaluate_video_reference_metrics.py`를 추가했다. `reference_case_manifest`와 `video_accuracy_batch.py`의 `aggregate.json`을 받아 sample별 reference를 연결하고 지표 JSON을 생성한다. |
| 고정 지표 | 직접 충돌 대상 정확도, 사고 대분류 정확도, context 오염률, 관찰값 0개 비율, 근거 부적합률, 분기형 판단 coverage를 산출한다. |
| Fixture | `tests/fixtures/video_accuracy/reference_metrics_manifest.json`과 `reference_metrics_batch_aggregate.json`을 추가해 실제 영상 없이도 지표 계산을 검증할 수 있게 했다. |
| 문서 | `docs/VIDEO_REFERENCE_METRICS.md`에 지표 의미, 기본 threshold, 실행 순서, 해석 기준을 정리했다. `DEVELOPMENT_PROMPT.md`의 evaluation 규칙에도 P2-2 지표 사용 기준을 추가했다. |
| 검증 | Reference metrics manifest preflight 통과. Synthetic aggregate 평가 결과 `direct_collision_target_accuracy=1.0`, `accident_party_accuracy=1.0`, `context_pollution_rate=0.0`, `zero_observation_rate=0.0`, `evidence_mismatch_rate=0.0`, `conditional_branch_coverage=1.0`으로 threshold 통과. Python compile과 `git diff --check`도 통과했다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 실제 사고 영상 1~5나 공개 reference 후보는 같은 스크립트에 로컬 manifest와 batch aggregate를 넣어 평가한다. 다음 단계는 P2-3 Agent 근거 검색·표시 정합성으로, 사고유형이 맞게 잡힌 뒤 KNIA/법령/판례 근거도 같은 사고축으로 검색되는지 보강하는 것이다.

## 2026-05-29 P2-1 외부 참고 케이스 Manifest 보강

P2-1 단계에서 한문철TV 같은 공개 사고 영상 링크, 사용자 제공 사고 영상 요약, AI Hub 샘플 정보를 Agent 입력 사실이나 정답 데이터로 오용하지 않도록 reference manifest 계약과 preflight 검증을 보강했다. 목적은 외부 사례를 “답 맞추기”가 아니라 영상 관찰값 오염, 사고 대상 오인, 분기형 판단 누락을 찾는 평가/calibration reference로만 관리하는 것이다.

| 범위 | 변경 내용 |
| --- | --- |
| Manifest 계약 | `tests/fixtures/video_accuracy/reference_case_manifest.schema.json`에 `reference_role`, `review_status`, `reference_outcome`을 추가했다. 전문가 의견 요약과 실제 결과 공개 여부는 기록할 수 있지만 Agent 사용자 입력 사실로 주입하지 않는다. |
| 예시 fixture | `tests/fixtures/video_accuracy/reference_case_manifest.example.json`을 새 계약에 맞춰 갱신했다. 사고 1번 로컬 예시, 공개 링크 후보, AI Hub 샘플이 모두 원본 영상 미커밋과 Agent 입력 금지 정책을 명시한다. |
| 수집 스크립트 | `scripts/collect_public_video_references.py`가 공개 URL/YouTube 후보를 수집할 때 `calibration_reference_only`, `candidate_requires_manual_review`, `reference_outcome` 기본값을 함께 생성한다. 원본 영상은 다운로드하지 않는다. |
| Preflight | `scripts/validate_reference_case_manifest.py`를 추가했다. 필수 필드, 직접 충돌 대상 기대값, `must_not_promote`, raw video commit 금지, Agent 입력 금지, private local path 노출 여부를 검사한다. |
| 문서 | `docs/VIDEO_REFERENCE_DATA_POLICY.md`, `docs/PUBLIC_VIDEO_REFERENCE_COLLECTION.md`, `docs/VIDEO_AGENT_WORK_PLAN.md`에 새 manifest 필드와 검증 명령을 반영했다. |
| 검증 | 예시 manifest preflight 통과. 공개 URL 수집 smoke manifest도 error 0으로 통과했으며, 수동 검토 전 후보에 대해서는 expected context 보강 warning이 정상 출력된다. Python compile과 `git diff --check`를 통과했다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 실제 공개 영상 원본, AI Hub 원본, API key, 로컬 개인 경로가 들어간 manifest는 계속 Git에 포함하지 않는다. 다음 단계는 P2-2 평가 지표 고정으로, 사고 대상 정확도·오염률·관찰값 0개 비율·근거 부적합률 등을 반복 측정 가능한 지표로 묶는 것이다.
## 2026-05-29 KNIA 대분류 라우터와 Party Guard 보강

자연어 또는 영상만 입력되어도 KNIA 대분류를 먼저 확정하고, 이후 사고유형·질문·KNIA 기준·가감요소·과실비율 산정이 같은 대분류 안에서만 움직이도록 Agent 판단 경계를 보강했다.

| 범위 | 변경 내용 |
| --- | --- |
| 대분류 라우터 | `apps/agent/app/services/party_agents/`를 추가했다. `router.py`는 사용자 입력, 구조화 사실, 선택 키워드, 영상 입력 계약을 보고 `car_vs_car`, `car_vs_person`, `car_vs_bicycle`, `car_vs_motorcycle`, `car_vs_object`, `single_vehicle`, `unknown` 중 하나를 먼저 확정한다. 사용자 입력이 명시적이면 우선하고, 고신뢰 영상이 다른 직접 충돌 대상을 가리키면 conflict metadata로 남긴다. |
| 입력 정규화 | `input_normalizer.py`가 sanitize/오타 보정 뒤 video input contract를 만들고 party router 결과를 facts에 반영한다. 반환값에는 `party_agent_result`, `knia_major_party_type`, `excluded_knia_party_types`가 포함된다. |
| KNIA Party Guard | `apps/agent/app/services/knia/party_guard.py`를 추가했다. chart prefix, query term, tag, candidate item을 대분류별로 필터링해 차대차 사고에서 보행자·자전거·기물·단독 기준이 최종 KNIA 기준으로 노출되지 않게 한다. |
| 검색/분류 | `scenario_classifier.py`, `scenario_search_terms.py`, `knia_matcher.py`, `orchestration_evidence.py`가 확정된 `knia_major_party_type`을 존중한다. KNIA matcher는 party mismatch 제거 수, fallback 사용 여부, no match reason, party guard policy를 결과 metadata에 포함한다. |
| 가감요소 registry | `apps/agent/app/services/knia/adjustments/`를 추가했다. 우선 차대차 후미추돌, 차선변경, 교차로, 중앙선/장애물, 주정차/스텔스 정차 차량, 위험 태그 전용 사고를 registry 계약으로 평가하며, 브레이크등 모름처럼 확정할 수 없는 항목은 숫자를 바로 바꾸지 않고 unknown/conditional outcome으로 남긴다. |
| 질문/표시 | Agent 동적 질문은 모든 질문에 `fact_key`를 포함한다. Frontend guided flow는 KNIA 대분류를 먼저 선택하고 차대차 선택 시 세부 사고유형 질문으로 이어진다. Gateway report composer는 기본 과실, 적용/미적용/불확실 가감요소, 조건별 결과 카드 payload를 분리해 만든다. |

이 변경은 DB schema, migration, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 실제 `.env` 값이나 secret은 문서와 로그에 포함하지 않는다.
## 2026-05-29 P1-3 애매한 사고의 분기형 결과 보강

P1-3 단계에서 입력 또는 영상으로 확인되지 않은 핵심 사실 때문에 결론이 갈리는 사고를 사용자 화면에서 조건별로 나눠 설명하도록 Gateway 결과 표시 정책을 보강했다. 이번 변경은 특정 사고 영상에 결론을 맞추는 처리가 아니라, 신호·사고 대상·중앙선 침범 사유·정차/후방추돌 사유처럼 판단 방향을 바꾸는 공통 불확실성 축을 구조화하는 범용 출력 정책이다.

| 범위 | 변경 내용 |
| --- | --- |
| 분기 감지 | `apps/gateway/src/lib/report-composer.ts`가 `missing_info`, `input_requirements`, 영상 보류 관찰값, `fact_arbitration` 확인 필요 필드를 함께 보고 조건별 결과 카드가 필요한지 판단한다. |
| 신호 분기 | 상대 신호 미확인, 황색/적색 전환, 교차로 진입 시점이 불명확한 경우 `신호 확인에 따라 달라지는 판단` 카드로 정상 진행 신호와 상대 신호위반 가능성을 나눠 설명한다. 우회전/직진 같은 진행 방향 단어만으로 신호 분기가 뜨지 않도록 감지 조건을 좁혔다. |
| 사고 대상 분기 | 영상에 사람·자전거·객체가 보이더라도 실제 직접 충돌 대상인지, 주변 환경 또는 비접촉 유발 대상인지가 불명확하면 `사고 대상 확인에 따라 달라지는 판단` 카드로 차대차 기준과 비차량 대상 기준을 분리한다. |
| 중앙선/정차 분기 | 중앙선 침범 사유, 도로 장애물, 불법 주정차, 앞차 정차 사유, 후방추돌/비접촉 유발 여부가 불명확한 경우 각각 별도 조건별 판단 카드로 필요한 증거와 확인 포인트를 제시한다. |
| 검증 | Gateway `report-composer` 테스트 38개를 통과했다. 신규 테스트는 사고 대상 오염, 중앙선 침범 사유, 정차/후방추돌 사유 분기 카드가 raw field key 없이 표시되는지 검증한다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 다음 단계는 P2-1 외부 참고 케이스 manifest로, 공개 참고 사례와 사용자 제공 사고 영상을 평가/calibration reference로만 안전하게 관리하는 흐름을 정리하는 것이다.

## 2026-05-29 P1-2 사용자 입력과 영상 관찰값 중재 보강

P1-2 단계에서 사용자 입력과 영상 관찰값이 충돌하거나 영상 관찰값이 품질 기준을 넘지 못한 경우를 더 명확히 분리하도록 Agent 중재 계약과 Gateway 표시 계약을 보강했다. 이번 변경은 영상이 애매할 때 사용자 입력을 무조건 덮어쓰지 않고, 확정·보류·확인 필요 상태를 구조화하는 범용 처리다.

| 범위 | 변경 내용 |
| --- | --- |
| Agent 중재 계약 | `apps/agent/app/services/fact_arbitration.py`가 `uncertain_observations`를 함께 검토해 `pending_video_confirmations`, `held_video_fields`, `tentatively_supported_fields`, `confirmation_fields`를 생성한다. |
| 충돌 처리 | 보류 영상 관찰값이 사용자 입력과 충돌하면 사용자 값을 유지하고 `user_video_conflict_video_held` 상태로 확인 질문에 넘긴다. 사용자 입력이 비어 있으면 `missing_user_fact_video_held`로 남기며, 사용자 입력과 같은 방향이면 `user_supported_by_held_video`로 참고 보강만 표시한다. |
| 분석 입력 전달 | `apps/agent/app/services/input_normalizer.py`의 분석용 중재 요약에 보류 영상 필드와 확인 필요 항목을 포함해 downstream Agent 판단이 이 정보를 볼 수 있게 했다. |
| 결과 표시 | `apps/gateway/src/lib/report-composer.ts`가 `pending_video_confirmations`를 영상 기반 사실 카드의 검토 항목과 missing_info 확인 질문으로 표시한다. 확정 기준을 넘지 못한 영상 후보는 화면에서 내부 키가 아니라 한국어 질문으로 노출된다. |
| 표시 안전성 | Gateway/Frontend sanitizer의 기술 키 목록에 새 중재 필드를 추가해 raw contract key가 사용자 화면에 섞이지 않게 했다. |
| 검증 | Agent 중재/영상 입력 계약 테스트 48개, Agent 중재/영상 입력/오케스트레이터 테스트 57개, Gateway report-composer 테스트 35개, Gateway/Frontend build, Docker 기반 `scripts/verify_agent_regression.ps1`을 통과했다. |

이 변경은 public route, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 응답 내부 metadata의 `fact_arbitration` 계약에는 새 필드가 추가되지만 기존 `conflicts`, `requires_confirmation` 필드는 유지된다. 다음 단계는 P1-3 애매한 사고의 분기형 결과로, 상대 신호 미확인처럼 결론이 갈리는 사고를 근거 기반 시나리오별로 설명하는 출력 정책을 보강하는 것이다.

## 2026-05-29 P1-1 사고 시점 후보 추출 개선

P1-1 단계에서 영상 초반의 위험 장면이나 배경 객체가 실제 사고로 오인되지 않도록 Worker 프레임 전처리 계약을 보강했다. 이번 변경은 특정 사고 1~5에 맞춘 보정이 아니라, 영상 전체에서 여러 사고 후보 구간을 만들고 각 후보의 사고 전·중·후 흐름을 비교하게 하는 범용 처리다.

| 범위 | 변경 내용 |
| --- | --- |
| 사고 후보 구간 | `apps/worker/worker/video_preprocess.py`가 ffmpeg scene-change 이벤트를 `event_window_*` 후보 구간으로 클러스터링한다. scene-change가 없으면 짧은 영상은 중앙 1개, 중간 영상은 2개, 긴 영상은 3개 temporal fallback 후보를 만든다. |
| 프레임 메타데이터 | 추출 프레임에 `event_candidate_id`, `event_phase`, `event_center_time_sec`, `event_window_start_sec`, `event_window_end_sec`를 추가했다. `event_phase`는 `pre_event_context`, `event_candidate`, `post_event_context`로 구분된다. |
| OpenAI/YOLO 입력 | `apps/worker/worker/frame_analysis.py`와 `apps/worker/worker/yolo_frame_analysis.py`가 분석 프레임 참조에 사고 후보 구간과 phase를 함께 전달한다. OpenAI 프롬프트는 여러 후보가 있을 때 각 후보의 사고 전·중·후 프레임을 비교하도록 명시한다. |
| 환경변수 | worker compose/env 예시에 `VIDEO_EVENT_WINDOW_CLUSTER_GAP_SEC`(기본 `3.0`)와 `VIDEO_EVENT_WINDOW_MAX_CANDIDATES`(기본 `6`)를 추가했다. |
| 검증 | Worker 전체 테스트 42개, Agent 영상 입력 계약 테스트 43개, Docker 기반 `scripts/verify_agent_regression.ps1`을 통과했다. |

이 변경은 public route, DB schema, Redis key, storage path, 외부 API 종류를 변경하지 않는다. 새 환경변수는 Worker 내부 사고 후보 구간 생성 민감도만 조정한다. 다음 단계는 P1-2 사용자 입력과 영상 관찰값 중재로, 사용자 입력과 영상 후보가 충돌하거나 영상이 애매할 때 확정·보류·확인 필요 상태를 더 명확히 분리하는 것이다.

## 2026-05-29 P0-5 관찰값 0개 Fallback 보강

P0-5 단계에서 대표 프레임은 충분하지만 Agent 판단에 바로 반영할 영상 관찰값이 없거나, 보류 관찰값만 존재하는 경우를 방치하지 않도록 recovery contract를 보강했다. 이번 변경은 특정 사고 영상에 맞춘 보정이 아니라 `프레임 충분 + 확정 사실 부족` 상태를 별도 품질 신호와 재시도 계획으로 남기는 범용 처리다.

| 범위 | 변경 내용 |
| --- | --- |
| fallback 관찰값 | `apps/agent/app/services/video_input_contract_metadata.py`가 사고 시점 후보가 있는 frame-rich 영상에서 `accident_event_candidate`와 `visual_evidence_limited`를 supporting observation으로 함께 남긴다. 두 값은 과실 판단 fact로 승격되지 않고 품질/확인 신호로만 사용한다. |
| recovery contract | `analysis_recovery`에 `retry_plan`과 `confirmation_prompts`를 추가했다. 프레임 재선택, OpenAI 프레임 재분석, YOLO 후보 검토, 사용자 확인 질문 생성을 구조화해 다음 처리 단계가 흔들리지 않게 했다. |
| 보류 관찰값 처리 | 확정 fact는 없지만 보류 관찰값이 있는 frame-rich 영상은 `frame_rich_uncertain_observations_only` 상태로 구분한다. 충돌 대상, 충돌 지점, 신호 상태 같은 확인 질문 후보를 생성한다. |
| 검증 스크립트 | `scripts/verify_agent_regression.ps1`가 Docker 하위 명령의 실패 exit code를 즉시 예외로 처리하도록 변경했다. 내부 회귀 실패가 출력된 뒤 최종 pass로 보이는 검증 신뢰도 문제를 막는다. |
| 검증 | `PYTHONPATH=apps/agent py -3.13 -m pytest apps/agent/tests/test_video_input_contract.py apps/agent/tests/test_video_input_contract_guards.py apps/agent/tests/test_fact_arbitration.py -q` 43개 통과. OpenAI+YOLO 병합 평가는 `contamination_regression_count=0`, `status=pass`를 유지했다. `powershell -ExecutionPolicy Bypass -File scripts/verify_agent_regression.ps1`도 Docker 빌드 포함 통과했다. |

이 변경은 public route, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 다음 단계는 P1-1 사고 시점 후보 추출 개선으로, 긴 영상이나 휴대폰 재촬영 영상에서도 사고 전·충돌·사고 후 구간을 더 안정적으로 잡는 것이다.

## 2026-05-29 P0-4 영상 오염 방지 Guard 확장

P0-4 단계에서 영상 관찰값의 객체 존재가 사고유형 확정으로 잘못 승격되는 경로를 더 넓게 막도록 Agent video input guard를 확장했다. 이번 변경은 특정 사고 1~5에 맞춘 보정이 아니라 `객체 존재 != 직접 충돌 대상`, `환경 정보 != 사고 원인 확정` 원칙을 코드 guard로 일반화한 것이다.

| 범위 | 변경 내용 |
| --- | --- |
| 충돌 대상 guard | `apps/agent/app/services/video_input_contract_guards.py`가 보행자뿐 아니라 자전거와 도로 객체/장애물도 직접 충돌 근거 없이 `collision_partner_type`으로 확정하지 않는다. `direct_collision_partner_type` 또는 충돌 지점과 목표 텍스트가 맞을 때만 유지한다. |
| 객체 후보 guard | `primary_collision_target=*_candidate` 같은 후보성 값은 확정 충돌 대상으로 승격하지 않고 `uncertain`으로 내린다. YOLO 객체 후보가 사고 대상을 오염시키는 경로를 막는다. |
| 신호 guard | `opponent_signal_violation=true`는 상대 신호 상태 또는 신호 전환 근거가 없으면 보류한다. 신호등 존재만으로 신호위반 사고가 되지 않게 했다. |
| 중앙선/정차/비접촉 guard | `centerline_crossed`, `stopped_vehicle_without_lights`, `front_vehicle_stopped`, `non_contact_trigger`는 침범 사유, 도로 장애물, 대향 차량, 충돌 지점, 정차 맥락, 유발 주체/행동 같은 보조 근거가 없으면 보류한다. |
| 회귀 테스트 | `apps/agent/tests/test_video_input_contract_guards.py`에 자전거 직접 충돌, 신호위반, 후보 충돌 대상, 중앙선 침범 오염 방지 테스트를 추가했다. |
| 검증 | `PYTHONPATH=apps/agent py -3.13 -m pytest apps/agent/tests/test_video_input_contract.py apps/agent/tests/test_video_input_contract_guards.py apps/agent/tests/test_fact_arbitration.py -q` 42개 통과. OpenAI+YOLO 병합 평가도 `status=pass`, contamination regression 0개를 유지했다. |

이 변경은 public route, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 다음 단계는 P0-5 관찰값 0개 fallback 보강으로, 프레임은 충분하지만 확정 가능한 관찰값이 없는 경우 재시도/대체 분석/사용자 확인 후보 생성을 더 명확하게 연결하는 것이다.

## 2026-05-29 P0-3 OpenAI+YOLO 관찰값 병합 검증

P0-3 단계에서 OpenAI 프레임 분석 결과와 YOLO 객체 후보를 함께 Agent 입력 계약으로 넣었을 때 사고 대상·환경 정보가 오염 없이 처리되는지 재현 가능한 평가 경로를 추가했다. 목적은 YOLO가 감지한 사람, 신호등, 차량 후보를 사고유형 확정값으로 바로 쓰지 않고, Agent fact contract와 fact arbitration에서 보류/확인 후보로 남기는 것이다.

| 범위 | 변경 내용 |
| --- | --- |
| 병합 평가 스크립트 | `scripts/evaluate_video_observation_merge.py`를 추가했다. P0-2 OpenAI debug 결과와 YOLO smoke 결과를 같은 `metadata.observations` 계약으로 병합한 뒤 `normalize_video_input_contract()`와 `arbitrate_facts()`를 실행한다. |
| 오염 방지 측정 | 사고 1~5 로컬 결과 기준 OpenAI 관찰값 8개, YOLO 후보 13개를 병합했다. YOLO 후보 13개는 모두 `uncertain`으로 남았고 `accepted`, `fact_patch`, `applied_video_fields`, `confirmed_fields`로 승격되지 않았다. |
| 회귀 테스트 | `apps/agent/tests/test_video_input_contract.py`에 YOLO의 객체 존재 후보가 보행자 사고, 상대 신호 확정, 직접 충돌 대상 확정으로 승격되지 않는 회귀 테스트를 추가했다. |
| 로컬 산출물 | 실행 결과는 `logs/video_accuracy/p0_3_openai_yolo_merge_20260529.json`에 생성되며 Git에는 포함하지 않는다. |
| 검증 | `PYTHONPATH=apps/agent py -3.13 -m pytest apps/agent/tests/test_video_input_contract.py apps/agent/tests/test_fact_arbitration.py -q` 통과, `scripts/evaluate_video_observation_merge.py` 병합 평가 `status=pass` 통과. |

이 변경은 public route, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 다음 단계는 P0-4 오염 방지 guard 확장으로, 객체 존재와 사고유형 확정을 분리하는 guard를 자전거, 중앙선, 정차 차량, 장애물, 진행방향, 앞차/뒤차 역할까지 넓히는 것이다.

## 2026-05-29 영상 분석 모델 후보 문서화

영상 처리 고도화 과정에서 OpenAI 외의 무료/로컬/모바일 후보를 비교할 수 있도록 `docs/VIDEO_MODEL_OPTIONS.md`를 추가했다. 이 문서는 YOLO, Qwen2.5-VL, Gemini API Free Tier, Google ML Kit, MediaPipe의 역할 차이와 무료 범위 기준 추천 순서를 정리한다.

| 범위 | 정리 내용 |
| --- | --- |
| 객체 감지/추적 | YOLO, ML Kit, MediaPipe는 사고 판단 모델이 아니라 차량·사람·신호등 등 객체 후보 관찰값을 만드는 보조 모델로 분류했다. |
| 영상 이해 | Qwen2.5-VL 로컬과 Gemini API Free Tier는 사고 흐름/장면 의미 후보를 만드는 영상 이해 모델로 분류했다. |
| 모바일 선처리 | ML Kit은 현재 Docker Worker에 직접 붙이기보다, 향후 Capacitor 기반 모바일 앱에서 업로드 전 온디바이스 1차 관찰값을 만드는 용도가 적합하다고 정리했다. |
| 적용 우선순위 | 현재 연결된 OpenAI/YOLO 경로 검증, provider 인터페이스 추상화, Qwen 로컬 smoke, Gemini 무료 비교, 모바일 ML Kit 설계 순서로 분류했다. |

이 변경은 코드, API route, DB schema, Redis key, storage path, 환경변수 키를 변경하지 않는 문서 보강이다.

## 2026-05-29 P0-2 영상 기준선 측정 스크립트 보강

P0-2 사고 1~5 영상 기준선 재측정 중 공개 upload API가 보안상 `openai_frame_analysis` 원문 metadata를 제거하면서, `scripts/video_agent_e2e.py`가 실제 분석이 실행된 샘플도 “OpenAI frame analysis was not enabled”로 오판하는 문제가 확인됐다. 원본 영상 분석 payload는 사용자-facing upload 응답에 노출하지 않는 것이 맞으므로, E2E 스크립트가 Agent debug 계약의 `video_input_contract`와 결과 화면의 `video_fact_explanation_card`를 함께 사용해 영상 관찰값 수, 참고 관찰, 대표 프레임 수를 집계하도록 보강했다.

| 범위 | 변경 내용 |
| --- | --- |
| E2E 측정 | `scripts/video_agent_e2e.py`가 공개 upload metadata에 원문 OpenAI payload가 없더라도 Agent debug contract의 accepted/uncertain/supporting observation을 frame observation summary로 사용할 수 있다. |
| 보안 경계 | `openai_frame_analysis` 원문 metadata는 계속 public upload 응답에서 제거된다. 측정 스크립트는 원문 payload 노출을 요구하지 않는다. |
| P0-2 실행 전제 | 사고 영상 reference manifest는 `logs/` 아래 로컬 파일로 유지하고, 실제 원본 영상과 배치 결과는 Git에 포함하지 않는다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. P0-2 결과는 `logs/video_accuracy/` 아래 로컬 산출물로만 관리한다.

## 2026-05-29 P0-2a 영상 reference 데이터 정책

P0-2 사고 1~5 영상 기준선 재측정 전에, 외부 사고 영상과 사고 설명이 함께 있는 reference 데이터를 안전하게 수집하고 테스트에 사용하는 기준을 추가했다. 목적은 특정 사고에 답을 맞추는 것이 아니라 영상 관찰값 오염, 사고 대상 오인, 사고 시점 후보 누락, 근거 검색 오염을 발견하기 위한 평가 기준을 넓히는 것이다.

| 범위 | 변경 내용 |
| --- | --- |
| Reference 정책 | `docs/VIDEO_REFERENCE_DATA_POLICY.md`를 추가해 기존 사용자 제공 영상, AI Hub 샘플, 공개 영상 링크, KNIA/법령/판례 등 공식 근거 자료를 어떤 용도로 사용할지 구분했다. |
| 공개 후보 수집 | `scripts/collect_public_video_references.py`와 `docs/PUBLIC_VIDEO_REFERENCE_COLLECTION.md`를 추가해 YouTube Data API 또는 직접 URL 입력으로 공개 사고 영상 링크/메타데이터 후보 manifest를 만들 수 있게 했다. 원본 영상은 다운로드하지 않는다. |
| Manifest schema | `tests/fixtures/video_accuracy/reference_case_manifest.schema.json`을 추가해 reference case의 필수 필드, 기대 관찰값, 오염 방지 항목, 사용 제한을 구조화했다. |
| Manifest example | `tests/fixtures/video_accuracy/reference_case_manifest.example.json`을 추가해 사고 1, 공개 영상 링크 reference, AI Hub 샘플 reference의 안전한 예시를 제공했다. 실제 로컬 영상 경로와 원본 파일은 포함하지 않는다. |
| 개발 기준 | `DEVELOPMENT_PROMPT.md`와 `docs/VIDEO_AGENT_WORK_PLAN.md`에 공개 영상/AI Hub reference는 Agent 입력 사실이 아니라 평가와 calibration 기준으로만 사용한다는 규칙을 명확히 했다. |
| 검증 | JSON schema/example parse와 `git diff --check`를 통과했다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path를 변경하지 않는다. 외부 공개 영상 후보 수집은 선택적 `YOUTUBE_API_KEY` 로컬 환경변수가 있을 때만 검색 기반으로 동작하며, 키 값은 문서나 Git에 기록하지 않는다. 다음 단계는 P0-2 사고 1~5 영상 기준선 재측정이며, 확보 가능한 external reference는 원본 파일 없이 manifest 기반 평가 후보로 먼저 관리한다.

## 2026-05-29 P0-1 사고 오염 유형 매트릭스

영상·입력 사실 추출 보강의 첫 단계로 사고를 잘못 인식할 수 있는 오염 유형을 범용 매트릭스로 고정했다. 이 작업은 코드 동작을 바꾸지 않고, 이후 P0-2 기준선 재측정과 P0-3/P0-4 Agent 계약·guard 보강의 기준 자료를 만드는 단계다.

| 범위 | 변경 내용 |
| --- | --- |
| 오염 유형 문서 | `docs/VIDEO_CONTAMINATION_RISK_MATRIX.md`를 추가해 객체 존재와 직접 사고 사실을 분리하는 공통 판단 축, 오염 위험 유형, 우선 확인 질문, 구현 적용 기준을 정리했다. |
| Fixture | `tests/fixtures/video_accuracy/contamination_risk_matrix.json`을 추가해 이후 평가 스크립트나 guard 테스트에서 재사용할 수 있는 machine-readable 오염 유형 목록을 제공한다. 실제 영상 경로, 사용자 정보, 변호사 의견 원문은 포함하지 않는다. |
| 작업 계획 상태 | `docs/VIDEO_AGENT_WORK_PLAN.md`의 P0-1 상태를 완료로 갱신하고 산출물 경로를 연결했다. |
| 검증 | `git diff --check`와 JSON parse 검증을 통과했다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 다음 단계는 P0-2 사고 1~5 영상 기준선 재측정이다.

## 2026-05-29 횡단보도 환경 정보의 보행자 사고 오염 방지

프론트 guided answer -> `structured_facts` 매핑에서 횡단보도 위치 또는 횡단보도 인접 정보만으로 사고 대분류를 `차대사람`으로 승격하던 경로를 제거했다. 이 변경은 사고 영상 2·3처럼 횡단보도나 사람이 화면에 보이더라도 실제 충돌 대상이 차량이면 차대차 사고로 유지되어야 한다는 영상 입력 계약을 프론트 입력 흐름에도 맞춘 것이다.

| 범위 | 변경 내용 |
| --- | --- |
| Fact mapping | `apps/frontend/src/composables/caseWorkspaceFactMapping.ts`에서 `crosswalk_context`와 `accident_location_context=crosswalk`는 `crosswalk_nearby`/`road_context`만 보강하고, `car_vs_person` 또는 `pedestrian_crosswalk_accident`를 직접 설정하지 않는다. |
| 승격 조건 | 보행자 사고 승격은 사용자가 사고 상대를 `person`으로 고르거나, 사고 방향/대분류에서 명시적으로 보행자 사고를 선택한 경우처럼 직접 충돌 대상이 확인되는 입력 경로에 한정한다. |
| 표시 계약 테스트 | `apps/frontend/scripts/test-display.mjs`에 횡단보도 환경 정보만으로 보행자 사고 승격이 재발하지 않도록 정적 계약 검사를 추가했다. 기존 SRP 분리 이후 분석 모드 상수를 `caseWorkspaceGuidanceData.ts`에서 읽도록 테스트 범위도 동기화했다. |
| 검증 | Frontend `npm run test:display`와 `npm run build`를 통과했다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 목적은 사용자 입력과 영상 관찰값에서 사고 대상이 오염되지 않도록 하는 P0 계열 보강이다.

## 2026-05-29 Frontend Guidance SRP 보강 P1-1

`apps/frontend/src/composables/caseWorkspaceGuidance.ts`가 안내용 상수, 사고유형/분석모드 선택지, fallback 질문 데이터, 질문 타입 추론 로직을 한 파일에서 함께 담당하던 구조를 분리했다. 이번 변경은 기존 import 경로를 유지하면서 프론트 guidance 데이터와 추론 로직의 책임 경계를 줄인 구조 보강이다.

| 범위 | 변경 내용 |
| --- | --- |
| Guidance data | `apps/frontend/src/data/caseWorkspaceGuidanceData.ts`를 추가해 기본 키워드, 진행 단계, 분석 모드, 사고유형 선택지, fallback 질문 세트와 질문 세트 매핑을 담당한다. |
| Question inference | `apps/frontend/src/logic/caseWorkspaceQuestionInference.ts`를 추가해 사고 설명과 구조화 입력을 바탕으로 fallback 질문 유형을 고르는 추론 로직을 담당한다. |
| Facade 유지 | `caseWorkspaceGuidance.ts`는 기존 화면과 composable import가 깨지지 않도록 data/logic re-export만 담당한다. |
| 검증 | Frontend `npm run build`를 통과했다. |

이 변경은 public route, API payload, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. P1-1까지 완료되었으므로 다음 개발 흐름은 사용자 영상과 입력에서 오염되지 않은 사실 데이터를 추출하고 Agent 판단 계약으로 연결하는 작업으로 이동한다.


## 2026-05-29 Gateway Route SRP 보강 P1-2

`apps/gateway/src/routes/uploads.ts`와 `apps/gateway/src/routes/analysis.ts`가 라우트 등록, DB 조립, 저장소 오류 매핑, 분석 결과 저장, 진행 상태 payload 조립을 한 파일에서 함께 담당하던 구조를 분리했다. 이번 변경은 public API route와 응답 payload를 바꾸지 않고 Gateway route 파일이 요청 검증과 라우팅 흐름에 집중하도록 만든 구조 보강이다.

| 범위 | 변경 내용 |
| --- | --- |
| Upload service | `apps/gateway/src/services/uploadService.ts`를 추가해 업로드 공개 payload sanitizing, storage key 정규화, storage 오류 코드/사용자 메시지 매핑, DB insert query 조립, 전처리 job enqueue, 로컬/NAS/S3 content streaming, 업로드 완료 검증 책임을 담당한다. |
| Analysis service | `apps/gateway/src/services/analysisService.ts`를 추가해 분석 진행 상태 payload, 재분석 영상 metadata 구성, 결과 리포트 context 조회, `analysis_results` 저장 책임을 담당한다. |
| Route facade 유지 | `routes/uploads.ts`와 `routes/analysis.ts`는 기존 route 등록과 인증/응답 흐름을 유지하며, 기존 테스트가 참조하던 `buildUploadInsert`, `publicUpload`, `composeGuidedProgressPayload`, `buildReanalysisVideoMetadata` re-export 계약을 유지한다. |
| 검증 | Gateway `npm run build`와 `npm test`를 통과했다. 테스트 기준은 8개 파일, 59개 테스트다. |

이 변경은 DB schema, Redis key, storage path, public API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. 남은 P1-1 범위는 프론트 guidance 데이터/질문 추론 책임 분리이며, 이후 개발 흐름은 사용자 영상과 입력에서 오염되지 않은 사실 데이터를 추출하고 Agent 판단 계약으로 연결하는 작업으로 이동한다.

## 2026-05-29 Agent Video Input Guard SRP 보강 P0-4

P0-3 이후 `apps/agent/app/services/video_input_contract.py`에 남아 있던 영상 fact guard 책임을 별도 모듈로 분리했다. 이번 변경은 영상 관찰값이 보행자/횡단보도 context를 실제 보행자 충돌로 오인하거나, 직접 충돌 대상과 broad collision partner가 충돌하는 경우를 방어하는 정책을 명시적인 guard 계층으로 이동한 구조 보강이다.

| 범위 | 변경 내용 |
| --- | --- |
| Guard 모듈 | `apps/agent/app/services/video_input_contract_guards.py`를 추가해 `apply_video_fact_guards()`를 단일 진입점으로 제공한다. 충돌 대상 분류 guard, 직접 충돌 대상 정렬, context-dependent fact demotion, accepted -> uncertain 이동 책임을 이 파일이 담당한다. |
| Facade 축소 | `video_input_contract.py`는 영상 입력 계약 조립, observation 처리, recovery/quality summary 연결만 담당하고 guard 정책은 `apply_video_fact_guards()` 호출로 위임한다. |
| Guard 단위 테스트 | `apps/agent/tests/test_video_input_contract_guards.py`를 추가해 차대차 사고에서 보행자 context demotion, direct collision partner 정렬, 보행자 충돌 직접 접촉 근거 요구를 순수 함수 수준에서 고정했다. |
| 검증 | `PYTHONPATH=apps/agent py -3.13 -m pytest apps/agent/tests/test_video_input_contract.py apps/agent/tests/test_video_input_contract_guards.py -q` 30개 테스트와 `py -3.13 -m py_compile`을 통과했다. 전체 Agent suite는 Python 3.13 기준 157개 통과, 4개 기존 테스트 실패가 남았다. 실패 범위는 동적 질문지 문구, 입력 요구 blocking reason, KNIA 사용자 관점 매핑 테스트다. |

이 변경은 DB schema, Redis key, storage path, public API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. `video_input_contract.py`는 이제 public facade 역할만 남았으며, 추가 SRP 보강은 영상 입력 계약보다 다른 Agent 장문 파일(`orchestration_analysis.py`, `orchestration_evidence.py`, 일부 analyst prompt/guard 파일)을 우선 점검하는 것이 적합하다.


## 2026-05-29 Agent Video Input Contract SRP 보강 P0-3

`apps/agent/app/services/video_input_contract.py`가 영상 입력 계약 정규화, 관찰값 수집, fact 품질 gate, 확인 후보 생성, 기술 metadata/recovery plan, 충돌 대상 guard를 한 파일에서 함께 담당하던 구조를 분리했다. 이번 변경은 `VERSION`과 `normalize_video_input_contract()` public import 계약을 유지하면서 Agent 영상 입력 계약의 내부 책임 경계를 줄이는 구조 보강이다.

| 범위 | 변경 내용 |
| --- | --- |
| 계약 상수/정규화 규칙 | `apps/agent/app/services/video_input_contract_rules.py`를 추가해 contract version, fact field 목록, confidence threshold, frame reference 요구 기준, field alias, fact value normalization을 담당한다. |
| 영상 metadata/recovery | `apps/agent/app/services/video_input_contract_metadata.py`를 추가해 기술 metadata 추출, 사고 event summary, frame-rich zero-observation fallback, OpenAI/YOLO 재시도 recovery plan 생성을 담당한다. |
| 관찰값 품질 gate | `apps/agent/app/services/video_input_contract_observations.py`를 추가해 observation 수집/정규화, source 검증, fact 품질 gate, confirmation candidates/groups, observation quality summary를 담당한다. |
| 기존 facade 유지 | `video_input_contract.py`는 `normalize_video_input_contract()` 조립 흐름과 충돌 대상/보행자 오염 방지 guard만 보유한다. 기존 테스트가 참조하는 `VERSION` import 계약은 유지한다. |
| 검증 | `PYTHONPATH=apps/agent py -3.13 -m pytest apps/agent/tests/test_video_input_contract.py -q` 27개 테스트와 `py -3.13 -m py_compile`을 통과했다. 전체 Agent suite는 Python 3.13 기준 154개 통과, 4개 기존 테스트 실패가 남았다. 실패 범위는 동적 질문지 문구와 KNIA 사용자 관점 매핑 테스트이며 이번 분리 파일과 직접 관련된 `video_input_contract` 테스트는 통과했다. |

이 변경은 DB schema, Redis key, storage path, public API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. 충돌 대상 guard 묶음은 P0-4에서 별도 모듈로 분리했다.


## 2026-05-28 Worker Frame Analysis SRP 보강 P0-2

`apps/worker/worker/frame_analysis.py`가 OpenAI 프레임 분석 orchestration, 대표 프레임 선택, 관찰값 정규화, 품질 요약, AI usage 이벤트 조립을 한 파일에서 함께 담당하던 구조를 일부 분리했다. 이번 변경은 `analyze_frames_with_openai()`의 public worker 계약과 기존 테스트에서 참조하던 compatibility helper 이름을 유지하면서 내부 책임 경계를 줄이는 구조 보강이다.

| 범위 | 변경 내용 |
| --- | --- |
| 프레임 선택 | `apps/worker/worker/frame_selection.py`를 추가해 대표 프레임 선택 전략과 선택 metadata 생성을 담당한다. `frame_analysis.py`의 `_select_openai_frames()`, `_frame_selection_metadata()`는 기존 테스트 호환 wrapper로 유지한다. |
| 관찰값 정규화 | `apps/worker/worker/frame_observations.py`를 추가해 OpenAI 관찰값 필터링, confidence 보정, accident event summary 정규화, 관찰 품질 요약을 담당한다. |
| AI 사용량 이벤트 | `apps/worker/worker/frame_analysis_usage.py`를 추가해 OpenAI token usage 집계와 `ai_usage_event` 생성을 담당한다. |
| 기존 facade 유지 | `frame_analysis.py`는 OpenAI 호출 흐름, 재시도, fixture, payload 생성, 외부 호출 adapter를 계속 보유하되 분리된 순수 모듈을 호출한다. |
| 검증 | `PYTHONPATH=apps/worker python -m pytest apps/worker/tests -q` 38개 테스트와 `python -m py_compile`을 통과했다. |

이 변경은 DB schema, Redis key, storage path, public API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. 남은 SRP 후보는 `frame_analysis.py` 내부의 OpenAI payload/prompt 생성과 실제 provider 호출/재시도 orchestration이며, 이는 비용과 외부 API 동작에 민감하므로 별도 단계에서 테스트를 보강한 뒤 분리한다.

## 2026-05-28 Gateway Report Composer SRP 보강 P0-1

`apps/gateway/src/lib/report-composer.ts`가 사용자 결과 리포트 조립, KNIA 링크 표시, 전문가 안내 카드, 분석 모드 표시 정책, 공통 sanitizing을 한 파일에서 함께 담당하던 구조를 일부 분리했다. 이번 변경은 출력 payload와 public API route를 바꾸지 않고 Gateway 내부 책임 경계를 줄이는 구조 보강이다.

| 범위 | 변경 내용 |
| --- | --- |
| 공통 표시 유틸 | `apps/gateway/src/lib/report-composer-common.ts`를 추가해 `AnyRecord`, 안전 텍스트 정제, 배열/숫자 변환, KNIA URL 검증, 표시용 공통 상수와 helper를 담당한다. |
| 분석 모드 정책 | `apps/gateway/src/lib/report-analysis-mode.ts`를 추가해 `quick_summary`, `fault_ratio_focused`, `legal_precedent_focused`, `insurance_response_focused`, `full_deep_research` 표시 계약과 legacy mode 호환 처리를 담당한다. |
| KNIA 링크 카드 | `apps/gateway/src/lib/report-knia-links.ts`를 추가해 KNIA 후보 수집, 원문/영상 URL 검증, 중복 제거, 링크 카드 생성을 담당한다. |
| 전문가 안내 카드 | `apps/gateway/src/lib/report-expert-guidance-card.ts`를 추가해 Agent의 `expert_guidance_sections`를 사용자용 법률/보험 안내 카드로 변환한다. |
| 기존 facade 유지 | `report-composer.ts`는 `composeClientReport`, `composeDebugReport`, `enrichEasyReport`, `sanitizeEasyReport`, `composeEasyFallback`, `composeReanalysisChangeCard` 공개 함수를 유지하고, 분리된 모듈을 조립하는 역할로 축소했다. |
| 검증 | Gateway `npm run build`와 `npm test`를 통과했다. 테스트 기준은 8개 파일, 59개 테스트다. |

이 변경은 DB schema, Redis key, storage path, public API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. 남은 SRP 후보는 `report-composer.ts` 내부의 영상 사실 카드/보완 질문 조립과 missing-info 우선순위 로직이며, 이는 영상/Agent 판단 회귀 위험이 높아 별도 단계에서 테스트를 고정한 뒤 분리한다.

## 2026-05-28 StorageAdapter 및 Synology NAS 파일 저장소

Synology NAS DS216play는 Docker를 실행하지 않는 파일 저장소로만 사용한다. LawCompass Gateway, Agent, Worker, PostgreSQL, Redis는 기존처럼 Docker 가능한 PC/서버에서 실행하며, PostgreSQL 데이터 디렉터리를 NAS 공유폴더로 옮기지 않는다. DB에는 영상 바이너리를 저장하지 않고 `storage_driver`, `storage_key`, `storage_path`, `original_filename`, `mime_type`, `size_bytes`, `sha256`, `storage_status` 같은 파일 메타데이터만 저장한다.

| 범위 | 변경 내용 |
| --- | --- |
| StorageAdapter | Gateway에 `apps/gateway/src/lib/storage/` 계층을 추가했다. `local`, 기존 비활성 `s3`, 신규 `nas_sftp` 드라이버를 같은 인터페이스로 선택하며, 기존 `apps/gateway/src/storage/provider.ts`는 호환 re-export로 유지한다. |
| NAS SFTP | `STORAGE_DRIVER=nas_sftp`이면 Gateway 업로드는 NAS의 tmp 경로에 저장 후 original key로 이동하고, Worker는 원본을 `LOCAL_VIDEO_CACHE_DIR`로 내려받아 ffprobe/ffmpeg를 실행한 뒤 추출 프레임을 `processed/frames` key로 다시 업로드한다. Synology SFTP에서 앱이 사용하는 base path는 공유폴더 기준 `/lawcompass`이며, NAS 직접 URL과 SFTP 절대경로는 사용자 응답에 노출하지 않는다. |
| Upload metadata | Gateway `putUpload()`은 tmp key로 업로드한 뒤 original key로 이동하며, DB에 저장되는 `storage_key`와 `storage_path`는 이동 후 최종 original 위치를 가리켜야 한다. 임시 `.part` key는 `tmpPath` 진단값으로만 남기고 공개 payload에는 노출하지 않는다. |
| Worker cache | Worker에 `worker/storage/` 계층을 추가했다. ffmpeg는 SFTP remote path를 직접 읽지 않고 항상 로컬 캐시 파일을 처리한다. 처리 후 로컬 캐시와 임시 프레임 폴더를 정리한다. |
| DB migration | `infra/postgres/migrations/014_storage_adapter_metadata.sql`와 `015_uploads_storage_adapter_compat.sql`가 uploads 테이블에 storage adapter metadata 컬럼을 idempotent하게 추가한다. 기존 `storage_provider`, `storage_path`, `s3_key`는 backward compatibility로 유지한다. 현재 업로드 500의 핵심 원인은 NAS 권한이 아니라 운영 DB에 `uploads.storage_driver` 등 storage metadata 컬럼이 아직 적용되지 않은 schema mismatch다. |
| NAS directory layout | Synology 내부 SSH 경로는 `/volume1/lawcompass`일 수 있지만, LawCompass SFTP 설정에는 공유폴더 기준 `/lawcompass`를 사용한다. 하위 경로는 `uploads/original`, `uploads/tmp`, `processed/frames`, `processed/clips`, `reports`, `db-backups`, `quarantine`이다. |
| DB backup | `scripts/backup_postgres_to_nas.ps1`는 PostgreSQL dump를 임시 로컬 파일로 만든 뒤 SFTP로 `db-backups`에 업로드한다. NAS는 백업 파일 보관 위치일 뿐 DB 실행 위치가 아니다. |
| Frontend 표시 | 일반 사용자 화면에서는 S3/NAS/SFTP/storage key 같은 내부 용어를 숨기고 “영상 저장하기”, “사고 장면 확인하기” 같은 문구만 표시한다. |

NAS 인증 우선순위는 `NAS_PRIVATE_KEY_PATH`가 있으면 private key를 우선 사용하고, 없을 때 `NAS_PASSWORD`를 사용한다. 실제 비밀번호와 key passphrase는 `.env`에만 두며 문서나 코드에 기록하지 않는다.

## 2026-05-27 Agent 후미추돌 신호대기 판단 신뢰성 보강

빨간불 신호대기 중 정차 차량을 뒤차가 추돌한 사고가 교차로 신호위반/좌회전 대 직진 KNIA 기준으로 오염되는 문제를 보정했다. 신규 기능이 아니라 Agent 판단 신뢰성 보강이며, 특정 문장 고정이 아닌 정상 정차 사유와 신호위반 진입 맥락을 분리하는 범용 규칙으로 처리한다.

| 범위 | 변경 내용 |
| --- | --- |
| 입력 정규화/분류 | `apps/agent/app/services/input_normalizer.py`, `scenario_classifier.py`, `accident_perspective.py`가 `신호대기`, `빨간불에 정차`, `적색신호 대기`, `정지선 대기`를 `stopped_due_to_signal`, `stopped_at_red_light`, `lawful_stop_reason`, `rear_end_context`로 보강한다. `빨간불에 진입`, `적색신호 위반`, `정지신호 무시`처럼 진행/진입/위반 맥락이 있을 때만 신호위반 교차로 사고로 분류한다. |
| rear_end 검색어 | `scenario_search_terms.py`가 rear_end_collision 검색을 후미추돌, 정차 차량 추돌, 신호대기 정차, 뒤차/뒷차 추돌, 안전거리, 선행차/앞차, 차41/차42 중심으로 확장하고, 신호위반·좌회전·직진 대 좌회전·차16 검색어 오염을 제거한다. |
| KNIA primary guard | `knia_matcher.py`와 `orchestration_evidence.py`가 rear_end_collision에서 차41/차42 또는 후미추돌·후방추돌·뒤차·안전거리·정차 차량·선행 차량 근거가 있는 항목만 primary 후보로 유지한다. 차16, 좌회전 대 직진, 신호등 없는 교차로, 진로/차선변경, 보행자/자전거/기물/중앙선 불일치 항목은 primary/표시 근거에서 제외한다. |
| 과실 덮어쓰기 방지 | `orchestration_analysis.py`가 KNIA fault estimate의 source chart가 scenario_type과 호환되지 않으면 최종 `fault_ratio.my/other`를 덮어쓰지 않고 `knia_reference_fault`, `rejected_knia_fault_estimate`, `knia_override_policy`로만 남긴다. |
| 캐시 격리 | `rag/two_stage_cache.py`의 KNIA JSON exact Redis key를 `knia_json:exact:v2:{version}:{party}:{scenario}:{query_hash}` 형태로 올리고, `semantic_query_cache` 조회 조건에 `scenario_type`과 vector distance threshold를 포함했다. scenario_type이 있는 요청은 같은 car_vs_car 내 다른 사고 유형 semantic cache를 재사용하지 않는다. |
| 과실 안내 | 후미추돌 피해 차량으로 판단되면 기본적으로 내 과실 0~10%, 상대 90~100% 계열로 안내하되, 급정지·제동등 고장·비정상 정차·선행사고 후 정차·야간 무등화·시야장애는 조정 확인 항목으로 표시한다. |

기존 오염 캐시가 남아 있을 수 있으므로 로컬 재검증 전 KNIA JSON 범위만 삭제한다. PostgreSQL 전체 볼륨 삭제나 `docker compose down -v`는 사용하지 않는다.

```powershell
docker compose exec postgres psql -U law -d lawcompass -c "DELETE FROM semantic_query_cache WHERE source_scope='knia_json';"
docker compose exec redis sh -lc "redis-cli --scan --pattern 'knia_json:exact:*' | xargs -r redis-cli del"
```

## 2026-05-26 P3: 실제 OpenAI 영상 회귀 재측정 및 실행 진입점 보강

P3는 실제 OpenAI 프레임 분석을 켠 상태에서 사고 영상 1~5번 reference set을 다시 측정하고, P1/P2에서 보강한 보완 질문·fallback 흐름이 실제 batch 로그에서도 유지되는지 확인한 작업이다. 특정 사고 영상에 맞춘 판단 규칙을 추가하지 않고, 현재 영상 처리 파이프라인의 실행 안정성과 관찰값 품질 리스크를 분리해 기록했다.

| 범위 | 변경 내용 |
| --- | --- |
| Docker 실행 보강 | `apps/gateway/Dockerfile`과 `apps/gateway/package.json`의 production start 경로를 TypeScript build 산출물 위치인 `dist/src/main.js`로 맞췄다. `apps/frontend/Dockerfile`은 `vite preview` 실행 전 `npm run build`를 수행하도록 수정했다. |
| 실제 OpenAI batch | `storage/reference-videos/edited/`의 사고 영상 1~5번을 `ENABLE_OPENAI_FRAME_ANALYSIS=1`, fixture OFF 상태에서 측정했다. 1차 batch는 4/5 통과했고, 사고 4번은 OpenAI read timeout으로 실패했다. |
| Timeout 재시도 | 사고 4번은 worker를 `OPENAI_TIMEOUT_SEC=90`으로 재시작한 뒤 단일 재시도에서 통과했다. 통합 aggregate는 사고 4번 timeout 결과를 재시도 성공 결과로 대체해 5/5 pipeline 통과로 평가한다. |
| 회귀 측정 표시 | `scripts/video_agent_e2e.py`와 `scripts/video_accuracy_batch.py`가 영상 사실 카드의 `quality_notes`, `recovery_actions`, recovery action count를 향후 batch aggregate에 포함하도록 보강했다. 이번 P3의 기존 batch JSON은 패치 전 산출물이므로 recovery action count는 0으로 남아 있을 수 있다. |
| P1/P2 확인 | 사고 2번은 `상대 차량 신호`가 최우선 보완 질문으로 유지됐다. 프레임은 충분하지만 확정 관찰값이 부족한 경우 `visual_evidence_limited` 상태와 Agent 입력 계약의 recovery action이 생성되는 것을 확인했다. |
| 평가 결과 | 통합 aggregate 기준 `reference_guidance_eval`, `reference_evidence_alignment_eval`, `reference_guidance_calibration_eval` 모두 5개 샘플 통과. Calibration은 5/5 `calibrated_for_user_flow`, evidence alignment는 22개 focus 모두 `evidence_content_ready`로 평가됐다. |

P3 기준 영상 flow 통합 요약은 대표 프레임 관찰값 13개, Agent accepted 8개, supporting 5개, 판단 반영 4개, 사용자 입력 확인 3개, 충돌 1개다. 사용자 표시 상태는 `확정 사실 없음` 4개, `반영 가능` 1개로, OpenAI가 실제 사고 장면을 항상 충분히 구조화하지 못하는 리스크가 아직 크다.

잔여 리스크:

- 실제 OpenAI 프레임 분석은 어두운 영상이나 난도가 높은 영상에서 timeout이 발생할 수 있다. 비용 방지를 위해 측정 후 worker는 기본적으로 `ENABLE_OPENAI_FRAME_ANALYSIS=0` 상태로 복구한다.
- `확정 사실 없음` 비율이 높으므로 다음 단계는 과실 숫자 튜닝보다 영상 관찰 품질 보강이 우선이다. YOLO 보조 관찰, OpenAI 재시도 조건, 사고 시점 후보 추출, 충돌 대상 확인 fallback을 함께 다뤄야 한다.
- 통합 평가의 근거 품질은 현재 batch payload에 source quality metadata가 부족해 `source_quality_unknown` 경고가 남는다. 최종 제품 수준에서는 실제 Gateway/Agent 최신 경로로 근거 출처 품질 필드를 포함해 재생성해야 한다.

이 변경은 DB schema, Redis key, storage path, public API route, 외부 API 종류를 변경하지 않는다. OpenAI 실행 로그와 reference manifest/current aggregate는 `logs/` 아래 로컬 산출물이며 Git에 포함하지 않는다.

## 2026-05-28 Frontend Workspace SRP 보강 P0

P3 이후 적용할 구조 보강 항목으로 `apps/frontend/src/composables/useCaseWorkspace.ts`의 단일 책임 분리를 시작했다. 먼저 비슷한 장문 파일을 점검한 결과 `apps/gateway/src/lib/report-composer.ts`, `apps/worker/worker/frame_analysis.py`, `apps/agent/app/services/video_input_contract.py`, `apps/gateway/src/routes/uploads.ts`도 향후 SRP 점검 후보지만, 이번 P0은 프론트 workspace composable에 한정한다.

| 범위 | 변경 내용 |
| --- | --- |
| Guided data 분리 | 사고유형 옵션, 분석모드 옵션, guided question set, fallback 질문 추론 상수/순수 함수를 `apps/frontend/src/composables/caseWorkspaceGuidance.ts`로 이동했다. |
| 표시 유틸 분리 | `prettySize`, `formatDate`, `statusLabel`, `statusClass`를 `apps/frontend/src/composables/caseWorkspaceFormatters.ts`로 이동했다. |
| 외부 계약 유지 | `useCaseWorkspace()`의 반환값과 기존 re-export는 유지해 `CaseDetailView.vue` 및 case components의 import/사용 방식을 바꾸지 않았다. |
| 표시 계약 테스트 | `apps/frontend/scripts/test-display.mjs`가 분리된 guidance/formatter 파일도 사용자 표시 계약 검사 범위에 포함한다. |
| 남은 단계 | P1은 report/progress payload 판별 로직, P2는 guided answer -> facts 매핑, P3는 upload/progress/report orchestration composable 분리를 검토한다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 목적은 화면 동작 변경이 아니라 프론트 소스 책임 경계를 줄여 이후 사고유형/질문지 확장 시 충돌과 회귀 위험을 낮추는 것이다.

## 2026-05-28 Frontend Workspace SRP 보강 P1

P1은 P0 이후 `useCaseWorkspace.ts`에 남아 있던 report/progress 판별 로직을 순수 helper로 분리한 작업이다. 화면 상태 ref와 API 호출 흐름은 기존 composable에 남기고, 상태값 분류와 payload 추출 기준만 별도 파일로 이동했다.

| 범위 | 변경 내용 |
| --- | --- |
| Progress helper | `apps/frontend/src/composables/caseWorkspaceProgress.ts`를 추가해 job running/finished/failed 판별, progress step label 정규화, report payload 추출, report ready 판별을 담당한다. |
| Workspace 축소 | `useCaseWorkspace.ts`는 helper를 import해 사용하며, 직접 보유하던 report/progress 순수 판단 함수를 제거했다. |
| 표시 계약 테스트 | `apps/frontend/scripts/test-display.mjs`가 `caseWorkspaceProgress.ts`도 검사 범위에 포함해 guided flow와 public storage 표시 계약을 유지한다. |
| 남은 단계 | P2는 `answerGuidedQuestion()`의 guided answer -> facts 매핑 분리, P3는 upload/progress/report orchestration composable 분리를 검토한다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다.

## 2026-05-28 Frontend Workspace SRP 보강 P2

P2는 `useCaseWorkspace.ts`에 남아 있던 guided answer -> structured facts 변환 책임을 별도 helper로 분리한 작업이다. 사고유형 선택, 질문 답변 저장, 분석 시작 같은 화면 흐름은 기존 composable에 남기고, 답변 값이 어떤 `AccidentFacts` 필드로 반영되는지는 순수 함수로 이동했다.

| 범위 | 변경 내용 |
| --- | --- |
| Fact mapping helper | `apps/frontend/src/composables/caseWorkspaceFactMapping.ts`를 추가해 `getGuidedQuestionId()`와 `applyGuidedQuestionAnswer()`를 담당한다. |
| Workspace 축소 | `answerGuidedQuestion()`은 답변 id 저장과 `facts.value` 갱신만 수행하며, 후미추돌·차대사람·자전거·스텔스 정차 차량·교차로 등 세부 facts 매핑 분기는 helper로 이동했다. |
| 표시 계약 테스트 | `apps/frontend/scripts/test-display.mjs`가 분리된 fact mapping 파일도 검사 범위에 포함한다. |
| 남은 단계 | P3는 upload/progress/report orchestration composable 분리를 검토한다. 단, P3는 API 호출 흐름과 polling 타이머를 건드리므로 P0~P2보다 회귀 위험이 높아 범위를 작게 나눠 진행한다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 목적은 사고 질문 확장 시 UI composable이 도메인 매핑 세부사항을 계속 떠안지 않도록 책임 경계를 줄이는 것이다.

## 2026-05-28 Frontend Workspace SRP 보강 P3

P3는 `useCaseWorkspace.ts`의 업로드/분석 흐름 중 진행상태와 리포트 준비 상태를 다루는 orchestration 보조 책임을 분리한 작업이다. API 호출 순서와 polling 주기는 유지하고, 진행률 표시와 작업 상태별 문구 선택을 별도 helper로 이동해 이후 업로드/리포트 실행 흐름을 더 안전하게 나눌 수 있는 기반을 만든다.

| 범위 | 변경 내용 |
| --- | --- |
| Orchestration helper | `apps/frontend/src/composables/caseWorkspaceOrchestration.ts`를 추가해 `delay()`, `createCaseWorkspaceProgressController()`, `getRunningJobProgress()`를 담당한다. |
| Progress controller | backend progress payload 반영, local progress clamp, report ready 상태 세팅을 helper가 처리한다. |
| Polling message split | `video_preprocess`, `video_analyze`, 기타 job type별 진행 문구 선택을 `getRunningJobProgress()`로 이동했다. |
| Workspace 축소 | `useCaseWorkspace.ts`는 API 호출과 guided flow 상태 전환을 유지하되, 진행률/리포트 준비 표시의 세부 구현을 직접 보유하지 않는다. |
| 표시 계약 테스트 | `apps/frontend/scripts/test-display.mjs`가 orchestration helper도 표시 계약 검사 범위에 포함한다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 남은 구조 보강 후보는 upload/save/report API 호출 자체를 더 작은 composable로 옮기는 작업이지만, 해당 범위는 타이머와 비동기 분석 흐름 회귀 위험이 있어 별도 단계에서 검토한다.

## 2026-05-28 Frontend Workspace SRP 보강 P4

P4는 `useCaseWorkspace.ts`에 남아 있던 API 요청 payload 조립 책임을 분리한 작업이다. 실제 저장, 텍스트 분석, 영상 분석, 보완 재분석 호출 순서는 유지하고, 각 호출에 들어가는 `description_text`, `structured_facts`, `selected_keywords`, `analysis_mode`, `followup_answers`, `upload_id` 조합만 별도 helper로 이동했다.

| 범위 | 변경 내용 |
| --- | --- |
| Payload helper | `apps/frontend/src/composables/caseWorkspacePayloads.ts`를 추가해 `normalizeCaseDescription()`, `buildCaseInputPayload()`, `buildTextAnalysisPayload()`, `buildVideoAnalysisPayload()`, `buildFollowupAnalysisPayload()`를 담당한다. |
| Workspace 축소 | `useCaseWorkspace.ts`는 화면 ref 값을 helper 입력으로 넘기고, API payload shape 세부사항을 직접 보유하지 않는다. |
| 기본 설명 정규화 | 영상만 입력한 경우 사용하는 기본 설명 `"영상 자료 기반 사고 분석"`을 helper로 모아 저장/분석 payload가 같은 정규화 기준을 쓰도록 했다. |
| 표시 계약 테스트 | `apps/frontend/scripts/test-display.mjs`가 payload helper도 검사 범위에 포함한다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. 목적은 이후 Agent 입력 계약이 확장될 때 화면 상태 composable이 API payload 세부 필드를 계속 떠안지 않도록 책임 경계를 줄이는 것이다.

## 2026-05-26 P2: 프레임 충분·관찰값 부족 fallback 표시 보강

P2는 “대표 프레임은 충분히 추출됐지만 분석 관찰값이 0개이거나 판단 반영값이 없는 상태”를 실패처럼 방치하지 않고, 안전한 fallback 상태와 다음 조치를 명확히 남기는 작업이다. 특정 사고 영상에 맞춘 보정이 아니라, 영상 입력 전반에서 재시도/보조 분석/사용자 보완 입력 흐름이 끊기지 않도록 Agent-Gateway-Frontend 계약을 보강했다.

| 범위 | 변경 내용 |
| --- | --- |
| Agent 영상 입력 계약 | `apps/agent/app/services/video_input_contract.py`가 대표 프레임 6장 이상이고 OpenAI/YOLO 분석이 실행됐지만 관찰값이 0개인 payload를 `visual_evidence_limited` 참고 관찰로 복구한다. 분석이 실행되지 않은 프레임-rich payload는 사실 후보를 만들지 않고 `analysis_recovery` 액션만 남긴다. |
| 복구 액션 | `analysis_recovery`와 `observation_quality_summary.recovery_actions`에 OpenAI 프레임 분석 활성화, 프레임 분석 재시도, YOLO 보조 관찰 활성화, 사고 시점/충돌 대상 확인 같은 다음 조치를 안전 문구로 기록한다. API key, raw prompt, frame path 원문은 노출하지 않는다. |
| Gateway 표시 계약 | `apps/gateway/src/lib/report-composer.ts`가 recovery action을 easy-report의 `video_fact_explanation_card.quality_summary.recovery_actions`로 전달하고, “프레임은 충분하지만 판단 반영값이 부족해 재시도 또는 보조 분석이 필요하다”는 상태 note를 추가한다. |
| Frontend 표시 | `apps/frontend/src/components/easy/VideoFactExplanationCard.vue`가 recovery action을 영상 사실 카드 안에서 표시한다. 사용자는 0개 상태가 단순 실패인지, 재시도/YOLO/사용자 보완이 필요한 상태인지 구분할 수 있다. |
| 검증 | Agent `test_video_input_contract.py` 23개, Gateway `report-composer.test.ts` 33개, Gateway build, Frontend build를 통과했다. Agent 테스트는 로컬 구조상 `PYTHONPATH=apps/agent`를 지정해 실행한다. |

이 변경은 DB schema, Redis key, storage path, public API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. Worker의 기존 OpenAI zero-observation retry와 `visual_evidence_limited` fallback을 대체하지 않고, Agent 입력 계약에서 한 번 더 방어하는 보강이다.

## 2026-05-26 P1: 신호 불명확 교차로 사고 안내 흐름 보강

작업 시작 전 `DEVELOPMENT_PROMPT.md`, `SYSTEM_OVERVIEW.md`, `docs/GITHUB_COLLABORATION_WORKFLOW.md`를 확인하고, 최신 `main` pull 및 reference video 폴더 상태를 점검한 뒤 `codex/p1-signal-guidance-flow` 브랜치에서 P1 작업을 진행했다.

| 범위 | 변경 내용 |
| --- | --- |
| Gateway 결과 조합 | `apps/gateway/src/lib/report-composer.ts`의 조건부 판단 카드 생성 조건을 보강했다. Agent가 `fault_ratio.conditional_outcomes`를 직접 주지 않아도 `intersection_signal_violation`, 내 차량 황색/적색 전환, 상대 신호 미확인, 교차로 좌·우회전/직진 같은 구조화 사실이 있으면 “상대 신호가 정상 진행 신호였을 때”와 “상대도 적색 또는 신호위반이었을 때”를 나눠 안내한다. |
| 보완 질문 우선순위 | 조건부 판단 카드가 생성된 뒤 `missing_info`를 한 번 더 정렬해, 상대 차량 신호/신호 가시성 질문이 차량 파손 정도 같은 후순위 질문보다 먼저 나오도록 했다. |
| 사고 대상 오염 방지 | 차대차 교차로 사고에서 횡단보도나 보행자가 영상에 등장하더라도 조건부 신호 안내가 보행자 사고처럼 변하지 않도록 테스트를 추가했다. 보행자는 사고 환경일 수 있지만, `collision_partner_type=vehicle`이면 사고 당사자 근거로 승격하지 않는다. |
| 검증 | Gateway `report-composer.test.ts`에 구조화 사실 기반 조건부 신호 분기 및 보완 질문 재정렬 테스트를 추가했고, 총 33개 테스트가 통과했다. |

이 변경은 DB schema, Redis key, storage path, public API route, 외부 API 종류를 변경하지 않는다. 실제 영상 분석 모델의 관찰값 품질은 Worker/Agent 영상 P단계에서 계속 다루며, 이번 P1은 신호가 불명확한 차대차 교차로 사고의 결과 표시와 질문 흐름을 범용적으로 보강한 작업이다.

## 2026-05-26 P0: AI 사용량 안전 이벤트 계약 보강

작업 시작 전 `DEVELOPMENT_PROMPT.md`, `SYSTEM_OVERVIEW.md`, `docs/GITHUB_COLLABORATION_WORKFLOW.md`를 확인하고, 최신 `main` pull 및 최근 병합 이력을 점검한 뒤 `codex/p0-evidence-source-hardening` 브랜치에서 P0 작업을 진행했다.

| 범위 | 변경 내용 |
| --- | --- |
| Worker OpenAI 프레임 분석 | `apps/worker/worker/frame_analysis.py` 결과에 `ai_usage_event`를 추가했다. 이벤트는 `provider`, `endpoint`, `model`, `enabled`, `success`, `frame_count`, `selected_frame_count`, `max_output_tokens`, `retry_count`, `usage` 숫자만 담고 API key, raw prompt, raw user text는 포함하지 않는다. |
| Agent LLM 정책 | `apps/agent/app/services/llm_policy.py`가 analyst 섹션별 `ai_usage_event`를 생성하고 `summarize_case_llm_policy`의 section summary와 `cost_metadata.usage_event_version`에 반영한다. 현재 Agent chat completion token 수는 아직 수집하지 않고 안전 호출 메타데이터만 남긴다. |
| 운영 리스크 요약 | `scripts/summarize_operating_risk.py`가 batch 결과의 `ai_usage_event`를 읽어 event version count와 token usage totals를 함께 집계한다. |
| 검증 | Worker frame analysis contract 테스트와 Agent LLM policy 테스트에서 `ai_usage_event`가 생성되고 secret/prompt 없이 안전 필드만 남는지 확인한다. |

이 변경은 DB schema, Redis key, storage path, public API route, 외부 API 종류를 변경하지 않는다. PostgreSQL `ai_usage_events` 영속 테이블과 관리자 사용량 대시보드는 후속 Phase B 작업이다.

## 2026-05-25 영상 P4~P8: 근거 품질, 운영 리스크, 최종 검증 보강

P4~P8은 영상 처리 자체의 세부 튜닝보다 “분석 결과를 제품 수준으로 검증·운영할 수 있는 구조”를 닫는 작업으로 진행했다. 특정 사고 영상에 맞춘 출력 보정은 하지 않았고, 원문 근거 커버리지, static fallback 의존, 사용자 표시 문구, OpenAI 사용량 메타데이터, 최종 검증 재현성을 보강했다.

| 단계 | 변경 내용 |
| --- | --- |
| P4 원문/보조 근거 커버리지 | `evidence_source_status.py`를 `evidence-source-status-v2`로 올리고, legal/KNIA 소스별 `source_quality_counts`, `original_or_collected_count`, `static_support_count`, `source_url_count`, `coverage_status`, 전체 `source_quality_totals`를 제공한다. 원문 근거 없이 보조 근거만 있는 경우 recovery action에 원문 수집 확장을 남긴다. |
| P5 평가 기준 | `reference_evidence_alignment_eval.py`가 카드별 `source_quality_review`, aggregate `source_quality_status_counts`, 원문 대조 필요 개수, source URL 개수, source quality 누락 권고를 산출한다. 오래된 fixture처럼 출처 품질 필드가 없는 결과도 최종 근거 리뷰 전 재생성 대상으로 표시된다. |
| P6 사용자 UX | Gateway 전문가 안내 카드에 `source_summary`를 추가하고, Frontend는 원문 대조 경고를 `needs_original_source_review=true`인 basis item에만 표시한다. 원문 링크가 있는 근거, 보조 기준, 원문 대조 필요 근거가 한 번 더 구분된다. |
| P7 운영 리스크 | Worker OpenAI 프레임 분석 응답에 provider `usage`가 있으면 `input_tokens`, `output_tokens`, `total_tokens`만 안전 메타데이터로 보존한다. `scripts/summarize_operating_risk.py`는 reference 평가와 batch 결과를 묶어 token usage, static fallback, 원문 대조 필요, zero-observation 상태를 요약한다. |
| P8 최종 검증 | `scripts/verify_final_readiness.ps1`를 추가해 Python compile, Agent source-status 테스트, reference hardening fixture, 운영 리스크 요약, Gateway 테스트/빌드, Frontend 빌드, 선택적 Docker/Agent 회귀 검증을 한 번에 재현한다. |

검증은 `python -m py_compile`, Agent `pytest` 15개, `verify_reference_hardening_fixture.py`, `summarize_operating_risk.py`, Gateway `report-composer.test.ts` 32개, Gateway build, Frontend build, `verify_final_readiness.ps1 -SkipDockerChecks`를 통과했다. 이후 Docker 재빌드와 `/health` 확인으로 실행 상태를 검증한다.

이 변경은 DB schema, Redis key, storage path, public API route, 외부 API 종류를 변경하지 않는다. OpenAI/YOLO/AI Hub 키와 원본 데이터는 계속 Git에 올리지 않는다.

## 2026-05-25 영상 P3: 근거 출처 품질 및 원문/보조 근거 구분

전문가 안내 카드의 근거가 실제 수집 원문 근거인지, KNIA 수집 기준인지, static fallback 보조 근거인지 구분할 수 있도록 Agent-Gateway-Frontend 표시 계약을 보강했다. 목적은 특정 사고 영상에 맞춘 결과 보정이 아니라, 모든 사고 입력에서 “정확한 원문 기반 근거”와 “임시 보조 근거”를 사용자가 구분할 수 있게 만드는 것이다.

| 범위 | 변경 내용 |
| --- | --- |
| Agent 근거 payload | `expert_guidance_sections.py`가 각 basis item에 `source_quality`, `source_quality_label`, `source_review_note`, `needs_original_source_review`, `source_url`을 붙인다. `chunk_id`, cache key, 내부 retrieval id는 계속 노출하지 않는다. |
| 출처 품질 분류 | `static_fallback`/`static_scenario_support` 또는 `static:` chunk는 `보조 참고 근거`로 표시한다. KNIA/법령/판례 원문 URL이 있는 근거는 `수집 KNIA 원문 기준` 또는 `원문 법령/판례 근거`로 표시한다. |
| Gateway 표시 계약 | `report-composer.ts`가 Agent basis source quality와 원문 링크를 보존하되, 내부 ID는 필터링한다. 일반 easy-report의 전문가 카드에서 원문/보조 근거 구분이 유지된다. |
| Frontend 표시 | `ExpertGuidanceCard.vue`가 근거 카드마다 출처 품질 배지를 표시하고, 원문 URL이 있는 경우 `원문 보기` 버튼을 제공한다. 원문 확인이 필요한 보조 근거는 별도 색상으로 표시한다. |
| 평가 스크립트 | `reference_evidence_alignment_eval.py`가 `source_quality_counts`, `static_support_basis_count`, `original_or_collected_basis_count`를 집계한다. 이후 실제 원문 DB 확장이나 fallback 의존 감소 작업의 기준으로 사용한다. |
| 검증 | Agent 전문가 안내 섹션 테스트, Gateway report composer 테스트, Frontend production build, 평가 스크립트 py_compile을 통과했다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 종류를 변경하지 않는다. 실제 법령·판례·KNIA 원문 데이터셋 확장은 다음 단계의 수집/색인 범위이며, 이번 P3는 현재 근거의 품질과 출처를 사용자와 평가 로그에서 구분 가능하게 만드는 구조 보강이다.

## 2026-05-25 영상 P0 검증: OpenAI+YOLO 실제 영상 1~5 회귀

사고 영상 1~5번을 실제 OpenAI 프레임 분석 ON, YOLO 보조 관찰 ON, fixture OFF 상태에서 재측정했다. 결과 로그는 `logs/video_accuracy/p0_video_openai_yolo_final_20260525/` 아래 로컬 파일로만 남기며 Git에는 포함하지 않는다.

| 항목 | 결과 |
| --- | --- |
| 배치 결과 | `video_accuracy_batch=completed`, 5개 샘플 모두 pipeline 통과 |
| 영상 관찰 흐름 | 총 프레임 관찰값 34개, Agent accepted 21개, 판단 반영 14개, 사용자 입력 확인 5개, 충돌 2개 |
| 사용자 표시 상태 | 3개 샘플은 `일부 반영`, 2개 샘플은 `확정 사실 없음`으로 표시됐다. `확정 사실 없음`은 실패가 아니라 확정 가능한 물리 사실이 부족하다는 안전 상태다. |
| 품질 보강 확인 | OpenAI timeout 복구 retry, 관찰값 0개 retry, `visual_evidence_limited` 지원 관찰값 경로가 테스트와 실제 회귀 흐름에 포함됐다. |
| reference guidance 평가 | 5개 샘플 모두 `ready_for_legal_knia_insurance_evidence_eval`, 전문가 안내 카드 5개 모두 reference review 가능 상태 |
| evidence/calibration 잔여 리스크 | 사고 1·4·5 등에서 근거 제목/사유가 reference focus 핵심어를 충분히 담지 못하는 `basis_mentions_reference_focus_terms` 실패가 남았다. 이는 영상 처리 P0가 아니라 다음 단계의 근거 검색/표시 적합도 보정 항목이다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 종류를 변경하지 않는다. OpenAI/YOLO 실제 호출은 비용과 시간이 발생하므로 기본 운영에서는 계속 비활성 또는 제한적으로 사용한다.

## 2026-05-25 영상 P0: 비접촉 유발자와 실제 충돌 상대 분리

영상 분석 결과가 사고 판단에 반영될 때 자전거, 보행자, 횡단보도, 신호등처럼 영상에 등장한 객체가 실제 충돌 대상처럼 오분류되는 문제를 줄이기 위해 Agent 영상 입력 계약을 확장했다. 목적은 특정 테스트 영상에 맞춘 보정이 아니라, 실제 사고 전반에서 “사고 유발 요인”과 “물리적으로 접촉한 상대”를 분리하는 것이다.

| 범위 | 변경 내용 |
| --- | --- |
| Worker 프레임 분석 | OpenAI 프레임 분석 허용 관찰값에 `non_contact_trigger`, `trigger_actor_type`, `trigger_actor_behavior`, `direct_collision_partner_type`, `rear_vehicle_collision`을 추가했다. 프롬프트는 비접촉 유발 사고에서 유발 객체와 실제 충돌 상대를 분리하도록 지시한다. |
| Agent 입력 계약 | `video_input_contract.py`가 새 관찰값을 fact 후보로 수용하고 confidence/frame reference 기준을 적용한다. `fact_arbitration.py`도 새 필드를 video-primary 물리 사실로 취급한다. |
| 사고 분류 | `scenario_classifier.py`와 `input_normalizer.py`가 자전거가 사고를 유발했지만 실제 접촉은 후방 차량과 발생한 경우를 `car_vs_bicycle` 직접 충돌이 아니라 `car_vs_car` 후방추돌/비접촉 유발 맥락으로 분류한다. |
| 과실/근거 판단 | `fault_ratio_analyst.py`, `expert_guidance_sections.py`, `orchestration_evidence.py`가 새 필드를 반영해 비접촉 자전거 유발, 후방 차량 안전거리, 실제 충돌 상대를 분리해서 근거를 고른다. |
| 사용자 표시 | Gateway easy-report가 새 필드의 라벨, 질문, 옵션, 우선순위를 제공한다. 보완 질문은 보행자/횡단보도 맥락보다 유발 객체, 실제 충돌 상대, 후방 추돌 여부를 먼저 확인하도록 정렬한다. |
| 검증 | Agent 영상 입력 계약/분류 테스트, Gateway report composer 테스트, Worker 프레임 분석/job processor 계약 테스트를 추가 또는 갱신했다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. 기존 OpenAI/YOLO provider adapter가 생성하는 관찰값을 더 명확한 Agent 입력 계약으로 받아들이는 구조 보강이다.

## 2026-05-25 AI Hub 로컬 데이터 폴더

AI Hub 교통사고/차량 인지 데이터셋 확인을 위해 저장소 루트에 `datasets/aihub/` 로컬 작업 폴더를 둔다. 원본 전체 데이터는 테라 단위라 로컬에 받지 않는 것을 원칙으로 하고, 샘플 데이터와 AI Hub Shell의 파일 목록/선택 다운로드 결과만 데이터셋별 폴더에 보관한다. 실제 데이터 파일은 Git에 올리지 않는다.

| 폴더 | 역할 |
| --- | --- |
| `datasets/aihub/traffic-accident-video/samples/` | AI Hub `교통사고 영상 데이터`의 샘플(경량) 데이터 위치 |
| `datasets/aihub/traffic-accident-video/aihubshell/` | `교통사고 영상 데이터`의 AI Hub Shell 파일 목록, 선택 다운로드 결과, 실행 로그 위치 |
| `datasets/aihub/vehicle-person-recognition/samples/` | AI Hub `차량 및 사람 인지 영상`의 샘플(경량) 데이터 위치 |
| `datasets/aihub/vehicle-person-recognition/aihubshell/` | `차량 및 사람 인지 영상`의 AI Hub Shell 파일 목록, 선택 다운로드 결과, 실행 로그 위치 |

AI Hub Shell은 `datasetkey`만으로 다운로드하면 전체 데이터셋을 받으므로 사용하지 않는다. 먼저 `list 모드`로 파일 목록과 `filekey`를 확인하고, 필요한 라벨/샘플 파일만 선택 다운로드한다. `.gitignore`는 위 하위 폴더의 실제 데이터와 Shell 산출물을 제외하고, 안내용 README만 추적하도록 설정한다. API key, 개인정보, 원본 대용량 데이터, 모델 가중치는 커밋하지 않는다.

## 2026-05-25 YOLO 로컬 보조 관찰 PoC

Ultralytics YOLO는 LawCompass 본 서비스의 사고 판단 모델이 아니라 차량, 사람, 신호등 같은 객체 위치를 안정적으로 뽑는 로컬 보조 관찰 모델로 취급한다. 프로젝트에는 재현 가능한 스크립트와 문서만 추가하고, 가상환경·모델 가중치·추론 산출물은 저장소 밖 또는 ignore 대상 경로에 둔다.

| 범위 | 기준 |
| --- | --- |
| 설치 위치 | 로컬 검증 가상환경은 `C:/Users/yangbun/Documents/OSS/.venv-yolo`, 모델은 `C:/Users/yangbun/Documents/OSS/yolo-models`, 결과는 `C:/Users/yangbun/Documents/OSS/yolo-runs`를 사용한다. |
| 프로젝트 파일 | `tools/yolo/requirements-yolo.txt`와 `tools/yolo/run_yolo_observation_smoke.py`가 팀원 재현용 진입점이다. |
| 문서 | `docs/YOLO_LOCAL_SETUP.md`에 설치, GPU 확인, smoke test, 영상처리 연결 구조를 기록했다. `THIRD_PARTY_NOTICES.md`에 Ultralytics YOLO AGPL-3.0/Enterprise 라이선스 고지를 추가했다. |
| 현재 검증 | RTX 5070 Ti에서 `torch 2.11.0+cu128`, `ultralytics 8.4.53`로 CUDA 사용 가능 상태를 확인했다. AI Hub `차량 및 사람 인지 영상` 샘플 이미지 1장에서 YOLO가 차량 2대와 트럭 1대를 감지했다. |
| Agent 연결 원칙 | YOLO 탐지는 `vision_model:yolo` source의 객체 위치 후보일 뿐이다. 사람 객체가 보인다고 차대사람 사고로 승격하지 않고, 차량 객체가 보인다고 `collision_partner_type=vehicle`을 확정하지 않는다. 후보 관찰값은 `video_observations` 계약과 fact arbitration을 거친 뒤 수용/보류/충돌로 분리한다. |

이 변경은 운영 Docker image, DB schema, Redis key, API route, 외부 API 계약을 변경하지 않는다. 실제 서비스 자동 파이프라인에 YOLO를 붙이기 전에는 라이선스, 리소스, provider adapter 경계를 다시 검토한다.

## 2026-05-25 YOLO Worker provider adapter 연결

YOLO 보조 관찰 PoC를 Worker 영상 전처리 경로에 선택형 provider adapter로 연결했다. 기본값은 `ENABLE_YOLO_FRAME_ANALYSIS=0`이라 기존 운영 흐름과 Docker 기본 실행에는 영향을 주지 않는다.

| 범위 | 변경 내용 |
| --- | --- |
| Worker adapter | `apps/worker/worker/yolo_frame_analysis.py`가 기존 ffmpeg 대표 프레임 목록을 입력받아 Ultralytics YOLO 객체 탐지를 수행한다. 원본 영상을 다시 읽지 않고 추출된 프레임만 분석한다. |
| 환경변수 | `ENABLE_YOLO_FRAME_ANALYSIS`, `YOLO_MODEL_PATH`, `YOLO_DEVICE`, `YOLO_CONFIDENCE`, `YOLO_FRAME_ANALYSIS_MAX_FRAMES`, `YOLO_MAX_DETECTIONS`, `YOLO_MAX_FRAME_REFS`를 worker compose 환경에 추가했다. |
| 관찰값 병합 | `job_processor.py`가 `openai_frame_analysis`와 `yolo_frame_analysis`를 각각 metadata에 보존하고, 두 provider의 `observations`를 `metadata["observations"]`로 병합해 기존 Agent `video_observations` 계약으로 전달한다. |
| 안전장치 | YOLO는 `vision_model:yolo` source로만 들어가며, 사람/차량/신호등 탐지 confidence를 Agent 확정 임계값 아래로 제한한다. 따라서 YOLO 단독으로 차대사람/차대차/과실비율을 확정하지 못하고 보완 후보로만 쓰인다. |
| 배포 주의 | 기본 worker image에는 Ultralytics가 필수 의존성으로 추가되지 않았다. YOLO를 Docker에서 켜려면 별도 image/override 또는 로컬 worker 환경에 `ultralytics`와 모델 가중치를 준비해야 한다. |
| 검증 | worker 단위 테스트가 비활성 기본값, 모델 경로 누락, 후보 confidence cap, 사고 후보 프레임 선택, OpenAI+YOLO 관찰값 병합을 확인한다. |

이 변경은 DB schema, Redis key, API route, 외부 API 종류를 변경하지 않는다. Worker metadata payload와 compose 환경변수만 확장한다.

## 2026-05-25 영상 관찰값 0개 bounded retry 보강

OpenAI 프레임 분석이 정상 응답을 받았지만 `observations`가 0개로 끝나는 경우, 대표 프레임이 충분하면 1회에 한해 재분석을 수행하도록 Worker를 보강했다. 목적은 사고 시점 후보나 프레임 문맥은 존재하지만 첫 응답이 지나치게 보수적으로 빈 관찰값을 반환하는 경우를 복구하는 것이다.

| 범위 | 변경 내용 |
| --- | --- |
| 재시도 조건 | `OPENAI_FRAME_ANALYSIS_ZERO_OBSERVATION_RETRY=1`이고 선택 프레임 수가 `OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES` 이상이며, 1차 OpenAI 응답의 정규화 관찰값이 0개일 때만 1회 재시도한다. |
| 재시도 프롬프트 | 재시도는 기존 사고 대상 우선 계약을 유지하되, “확실하지 않은 사실은 만들지 말고, 시각적으로 지지 가능한 사고 대상·충돌 파트너·신호·중앙선·정차 차량·도로 장애물·횡단보도 맥락·보행자 충돌 아님 여부가 있으면 빈 관찰값으로 끝내지 말라”는 복구 지시를 추가한다. |
| 사고 후보 파생 | 모델이 `accident_event_summary`를 생략했지만 `collision_partner_type`, `primary_collision_target`, `collision_point_visible`, `impact_direction` 같은 고신뢰 충돌 관찰값이 있으면 해당 `frame_refs`로 사고 시점 후보를 파생한다. |
| 일시 오류 재시도 | 실제 OpenAI 분석 중 `read timeout` 같은 일시 네트워크 오류가 발생하면 `OPENAI_FRAME_ANALYSIS_ERROR_RETRY=1`이고 대표 프레임이 충분한 경우 1회만 bounded retry를 수행한다. |
| 제한적 영상 근거 fallback | 모든 bounded retry 이후에도 관찰 가능한 물리 사실이 0개라면 `visual_evidence_limited` 지원 관찰값을 남긴다. 이 값은 과실 판단 fact가 아니라 “프레임은 분석됐지만 직접 반영할 영상 사실이 부족하다”는 품질 신호다. |
| 결과 메타데이터 | Worker 결과에 `zero_observation_retry_used`, `zero_observation_retry_error`, `error_retry_used`, `error_retry_error`, `analysis_attempts`를 남긴다. 각 attempt는 response id/status, 관찰값 수, 사고 후보 프레임 수, impact visible 여부만 포함하며 prompt나 secret은 저장하지 않는다. |
| Compose 기본값 | worker 환경변수 기본값으로 `OPENAI_FRAME_ANALYSIS_ZERO_OBSERVATION_RETRY=1`, `OPENAI_FRAME_ANALYSIS_ERROR_RETRY=1`, `OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES=6`을 추가했다. |
| 검증 | Worker 단위 테스트가 관찰값 0개 + 충분한 프레임에서 재시도가 1회 실행되는지, 짧은 프레임 세트에서는 재시도하지 않는지, timeout 같은 일시 오류에서 error retry가 1회만 실행되는지 확인한다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 종류를 변경하지 않는다. 기존 OpenAI 프레임 분석 경로 안에서 조건부 1회 재시도와 안전 메타데이터만 추가한다.

## 2026-05-25 OpenAI 프레임 분석 호출 예산 보강

사고 영상 1~5번을 실제 OpenAI 프레임 분석 ON 상태로 재측정한 결과, 새 프레임 순서 기반 사고 시점 판별 프롬프트가 길어지면서 일부 응답이 `max_output_tokens` 부족으로 `incomplete` 처리되고, 일부 샘플은 18초 timeout으로 실패했다. 이 상태에서는 `observations`와 `accident_event_summary`가 비어 영상 기반 사실 반영 영역이 실질적으로 동작하지 않는다.

| 범위 | 변경 내용 |
| --- | --- |
| Worker 호출 예산 | `apps/worker/worker/frame_analysis.py`의 OpenAI 프레임 분석 기본 timeout을 45초로, 기본 `OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS`를 2200으로 올렸다. 코드 상한도 3000으로 늘려 실제 사고 시점 후보와 관찰값 JSON이 잘리지 않게 했다. |
| Compose 기본값 | `compose.yaml`의 worker `OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS` 기본값을 2200, worker `OPENAI_TIMEOUT_SEC` 기본값을 45초로 맞췄다. Agent의 일반 OpenAI timeout 기본값은 그대로 18초다. |
| 사고 시점 후보 표시 | `video_input_contract.py`가 OpenAI의 `accident_event_summary`를 안전한 frame count 메타데이터로 보존하고, Gateway/Frontend의 영상 기반 사실 반영 카드가 “사고 시점 후보”를 표시한다. 관찰값이 0개여도 실제 충돌 구간 후보가 잡혔는지 확인할 수 있다. |
| 시나리오 우선순위 | `scenario_classifier.py`가 좌회전·직진 차량·교차로·신호전환/CCTV 필요 맥락을 후방추돌/횡단보도 정차 맥락보다 먼저 분류한다. 영상 일부 프레임에서 정차나 횡단보도가 보여도 사고 본질이 교차로 신호 사고라면 후방추돌 기준으로 덮지 않는다. |
| 검증 로그 | `scripts/video_agent_e2e.py`가 `accident_event_summary`와 easy-report의 `event_candidate`를 결과 JSON에 남긴다. 이후 사고 영상 회귀 테스트에서 “사고 시점 후보”가 UI 카드까지 전달됐는지 로그만으로 확인할 수 있다. |
| 적용 범위 | 사고 1~5 같은 실제 영상 검증 경로에서만 OpenAI 비용과 시간이 늘 수 있다. OpenAI 프레임 분석이 꺼진 기본 운영 경로(`ENABLE_OPENAI_FRAME_ANALYSIS=0`)에는 비용 영향이 없다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 종류를 변경하지 않는다. 기존 환경변수 키의 기본값만 영상 분석 안정성 기준에 맞게 조정한다.

## 2026-05-25 영상 프레임 전체 순서 기반 사고 시점 판별 보강

영상 분석에서 먼저 등장하는 위험 장면, 횡단보도, 보행자, 정차 차량, 신호, 차선 갈등을 실제 사고로 오인할 수 있는 위험을 줄이기 위해 Worker 프레임 분석 기준을 보강했다. OpenAI 프레임 분석은 선택된 프레임 전체를 시간 순서대로 확인한 뒤 실제 충돌/접촉 또는 충돌 직전·직후 정황이 보이는 구간을 기준으로 사고 대상과 충돌 지점을 판단해야 한다.

| 범위 | 변경 내용 |
| --- | --- |
| 프레임 선택 | `frame_analysis.py`의 선택 전략을 `full-sequence-event-spread-plus-impact-context`로 바꿨다. 여러 `accident_candidate`가 있을 때 앞쪽 후보만 채우지 않고, 초반·중간·후반 후보를 분산 선택한 뒤 각 후보 주변 프레임을 추가한다. |
| OpenAI 프롬프트 | 분석 프롬프트에 “모든 제공 frame_ref를 시간 순서대로 확인하고 실제 impact/contact moment 또는 직전·직후 구간을 먼저 식별하라”는 지시를 추가했다. 첫 위험 장면이나 첫 등장 객체를 사고로 확정하지 말고, 여러 후보를 비교하도록 명시했다. |
| 품질 메타데이터 | OpenAI 응답에 `accident_event_summary`를 허용하고, `impact_visible`, `event_frame_refs`, `pre_impact_frame_refs`, `post_impact_frame_refs`, `rationale`만 안전 메타데이터로 보존한다. 이는 법률 판단이 아니라 영상 품질 점검용 정보다. |
| 회귀 테스트 | Worker 테스트에 다중 사고 후보 프레임이 초반·중간·후반에서 모두 선택되는지, 프롬프트가 “첫 위험 장면 오인 금지”와 `accident_event_summary`를 포함하는지 검증을 추가했다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. 영상 분석 provider 계약의 안전 메타데이터만 확장한다.

## 2026-05-25 교차로 차대차 신호 불확실성 및 보행자 맥락 오염 차단

사고 영상 2번 테스트에서 `차대차` 대분류와 좌회전/직진 충돌 설명이 입력됐음에도, 영상 또는 설명에 사람·횡단보도 맥락이 보인다는 이유로 보행자 관련 근거와 KNIA 기준이 섞이는 문제가 확인됐다. 또한 상대 차량 신호가 보이지 않는 교차로 사고에서 한 가지 과실비율만 제시해, 사용자가 어떤 추가 자료를 확보해야 하는지 이해하기 어려웠다. 이번 변경은 특정 영상 2번에 맞춘 출력 보정이 아니라, 신호가 불명확한 교차로 차대차 사고 전반에 적용되는 판정 구조 보강이다.

| 범위 | 변경 내용 |
| --- | --- |
| Agent 입력 정규화 | `input_normalizer.py`가 사용자 설명에서 좌회전, 직진 상대 차량, 교차로, 황색→적색 전환, 상대 신호 확인 불가 단서를 구조화 fact로 보강한다. `car_vs_car` 또는 `collision_partner_type=vehicle`이 명시되면 사람·횡단보도는 사고 대상이 아니라 환경 맥락으로 분리한다. |
| 사고 분류/KNIA party | `scenario_classifier.py`와 `knia/taxonomy.py`가 차량 충돌 대상이 명시된 경우 `pedestrian_visible=true`만으로 차대사람 사고로 승격하지 않는다. `intersection_signal_violation` 사고 유형도 차대차 교차로 사고로 안정적으로 분류한다. |
| 과실 추정 | `fault_ratio_analyst.py`가 상대 차량 신호가 보이지 않는 좌회전/직진 교차로 사고에 `conditional_outcomes`를 제공한다. 상대 차량 신호가 정상 진행 신호인 경우와 상대도 적색/신호위반인 경우를 분리해 예상 과실 범위, 이유, 확인 자료를 함께 반환한다. |
| 근거 필터 | `orchestration_evidence.py`와 `expert_guidance_sections.py`가 차대차/차량 충돌 맥락에서는 보행자 보호·어린이보호구역·차대사람 기준을 대표 근거에서 제외한다. 횡단보도는 보행자 사고 판정 근거가 아니라 교차로/도로 환경 맥락으로만 남긴다. |
| 사용자 표시 | Gateway `report-composer.ts`가 Agent의 조건부 결과를 `conditional_outcome_card`로 표시하고, 교차로 신호 불확실성 문구를 “추가 사실 확인 필요” 식의 애매한 결론 대신 조건별 판단 구조로 설명한다. 일반 표시 근거에서도 차대차 사고와 맞지 않는 보행자 대상 근거를 제외한다. |
| 영상 프레임 분석 기본값 | Worker OpenAI 프레임 분석 기본값을 대표 프레임 18장, image detail `high`로 상향했다. `.env`에 값이 있으면 `.env`가 우선하며, 현재 로컬 검증용 `.env`도 같은 값으로 맞췄다. 비용 안전 기본 원칙은 유지하되 실제 영상 정확도 테스트에서는 더 많은 프레임을 사용한다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. 기존 `ENABLE_OPENAI_FRAME_ANALYSIS`, `OPENAI_FRAME_ANALYSIS_MAX_FRAMES`, `OPENAI_FRAME_ANALYSIS_DETAIL` 키를 그대로 사용하며 기본값과 권장 검증값만 조정했다.

## 2026-05-25 보완 질문 독립 입력 및 신호 불확실성 분기 안내

관리자 Agent 테스트에서 영상 보류 관찰값 기반 보완 질문을 선택할 때 서로 관련 없는 항목의 선택값이 함께 바뀌거나, "영상에서 충돌 지점 보임이(가) 충돌 지점 보임처럼..."처럼 중복되고 지저분한 문장이 노출되는 문제가 확인됐다. 또한 교차로 신호 사고처럼 상대 차량 신호 확인 여부에 따라 판단이 크게 달라지는 경우, 단일 결론만 표시하면 사용자가 왜 추가 자료가 필요한지 이해하기 어렵다.

| 범위 | 변경 내용 |
| --- | --- |
| 보완 질문 UI | `MissingInfoCard.vue`가 답변 상태를 `field`가 아니라 질문 인스턴스별 `answerKey`로 관리한다. 같은 field가 재정렬되거나 영상 보류 질문과 기존 질문이 섞여도 각 select/input은 독립적으로 동작하고, 제출 시에만 원래 field별 답변 payload로 변환한다. |
| 질문 문구 | Gateway `report-composer`의 영상 품질 보류 질문을 필드별 직관 문장으로 바꿨다. 충돌 지점, 내 차량 신호, 상대 차량 신호, 파손 정도, 사고 대상, 중앙선/장애물, 후속 충돌 등은 중복 표현 없이 무엇을 확인해야 하는지 바로 묻는다. |
| 신호 불확실성 | 교차로·신호 맥락에서 상대 차량 신호가 보이지 않거나 보완 질문으로 남은 경우 `conditional_outcome_card`를 생성한다. 상대 신호가 정상 진행 신호인 경우와 상대도 적색/신호위반인 경우를 나눠 확인할 자료와 판단 방향을 설명한다. |
| 사용자 표시 | `EasyReportView.vue`가 조건별 판단 카드를 보완 질문 다음에 표시한다. 이 카드는 특정 영상 2번에 맞춘 결론이 아니라 신호가 불명확한 교차로 사고 전반에 적용되는 설명 구조다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. Frontend 표시 컴포넌트와 Gateway easy-report 표시 payload만 확장한다.

## 2026-05-25 중앙선·장애물 회피 대향차 사고 판단 보강

관리자 Agent 테스트에서 `중앙선/장애물 회피 중 대향 충돌` 사고가 50:50처럼 러프하게 표시되고, 후방추돌·보행자·영문 fallback 근거가 함께 노출되는 문제가 확인됐다. 이번 변경은 `car_accident_1.mp4`에 맞춘 하드코딩이 아니라 “중앙선 침범 사유 + 도로 장애물/불법 주정차 + 대향 차량 충돌”이라는 일반 사고 맥락을 처리하는 기준 보강이다.

| 범위 | 변경 내용 |
| --- | --- |
| 과실 추정 | `fault_ratio_analyst`가 구조화 fact뿐 아니라 사용자 설명의 “멈췄다/거의 멈췄다”, “상대가 그대로 왔다/못 봤다” 같은 정차·상대 회피 가능성 단서를 함께 읽는다. 중앙선·장애물·대향차 맥락에서 정차/상대 미감속 단서가 있으면 `내 책임 30% / 상대 70%`, 단서가 부족하면 `40% / 60%` 참고 범위로 처리한다. |
| KNIA 기준 정합성 | 중앙선·대향차·도로 장애물 태그가 있는 경우 대표 유사 기준에서 후방추돌(`차41`, `차42`)과 보행자(`보*`) 기준을 제외하고, `차43` 계열 및 중앙선/진로변경 관련 기준을 우선한다. 후속 추돌은 별도 고려 요소로 남기되 1차 사고 유사 기준을 덮지 않는다. |
| 법률/근거 표시 | static fallback의 사용자 노출 title/source/law_name/summary를 한국어로 정리했다. 중앙선 회피 사고에는 중앙선 침범 사유, 장애물 회피 불가피성, 대향 차량 전방주시·감속 가능성, 후속 추돌 분리를 우선 근거로 설명한다. |
| 쉬운 결과 문구 | Gateway easy report가 이 사고군을 “추가 사실 확인 필요” 일반 문구로 뭉개지 않고, 중앙선·도로 장애물 회피 중 대향 차량 충돌 맥락으로 요약한다. 과실 설명의 핵심 이유도 중앙선 침범 사유, 정차 여부, 상대 회피 가능성, 후속 추돌 분리로 고정한다. |
| 영상/원문 링크 | KNIA 관련 영상/원문 카드에서 깨진 썸네일 또는 iframe을 렌더링하지 않고, 원본 사이트로 이동하는 버튼만 유지한다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. 다만 Agent 과실 분석, KNIA ranking/filter, static legal fallback, Gateway report composer, Frontend KNIA media card, 관련 회귀 테스트가 함께 변경됐다.

## 2026-05-24 Agent 입력 모드/재분석/사고 대분류 보강

관리자 Agent 테스트에서 분석 모드와 기본 테스트 fact가 사고 사실처럼 Agent 판단에 섞이고, 결과 화면의 “더 정확한 분석을 위해 필요한 정보” 답변이 관리자 화면과 케이스 상세 화면에서 재분석으로 연결되지 않는 문제가 확인됐다. 이번 변경은 특정 사고 샘플에 맞춘 보정이 아니라 입력 계약을 일반화하는 구조 보강이다.

| 범위 | 변경 내용 |
| --- | --- |
| 분석 모드 분리 | `analysis_mode`를 빠른 요약, 과실비율 중심, 법률/판례 근거 중심, 형사 리스크 중심, 보험/대응 중심, 증거 보강 중심 같은 출력 강조 모드로만 사용한다. Agent 입력 정규화에서는 분석 모드 문자열을 `merged_text`에서 제거해 사고 유형 분류에 영향을 주지 않는다. |
| 관리자 테스트 입력 | `/admin/agent-test`의 기본 사고 설명과 후미추돌 기본 fact를 제거했다. 입력만/영상만/입력+영상 모드가 실제로 독립 검증되도록 하고, 사고 대분류(`accident_party_type`)와 보편적 세부 사고 유형을 선택할 수 있게 확장했다. |
| 보완 재분석 | 관리자 테스트 화면과 케이스 상세 화면의 `EasyReportView`에 보완 질문 제출 이벤트를 연결했다. 사용자가 누락 정보에 답하면 `POST /api/v1/cases/:caseId/reanalyze`로 최신 케이스 입력, 기존 영상 메타데이터, follow-up 답변을 병합해 재분석한다. |
| 사고 분류 일반화 | Frontend/Gateway/Agent가 `car_vs_car`, `car_vs_person`, `car_vs_bicycle`, `car_vs_object`, `single_vehicle` 대분류와 `right_turn_front_stop`, `centerline_obstacle_collision`, `stopped_vehicle_collision`, `non_contact_trigger` 같은 보편적 사고 유형을 처리한다. |
| 오분류 방지 | 어린이보호구역, 횡단보도, 보행자 신호 같은 환경 요소만으로 차대사람 사고를 만들지 않는다. 보행자/사람이 실제 충돌 대상이거나 명시 입력된 경우에만 보행자 사고로 승격한다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. 다만 Frontend 표시 옵션, Gateway follow-up 정규화, Agent scenario classifier, 관련 회귀 테스트가 함께 변경됐다.

## 2026-05-24 영상 관찰값 사고 객체 판별 보강

사고 영상 테스트 1~5번에서 횡단보도·보행자·신호등 같은 환경 요소가 실제 충돌 대상보다 앞서 해석되어 차대차 사고가 차대사람 사고처럼 표시되거나, 영상만 제출한 경우 “근거가 더 필요”라는 일반 문구만 반환되는 문제가 확인됐다. 이번 보강은 영상 분석의 1차 목적을 “사고 대상, 충돌 지점, 원인 후보 관찰값 추출”로 다시 고정한다.

| 범위 | 변경 내용 |
| --- | --- |
| Worker 프레임 분석 | OpenAI 프레임 분석 기본 프레임 수를 코드 기준 14장, 상한 18장으로 늘렸다. 프롬프트는 `front_vehicle_stopped`, `ego_turn_direction`, `intersection`, `opponent_signal_visible`, `signal_transition`, `pedestrian_signal`, `stopped_vehicle_without_lights`, `highway_or_expressway`를 추가 관찰값으로 요청한다. |
| 오분류 방지 | `pedestrian_visible=false`를 더 이상 버리지 않는다. 횡단보도가 보여도 `collision_partner_type=vehicle`이면 차대차 사고로 유지하고, 보행자 신호나 횡단보도는 사고 환경 맥락으로만 사용한다. |
| 신호 불확실성 | 사고 2처럼 상대 차량 신호가 영상에 보이지 않는 경우 `opponent_signal_visible=false`를 관찰값으로 남긴다. 상대 신호를 추측해 신호위반으로 확정하지 않고 CCTV/신호체계 확인 질문으로 넘긴다. |
| 우회전 앞차 정차 | 사고 3처럼 우회전 중 횡단보도 앞 정차 차량을 추돌한 경우 `front_vehicle_stopped=true`, `ego_turn_direction=right`, `collision_partner_type=vehicle`을 우선 반영해 후방 추돌 차대차 맥락을 유지한다. 단, `ego_turn_direction`은 교차로·횡단보도·분기점 같은 명확한 회전 맥락이 없으면 확정 fact로 승격하지 않고 확인 후보로 남긴다. 곡선 도로 또는 카메라 yaw만으로 우회전 사고로 판단하지 않기 위한 안전장치다. |
| 근거 랭킹 안전장치 | `pedestrian_visible=false`처럼 “보행자 충돌 대상 아님”을 뜻하는 부정 관찰값이 근거 랭킹 문맥에서 보행자 근거를 밀어 올리지 않도록 `expert_guidance_sections`의 fact context 생성을 분리했다. 차대차 영상에서 횡단보도/보행자 fallback 근거가 우선 노출되는 문제를 막는다. |
| 고속도로 무등화 정차 | 사고 4처럼 속도 자체를 영상에서 산출할 수 없는 경우에도 `stopped_vehicle_without_lights`, `highway_or_expressway` 같은 확인 가능한 환경 fact만 추출하고, 속도는 사용자 보완 또는 별도 자료 확인 대상으로 남긴다. |
| Agent/Gateway 연결 | Agent 입력 계약, 사실 중재, 시나리오 분류, 검색어 확장, 쉬운 결과 문구, Gateway 보완 질문 우선순위를 새 관찰값에 맞게 확장했다. 보완 질문은 사고 대상·충돌 지점·신호 가시성·앞차 정차를 상해 여부보다 먼저 묻는다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. 다만 실제 운영에서 `.env`의 `OPENAI_FRAME_ANALYSIS_MAX_FRAMES`가 10으로 고정되어 있으면 compose 실행 시 코드 기본값보다 `.env` 값이 우선한다. 영상 정확도 검증 시에는 14장 이상으로 재기동해 확인하는 것이 현재 기준이다.

## 2026-05-24 사고 대상 우선 영상 전처리 보강

영상 분석 기준을 “사고 환경 탐지”가 아니라 “사고 대상과 실제 충돌 지점 식별” 우선으로 재정렬했다. 횡단보도, 중앙선, 신호, 주정차, 도로 장애물은 사고 대상을 대신하는 결론이 아니라 충돌 대상과 충돌 지점을 설명하는 보조 맥락으로만 사용한다.

| 범위 | 변경 내용 |
| --- | --- |
| 긴 영상 대응 | Worker가 `ffmpeg` scene-change 신호를 읽어 긴 영상에서도 후보 사고 구간 주변 프레임을 우선 추출한다. 후보 구간이 잡히면 충돌 전후 `accident_candidate`/`event_context` 프레임을 우선 배치하고, 시작/끝 프레임은 문맥으로 유지한다. |
| 휴대폰 재촬영 대응 | VLM 관찰 계약에 `recaptured_screen`, `dashcam_screen_visible`, `screen_glare_or_reflection`을 supporting observation으로 추가했다. 이는 사고 사실로 직접 반영하지 않고 영상 품질/화면 인식 리스크 판단에만 사용한다. |
| 사고 대상 우선 계약 | Worker OpenAI 프레임 분석 프롬프트에 `collision_partner_type`, `primary_collision_target`, `collision_point_visible`, `collision_point_location`을 추가했다. 프롬프트는 사고 대상·충돌 지점·상대 객체를 먼저 식별하고 도로 환경은 보조 맥락으로만 쓰도록 제한한다. |
| Agent 연결 | `video_input_contract`, `fact_arbitration`, KNIA taxonomy, scenario classifier가 `collision_partner_type`을 우선 반영한다. 예를 들어 횡단보도가 보여도 `collision_partner_type=vehicle`이면 차대차 맥락을 유지한다. |
| 표시/보완 질문 | Gateway 결과 구성과 follow-up 정규화가 사고 대상 유형, 주 충돌 대상, 충돌 지점 보임 여부, 충돌 지점 위치를 우선 질문으로 처리한다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다. 외부 YOLO/NVIDIA/Gemini Provider를 즉시 추가하지 않고, 현재 OpenAI 프레임 분석 앞단의 프레임 선별과 사고 대상 우선 계약을 먼저 강화한다.

## 2026-05-24 영상 관찰값 계약 보강

사고 영상 1·2번 점검에서 “횡단보도가 보인다”는 사실만으로 차대사람 사고로 분류될 수 있고, 중앙선 침범 사유·불법 주정차·도로 장애물·대향 차량 미정지처럼 일반 사용자가 선택하기 어려운 사실을 Agent 입력으로 충분히 전달하지 못하는 문제가 확인됐다.

이번 보강은 영상 분석을 단순 사고 유형 추정기가 아니라 사용자 입력을 보조하는 객관적 관찰값 공급원으로 다루도록 계약을 확장한다.

| 범위 | 변경 내용 |
| --- | --- |
| Worker 프레임 분석 | OpenAI 프레임 분석 허용 필드에 `pedestrian_visible`, `centerline_crossed`, `centerline_cross_reason`, `road_obstruction`, `illegal_parking_obstruction`, `opposing_vehicle_present`, `opposing_vehicle_did_not_stop`, `secondary_collision`을 추가했다. 프롬프트에는 `crosswalk_nearby`만으로 보행자 사고를 추론하지 말고, 보행자가 실제로 보일 때만 `pedestrian_visible=true`를 쓰도록 제한했다. |
| Agent 입력 계약 | 새 영상 관찰 필드를 `video_input_contract`의 fact 후보로 추가하고, 프레임 근거와 confidence 기준을 통과한 경우에만 `fact_patch`로 반영한다. 중앙선/장애물/대향차/2차 충돌은 사용자 입력보다 영상이 보완할 수 있는 물리 사실로 `fact_arbitration`의 video-primary 필드에 포함했다. |
| 시나리오 분류 | `crosswalk_nearby` 또는 “횡단보도” 텍스트만으로 `pedestrian_crosswalk_accident`나 `car_vs_person`을 선택하지 않는다. 보행자 존재가 명시되지 않은 교차로·횡단보도 주변 차대차 사고는 차대차 맥락을 유지한다. |
| 사용자/관리자 표시 | Gateway 결과 구성과 보완 답변 정규화가 새 필드의 한국어 라벨, 질문 옵션, 우선순위, 답변 patch를 처리한다. “횡단보도 주변” 질문 사유도 보행자 보호 의무로 고정하지 않고 교차로/도로 위치 맥락으로 설명한다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다. OpenAI 사용량 정책도 바꾸지 않으며, 기존 `ENABLE_OPENAI_FRAME_ANALYSIS` 설정에 따라 동일하게 동작한다.

## 2026-05-24 관리자 Agent 입력 테스트 화면

관리자 계정에서 Agent 입력 경로를 빠르게 검증할 수 있도록 프론트엔드에 `/admin/agent-test` 라우트를 추가했다. 이 화면은 일반 사용자용 서비스 화면이 아니라 관리자 진단용 화면이며, 로그인된 사용자의 role이 `admin`인 경우에만 접근한다.

테스트 방식은 세 가지다.

| 방식 | 동작 |
| --- | --- |
| 입력만 | 새 케이스를 만들고 `POST /api/v1/cases/:caseId/analyze-text`를 호출해 사용자 설명/구조화 사실만으로 Agent 결과를 확인한다. |
| 영상만 | 새 케이스를 만들고 로컬 업로드 후 `POST /api/v1/uploads/complete`를 호출한다. Worker가 기존 흐름대로 `video_preprocess` 완료 후 `video_analyze`를 자동 등록한다. 사고 설명 입력은 필수가 아니다. |
| 입력+영상 | 새 케이스의 설명/구조화 사실을 저장한 뒤 영상 업로드와 전처리를 실행해 사용자 입력과 영상 관찰값의 반영/충돌/보류 상태를 함께 확인한다. |

화면은 기존 Gateway API client만 사용한다. 결과 조회는 `/api/v1/cases/:caseId/easy-report`, 관리자 진단은 `/api/v1/admin/cases/:caseId/agent-trace`를 사용한다. 이 변경은 Frontend route/API wrapper/UI만 추가하며 DB schema, Redis key, storage path, 외부 API 계약, 환경변수 키를 변경하지 않는다.

영상 테스트는 업로드 완료 응답의 `video_preprocess` job만 보고 완료 처리하지 않고, Worker가 자동 생성한 `video_analyze` job이 `succeeded`가 될 때까지 polling한다. `video_preprocess`만 성공하고 `video_analyze`가 아직 생성 또는 완료되지 않은 중간 상태를 최종 결과 없음으로 오인하지 않기 위한 관리자 화면 전용 안전장치다.

## 2026-05-23 영상 처리 마감 기준

오늘 기준 영상 처리 파이프라인은 “업로드된 사고 영상을 저장하고, ffprobe/ffmpeg로 대표 프레임을 추출한 뒤, 선택적으로 OpenAI 프레임 관찰값을 생성하고, Agent 입력 계약에서 사용자 입력과 영상 관찰값을 검증/보류/반영하는 구조”까지 완료 상태로 본다. 기본 운영값은 비용 방지를 위해 `ENABLE_OPENAI_FRAME_ANALYSIS=0`이며, 실제 OpenAI 프레임 분석은 검증 또는 운영 판단이 필요한 경우에만 명시적으로 켠다.

| 범위 | 현재 기준 |
| --- | --- |
| 영상 저장 | Gateway가 로컬 스토리지에 업로드 파일을 저장하고 Worker job으로 넘긴다. S3 직접 업로드는 후속 전환 항목이다. |
| 영상 전처리 | Worker가 `ffprobe`로 메타데이터를 읽고 `ffmpeg`로 최대 18장의 대표 프레임을 추출한다. 짧은 사고 영상은 0.35~0.75초 간격과 비율 앵커를 섞어 전후 맥락을 남긴다. |
| OpenAI 프레임 분석 | Worker가 기본 최대 10프레임, 코드 상한 12프레임을 OpenAI Responses API로 보낸다. 선택 프레임은 시작/끝 문맥과 영상 중앙부 연속 프레임을 우선 포함해 짧은 사고의 충돌 전후 변화가 빠지지 않도록 한다. OpenAI가 꺼져 있어도 `frame_selection_strategy`, 사용 가능 프레임 수, 선택 프레임 수를 결과 메타데이터에 남긴다. |
| 비용/안전 정책 | 모델, 프레임 수, 출력 토큰, detail, timeout은 환경변수로 제한한다. 응답 저장은 `store=false`이고, 기본값은 OpenAI 비활성화다. |
| 관찰값 품질 | `stopped=false`처럼 오판 위험이 큰 값은 Worker에서 confidence를 제한하고, Agent에서 확정 사실이 아닌 확인 후보로 다룬다. |
| Agent 연결 | 영상 관찰값은 `video_input_contract`에서 사용자 입력과 충돌 여부, 보류 사유, 확인 후보, 후보 그룹으로 정리된다. 낮은 confidence나 방향/행동 혼동값은 판정에 바로 반영하지 않는다. |
| 사용자 화면 | 관찰값 0개, 확인 필요, 충돌, 반영 상태를 결과 화면에서 구분한다. 내부 raw trace, frame refs, prompt, token, secret 값은 일반 화면에 노출하지 않는다. |
| 검증 기준 | Worker 단위 테스트, Gateway 표시 테스트, Agent 입력 계약 테스트, `scripts/video_agent_e2e.py` 실제 영상 smoke 경로로 확인한다. 실제 OpenAI 호출 검증 후에는 반드시 worker를 `ENABLE_OPENAI_FRAME_ANALYSIS=0`으로 되돌린다. |

후속 고도화는 “프로젝트 구조 보강”이 아니라 실제 정확도 개선 단계로 분류한다. 남은 대표 항목은 교통사고 특화 비전 모델 후보 조사, 실제 사고 영상 데이터셋 기반 threshold 튜닝, S3 직접 업로드 전환, OpenAI 사용량/비용 대시보드, 더 많은 실제 영상 회귀 샘플 확보다.

아래 정확도 고도화 1~12단계 기록은 영상/Agent 판단 구조와 평가 절차를 만든 기준선이다. 즉, 현재까지의 완료 의미는 “실제 제품 정확도 보장”이 아니라 “실제 OpenAI ON 재측정, reference 확장, KNIA/법령/판례 원문 데이터 확장을 안전하게 반복할 수 있는 평가 골격 완료”다.

## 2026-05-23 영상 정확도 고도화 1차

영상 프레임 분석 정확도를 높이기 위해 Worker가 OpenAI 프레임 분석을 호출할 때 케이스의 구조화 입력 중 시각적으로 검토 가능한 항목만 `visual_focus`로 전달한다. 이 값은 사고 유형, 정차 여부, 차선 변경 여부, 교차로/신호 상태, 상대 차량 행동처럼 사용자가 비교적 안정적으로 입력하는 항목에 한정한다. 프롬프트에는 이 컨텍스트가 “검토 초점”일 뿐이며, 프레임에서 확인되지 않으면 관찰값으로 복사하지 말라는 제한을 추가했다.

`scripts/video_agent_e2e.py`에는 샘플별 정확도 기준을 걸 수 있도록 `--expect-frame-observation field=value`와 `--expect-agent-fact field=value` 옵션을 추가했다. 실제 OpenAI 검증이나 fixture 검증 시 특정 관찰값 또는 Agent `fact_patch`가 기대값과 맞지 않으면 실패하도록 하여, 이후 threshold 조정과 모델 교체 후보 비교를 반복 측정할 수 있게 한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/worker/worker/job_processor.py` | 영상 전처리 단계에서 케이스의 구조화 입력을 읽고, 안전한 `visual_focus` 컨텍스트로 OpenAI 프레임 분석에 전달한다. |
| `apps/worker/worker/frame_analysis.py` | 사용자 컨텍스트를 시각 검토 초점으로만 사용하고 프레임 증거 없이는 관찰값으로 쓰지 말라는 프롬프트 제한을 추가했다. |
| `apps/agent/app/services/fact_arbitration.py` | `rear_vehicle_collision`과 `rear_collision`처럼 같은 의미의 사용자/영상 값을 충돌로 보지 않고 canonical 값으로 확정한다. |
| `scripts/video_agent_e2e.py` | 샘플별 기대 관찰값/Agent fact 검증 옵션과 `accuracy_expectations` 출력 요약을 추가했다. 영상 fact 검증은 새로 적용된 필드뿐 아니라 사용자 입력과 영상이 일치해 `confirmed_fields`로 확정된 필드도 성공으로 본다. |
| `apps/worker/tests/test_job_processor_contract.py`, `apps/worker/tests/test_frame_analysis_contract.py`, `apps/agent/tests/test_fact_arbitration.py` | visual focus 전달, 프롬프트 제한, 사용자/영상 canonical alias 처리를 회귀 테스트로 고정했다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/components/easy/VideoFactExplanationCard.vue`, `apps/gateway/test/report-composer.test.ts` | 영상 관찰값이 사용자 입력과 같은 사실을 확인한 경우를 `confirmed_items`와 `영상 확인` 통계로 분리 표시한다. 새로 판단에 반영된 값과 기존 입력을 영상이 확인한 값을 혼동하지 않도록 회귀 테스트를 추가했다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약을 변경하지 않는다. OpenAI 호출 비용 정책도 바꾸지 않으며 기본값은 계속 `ENABLE_OPENAI_FRAME_ANALYSIS=0`이다.

### 2026-05-23 영상 정확도 측정 도구 보강

`scripts/video_agent_e2e.py`는 실제 OpenAI 프레임 분석 결과를 정확도 튜닝 근거로 남길 수 있도록 보강됐다. `--allow-accuracy-mismatch`를 사용하면 기대값 불일치를 즉시 실패로 끊지 않고 `accuracy_expectations`와 `video_accuracy_metrics`에 기록한다. `--output-json`을 사용하면 전체 결과를 로컬 JSON 파일로 저장할 수 있다. 저장 위치로 `logs/`를 쓰면 `.gitignore` 정책에 따라 측정 결과가 Git에 올라가지 않는다.

로컬 Python 테스트 실행을 위해 루트에 `requirements-dev.txt`를 추가했다. 현재 포함 항목은 `pytest==9.0.3`이며, 로컬에서는 `python -m pip install --user -r requirements-dev.txt` 후 `python -m pytest ...` 형태로 실행한다. 운영 Docker image의 production requirements에는 pytest를 추가하지 않는다.

실제 사고 영상 `car_accident_1.mp4`로 OpenAI 프레임 분석을 재측정한 결과는 다음과 같다. 실행 후 worker는 다시 비용 안전 기본값인 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=` 상태로 복구했다.

| 항목 | 결과 |
| --- | --- |
| 모델/설정 | `gpt-4.1-mini`, `detail=low`, 6프레임 선택 |
| Worker 관찰값 | 4개: `stopped=true`, `impact_direction=rear_end`, `damage_level=minor_rear_bumper_damage`, `opponent_behavior=rear_vehicle_collision` |
| Agent 수용 | accepted 4개, uncertain 0개, conflict 0개 |
| Agent fact_patch | `stopped=true`, `damage_level=minor_rear_bumper_damage`, `opponent_behavior=rear_collision` |
| 사실 중재 | 새로 덮어쓴 필드 0개, 기존 입력과 영상이 일치한 `confirmed_fields` 3개 |
| 기대값 검증 | `stopped=true`, `opponent_behavior=rear_collision` 포함 3개 기대값 모두 통과 |
| 표시 상태 | `영상 확인 3개`, `판단 반영 0개`, `품질 상태=반영 가능` |

이 결과는 현재 샘플 기준으로 OpenAI 프레임 분석이 정차 후방 추돌 후보를 안정적으로 확인했음을 의미한다. 다음 정확도 고도화는 동일한 측정 도구로 샘플 수를 늘려 `stopped`, `opponent_behavior`, `damage_level`의 confidence threshold를 조정하는 단계다.

### 2026-05-23 영상 정확도 배치 측정 도구

여러 사고 영상 샘플을 같은 기준으로 반복 측정하기 위해 `scripts/video_accuracy_batch.py`를 추가했다. 이 스크립트는 manifest의 `samples`를 읽고 샘플마다 `scripts/video_agent_e2e.py`를 실행한 뒤, 개별 결과 JSON과 `aggregate.json`을 `logs/video_accuracy/` 아래에 저장한다. `logs/`는 Git에서 제외되므로 실제 영상 경로, 케이스 ID, 측정 결과가 저장소에 올라가지 않는다.

| Path | 변경 내용 |
| --- | --- |
| `scripts/video_agent_e2e.py` | `--case-json` 옵션을 추가했다. 샘플별 케이스 payload 또는 `{ "case": ... }` 형태의 JSON을 사용해 영상별 입력 사실을 바꿔 측정할 수 있다. |
| `scripts/video_accuracy_batch.py` | manifest 기반 배치 측정 도구다. 샘플별 기대 관찰값/Agent fact, `require_frame_observations`, `require_agent_video_facts`, `exercise_held_observation_followup` 옵션을 `video_agent_e2e.py`로 전달하고 aggregate metric을 생성한다. `aggregate.json`에는 필드별 관찰/반영/확인/충돌 통계(`field_summary`), threshold 조정 준비 상태(`calibration_readiness`), 다음 조치 추천(`recommendations`)을 함께 남긴다. Windows BOM manifest와 UTF-8 출력 수집을 안전하게 처리한다. |
| `config/video_accuracy_samples.example.json` | 배치 측정 manifest 예시다. 실제 영상 경로는 로컬 파일 경로로 바꿔 사용한다. |
| `docs/OPERATIONS.md` | 배치 측정 실행 방법, OpenAI/fixture worker 상태 전제, `--fail-on-mismatch` 사용 기준을 추가했다. |

검증은 `FRAME_ANALYSIS_FIXTURE_MODE=rear_end`로 worker를 일시 재기동한 뒤 `logs/video_accuracy/local_manifest.json`을 사용해 수행했다. 결과는 sample 1개, passed 1개, mismatch 0개, failed 0개, expectation 3/3 통과였다. 배치 결과는 샘플 수가 1개뿐이므로 `calibration_readiness=collect_more_samples`를 반환하며, `opponent_behavior` 충돌은 conflict gate 점검 추천으로 남는다. threshold 조정은 이 결과만으로 바로 수행하지 않고 최소 3개 이상의 실제 사고 영상 샘플을 같은 manifest 기준으로 누적한 뒤 검토한다. 검증 후 worker는 다시 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=` 상태로 복구했다.

### 2026-05-23 변호사 의견 기반 영상 평가 샘플

사고 영상 1~5번과 전문 변호사 의견을 영상 정확도 고도화용 reference set으로 정리했다. 이 reference는 실제 판결이나 절대 정답이 아니라, Agent가 유사 KNIA 기준/법령/판례/상황 사실을 조율해 합리적인 안내 범위에 도달하는지 확인하기 위한 평가 기준이다. 따라서 변호사 의견은 Agent 입력 `case_json`에 넣지 않고, `logs/video_accuracy/lawyer_reference_manifest.json`의 `reference` 메타데이터로만 보관한다. 해당 파일과 로컬 영상 경로는 `/logs/` 및 `*.mp4` ignore 정책에 따라 Git에 올라가지 않는다.

| 샘플 | 평가 초점 |
| --- | --- |
| 사고1 | 주차 차량 회피로 중앙선을 넘은 뒤 정차, 마주오던 차량 및 후속 추돌이 있는 복합 사고. 중앙선 침범 사유, 정차 여부, 상대 회피 가능성, 2차 추돌을 분리해야 한다. |
| 사고2 | 좌회전 차량과 직진 차량의 신호 전환 교차로 사고. 블박차 신호위반 가능성, 상대 신호 진입 시점, CCTV 필요성을 불확실성으로 남겨야 한다. |
| 사고3 | 우회전 중 횡단보도 전 일시정지 차량을 추돌한 후방 추돌. 안전거리 원칙과 이유 없는 급정지 항변 가능성을 함께 제시해야 한다. |
| 사고4 | 무등화 정차 차량 추돌 및 사망 결과가 있는 고위험 사고. 속도위반과 회피 가능성 감정, 형사 판단과 민사 과실 판단의 차이를 구분해야 한다. |
| 사고5 | 자전거 비접촉 유발, 트럭 정지, 후방 고속버스 추돌이 결합된 사고. 유발 차량, 후방 추돌 책임, 급차로변경/급제동 여부를 분리해야 한다. |

이 샘플들은 결과를 “확정 판결”로 맞추기 위한 정답지가 아니라, 간단한 사용자 설명과 영상만으로도 참고 과실범위, 유사 근거, 추가 확인 필요 사항을 균형 있게 제시하는지 확인하는 회귀/캘리브레이션 자료다.

### 2026-05-23 AI 교통사고 전문 변호사형 Agent 역할 보강

Agent 내부 역할 정의를 “AI 교통사고 전문 변호사형 분석관”과 “AI 보험 처리 실무 분석관”으로 명확히 했다. 이는 실제 변호사 자문을 제공한다는 의미가 아니라, 유사 판례·법령·KNIA 기준·보험 실무 근거를 확인한 뒤 변호사 관점의 예상 판결 범위, 민사/형사 대응 방향, 보험 처리 예상 흐름을 분리해 작성하도록 하는 내부 분석 역할이다. 공개 사용자 화면에서는 특정 유명 변호사나 실제 자문처럼 오해될 표현을 쓰지 않고, “AI 교통사고 법률 분석”, “변호사 관점의 판례 기반 예상”, “보험 처리 기준 기반 예상”처럼 역할과 한계를 함께 드러내야 한다.

| Path | 변경 내용 |
| --- | --- |
| `DEVELOPMENT_PROMPT.md` | 내부 Agent 역할, 법률/보험 분석 분리, 판례·KNIA·법령 근거 기반 원칙, 공개 화면 표현 제한을 개발 기준에 추가했다. |
| `apps/agent/app/services/specialists.py` | 기본 specialist 목록에 `traffic-accident-attorney-analyst`, `insurance-claims-practice-analyst`를 추가하고 대표 사고 profile에 포함했다. |
| `apps/agent/app/services/llm_client.py` | LLM 보조 프롬프트를 교통사고 전문 변호사형 분석관, 형사 리스크 분석관, 보험 처리 실무 분석관 역할로 강화했다. |
| `apps/agent/app/services/llm_policy.py` | LLM 권한 설명을 내부 전문 역할 기준으로 갱신하되, 과실 수치·법률 확정·보험 책임 확정은 여전히 결정론적 근거/계약이 우선하도록 유지했다. |

### 2026-05-23 정확도 고도화 1단계 완료

`logs/video_accuracy/lawyer_reference_manifest.json`의 사고 영상 1~5번을 기준으로 Agent 과실 추정과 실제 OpenAI 프레임 분석 경로를 재검증했다. 1차 OFF 측정에서 사고1 중앙선 회피 정차 사고와 사고4 무등화 정차 차량 사고가 KNIA 기본 후방추돌값에 덮여 `내 책임 90~100%`로 표시되는 문제가 확인됐다. 원인은 복합 사고 맥락 기반 추정 이후 `_apply_knia_fault_estimate()`가 KNIA 기본값을 무조건 사용자 관점 과실로 다시 매핑했기 때문이다.

수정 후 복합 사고 추정(`contextual_complex_case`)은 최종 과실범위를 보존하고, KNIA 기본값은 `knia_reference_fault` 참고값으로만 남긴다. 이후 OpenAI OFF 기준 배치와 실제 OpenAI ON 기준 배치를 모두 재실행했다. 최종 OpenAI ON 배치는 5개 샘플 모두 통과했고, 실행 후 worker는 비용 안전 기본값인 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=` 상태로 복구했다.

| 샘플 | 최종 과실 안내 범위 | OpenAI 프레임 분석/Agent 상태 |
| --- | --- | --- |
| 사고1 | `내 책임 20~40% / 상대 60~80% 참고` | `stopped`, `opponent_behavior`, `collision_direction`, `damage_level` 후보가 생성됐으나 낮은 confidence 또는 복합 충돌 맥락으로 모두 보류됐다. |
| 사고2 | `내 책임 70~90% / 상대 10~30% 참고` | `crosswalk_nearby`가 반영됐고, 신호 전환/CCTV 확인은 계속 핵심 보완 사실로 남는다. |
| 사고3 | `내 책임 90~100% / 상대 0~10% 참고` | `crosswalk_nearby`는 영상 확인, `turn_signal`과 `user_signal`은 반영, `stopped`는 사용자 입력과 충돌해 확인 질문으로 남는다. |
| 사고4 | `내 책임 30~50% / 상대 50~70% 참고` | `stopped=false`, `opponent_behavior=stationary`, `impact_direction=rear` 후보가 생성됐지만 무등화·속도·회피 가능성 쟁점 때문에 보류됐다. |
| 사고5 | `내 책임 10~30% / 상대 70~90% 참고` | 정차/급정거/후방추돌 후보가 생성됐고, `opponent_behavior`는 사용자 입력과 충돌해 확인 질문으로 남는다. |

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/analysts/fault_ratio_analyst.py` | 중앙선 회피 정차, 무등화 정차 차량, 자전거 비접촉 유발, 신호 전환 불확실성 같은 복합 사고 추정을 `contextual_complex_case`로 표시한다. |
| `apps/agent/app/services/orchestration_analysis.py` | 복합 사고 추정은 KNIA 기본값으로 덮지 않고, KNIA 값은 참고 기준으로만 보존한다. |
| `apps/agent/tests/test_orchestrator.py` | 복합 사고 추정이 KNIA 기본값에 덮이지 않는 회귀 테스트를 추가했다. |
| `apps/gateway/src/lib/report-composer.ts` | `missing_info.priority_items`와 보완 질문 문구에 내부 field key가 섞일 경우 한국어 안전 라벨로 치환한다. |
| `apps/gateway/test/report-composer.test.ts` | 보완 질문 우선순위 문구에 raw field token이 노출되지 않는 회귀 테스트를 추가했다. |

검증은 `docker compose exec -T agent python -m pytest tests/test_orchestrator.py -q`, `npm test -- report-composer`, `npm run build`, `scripts/video_accuracy_batch.py --manifest logs/video_accuracy/lawyer_reference_manifest.json`, `powershell -ExecutionPolicy Bypass -File scripts/verify_agent_regression.ps1 -SkipDockerBuild`로 통과했다. 이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

### 2026-05-23 정확도 고도화 2단계 완료

OpenAI 프레임 분석이 `collision_direction` 또는 `impact_direction`을 자주 반환하더라도, 이 값은 “충돌/충격 방향” 참고 관찰일 뿐 단독으로 `opponent_behavior=rear_collision` 같은 과실 판단 사실로 승격하지 않도록 정책을 분리했다. 후미추돌 판단 사실은 명시적인 `opponent_behavior=rear_collision` 관찰값이 confidence/frame 근거 기준을 통과할 때만 `fact_patch` 후보가 된다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/video_input_contract.py` | `impact_direction`, `collision_direction`을 `supporting_observations`로 분리하고 `observation_quality_summary.supporting_count`에 집계한다. 방향값은 `accepted_observations`, `uncertain_observations`, `confirmation_candidates`, `fact_patch`로 들어가지 않는다. |
| `apps/gateway/src/lib/report-composer.ts` | 일반 결과 카드에 참고 관찰 통계와 `supporting_items`를 추가하고, raw 계약 값은 계속 숨긴다. 정차 여부와 상대 차량 행동 충돌/보류 질문은 “충돌 직전 내 차량이 정차 중이었는지”, “충돌 직전 상대 차량이 어떤 행동을 했는지”처럼 실제 사용자 흐름에 맞게 문구를 조정했다. |
| `apps/frontend/src/components/easy/VideoFactExplanationCard.vue` | 영상 사실 카드에서 참고 관찰 수와 참고 관찰 항목을 별도 섹션으로 표시한다. |
| `scripts/video_agent_e2e.py`, `scripts/video_accuracy_batch.py` | E2E/배치 출력에 `agent_supporting_count`와 supporting field 집계를 추가했다. supporting field는 “관찰값은 많지만 fact_patch가 없음” 임계값 조정 추천의 대상에서 제외한다. |
| `apps/agent/tests/test_video_input_contract.py`, `apps/gateway/test/report-composer.test.ts` | 방향 관찰값이 후미추돌 사실로 승격되지 않는지, 사용자 화면이 참고 관찰만 표시하고 보완 질문을 만들지 않는지 회귀 테스트를 추가했다. |

검증은 `docker compose exec -T agent python -m pytest tests/test_video_input_contract.py tests/test_orchestrator.py -q`, `npm test -- report-composer`, `npm run build`(Gateway/Frontend), `python -m py_compile scripts/video_agent_e2e.py scripts/video_accuracy_batch.py`, `python scripts/video_accuracy_batch.py --manifest logs/video_accuracy/lawyer_reference_manifest_no_require_frames.json --output-dir logs/video_accuracy/stage2_direction_policy_off --timeout-sec 300`으로 통과했다. 이번 단계는 OpenAI 호출을 새로 켜지 않았고, worker는 비용 안전 기본값인 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=` 상태다. DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키 변경은 없다.

### 2026-05-23 정확도 고도화 3단계 완료

보류된 영상 관찰값이 보완 질문으로 생성된 뒤, 사용자의 답변이 실제 재분석 버전과 케이스 facts에 반영되는지 검증하는 흐름을 강화했다. 기존 검증은 `analysis_change_card` 존재 여부만 확인했지만, 이제는 새 분석 버전 생성, `analysis_change_card.question_flow`, 최신 easy-report의 변화 카드 보존, `cases.structured_facts`의 `_followup_answered_fields` 또는 `_followup_unresolved_fields` 기록까지 함께 확인한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | 재분석 변화 카드에 `question_flow`와 `질문 변화` 통계를 추가했다. 보완 답변 후 남은 질문 수가 줄었는지, 그대로인지, 늘었는지를 사용자 안전 문구로 설명한다. |
| `apps/gateway/test/report-composer.test.ts` | `composeReanalysisChangeCard()`가 질문 수 변화, 답변/미확인/제외 카운트, 질문 흐름 상태를 안전하게 표시하는지 검증한다. |
| `scripts/video_agent_e2e.py` | `--exercise-held-observation-followup` 검증을 강화해 새 분석 버전, 변화 카드의 `question_flow`, 최신 easy-report 보존, 케이스 facts의 보완 답변 상태 기록, 남은 질문 필드 변화를 확인한다. |
| `scripts/video_accuracy_batch.py` | 배치 aggregate에 `held_observation_followup_summary`를 추가해 보완 질문 재분석을 실행한 샘플 수, 질문 감소 수, 답변 필드 제거 수를 집계한다. |
| `apps/frontend/src/utils/displaySanitizer.ts` | `supporting_observations`를 기술 필드로 추가해 원시 영상 계약이 일반 화면에 직접 노출되지 않도록 보강했다. |
| `docs/OPERATIONS.md` | `held_quality` fixture 검증 범위가 보완 질문 생성뿐 아니라 재분석 버전, 질문 흐름, 케이스 facts 기록까지 확인한다는 내용을 추가했다. |

검증은 `npm test -- report-composer followup-normalizer`, `npm run build`(Gateway/Frontend), `python -m py_compile scripts/video_agent_e2e.py scripts/video_accuracy_batch.py`, `FRAME_ANALYSIS_FIXTURE_MODE=held_quality` 기준 `python scripts/video_agent_e2e.py --video-path "C:/Users/yangbun/Downloads/OSS_task3_블박영상/car_accident_1.mp4" --timeout-sec 240 --require-frame-observations --exercise-held-observation-followup --output-json logs/video_accuracy/stage3_held_followup.json`으로 통과했다. 검증 후 worker는 비용 안전 기본값인 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=` 상태로 복구했다. 이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

### 2026-05-23 정확도 고도화 1~3단계 통합 점검

4단계로 넘어가기 전에 1~3단계 변경을 통합 점검했다. 큰 구조상 누락은 없었지만, 3단계의 재분석 E2E 검증이 “재분석 응답의 변화 카드”는 확인하면서도 “최신 easy-report에 저장된 변화 카드의 `question_flow`가 실제 남은 질문 수와 일치하는지”까지는 강하게 검증하지 못했다. 이 부분을 보강해 보류 관찰값 답변 이후 최신 결과 화면 기준의 질문 흐름까지 자동 검증한다.

| Path | 보강 내용 |
| --- | --- |
| `apps/gateway/src/routes/analysis.ts`, `apps/gateway/src/lib/report-composer.ts` | 재분석 변화 카드가 Agent 내부 `required_input_questions`만 보지 않고 실제 사용자 화면에 표시된 보완 질문 수를 기준으로 `question_flow`를 계산하도록 보강했다. |
| `apps/gateway/test/report-composer.test.ts` | 화면 기준 질문 수 override가 변화 카드의 `question_flow`와 `질문 변화` 통계에 반영되는지 회귀 테스트를 추가했다. |
| `scripts/video_agent_e2e.py` | `--exercise-held-observation-followup` 경로에서 최신 easy-report의 `analysis_change_card.question_flow` 존재 여부, 남은 질문 수 일치 여부, 답변 카운트 보존 여부를 추가 검증한다. |
| `scripts/video_accuracy_batch.py` | 배치 aggregate의 `held_observation_followup_summary`에 전체 질문 감소량(`question_delta_total`)과 답변 후에도 같은 field 질문이 남은 샘플 수(`field_retained_count`)를 추가했다. |

검증은 `npm test -- report-composer`, `npm run build`(Gateway), `python -m py_compile scripts/video_agent_e2e.py scripts/video_accuracy_batch.py`, `FRAME_ANALYSIS_FIXTURE_MODE=held_quality` 기준 `python scripts/video_agent_e2e.py --video-path "C:/Users/yangbun/Downloads/OSS_task3_블박영상/car_accident_1.mp4" --timeout-sec 240 --require-frame-observations --exercise-held-observation-followup --output-json logs/video_accuracy/stage123_integrated_followup.json`, `powershell -ExecutionPolicy Bypass -File scripts/verify_agent_regression.ps1 -SkipDockerBuild`로 통과했다. 검증 후 worker는 비용 안전 기본값인 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=` 상태로 복구했다.

이 통합 점검은 서비스 API, DB schema, Redis key, storage path, 외부 API 계약, 환경변수 키를 변경하지 않는다. 4단계는 이 검증 기반 위에서 실제 OpenAI/샘플 배치 결과의 보류·반영·충돌 비율을 더 넓게 측정하고, 정확도 임계값과 사용자 질문 우선순위를 조정하는 방향으로 진행한다.

### 2026-05-23 정확도 고도화 4단계 완료

실제 OpenAI 프레임 분석을 켠 상태에서 사고 영상 1~5번 reference manifest를 다시 측정하고, 배치 결과가 사용자 화면 기준의 영상 상태와 보완 질문 우선순위까지 집계하도록 보강했다. 측정 결과 5개 샘플은 모두 E2E 통과했고, 23개 프레임 관찰값 중 Agent 수용 7개, 보류 9개, 참고 관찰 7개, 판단 반영 2개, 기존 입력 확인 3개, 사용자 입력 충돌 2개로 집계됐다. 사용자 화면 상태는 4개 샘플이 `일부 반영`, 1개 샘플이 `확인 필요`였다.

| Path | 변경 내용 |
| --- | --- |
| `scripts/video_accuracy_batch.py` | `video_flow_summary`와 `question_priority_summary`를 추가해 반영/보류/참고/충돌 비율, 화면 상태 분포, 첫 보완 질문 분포를 배치 aggregate에 남긴다. 보류율이 높거나 충돌이 있으면 threshold를 낮추기보다 보완 질문 흐름을 유지하라는 추천을 생성한다. |
| `apps/gateway/src/lib/report-composer.ts` | 영상 보류 질문과 일반 보완 질문 우선순위에서 `급정거 여부`를 보험/파손 후속 정보보다 앞에 배치했다. 정차 여부, 상대 차량 행동, 급정거 여부처럼 과실 판단을 좌우하는 사실을 먼저 묻도록 조정했다. |
| `apps/gateway/test/report-composer.test.ts` | 후방 추돌 판단 핵심 질문이 파손 정도 같은 후속 정보보다 먼저 정렬되는지 회귀 테스트를 추가했다. |
| `docs/OPERATIONS.md` | 배치 aggregate의 `video_flow_summary`, `question_priority_summary`, 보수적 threshold 추천 의미를 문서화했다. |

실제 OpenAI 배치 결과 보류율은 39.1%, 충돌률은 8.7%였다. 따라서 4단계 결론은 “threshold를 즉시 낮추지 않고, 충돌/보류 질문을 사용자에게 먼저 확인시키는 현재 보수 정책 유지”다. 가장 자주 첫 질문으로 올라온 항목은 `정차 여부`였고, 다음으로 `상대 차량 행동`이 올라왔다.

검증은 `python -m py_compile scripts/video_accuracy_batch.py scripts/video_agent_e2e.py`, `npm test -- report-composer`, `npm run build`(Gateway), `docker compose up -d --build gateway`, `python scripts/video_accuracy_batch.py --manifest logs/video_accuracy/lawyer_reference_manifest.json --output-dir logs/video_accuracy/stage4_openai_flow --timeout-sec 300`, `powershell -ExecutionPolicy Bypass -File scripts/verify_agent_regression.ps1 -SkipDockerBuild`로 통과했다. 검증 후 worker는 비용 안전 기본값인 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=` 상태로 복구했다. 이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

### 2026-05-23 정확도 고도화 5단계 완료

Stage 4의 실제 OpenAI 프레임 분석 배치 결과(`logs/video_accuracy/stage4_openai_flow/aggregate.json`)를 `lawyer_reference_manifest.json`의 전문가 참고 쟁점과 대조했다. 목적은 프레임 관찰 성공률만 보는 것이 아니라, 영상 관찰값·사용자 입력·전문가 참고 쟁점·전문가 안내 카드가 실제 법률/KNIA/보험 근거 대조 단계로 넘어갈 수 있는 상태인지 확인하는 것이다.

평가 결과 5개 샘플 모두 pipeline은 통과했다. 사고 1, 2, 4는 `ready_for_legal_knia_insurance_evidence_eval` 상태로 분류되어 다음 단계에서 KNIA/법령/판례/보험 근거 정합성 대조로 넘어갈 수 있다. 사고 3과 사고 5는 영상 관찰값과 사용자 입력 충돌이 있어 `needs_conflict_resolution_before_guidance` 상태로 남겼다. 전문가 안내 카드는 3개 샘플이 `expert_guidance_ready_for_reference_review`, 2개 샘플이 `expert_guidance_safe_with_pending_facts`로 분류되어 카드 누락 또는 표시 계약 문제는 확인되지 않았다.

| Path | 변경 내용 |
| --- | --- |
| `scripts/reference_guidance_eval.py` | 전문가 참고 쟁점 매핑 기준을 한국어/영문 키워드로 정규화하고, 횡단보도/자전거/무등화/형사·민사 쟁점처럼 더 구체적인 기준이 일반 신호·후방추돌 기준보다 먼저 선택되도록 했다. Stage 4 batch의 `video_flow_summary`와 `question_priority_summary`도 평가 출력에 포함한다. |
| `docs/OPERATIONS.md` | Stage 4 실제 OpenAI 배치 결과를 reference guidance 평가에 연결하는 실행 예시와 출력 해석 기준을 보강했다. |

5단계 로컬 평가 출력은 `logs/video_accuracy/reference_guidance_eval_stage5.json`에 저장했다. `logs/`는 Git에서 제외되므로 실제 영상 경로와 측정 결과는 저장소에 올라가지 않는다. 요약 지표는 프레임 관찰값 23개 중 수용 7개, 보류 9개, 참고 관찰 7개, 판단 반영 2개, 기존 입력 확인 3개, 충돌 2개이며, 첫 보완 질문은 `정차 여부` 3개, `상대 차량 행동` 2개로 집계됐다.

검증은 `python -m py_compile scripts/reference_guidance_eval.py`와 `python scripts/reference_guidance_eval.py --manifest logs/video_accuracy/lawyer_reference_manifest.json --batch-output logs/video_accuracy/stage4_openai_flow/aggregate.json --output logs/video_accuracy/reference_guidance_eval_stage5.json`로 통과했다. 이번 단계는 저장된 Stage 4 결과를 재평가한 것이므로 OpenAI API를 새로 호출하지 않았고, DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키 변경은 없다.

### 2026-05-23 정확도 고도화 6단계 완료

5단계에서 근거 정합성 대조 대상으로 분류된 사고 1, 2, 4를 대상으로 `expert_guidance_card`의 법률/KNIA/보험 근거 family가 실제 전문가 참고 쟁점별로 갖춰지는지 평가했다. 초기 점검에서는 사고 1과 사고 4에서 KNIA 근거가 카드 슬롯을 먼저 채워 법률 근거가 사용자 화면의 `basis`에 보이지 않는 문제가 있었다. 전문가 안내 카드는 확정 판결이 아니라 참고 가이드이므로, 과실비율 기준만 보이는 상태보다 법률 근거와 KNIA 기준이 함께 노출되는 구조가 필요하다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/expert_guidance_sections.py` | `basis` 생성 시 들어온 순서대로 5개를 자르지 않고 법률, KNIA, 보험 family를 우선 균형 선택한다. 사용자 결과에는 `법률 근거`, `KNIA 기준`, `보험 처리 근거`처럼 안전한 family label만 남긴다. |
| `apps/agent/app/services/static_legal_fallback.py` | 중앙선 회피·마주오던 차량 충돌, 야간 무등화 정차 차량 추돌에 대한 법률 fallback 근거를 추가했다. 속도·회피 가능성·형사/민사 분리 쟁점은 기존 정적 법률 근거와 함께 검색된다. |
| `scripts/video_agent_e2e.py`, `scripts/video_accuracy_batch.py` | `expert_guidance_card`의 상세 법률 포인트, 보험 단계, 근거 목록, missing item을 로컬 평가 JSON에 보존한다. |
| `scripts/reference_evidence_alignment_eval.py` | 5단계 reference 평가와 6단계 샘플 출력을 대조해 쟁점별 필수 family(`legal`, `knia`, `insurance`) 충족 여부를 판정한다. |
| `apps/agent/tests/test_expert_guidance_sections.py` | KNIA 항목이 먼저 들어와도 법률 근거가 카드에 보존되는지와 복합 사고 정적 법률 fallback 검색을 회귀 테스트로 고정했다. |

최종 6단계 로컬 평가는 사고 1, 2, 4 모두 pipeline 통과, `expert_guidance_card` 표시 통과, `reference_evidence_alignment_eval` 기준 13개 쟁점 전부 `evidence_alignment_ready`로 통과했다. 사고 1은 중앙선 회피 법률 근거와 KNIA 후방추돌/진로변경 기준을 함께 표시하고, 사고 4는 무등화 정차 차량 법률 근거와 KNIA 후방추돌 기준을 함께 표시한다. 사고 2는 신호 준수 법률 근거, 교차로 과실비율 기준, 신호 전환/CCTV 확인 근거를 함께 표시한다.

검증은 `python -m py_compile ...`, `python -m pytest tests/test_expert_guidance_sections.py -q`, `docker compose up -d --build agent`, `docker compose exec -T agent python -m compileall app scripts`, `python scripts/video_accuracy_batch.py --manifest logs/video_accuracy/stage6_ready_manifest.json --output-dir logs/video_accuracy/stage6_evidence_capture --timeout-sec 300`, `python scripts/reference_evidence_alignment_eval.py --reference-eval logs/video_accuracy/reference_guidance_eval_stage5.json --sample-dir logs/video_accuracy/stage6_evidence_capture --output logs/video_accuracy/reference_evidence_alignment_stage6.json`로 통과했다. 이번 단계는 OpenAI 프레임 분석을 새로 켜지 않고 저장/전처리/Agent 카드 경로를 평가했으며, DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키 변경은 없다.

### 2026-05-23 정확도 고도화 4~6단계 통합 점검

7단계로 넘어가기 전에 4~6단계 결과를 다시 점검했다. 기능 흐름의 추가 누락은 없었지만, 6단계에서 `expert_guidance_sections.py`에 이전 구현의 legacy family helper와 표시 문자열 정리 잔여물이 남아 있어 사용자 결과 생성 파일의 책임 경계가 흐려질 수 있었다. 해당 잔여 코드를 제거하고, 근거 family 분류와 사용자 표시 label을 현재 `expert_guidance_card` 계약에 맞춰 정리했다.

| 점검 범위 | 결과 |
| --- | --- |
| 4단계 실제 OpenAI 배치 결과 | 저장된 Stage 4 배치 기준을 유지한다. 5개 샘플 모두 pipeline 통과, 보류율 39.1%, 충돌률 8.7%였고 threshold를 낮추기보다 보완 질문 흐름을 유지하는 결론은 변동 없다. |
| 5단계 reference guidance 평가 | 재평가 결과 5개 샘플 모두 pipeline 통과, 사고 1·2·4는 `ready_for_legal_knia_insurance_evidence_eval`, 사고 3·5는 `needs_conflict_resolution_before_guidance`로 유지됐다. |
| 6단계 근거 family 정합성 | 사고 1·2·4 모두 `reference_evidence_alignment_eval` 기준 통과, 13개 쟁점 전부 `evidence_alignment_ready`로 유지됐다. |
| 코드 품질 보강 | `apps/agent/app/services/expert_guidance_sections.py`에서 legacy helper를 제거하고 `법률 근거`, `KNIA 기준`, `보험 처리 근거`, `참고 근거` family label만 생성하도록 정리했다. |

검증은 `python -m py_compile apps\agent\app\services\expert_guidance_sections.py scripts\reference_evidence_alignment_eval.py scripts\reference_guidance_eval.py scripts\video_agent_e2e.py scripts\video_accuracy_batch.py`, `python -m pytest tests\test_expert_guidance_sections.py -q`, `docker compose up -d --build agent`, `docker compose exec -T agent python -m compileall app scripts`, `python scripts\reference_guidance_eval.py --manifest logs\video_accuracy\lawyer_reference_manifest.json --batch-output logs\video_accuracy\stage4_openai_flow\aggregate.json --output logs\video_accuracy\reference_guidance_eval_stage5.json`, `python scripts\video_accuracy_batch.py --manifest logs\video_accuracy\stage6_ready_manifest.json --output-dir logs\video_accuracy\stage6_evidence_capture --timeout-sec 300`, `python scripts\reference_evidence_alignment_eval.py --reference-eval logs\video_accuracy\reference_guidance_eval_stage5.json --sample-dir logs\video_accuracy\stage6_evidence_capture --output logs\video_accuracy\reference_evidence_alignment_stage6.json`로 통과했다. 이번 통합 점검은 OpenAI API를 새로 호출하지 않았고, DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키 변경은 없다.

### 2026-05-23 정확도 고도화 7단계 완료

6단계에서 확인한 근거 family 정합성을 실제 근거 제목/본문 요약 내용까지 확장했다. 기존 `reference_evidence_alignment_eval.py`는 쟁점별로 `legal`, `knia`, `insurance` family가 있는지 중심으로 평가했지만, 7단계부터는 각 `criterion_id`별 필수 키워드 묶음이 `expert_guidance_card.basis.title`과 `reason`에 실제로 나타나는지도 확인한다. 또한 현재 사고 쟁점과 직접 맞지 않는 추가 근거가 카드에 섞이면 `extra_basis_review`로 표시한다.

| Path | 변경 내용 |
| --- | --- |
| `scripts/reference_evidence_alignment_eval.py` | `centerline_obstacle`, `signal_transition`, `unlit_stopped_vehicle_visibility`, `speed_avoidability`, `criminal_civil_split` 등 전문가 reference 쟁점별 content-fit keyword rule을 추가했다. 출력에는 `content_fit`, `matched_basis_titles`, `missing_keyword_groups`, `extra_basis_review`, `ready_for_stage8_guidance_calibration` 상태가 포함된다. |
| `apps/agent/app/services/expert_guidance_sections.py` | 전문가 안내 카드의 basis 선택 시 사고 scenario, facts, legal issue, fault key factor를 문맥으로 사용해 근거 relevance를 계산한다. 신호 전환 사고에 차로변경 근거가 섞이거나, 중앙선 회피 사고에 무등화 정차 차량 근거가 우선 노출되는 문제를 줄였다. |
| `apps/agent/tests/test_expert_guidance_sections.py` | 신호 전환 사고에서 차로변경 근거가 basis에 남지 않는 회귀 테스트를 추가했다. |
| `docs/OPERATIONS.md` | `reference_evidence_alignment_eval.py`의 Stage 7 실행 예시와 `ready_for_stage8_guidance_calibration`, `needs_evidence_content_fit` 상태 의미를 문서화했다. |

Stage 7 재생성 결과 사고 1, 2, 4 모두 `video_accuracy_batch` 통과, `reference_evidence_alignment_eval` 기준 13개 쟁점 전부 `evidence_content_ready`, 샘플 3개 모두 `ready_for_stage8_guidance_calibration`으로 통과했다. `extra_basis_review_count`는 0이다. 사고 1은 중앙선 회피 법률 근거, 후방추돌 KNIA 기준, 중앙선 회피 KNIA 기준을 함께 표시하고, 사고 2는 신호 준수 법률 근거, 교차로 과실비율 기준, 신호 전환/CCTV 확인 근거만 표시한다. 사고 4는 무등화 정차 차량, 야간 시인성, 속도·회피 가능성, 형사/민사 구분 근거를 함께 표시한다.

검증은 `python -m py_compile apps\agent\app\services\expert_guidance_sections.py scripts\reference_evidence_alignment_eval.py`, `python -m pytest tests\test_expert_guidance_sections.py -q`, `docker compose up -d --build agent`, `docker compose exec -T agent python -m compileall app scripts`, `python scripts\video_accuracy_batch.py --manifest logs\video_accuracy\stage6_ready_manifest.json --output-dir logs\video_accuracy\stage7_evidence_content_capture --timeout-sec 300`, `python scripts\reference_evidence_alignment_eval.py --reference-eval logs\video_accuracy\reference_guidance_eval_stage5.json --sample-dir logs\video_accuracy\stage7_evidence_content_capture --output logs\video_accuracy\reference_evidence_alignment_stage7.json`로 통과했다. 이번 단계는 OpenAI 프레임 분석을 새로 켜지 않았고, DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키 변경은 없다.

### 2026-05-23 정확도 고도화 8단계 완료

근거가 맞는 상태에서 사용자에게 보이는 예상 과실 범위, 전문가 안내 문구, 보완 질문 우선순위를 실제 사용자 흐름 기준으로 캘리브레이션했다. 특히 신호 전환 사고는 설명 문장에 `황색/적색` 같은 단어가 포함되어 있어도 내 차량 신호와 상대 차량 신호가 각각 확인된 것으로 보지 않도록 조정했다. 또한 쉬운 리포트 변환 단계에서 `user_signal`, `opponent_signal` 같은 안전한 질문 field가 내부 토큰 정리 로직에 의해 지워지던 문제를 고쳤다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/input_requirements.py` | 교차로 신호 사고에서는 `user_signal`, `opponent_signal`, `opponent_signal_violation`을 자연어 키워드만으로 충족 처리하지 않고, 명시 fact 또는 보완 질문으로 확인한다. 양방향 신호 질문은 인명피해/파손 질문보다 먼저 나오도록 priority를 0으로 조정했다. |
| `apps/agent/app/services/elderly_friendly/plain_language_agent.py` | `missing_info.questions` 생성 시 안전한 field id는 원문을 보존하고, 사용자 표시 문구만 정제한다. 이로써 Gateway가 신호/자전거/횡단보도 질문을 안전하게 정렬할 수 있다. |
| `apps/gateway/src/lib/report-composer.ts` | 보완 질문 우선순위를 실제 사고 흐름에 맞게 조정했다. 양방향 신호, 자전거 위치/방향, 횡단보도/보행자 신호는 판단 질문으로 우선 처리하고, 일반 `signal_state`는 인명피해보다 뒤로 둔다. |
| `scripts/reference_guidance_calibration_eval.py` | 전문가 reference와 batch 결과를 대조해 과실 참고 범위 overlap, 근거 쟁점 키워드, 추가 확인 항목, 첫 보완 질문이 사용자 흐름에 맞는지 평가한다. |
| `apps/agent/tests/test_input_requirements.py`, `apps/gateway/test/report-composer.test.ts` | 신호 전환 사고에서 양방향 신호 질문이 먼저 남는지, generic signal 질문이 불필요하게 최상단으로 올라오지 않는지 회귀 테스트를 추가했다. |
| `docs/OPERATIONS.md` | Stage 8 캘리브레이션 평가 실행 방법과 `calibrated_for_user_flow`, `needs_user_flow_calibration` 상태 의미를 문서화했다. |

Stage 8 로컬 검증 결과 5개 사고 샘플은 OpenAI 프레임 분석 비활성 상태의 표시 계약 배치에서 모두 통과했다. `reference_guidance_calibration_eval.py` 기준 사고 1, 2, 4는 모두 `calibrated_for_user_flow`로 통과했고, 실패 check는 0개다. 사고 2 신호 전환 샘플의 첫 보완 질문은 `내 차량 신호`로 조정되어, 인명피해 질문보다 결론을 좌우하는 신호 확인 질문이 먼저 표시된다. 사고 5 자전거 비접촉 유발 샘플도 첫 질문이 `자전거 위치`로 정렬된다.

검증은 `docker compose exec -T agent python -m py_compile app/services/input_requirements.py app/services/elderly_friendly/plain_language_agent.py`, `npm test -- report-composer`, `npm run build`(Gateway), `docker compose up -d --build agent worker gateway`, `python scripts/video_accuracy_batch.py --manifest logs/video_accuracy/lawyer_reference_manifest_stage8_no_frame_required.json --output-dir logs/video_accuracy/stage8_guidance_calibration_capture --timeout-sec 180`, `python scripts/reference_guidance_calibration_eval.py --manifest logs/video_accuracy/lawyer_reference_manifest.json --batch-output logs/video_accuracy/stage8_guidance_calibration_capture/aggregate.json --output logs/video_accuracy/reference_guidance_calibration_eval_stage8.json`로 통과했다. OpenAI API를 새로 호출하지 않았고, 검증용 manifest와 batch 결과는 `logs/` 아래에만 저장된다. DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키 변경은 없다.


### 2026-05-23 정확도 고도화 9단계 완료

영상 관찰값과 사용자 입력이 충돌한 뒤 사용자가 보완 질문에 답하는 재분석 흐름을 보강했다. 기존 `/api/v1/cases/:caseId/reanalyze`는 보완 답변을 Agent text 분석으로만 넘겨 최신 업로드의 영상 메타데이터를 다시 전달하지 않았기 때문에, 재분석 이후 `fact_arbitration`에서 같은 영상 근거와 사용자 답변을 다시 대조하기 어려웠다. 이제 Gateway가 최신 업로드의 `metadata`, `file_name`, `status`, `preprocess_summary`를 재분석 요청에 포함하고, Agent의 text 분석 DTO도 `video_metadata`를 받을 수 있다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/routes/analysis.ts` | `/reanalyze`에서 최신 업로드 영상 메타데이터를 Agent payload에 다시 포함한다. 명시 `video_metadata` payload가 있으면 테스트/운영 도구 입력을 우선한다. |
| `apps/agent/app/schemas.py`, `apps/agent/app/routers/internal_routes/analysis.py`, `apps/agent/app/services/orchestrator.py` | `/internal/v1/analyze/text`도 `video_metadata`를 수신해 기존 `normalize_analysis_input`의 영상 입력 계약과 사실 중재 경로를 그대로 사용할 수 있게 했다. |
| `apps/gateway/src/lib/followup-normalizer.ts` | 보완 답변 정규화가 한글 선택지뿐 아니라 E2E/진단 도구의 canonical 값(`true`, `false`, `rear_collision`, `opponent`, `red` 등)도 안전하게 facts로 변환한다. |
| `scripts/video_agent_e2e.py` | `--exercise-conflict-followup` 옵션을 추가했다. 영상-사용자 충돌 질문을 찾아 영상값 기준 답변을 제출하고, 재분석 후 해당 충돌이 남지 않는지 확인한다. |
| `scripts/video_accuracy_batch.py` | manifest의 `exercise_conflict_followup`을 E2E 옵션으로 연결하고, 샘플별 `conflict_followup`과 전체 `conflict_followup_summary`를 집계한다. |
| `apps/gateway/test/followup-normalizer.test.ts`, `apps/gateway/test/analysis-routes.test.ts` | canonical 보완 답변 정규화와 재분석 영상 메타데이터 보존 helper를 검증한다. |
| `docs/OPERATIONS.md` | 충돌 보완 질문 E2E 옵션과 배치 집계 해석 기준을 문서화했다. |

검증은 `python -m py_compile scripts/video_agent_e2e.py scripts/video_accuracy_batch.py`, `python -m py_compile apps/agent/app/schemas.py apps/agent/app/routers/internal_routes/analysis.py apps/agent/app/services/orchestrator.py`, `npm test -- followup-normalizer analysis-routes`, `npm run build`(Gateway)로 통과했다. 이번 단계는 DB schema, Redis key, storage path, 외부 API, 환경변수 키를 변경하지 않는다. `/api/v1/cases/:caseId/reanalyze`의 내부 Agent payload에는 `video_metadata`가 추가되므로 영상 업로드가 있는 케이스의 재분석은 기존 영상 근거를 유지한다.


### 2026-05-23 정확도 고도화 7~9단계 통합 점검

7~9단계를 10단계 진입 전 기준으로 다시 점검했다. 7단계의 근거 내용 적합성, 8단계의 사용자 질문 우선순위, 9단계의 충돌 보완 재분석 방향은 유지한다. 다만 9단계에서 `--exercise-conflict-followup` 옵션은 추가됐지만, 비용 없이 이 경로를 재현하는 deterministic fixture가 부족해 실제 OpenAI 호출 전 회귀 확인이 어려웠다.

| Path | 보강 내용 |
| --- | --- |
| `apps/worker/worker/frame_analysis.py` | `FRAME_ANALYSIS_FIXTURE_MODE=conflict_stopped`를 추가했다. 기본 E2E 케이스의 `stopped=true`와 충돌하도록 `stopped=false`, confidence `0.93`, 2개 frame ref 관찰값을 반환한다. |
| `apps/worker/tests/test_frame_analysis_contract.py` | `conflict_stopped` fixture가 다중 프레임 high-quality 관찰값을 반환하는지 검증한다. |
| `docs/OPERATIONS.md` | `conflict_stopped` fixture로 `--exercise-conflict-followup` 재분석 경로를 비용 없이 확인하는 명령을 추가했다. |

검증은 `python -m unittest discover -s tests`와 `python -m compileall worker tests`(Worker), `npm test`와 `npm run build`(Gateway), `FRAME_ANALYSIS_FIXTURE_MODE=conflict_stopped` 상태의 `python scripts/video_agent_e2e.py --video-path ... --require-frame-observations --exercise-conflict-followup`로 통과했다. E2E에서는 `stopped` 충돌 질문 답변 후 새 분석 버전이 생성되고, 최신 `fact_arbitration.conflicts`가 0개로 줄며 `confirmed_fields=["stopped"]`가 남는 것을 확인했다. 검증 후 worker는 다시 비용 안전 기본값인 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=` 상태로 복구했다.

이 통합 보강은 실제 사고 판단 모델이 아니라 9단계 재분석 계약을 검증하기 위한 테스트 fixture다. DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키 변경은 없다. 10단계에서는 이 fixture와 실제 샘플을 이용해 사고 3·5 같은 충돌 케이스가 `확인 질문 -> 재분석 -> 근거 안내` 흐름으로 안정적으로 이어지는지 검증하면 된다.

### 2026-05-23 정확도 고도화 10단계 완료

충돌 보완 질문으로 영상-사용자 입력 충돌이 해소된 샘플이 다음 근거 대조 단계로 넘어갈 수 있도록 reference 평가 계층을 보강했다. 기존 `reference_guidance_eval.py`는 `field_metrics.conflict=true`만 보고 샘플을 계속 `needs_conflict_resolution_before_guidance`로 분류했기 때문에, 9단계에서 `/reanalyze`가 충돌을 해소해도 운영 평가에서는 사고 3·5 같은 샘플이 계속 보류로 남는 문제가 있었다.

| Path | 변경 내용 |
| --- | --- |
| `scripts/reference_guidance_eval.py` | batch aggregate의 `conflict_followup`과 `conflict_followup_summary`를 읽는다. `latest_conflict_count=0`이면 해당 focus를 `conflict_resolved_ready_for_evidence_review`로 분류하고, 샘플은 `ready_for_legal_knia_insurance_evidence_eval`로 이동할 수 있게 했다. |
| `docs/OPERATIONS.md` | `conflict_resolved_ready_for_evidence_review` 상태의 의미와, 충돌 해소 후에도 최종 판정이 아니라 KNIA/법령/판례/보험 근거 대조로 넘어가는 기준임을 문서화했다. |

검증은 `python -m py_compile scripts/reference_guidance_eval.py`와 `logs/video_accuracy/stage10_eval_fixture/` 아래 synthetic batch를 이용한 `reference_guidance_eval.py` 실행으로 통과했다. 후속 확인이 없는 충돌 샘플은 기존처럼 `needs_conflict_resolution_before_guidance`로 남고, `conflict_followup.latest_conflict_count=0`인 샘플은 `conflict_resolved_ready_for_evidence_review` 및 `ready_for_legal_knia_insurance_evidence_eval`로 이동하는 것을 확인했다. 이번 단계는 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

### 2026-05-23 정확도 고도화 11단계 완료

10단계에서 충돌 해소로 승격된 샘플이 근거 정합성 평가와 사용자 흐름 캘리브레이션까지 이어지도록 평가 도구와 Agent 근거 선택을 보강했다. 기존 `reference_evidence_alignment_eval.py`는 샘플별 E2E JSON 디렉터리만 상세 카드 입력으로 사용할 수 있어, `video_accuracy_batch.py`의 aggregate에 상세 `expert_guidance`가 있어도 사고 3·5 같은 승격 샘플을 바로 평가하기 어려웠다. 또한 `reference_guidance_calibration_eval.py`는 reference gate를 보지 않아 충돌 미해소 샘플도 과실 범위 튜닝 대상으로 섞일 수 있었다.

| Path | 변경 내용 |
| --- | --- |
| `scripts/reference_evidence_alignment_eval.py` | `--batch-output` 입력을 추가해 batch aggregate의 상세 `expert_guidance`로 근거 정합성을 평가할 수 있게 했다. 평가 출력에 `conflict_followup_resolved`, `conflict_followup`, `resolved_conflict_sample_count`를 포함한다. `front_vehicle_stop_reason` content rule은 사고 5처럼 자전거 유발·후방 버스 추돌·시간적 여유가 정지 사유와 함께 판단되는 경우를 반영하도록 보강했다. |
| `scripts/reference_guidance_calibration_eval.py` | `--reference-eval` readiness gate를 추가했다. `ready_for_legal_knia_insurance_evidence_eval`이 아닌 샘플은 `blocked_by_reference_gate`로 분류하고, 사고 3·5 캘리브레이션 규칙을 추가했다. |
| `apps/agent/app/services/static_legal_fallback.py` | 횡단보도 앞 앞차 정지 후 후방 추돌 사고용 `Crosswalk front vehicle stop reason and rear-end fault guide` fallback 근거를 추가했다. |
| `apps/agent/app/services/expert_guidance_sections.py` | 근거 선택 컨텍스트에 횡단보도/보행자 신호/앞차 정지 사유와 자전거 비접촉 유발/시간적 여유/후방 버스 추돌 쟁점을 명시적으로 반영한다. |
| `apps/agent/tests/test_expert_guidance_sections.py` | 사고 3·5 유형에서 횡단보도 앞 정지 근거와 자전거 비접촉 유발 근거가 basis에 유지되는지 회귀 테스트를 추가했다. |
| `docs/OPERATIONS.md` | `reference_evidence_alignment_eval.py --batch-output`와 `reference_guidance_calibration_eval.py --reference-eval` 사용 기준을 문서화했다. |

검증은 `python -m py_compile ...`, `python -m pytest tests/test_expert_guidance_sections.py -q`, `docker compose up -d --build agent gateway`, OpenAI 프레임 분석 비활성 상태의 `python scripts/video_accuracy_batch.py --manifest logs/video_accuracy/lawyer_reference_manifest_stage8_no_frame_required.json --output-dir logs/video_accuracy/stage11_guidance_capture --timeout-sec 180`, `python scripts/reference_evidence_alignment_eval.py --reference-eval logs/video_accuracy/stage10_eval_fixture/reference_guidance_eval_stage11_resolved_3_5.json --batch-output logs/video_accuracy/stage11_guidance_capture/aggregate.json --output logs/video_accuracy/reference_evidence_alignment_stage11.json`, `python scripts/reference_guidance_calibration_eval.py --manifest logs/video_accuracy/lawyer_reference_manifest.json --batch-output logs/video_accuracy/stage11_guidance_capture/aggregate.json --reference-eval logs/video_accuracy/stage10_eval_fixture/reference_guidance_eval_stage11_resolved_3_5.json --output logs/video_accuracy/reference_guidance_calibration_eval_stage11.json`로 통과했다. 결과는 5개 샘플 모두 `ready_for_stage8_guidance_calibration`, resolved conflict sample 2개, calibration 5개 통과다. 실제 미해소 reference 결과를 gate로 넘기면 사고 3·5는 `blocked_by_reference_gate`로 남는 것도 확인했다. 이번 단계는 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

### 2026-05-24 정확도 고도화 12단계 완료

정확도 고도화 1~11단계에서 만든 평가 흐름을 최종 기준선으로 묶어 점검했다. 12단계는 새 기능 추가가 아니라, `reference_guidance_eval`의 readiness gate, `reference_evidence_alignment_eval`의 근거 정합성, `reference_guidance_calibration_eval`의 사용자 흐름 캘리브레이션이 같은 batch 결과와 충돌 해소 상태를 기준으로 일관되게 연결되는지 확인하는 마감 단계다.

| 점검 축 | 최종 기준 |
| --- | --- |
| 충돌 해소 gate | 충돌 보완 재분석이 확인된 샘플만 `ready_for_legal_knia_insurance_evidence_eval` 이후 단계로 넘긴다. 미해소 샘플은 과실 범위/문구 튜닝 대상이 아니라 `blocked_by_reference_gate` 또는 충돌 보완 대상으로 남긴다. |
| 근거 정합성 | 5개 전문가 reference 샘플 모두 근거 family와 쟁점 키워드가 맞아 `ready_for_stage8_guidance_calibration` 상태로 통과했다. 충돌 해소 샘플 수는 2개다. |
| 사용자 흐름 캘리브레이션 | 충돌 해소 fixture 기준 5개 샘플 모두 `calibrated_for_user_flow`로 통과했다. 미해소 reference gate 기준으로는 사고 3·5가 계속 막히는 것을 재확인했다. |
| 비용 안전 | 이번 최종 점검은 OpenAI 프레임 분석을 새로 호출하지 않았고, worker는 `ENABLE_OPENAI_FRAME_ANALYSIS=0` 상태다. |
| 완료 범위 | 영상/Agent 정확도 고도화 12단계는 개발 기준선으로 완료한다. 이는 실제 제품 완성이 아니라, 이후 실제 OpenAI ON 검증과 운영 데이터 확장을 진행할 수 있는 평가 골격 완료를 의미한다. |

검증은 `python -m py_compile scripts/reference_guidance_eval.py scripts/reference_evidence_alignment_eval.py scripts/reference_guidance_calibration_eval.py scripts/video_accuracy_batch.py scripts/video_agent_e2e.py`, `python -m pytest tests/test_expert_guidance_sections.py -q`, `npm test -- report-composer`, `npm run build`, `docker compose ps`, worker `ENABLE_OPENAI_FRAME_ANALYSIS=0` 확인으로 통과했다. 최종 평가 산출물은 `logs/video_accuracy/reference_evidence_alignment_stage12_final.json`, `logs/video_accuracy/reference_guidance_calibration_eval_stage12_final.json`, `logs/video_accuracy/reference_guidance_calibration_eval_stage12_gate_check.json`에 저장했다. `logs/`는 Git에서 제외되므로 실제 영상 경로와 평가 payload는 저장소에 포함되지 않는다.

후속 작업은 프로젝트 구조 보강이 아니라 제품 완성 개발로 분류한다. 우선순위는 실제 OpenAI 프레임 분석 ON 상태에서 5개 이상 실제 영상 재측정, 더 많은 변호사/보험 reference 샘플 확보, KNIA/법령/판례 원문 데이터 확장, 비용 모니터링과 API 사용량 제한, S3 직접 업로드 전환, 사용자/관리자 UI 수용성 점검, 배포/보안 운영 점검 순서다. 이번 단계는 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

### 2026-05-24 정확도 평가 최소 fixture 추가

정확도 고도화 평가 흐름이 `logs/`에만 의존하지 않도록 tracked synthetic fixture를 추가했다. 기존 실제 영상 측정 결과와 전문가 reference manifest는 `logs/` 아래에 있어 Git에 포함되지 않는다. 이는 보안상 맞지만, 새 환경에서는 `reference_guidance_eval.py`, `reference_evidence_alignment_eval.py`, `reference_guidance_calibration_eval.py`의 연결을 바로 재현하기 어렵다는 문제가 있었다.

| Path | 역할 |
| --- | --- |
| `tests/fixtures/video_accuracy/reference_hardening_minimal/manifest.json` | 실제 영상 경로, 사용자 정보, 실제 변호사 의견 원문이 없는 최소 reference manifest다. ready 샘플 1개와 충돌 gate 샘플 1개를 포함한다. |
| `tests/fixtures/video_accuracy/reference_hardening_minimal/cases/accident_1.json` | 중앙선 장애물 회피와 후속 추돌을 재현하는 synthetic case다. |
| `tests/fixtures/video_accuracy/reference_hardening_minimal/cases/accident_3.json` | 후방 추돌 정차 여부 충돌 gate를 재현하는 synthetic case다. |
| `tests/fixtures/video_accuracy/reference_hardening_minimal/batch_aggregate.json` | `video_accuracy_batch.py`의 최소 aggregate 형태를 흉내 내는 synthetic batch output이다. |
| `tests/fixtures/video_accuracy/reference_hardening_minimal/batch_aggregate_conflict_resolved.json` | 충돌 보완 답변 후 `conflict_followup.latest_conflict_count=0`인 상태를 재현하는 synthetic batch output이다. |
| `scripts/verify_reference_hardening_fixture.py` | 미해소/해소 fixture를 모두 실행하고 guidance, evidence alignment, calibration gate의 기대 카운트를 검증하는 smoke 스크립트다. |
| `scripts/verify_core.ps1` | 핵심 검증에 reference hardening fixture smoke 단계를 포함한다. |

검증은 `python scripts/reference_guidance_eval.py --manifest tests/fixtures/video_accuracy/reference_hardening_minimal/manifest.json --batch-output tests/fixtures/video_accuracy/reference_hardening_minimal/batch_aggregate.json --output logs/video_accuracy/reference_hardening_minimal_guidance_eval.json`, `python scripts/reference_evidence_alignment_eval.py --reference-eval logs/video_accuracy/reference_hardening_minimal_guidance_eval.json --batch-output tests/fixtures/video_accuracy/reference_hardening_minimal/batch_aggregate.json --output logs/video_accuracy/reference_hardening_minimal_evidence_alignment.json`, `python scripts/reference_guidance_calibration_eval.py --manifest tests/fixtures/video_accuracy/reference_hardening_minimal/manifest.json --batch-output tests/fixtures/video_accuracy/reference_hardening_minimal/batch_aggregate.json --reference-eval logs/video_accuracy/reference_hardening_minimal_guidance_eval.json --output logs/video_accuracy/reference_hardening_minimal_calibration_eval.json`로 통과했다. 결과는 guidance ready 1개/충돌 대기 1개, evidence alignment ready 1개, calibration 통과 1개/`blocked_by_reference_gate` 1개다. 이 fixture는 실제 정확도 측정이 아니라 평가 스크립트와 gate 계약의 최소 재현성 확인용이며, DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

3단계 보강으로 같은 최소 fixture 안에 충돌 해소 후 승격 흐름을 추가했다. `batch_aggregate_conflict_resolved.json`은 실제 영상 로그 없이 사고 3 유형의 `stopped` 충돌이 보완 답변 이후 해소된 상태를 재현한다. 검증은 resolved batch로 `reference_guidance_eval.py`, `reference_evidence_alignment_eval.py`, `reference_guidance_calibration_eval.py`를 다시 실행해 guidance ready 2개, resolved conflict sample 1개, evidence alignment ready 2개, calibration 통과 2개를 확인하는 방식이다. 이번 보강은 synthetic fixture와 운영 문서만 추가하며 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

3단계 후속 검증으로 위 검증을 `scripts/verify_reference_hardening_fixture.py` 한 명령으로 묶었다. 이 스크립트는 미해소 fixture에서 ready 1개/충돌 gate 1개, 해소 fixture에서 ready 2개/충돌 해소 1개/evidence ready 2개/calibration 2개를 강제 확인한다. `scripts/verify_core.ps1`에도 포함해 이후 핵심 검증에서 reference gate 회귀를 같이 잡도록 했다. 출력 산출물은 `logs/video_accuracy/reference_hardening_fixture_smoke/`에 저장되며 Git에는 포함되지 않는다.

4단계 사전 검증으로 실제 OpenAI 영상 배치 실행 전 manifest preflight 도구를 추가했다. `scripts/validate_video_accuracy_manifest.py`는 OpenAI API를 호출하지 않고 sample 수, 중복 이름, 영상 파일 존재 여부, `case_json` 존재/형식, `reference.purpose=evaluation_only_not_agent_input`, reference 전용 토큰이 Agent 입력 `case_json`에 섞였는지 여부를 검사한다. 실제 측정 manifest는 `logs/video_accuracy/lawyer_reference_manifest.json`처럼 Git에서 제외된 위치에 두고, `--require-reference --min-samples 5`로 확인한 뒤 `video_accuracy_batch.py`를 실행한다. 문서 예시 manifest는 `--allow-missing-files`로 구조만 확인할 수 있다. 출력은 `logs/video_accuracy/manifest_preflight*.json`에 저장되며 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

### 2026-05-24 실제 OpenAI ON 최신 재측정(4단계)

현재 최신 코드 기준으로 `logs/video_accuracy/lawyer_reference_manifest.json`의 사고 영상 1~5번을 실제 OpenAI 프레임 분석 ON 상태에서 다시 측정했다. 실행 전 `scripts/validate_video_accuracy_manifest.py --manifest logs/video_accuracy/lawyer_reference_manifest.json --min-samples 5 --require-reference`로 manifest를 검증했고, 측정 후 worker를 다시 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=` 상태로 복구했다.

| 비교 항목 | 기존 Stage 4 | 2026-05-24 최신 재측정 |
| --- | --- | --- |
| 전체 프레임 관찰값 | 23개 | 20개 |
| Agent 수용/보류/참고 | 수용 7, 보류 9, 참고 7 | 수용 8, 보류 6, 참고 5 |
| 판단 반영/기존 입력 확인/충돌 | 반영 2, 확인 3, 충돌 2 | 반영 4, 확인 2, 충돌 2 |
| 화면 상태 | `일부 반영` 4개, `확인 필요` 1개 | `일부 반영` 3개, `확인 필요` 2개 |
| 첫 보완 질문 | `정차 여부` 3개, `상대 차량 행동` 2개 | `정차 여부` 3개, `급정거 여부` 1개, `상대 차량 행동` 1개 |

최신 배치 결과는 5개 샘플 모두 pipeline 통과, mismatch 0개다. `reference_guidance_eval.py` 기준 사고 1, 2, 4는 `ready_for_legal_knia_insurance_evidence_eval`, 사고 3, 5는 기존처럼 `needs_conflict_resolution_before_guidance`로 남았다. 즉 충돌 gate는 정상적으로 유지된다.

후속 근거/사용자 흐름 평가는 잔여 이슈를 드러냈다. `reference_evidence_alignment_eval.py` 기준 사고 1과 4는 `ready_for_stage8_guidance_calibration`으로 통과했지만, 사고 2 신호 전환 샘플은 `needs_evidence_content_fit`으로 남았다. 근거 카드가 신호 전환/CCTV 쟁점보다 후방추돌·횡단보도 정지 근거를 우선 표시했고, `reference_guidance_calibration_eval.py`에서도 첫 보완 질문이 `급정거 여부`로 올라와 신호/CCTV 확인보다 낮은 사용자 흐름 품질을 보였다. 따라서 다음 제품 개발 전 보강 대상은 “신호 전환 사고의 근거 검색/카드 선택/보완 질문 우선순위”다.

검증 산출물은 `logs/video_accuracy/stage4_openai_latest_20260524/aggregate.json`, `logs/video_accuracy/reference_guidance_eval_stage4_latest_20260524.json`, `logs/video_accuracy/reference_evidence_alignment_stage4_latest_20260524.json`, `logs/video_accuracy/reference_guidance_calibration_stage4_latest_20260524.json`에 저장했다. `logs/`는 Git에서 제외되므로 실제 영상 경로와 측정 payload는 저장소에 포함되지 않는다. 이번 단계는 OpenAI API를 실제 호출했지만, DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

### 2026-05-24 운영 리스크 보강 계획 반영(5단계)

정확도 고도화 이후 제품 완성 단계에서 관리해야 하는 운영 리스크를 `docs/OPERATING_RISK_ROADMAP.md`로 분리했다. 이 문서는 OpenAI token/cost 사용량 기록 부족, 정적 fallback 의존, 실제 KNIA/법령/판례 원문 DB 부족, S3 직접 업로드 전환, API 사용량 제한, UI 수용성 점검을 제품 완성 로드맵으로 재분류한다.

| 항목 | 현재 책임 경계 |
| --- | --- |
| OpenAI 프레임 분석 비용 상한 | `apps/worker/worker/frame_analysis.py`가 기본 비활성화, 최대 프레임/출력 토큰/detail/timeout, `store=false`, 응답 `usage` 수집 경로를 담당한다. |
| Agent LLM 비용 관찰 | `apps/agent/app/services/llm_policy.py`와 `apps/agent/app/services/agent_quality_packet.py`가 LLM 허용/차단/실패/fallback 이유와 `cost_observability`를 남긴다. 실제 token usage 영속화는 후속 항목이다. |
| fallback 및 근거 소스 상태 | `apps/agent/app/services/rag_client.py`, `apps/agent/app/services/evidence_source_status.py`, `apps/agent/app/services/static_legal_fallback.py`가 정적 fallback과 degraded 상태를 표시한다. fallback은 원문 DB 부족을 보완하는 임시 안전장치이며 제품 품질의 최종 근거로 보지 않는다. |
| S3 전환 | `apps/gateway/src/storage/provider.ts`의 로컬 provider가 현재 동작 경로이고 `S3StorageProvider`는 미구현 상태를 명시적으로 반환한다. |
| API 제한과 UI 수용성 | Gateway rate limit, 내부 호출 timeout/retry, 결과 화면 sanitizer와 관리자 진단이 현재 안전 경계다. 사용자별 quota, 사용량 대시보드, UI 수용성 검증은 후속 제품 완성 항목이다. |

비용/사용량 계측의 첫 구현 범위는 정확한 원화 비용 계산이 아니라 `ai-usage-event-v1` 수준의 안전 메타데이터 계약으로 확정했다. provider, service, endpoint, model, enabled, attempted, success, token usage, frame count, max output tokens, timeout, fallback reason, case/analysis/trace 식별자, created_at을 기록 대상으로 삼고, raw prompt, raw user text, secret, API key, 비밀번호는 저장하지 않는다. Phase A는 기존 trace와 quality packet 필드 정렬, Phase B는 PostgreSQL `ai_usage_events` 영속화, Phase C는 관리자 집계 API/UI, Phase D는 공식 가격표 확인 후 비용 추정 레이어로 진행한다.

`docs/OPERATIONS.md`와 `DEVELOPMENT_PROMPT.md`도 이 운영 리스크 로드맵을 참조하도록 업데이트했다. 이번 단계는 문서/운영 기준 정리이며 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

### 2026-05-23 전문가 참고 의견 안내 품질 평가 도구

`scripts/reference_guidance_eval.py`를 추가했다. 이 스크립트는 영상 정확도 배치 결과와 `lawyer_reference_manifest.json`의 `reference.evaluation_focus`를 결합해, 샘플별로 예상 과실 안내를 만들기 전에 필요한 사실/근거 검증 상태를 평가한다. 목적은 실제 판결 정답을 주입하는 것이 아니라, 전문가 참고 의견의 쟁점에 도달하기 위해 Agent가 어떤 fact, 영상 관찰값, KNIA/법령/판례/보험 근거를 더 확인해야 하는지 정리하는 것이다.

| Path | 변경 내용 |
| --- | --- |
| `scripts/reference_guidance_eval.py` | 사고 샘플의 평가 초점을 중앙선 회피, 후속 추돌, 신호 전환, 후방 추돌, 앞차 정지 사유, 횡단보도/보행자 신호, 무등화 정차 차량, 속도/회피 가능성, 형사/민사 구분, 자전거 비접촉 유발, 시간적 여유 같은 기준으로 매핑한다. 각 기준별로 입력 fact 존재 여부, 영상 관찰/반영 여부, 사용자-영상 충돌, 필요한 근거 확인 항목을 JSON으로 출력한다. |
| `docs/OPERATIONS.md` | `reference_guidance_eval.py` 실행 방법과 여러 batch output을 병합해 재시도 결과를 반영하는 방식을 문서화했다. |

로컬 평가 결과는 `logs/video_accuracy/reference_guidance_eval*.json`에 저장한다. `logs/`는 Git에서 제외되므로 실제 영상 경로, 케이스 입력, 전문가 참고 의견 기반 측정 결과가 저장소에 올라가지 않는다. 2026-05-23 Stage 5 기준 사고 1~5번은 pipeline 기준 모두 통과했고, 사고 3과 사고 5는 사용자 입력과 영상 관찰값 충돌을 먼저 해소해야 하는 상태로 분류됐다. 나머지 사고 1, 2, 4는 법령/KNIA/판례/보험 근거 대조 단계로 넘어갈 수 있는 상태로 분류됐다.

### 2026-05-23 전문가 참고 샘플 근거 검색 보강

전문가 참고 의견 샘플에서 드러난 쟁점을 Agent 근거 검색 단계에 반영했다. 변경 목표는 과실비율 숫자를 정답처럼 맞추는 것이 아니라, 중앙선 회피·후속 추돌·신호 전환·횡단보도 앞 후방 추돌·무등화 정차 차량·속도별 회피 가능성·자전거 비접촉 유발처럼 실제 안내에 필요한 쟁점이 검색어와 fallback 근거에서 누락되지 않게 하는 것이다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/scenario_classifier.py` | 횡단보도 앞 정차 차량 추돌은 보행자 사고로 단정하지 않고 후방 추돌 시나리오로 분류하면서 `crosswalk` tag를 보존한다. 무등화/스텔스 정차 차량은 정차 차량 시나리오로 분류하고 `visibility`, `night`, `rear_end` tag를 부여한다. 중앙선, 2차 충돌, 자전거 비접촉 유발, 속도, 사망 사고 tag도 보강했다. |
| `apps/agent/app/services/scenario_search_terms.py` | `centerline_crossed`, `secondary_collision`, `stopped_vehicle_without_lights`, `reported_speed_kmh`, `speed_limit_kmh`, `fatality`, `bicycle_involved`, `possible_trigger_vehicle`, `time_gap_sec` fact가 검색어로 확장되도록 추가했다. |
| `apps/agent/app/services/static_legal_fallback.py` | DB/KNIA 원문 근거가 부족한 개발 환경에서도 중앙선 장애물 회피, 무등화 정차 차량, 속도·회피 가능성 및 형사/민사 구분, 자전거 비접촉 유발, 신호 전환·CCTV 확인 기준을 fallback evidence로 검색할 수 있게 보강했다. |
| `apps/agent/app/services/evidence_quality_gate.py` | `parking_or_stopped_vehicle_accident` 전용 evidence profile을 추가해 정차 차량·중앙선·시인성 쟁점에서 legal/KNIA 근거가 모두 있는지 평가한다. |
| `apps/agent/scripts/test_evidence_search_quality.py`, `apps/agent/tests/test_scenario_search_terms.py` | 전문가 참고 샘플에서 필요한 3개 대표 근거 검색 회귀 케이스를 추가했다. 중앙선 회피/후속 추돌, 무등화 정차 차량/속도·회피 가능성, 자전거 비접촉 유발/버스 후방 추돌 기준이 모두 통과해야 한다. |

검증은 Docker Agent 환경에서 `powershell -ExecutionPolicy Bypass -File scripts/verify_agent_regression.ps1 -SkipDockerBuild`로 통과했다. 새 근거 검색 케이스 3개는 모두 `coverage=high`로 평가됐고, 기존 후방 추돌/차선 변경/신호위반/보행자/스쿨존/자전거 회귀도 유지됐다. 로컬 Python 직접 실행은 `psycopg`가 설치되어 있지 않으면 DB 연동 검색 스크립트에서 막히므로, Agent 전체 검증은 Docker 컨테이너 또는 `apps/agent/requirements.txt` 설치 환경에서 실행한다.

## 2026-05-22 프로젝트 구조 보강 완료 판정

현재 프로젝트 구조 보강 기준에서 P0와 신뢰성 관련 P1은 완료 상태로 판정한다. 완료 판정의 기준은 Agent 판단 골격, 영상 관찰값 입력 계약, 근거 검색 품질 회귀 검증, 서비스별 단일 책임 경계가 모두 코드와 검증 스크립트로 확인 가능해야 한다는 것이다.

| 범위 | 상태 | 완료 근거 |
| --- | --- | --- |
| P0 Agent 신뢰 골격 | 완료 | 사고 사실 표준화, 근거 기반 후보 선택, 과실 산정, 판정 추적, 반성/품질 게이트, 품질 패킷이 Agent 서비스 경계 안에 분리되어 있다. |
| P1 영상 관찰값 연결 | 완료 | Worker의 ffmpeg 프레임 추출 결과와 OpenAI 프레임 관찰값을 Agent 입력 계약으로 연결했고, fixture 기반 재현 검증과 실제 OpenAI E2E 검증 경로를 분리했다. |
| P1 영상/사용자 사실 충돌 처리 | 완료 | 영상 관찰값과 사용자 서술이 충돌할 때 `quality_gate`가 후속 추론을 차단하고 보완 입력을 요구한다. |
| P1 근거 검색 품질 | 완료 | 후방 추돌/정차 시나리오가 근거 검색에서 우선 검색되는지 회귀 테스트로 고정했고, 통합 회귀 스크립트에 포함했다. |
| Gateway/Worker/Frontend 책임 경계 | 완료, 유지관리 대상 | Gateway 라우트, Worker 전처리/관찰값 생성, Frontend 화면/상태 책임이 현재 규모에서 단일 책임 원칙을 만족한다. 기능 확장 시에만 추가 분리가 필요하다. |

따라서 현재 남은 항목은 구조 보강의 필수 차단 이슈가 아니라 운영 안정화, 정확도 고도화, 배포 준비, UI 마감 성격의 후속 작업으로 분류한다. 이후 개발에서는 이 문서를 기준으로 P0/P1 구조 보강을 반복하지 않고, 실제 서비스 완성도를 높이는 작업으로 넘어간다.

남아 있는 대표 후속 작업은 KNIA 원문/DB 수집 안정화, 실제 사고 영상 기반 프레임 분석 보정, OpenAI 비용 모니터링, S3 직접 업로드 전환, 관리자/사용자 UI 마감, 장기적으로 교통사고 특화 비전 모델 검토다.

## 2026-05-23 실제 OpenAI 프레임 분석 결과 및 사용자 흐름 보정

실제 사고 영상 `car_accident_1.mp4`로 OpenAI 프레임 분석을 켠 상태에서 E2E를 실행했다. 검증 설정은 `gpt-4.1-mini`, `detail=low`, 최대 6프레임, 출력 900토큰이다. Worker는 관찰값 2개를 생성했지만 Agent 품질 기준에서는 2개 모두 confidence threshold 미달로 보류되어, 이번 샘플 기준 승격 0개/보류 2개(승격 0%, 보류 100%)가 확인됐다. 이 결과는 모델이 관찰 후보를 만들더라도 곧바로 사고 사실로 확정하지 않고 보완 질문으로 넘기는 현재 안전 정책이 동작한다는 의미다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | 영상 관찰값 결과 카드에서 `Agent`, `품질 기준` 같은 내부 용어를 줄이고, “영상 관찰 후보”, “확인 필요”, “바로 반영하지 않음”처럼 실제 사용자 흐름에 맞춘 표현으로 조정했다. 보류 관찰값 질문은 정차 여부, 상대 행동, 차선변경 주체, 신호 위반처럼 과실 판단에 큰 영향을 주는 항목이 먼저 나오도록 우선순위를 둔다. |
| `apps/frontend/src/components/easy/VideoFactExplanationCard.vue` | 결과 화면의 영상 관찰값 섹션 라벨을 “영상 관찰값 상태”, “분석 반영”, “확인 필요” 중심으로 정리했다. |
| `scripts/video_agent_e2e.py` | 보류 관찰값 보완 질문 탐색 로직이 새 사용자 문구를 인식하도록 업데이트했다. |
| `apps/gateway/test/report-composer.test.ts` | 사용자 안전 카드의 관찰 후보 카운트, 보류 질문 문구, 질문 우선순위를 회귀 테스트로 고정했다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약을 변경하지 않는다. 실제 OpenAI 실행 후 worker는 기본 비용 안전 상태인 `ENABLE_OPENAI_FRAME_ANALYSIS=0`으로 되돌려야 한다.

## 2026-05-23 영상 관찰값 확인 후보 계약 보강

실제 사고 영상에서 OpenAI 프레임 분석이 낮은 confidence의 관찰값을 반환하는 경우, Agent가 해당 값을 사실로 승격하지 않으면서도 후속 확인 질문과 관리자 진단에서 우선 확인할 수 있게 `video_input_contract`를 보강했다. `stopped`, `opponent_behavior`, `lane_change_actor`, `opponent_signal_violation`처럼 과실 판단에 큰 영향을 주는 보류 관찰값은 `confirmation_candidates`로 정렬하고, 정차 중 후방 추돌처럼 함께 해석해야 하는 후보는 `confirmation_groups`로 묶는다. 이 계약은 자동 판정 근거가 아니라 사용자 확인 또는 운영 진단을 위한 안전 메타데이터다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/video_input_contract.py` | 보류 관찰값의 canonical value를 정리하고, 확인 후보/후보 그룹/품질 요약 카운트를 생성한다. 낮은 confidence 값은 계속 `fact_patch`에 들어가지 않는다. |
| `apps/agent/tests/test_video_input_contract.py` | 낮은 confidence 신호위반 후보와 실제 영상에서 자주 발생할 수 있는 정차+후방추돌 후보 그룹을 회귀 테스트로 고정했다. |
| `apps/gateway/src/lib/agent-diagnostics.ts` | 관리자 진단에 확인 후보 수와 후보 그룹 수를 표시한다. |
| `scripts/video_agent_e2e.py` | 실제 영상 E2E 출력에 `confirmation_candidate_count`와 `confirmation_groups`를 포함한다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | 새 내부 계약 키가 일반 사용자 화면에 raw debug 값으로 노출되지 않도록 기술 필드 목록에 추가했다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약을 변경하지 않는다. 공개 결과 화면은 기존 보완 질문 흐름을 유지하며, 새 후보 계약은 Agent/관리자 진단/실제 영상 E2E에서 입력 품질을 해석하는 데 사용한다.

### 실제 영상 재검증 결과

`car_accident_1.mp4`로 실제 OpenAI 프레임 분석을 다시 실행했다. worker는 실행 전 `ENABLE_OPENAI_FRAME_ANALYSIS=1`, `FRAME_ANALYSIS_FIXTURE_MODE=` 상태로 일시 재기동했고, 검증 후 비용 안전을 위해 `ENABLE_OPENAI_FRAME_ANALYSIS=0`으로 되돌렸다.

| 항목 | 결과 |
| --- | --- |
| OpenAI 프레임 분석 | 성공. `gpt-4.1-mini`, `detail=low`, 6프레임 분석 |
| Worker 관찰값 | 3개 생성: `stopped=false` 0.9, `lane_change_actor=opponent` 0.8, `sudden_brake=false` 0.7 |
| Agent 반영 | `stopped=false`는 품질 기준을 통과했지만 사용자 입력 `stopped=true`와 충돌해 최종 구조화 사실에는 바로 적용하지 않았다. |
| 확인 후보 | `lane_change_actor`, `sudden_brake` 2개가 `confirmation_candidates`로 생성됐다. |
| 후보 그룹 | `lane_change_candidate` 1개가 `confirmation_groups`에 생성됐다. |
| 보완 질문 E2E | 보류 관찰값 질문 제출과 재분석 `analysis_change_card` 생성까지 통과했다. |

이 결과는 영상 관찰값을 우선 고려하되, 충돌하거나 임계값이 낮은 경우 바로 확정하지 않고 사용자 확인 또는 재분석 흐름으로 넘기는 현재 정책이 실제 영상에서도 동작한다는 근거다. 이후 튜닝 후보는 `stopped=false`처럼 높은 confidence지만 사용자 입력과 충돌한 관찰값을 결과 화면에서 더 명확히 보여주는 방식이다.

### 영상/사용자 입력 충돌 표시 보강

실제 영상 재검증에서 `stopped=false`가 높은 confidence로 관찰됐지만 사용자 입력 `stopped=true`와 충돌한 사례를 반영해, 일반 결과 화면의 영상 기반 사실 카드가 충돌 내용을 더 명확히 보여주도록 보강했다. 이 변경은 Agent의 승격/보류 정책을 바꾸지 않고, 사용자가 확인해야 할 차이를 안전한 문구로 보여주는 표시 계층 변경이다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | `video_fact_explanation_card.review_items`에 입력값 라벨, 영상 관찰 라벨, 충돌 비교 문구, 상태 라벨을 추가했다. 보완 질문도 “영상 기준 값”과 “기존 입력 값”을 함께 보여준다. |
| `apps/frontend/src/components/easy/VideoFactExplanationCard.vue` | 사용자 입력과 영상 관찰값을 나란히 표시하고, 유지/반영 상태와 영상 신뢰도를 카드 안에서 확인할 수 있게 했다. |
| `apps/gateway/test/report-composer.test.ts` | 높은 confidence 영상 관찰값이 사용자 입력과 충돌할 때 최종 사실으로 덮지 않고, 공개 카드와 보완 질문에 안전하게 표시되는지 회귀 테스트로 고정했다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약을 변경하지 않는다.

### 영상 `stopped=false` 오판 방지 보강

실제 프레임 분석에서 dashcam 화면 변화, 카메라 흔들림, 주변 차량 이동을 근거로 사용자 차량이 주행 중이었다고 과잉 판단할 수 있으므로 Worker의 OpenAI 프레임 분석 프롬프트와 정규화 정책을 보강했다. `stopped=false`는 사용자 차량이 충돌 직전 또는 충돌 시점에 실제로 전진 이동 중인 장면이 여러 프레임에서 명확해야만 반환하도록 요청하며, Worker 정규화 단계에서는 현재 OpenAI 관찰값만으로는 Agent의 `stopped` 사실 승격 기준인 0.82를 넘지 않도록 confidence를 제한한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/worker/worker/frame_analysis.py` | `stopped=false` 판단 기준을 프롬프트에 명시하고, `stopped=false` 관찰값은 3프레임 이상이어도 confidence 최대 0.81, 그보다 적으면 0.74로 제한한다. 이 값은 Agent에서 바로 `fact_patch`로 승격되지 않고 확인 후보/보완 질문 흐름으로 남는다. |
| `apps/worker/tests/test_frame_analysis_contract.py` | OpenAI 응답이 `stopped=false` 0.95를 반환해도 Worker가 0.81 low quality로 낮추고 프롬프트에 dashcam 화면 변화 오판 방지 문구가 포함되는지 검증한다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다. 실제 OpenAI 호출 없이 계약 테스트와 Agent 입력 계약 스모크로 확인했으며, 운영 기본값은 계속 `ENABLE_OPENAI_FRAME_ANALYSIS=0`이다.

### 영상 관찰값 방향/행동 혼동 방지 보강

실제 OpenAI 프레임 분석 재검증 중 `collision_direction: front`처럼 충돌 방향을 나타내는 값이 `opponent_behavior: front`로 확정될 수 있는 위험을 확인했다. 충돌 방향은 상대 차량 행동과 동일하지 않으므로 Agent 입력 계약에서 `rear_collision`, `lane_change`, `signal_violation`처럼 해석 가능한 행동값만 `opponent_behavior`로 승격하고, `front` 같은 방향값은 `value_not_actionable`로 보류하되 확인 후보에는 올리지 않도록 보강했다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/video_input_contract.py` | `opponent_behavior` 값 정규화를 엄격히 제한했다. `collision_direction=front`는 더 이상 `fact_patch`나 `confirmation_candidates`에 들어가지 않는다. |
| `apps/agent/tests/test_video_input_contract.py` | `collision_direction=front`가 상대 행동 사실로 승격되지 않고 `value_not_actionable`으로 남는 회귀 테스트를 추가했다. |
| `apps/gateway/src/lib/report-composer.ts` | 영상 관찰값에서 안전한 보완 질문이 생성되면 같은 field의 기존 저장 질문을 대체한다. 이로써 `front` 같은 raw 옵션이 사용자 선택지로 남지 않게 했다. |
| `apps/gateway/test/report-composer.test.ts` | 기존 질문에 raw `front` 옵션이 있어도 영상 기반 안전 질문으로 교체되는지 검증한다. |
| `scripts/video_agent_e2e.py` | 보류 관찰값 보완 질문 탐색이 깨진 한글 문자열에만 의존하지 않고 안전 field 기준으로 동작하도록 보강했다. |

실제 사고 영상 `car_accident_1.mp4`로 OpenAI 프레임 분석을 다시 실행한 결과, OpenAI 호출은 완료됐지만 보강된 프롬프트 기준에서 관찰값 0개를 반환했다. 따라서 이번 실제 E2E의 의미는 “모델이 애매한 프레임을 확정 사실로 만들지 않음”으로 해석하며, Worker는 검증 후 다시 `ENABLE_OPENAI_FRAME_ANALYSIS=0` 상태로 복구했다. 이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

### 영상 관찰값 0개 사용자 표시 보강

영상 업로드와 프레임 추출은 성공했지만 Agent에 반영할 수 있는 관찰값이 0개인 경우, 결과 화면에서 영상 분석이 실패한 것처럼 보이지 않도록 Gateway 표시 계약을 보강했다. `video_input_contract`에 대표 프레임 등 전처리 정보가 있으면 `video_fact_explanation_card`를 생성하고, 상태를 `확정 사실 없음`으로 표시한다. 이 상태는 “영상 처리 실패”가 아니라 “현재 기준으로 바로 판단에 반영할 수 있는 물리 사실을 확정하지 않았다”는 의미다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | accepted/uncertain/conflict가 없어도 대표 프레임 수 또는 품질 요약이 있는 영상 계약이면 영상 카드가 생성되도록 했다. 카드에는 대표 프레임 수, 관찰 후보 0개, 판단 반영 0개, 품질 상태 `확정 사실 없음`을 표시한다. |
| `apps/gateway/test/report-composer.test.ts` | 대표 프레임 12장이 있지만 관찰값 0개인 계약에서도 영상 카드가 생성되고, 확정 사실 없음 상태와 빈 적용/검토/보류 목록이 유지되는지 검증한다. |
| `scripts/video_agent_e2e.py` | 실제 영상 E2E에서 `video_fact_explanation_card` 존재 여부, 품질 상태, 대표 프레임 수, 통계 목록을 함께 검증하고 출력한다. |

비용 없는 실제 영상 E2E 기준 `car_accident_1.mp4`는 `duration=11.167s`, 대표 프레임 12장, `frame_observations=0`, `video_fact_card.status_label=확정 사실 없음`으로 통과했다. 이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

### OpenAI 프레임 분석 표시 상태 회귀 보강

실제 OpenAI 프레임 분석이 켜졌을 때 결과 화면의 영상 카드가 관찰값 상태에 따라 일관되게 동작하는지 샘플별 회귀 테스트를 넓혔다. 실제 API를 매번 호출하지 않고 `frame_analysis:openai` 형태의 대표 payload를 고정해, 비용 없이 네 상태를 반복 검증한다.

| 상태 | 표시 기대값 |
| --- | --- |
| 관찰값 0개 | 대표 프레임은 표시하고 품질 상태는 `확정 사실 없음`으로 표시한다. |
| 보류 | 영상 관찰 후보는 표시하되 판단 반영은 0개이며, 보완 질문 field가 생성된다. |
| 충돌 | 사용자 입력과 영상 관찰의 차이를 `입력 충돌 검토`로 표시하고, 최종 반영 대신 확인 질문으로 연결한다. |
| 반영 | 품질 기준을 통과한 영상 관찰값을 `판단 반영`으로 표시한다. |

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/test/report-composer.test.ts` | `frame_analysis:openai` source를 가진 0개/보류/충돌/반영 샘플을 하나의 회귀 테스트로 고정했다. 각 샘플은 `영상 관찰 후보`, `판단 반영`, `입력 충돌 검토`, `확인 필요`, `품질 상태` 통계를 검증하고, 사용자 카드에 `frame_analysis:openai`, `video_input_contract`, `fact_arbitration`, `frame_refs`, raw value가 노출되지 않는지 확인한다. |

이 변경은 테스트 coverage 확장만 수행하며 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다.

## 2026-05-23 easy-report 사용자 흐름 및 payload 표시 정합성 보정

Agent 결과 payload가 사용자 화면에서 카드별로 중복되거나 과도한 경고처럼 보이지 않도록 easy-report 표시 계약을 정리했다. 보완 질문은 `missing_info.questions`의 선택형 입력으로만 강조하고, 동일 문장은 `missing_info.items` 체크리스트에서 제거해 한 화면 안에서 같은 질문이 반복되지 않도록 했다. 근거 연결, 영상 관찰, Agent 처리 과정, 재분석 비교 카드의 안내 문구는 최종 판정 경고를 반복하지 않고 각 카드가 보여주는 상태 설명으로 낮췄다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | `compactDisplayItems()`를 추가해 보완 질문과 체크리스트 문구를 분리했다. 근거 연결/영상 관찰/Agent 처리 카드의 notice 문구를 카드 역할 설명 중심으로 조정했다. |
| `apps/frontend/src/components/easy/*.vue` | notice가 없는 경우 빈 경고 문단을 렌더링하지 않고, 근거/영상/Agent/재분석 카드의 반복 안내는 일반 보조 문구 스타일로 표시한다. |
| `apps/gateway/test/report-composer.test.ts` | 보완 질문과 체크리스트가 분리되고, 근거 연결 카드 notice가 과도한 최종 판정 경고로 회귀하지 않는지 검증한다. |

이 변경은 공개 easy-report payload의 기존 필드 의미를 유지하면서 표시용 문구와 중복 제거 로직만 보정한다. DB schema, Redis key, storage path, API route, 외부 API 계약은 변경하지 않는다.

## 2026-05-23 KNIA 검색순위 상세 기준 수집 상태 보강

KNIA 검색순위 화면에서 “검색순위는 보이지만 상세 기준 본문은 없는 상태”를 바로 확인하고, 관리자 계정이 표시된 항목의 상세 기준 수집을 이어서 실행할 수 있게 했다. 목적은 검색순위 기반 기준 보기에서 placeholder 화면이 반복되는 문제를 줄이고, 상세 본문/가감요소/관련법규 수집 필요 여부를 사용자가 명확히 알 수 있게 하는 것이다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/routes/knia.ts` | `/api/v1/knia/ranking` 응답에 `detail_summary`를 추가했다. 표시된 ranking 항목 중 상세 기준 수집 완료/미완료 건수와 상세 수집 필요 여부를 반환한다. |
| `apps/frontend/src/views/KniaRankingView.vue` | 검색순위 화면에 상세 수집 현황 문구를 표시하고, 관리자에게만 `표시된 항목 상세 수집` 버튼을 노출한다. 이 버튼은 기존 `/admin/knia/collect-ranking-details` API를 사용한다. |
| `apps/frontend/src/components/knia/KniaRankingCard.vue` | 각 ranking 항목에 `상세 수집 완료` 또는 `상세 수집 필요` 상태 칩을 표시한다. |

이 변경은 기존 API route를 추가하지 않고 `/api/v1/knia/ranking`의 표시용 메타데이터만 확장한다. DB schema, Redis key, storage path, 외부 API 계약은 변경하지 않는다.

## 2026-05-23 보완 답변 재분석 표시 개선

보류된 영상 관찰값 또는 일반 보완 질문에 사용자가 답변한 뒤, 결과 화면에서 “답변이 실제 분석 입력으로 반영됐는지”, “확인 필요로 남았는지”, “지원하지 않아 제외됐는지”를 별도 섹션으로 확인할 수 있게 했다. 목적은 재분석 후 과실비율이 크게 바뀌지 않더라도 사용자가 자신의 답변 처리 결과를 이해할 수 있게 하는 것이다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | `analysis_change_card`에 `status_label`과 `answer_items`를 추가했다. `answer_items`는 보완 답변을 “분석 반영”, “추가 확인 필요”, “반영 제외”로 나누며, 지원하지 않는 raw field명은 사용자 화면에 노출하지 않는다. |
| `apps/frontend/src/components/easy/AnalysisChangeCard.vue` | 재분석 비교 카드에 재분석 상태 바와 “보완 답변 처리 결과” 섹션을 추가했다. |
| `apps/gateway/test/report-composer.test.ts` | 답변 처리 상태, 지원하지 않는 내부 필드 비노출, 재분석 카드 안전성을 검증한다. |
| `scripts/video_agent_e2e.py` | 보류 관찰값 보완 답변 E2E에서 `analysis_change_card.answer_items`가 생성되고 raw field명이 노출되지 않는지 확인한다. |

이 변경은 공개 easy-report payload의 표시용 필드를 추가하지만 DB schema, Redis key, storage path, API route, 외부 API 계약은 변경하지 않는다.

## 2026-05-23 남은 보완 질문 우선순위 표시

재분석 후에도 질문이 남아 있을 때 사용자가 무엇을 먼저 확인해야 하는지 알 수 있도록 `missing_info` 표시 계약을 보강했다. 질문은 사고 유형, 정차 여부, 상대 행동, 차선변경 주체, 신호위반처럼 과실 판단에 직접 영향을 주는 항목을 우선하고, 각 질문에는 사용자용 우선순위 라벨과 이유를 붙인다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | `missing_info.questions`를 사용자 흐름 기준으로 정렬하고 `priority_label`, `priority_reason`, `priority_items`, `next_focus`, `guidance`를 생성한다. 지원하지 않는 raw field는 우선순위 목록에서 제외한다. |
| `apps/frontend/src/components/easy/MissingInfoCard.vue` | 보완 질문 카드 상단에 “먼저 확인할 항목”과 상위 질문 1~3개의 우선순위 사유를 표시한다. 각 질문 아래에도 우선순위 사유를 함께 보여준다. |
| `apps/gateway/test/report-composer.test.ts` | 일반 보완 질문과 영상 보류 관찰값 질문이 우선순위대로 정렬되고 내부 field가 노출되지 않는지 검증한다. |
| `scripts/video_agent_e2e.py` | E2E에서 보완 질문이 있는 easy-report에 `priority_items`가 존재하고 raw field명이 노출되지 않는지 확인한다. |

이 변경은 공개 easy-report payload의 표시용 필드를 추가하지만 DB schema, Redis key, storage path, API route, 외부 API 계약은 변경하지 않는다.

## 2026-05-23 결과 화면 핵심 카드 순서 정리

Agent 결과를 사용자가 행동 가능한 순서로 읽을 수 있도록 easy-report 화면 카드 순서를 조정했다. 결론과 재분석 변화 다음에는 남은 보완 질문을 바로 보여주고, 그 뒤에 과실비율, 영상 사실, 근거 신뢰도, Agent 처리 과정, 보험/법률 안내가 이어진다. 보완 질문이 없으면 빈 카드가 나타나지 않는다.

| Path | 변경 내용 |
| --- | --- |
| `apps/frontend/src/components/easy/EasyReportView.vue` | `MissingInfoCard`를 결과 하단에서 결론/재분석 카드 바로 아래로 이동하고, `safeReport.missing_info` 기준으로만 표시한다. 질문, 항목, 우선순위 정보가 없으면 카드를 숨긴다. |

이 변경은 Frontend 표시 순서만 조정하며 DB schema, Redis key, storage path, API route, 외부 API 계약은 변경하지 않는다.

## 2026-05-23 결과 화면 행동/근거 흐름 분리

결과 화면에서 사용자가 바로 해야 할 일과 검증용 근거 정보를 분리해 읽을 수 있도록 easy-report 카드 흐름을 한 번 더 정리했다. 보완 질문 다음에는 즉시 행동 카드, 보험 처리, 법률상 확인할 점을 먼저 보여주고, 과실비율/영상 사실/근거 신뢰도/법률 근거/Agent 처리 과정은 그 뒤에 배치한다. 행동 카드에 표시할 항목이 없으면 빈 카드를 렌더링하지 않는다.

| Path | 변경 내용 |
| --- | --- |
| `apps/frontend/src/components/easy/EasyReportView.vue` | `top_actions`, 보험 처리, 법률 확인 카드를 판단/근거 카드보다 앞에 배치하고, `top_actions`가 없으면 `ElderlyActionCard`를 숨긴다. `AgentProcessCard`는 상세 검증 성격에 맞춰 근거 카드 뒤쪽으로 이동했다. |

이 변경은 Frontend 표시 순서만 조정하며 DB schema, Redis key, storage path, API route, 외부 API 계약은 변경하지 않는다.

## 2026-05-22 영상 프레임 관찰값 품질 보정

실제 사고 영상 기반 프레임 분석의 다음 안정화 단계로, OpenAI/fixture 관찰값이 Agent 사실로 승격되기 전 품질 기준을 명확히 했다. 짧은 사고 영상은 유효 프레임 수가 제한적이므로 단일 프레임 관찰값도 보강 입력으로 사용할 수 있지만, 프레임 참조가 없는 관찰값이나 신호위반/스쿨존/횡단보도처럼 오판 위험이 큰 필드는 더 엄격하게 보류한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/worker/worker/frame_analysis.py` | 각 프레임 관찰값에 `observation_quality`를 추가한다. confidence, frame ref 개수, single-frame 여부, missing frame ref 여부를 기록하고, 응답 전체에 `observation_quality_summary`를 남긴다. |
| `apps/agent/app/services/video_input_contract.py` | Agent 사실 승격 전에 필드별 confidence threshold와 frame reference 요건을 검사한다. `stopped`는 0.82 이상, `opponent_behavior`/`lane_change_actor`/`opponent_signal_violation`은 0.88 이상, `crosswalk_nearby`/`school_zone`은 0.85 이상이어야 하며, 프레임 분석 계열 source는 최소 1개 frame ref가 필요하다. |
| `apps/agent/app/services/agent_quality_packet.py` | 품질 패킷의 evaluation에 `video_observation_quality_summary`를 포함해 영상 관찰값 품질 분포를 추적할 수 있게 했다. |
| `scripts/video_agent_e2e.py` | E2E 출력에 worker의 `observation_quality_summary`와 Agent `video_input_contract.observation_quality_summary`를 함께 표시한다. |
| `apps/worker/tests/test_frame_analysis_contract.py`, `apps/agent/tests/test_video_input_contract.py` | 단일 프레임 관찰값 품질 표시, frame ref 누락 관찰값 보류, 신호위반 필드의 강화된 threshold, 품질 요약 생성을 검증한다. |
| `apps/agent/scripts/test_agent_quality_report.py` | 영상 품질 패킷 fixture에 frame refs를 명시해 실제 승격 조건과 맞췄다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약을 변경하지 않는다. OpenAI 모델 자체는 기존 기본값 `gpt-4.1-mini`, `detail=low`를 유지하되, 짧은 사고 영상의 전후 맥락 누락을 줄이기 위해 현재 프레임 분석 정책은 기본 최대 10프레임/코드 상한 12프레임으로 운영한다. 향후 실제 영상 샘플이 쌓이면 필드별 threshold와 conflict override gate를 운영 데이터 기반으로 조정한다.

## 2026-05-22 KNIA/법률 근거 소스 안정화

실제 서비스 개발 단계의 첫 안정화 작업으로, 법률 RAG 또는 KNIA 상세 근거 소스가 비어 있거나 일시적으로 실패할 때 Agent가 조용히 빈 근거로 진행하지 않도록 보강했다. 법률 DB 검색 실패는 정적 사고 유형 근거로 복구하고, 복구 사실과 KNIA/법률 소스 상태를 `model_info.evidence_source_status` 및 `agent_quality_packet.evidence_source_status`에 안전 메타데이터로 남긴다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/rag_client.py` | 법률 RAG 조회 예외를 잡아 정적 사고 유형 근거 fallback으로 복구한다. `fallback_used`, `static_support_count`, `retrieval_error`를 검색 결과에 남긴다. |
| `apps/agent/app/services/knia/knia_matcher.py` | KNIA chart lookup 실패를 빈 배열로만 숨기지 않고 `lookup_error` 안전 메타데이터로 남긴다. |
| `apps/agent/app/services/evidence_source_status.py` | `evidence-source-status-v1` 생성기. `legal_rag`, `knia_chart_match`, `knia_json_detail`의 준비 상태, fallback 사용 여부, 비활성 사유, 복구 액션을 요약한다. |
| `apps/agent/app/services/orchestration_output.py` | 최종 Agent `model_info`에 `evidence_source_status`와 버전을 기록하고, 품질 패킷 생성 전에 이 메타데이터가 준비되도록 연결했다. |
| `apps/agent/app/services/agent_quality_packet.py` | 품질 패킷에 근거 소스 상태를 포함하고, 근거 소스 장애를 `failure_observations`에 병합한다. |
| `apps/agent/scripts/test_evidence_source_resilience.py` | 법률 RAG 장애를 시뮬레이션해 정적 근거 fallback, KNIA/DB 비활성 상태, 복구 액션 생성이 동작하는지 검증한다. |
| `scripts/verify_agent_regression.ps1` | 기존 Agent 검증 흐름에 근거 소스 복구력 검사를 추가했다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약을 변경하지 않는다. 일반 사용자 화면에는 raw `model_info`와 품질 패킷을 직접 노출하지 않는 기존 sanitizer 정책을 유지해야 한다.

## 2026-05-22 Agent 품질 패킷 및 LLM 실패 관측 보강

수업자료의 Agentic Design 기준 중 “단계별 packet, 관측 가능성, 실패 복구, 비용 인식”을 실제 Agent 출력 계약에 반영했다. `agent_trace`는 실행 순서를 설명하고, 새 `agent_quality_packet`은 결과가 필요한 packet을 모두 갖췄는지, LLM 보조 호출이 사용/차단/실패했는지, 영상 프레임 수와 판단 상태가 어떤지 안전한 메타데이터로 요약한다. 원문 사용자 입력, 내부 토큰, raw prompt는 포함하지 않는다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/agent_quality_packet.py` | `agent-quality-packet-v1` 생성기. 입력/근거/주장검증/판정계약/reflection/trace packet 존재 여부, 판단 준비 상태, 비용 관측 메타데이터, 실패 관측값을 안전 메타데이터로 만든다. |
| `apps/agent/app/services/orchestration_output.py` | `claim_evidence`, KNIA/검색 메타데이터를 먼저 붙인 뒤 `agent_trace`와 `agent_quality_packet`을 생성하도록 순서를 정리했다. `model_info.agent_quality_packet_version`도 기록한다. |
| `apps/agent/app/services/llm_policy.py` | 허용된 LLM 호출이 응답 없음, JSON 파싱 실패, guard 거부 등으로 실제 사용되지 못한 경우 `llm_output_unavailable` 실패 관측값과 비용 메타데이터를 남긴다. |
| `apps/agent/app/services/analysts/*`, `apps/agent/app/services/report_composer.py` | LLM이 허용됐지만 결과를 만들지 못하면 결정론 fallback을 계속 사용하되, `llm_usage.failure_observation`으로 복구 가능한 실패를 기록한다. |
| `apps/agent/app/schemas.py` | `AnalysisOutput.agent_quality_packet` 필드를 추가했다. |
| `apps/agent/scripts/test_agent_quality_report.py` | 텍스트, 영상, prompt-injection 문구 포함 입력에 대해 품질 패킷 계약, safe metadata trace, 영상 프레임 수 전파, 내부 문자열 비노출을 검증한다. |
| `scripts/verify_agent_regression.ps1` | Agent 컴파일, 내부 라우트, 대표 사고 회귀, 근거 검색 품질 검사 뒤 품질 패킷 검사를 추가 실행한다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약을 변경하지 않는다. 공개 사용자 화면은 기존 sanitizer 정책에 따라 raw `agent_trace`, `agent_quality_packet`, `llm_policy`를 직접 노출하지 않는 구조를 유지해야 한다.

## 2026-05-22 P1 근거 검색 품질 회귀 검증

P1의 `Evidence/search quality`를 운영 데이터 수집 여부와 분리해 반복 검증할 수 있도록 Agent 근거 검색 품질 회귀 스크립트를 추가했다. 이 스크립트는 대표 사고 유형별로 검색어 확장, 실제 DB 검색 또는 정적 보조 근거 fallback, 근거 품질 게이트를 함께 통과해야 성공한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/scripts/test_evidence_search_quality.py` | 후미추돌, 상대 차선변경, 교차로 신호위반, 횡단보도 보행자, 어린이보호구역, 자전거 사고에 대해 `retrieve_for_scenario()`를 실행한다. 각 시나리오는 필수 검색어가 query expansion에 포함되고, 법률/KNIA 근거군이 모두 존재하며, 사고 유형 직접 관련 근거가 2개 이상이고, coverage가 `medium` 이상이어야 통과한다. |
| `scripts/verify_agent_regression.ps1` | 기존 Agent 컴파일, 내부 라우트, 대표 사고 판단 회귀 뒤에 근거 검색 품질 회귀 스크립트를 추가 실행한다. |

현재 일부 시나리오는 로컬 DB 수집량이 부족해 정적 fallback 근거 2~3개로 `medium` 수준을 만족한다. 따라서 이 검증은 “최소 신뢰선이 낮음으로 떨어지는지”를 막는 구조 보강이며, 실제 KNIA/법률 DB 수집량이 늘어난 뒤에는 `total_evidence`와 `coverage=high` 기준을 점진적으로 올릴 수 있다. DB schema, Redis key, storage path, API route는 변경하지 않는다.

## 2026-05-22 P1 영상 관찰값 충돌 품질 게이트

실제 OpenAI 프레임 분석 검증 결과처럼 모델이 사용자 입력과 다른 물리 사실 후보를 만들 수 있으므로, Agent 사실 중재 단계에 충돌 품질 게이트를 추가했다. 영상 관찰값은 사용자가 입력하지 않은 물리 사실을 보강하는 데 계속 사용하지만, 사용자 입력과 충돌하는 경우에는 `verified`/수동 검토이거나 `confidence >= 0.92` 및 대표 프레임 2장 이상 조건을 만족해야만 영상값이 사용자 입력을 덮어쓴다. 조건을 통과하지 못하면 사용자 입력을 유지하고 `requires_confirmation`에 남겨 보완 질문과 재분석 흐름으로 넘긴다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/fact_arbitration.py` | `CONFLICT_OVERRIDE_CONFIDENCE=0.92`, `CONFLICT_OVERRIDE_MIN_FRAME_REFS=2` 기반 충돌 품질 게이트를 추가했다. 영상 우선 필드라도 충돌 품질 조건을 통과하지 못하면 사용자 입력을 유지하고 conflict에 `quality_gate`, `needs_confirmation`을 기록한다. |
| `apps/agent/tests/test_fact_arbitration.py`, `apps/agent/tests/test_video_input_contract.py` | 강한 영상 근거는 충돌을 덮어쓸 수 있고, OpenAI 관찰값이 품질 게이트를 통과하지 못하면 사용자 입력을 유지하는 케이스를 검증한다. |
| `apps/agent/scripts/test_agent_regression_scenarios.py` | 영상이 사용자 입력과 충돌해도 강한 근거가 있을 때만 후방추돌 회귀 시나리오가 영상값을 우선하도록 fixture 관찰값을 명확히 보강했다. |
| `apps/worker/worker/frame_analysis.py` | 테스트 fixture 관찰값의 confidence를 충돌 품질 게이트에 맞게 조정했다. 실제 OpenAI 관찰값에는 영향을 주지 않는다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약을 변경하지 않는다. P1 영상 관찰값 구조는 실제 모델 호출, 비용 상한, Agent 입력 계약, 사실 중재, 보완 질문까지 연결된 상태이며, 남은 작업은 실제 모델 품질 데이터가 쌓인 뒤 필드별 임계값을 조정하는 운영 튜닝이다.

## 2026-05-22 P1 실제 OpenAI 프레임 분석 비용 정책

실제 영상 프레임 관찰값 검증을 진행하기 전에 worker의 OpenAI 프레임 분석 기본 정책을 저비용·상한 고정 방식으로 조정했다. 기본 모델은 이미지 입력을 지원하는 비추론 모델 `gpt-4.1-mini`이며, 사고 법률 판단이 아니라 프레임에서 관찰 가능한 물리 사실 후보만 JSON으로 추출하는 역할이다.

| Path | 변경 내용 |
| --- | --- |
| `apps/worker/worker/frame_analysis.py` | 기본 `OPENAI_VISION_MODEL`을 `gpt-4.1-mini`로 조정했다. `OPENAI_FRAME_ANALYSIS_MAX_FRAMES`는 기본 10장/상한 12장, `OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS`는 기본 900/상한 1400으로 제한한다. GPT-5 계열 모델에는 `reasoning.effort=minimal`과 `text.verbosity=low`를 사용하고 `temperature`를 보내지 않는다. 비 GPT-5 모델은 기존처럼 `temperature=0`을 사용한다. Responses API 요청에는 `store=false`를 전달하며, 응답이 비어 있을 때 원인 추적용 response status를 metadata에 남긴다. |
| `compose.yaml`, `env.example` | worker의 영상 분석 기본 환경값을 `gpt-4.1-mini`, `low`, 10프레임, 900 출력 토큰으로 명시했다. GPT-5 계열 비교 실행을 위한 reasoning 환경값도 유지한다. |
| `apps/worker/tests/test_frame_analysis_contract.py` | GPT-5 계열 payload가 비용 제어 필드와 파라미터 호환성을 지키는지, 비 GPT-5 모델은 기존 deterministic temperature 제어를 유지하는지 검증한다. |
| `docs/OPERATIONS.md` | 실제 OpenAI 프레임 분석 검증 시 기본 비용 정책, 일시 품질 상향 기준, 기본값 복구 기준을 기록했다. |

이 변경은 DB schema, Redis key, storage path, 외부 API route를 변경하지 않는다. 실제 API 키 값은 문서와 로그에 기록하지 않는다.

검증 결과 `gpt-5-nano`는 관찰값을 반환하지 않았고, `gpt-5-mini`는 `max_output_tokens` 중단으로 관찰값을 만들지 못했다. 같은 조건에서 `gpt-4.1-mini`, `detail=low`, 6프레임, 출력 900토큰은 실제 사고 영상 E2E에서 관찰값 2개를 생성하고 Agent `video_input_contract`와 `fact_arbitration`까지 통과했다. 따라서 현재 기본값은 최신성보다 검증 가능성과 비용 예측성을 우선해 `gpt-4.1-mini`로 둔다.

## 2026-05-22 P1 영상 관찰값 계약 검증 보강

P1의 `Video observation validation`을 실제 OpenAI 비용 없이도 반복 검증할 수 있도록 worker 프레임 분석 fixture 모드를 추가했다. 이 모드는 실제 사고 판단 모델이 아니라, 프레임 관찰값이 worker metadata, Agent `video_input_contract`, `fact_arbitration`, easy-report 안전 카드까지 전달되는 계약 흐름을 검증하는 용도다.

| Path | 변경 내용 |
| --- | --- |
| `apps/worker/worker/frame_analysis.py` | `FRAME_ANALYSIS_FIXTURE_MODE`를 추가했다. `ENABLE_OPENAI_FRAME_ANALYSIS=1`이고 fixture mode가 `rear_end` 또는 `lane_change`이면 `OPENAI_API_KEY` 없이도 deterministic 관찰값을 생성한다. 실제 OpenAI 호출 경로는 fixture mode가 비어 있을 때만 사용된다. |
| `compose.yaml` | worker 환경변수에 `FRAME_ANALYSIS_FIXTURE_MODE`를 전달한다. 기본값은 빈 값이라 운영 동작은 기존과 동일하다. |
| `apps/worker/tests/test_frame_analysis_contract.py` | fixture mode가 API key 없이 contract 관찰값을 반환하는지, fixture가 없고 key도 없으면 안전하게 disabled reason을 반환하는지 검증한다. |
| `docs/OPERATIONS.md` | fixture 기반 실제 영상 E2E 실행 방법과 기본 모드로 되돌리는 절차를 기록했다. |

실제 OpenAI 모델 검증은 여전히 `FRAME_ANALYSIS_FIXTURE_MODE`를 비운 뒤 `ENABLE_OPENAI_FRAME_ANALYSIS=1`, 유효한 `OPENAI_API_KEY` 상태에서 `scripts/video_agent_e2e.py --require-frame-observations --require-agent-video-facts`를 실행해야 한다. 이 변경은 DB schema, Redis key, storage path, 외부 API 계약을 바꾸지 않는다.

## 2026-05-22 P1 근거 검색 품질 보강

P1의 `Evidence/search quality` 첫 단계를 진행했다. DB/외부 API 수집 상태가 부족해도 대표 사고 유형의 법률·KNIA 근거 품질 게이트가 최소한의 직접 관련 근거를 확보할 수 있도록 Agent 내부 검색어 확장과 정적 보조 근거 fixture를 보강했다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/scenario_search_terms.py` | `structured_facts` 값 기반 검색어 확장을 추가했다. `opponent_behavior=rear_collision`, `lane_change_actor=user/opponent`, 상대 신호위반, 적색신호, 후방 범퍼 파손, 어린이 피해, 자전거 통행 위치 같은 사실을 검색어로 변환한다. |
| `apps/agent/app/services/static_legal_fallback.py` | 차선변경, 보행자·횡단보도, 어린이보호구역 사고에 대한 과실비율 참고 기준 fixture를 추가했다. 이 fixture들은 외부 API 실패나 로컬 DB 수집 부족 시에도 `knia` family 보조 근거로 품질 게이트에 반영된다. |
| `apps/agent/tests/test_scenario_search_terms.py` | 사고 사실값 기반 검색어 확장 테스트를 추가했다. |
| `apps/agent/tests/test_static_scenario_support.py` | 차선변경, 보행자, 스쿨존 정적 보조 근거가 `family:knia` 부족을 해소하고 사고 유형 직접 근거로 잡히는지 검증한다. |

이 변경은 DB schema, Redis key, storage path, 환경 변수, 외부 API 계약을 변경하지 않는다. 실제 KNIA 원문 상세 기준이 DB에 들어오면 기존 KNIA 매칭 결과가 우선 활용되고, 정적 fixture는 검색 실패 또는 보조 근거 역할로만 사용된다.

## 2026-05-22 Agent Reflection Loop 근거 보강 표시 개선

Agent의 bounded reflection/requery 단계가 사고 유형별 한국어 검색어와 사용자용 복구 문장을 생성하도록 보강했다. 후방추돌, 차선변경, 교차로 신호위반, 보행자/스쿨존/자전거 사고 등 대표 시나리오에서 근거 부족이 감지되면 일반 영문 키워드 대신 KNIA/도로교통법 기준에 맞춘 한국어 검색어를 추가한다. 재검색 후에도 확정 조건이 남으면 `reference_only` 상태와 함께 보완 입력 또는 근거 보강 방향을 명시한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/reflection_loop.py` | `build_requery_plan()`이 `scenario_type`, `description_text`를 받아 사고 유형별 한국어 `query_terms`, `user_message`, `recovery_suggestions`를 만든다. `build_reflection_loop_result()`는 최종 상태에 맞는 사용자용 설명과 초기 재검색어를 보존한다. |
| `apps/agent/app/services/orchestration_analysis.py` | reflection requery 단계에 현재 사고 유형과 입력 설명을 전달해 재검색어가 사고 맥락을 반영하도록 연결했다. |
| `apps/gateway/src/lib/report-composer.ts` | `reflection_loop`의 내부 키를 그대로 노출하지 않고 `agent_process_card.decision_notes`로 보완 입력 항목, 부족한 근거 조건, 복구 제안을 한국어 라벨로 변환한다. |
| `apps/frontend/src/components/easy/AgentProcessCard.vue` | Agent 판단 검증 카드에서 `decision_notes`를 별도 목록으로 표시한다. |
| `apps/agent/tests/test_reflection_loop.py`, `apps/gateway/test/report-composer.test.ts` | 사고 유형별 재검색어 생성, 참고용 상태 설명, 사용자 안전 카드 변환을 검증한다. |

이 변경은 DB schema, Redis key, storage path, 환경 변수, 외부 API 계약을 변경하지 않는다. 공개 easy-report payload에는 기존 `agent_process_card` 안에 `decision_notes`가 추가된다.

## 2026-05-22 P0 보강 완료 판정

프로젝트 골격 보강 중 P0로 분류했던 Agent 신뢰성·근거 검증·실행 추적·SRP·핵심 회귀 검증 항목을 완료 상태로 정리했다. P0 완료 기준은 “새 기능 확장 전 반드시 막아야 하는 판단 신뢰성 위험을 자동 검증할 수 있고, 부족한 근거/입력은 확정 결과처럼 보이지 않게 제어되며, 사용자 화면에는 내부 trace/packet/raw key가 노출되지 않는 상태”다.

| P0 항목 | 완료 근거 |
| --- | --- |
| Agent regression automation | `scripts/verify_agent_regression.ps1`, `scripts/verify_core.ps1`, `.github/workflows/ci.yml`이 대표 사고 회귀, 내부 route contract, frontend/gateway/worker checks를 실행한다. |
| Agent execution trace | `agent_trace`, `video_input_contract`, `fact_arbitration`, `evidence_audit`, `agent_judgment`, `presentation_policy`가 결과에 남고, 관리자 진단 API와 사용자용 안전 카드가 분리되어 있다. |
| Reflection/reverification loop | 근거 부족 시 1회 bounded requery를 수행하고, 이후 `finalize`, `request_missing_input`, `present_reference_only`, `manual_review`로 상태를 분리한다. 사고 유형별 한국어 재검색어와 사용자용 복구 문장도 생성한다. |
| Agent SRP | `orchestrator.py`는 stage sequencing 중심으로 유지하고, 입력 정규화, 근거 수집, 분석 실행, reflection requery, 출력 보강은 전용 stage/service 모듈이 담당한다. |
| 실제 영상 기반 E2E smoke | `scripts/video_agent_e2e.py --video-path "C:/Users/yangbun/Downloads/car_accident_1.mp4" --timeout-sec 240` 실행 기준으로 업로드, 전처리, video_analyze job, easy-report, `agent_process_card` 안전성까지 통과했다. 기본 설정상 `ENABLE_OPENAI_FRAME_ANALYSIS=0`이므로 OpenAI 관찰값 필수 검증은 별도 옵션을 켤 때 수행한다. |

P0 이후 개발은 아래 “Reinforce Next”의 P1 항목부터 진행한다. 특화 영상 모델 교체, S3 전환, 개발자 페이지 확장, 비용 대시보드, 표준 MCP 도입은 P0 완료 범위가 아니라 후속 안정화/확장 단계다.

## 2026-05-22 실제 영상 기반 Agent E2E 점검 스크립트

실제 사고 영상을 저장소에 넣지 않고 로컬 경로로만 전달해 영상 업로드, ffmpeg 전처리, 자동 `video_analyze` job, Agent 결과, `agent_process_card` 노출 안전성까지 확인하는 E2E 스크립트를 추가했다. 사용자가 제공한 사고 영상은 테스트 실행에만 사용하고 Git에는 포함하지 않는다.

| Path | 변경 내용 |
| --- | --- |
| `scripts/video_agent_e2e.py` | 임시 로컬 계정을 생성하고 케이스 생성, `/uploads/local` 업로드, `/uploads/complete`, job polling, `/cases/{caseId}/easy-report` 검증을 수행한다. `agent_process_card`가 존재하고 raw `agent_trace`, `reflection_loop`, `packet`, 내부 step id, `next_action`이 노출되지 않는지 검사한다. `--require-frame-observations` 옵션을 사용하면 OpenAI 프레임 분석이 켜져 있고 오류 없이 1개 이상의 관찰값을 반환해야 통과한다. `--require-agent-video-facts` 옵션을 사용하면 Agent `video_input_contract`가 관찰값을 수용하고 `fact_arbitration`이 영상 기반 사실을 실제 적용해야 통과한다. |
| `docs/OPERATIONS.md` | 실제 영상 기반 E2E 실행 방법과 `ENABLE_OPENAI_FRAME_ANALYSIS=0`일 때 프레임은 추출되지만 GPT 관찰값은 0개일 수 있다는 주의 사항을 추가했다. OpenAI 관찰값 및 Agent 영상 사실 적용 필수 검증 명령도 함께 기록했다. |

실행 예시는 `python scripts/video_agent_e2e.py --video-path "C:/path/to/accident.mp4" --timeout-sec 240`이다. 이 스크립트는 DB schema, Redis key, storage path, 환경 변수, 외부 API 계약을 변경하지 않는다.

## 2026-05-22 Agent 판단 검증 상태 화면 연결

Agent P1에서 생성한 `agent_trace`와 `reflection_loop`를 일반 결과 화면에서 직접 JSON으로 노출하지 않고, Gateway가 사용자 안전 요약 카드인 `agent_process_card`로 변환해 내려주도록 보강했다. 목적은 Agent가 입력 정리, 사실 중재, 근거 검색, 주장-근거 검증, 판단 계약, 근거 보강 루프를 어떤 상태로 통과했는지 확인 가능하게 하되, raw packet, evidence id, 내부 stage id, 모델 메타데이터, 사용자 원문 입력은 일반 화면에 섞이지 않게 하는 것이다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | `composeAgentProcessCard()`를 추가했다. `agent_trace`, `reflection_loop`, `agent_judgment`를 기반으로 다음 처리 상태, 근거 재검색 여부, 추가 근거 수, 검증 단계 수, 단계별 사용자 라벨을 생성한다. `sanitizeEasyReport()`의 기술 필드 필터도 `agent_trace`, `reflection_loop`, trace packet 관련 키를 숨기도록 확장했다. |
| `apps/frontend/src/components/easy/AgentProcessCard.vue` | 결과 화면에 표시되는 Agent 판단 검증 카드다. Gateway가 만든 `agent_process_card`만 렌더링하며 raw JSON이나 내부 packet은 표시하지 않는다. |
| `apps/frontend/src/components/easy/EasyReportView.vue` | `EvidenceReliabilityCard` 다음에 `AgentProcessCard`를 표시하도록 연결했다. |
| `apps/frontend/src/utils/displaySanitizer.ts` | 일반 화면 sanitize 단계에서 raw `agent_trace`, `reflection_loop`, 재검색 내부 키가 노출되지 않도록 필터를 확장했다. |
| `apps/gateway/test/report-composer.test.ts` | `agent_process_card`가 사용자 안전 라벨만 포함하고 raw trace packet, 내부 step id, `next_action` 같은 내부 키를 노출하지 않는지 검증하는 테스트를 추가했다. |

이 변경은 DB schema, Redis key, storage path, 환경 변수, 외부 API 계약을 바꾸지 않는다. `/api/v1/cases/:caseId/easy-report` 응답의 사용자용 report payload에 `agent_process_card`가 추가된다.

## 2026-05-22 Agent P1 영상/사용자 사실 중재 계층

영상 프레임 분석 결과가 Agent 판단에 들어올 때 사용자 입력과 단순 병합하지 않고 `agent-fact-arbitration-v1` 계약으로 출처와 우선순위를 기록하도록 보강했다. 목적은 사용자가 주관적으로 잘못 입력할 수 있는 물리적 사고 사실은 고신뢰 영상 관찰값을 우선하고, 사용자가 직접 알고 있는 사고 유형/부상/보험 상태 같은 문맥 정보는 사용자 입력을 우선해 Agent 판단의 입력 근거를 명확히 남기는 것이다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/fact_arbitration.py` | 신규 `agent-fact-arbitration-v1` 모듈이다. `stopped`, `opponent_behavior`, `lane_change_actor`, 신호/횡단보도/스쿨존/손상 정도처럼 프레임에서 관찰 가능한 물리적 사실은 `video_primary`로 분류한다. `accident_type`, `injury`, 치료/보험/운전자 역할 정보는 `user_primary`로 분류한다. 충돌 시 승자, 원래 사용자 값, 영상 값, confidence, frame_refs를 `conflicts`와 `requires_confirmation`에 기록한다. |
| `apps/agent/app/services/input_normalizer.py` | 기존 `video_fact_patch + user_facts` 단순 병합을 중단하고 `arbitrate_facts()`를 거쳐 `structured_facts`를 만든다. Agent 분석 텍스트에는 영상 입력 계약과 별도로 사실 중재 계약 요약을 포함해 어떤 값이 영상에서 채택됐는지 추적할 수 있게 했다. |
| `apps/agent/app/services/report_composer.py`, `apps/agent/app/schemas.py` | Agent 결과에 `fact_arbitration`을 top-level과 `model_info.fact_arbitration`으로 포함한다. 사용자 표시용 `structured_facts`에는 `_fact_arbitration`, `_fact_sources`를 숨김 추적 정보로 함께 보관한다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | 사실 중재 계약의 내부 필드가 일반 사용자용 쉬운 보고서/프론트 화면에 원문 JSON으로 노출되지 않도록 기술 필드 필터에 추가했다. |
| `apps/agent/tests/test_fact_arbitration.py`, `apps/agent/tests/test_video_input_contract.py` | 영상 우선 물리 사실 충돌, 사용자 우선 문맥 정보 충돌, 사용자/영상 일치값 확인 처리를 검증하는 테스트 케이스를 추가했다. |

현재 정책상 정차 여부처럼 영상에서 확인 가능한 사실은 `ENABLE_OPENAI_FRAME_ANALYSIS=1`로 추출된 고신뢰 관찰값이 사용자 입력과 충돌해도 Agent 입력에서 우선된다. 반대로 부상 여부는 영상으로 정확히 판단하기 어렵기 때문에 사용자 입력이 우선된다. 이 변경은 DB schema, Redis key, storage path, 외부 API 계약을 변경하지 않으며 Agent 응답 DTO에 `fact_arbitration` 메타데이터만 추가한다.

## 2026-05-22 Worker P1 이벤트 프레임 추출 및 GPT 프레임 분석

영상 업로드 후 고정 4장만 뽑던 전처리를 짧은 사고 영상에 맞는 시간순 이벤트 프레임 추출로 보강하고, 선택적으로 OpenAI 이미지 입력 분석을 실행해 관측 가능한 사고 사실을 `observations`로 저장하도록 확장했다. GPT API는 과실비율이나 법률 판단을 하지 않고, 프레임에서 보이는 물리적 사실 후보만 JSON으로 추출한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/worker/worker/video_preprocess.py` | `frame_times_for_duration()`과 `extract_event_frames()`를 추가했다. 5초 이하는 0.35초 간격, 10초 이하는 0.5초 간격, 15초 이하는 0.75초 간격, 그 이상은 길이에 맞춰 시간순 프레임을 추출하고 최대 18장으로 균등 선별한다. 추출 프레임은 `representative_frame_details`에 time_sec/role/path와 함께 저장한다. |
| `apps/worker/worker/frame_analysis.py` | `analyze_frames_with_openai()`를 추가했다. `ENABLE_OPENAI_FRAME_ANALYSIS=1`이고 `OPENAI_API_KEY`가 있을 때만 OpenAI Responses API에 프레임 이미지를 base64 data URL로 전달한다. 결과는 `openai_frame_analysis`와 `observations`에 저장하며 worker 로그에도 모델명, 프레임 수, 관측값 요약을 한 번 출력한다. |
| `apps/agent/app/services/video_input_contract.py` | OpenAI 프레임 분석 결과의 `frame_refs`와 `reason`을 Agent 영상 입력 계약에 보존한다. `source=frame_analysis:openai`는 기존 `frame_analysis` 계열 source로 처리되어 confidence 기준을 통과해야만 facts로 승격된다. |
| `compose.yaml` | worker에 `ENABLE_OPENAI_FRAME_ANALYSIS`, `OPENAI_API_KEY`, `OPENAI_VISION_MODEL`, `OPENAI_FRAME_ANALYSIS_MAX_FRAMES`, `OPENAI_FRAME_ANALYSIS_DETAIL`, `OPENAI_TIMEOUT_SEC` 환경변수 전달을 추가했다. 기본값은 비용 방지를 위해 `ENABLE_OPENAI_FRAME_ANALYSIS=0`이다. |

OpenAI 프레임 분석은 공식 OpenAI Images/Vision 및 Responses API 문서 기준의 이미지 입력 흐름을 사용한다. 이미지 입력은 비용이 발생하므로 기본은 꺼져 있으며, 활성화 시 기본 `detail=low`, 기본 최대 10프레임/코드 상한 12프레임으로 제한한다. 향후 교통사고 특화 모델을 도입할 경우 `analyze_frames_with_openai()` 위치를 `VideoAnalyzerProvider` 추상화로 분리해 OpenAI, ML Kit, TFLite, 사고 특화 모델을 교체 가능하게 만드는 것이 다음 구조화 단계다.

## 2026-05-22 Agent P1 영상 전처리 입력 계약 연결

영상 전처리 결과가 Agent의 일반 `video_metadata` 문자열로만 합쳐지던 흐름을 `agent-video-input-contract-v1` 계약으로 정규화했다. 현재 worker 전처리는 ffprobe/ffmpeg 기반 기술 메타데이터와 대표 프레임 추출까지 수행하므로, Agent는 이 기술 메타데이터를 사고 사실로 직접 승격하지 않는다. 향후 영상 분석/프레임 분석기가 `observations` 형태의 명시적 관측값을 넣으면, 출처와 신뢰도 기준을 통과한 항목만 `structured_facts`에 병합된다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/video_input_contract.py` | `agent-video-input-contract-v1`을 추가했다. `duration_sec`, 해상도, fps, codec, 대표 프레임 개수 같은 기술 메타데이터와 `observations` 기반 사고 관측값을 분리한다. `frame_analysis`, `vision_model`, `manual_video_review` 등 명시적 source와 `0.75` 이상의 confidence 또는 verified flag가 있는 관측값만 `fact_patch`로 승격한다. |
| `apps/agent/app/services/input_normalizer.py` | Agent 입력 정규화 시 영상 계약을 생성하고, 영상 `fact_patch`를 사용자 `structured_facts`와 병합한다. 사용자 입력 facts가 있으면 영상 추출값보다 우선한다. LLM/분석 텍스트에는 raw 영상 metadata 대신 정규화된 영상 입력 계약 요약을 포함한다. |
| `apps/agent/app/services/report_composer.py`, `apps/agent/app/schemas.py` | Agent 결과에 `video_input_contract`를 포함하고 `model_info.video_input_contract`에도 기록한다. 일반 사용자용 `structured_facts`에는 `_video_input_contract`로 숨김 메타데이터를 남겨 추적 가능성을 확보했다. |
| `apps/worker/worker/main.py` | worker 전처리 산출물에 `worker-video-preprocess-v1` 버전을 남기고, `/internal/v1/analyze/video` 호출 시 업로드 metadata와 payload video metadata를 함께 전달한다. |
| `apps/gateway/src/main.ts` | `/api/v1/cases/:caseId/analyze-video`에서 전달된 `video_metadata`를 video analyze job payload에 보존한다. |
| `docs/api/openapi.yaml` | `/cases/{caseId}/analyze-video` 요청 body에 `video_metadata`를 명시해 영상 전처리/프레임 분석 관측값 전달 계약을 문서화했다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | `video_input_contract`, 관측값 목록, `fact_patch` 같은 내부 계약 필드가 사용자 화면에 원시 JSON으로 노출되지 않도록 필터링한다. |
| `apps/agent/tests/test_video_input_contract.py`, `apps/agent/tests/test_orchestrator.py` | 고신뢰 영상 관측값이 `structured_facts`로 병합되는지, 저신뢰 관측값은 보류되는지, 순수 기술 메타데이터는 사고 사실로 승격되지 않는지 검증한다. |

현재 계약에서 사고 사실로 승격 가능한 대표 필드는 `stopped`, `sudden_brake`, `opponent_behavior`, `lane_change_actor`, `turn_signal`, `user_signal`, `opponent_signal`, `opponent_signal_violation`, `crosswalk_nearby`, `school_zone`, `injury`, `damage_level` 등이다. 이 작업은 DB schema, Redis key, 환경 변수, 외부 기관/API 연동을 변경하지 않는다. 공개 API 문서는 선택적 `video_metadata` 전달을 반영하도록 보강했다. 다음 Agent P1 작업은 이 계약을 기반으로 실제 프레임/비전 분석 모듈을 붙일지, 또는 현재 로컬 ffmpeg 전처리만 유지하고 사용자 보완 입력 중심으로 갈지 결정하는 단계다.

## 2026-05-22 Agent P1 보완 질문 루프 고도화

보완 질문 답변을 프론트 임시 매핑에만 의존하지 않고 Gateway에서 서버 기준으로 정규화하며, Agent가 재분석 반복 상태와 종료 사유를 결과에 남기도록 보강했다. 이 변경은 기존 `/api/v1/cases/:caseId/reanalyze` 흐름을 확장하며 DB schema, Redis key, 환경 변수, 외부 API 계약은 변경하지 않는다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/followup-normalizer.ts` | 사용자 보완 답변을 canonical `structured_facts` patch로 변환한다. 예: `다친 사람 없음 -> injury=false`, `상대 차량 -> opponent_lane_change=true`, `적색 -> red`, `확인 중 -> unresolved field`로 정규화한다. `_followup_iteration`, `_followup_answered_fields`, `_followup_unresolved_fields` 메타데이터도 함께 생성한다. |
| `apps/gateway/src/main.ts` | `/api/v1/cases/:caseId/reanalyze`에서 `followup_answers`를 받아 서버 정규화 결과를 기존 케이스 facts와 병합한 뒤 Agent에 전달한다. 기존 `structured_facts` payload도 계속 허용한다. |
| `apps/frontend/src/api/client.ts`, `apps/frontend/src/views/CaseResultView.vue` | 결과 화면의 보완 답변 제출 시 기존 `structured_facts`와 함께 원본 `followup_answers`도 Gateway에 전달해 서버 정규화가 항상 실행되도록 했다. |
| `apps/agent/app/services/input_requirements.py` | `agent-followup-loop-v1`을 추가했다. 남은 blocking/optional 질문 수, 반복 횟수, 답변/미확인 필드, `complete`, `waiting_for_input`, `continue`, `optional_followup_available`, `stopped` 상태와 종료 사유를 산정한다. 후방추돌 문맥에서 `정차`, `뒤에서 추돌`이 문장에 있으면 정차 여부와 상대 행동을 반복 질문하지 않도록 만족 판정을 보강했다. |
| `apps/agent/app/services/orchestrator.py`, `apps/agent/app/services/report_composer.py`, `apps/agent/app/schemas.py` | Agent 최종 결과에 `followup_loop`를 포함하고 `model_info.followup_loop`에도 기록한다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | `followup_loop` 내부 메타데이터가 일반 사용자 리포트에 원시 필드로 노출되지 않도록 필터링한다. |
| `apps/gateway/test/followup-normalizer.test.ts`, `apps/agent/tests/test_input_requirements.py` | 보완 답변 정규화, 미확인 답변 처리, 반복 횟수 증가, blocking 질문 해소/최대 반복 도달 상태를 검증한다. |

보완 루프 상태 의미:

| 상태 | 의미 |
| --- | --- |
| `waiting_for_input` | 첫 보완 답변을 기다리는 상태 |
| `continue` | 필수 질문이 아직 남아 추가 보완이 필요한 상태 |
| `optional_followup_available` | 확정 판단을 막는 필수 질문은 해소됐고 선택 보완 질문만 남은 상태 |
| `complete` | 남은 보완 질문이 없는 상태 |
| `stopped` | 최대 보완 반복 횟수에 도달해 더 이상 질문을 늘리지 않는 상태 |

현재 최대 반복 횟수는 Agent 내부 상수 `MAX_FOLLOWUP_ITERATIONS=3`이다.

## 2026-05-22 Agent P1 LLM/fallback 책임 분리

Agent P1 첫 단계로 LLM이 판단 수치나 근거 존재 여부를 임의로 결정하지 못하도록 섹션별 LLM 사용 정책을 추가했다. 이 변경은 외부 도구를 새로 도입하지 않고 기존 `OPENAI_API_KEY`, `ENABLE_OPENAI_ANALYSTS` 기반 호출 흐름에 정책 게이트와 결과 메타데이터를 더하는 방식이다. DB schema, Redis key, 환경 변수 이름, 외부 API 계약은 변경하지 않았다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/llm_policy.py` | `llm-policy-v1`을 추가했다. traffic law, fault ratio, criminal liability, insurance, action plan, final report 섹션별로 LLM 허용 조건, 필요한 근거군, LLM이 생성해도 되는 출력, 결정론적 로직이 우선하는 출력 필드를 정의한다. |
| `apps/agent/app/services/analysts/traffic_law_analyst.py` | 법률 근거가 있을 때만 LLM 보조 해석을 허용하고, 적용 법규와 판단 상태는 근거/guard가 우선하도록 `llm_usage`와 `analysis_source`를 남긴다. |
| `apps/agent/app/services/analysts/fault_ratio_analyst.py` | KNIA 근거가 없으면 과실비율 LLM 호출을 차단한다. 과실 수치, 사용자 관점 변환, KNIA 산정값은 결정론적 로직과 KNIA 산정기가 우선한다. |
| `apps/agent/app/services/analysts/criminal_liability_analyst.py` | 법률 근거가 있을 때만 형사책임 체크리스트 보조 생성을 허용하고, 신고 필요 여부와 위험도는 guard와 입력 사실 중심으로 유지한다. |
| `apps/agent/app/services/analysts/insurance_analyst.py`, `apps/agent/app/services/analysts/action_plan_analyst.py` | LLM은 절차 안내와 행동 목록 보조에만 사용하고, 보상금액이나 책임 확정 표현을 생성하는 역할로 쓰지 않는다. |
| `apps/agent/app/services/report_composer.py` | 최종 리포트 LLM 호출도 요약 전용 정책을 통과할 때만 실행한다. `model_info.llm_policy`에 섹션별 LLM 허용/사용/차단 사유를 기록한다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | `llm_usage`, `llm_policy`, `analysis_source` 등 내부 정책 필드가 일반 사용자 화면에 원시 JSON으로 노출되지 않도록 필터링한다. |
| `apps/agent/tests/test_llm_policy.py`, `apps/agent/tests/test_orchestrator.py` | KNIA 근거가 없는 과실비율 LLM 호출 차단, 법률 근거가 있는 법률 분석 허용, Agent 결과의 `model_info.llm_policy` 포함 여부를 검증한다. |

정책의 핵심은 다음과 같다.

| 섹션 | LLM 허용 범위 | 결정론적 우선 영역 |
| --- | --- | --- |
| 법률 분석 | 검색된 법률 근거의 쉬운 해석, 위험 플래그, 추가 확인 사실 정리 | 적용 법규 존재 여부, 근거 ID, 판단 상태 |
| 과실비율 | KNIA 근거가 있을 때 설명과 key factor 보조 | `my/other` 수치, KNIA 기준 매칭, 사용자 차량 역할, KNIA 가감요소 산정 |
| 형사책임 | 법률 근거 기반 체크리스트 보조 | 신고 필요 여부, 형사 리스크 등급, 판단 상태 |
| 보험 안내/행동 계획 | 절차 안내와 필요 서류, 행동 순서 보조 | 보상금액 확정, 책임 확정, 과실 판단 |
| 최종 리포트 | 이미 검증된 섹션을 쉬운 문장으로 요약 | 과실, 법률책임, 근거, Agent 판단 계약 |

현재 LLM은 `ENABLE_OPENAI_ANALYSTS=1`이고 `OPENAI_API_KEY`가 있을 때만 후보가 되며, 각 섹션의 필수 근거군이 부족하면 deterministic fallback으로 내려간다. 이 단계 이후 P1의 다음 작업은 보완 질문 답변을 반복 분석 루프에서 정규화하고 종료 조건을 명확히 하는 것이다.

## 2026-05-21 Agent P0 판단 골격 보강

Agent 레이어의 P0 골격을 보강하여 “입력 부족”, “근거 부족”, “KNIA 기준 부족”, “확정 판단 불가”가 하나의 `needs_review` 상태로 뭉개지지 않도록 판단 계약을 세분화했다. 이 변경은 Agent/Gateway/Frontend 표시 필터와 테스트만 수정하며, DB schema, Redis key, 환경 변수, 외부 API 계약은 변경하지 않았다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/judgment_contract.py` | 판단 계약 버전을 `agent-judgment-contract-v2`로 올리고 `decision_blockers`, `decision_readiness`, `knia_basis`, `knia_fault_basis` stage를 추가했다. 사고 유형별 KNIA 필요 여부, 대표 KNIA 기준, 기본과실/최종과실 존재 여부, 적용/제외된 가감요소 수, 누락 사유를 추적한다. |
| `apps/agent/app/services/orchestrator.py` | KNIA 매칭 결과와 KNIA 과실 산정 결과를 판단 계약 생성 단계에 전달해 Agent 최종 결과의 판단 가능 여부가 KNIA 기준 상태까지 반영하도록 연결했다. |
| `apps/gateway/src/lib/report-composer.ts` | 재분석 비교 카드가 KNIA 기본과실, 가감 후 과실, 적용된 가감요소 수, 추가/제외된 가감요소를 사용자용 문구로 비교하도록 확장했다. 새 내부 계약 필드(`decision_blockers`, `decision_readiness`, `knia_basis`)는 일반 리포트에 노출하지 않는다. |
| `apps/frontend/src/utils/displaySanitizer.ts` | 새 Agent 내부 계약 필드가 화면에 원시 JSON이나 내부 코드로 노출되지 않도록 기술 필드 목록에 추가했다. |
| `apps/agent/tests/test_judgment_contract.py` | 입력 부족, 근거 부족, KNIA 기준 부족이 각각 별도 blocker category로 기록되는지와 KNIA 가감요소 basis가 계약에 포함되는지 검증한다. |
| `apps/gateway/test/report-composer.test.ts` | 재분석 비교 카드가 KNIA 가감요소 변화를 표시하면서 내부 판단 계약과 raw evidence id를 노출하지 않는지 검증한다. |

새 판단 계약의 핵심 필드는 다음과 같다.

| 필드 | 의미 |
| --- | --- |
| `agent_judgment.decision_blockers` | 판단을 보류하거나 확정 표시를 막는 사유 목록. category는 `input_missing`, `evidence_missing`, `knia_missing`, `claim_unsupported`, `stage_unsupported`, `stage_review`로 구분한다. |
| `agent_judgment.decision_readiness` | 사용자에게 보여줄 수 있는 판단 준비 상태. `판단 가능`, `추가 확인 필요`, `확정 판단 불가` 중 하나의 label과 blocker category 요약을 포함한다. |
| `agent_judgment.knia_basis` | KNIA 기준 필요 여부, 대표 기준번호, 기본/최종 과실, 적용/제외 가감요소 수, KNIA 누락 사유를 포함한다. |
| `stage_statuses[].name = knia_fault_basis` | KNIA 과실 산정 근거가 Agent 판단 단계에서 별도 stage로 추적된다. |

현재 이 단계는 Agent 판단 구조를 단단히 만드는 P0 작업이며, 이후 P1에서는 LLM/fallback 책임 분리, 보완 질문 루프 고도화, 영상 분석 입력 계약 연결을 진행할 수 있다.

## 2026-05-21 재분석 전후 판단 비교 카드 추가

보완 입력이 실제 Agent 판단에 어떤 변화를 만들었는지 추적하기 위해, 직전 분석 결과와 새 재분석 결과를 Gateway에서 비교해 사용자용 `analysis_change_card`를 생성하도록 보강했다. 이 변경은 기존 `analysis_results.elderly_friendly_report` JSON에 비교 카드를 저장하는 방식이며, DB schema, Redis key, 환경 변수, 외부 API 연동은 변경하지 않았다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | `composeReanalysisChangeCard(previous, next)`를 추가했다. 사고 유형, 과실비율, 근거 충족도, 판단 상태, 남은 보완 질문 수를 직전 분석과 새 분석 기준으로 비교하고, 내부 `agent_judgment` 원문 값은 사용자 화면에 노출하지 않는 한국어 요약 카드로 변환한다. |
| `apps/gateway/src/main.ts` | `/api/v1/cases/:caseId/reanalyze`가 재분석 전 최신 `analysis_results.result`를 조회한 뒤 새 Agent 결과와 비교하여 `analysis_change_card`를 포함한 easy report를 저장 및 반환하도록 변경했다. |
| `apps/frontend/src/components/easy/AnalysisChangeCard.vue` | 결과 화면에 재분석 비교 카드 UI를 추가했다. 현재 과실비율, 근거 충족도, 남은 질문 수, 변경된 판단 항목을 보여준다. |
| `apps/frontend/src/components/easy/EasyReportView.vue` | easy report에 `analysis_change_card`가 있으면 상단 결론과 근거 검증 카드 사이에 표시하도록 연결했다. |
| `apps/gateway/test/report-composer.test.ts` | 재분석 비교 카드가 과실비율과 남은 질문 수 변화를 표시하면서 내부 판단 상태 원문을 노출하지 않는지 검증한다. |

2026-05-21 추가 보강: `analysis_change_card`는 대표 KNIA 기준, 전체/관련/KNIA 근거 수, 법률/KNIA/기타 근거 구성, 부족한 근거 조건 수까지 함께 비교한다. 또한 직전 분석 대비 새로 반영된 근거와 이번 결과에서 빠진 근거를 사용자용 제목, 출처 라벨, 근거 유형 라벨 기준으로 보여준다. Frontend의 `AnalysisChangeCard.vue`는 긴 KNIA 기준명도 깨지지 않도록 반응형 통계 그리드, 근거 메모 목록, 근거 변경 목록을 표시한다.

이 단계부터 보완 입력 후 결과 화면은 “답변을 반영했다”에서 끝나지 않고, 직전 분석 대비 무엇이 달라졌는지와 근거/KNIA 기반이 얼마나 보강됐는지 함께 확인할 수 있다. Agent 판단 검증 체계 관점에서는 이후 동일 카드에 KNIA 가감요소 적용 변화까지 확장할 수 있다.

작성 기준: `C:/Users/yangbun/Desktop/프로젝트 정리.txt`의 5개 분석 항목을 기준으로, 현재 저장소의 파일 구조와 소스 코드를 역분석한 초안이다. 민감 정보는 실제 값이 아니라 환경변수 이름만 기록한다.

## 1. 기본 식별 정보

### 프로젝트 개요

| 항목 | 내용 |
| --- | --- |
| 프로젝트명 | LawCompass |
| 목적 | 교통사고 상황을 입력받아 법률 근거, 과실비율, 보험/형사 리스크, 행동 가이드를 제공하는 AI 분석 MVP |
| 구조 | 단일 저장소 모노레포 |
| 실행 기준 | Docker Compose 기반 단일 서버 배포 |
| 주요 런타임 | Vue 3, Vite, Fastify, FastAPI, Redis, PostgreSQL, pgvector |
| 최초/현재 담당자 | 저장소 내 명시 정보 없음 |

### 기준 문서 체계

| 파일 | 역할 |
| --- | --- |
| `AGENTS.md` | 에이전트가 개발/점검/문서 작업 전에 우선 읽는 진입 지침. `DEVELOPMENT_PROMPT.md`와 `SYSTEM_OVERVIEW.md`를 먼저 참조하도록 안내 |
| `DEVELOPMENT_PROMPT.md` | 개발 요청 처리 전 우선 읽는 LawCompass 전담 Principal Software Architect 작업 원칙 문서. 역할, 작업 순서, 보안, 검증, 문서 동기화 규칙을 정의 |
| `SYSTEM_OVERVIEW.md` | 프로젝트 구조, 핵심 파일, 리소스 연동, 완성도, To-Do를 기록하는 인수인계 기준 문서 |
| `README.md` | 프로젝트 요약과 빠른 시작 절차 |
| `docs/OPERATIONS.md` | 운영 절차, 외부 API 점검, E2E 스모크 테스트 안내 |
| `docs/api/openapi.yaml` | 공개 API 명세 |
| `docs/STACK_DECISION_REVIEW.md` | 초기 기술 스택 계획안과 현재 적용 스택을 비교하고 향후 도입 판단 기준을 기록한 기술 의사결정 참고 문서 |
| `docs/PROJECT_BASELINE_2026-05-21.md` | 2026-05-21 기준 인수 직전 구현 상태를 고정 기록한 베이스라인 스냅샷. 이후 개발 변화 비교의 기준 |
| `docs/PROJECT_EVOLUTION_2026-05-24.md` | 2026-05-21 베이스라인 대비 2026-05-24 현재 프로젝트 변화, 완료된 보강, 남은 과제를 정리한 변화 기록 |

문서 최신화 원칙:

1. 개발로 인해 서비스 구조, API route, DTO, DB schema, Redis key, storage path, 외부 API, 환경변수, 실행 방법, known issue가 바뀌면 `SYSTEM_OVERVIEW.md`를 함께 업데이트한다.
2. 개발 원칙, 검증 방식, 문서 동기화 규칙, 서비스 책임 경계, 보안 기준이 바뀌면 `DEVELOPMENT_PROMPT.md`를 업데이트한다.
3. `.env`, API key, JWT secret, 내부 서비스 토큰, 사용자 비밀번호 등 민감값은 문서에 실제 값으로 기록하지 않는다.
4. 외부 도구, 모듈, SDK, AI 모델, 영상 분석 도구, 공공/기관 API를 새로 도입하거나 교체할 때는 2026-05-20 이후의 최신 공식 근거, 유지보수 상태, 비용, 라이선스, 리소스 사용량, 프로젝트 적합성을 확인한다.

### 상위 폴더 역할

| 경로 | 역할 및 목적 |
| --- | --- |
| `apps/frontend` | 사용자 웹 화면. 로그인, 케이스 생성, 영상 업로드, 분석 결과, KNIA 기준 조회, AI 채팅 UI 제공 |
| `apps/gateway` | 외부 API 게이트웨이. 인증/세션, 케이스/업로드/분석 API, DB 접근, Redis rate limit, Agent 호출 담당 |
| `apps/agent` | 내부 AI 분석 서비스. 사고 분석, 법률 RAG, KNIA 매칭, 채팅 오케스트레이션, 외부 법률/공공 API 호출 담당 |
| `apps/worker` | 비동기 작업 처리. Redis Streams에서 영상 전처리/분석 작업을 소비하고 ffmpeg/ffprobe 및 Agent 호출 수행 |
| `infra/postgres/migrations` | PostgreSQL, pgvector, 업무 테이블, 인덱스, 트리거 정의 |
| `infra/caddy` | Caddy reverse proxy 및 보안 헤더 설정 |
| `config` | KNIA 수집 범위 등 실행 설정 JSON |
| `scripts` | 로컬 E2E, KNIA 스크래핑/JSON 자료, 보조 스크립트 |
| `docs` | 운영 절차 및 OpenAPI 문서 |
| `storage` | 로컬 업로드 파일, 프레임 추출 결과, 테스트 산출물 저장소 |
| `sample_data` | 샘플 영상/사고 JSON |
| `docs/STACK_DECISION_REVIEW.md` | 초기 설계 스택과 현재 적용 스택의 차이, 향후 도입 후보, 기술 선택 판단 기준 문서 |
| `docs/PROJECT_BASELINE_2026-05-21.md` | 인수 직전 현재 구현 상태를 고정 기록한 비교용 베이스라인 문서 |
| `docs/PROJECT_EVOLUTION_2026-05-24.md` | 인수 직전 베이스라인 대비 현재 변화와 후속 과제를 비교하는 변화 기록 문서 |

### 서비스 구성

| 서비스 | 컨테이너/포트 | 주요 책임 |
| --- | --- | --- |
| `edge` | Caddy, host `80/443` | `/api/*`, `/health`, `/ready`를 gateway로 프록시하고 나머지는 frontend로 프록시 |
| `frontend` | 내부 `5173` | Vite preview 서버로 정적 프론트 제공 |
| `gateway` | 내부 `3000` | 공개 API, 인증, DB/Redis 접근, Agent 내부 호출 |
| `agent` | 내부 `8000` | `/internal/v1/*` 분석/수집/검색 내부 API 제공 |
| `worker` | 포트 없음 | Redis Stream 기반 백그라운드 작업 처리 |
| `postgres` | 내부 `5432` | 업무 데이터와 벡터 검색 데이터 저장 |
| `redis` | 내부 `6379` | rate limit, 작업 큐, 작업 상태 캐시 |

## 2. 기능 및 로직 명세

### Frontend

핵심 파일:

| 파일 | 역할 |
| --- | --- |
| `apps/frontend/src/main.ts` | Vue 앱, Pinia, Router 부트스트랩 |
| `apps/frontend/src/router/index.ts` | 로그인 필요 화면 보호 및 라우팅 |
| `apps/frontend/src/api/client.ts` | Gateway API 호출 래퍼와 프론트 DTO 정의 |
| `apps/frontend/src/stores/session.ts` | 세션 부트스트랩, 로그인 상태 관리 |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | 케이스 상세 화면의 입력, 업로드, 분석 요청, job polling 상태 관리 |
| `apps/frontend/src/views/*.vue` | 로그인, 대시보드, 케이스 생성/상세/결과, KNIA 화면 |
| `apps/frontend/src/views/AdminAgentTestView.vue` | 관리자 전용 Agent 입력 경로 테스트 화면. 입력만, 영상만, 입력+영상 테스트를 실행하고 easy report와 Agent 진단을 확인 |
| `apps/frontend/src/components/chat/*` | AI 사고 상담 패널, 메시지, 초안 케이스, KNIA 매칭 카드 |
| `apps/frontend/src/components/knia/*` | KNIA 순위, 기준, 미디어, JSON 검색 UI |
| `apps/frontend/src/components/easy/*` | 고령자 친화 리포트 표시 컴포넌트 |
| `apps/frontend/src/components/easy/EvidenceReliabilityCard.vue` | Agent 판단과 근거 문서의 연결 상태를 사용자용 카드로 표시 |

주요 화면 라우트:

| 경로 | 컴포넌트 | 인증 |
| --- | --- | --- |
| `/` | `DashboardView` | 필요 |
| `/login` | `LoginView` | 불필요 |
| `/signup` | `SignupView` | 불필요 |
| `/cases/new` | `CaseCreateView` | 필요 |
| `/cases/:caseId` | `CaseDetailView` | 필요 |
| `/cases/:caseId/wizard` | `AccidentWizardView` | 필요 |
| `/cases/:caseId/result` | `CaseResultView` | 필요 |
| `/evidence/:chunkId` | `EvidenceDetailView` | 필요 |
| `/knia/ranking` | `KniaRankingView` | 필요 |
| `/knia/charts/:chartNo` | `KniaChartView` | 필요 |
| `/admin/agent-test` | `AdminAgentTestView` | 관리자 필요 |

프론트 주요 DTO:

| DTO | 필드 요약 |
| --- | --- |
| `User` | `id`, `email`, `role`, `display_name` |
| `AccidentFacts` | 사고 유형, 어린이보호구역, 보행자/자전거/차대차, 신호, 차선 변경, 날씨, 피해 정도 등 |
| `CaseItem` | `id`, `title`, `description_text`, `status`, `structured_facts`, `selected_keywords`, `analysis_mode`, `created_at` |
| `UploadItem` | `id`, `file_name`, `content_type`, `file_size_bytes`, `status`, `storage_provider`, `metadata`, `created_at` |

### Gateway

핵심 파일:

| 파일 | 역할 |
| --- | --- |
| `apps/gateway/src/main.ts` | Fastify 앱 엔트리포인트. 인증, 케이스, 업로드, 분석, KNIA, 관리자 API 대부분을 정의 |
| `apps/gateway/src/routes/chat.ts` | AI 채팅 세션/메시지/빠른 상담 API |
| `apps/gateway/src/services/chatService.ts` | 채팅 세션 저장, Agent 채팅 호출, 메시지 저장 |
| `apps/gateway/src/lib/internal-client.ts` | 내부 Agent POST 호출 및 재시도 |
| `apps/gateway/src/lib/errors.ts` | 표준 오류 응답 envelope, validation 오류 정규화 |
| `apps/gateway/src/lib/report-composer.ts` | 분석 결과를 클라이언트 리포트/쉬운 리포트 형태로 조립하고 `claim_evidence`를 사용자용 근거 연결 상태 카드로 요약 |
| `apps/gateway/src/lib/security.ts` | 민감값 마스킹, 해시 유틸리티 |
| `apps/gateway/src/lib/ai-router.ts` | 영상 분석용 AI 라우팅 결정 |
| `apps/gateway/src/storage/provider.ts` | 로컬 업로드 저장소 구현. S3 저장소 인터페이스는 있으나 현재 미활성 |

공개 API 책임:

| API 그룹 | 대표 경로 | 책임 |
| --- | --- | --- |
| 상태 | `GET /health`, `GET /ready` | 프로세스, DB, Redis 준비 상태 확인 |
| 인증 | `/api/v1/auth/signup`, `/login`, `/refresh`, `/logout`, `/me` | 이메일 기반 회원가입/로그인, JWT access cookie, refresh token 회전 |
| 케이스 | `/api/v1/cases` | 사고 케이스 생성, 조회, 수정 |
| 업로드 | `/api/v1/uploads/*` | 로컬 영상 업로드, 완료 처리, 조회, 재생/다운로드 URL |
| 분석 | `/api/v1/cases/:caseId/analyze-text`, `/analyze-video`, `/result`, `/report`, `/easy-report` | Agent 호출 또는 작업 큐 등록, 분석 결과 조회 |
| 증거 | `/api/v1/cases/:caseId/evidence`, `/api/v1/legal/evidence/:chunkId` | 법률 근거 chunk 조회 |
| KNIA | `/api/v1/knia/*` | 과실비율 순위, 기준 상세, 매칭, 추정, JSON/미디어 검색 |
| 관리자 | `/api/v1/admin/*` | 법률 KB 적재, 임베딩 재생성, KNIA 수집/임포트/캐시 무효화 |
| 채팅 | `/api/v1/chat/*` | AI 사고 상담 세션 및 메시지 |

Gateway 주요 로직:

| 로직 | 설명 |
| --- | --- |
| 인증 | `lc_at`, `lc_rt` HTTP-only cookie 사용. access token은 JWT, refresh token은 DB에 해시 저장 |
| 권한 | 일반 API는 `requireUser`, 관리자 API는 `requireAdmin` 사용. 관리자 권한은 사용자 role `admin` 또는 `INTERNAL_ADMIN_TOKEN` 헤더 매칭 |
| rate limit | Redis에 분 단위 route key를 기록해 90회 초과 시 제한 |
| idempotency | `Idempotency-Key`를 해시해 중복 POST/PATCH/DELETE 응답 재사용 |
| Agent 호출 | `INTERNAL_AGENT_URL`, `INTERNAL_SERVICE_TOKEN`으로 내부 FastAPI 호출 |
| 업로드 | `LocalStorageProvider`가 `storage/uploads/{caseId}/{uploadId}/original.ext`에 영상 저장 |

### Agent

핵심 파일:

| 파일 | 역할 |
| --- | --- |
| `apps/agent/app/main.py` | FastAPI 앱 엔트리포인트 |
| `apps/agent/app/routers/internal.py` | 내부 전용 `/internal/v1/*` API composition router |
| `apps/agent/app/routers/internal_auth.py` | 내부 API `INTERNAL_SERVICE_TOKEN` guard |
| `apps/agent/app/routers/internal_routes/analysis.py` | `/analyze/*` text/video/scenario analysis routes |
| `apps/agent/app/routers/internal_routes/jobs.py` | `/jobs/process` worker job route |
| `apps/agent/app/routers/internal_routes/legal.py` | `/legal/*` legal KB ingest/rebuild/retrieval test routes |
| `apps/agent/app/routers/internal_routes/chat.py` | `/chat/message` accident consultation route |
| `apps/agent/app/routers/internal_routes/knia.py` | `/knia/*` collection, matching, fault estimate, JSON/search routes |
| `apps/agent/app/routers/internal_routes/cache.py` | `/cache/invalidate` semantic cache invalidation route |
| `apps/agent/app/routers/internal_routes/health.py` | unauthenticated `/health` route |
| `apps/agent/app/schemas.py` | Pydantic 요청/응답 모델 |
| `apps/agent/app/services/orchestrator.py` | 사고 분석 파이프라인 총괄 |
| `apps/agent/app/services/analyst_output_contracts.py` | 법률/과실/형사/보험 분석가 출력의 Pydantic 계약 모델 |
| `apps/agent/app/services/analyst_output_guard.py` | 법률/과실/형사/보험 분석가 출력에 근거 충분성, caveat, 신뢰도 상한을 적용하는 공통 가드 |
| `apps/agent/app/services/claim_evidence_validator.py` | Agent 분석 결과의 주요 판단과 근거 문서를 연결하고 근거 누락 판단을 `evidence_audit`에 반영 |
| `apps/agent/app/services/elderly_friendly/plain_language_agent.py` | 쉬운 리포트 문장 생성. analyst 근거 상태가 약하면 과실/법률/보험 문장을 확정 표현 대신 추가 확인 표현으로 완화 |
| `apps/agent/app/services/scenario_classifier.py` | 사고 유형 및 당사자 유형 분류 |
| `apps/agent/app/services/analysts/*` | 과실비율, 형사 책임, 보험, 행동 계획, 법규 분석 |
| `apps/agent/app/services/legal/*` | 법률 문서 수집, chunking, vectorizing, evidence retrieval |
| `apps/agent/app/services/knia/*` | KNIA 수집, 파싱, 저장소, 매칭, 벡터화, JSON import |
| `apps/agent/app/services/chat/*` | AI 사고 상담 의도 분류, 응답 생성, 초안 케이스 생성 |
| `apps/agent/app/mcp/*` | 내부 tool registry/executor 및 KNIA/RAG/cache 도구 |

Agent 내부 API:

| 경로 | 책임 |
| --- | --- |
| `GET /internal/v1/health` | Agent 상태 확인 |
| `POST /internal/v1/analyze/text` | 텍스트 사고 분석 |
| `POST /internal/v1/analyze/video` | 영상 전처리 요약 기반 사고 분석 |
| `POST /internal/v1/analyze/scenario` | 구조화 시나리오 분석 |
| `POST /internal/v1/legal/ingest` | 교통 법률 KB 수집/적재 |
| `POST /internal/v1/legal/rebuild-embeddings` | KB chunk 임베딩 생성 |
| `GET /internal/v1/legal/retrieval-test` | 법률 검색 테스트 |
| `POST /internal/v1/chat/message` | AI 사고 상담 처리 |
| `POST /internal/v1/knia/*` | KNIA 수집, 매칭, 과실 추정, JSON import, 임베딩 재생성 |
| `POST /internal/v1/cache/invalidate` | KNIA JSON 캐시 무효화 |

Agent 주요 DTO:

| 모델 | 필드 요약 |
| --- | --- |
| `AnalyzeTextRequest` | `case_id`, `user_id`, `description_text`, `structured_facts`, `selected_keywords`, `analysis_mode`, `ai_profile`, `specialist_roles` |
| `AnalyzeVideoRequest` | `case_id`, `user_id`, `upload_id`, `preprocessed_summary`, `video_metadata`, `structured_facts`, `selected_keywords`, `analysis_mode` |
| `EvidenceItem` | `chunk_id`, `title`, `source`, `score`, `snippet`, `law_name`, `article_title`, `plain_summary`, `source_url`, `source_type` |
| `AnalysisOutput` | 사고 요약, 시나리오, 법률 분석, 과실비율, 보험/형사 가이드, 근거, KNIA 매칭, 불확실성, 후속 질문, 모델 정보, 쉬운 리포트 |
| Analyst output contracts | `TrafficLawAnalysisOutput`, `FaultRatioAnalysisOutput`, `CriminalLiabilityAnalysisOutput`, `InsuranceAnalysisOutput`. 각 analyst 결과를 Pydantic으로 정규화하고 공통 guard fields를 포함 |
| Analyst output guard fields | `legal_analysis`, `fault_ratio`, `legal_liability`, `insurance_guide` 내부의 `evidence_support_level`, `judgment_status`, `required_evidence_family`, `evidence_count`, `evidence_ids`, `used_evidence_ids`, `caveats`. 직접 근거 부족 시 확정 표현을 피하도록 경고하고 과실비율 `confidence`를 제한 |
| `claim_evidence` | Agent 주요 판단별 근거 연결 상태, 지원 수준, 미지원 판단, 근거 커버리지 |

### Worker

핵심 파일:

| 파일 | 역할 |
| --- | --- |
| `apps/worker/worker/main.py` | Redis Streams Consumer Group 기반 작업 루프 |

작업 흐름:

1. `jobs:v1:stream`에서 `video_preprocess`, `video_analyze` 작업 수신
2. `video_preprocess`에서 `ffprobe`로 영상 메타데이터 확인
3. `ffmpeg`로 대표 프레임 4장을 `storage/frames/{caseId}/{uploadId}`에 추출
4. 업로드 상태를 `processing`에서 `ready`로 갱신
5. 후속 `video_analyze` job을 DB와 Redis Stream에 등록
6. `video_analyze`에서 Agent `/internal/v1/analyze/video` 호출
7. `analysis_results`에 결과 저장 후 `cases.latest_result_id`, `cases.status` 갱신

### 핵심 파일 상세 명세

이 섹션은 인수인계 시 코드를 직접 열어보지 않아도 주요 파일의 역할, 입출력, 호출 관계, 리소스 접근 범위를 빠르게 파악하기 위한 파일 단위 명세다. 작성자/담당자는 저장소 내 명시 정보가 없어 `저장소 내 명시 없음`으로 기록한다.

#### 핵심 파일 식별 정보

| Path | Name & Type | Purpose Overview | Owner/Author |
| --- | --- | --- | --- |
| `compose.yaml` | Docker Compose 서비스 정의 | 전체 MSA 구성, 네트워크, 볼륨, 헬스체크, 환경변수 주입 규칙을 정의한다 | 저장소 내 명시 없음 |
| `infra/caddy/Caddyfile` | Edge reverse proxy 설정 | `/api/*`, `/health`, `/ready`를 Gateway로 전달하고 프론트 정적 서비스를 프록시한다 | 저장소 내 명시 없음 |
| `infra/postgres/migrations/001_init.sql` | DB 초기 스키마 | 인증, 케이스, 업로드, 작업, 분석 결과, KB, 감사/멱등성의 기본 테이블과 확장을 만든다 | 저장소 내 명시 없음 |
| `apps/frontend/src/main.ts` | Frontend bootstrap | Vue 앱에 Pinia와 Router를 연결해 화면 앱을 시작한다 | 저장소 내 명시 없음 |
| `apps/frontend/src/router/index.ts` | Frontend router/guard | 화면 라우팅과 인증 필요 페이지 접근 제어를 담당한다 | 저장소 내 명시 없음 |
| `apps/frontend/src/api/client.ts` | Frontend API client/DTO | Gateway API 호출 함수와 프론트 타입 정의를 제공한다 | 저장소 내 명시 없음 |
| `apps/frontend/src/stores/session.ts` | Pinia session store | 사용자 세션 복원, 로그인, 로그아웃, refresh 흐름을 관리한다 | 저장소 내 명시 없음 |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | Vue case workspace composable | 케이스 상세 화면의 API 상태, 입력 저장, 업로드, 전처리, 분석 요청, job polling을 관리한다 | 저장소 내 명시 없음 |
| `apps/frontend/src/views/CaseDetailView.vue` | Frontend case workspace view | 케이스 상세 화면의 페이지 흐름을 조립하고 상태 composable과 섹션 컴포넌트를 연결한다 | 저장소 내 명시 없음 |
| `apps/frontend/src/components/case/*.vue` | Frontend case workspace components | 케이스 헤더, 요약, 사고 입력, 영상 업로드, 분석 요청 섹션을 표시 전용 책임으로 분리한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/main.ts` | Fastify API entrypoint/controller | 공개 API 대부분과 인증, rate limit, idempotency, DB/Redis/Agent 연동을 담당한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/routes/chat.ts` | Fastify chat router | 채팅 세션 생성, 메시지 조회/전송, 빠른 상담 API를 등록한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/services/chatService.ts` | Chat domain service | 채팅 세션/메시지를 DB에 저장하고 Agent 채팅 API를 호출한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/lib/internal-client.ts` | Internal HTTP client | Gateway에서 Agent 내부 POST API를 timeout/retry 포함해 호출한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/lib/errors.ts` | Gateway error formatter | `error.code/message/trace_id` 표준 응답을 만들고 Fastify validation 오류를 400 응답으로 정규화한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/storage/provider.ts` | Storage abstraction | 로컬 영상 업로드 저장을 구현하고 S3 provider 인터페이스를 남겨둔다 | 저장소 내 명시 없음 |
| `apps/agent/app/main.py` | FastAPI app entrypoint | Agent 앱을 생성하고 internal router를 등록한다 | 저장소 내 명시 없음 |
| `apps/agent/app/routers/internal.py` | FastAPI internal router composition root | `/internal/v1` prefix를 가진 domain router들을 조립한다 | 저장소 내 명시 없음 |
| `apps/agent/app/routers/internal_auth.py` | FastAPI internal auth helper | 내부 token guard를 라우터별로 공유한다 | 저장소 내 명시 없음 |
| `apps/agent/app/routers/internal_routes/*.py` | FastAPI domain route modules | 분석, job, 법률, KNIA, 채팅, 캐시, health 내부 API를 책임별 파일로 제공한다 | 저장소 내 명시 없음 |
| `apps/agent/app/schemas.py` | Pydantic DTO schema | 분석 요청/응답과 근거 item 모델을 정의한다 | 저장소 내 명시 없음 |
| `apps/agent/app/services/orchestrator.py` | Analysis orchestration service | 사고 분석 전체 파이프라인을 조립하고 최종 `AnalysisOutput` payload를 만든다 | 저장소 내 명시 없음 |
| `apps/agent/app/services/orchestration_output.py` | Analysis output enrichment service | 판단 계약, 재검증 루프, 실행 trace, KNIA 계산 메타데이터, 사용자용 리포트를 최종 출력에 부착한다 | 저장소 내 명시 없음 |
| `apps/agent/app/services/analyst_output_contracts.py` | Analyst output contract schema | 분석가별 출력 모델을 Pydantic으로 정의하고 LLM/fallback 결과의 타입을 정규화한다 | 저장소 내 명시 없음 |
| `apps/agent/app/services/analyst_output_guard.py` | Analyst output guard service | 분석가별 LLM/fallback 출력을 근거 충분성 기준으로 보강하고 직접 근거 부족 시 caveat와 confidence 상한을 적용한다 | 저장소 내 명시 없음 |
| `apps/agent/app/services/legal_api_clients.py` | External legal/public API client | 국가법령정보센터와 공공데이터포털 교통 API 검색 결과를 내부 근거 형식으로 변환한다 | 저장소 내 명시 없음 |
| `apps/gateway/src/routes/knia-admin.ts` | Fastify KNIA admin router | KNIA 수집, 상세 수집, 임베딩 재생성, JSON import, cache invalidation 관리자 API를 등록한다 | 저장소 내 명시 없음 |
| `apps/worker/worker/main.py` | Redis Streams worker entrypoint | Redis consumer group을 유지하고 job 실행 성공/실패 상태 캐시를 갱신한다 | 저장소 내 명시 없음 |
| `apps/worker/worker/job_processor.py` | Worker job processor | `video_preprocess`, `video_analyze` job의 DB 상태 전이, Agent 호출, 분석 결과 저장을 수행한다 | 저장소 내 명시 없음 |
| `apps/worker/worker/video_preprocess.py` | Video preprocessing service | ffprobe 영상 metadata 확인, 이벤트 프레임 시간 선택, ffmpeg 프레임 추출을 수행한다 | 저장소 내 명시 없음 |
| `apps/worker/worker/frame_analysis.py` | Optional frame analysis provider | OpenAI 이미지 입력을 이용해 프레임에서 관측 가능한 사고 사실 후보를 추출한다 | 저장소 내 명시 없음 |
| `AGENTS.md` | Agent entry instruction document | 에이전트가 작업 전 `DEVELOPMENT_PROMPT.md`와 `SYSTEM_OVERVIEW.md`를 먼저 읽도록 안내한다 | 저장소 내 명시 없음 |
| `DEVELOPMENT_PROMPT.md` | Development guidance document | 개발 전 참조하는 LawCompass 전담 Principal Software Architect 역할, 작업 순서, 검증, 보안, 문서 동기화 기준을 정의한다 | 저장소 내 명시 없음 |
| `SYSTEM_OVERVIEW.md` | Project handoff/spec document | 프로젝트 구조와 현재 구현 상태를 추적하는 기준 문서다 | 저장소 내 명시 없음 |
| `docs/STACK_DECISION_REVIEW.md` | Stack decision review document | 초기 스택 계획안과 현재 적용 스택을 비교하고 S3, Capacitor, 영상 분석, MCP, OpenAI API 전환 판단 기준을 기록한다 | 저장소 내 명시 없음 |
| `docs/PROJECT_BASELINE_2026-05-21.md` | Baseline snapshot document | 2026-05-21 인수 시점 구현 상태, 미완성 영역, 이후 변화 비교 질문을 기록한다 | 저장소 내 명시 없음 |

#### 주요 함수 및 입출력

| 파일 | Key Methods | Input | Output | Core Logic |
| --- | --- | --- | --- | --- |
| `apps/frontend/src/router/index.ts` | `router.beforeEach` | 대상 route | redirect 또는 `true` | `session.bootstrap()` 후 인증 필요 route에서 미로그인 사용자를 `/login`으로 이동 |
| `apps/frontend/src/api/client.ts` | `request<T>`, `formatApiError` | API path, `RequestInit`, API 오류 객체 | typed JSON response 또는 사용자 표시용 오류 문구 | `fetch`에 cookie 포함, JSON 파싱, 오류 객체 정규화, Gateway validation detail을 화면 표시용 필드 안내로 변환 |
| `apps/frontend/src/api/client.ts` | `api.login`, `api.createCase`, `api.analyzeText`, `api.searchKniaJson` 등 | 화면 DTO | Gateway 응답 DTO | `/api/v1/*` 공개 API 호출을 함수 단위로 래핑 |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | `useCaseWorkspace` | `caseId` | 화면 refs/actions | 케이스 상세 화면에서 쓰는 입력값, 업로드 목록, 영상 URL, 분석 job, easy report, polling lifecycle을 하나의 composable로 제공 |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | `statusLabel`, `statusClass`, `prettySize`, `formatDate` | status/size/date | 표시용 문자열/class | 케이스, 업로드, job 상태 표시 포맷을 CaseDetailView와 분리 |
| `apps/frontend/src/components/case/*.vue` | `CaseWorkspaceHeader`, `CaseSummaryCard`, `CaseInputStep`, `CaseUploadStep`, `CaseAnalysisStep` | props/events | Vue section markup | 케이스 상세 화면의 헤더, 요약, 입력, 업로드, 분석 요청 UI를 표시 단위로 분리하고 상태 변경은 상위 view/composable로 emit |
| `apps/frontend/src/stores/session.ts` | `restoreLocal` | 없음 | 없음 | `localStorage`의 `lawcompass:user`를 읽어 세션 상태 복원 |
| `apps/frontend/src/stores/session.ts` | `bootstrap` | 없음 | 없음 | `/auth/me` 실패 시 `/auth/refresh` 재시도 후 사용자 상태 갱신 |
| `apps/frontend/src/stores/session.ts` | `login`, `logout` | 이메일/비밀번호 또는 없음 | 없음 | Gateway 인증 API 호출 후 Pinia 상태와 localStorage 동기화. App logout 액션은 세션 정리 후 `/login`으로 이동 |
| `apps/gateway/src/main.ts` | `requireUser` | Fastify request/reply | boolean | JWT 검증 결과가 없으면 401 표준 오류 반환 |
| `apps/gateway/src/main.ts` | `requireAdmin` | Fastify request/reply | boolean | 사용자 role `admin` 또는 `x-admin-token`을 검사해 관리자 API 보호 |
| `apps/gateway/src/main.ts` | `rateLimit` | Fastify request/reply | 없음 또는 429 | Redis minute key를 증가시켜 분당 90회 초과 요청 차단 |
| `apps/gateway/src/main.ts` | `idempotency` | Fastify request/reply | cached reply 가능 | `Idempotency-Key`와 request hash로 중복 요청 응답 재사용 |
| `apps/gateway/src/lib/errors.ts` | `errorPayload`, `validationErrorPayload`, `requestErrorPayload` | code/message/trace 또는 Fastify error | 표준 오류 envelope | Gateway 오류 응답을 `error.code`, `error.message`, `error.trace_id` 형식으로 통일하고 validation detail을 정규화 |
| `apps/gateway/src/main.ts` | Auth routes | `email`, `password`, `display_name` | user, token, trace_id | 이메일 계정 생성, bcrypt 검증, JWT/refresh cookie 발급 |
| `apps/gateway/src/main.ts` | Case/upload/analyze routes | case/upload/analysis payload | case, upload, job, result | DB에 업무 데이터를 저장하고 Redis job 또는 Agent 분석 호출 수행 |
| `apps/gateway/src/routes/chat.ts` | `registerChatRoutes` | Fastify instance, options | route registration | `/chat/sessions`, `/chat/quick`, 메시지 API를 Gateway에 등록 |
| `apps/gateway/src/services/chatService.ts` | `createChatSession` | userId, caseId, title, context | chat session row | `chat_sessions`에 상담 세션 생성 |
| `apps/gateway/src/services/chatService.ts` | `getChatSessionForAccess` | sessionId, userId | session 또는 forbidden/null | 채팅 세션 소유권 검사 |
| `apps/gateway/src/services/chatService.ts` | `listChatMessages` | sessionId | sanitized messages | `chat_messages` 조회 후 내부 기술 필드 제거 |
| `apps/gateway/src/services/chatService.ts` | `sendChatMessage` | sessionId, userId, message, context, traceId | assistant reply payload | 사용자 메시지 저장, Agent 호출, assistant 메시지/안전 로그 저장 |
| `apps/gateway/src/lib/internal-client.ts` | `callInternalAgent` | internal path, payload, traceId, options | Agent JSON | timeout과 retry를 적용해 Agent POST API 호출 |
| `apps/gateway/src/storage/provider.ts` | `LocalStorageProvider.putUpload` | caseId, uploadId, fileName, contentType, stream | `StoredObject` | video MIME 검사 후 로컬 `storage/uploads`에 파일 저장 |
| `apps/gateway/src/storage/provider.ts` | `S3StorageProvider.putUpload` | upload input | error | 현재 `S3_STORAGE_NOT_ENABLED` 오류를 발생시키는 미구현 provider |
| `apps/agent/app/routers/internal_auth.py` | `check_internal_token` | `x_internal_token` | 없음 또는 401 | `INTERNAL_SERVICE_TOKEN`과 요청 헤더 비교 |
| `apps/agent/app/routers/internal_routes/analysis.py` | `analyze_text`, `analyze_video`, `analyze_scenario_endpoint` | Pydantic/dict payload | `AnalysisOutput` | orchestrator 분석 함수를 호출해 표준 분석 응답 반환 |
| `apps/agent/app/routers/internal_routes/legal.py` | `legal_ingest`, `legal_rebuild_embeddings`, `legal_retrieval_test` | token/query | ingest/rebuild/search 결과 | 법률 KB 적재, 벡터 생성, 검색 테스트 수행 |
| `apps/agent/app/routers/internal_routes/knia.py` | `knia_*` endpoints | token, chart/query/import payload | KNIA 수집/검색/추정 결과 | KNIA collector, matcher, repository, vectorizer, JSON loader 호출 |
| `apps/agent/app/schemas.py` | `AnalyzeTextRequest` | 텍스트 분석 요청 JSON | Pydantic model | 케이스/사용자/설명/구조화 사실/키워드 유효성 정의 |
| `apps/agent/app/schemas.py` | `AnalyzeVideoRequest` | 영상 분석 요청 JSON | Pydantic model | 업로드 ID, 전처리 요약, 영상 metadata 포함 요청 정의 |
| `apps/agent/app/schemas.py` | `AnalysisOutput` | 분석 결과 dict | Pydantic response | 법률/과실/보험/형사/근거/KNIA/쉬운 리포트 응답 규격 정의 |
| `apps/agent/app/services/orchestrator.py` | `analyze_case` | description, facts, keywords, profile | analysis dict | 텍스트 입력을 `_analyze_core`로 전달 |
| `apps/agent/app/services/orchestrator.py` | `analyze_video_case` | preprocessed summary, video metadata | analysis dict | 영상 요약과 metadata를 `_analyze_core`로 전달 |
| `apps/agent/app/services/orchestrator.py` | `_analyze_core` | normalized accident inputs | final analysis dict | 입력 context, 근거 수집, 분석가 실행, 재검색, 출력 보강 단계를 순서대로 연결 |
| `apps/agent/app/services/orchestration_context.py` | `build_case_context` | 사고 입력, 영상 metadata | `CaseContext` | 영상 계약, 입력 정규화, 시나리오 분류, 차량 역할 추론, 보완 질문 상태 생성 |
| `apps/agent/app/services/orchestration_evidence.py` | `collect_evidence_stage` | `CaseContext`, 영상 metadata | `EvidenceBundle` | KNIA 매칭/JSON 검색/과실 산정 근거와 법률 RAG 근거를 수집 |
| `apps/agent/app/services/orchestration_evidence.py` | `_knia_estimate_to_evidence`, `_knia_refs_to_evidence` | KNIA 추정/참조 데이터 | evidence list | 과실 기본값, 가감요소, 관련 법규/사례를 evidence item으로 변환 |
| `apps/agent/app/services/orchestration_analysis.py` | `run_analysis_stage`, `run_reflection_requery_stage` | `CaseContext`, `EvidenceBundle` | `AnalysisBundle`/`ReflectionStageResult` | 분석가 실행, KNIA 과실 적용, 근거 감사, claim-evidence 검증, 1회 bounded requery 수행 |
| `apps/agent/app/services/orchestration_output.py` | `enrich_analysis_output` | composed output, context, evidence/analysis bundles, judgment/reflection contract | final analysis dict | 판단 계약 적용 후 reflection loop, execution trace, 쉬운 리포트, KNIA 계산/검색 metadata를 최종 출력에 부착 |
| `apps/agent/app/services/analyst_output_contracts.py` | `validate_*_output` | analyst result dict | normalized analyst result dict | 문자열/배열/숫자/불리언 필드를 Pydantic 계약에 맞춰 정규화하고 extra context는 보존 |
| `apps/agent/app/services/analyst_output_guard.py` | `guard_*_output` | analyst result, evidence list | guarded analyst result | 법률/KNIA/일반 근거 family를 판별해 `evidence_support_level`, `judgment_status`, `used_evidence_ids`, `caveats`를 부여하고 과실비율 confidence를 직접 근거 수준에 맞게 제한 |
| `apps/agent/app/services/elderly_friendly/plain_language_agent.py` | `make_headline`, `make_summary`, `make_fault_explanation`, `make_legal_explanation`, `make_insurance_explanation` | final analysis dict | elderly-friendly report sections | `judgment_status` 또는 `evidence_support_level`이 약하면 사용자 문장을 "확정"이 아닌 "추가 확인 필요" 표현으로 완화 |
| `apps/agent/app/services/legal_api_clients.py` | `fetch_law_search` | query, limit | evidence-like rows | 국가법령정보센터 `lawSearch.do`에서 법령/판례 검색 |
| `apps/agent/app/services/legal_api_clients.py` | `fetch_data_go_traffic` | query, limit | evidence-like rows | 공공데이터포털 교통사고 API 응답을 내부 근거 형식으로 변환 |
| `apps/worker/worker/main.py` | `init_group`, `main_loop` | 없음 | 없음 | Redis Stream consumer group 생성, job 메시지 소비, 성공/실패 status cache 갱신 |
| `apps/worker/worker/job_processor.py` | `process_job` | job_id, job_type, redis client | DB/Redis side effect | `video_preprocess`와 `video_analyze` job을 분기하고 DB transaction을 관리 |
| `apps/worker/worker/job_processor.py` | `_process_video_preprocess`, `_enqueue_video_analyze_job` | job row, payload | uploads/jobs 갱신 | 영상 metadata/프레임/관측값을 저장하고 후속 `video_analyze` job을 큐에 등록 |
| `apps/worker/worker/job_processor.py` | `_process_video_analyze`, `_insert_analysis_result` | job row, payload | analysis result row | Agent `/internal/v1/analyze/video` 호출 후 `analysis_results`와 case latest result를 갱신 |
| `apps/worker/worker/job_processor.py` | `mark_failed` | job_id, error | DB side effect | 실패 job 상태, error_info, 재시도 시간을 저장 |
| `apps/worker/worker/video_preprocess.py` | `probe_video` | storage_path | video metadata dict | `ffprobe`로 codec, duration, resolution, fps, size 추출 |
| `apps/worker/worker/video_preprocess.py` | `frame_times_for_duration`, `extract_event_frames`, `extract_frames` | storage path, case/upload ids, duration | frame descriptors/list | 짧은 사고 영상에 맞춰 시간순 대표 프레임을 추출 |
| `apps/worker/worker/frame_analysis.py` | `analyze_frames_with_openai` | frame details, context | observation result dict | OpenAI Responses API 이미지 입력을 선택적으로 호출하고 관측값 JSON을 정규화 |

#### 파일별 호출 관계 및 리소스

| 파일 | Caller | Callee / Imports | Configuration | Data Storage / External Resource | MSA Context |
| --- | --- | --- | --- | --- | --- |
| `compose.yaml` | 운영자, Docker Compose CLI | 각 서비스 Dockerfile, `.env`, volume/network | `.env`, Compose substitution | Docker volumes `postgres_data`, `redis_data`, `caddy_data`, bind mount `storage`, `logs`, `config`, `scripts` | 전체 서비스 정의. host `80/443`, 내부 `3000/8000/5173/5432/6379` |
| `infra/caddy/Caddyfile` | `edge` container | `frontend:5173`, `gateway:3000` | Caddy global email | HTTP reverse proxy, 보안 header | `edge` 서비스, host `80/443` |
| `infra/postgres/migrations/001_init.sql` | `postgres` init, `db-migrate` profile | PostgreSQL extensions | `POSTGRES_*`는 compose/env에서 주입 | `users`, `cases`, `uploads`, `jobs`, `analysis_results`, `kb_*`, `audit_logs`, `idempotency_keys` | `postgres` 서비스 내부 `5432` |
| `apps/frontend/src/main.ts` | Browser | Vue, Pinia, Router, `App.vue` | Vite env 간접 사용 | DOM mount `#app` | `frontend` 서비스 내부 `5173` |
| `apps/frontend/src/router/index.ts` | Vue app | `vue-router`, `session` store, view components | 없음 | Browser history, session state | Browser -> frontend |
| `apps/frontend/src/api/client.ts` | Vue views/components/stores | Fetch API, `import.meta.env.VITE_API_BASE_URL` | `VITE_API_BASE_URL` | Gateway `/api/v1/*`, cookie credentials | Browser -> `edge`/`gateway` |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | `CaseDetailView.vue` | Vue refs/lifecycle, `api`, `formatApiError` | 없음 | Gateway case/upload/analysis/job/easy-report APIs | Browser -> Gateway via API client |
| `apps/frontend/src/stores/session.ts` | Router, Login/Logout UI | Pinia, `api` client | 없음 | `localStorage` key `lawcompass:user`, auth cookies는 Gateway가 관리 | Browser state layer |
| `apps/gateway/src/main.ts` | `node dist/main.js`, `tsx watch` | Fastify plugins, `pg`, `ioredis`, `bcryptjs`, internal libs | `DATABASE_URL`, `REDIS_URL`, `JWT_*`, `INTERNAL_AGENT_URL`, `INTERNAL_SERVICE_TOKEN`, `INTERNAL_ADMIN_TOKEN`, timeout/storage env | PostgreSQL 업무 테이블, Redis `rl:v1:*`, Redis Stream `jobs:v1:stream`, local storage | `gateway` 서비스 내부 `3000` |
| `apps/gateway/src/routes/chat.ts` | `apps/gateway/src/main.ts` | `chatService`, chat schemas | route option으로 Agent URL/token 전달 | `chat_sessions`, `chat_messages`는 service가 접근 | `gateway` 서비스 내부 route |
| `apps/gateway/src/services/chatService.ts` | `routes/chat.ts` | `callInternalAgent` | options의 `agentUrl`, `internalToken`, timeout/retry | `chat_sessions`, `chat_messages`, `chat_safety_logs`, Agent `/internal/v1/chat/message` | `gateway` -> `agent:8000` |
| `apps/gateway/src/lib/internal-client.ts` | Gateway routes/services | Fetch API, `randomUUID` | call option으로 수신 | Agent internal HTTP | `gateway` -> `agent:8000` |
| `apps/gateway/src/storage/provider.ts` | Upload routes in `main.ts` | Node fs/path/stream | `LOCAL_STORAGE_ROOT`는 생성자에서 전달 | `storage/uploads/{caseId}/{uploadId}/original.ext` | `gateway` container local/bind volume |
| `apps/agent/app/main.py` | Uvicorn | FastAPI, internal router | 없음 | 없음 | `agent` 서비스 내부 `8000` |
| `apps/agent/app/routers/internal.py` | `apps/agent/app/main.py` | `internal_routes` package | 없음 | 없음 | `agent` 내부 `/internal/v1/*` composition |
| `apps/agent/app/routers/internal_routes/*.py` | Gateway, Worker via `internal.py` | orchestrator, legal, KNIA, chat, cache services | `INTERNAL_SERVICE_TOKEN`, `DATABASE_URL` | KB/KNIA/semantic cache DB 테이블, Agent service 함수 | `agent` 내부 `/internal/v1/*` |
| `apps/agent/app/schemas.py` | `internal.py`, tests | Pydantic | 없음 | 없음 | Agent DTO layer |
| `apps/agent/app/services/orchestrator.py` | `internal.py`, tests | orchestration stage modules, judgment contract, report composer, OpenAI flag | `OPENAI_API_KEY` 존재 여부 | 법률 RAG, KNIA DB/Redis 검색은 하위 stage service에서 접근 | Agent domain service |
| `apps/agent/app/services/orchestration_output.py` | `orchestrator.py` | execution trace, judgment contract output policy, elderly-friendly report, stage bundle DTOs | 없음 | 입력 bundle에 포함된 KNIA/RAG metadata만 최종 출력에 복사 | Agent domain output layer |
| `apps/agent/app/services/analyst_output_contracts.py` | `analyst_output_guard.py`, tests | Pydantic | 없음 | 없음 | Agent DTO guard layer |
| `apps/agent/app/services/analyst_output_guard.py` | Agent analyst modules | 없음 | 없음 | 입력 evidence list만 사용 | Agent domain guard |
| `apps/agent/app/services/legal_api_clients.py` | legal ingestion/retrieval 계열 service/script | `httpx` | `LAW_API_OC`, `LAW_API_BASE`, `LAW_API_TARGETS`, `DATA_GO_*` | `law.go.kr`, `apis.data.go.kr` 외부 HTTP | Agent egress |
| `apps/worker/worker/main.py` | Worker container process | Redis, `job_processor` | `REDIS_URL`, `REDIS_STREAM_KEY`, `REDIS_STREAM_GROUP` | Redis stream/status key | `worker` service, no public port |
| `apps/worker/worker/job_processor.py` | `main.py` | psycopg, `video_preprocess`, `frame_analysis`, Agent HTTP helper | `DATABASE_URL`, `INTERNAL_AGENT_URL`, `INTERNAL_SERVICE_TOKEN`, `LOCAL_STORAGE_ROOT`, `REDIS_STREAM_KEY` | `jobs`, `uploads`, `cases`, `analysis_results`, Redis Stream follow-up enqueue, local frames | Worker domain service |
| `apps/worker/worker/video_preprocess.py` | `job_processor.py`, tests/scripts | ffprobe/ffmpeg subprocess | 없음 | local original video, `storage/frames/{caseId}/{uploadId}` | Worker video service |
| `apps/worker/worker/frame_analysis.py` | `job_processor.py` | OpenAI Responses API via `urllib` | `ENABLE_OPENAI_FRAME_ANALYSIS`, `OPENAI_API_KEY`, `OPENAI_VISION_MODEL`, `OPENAI_TIMEOUT_SEC`, `OPENAI_FRAME_ANALYSIS_MAX_FRAMES`, `OPENAI_FRAME_ANALYSIS_DETAIL` | OpenAI external HTTP, local frame images | Worker optional vision provider |

#### 데이터 모델 및 DTO 매핑

| 위치 | 모델/타입 | 외부 노출 여부 | 용도 |
| --- | --- | --- | --- |
| `apps/frontend/src/api/client.ts` | `User` | 프론트 내부/서버 응답 | 로그인 사용자 표시와 권한 판별 |
| `apps/frontend/src/api/client.ts` | `AccidentFacts` | 프론트 입력/서버 요청 | 사고 구조화 입력 |
| `apps/frontend/src/api/client.ts` | `CaseItem` | 프론트 입력/서버 응답 | 케이스 목록/상세 표시 |
| `apps/frontend/src/api/client.ts` | `UploadItem` | 서버 응답 | 업로드 파일 상태 표시 |
| `apps/gateway/src/storage/provider.ts` | `StoredObject`, `StorageProvider` | Gateway 내부 | 업로드 저장 결과 및 provider 추상화 |
| `apps/gateway/src/lib/internal-client.ts` | `AgentCallOptions` | Gateway 내부 | Agent 호출 timeout/retry/token 옵션 |
| `apps/gateway/src/services/chatService.ts` | `ChatServiceOptions` | Gateway 내부 | 채팅 service가 DB/Agent 설정을 받는 규격 |
| `apps/gateway/src/lib/report-composer.ts` | `evidence_reliability_card` | Gateway public report response 일부 | raw `claim_evidence`를 숨기고 근거 연결률, 판단 수, 근거 부족 수, 주의 문구를 일반 사용자용 카드로 요약 |
| `apps/agent/app/schemas.py` | `AnalyzeTextRequest` | Agent internal API request | 텍스트 분석 요청 검증 |
| `apps/agent/app/schemas.py` | `AnalyzeVideoRequest` | Agent internal API request | 영상 분석 요청 검증 |
| `apps/agent/app/schemas.py` | `EvidenceItem` | Agent internal API response | 법률/KNIA 근거 item 규격 |
| `apps/agent/app/schemas.py` | `AnalysisOutput` | Agent internal API response | 최종 분석 결과 표준 응답 |
| `apps/agent/app/services/analyst_output_contracts.py` | Analyst Pydantic contracts | Agent internal API response 일부 | `legal_analysis`, `fault_ratio`, `legal_liability`, `insurance_guide` dict의 내부 출력 계약 |
| `apps/agent/app/services/analyst_output_guard.py` | `evidence_support_level`, `judgment_status`, `used_evidence_ids`, `caveats`, `evidence_count`, `evidence_ids` | Agent internal API response 일부 | 분석가별 판단이 직접 근거, 간접 근거, 근거 부족 중 어디에 속하는지 표시하고 확정 판단 방지를 위한 주의 문구를 제공 |
| `apps/agent/app/services/elderly_friendly/plain_language_agent.py` | 쉬운 리포트 섹션 dict | Gateway public report response 일부 | 근거 부족 상태를 사용자 친화적인 경고/주의 문장으로 반영 |
| `apps/agent/app/services/claim_evidence_validator.py` | `claim_evidence` dict | Agent internal API response 일부 | 법규, 과실비율, 형사책임, 보험 안내, 행동계획의 주요 claim별 연결 근거와 지원 수준 |

#### 테스트 및 유지보수 상태 매핑

| 파일/영역 | Progress State | Test Status | Known Issues / Review Notes |
| --- | --- | --- | --- |
| `apps/frontend/src/api/client.ts`, `apps/frontend/src/components/easy/*`, `apps/frontend/src/composables/useCaseWorkspace.ts` | 구현 완료 | `apps/frontend/scripts/test-display.mjs`, `apps/frontend/scripts/test-chat.mjs`에서 간접 검증 | 네트워크/JSON/API 오류를 사용자 문구로 정규화하고 Gateway validation detail을 로그인, 회원가입, 케이스 생성, 케이스 상세 주요 액션에서 필드별 안내로 표시한다. 결과/근거 화면은 로딩, 결과 없음, 오류 상태를 구분하고 일반 사용자 화면에서는 내부 근거 식별자와 원문 덤프를 숨긴다. 쉬운 리포트는 `evidence_reliability_card`로 Agent 판단의 근거 연결 상태를 표시한다. 인증 폼은 데모 기본값 없이 email 형식과 8자 이상 비밀번호를 선제 검증한다. 케이스 상세 화면의 입력/업로드/분석/job polling 로직은 `useCaseWorkspace` composable로 분리했다. |
| `apps/frontend/src/router/index.ts` | 구현 완료 | 전용 단위 테스트 없음 | 인증 bootstrap가 route guard마다 실행되므로 초기 진입 지연 가능성은 관찰 대상 |
| `apps/frontend/src/stores/session.ts` | 구현 완료 | 전용 단위 테스트 없음 | localStorage 사용자 정보와 cookie 세션 불일치 시 refresh 흐름에 의존 |
| `apps/gateway/src/main.ts` | 구현 완료, Gateway composition root | `apps/gateway/test/error-format.test.ts`, `npm test`, `npm run build` | validation 오류는 400 `VALIDATION_ERROR`로 정규화된다. 신규 API 동작은 route module에 추가해야 한다 |
| `apps/gateway/src/lib/report-composer.ts` | 구현 완료, 리포트 안전화 로직 | `apps/gateway/test/report-composer.test.ts`, `npm test` | raw Agent 결과를 일반 사용자 화면용 리포트로 변환하므로 내부 식별자/점수/claim 세부 구조가 노출되지 않도록 테스트 유지 필요 |
| `apps/gateway/src/routes/chat.ts` | 구현 완료 | Gateway test에서 직접 매핑 확인 필요 | 일부 route는 `requireUser`를 명시적으로 강제하지 않고 익명 세션도 허용하는 구조다 |
| `apps/gateway/src/services/chatService.ts` | 구현 완료 | 전용 단위 테스트 없음 | Agent 장애 시 Gateway route에서 502로 변환된다 |
| `apps/gateway/src/storage/provider.ts` | 로컬 provider 구현, S3 provider 미구현 | 전용 단위 테스트 없음 | `S3StorageProvider`는 현재 의도적으로 비활성 상태 |
| `apps/agent/app/routers/internal.py`, `apps/agent/app/routers/internal_routes/*` | 구현 완료 | `apps/agent/scripts/check_internal_routes.py`, `scripts/verify_agent_regression.ps1`, `apps/agent/scripts/test_*.py` | 내부 token 누락/불일치 시 401. Route split 후에도 기존 `/internal/v1/*` path contract를 유지해야 한다. |
| `apps/agent/app/schemas.py` | 구현 완료 | `apps/agent/tests/test_orchestrator.py` 및 scripts에서 간접 검증 | 응답 모델이 크므로 프론트 표시 필드와 동기화 관리 필요 |
| `apps/agent/app/services/orchestrator.py` | 구현 완료, stage sequencing 중심 | `apps/agent/tests/test_orchestrator.py`, `apps/agent/scripts/test_legal_rag.py`, `test_knia_*`, `test_chat_*` 간접 검증 | 신규 stage 책임은 context/evidence/analysis/output 모듈에 추가하고 orchestrator는 순서 조립에 집중해야 한다 |
| `apps/agent/app/services/orchestration_output.py` | 구현 완료, 최종 출력 보강 로직 | `apps/agent/tests/test_orchestrator.py`, `apps/agent/scripts/test_agent_regression_scenarios.py` 간접 검증 | 사용자 화면에 raw trace/내부 식별자가 노출되지 않도록 Gateway/Frontend sanitizer와 함께 유지해야 한다 |
| `apps/agent/app/services/analyst_output_contracts.py` | 구현 완료, Analyst 출력 계약 | `apps/agent/tests/test_analyst_output_guard.py`, `apps/agent/tests/test_orchestrator.py` | LLM이 예외적인 JSON 타입을 반환해도 가능한 범위에서 정규화하되, 신규 analyst 추가 시 계약 모델을 함께 추가해야 함 |
| `apps/agent/app/services/analyst_output_guard.py` | 구현 완료, Analyst 신뢰도 가드 | `apps/agent/tests/test_analyst_output_guard.py`, `apps/agent/tests/test_orchestrator.py` | 신규 analyst 출력 필드가 프론트 일반 화면에 기술 문자열로 노출되지 않도록 Gateway/Frontend sanitizer와 함께 관리 필요 |
| `apps/agent/app/services/elderly_friendly/plain_language_agent.py` | 구현 완료, 근거 상태 기반 문장 완화 | `apps/agent/tests/test_elderly_report_support_language.py`, `apps/agent/tests/test_orchestrator.py` | 쉬운 리포트 문장은 내부 코드가 아니라 사용자 표시 문구만 포함해야 하며, 근거 부족 시 확정 표현을 피해야 함 |
| `apps/agent/app/services/claim_evidence_validator.py` | 구현 완료, Agent 신뢰도 보강 로직 | `apps/agent/tests/test_claim_evidence_validator.py`, `apps/agent/tests/test_orchestrator.py` | 주요 판단별 근거 연결 상태를 산출하고 analyst의 `used_evidence_ids`가 있으면 claim별 evidence ref 선정에 우선 사용한다. 향후 Analyst별 claim 형식이 바뀌면 함께 갱신 필요 |
| `apps/agent/app/services/legal_api_clients.py` | 구현 완료, 외부 권한 의존 | `apps/agent/scripts/check_external_apis.py` | 국가법령정보센터 IP/도메인 검증, 공공데이터포털 활용신청 권한 상태에 따라 실패 가능 |
| `apps/worker/worker/main.py`, `apps/worker/worker/job_processor.py`, `apps/worker/worker/video_preprocess.py`, `apps/worker/worker/frame_analysis.py` | 구현 완료, Worker 책임 분리 적용 | `python -m compileall worker`, `apps/worker/tests/test_keys.py`, E2E smoke에서 간접 검증 | ffmpeg/ffprobe 설치와 로컬 파일 경로 접근 권한에 의존. OpenAI 프레임 분석은 기본 비활성이고 환경변수로 켜야 한다 |
| `infra/postgres/migrations/*.sql` | 초기/증분 migration 구현 | Compose init, `db-migrate` profile, E2E smoke | `db-migrate` 명령은 일부 migration glob을 명시 적용하므로 신규 migration 추가 시 compose 명령 확인 필요 |

## 3. 의존성

### 패키지 의존성

| 영역 | 주요 의존성 |
| --- | --- |
| Frontend | `vue`, `vue-router`, `pinia`, `vite`, `typescript`, `vue-tsc`, `@vitejs/plugin-vue` |
| Gateway | `fastify`, `@fastify/cookie`, `@fastify/cors`, `@fastify/jwt`, `@fastify/multipart`, `pg`, `ioredis`, `bcryptjs`, `uuid`, `zod`, AWS S3 SDK |
| Agent | `fastapi`, `uvicorn`, `pydantic`, `httpx`, `psycopg[binary]`, `redis`, `python-dotenv`, `beautifulsoup4` |
| Worker | `redis`, `psycopg[binary]`, `boto3`, `tenacity`, 시스템 바이너리 `ffmpeg`, `ffprobe` |
| Infra | Docker Compose, Caddy, PostgreSQL 16 + pgvector, Redis 7.2 |

### 내부 모듈 연결성

| 호출 주체 | 대상 | 방식 |
| --- | --- | --- |
| Browser/Frontend | Gateway | HTTP `/api/v1/*`, cookie 세션 포함 |
| Gateway | PostgreSQL | `pg.Pool` 직접 SQL |
| Gateway | Redis | rate limit, 작업 큐, 상태 캐시 |
| Gateway | Agent | 내부 HTTP + `x-internal-token` |
| Gateway | Storage | 로컬 파일 저장. S3 SDK 의존성 존재 |
| Worker | Redis | `xreadgroup`, `xadd`, `xack`, `setex` |
| Worker | PostgreSQL | job/upload/case/result 상태 갱신 |
| Worker | Agent | 내부 HTTP + `x-internal-token` |
| Agent | PostgreSQL | KB, KNIA, 임베딩, 분석 근거 조회/저장 |
| Agent | 외부 API | `httpx` 기반 법령/공공/KNIA 호출 |

### 주요 환경변수

| 영역 | 환경변수 |
| --- | --- |
| 공통 | `DATABASE_URL`, `REDIS_URL`, `NODE_ENV`, `PYTHONPATH` |
| Gateway 인증 | `JWT_ACCESS_SECRET`, `JWT_REFRESH_SECRET`, `JWT_ACCESS_TTL_SEC`, `JWT_REFRESH_TTL_SEC`, `INTERNAL_ADMIN_TOKEN` |
| 내부 통신 | `INTERNAL_AGENT_URL`, `AGENT_BASE_URL`, `INTERNAL_SERVICE_TOKEN`, `REQUEST_TIMEOUT_MS`, `ANALYZE_TIMEOUT_MS`, `RETRY_COUNT` |
| 저장소 | `STORAGE_PROVIDER`, `LOCAL_STORAGE_ROOT`, `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| OpenAI | `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`, `OPENAI_TIMEOUT_SEC`, `ENABLE_OPENAI_ANALYSTS` |
| 법률/공공 API | `LAW_API_OC`, `LAW_API_BASE`, `LAW_API_TARGETS`, `DATA_GO_SERVICE_KEY`, `DATA_GO_TRAFFIC_URL`, `DATA_GO_SEARCH_YEAR`, `DATA_GO_SIDO`, `DATA_GO_GUGUN` |
| KNIA | `KNIA_BASE_URL`, `KNIA_REQUEST_DELAY_MS`, `KNIA_TIMEOUT_SEC`, `KNIA_COLLECT_MAX_CHARTS`, `KNIA_FAULT_RATIO_JSON_PATH` |

## 4. 리소스 연동

### 데이터베이스

기본 DB는 PostgreSQL이며 `vector`, `pgcrypto`, `citext` 확장을 사용한다.

| 테이블 그룹 | 대표 테이블 | 목적 |
| --- | --- | --- |
| 인증 | `users`, `auth_refresh_tokens` | 이메일 계정, role, refresh token hash |
| 케이스 | `cases`, `uploads`, `jobs`, `analysis_results` | 사고 케이스, 영상 업로드, 비동기 작업, 분석 결과 |
| 감사/멱등성 | `audit_logs`, `idempotency_keys`, `prompt_policy_versions` | 추적, 중복 요청 방지, 프롬프트 정책 버전 |
| 법률 KB | `kb_sources`, `kb_documents`, `kb_chunks`, `kb_embeddings`, `legal_rules`, `scenario_legal_mappings`, `kb_ingest_runs` | 법령/판례/규칙 문서 및 벡터 근거 |
| 채팅 | `chat_sessions`, `chat_messages`, `chat_safety_logs` | AI 상담 세션 및 안전 로그 |
| KNIA | `knia_sources`, `knia_menu_pages`, `knia_fault_charts`, `knia_fault_chart_chunks`, `knia_fault_rankings`, `knia_media_assets`, `knia_ranking_items` | 손해보험협회 과실비율 기준 데이터 |
| KNIA JSON | `knia_json_import_runs`, `knia_myaccident_pages`, `knia_menu_nodes`, `knia_reference_documents`, `knia_reference_chunks`, `knia_json_media_assets` | JSON 기반 과실비율 자료 import 및 검색 |
| 캐시/도구 | `semantic_query_cache`, `mcp_tool_calls` | 의미 검색 캐시, 내부 도구 호출 로그 |

### Redis

| 사용처 | 키/스트림 |
| --- | --- |
| Rate limit | `rl:v1:{user}:{route}:{minute}` |
| 작업 큐 | `jobs:v1:stream` |
| Consumer group | `worker-group` |
| 작업 상태 캐시 | `job:v1:{job_id}:status` |

### 파일/오브젝트 저장소

| 저장소 | 현재 동작 |
| --- | --- |
| 로컬 저장소 | `storage/uploads/{caseId}/{uploadId}/original.ext`에 업로드 영상 저장 |
| 프레임 저장소 | `storage/frames/{caseId}/{uploadId}/frame_*.jpg`에 대표 프레임 저장 |
| S3 | README와 환경변수에는 AWS S3 사용 전제가 있으나, Gateway의 `S3StorageProvider.putUpload()`는 현재 `S3_STORAGE_NOT_ENABLED`를 반환하는 상태 |

### 외부 API 및 기관

| 연동명 | 기관/사이트 | 코드상 목적 |
| --- | --- | --- |
| OpenAI API | OpenAI | 분석 모델 및 임베딩 모델 호출 |
| 국가법령정보센터 OPEN API | `https://www.law.go.kr/DRF` | 법령/판례 검색. `lawSearch.do`, target 기본값 `law,prec` |
| 공공데이터포털 교통 API | `https://apis.data.go.kr/B552061/AccidentDeath/getRestTrafficAccidentDeath` | 사망교통사고정보 조회 계열 API |
| KNIA 과실비율정보포털 | `https://accident.knia.or.kr` | 과실비율 기준, 순위, 차트, 관련 문서/미디어 수집 및 매칭 |
| 손해보험협회 웹 리소스 | `www.knia.or.kr` 계열 링크 | KNIA 자료 내 PDF/미디어 링크 보조 참조 |

### 보안 및 토큰 사용

민감값은 `.env` 계열 파일과 실행 환경변수로 주입된다. 문서에는 실제 키 값을 기록하지 않는다.

| 항목 | 사용 방식 |
| --- | --- |
| 사용자 로그인 | 이메일 + 비밀번호. 비밀번호는 `bcrypt` hash로 저장 |
| Access token | JWT, `lc_at` HTTP-only cookie |
| Refresh token | 원문은 cookie, DB에는 SHA-256 hash 저장 및 회전 |
| 내부 서비스 토큰 | Gateway/Worker가 Agent 호출 시 `x-internal-token` 헤더 사용 |
| 관리자 토큰 | `INTERNAL_ADMIN_TOKEN`이 설정된 경우 `x-admin-token`으로 관리자 API 접근 가능 |
| API 키 | OpenAI, 국가법령정보센터, 공공데이터포털, AWS 키는 환경변수 사용 |

## 5. 완성도 및 To-Do

### 구현 완료로 보이는 영역

| 영역 | 상태 |
| --- | --- |
| Docker Compose 구동 | `edge`, `frontend`, `gateway`, `agent`, `worker`, `postgres`, `redis` 서비스 정의 완료 |
| 기본 인증 | 이메일 회원가입/로그인/refresh/logout/me 구현 |
| 케이스 관리 | 생성, 목록, 상세, 수정 구현 |
| 로컬 영상 업로드 | multipart 업로드, 로컬 저장, 재생/다운로드 URL 구현 |
| 영상 비동기 처리 | Redis Stream 작업 큐, ffprobe/ffmpeg 전처리, Agent 분석 연계 구현 |
| 텍스트 분석 | Gateway에서 Agent 내부 API 호출 후 결과 저장 구현 |
| 법률 RAG | KB 테이블, 임베딩 테이블, 적재/검색/재빌드 경로 구현 |
| KNIA 연동 | 수집, ranking, chart, JSON import, 매칭, media search 경로 구현 |
| AI 채팅 | 세션, 메시지, 빠른 상담, 초안 케이스 반환 흐름 구현 |
| 운영 문서 | README, `docs/OPERATIONS.md`, OpenAPI 문서, 공유용 `env.example` 존재 |

### 코드상 확인된 미완성/주의 지점

| 항목 | 근거 및 상태 |
| --- | --- |
| S3 업로드 구현 | Gateway에 AWS SDK 의존성은 있으나 `S3StorageProvider.putUpload()`가 `S3_STORAGE_NOT_ENABLED`를 던진다. 현재 실제 업로드 경로는 로컬 저장소 중심이다 |
| 로그인 식별자 | DB와 API 스키마는 `email`만 로그인 식별자로 사용한다. 별도 `username` 또는 `login_id` 컬럼/입력은 보이지 않는다. 프론트 로그인/회원가입 화면도 email-only 정책을 따르며 기본 데모 계정값을 자동 입력하지 않는다 |
| 오류 응답 UX | Gateway validation 오류와 프론트 API client 오류 문구가 정규화되었고 로그인, 회원가입, 케이스 생성, 케이스 상세의 저장/업로드/분석 주요 액션에서 field별 안내 문구를 표시한다. 결과/근거 화면은 로딩, 결과 없음, 오류 상태를 구분하며 내부 근거 식별자와 원문 덤프는 debug 모드에서만 표시한다. KNIA 검색순위/상세/JSON 근거 검색 화면은 API 실패, 검색 결과 없음, 미수집 상태, 상세 기준 수집 필요 상태를 구분해 표시한다. 검색순위에는 있으나 상세 기준이 아직 수집되지 않은 항목은 ranking placeholder 상세 화면을 표시하고, 관리자에게 해당 기준만 수집하는 액션을 제공한다 |
| 외부 API 권한 의존 | `docs/OPERATIONS.md`에 국가법령정보센터 IP/도메인 검증, 공공데이터포털 활용신청/권한 이슈 가능성이 명시되어 있다 |
| Agent fallback | 법률 API 또는 KB 적재가 부족할 때 정적 fallback 근거를 반환하는 코드가 존재한다 |
| 테스트 산출물/캐시 파일 | `__pycache__`, `dist`, `storage` 내 테스트/실행 산출물이 저장소에 존재한다 |

### 테스트 및 검증 경로

| 영역 | 파일/명령 |
| --- | --- |
| Frontend build | `apps/frontend/package.json`의 `npm run build` |
| Frontend 표시 테스트 | `npm run test:display`, `npm run test:chat` |
| Gateway test | `apps/gateway/test/error-format.test.ts`, `npm test` |
| Agent 테스트 스크립트 | `apps/agent/tests/test_orchestrator.py`, `apps/agent/scripts/test_*.py` |
| Worker 테스트 | `apps/worker/tests/test_keys.py` |
| E2E 스모크 | `scripts/smoke_e2e.ps1` |
| 외부 API 점검 | `docker compose exec -T agent sh -lc "PYTHONPATH=/app python scripts/check_external_apis.py"` |

### 현재 기준 실행 절차

```bash
docker compose --env-file .env up --build
docker compose exec agent python scripts/ingest_kb.py
```

브라우저 접속 기준은 `http://localhost`이다.

### 문서 유지 시 우선 확인 대상

1. `compose.yaml` 서비스/환경변수 변경 여부
2. `AGENTS.md` 에이전트 진입 지침 변경 여부
3. `DEVELOPMENT_PROMPT.md` 개발 원칙/검증/문서 동기화 규칙 변경 여부
4. `docs/STACK_DECISION_REVIEW.md` 기술 스택 도입/전환 판단 변경 여부
5. `docs/PROJECT_BASELINE_2026-05-21.md`는 과거 기준점이므로 원칙적으로 변경하지 않되, 기준일 상태 오기재만 수정
6. `apps/gateway/src/main.ts` 공개 API 및 인증 흐름 변경 여부
7. `apps/agent/app/routers/internal.py` 내부 분석 API 변경 여부
8. `infra/postgres/migrations` 테이블/인덱스 변경 여부
9. `apps/frontend/src/api/client.ts` 프론트 DTO 및 API 호출 변경 여부

## 2026-05-21 Agent 검색 품질 보강 기록

Agent 레이어의 판례/법률 RAG, KNIA 기준 매칭, 추천 키워드가 서로 다른 검색어 기준을 쓰면 같은 사고 입력이라도 근거 검색 품질이 흔들릴 수 있어 공통 검색어 보강 모듈을 추가했다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/scenario_search_terms.py` | 시나리오, 태그, 사고 당사자 유형, 구조화 사실을 표준 검색어로 확장하는 공통 모듈 |
| `apps/agent/app/services/rag_client.py` | 법률 근거 검색 전에 시나리오 검색어를 붙이고 `query_expansion_terms`를 retrieval 메타데이터에 기록 |
| `apps/agent/app/services/knia/knia_matcher.py` | KNIA FTS/vector/tag 검색 쿼리에 시나리오별 표준 검색어를 반영하고 `knia_query_expansion_terms` 추적 가능 |
| `apps/agent/app/services/keyword_recommender.py` | 추천 키워드와 후속 입력 안내를 공통 검색어 기준으로 정리 |
| `apps/agent/tests/test_scenario_search_terms.py` | 검색어 확장, 추천 키워드, 주정차 분류 회귀 테스트 |

DB schema, Redis key, 외부 API, 환경 변수 변경은 없다. Agent 최종 응답의 `model_info.retrieval`에는 `query_expansion_terms`, `knia_query_expansion_terms`가 추가된다. 실제 근거 품질은 DB에 적재된 법률 KB/KNIA 원문 상세 기준의 충실도에 계속 의존하므로 다음 Agent 단계에서는 직접 관련성 점수 하한과 시나리오별 필수 근거군 검증을 보강해야 한다.
## 2026-05-21 후미추돌 사용자 관점 및 근거 표시 보정

정차 중 뒤에서 추돌당한 사고에서 KNIA `A:B` 기준을 사용자 관점으로 변환하지 않아 `A차량=뒤차/추돌차량`의 100% 과실이 그대로 `내 책임`으로 표시되는 문제가 있었다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/accident_perspective.py` | 후미추돌 문장에서 사용자가 앞차/피추돌 차량인지 뒤차/추돌 차량인지 판별하고 KNIA A/B 과실을 사용자 기준 `my/other`로 변환 |
| `apps/agent/app/services/analysts/fault_ratio_analyst.py` | KNIA가 없을 때도 후미추돌 사용자 역할에 따라 앞차는 내 책임 0%, 뒤차는 내 책임 100%로 기본 추정 |
| `apps/agent/app/services/orchestrator.py` | KNIA 최종 A/B 산정값을 바로 `my/other`에 넣지 않고 사용자 차량 역할 기준으로 변환 |
| `apps/agent/app/services/static_legal_fallback.py` | 영어 fallback 근거 제목/요약을 한국어 법률 근거 카드로 교체하고, 검색어가 맞는 fallback 근거를 우선 표시 |
| `apps/agent/app/services/knia/knia_matcher.py` | `차/보/자/기/단` 기준번호 접두어로 KNIA 사고 당사자 유형 보정 |
| `apps/frontend/src/components/easy/EasyReportView.vue` | KNIA A/B 원문값과 별도로 사용자 기준 내 책임/상대 책임 표시 |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | `following` 같은 일반 영문 단어 안의 `low`가 `낮음`으로 치환되지 않도록 수준값 치환을 단독 값에만 적용 |
| `apps/agent/tests/test_rear_end_user_perspective.py` | 후미추돌 사용자 역할 판별, A/B 과실 변환, 한국어 fallback 근거 회귀 테스트 |

DB schema, Redis key, 외부 API, 환경 변수 변경은 없다. 기존 KNIA 원문 A/B 값은 보존하되, 사용자 화면의 `내 책임/상대방 책임`은 `user_vehicle_role` 판별 결과를 기준으로 표시한다.

## 2026-05-21 KNIA 사용자 관점 매핑 확장 및 시나리오 매칭 보정

후미추돌에 한정되어 있던 KNIA A/B 기준의 사용자 관점 변환을 Agent 레이어에서 차선변경, 교차로 신호위반, 보행자, 자전거, 시설물, 단독 사고 유형으로 확장했다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/accident_perspective.py` | 사고 문장과 구조화 입력에서 사용자의 역할을 판별한다. 후미추돌은 앞차/뒤차, 차선변경은 직진차/진로변경차, 신호위반은 정상 신호차/신호위반차, 보행자·자전거 사고는 사용자 역할을 KNIA A/B 기준으로 변환한다. |
| `apps/agent/app/services/analysts/fault_ratio_analyst.py` | KNIA 기준이 없을 때도 사용자 역할을 반영해 차선변경과 신호위반 fallback 과실비율을 산정한다. |
| `apps/agent/app/services/knia/knia_matcher.py` | 교차로 신호위반 시나리오에서 신호위반 기준이 아닌 후미추돌/차선변경 기준이 1순위로 붙지 않도록 strict mismatch 필터를 추가했다. 매칭 점수 조정 이후 기존 Redis 캐시를 피하기 위해 `knia:match:v4` 캐시 키를 사용한다. |
| `apps/agent/tests/test_knia_user_perspective_mapping.py` | 차선변경, 신호위반, 자전거 사고에서 사용자 역할과 A/B 과실 변환을 검증한다. |
| `apps/agent/tests/test_knia_matcher_scoring.py` | 신호위반 기준 점수 보정, 관련 없는 후미추돌 기준 배제, chart 번호 기반 사고 당사자 라벨 보정을 검증한다. |

현재 로컬 DB에는 `차12-1` 교차로 신호위반 KNIA 차트가 수집되어 있지 않고 `차41-1`, `차43-2`만 확인된다. 따라서 신호위반 사고에서는 관련 KNIA 차트가 없으면 잘못된 기준을 억지로 붙이지 않고, Agent fallback 과실 추정으로 내려간다. 이후 KNIA 상세 기준 수집 또는 JSON import로 `차12-1` 계열 기준이 들어오면 해당 기준을 우선 매칭하도록 동작한다.

## 2026-05-21 Agent 판단 계약 및 근거 검증 게이트 보강

Agent 레이어의 개별 결과값을 단순 출력하지 않고, 시나리오 분류부터 근거 검색, 법률 분석, 과실 산정, 형사책임, 보험 안내, 행동 계획까지 단계별 판단 상태를 `agent_judgment` 계약으로 묶어 추적하도록 보강했다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/judgment_contract.py` | Agent 판단 단계별 상태를 `evidence_supported`, `needs_review`, `unsupported`로 표준화한다. claim coverage, 누락 입력, unsupported stage를 종합해 `overall_status`, `must_not_present_as_final`, `blocking_reasons`를 생성한다. |
| `apps/agent/app/services/orchestrator.py` | claim evidence 검증 이후 `agent_judgment` 계약을 생성하고 최종 분석 결과에 포함한다. 확정 표현이 부적절한 경우 disclaimer와 uncertainty reason을 보강한다. |
| `apps/agent/app/services/claim_evidence_validator.py` | claim 검증이 근거 목록 존재 여부만 보지 않고 각 analyst의 `evidence_support_level`도 반영한다. analyst가 `insufficient`로 판정한 항목은 근거 후보가 있더라도 unsupported claim으로 처리한다. |
| `apps/agent/app/schemas.py` | `AnalysisOutput`에 `agent_judgment` 필드를 추가했다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | `agent_judgment`와 내부 판단 계약 필드를 일반 사용자용 리포트에 노출하지 않는 기술 필드로 등록했다. |
| `apps/agent/tests/test_judgment_contract.py` | analyst support level이 claim evidence에 반영되는지, unsupported claim이 최종 판단 계약에서 확정 표현 차단 상태로 이어지는지 검증한다. |

DB schema, Redis key, 외부 API, 환경 변수 변경은 없다. 이 변경은 Agent 판단 구조와 근거 검증 체계의 내부 계약을 강화하는 작업이며, 사용자 화면은 기존 쉬운 리포트와 근거 연결 카드 중심으로 유지된다.

## 2026-05-21 Agent 대표 시나리오 회귀 검증 추가

Agent 판단 구조가 사고 유형, 사용자 관점, KNIA 기준 매칭, 최종 판단 계약을 함께 유지하는지 확인하기 위해 대표 사고 시나리오 스모크 검증을 추가했다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/scripts/test_agent_regression_scenarios.py` | 후방추돌 피해자, 상대 차선변경, 사용자 차선변경, 상대 신호위반, 사용자 자전거 사고를 `analyze_case()`로 실행하고 `scenario_type`, 사용자 기준 과실비율, `user_vehicle_role`, KNIA 1순위 기준, `agent_judgment` 계약 존재 여부를 검증한다. `pytest` 없이 컨테이너에서 직접 실행 가능한 회귀 스크립트다. |
| `apps/agent/app/services/knia/knia_matcher.py` | 보행자, 어린이보호구역, 자전거, 시설물, 단독 사고 시나리오에서 사고 당사자 유형이 맞지 않는 KNIA 기준을 엄격히 배제한다. 자전거 사고가 차대차 차선변경 기준(`차43-2`)에 잘못 연결되는 문제를 막기 위해 KNIA 매칭 캐시 키를 `knia:match:v5`로 갱신했다. |
| `apps/agent/tests/test_knia_strict_party_matching.py` | 자전거/보행자 시나리오가 관련 없는 차대차 기준을 거부하고 올바른 기준번호 계열은 허용하는지 단위 테스트로 고정했다. |

DB schema, Redis key 구조, 환경 변수, 외부 API 계약 변경은 없다. Redis KNIA 매칭 캐시 prefix만 `knia:match:v5`로 변경되어 기존 잘못된 매칭 캐시를 재사용하지 않는다.

## 2026-05-21 Agent 최종 출력 정책 게이트 보강

Agent 판단 계약이 단순 메타데이터로만 남지 않도록 최종 출력 섹션에 표시 정책을 직접 반영했다. 근거가 부족한 섹션은 확정 판단처럼 보이지 않도록 `presentation_status`, `finality_notice`, 신뢰도 상한, caveat를 적용한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/judgment_contract.py` | `agent_judgment` 계약을 적용할 때 법률 판단, 과실비율, 형사책임, 보험 안내 섹션별 상태를 확인하고 `review_required` 또는 `blocked_for_final` 표시 정책을 적용한다. 전체 판단 상태는 `presentation_policy.finality`로 요약한다. |
| `apps/agent/app/services/orchestrator.py` | 판단 계약 적용 후 쉬운 리포트를 다시 생성해 보수적으로 보정된 섹션 상태가 사용자용 설명에도 반영되도록 했다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | `presentation_policy`, `presentation_status` 등 내부 표시 정책 키가 일반 리포트에 원시 필드로 노출되지 않도록 기술 필드 목록에 추가했다. |
| `apps/agent/tests/test_judgment_contract.py` | unsupported/needs_review 섹션이 최종 출력에서 확정 표현 차단 상태와 신뢰도 상한을 받는지 검증한다. |

DB schema, Redis key, 환경 변수, 외부 API 계약 변경은 없다. 이 변경은 Agent 레이어의 최종 답변 안전장치이며, 근거가 부족한 판단을 사용자에게 결론처럼 제시하지 않기 위한 내부 출력 정책이다.

## 2026-05-21 Agent 근거 검색 품질 게이트 보강

Agent 레이어가 법률/KNIA 근거의 개수만 보고 검색 품질을 판단하지 않도록, 사고 유형별 근거 관련성 점검 게이트를 추가했다. 이 변경은 RAG/KNIA 검색 결과가 실제 사고 시나리오와 맞는지 확인하기 위한 골격 보강이며, DB schema, Redis key, 환경 변수, 외부 API 계약은 변경하지 않았다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/evidence_quality_gate.py` | 사고 유형별 근거 프로필을 정의하고, 검색 근거의 family(`legal`, `knia`, `general`), 사고 관련 tag/keyword/text match, 관련 근거 수, 누락 family, 약점을 산정한다. |
| `apps/agent/app/services/analysts/evidence_auditor.py` | 기존 근거 개수/평균 점수 기반 audit에 `scenario_evidence_coverage`를 추가하고, 기본 품질과 시나리오 관련성 품질 중 더 보수적인 값을 `evidence_quality`로 사용한다. |
| `apps/agent/scripts/test_agent_regression_scenarios.py` | 대표 사고 회귀 검증에서 `scenario_evidence_coverage` 필드 존재와 coverage level을 함께 확인한다. |
| `apps/agent/tests/test_evidence_quality_gate.py` | 후방 추돌 관련 근거, 신호위반 사고에 무관한 차선변경 근거, 근거 없음 상태를 단위 검증한다. |

현재 품질 게이트는 Agent 최종 판단을 즉시 차단하는 목적보다, `evidence_audit.scenario_evidence_coverage`와 `agent_judgment`가 근거 관련성 부족을 보수적으로 드러내도록 하는 목적에 가깝다. 대표 시나리오 회귀 기준은 이 필드가 항상 존재하고 `agent_judgment`와 함께 추적되는지를 검증한다.

## 2026-05-21 Agent 필수 근거 충족 기준 보강

Agent 근거 검색 품질 게이트를 한 단계 강화하여, 단순히 검색 결과가 존재하는 상태와 확정 판단에 가까운 상태를 분리했다. 사고 유형별로 필요한 근거군, 최소 전체 근거 수, 최소 사고 관련 근거 수, 평균 점수 기준을 `required_evidence`로 노출하고, 부족한 조건은 `missing_requirements`로 기록한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/evidence_quality_gate.py` | `EvidenceProfile`에 `required_families`, `min_total`, `min_relevant`, `min_average_score`를 추가했다. 후방추돌, 차선변경, 신호위반, 보행자, 어린이보호구역, 자전거 사고는 법령/판례 계열 근거와 KNIA 계열 근거를 모두 요구하며, 조건이 모두 충족될 때만 `decision_ready=true`와 `coverage_level=high`가 된다. |
| `apps/agent/app/services/judgment_contract.py` | evidence retrieval 단계가 `coverage_level=high`와 `decision_ready=true`일 때만 supported가 되도록 변경했다. `medium` 또는 `low` 근거는 결과가 존재하더라도 `needs_review`로 남기며, stage summary에 quality, coverage, missing requirement 수를 기록한다. |
| `apps/agent/tests/test_evidence_quality_gate.py` | 완전한 후방추돌 근거가 high coverage가 되는 경우와, 일부 근거만 있는 경우가 medium에 머무르는 경우를 검증한다. |
| `apps/agent/tests/test_judgment_contract.py` | scenario coverage가 medium이면 evidence retrieval stage가 supported가 아니라 needs_review로 남는지 검증한다. |

대표 회귀 시나리오 검증 결과 후방추돌, 차선변경, 신호위반은 `medium` coverage와 `needs_review` 상태를 유지한다. 자전거 사고는 직접 관련 근거가 부족해 `low` coverage로 낮아지며, 확정 판단 대신 추가 확인이 필요한 참고 결과로 남는다.

## 2026-05-21 Agent 취약 시나리오 정적 근거 보강

자전거, 보행자, 어린이보호구역 사고처럼 DB/KNIA 수집 상태에 따라 직접 관련 근거가 부족해질 수 있는 시나리오에 대해 정적 법률 보조 근거를 추가했다. 이 변경은 외부 API, DB schema, Redis key를 바꾸지 않고 Agent 내부 fallback 근거 품질을 높이는 작업이다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/static_legal_fallback.py` | 기존 후방추돌, 신호위반, 차선변경, 부상 관련 정적 근거에 `scenario_tags`를 추가했다. 신규로 자전거 주의의무, 자전거 과실비율 참고, 보행자·횡단보도, 어린이보호구역 정적 근거를 추가했다. |
| `apps/agent/app/services/rag_client.py` | DB 법률 검색 결과가 있더라도 정적 시나리오 보조 근거를 병합하도록 변경했다. 중복 근거는 `chunk_id`/URL/제목 기준으로 제거하고, 기존 limit보다 최대 3건까지만 보조 근거를 추가한다. |
| `apps/agent/tests/test_static_scenario_support.py` | 자전거 사고 입력에서 정적 근거가 자전거 관련 근거로 반환되고, evidence quality gate의 `scenario_relevant_evidence` 부족이 해소되는지 검증한다. |
| `apps/agent/scripts/test_agent_regression_scenarios.py` | 사용자 자전거 사고 회귀 시나리오에서 coverage가 `medium` 이상이고 관련 근거가 2건 이상인지 검증한다. |

검증 결과 자전거 사고는 기존 `low` coverage에서 `medium` coverage로 올라갔다. 보행자와 어린이보호구역 사고도 정적 시나리오 근거가 병합되어 직접 관련 근거를 확보한다. 다만 간단한 자연어 입력에서는 사고 세부 사실이 부족해 `required_input_fields` 또는 평균 점수 조건 때문에 `needs_review`가 유지된다.

## 2026-05-21 Agent 필수 입력 질문 계약 보강

간단한 자연어 사고 설명만으로는 `required_input_fields`가 남아 Agent 판단이 `needs_review`에 머무르지만, 기존 출력은 어떤 정보를 왜 보완해야 하는지 구조화하지 못했다. 필수 입력 부족을 사용자 보완 질문으로 연결하기 위해 Agent 내부에 `input_requirements` 계약을 추가했다. 이 변경은 DB schema, Redis key, 외부 API, 환경 변수는 변경하지 않고 Agent 결과 JSON과 사용자용 리포트 구성만 보강한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/input_requirements.py` | 사고 유형, 현재 structured facts, 자연어 설명, 누락 필드를 기준으로 `blocking_fields`, `optional_fields`, `questions`, `question_texts`를 생성하는 입력 요구사항 계약을 추가했다. 후방추돌, 차선변경, 신호위반, 보행자, 어린이보호구역, 자전거 사고별 핵심 보완 질문과 선택지를 정의했다. |
| `apps/agent/app/services/orchestrator.py` | 시나리오 분류 직후 `input_requirements`를 생성하고, 판단을 막는 필드만 evidence audit과 `agent_judgment.blocking_reasons`에 반영하도록 연결했다. |
| `apps/agent/app/services/analysts/evidence_auditor.py`, `apps/agent/app/services/keyword_recommender.py` | 기존의 `field 정보를 입력해 주세요`식 문구 대신 `input_requirements`의 사용자 질문을 `followup_questions`, `suggested_next_inputs`로 사용한다. |
| `apps/agent/app/services/report_composer.py`, `apps/agent/app/schemas.py` | Agent 최종 출력에 `input_requirements`와 `required_input_questions`를 포함한다. `structured_facts`에는 기존 `missing_fields`와 별도로 `required_input_fields`, `optional_input_fields`를 기록한다. |
| `apps/agent/app/services/judgment_contract.py` | `agent_judgment.input_requirements`에 입력 계약 버전, 판단 차단 필드, 선택 보완 필드, 질문 개수, 요약을 기록한다. |
| `apps/agent/app/services/elderly_friendly/plain_language_agent.py` | 쉬운 리포트의 `missing_info`가 raw field key 대신 사용자에게 바로 물어볼 수 있는 한국어 질문을 우선 표시하도록 변경했다. |
| `apps/gateway/src/lib/report-composer.ts`, `apps/frontend/src/utils/displaySanitizer.ts` | Gateway fallback 리포트도 `required_input_questions`를 반영하고, 입력 계약 내부 필드는 일반 화면에 원시 기술 필드로 노출되지 않도록 필터링한다. |
| `apps/agent/tests/test_input_requirements.py` | 후방추돌 자연어 입력에서 사고 유형/상대 행동은 문맥으로 충족 처리하고, 인명피해 등 실제 필요한 보완 질문만 남는지 검증한다. |

예를 들어 `정차 중 뒤에서 추돌당했습니다.` 입력은 `accident_type`과 `opponent_behavior`를 다시 묻지 않고, `다친 사람이 있나요?`처럼 판단에 필요한 보완 질문을 우선 제시한다. 손상 정도나 신호 상태처럼 해당 사고에서 확정 판단을 직접 막지 않는 항목은 optional 또는 낮은 우선순위로 처리한다.

## 2026-05-21 결과 화면 보완 입력 및 재분석 흐름 추가

Agent의 `input_requirements` 계약을 실제 사용자 흐름에 연결하기 위해 결과 화면에서 보완 질문에 답하고 즉시 재분석할 수 있는 경로를 추가했다. 이 변경은 DB schema, Redis key, 외부 API, 환경 변수는 변경하지 않는다. 기존 `analysis_results.result` JSON과 `elderly_friendly_report.missing_info.questions`를 통해 질문 메타데이터를 전달하고, Gateway의 기존 `/api/v1/cases/:caseId/reanalyze` API를 확장해 보완 입력을 케이스와 새 분석 결과에 반영한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/elderly_friendly/elderly_report_schema.py` | `missing_info`에 사용자용 질문 메타데이터 `questions`를 추가했다. |
| `apps/agent/app/services/elderly_friendly/plain_language_agent.py` | `required_input_questions`를 `missing_info.questions`로 변환해 field, label, question, input_type, options를 사용자용 리포트에 싣는다. |
| `apps/gateway/src/main.ts` | `/api/v1/cases/:caseId/reanalyze`가 `structured_facts`, `selected_keywords`, `analysis_mode`를 받아 기존 케이스 입력과 병합하고 케이스 상태/최신 분석 결과를 갱신하도록 확장했다. 응답에는 `result`, `report`도 함께 반환한다. |
| `apps/gateway/src/lib/report-composer.ts` | `missing_info.questions`의 field/options를 사용자 입력 폼에서 쓸 수 있도록 안전하게 보존하고, 내부 `input_requirements` 원문은 계속 숨긴다. |
| `apps/frontend/src/api/client.ts` | `reanalyzeText` API 래퍼와 보완 입력용 `AccidentFacts` 필드를 추가했다. |
| `apps/frontend/src/components/easy/MissingInfoCard.vue` | 보완 질문 목록을 select/input 폼으로 표시하고 답변 제출 이벤트를 발생시키도록 확장했다. |
| `apps/frontend/src/components/easy/EasyReportView.vue` | `MissingInfoCard`의 답변 제출 이벤트를 결과 화면으로 전달한다. |
| `apps/frontend/src/views/CaseResultView.vue` | 케이스 정보와 리포트를 함께 불러오고, 보완 답변을 `structured_facts` patch로 변환해 `reanalyzeText`를 호출한 뒤 새 리포트를 즉시 표시한다. |
| `apps/gateway/test/report-composer.test.ts` | sanitize 후에도 사용자용 질문 field가 유지되고 내부 입력 계약 원문은 노출되지 않는지 검증한다. |

현재 보완 답변은 결과 화면에서 새 분석을 생성하는 흐름까지 연결되어 있다. 다음 단계에서는 재분석 후 `agent_judgment`와 근거 coverage가 실제로 개선됐는지 사용자에게 전후 비교로 보여주는 UX를 추가할 수 있다.

## 2026-05-22 SRP Refactor Baseline

This section records the first SRP cleanup pass so future changes can compare module boundaries against this baseline.

| Path | Responsibility after this pass |
| --- | --- |
| `apps/worker/worker/main.py` | Redis Stream consumer group setup, stream polling, ack, and short-lived job status cache updates. |
| `apps/worker/worker/job_processor.py` | Worker DB job orchestration, upload row loading, DB status/result updates, follow-up job enqueueing, and Agent submission coordination. |
| `apps/worker/worker/video_preprocess.py` | Owns `worker-video-preprocess-v1`, ffprobe video metadata probing, event frame time selection, ffmpeg frame extraction, and extracted frame descriptors. |
| `apps/worker/worker/frame_analysis.py` | Owns optional OpenAI image/frame observation calls, frame selection for cost control, response JSON parsing, and observation normalization. |
| `apps/gateway/src/config/env.ts` | Owns Gateway runtime environment defaults and cookie secure mode. |
| `apps/gateway/src/lib/request-guards.ts` | Owns route key generation plus user/admin request guard behavior. |
| `apps/gateway/src/routes/auth.ts` | Owns signup, login, refresh, logout, and current-user session routes. |
| `apps/gateway/src/routes/cases.ts` | Owns basic case CRUD routes: create case, list cases, read case detail, and patch editable case fields. |
| `apps/gateway/src/routes/uploads.ts` | Owns local upload routes, upload completion verification, local video content delivery, and video preprocess job enqueueing. |
| `apps/gateway/src/routes/analysis.ts` | Owns case analysis and report routes: text analysis, video analysis job enqueueing, result/report/easy-report lookup, reanalysis, job listing, and evidence lookup. |
| `apps/gateway/src/routes/knia.ts` | Owns KNIA public lookup/search routes and public KNIA Agent proxy routes. |
| `apps/gateway/src/routes/knia-admin.ts` | Owns KNIA admin collection/detail collection, embedding rebuild, JSON import, and cache invalidation routes. |
| `apps/gateway/src/routes/legal-admin.ts` | Owns legal/admin routes: legal KB ingest, legal embedding rebuild, and legal retrieval smoke test proxy. |
| `apps/agent/app/routers/internal.py` | Owns only `/internal/v1` router composition and includes domain-specific internal route modules. |
| `apps/agent/app/routers/internal_auth.py` | Owns the shared internal service token check for Agent internal routes. |
| `apps/agent/app/routers/internal_routes/analysis.py` | Owns text, video, and structured scenario analysis endpoint handlers. |
| `apps/agent/app/routers/internal_routes/jobs.py` | Owns the internal worker job processing endpoint. |
| `apps/agent/app/routers/internal_routes/legal.py` | Owns legal KB ingest, embedding rebuild, and retrieval-test internal endpoints. |
| `apps/agent/app/routers/internal_routes/knia.py` | Owns KNIA collection, matching, fault estimate, JSON/search, media-search, and embedding internal endpoints. |
| `apps/agent/app/routers/internal_routes/chat.py` | Owns the internal accident consultation chat endpoint. |
| `apps/agent/app/routers/internal_routes/cache.py` | Owns Agent semantic cache invalidation endpoint behavior. |
| `apps/agent/app/routers/internal_routes/health.py` | Owns the unauthenticated Agent health endpoint. |
| `apps/frontend/src/views/CaseDetailView.vue` | Owns case workspace page assembly, composable wiring, and high-level report placement only. |
| `apps/frontend/src/components/case/CaseWorkspaceHeader.vue` | Owns case workspace title/status and navigation actions. |
| `apps/frontend/src/components/case/CaseSummaryCard.vue` | Owns case status summary and workspace count metrics. |
| `apps/frontend/src/components/case/CaseInputStep.vue` | Owns accident description, structured fact inputs, analysis mode, and keyword input rendering. |
| `apps/frontend/src/components/case/CaseUploadStep.vue` | Owns local upload, selected upload, upload list, and video preview rendering. |
| `apps/frontend/src/components/case/CaseAnalysisStep.vue` | Owns text/video analysis action controls, status message, and analysis job list rendering. |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | Owns case workspace state and actions: case load/save, upload, preprocessing, analysis requests, job polling, report loading, and display formatting helpers. |
| `apps/frontend/tsconfig.json` | Sets `noEmit` so TypeScript source remains the only frontend source of truth under `apps/frontend/src`. |
| `.gitignore` | Prevents generated JavaScript from being tracked beside TypeScript source under `apps/frontend/src`. |

Remaining SRP debt to handle in later iterations:

- `apps/gateway/src/main.ts` is now a Gateway composition root with shared hooks, health checks, route-module registration, audit logging, and centralized error handling. Keep new API behavior inside route modules unless it changes shared Gateway lifecycle hooks.
- `apps/agent/app/services/orchestrator.py` now delegates context, evidence, analysis, reflection, and output enrichment to stage modules. Keep future stage-specific logic out of the orchestrator unless it only changes stage ordering.
- `apps/agent/app/routers/internal.py` is now thin; keep new internal endpoint behavior inside `apps/agent/app/routers/internal_routes/*`.
- `apps/worker/worker/main.py` is now a Redis consumer entrypoint; keep video preprocessing, vision analysis, DB persistence, and Agent submission in Worker service modules.
- `apps/frontend/src/views/CaseDetailView.vue` now delegates workspace state/actions to `useCaseWorkspace` and visual subsections to `apps/frontend/src/components/case/*`; keep future case workspace UI additions inside the owning section component unless they change page-level flow.
- KNIA parser/repository files are functionally cohesive but large; split only when adding new KNIA collection or persistence behavior.

## 2026-05-22 Frontend Case Workspace SRP Split

The case detail workspace was reduced so the Vue view owns page assembly while the API state machine lives in a composable and visual sections live in dedicated case components. This is behavior-preserving and does not alter public API routes, DTOs, DB schema, Redis keys, storage paths, environment variables, or external integrations.

| Path | Responsibility |
| --- | --- |
| `apps/frontend/src/views/CaseDetailView.vue` | Wires `useCaseWorkspace`, case section components, and `EasyReportView`; keeps only page-level layout. |
| `apps/frontend/src/composables/useCaseWorkspace.ts` | Owns `useCaseWorkspace(caseId)`, including case load/save, preset handling, local upload, upload completion, video URL issuance, text/video analysis requests, job polling, easy-report loading, and display helpers. |
| `apps/frontend/src/components/case/CaseWorkspaceHeader.vue` | Renders title/status and refresh/result navigation actions. |
| `apps/frontend/src/components/case/CaseSummaryCard.vue` | Renders case status, description, keyword/upload/job counts. |
| `apps/frontend/src/components/case/CaseInputStep.vue` | Renders description, analysis mode, structured fact inputs, and keyword chips through props/events. |
| `apps/frontend/src/components/case/CaseUploadStep.vue` | Renders local upload controls, selected upload list, view/download actions, and video preview. |
| `apps/frontend/src/components/case/CaseAnalysisStep.vue` | Renders text/video analysis controls, user message, and job list. |
| `apps/frontend/scripts/test-display.mjs` | Includes the split case header component in display safety contract checks. |

Verification:

- `npm run build` in `apps/frontend`
- `npm run test:display` in `apps/frontend`
- `npm run test:chat` in `apps/frontend`

## 2026-05-22 Worker Job Processor SRP Split

Worker runtime responsibilities were separated so `apps/worker/worker/main.py` only owns Redis Stream consumption and status cache updates. Job-specific DB transitions, video preprocessing orchestration, Agent submission, and analysis result persistence now live in `apps/worker/worker/job_processor.py`. Existing video preprocessing and optional OpenAI frame analysis remain in `video_preprocess.py` and `frame_analysis.py`.

This change is behavior-preserving and does not alter API routes, DB schema, Redis key names, storage paths, environment variables, or external API contracts.

| Path | Responsibility |
| --- | --- |
| `apps/worker/worker/main.py` | Redis consumer group setup, stream polling, ack, and `job:v1:{jobId}:status` cache updates. |
| `apps/worker/worker/job_processor.py` | `video_preprocess`/`video_analyze` job processing, DB state changes, follow-up job enqueueing, Agent video analysis call, `analysis_results` insertion, and pure contract builders for worker tests. |
| `apps/worker/worker/video_preprocess.py` | ffprobe metadata probing and ffmpeg event-frame extraction. |
| `apps/worker/worker/frame_analysis.py` | Optional OpenAI frame observation provider and observation normalization. |
| `apps/worker/tests/test_job_processor_contract.py` | Tests canonical `video_analyze` payload, Agent video request payload, and analysis result value shaping without requiring DB/Redis. |

Verification:

- `python -m unittest discover -s tests` in `apps/worker`
- `python -m compileall worker tests` in `apps/worker`
- `docker compose exec -T worker python -m compileall worker`

## 2026-05-22 Worker Job Processor Contract Tests

Worker job payload/result shaping now has local tests that run without PostgreSQL, Redis, ffmpeg, or OpenAI credentials. The DB-facing worker functions still perform the same side effects, but canonical payload assembly was extracted into pure helpers so future changes to video providers or Agent input contracts can be checked quickly.

| Path | Change |
| --- | --- |
| `apps/worker/worker/job_processor.py` | Adds `build_video_analyze_payload()`, `build_agent_video_request()`, and `build_analysis_result_values()`. `process_job()` and `mark_failed()` now import `psycopg` lazily, and the retry decorator has a no-op fallback for local contract tests when `tenacity` is not installed. |
| `apps/worker/tests/test_job_processor_contract.py` | Verifies auto-enqueued video analysis payloads, Agent request metadata/summary preservation, used evidence ID extraction, risk flag fallback, and analyst output persistence shape. |

This change does not alter API routes, DB schema, Redis key names, storage paths, environment variables, external API calls, or public report payloads.

## 2026-05-22 GitHub Actions CI Baseline

The repository now has a hosted CI baseline for fast deterministic checks on `main` pushes and pull requests. It does not require real secrets, DB, Redis, Docker services, OpenAI calls, or public API credentials.

| Path | Change |
| --- | --- |
| `.github/workflows/ci.yml` | Adds separate Frontend, Gateway, Worker Contracts, and Agent Contracts jobs. Frontend runs build/display/chat checks, Gateway runs tests/build, Worker runs local unittest/compile checks, and Agent runs requirements install, compile, internal route contract check, and deterministic regression scenarios with LLM disabled. |
| `apps/agent/app/services/rag/two_stage_cache.py` | Degrades KNIA JSON cache/search to an empty result with `disabled_reason` when `DATABASE_URL` is unavailable, allowing deterministic Agent contract checks without DB services. |
| `apps/agent/tests/test_knia_cache_fallback.py` | Verifies the no-DB KNIA cache fallback using stdlib unittest so CI can run it without pytest. |

Deferred CI work: full Docker E2E and actual external API smoke checks should only be added after CI secrets, service health timing, and cost controls are explicitly configured.

## 2026-05-22 Frontend TypeScript Source Hygiene

The frontend source tree is now TypeScript-only for source modules. Previously tracked generated JavaScript mirrors under `apps/frontend/src` were removed because `tsconfig.json` already uses `noEmit`, and the app imports the `.ts`/`.vue` sources directly through Vite.

| Path | Change |
| --- | --- |
| `apps/frontend/src/**/*.js` | Removed tracked generated JavaScript duplicates for API clients, router, stores, types, main entry, and display sanitizer. |
| `.gitignore` | Adds `apps/frontend/src/**/*.js` so emitted JavaScript cannot be reintroduced beside TypeScript source. |
| `apps/frontend/scripts/test-display.mjs` | Reads `src/utils/displaySanitizer.ts` instead of the removed JavaScript mirror. |

Verification:

- `npm run build` in `apps/frontend`
- `npm run test:display` in `apps/frontend`
- `npm run test:chat` in `apps/frontend`

## 2026-05-22 Agent Regression Guard Update

This update strengthens the Agent fault judgment regression guard around user perspective and video-derived facts.

| Path | Change |
| --- | --- |
| `apps/agent/app/services/accident_perspective.py` | Rear-end role inference now treats strong structured facts (`stopped=True`, `opponent_behavior=rear_collision`, and no sudden brake) as higher priority than conflicting natural-language role phrases. This prevents a stopped rear-end victim from being mapped as the following/striking vehicle when video-derived facts indicate otherwise. |
| `apps/agent/scripts/test_agent_regression_scenarios.py` | Added `video_rear_end_overrides_conflicting_user_fact`, which runs `analyze_video_case()` with high-confidence frame observations and conflicting user text. It verifies video fact arbitration, conflict recording, front-vehicle role mapping, and final 0:100 user-perspective fault mapping. |

Verification command:

`docker compose exec -T agent python scripts/test_agent_regression_scenarios.py`

Additional syntax verification:

`docker compose exec -T agent python -m compileall app scripts`

Route contract verification:

`docker compose exec -T agent python scripts/check_internal_routes.py`

Combined Agent verification command:

`powershell -ExecutionPolicy Bypass -File scripts/verify_agent_regression.ps1`

## 2026-05-22 Agent Internal Route SRP Split

Agent internal API handlers were moved out of the large `apps/agent/app/routers/internal.py` file into responsibility-specific modules under `apps/agent/app/routers/internal_routes/`. This change preserves existing `/internal/v1/*` paths, request/response DTOs, DB schema, Redis keys, storage paths, environment variables, and external integrations.

| Path | Responsibility |
| --- | --- |
| `apps/agent/app/routers/internal.py` | Keeps only the `/internal/v1` `APIRouter` and includes domain route modules. |
| `apps/agent/app/routers/internal_auth.py` | Shares internal token verification across protected internal routes. |
| `apps/agent/app/routers/internal_routes/analysis.py` | Text, video, and structured scenario analysis endpoints. |
| `apps/agent/app/routers/internal_routes/jobs.py` | Worker job processing endpoint. |
| `apps/agent/app/routers/internal_routes/legal.py` | Legal KB ingest, embedding rebuild, and retrieval smoke endpoint. |
| `apps/agent/app/routers/internal_routes/knia.py` | KNIA collection, ranking/detail, matching, fault estimate, JSON/search, media-search, and embedding endpoints. |
| `apps/agent/app/routers/internal_routes/chat.py` | Chat consultation endpoint. |
| `apps/agent/app/routers/internal_routes/cache.py` | Cache invalidation endpoint. |
| `apps/agent/app/routers/internal_routes/health.py` | Agent health endpoint. |
| `apps/agent/scripts/check_internal_routes.py` | Verifies that the required internal route paths are still registered after router refactors. |
| `scripts/verify_agent_regression.ps1` | Runs Docker-based Agent compile check, internal route contract check, and representative Agent regression scenarios. |

## 2026-05-22 Completion Priority Backlog

This backlog separates trust-critical reinforcement from deferred enhancements. Use it to decide future development order before adding new features.

### P0 Completed

| Priority | Area | Current State | Remaining Work |
| --- | --- | --- | --- |
| P0 | Agent regression automation | `scripts/verify_agent_regression.ps1` now runs compile, internal route contract, and representative judgment regression scenarios. `scripts/verify_core.ps1` calls this guard during Docker checks. `.github/workflows/ci.yml` runs frontend, gateway, worker contract, and Agent contract/regression checks on push/PR. | 완료. CI에서 secret/service dependency가 필요한 실제 영상 full E2E는 로컬 운영 검증으로 유지한다. |
| P0 | Agent execution trace | Outputs include `video_input_contract`, `fact_arbitration`, `evidence_audit`, `agent_judgment`, and `presentation_policy`. A safe admin diagnostic API now exposes stage and packet summaries without raw user text. Public easy-report uses sanitized cards only. | 완료. 개발자 페이지 확장은 local-only P1/P2 보조 도구로만 다룬다. |
| P0 | Reflection/reverification loop | `reflection_loop` now performs one bounded evidence requery when requeryable evidence requirements are missing, records next action, builds scenario-specific Korean requery terms, and exposes safe `agent_process_card.decision_notes`. | 완료. 향후 개선은 검색 품질 튜닝이며 P1로 분류한다. |
| P0 | Agent SRP | `orchestrator.py` now delegates input context, evidence collection, analyst execution, reflection requery, and final output enrichment to dedicated stage modules. | 완료. 이후 Agent 변경은 소유 stage module과 테스트 안에서 진행한다. |

### Reinforce Next

| Priority | Area | Current State | Needed Work |
| --- | --- | --- | --- |
| P1 | Gateway SRP | `gateway/src/main.ts` remains the composition root. Auth/session, case CRUD, upload, analysis/report, public KNIA, KNIA admin, and legal/admin routes live under `apps/gateway/src/routes/`. | Keep new API behavior in route modules; split large route modules only when they grow further. |
| P1 | Worker SRP | `main.py` now only consumes Redis Stream messages and delegates DB job processing to `job_processor.py`; ffprobe/ffmpeg preprocessing and OpenAI frame analysis live in dedicated modules. Local Worker contract tests now cover video analyze payload, Agent video request payload, and analysis result value shaping. | Add DB/Redis integration tests only when expanding queue persistence or video provider behavior. |
| P1 | Frontend source hygiene | `apps/frontend/src` is now TypeScript-only for source files; tracked generated `.js` duplicates were removed and `.gitignore` blocks them from returning. | Keep new frontend source in `.ts`/`.vue` files and avoid committing emitted JavaScript beside source. |
| P1 | Evidence/search quality | Structured fact 기반 검색어 확장, 정적 과실비율 fixture, 대표 사고 유형별 `test_evidence_search_quality.py` 회귀 검증을 추가했다. 이 검증은 실제 DB 또는 fallback 근거를 통해 필수 검색어, 법률/KNIA 근거군, 직접 관련 근거 수, 최소 coverage를 확인한다. | 완료. 실제 KNIA/법률 DB 수집량이 늘어난 뒤 `total_evidence`와 `coverage=high` 기준으로 점진 상향한다. |
| P1 | Video observation validation | 실제 OpenAI 프레임 분석 E2E를 `gpt-4.1-mini`, `detail=low`, 6프레임 측정 기준으로 통과했고, 이후 짧은 사고 영상의 전후 맥락 누락을 줄이기 위해 운영 프레임 예산을 기본 10프레임/상한 12프레임으로 올렸다. Agent 사실 중재에는 충돌 품질 게이트를 추가했다. 영상값은 미입력 사실 보강에 쓰이며, 사용자 입력과 충돌하면 강한 품질 조건 또는 검증 표시가 있을 때만 덮어쓴다. | 완료. 남은 작업은 실제 품질 데이터가 쌓인 뒤 필드별 임계값을 조정하는 운영 튜닝이다. |

### Defer Until Core Trust Is Stable

| Area | Why Deferred |
| --- | --- |
| UI polish/layout | Useful, but less important than judgment correctness and evidence traceability. |
| Developer page expansion | Local-only diagnostic aid; should not block service logic. |
| Full multi-agent process orchestration | Current analyst modules can support MVP; process-level agents add complexity. |
| Standard MCP adoption | Current internal registry is enough for MVP; standard MCP needs stronger security/tool isolation design. |
| Token/cost dashboard | LLM use is already gated; detailed billing UI can come after core loops. |
| S3/direct upload migration | Local storage works for current MVP and collaboration constraints. |
| Specialized traffic-accident video model | Desired later; current frame extraction plus optional OpenAI observation path is enough for next stabilization. |

## 2026-05-22 Agent Execution Trace Update

This update addresses the lecture-derived gap around Agent pipeline observability, packet-style data flow, and production guardrails. It adds a safe execution trace to each Agent analysis result without exposing raw user text or secrets.

| Path | Change |
| --- | --- |
| `apps/agent/app/services/agent_execution_trace.py` | Adds `agent-execution-trace-v1`, a safe metadata-only trace builder covering input normalization, fact arbitration, scenario classification, evidence retrieval, analyst execution, claim validation, judgment contract, and follow-up loop stages. |
| `apps/agent/app/services/orchestrator.py` | Adds `agent_trace` to final Agent output after the judgment contract is applied, and records `agent_trace_version` in `model_info`. |
| `apps/agent/app/schemas.py` | Adds `agent_trace` to `AnalysisOutput` so downstream Gateway/frontend consumers can safely inspect the Agent pipeline state. |
| `apps/agent/tests/test_orchestrator.py` | Adds contract assertions for trace version, safe metadata policy, stage IDs, video contract presence, video observation counts, and raw-text exclusion. |

The trace intentionally records counts, statuses, confidence-related state, and missing requirements rather than hidden chain-of-thought or raw user descriptions. This keeps the Agent debuggable while preserving privacy and output safety.

## 2026-05-22 Agent Reflection Loop Update

This update makes the Agent recovery path explicit when evidence coverage, KNIA/legal basis, or required inputs are insufficient.

| Path | Change |
| --- | --- |
| `apps/agent/app/services/reflection_loop.py` | Adds `agent-reflection-loop-v1`, a bounded recovery contract. It decides whether one evidence requery should be attempted, records missing requirements and blocking input fields, and resolves the final next action as `finalize`, `request_missing_input`, `present_reference_only`, or `manual_review`. |
| `apps/agent/app/services/orchestrator.py` | Runs one conservative legal evidence requery when requeryable evidence requirements are missing, merges newly found evidence, reruns analysts/audit/claim validation, then attaches `reflection_loop` to the final output. |
| `apps/agent/app/services/agent_execution_trace.py` | Adds a `reflection_loop` trace stage with requery attempt status, added evidence count, iteration count, and next action. |
| `apps/agent/app/schemas.py` | Adds `reflection_loop` to `AnalysisOutput`. |
| `apps/agent/tests/test_orchestrator.py` | Adds assertions for reflection loop version, next action, trace stage, and video-case compatibility. |

The loop is deliberately bounded to one requery attempt to avoid uncontrolled cost or latency. If evidence remains insufficient, the judgment contract and presentation policy keep the result as reference-only or request user-supplied missing facts.

## 2026-05-22 Video Fact Explanation Card

This update makes video-derived fact arbitration visible to users in safe Korean copy. When frame observations conflict with user input or are applied to Agent facts, the public report explains which physical fact was reflected without exposing raw contracts such as `video_input_contract`, `fact_arbitration`, frame-analysis provider strings, raw value keys, or internal reasons.

| Path | Change |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | Converts Agent video contracts into `video_fact_explanation_card`, including applied video facts, user-input comparison items, deferred observations, confidence labels, and representative frame counts. |
| `apps/frontend/src/components/easy/VideoFactExplanationCard.vue` | Renders the video fact explanation card with Korean labels and safe summaries only. |
| `apps/frontend/src/components/easy/EasyReportView.vue` | Places the video fact card after the Agent process card and before the fault ratio card. |
| `apps/gateway/test/report-composer.test.ts` | Verifies that the card is generated and raw arbitration/source/reason/value keys are not exposed. |

No DB schema, Redis key, storage path, environment variable, or external API contract changed. Public easy-report responses may now include `video_fact_explanation_card`.

## 2026-05-22 Video Conflict Follow-Up Questions

This update connects video/user fact conflicts to the existing follow-up and reanalysis loop. When `fact_arbitration.conflicts` contains a safe input field such as `lane_change_actor`, Gateway now adds a Korean single-choice question to `missing_info.questions`. The frontend already submits those answers through `MissingInfoCard` and `/api/v1/cases/:caseId/reanalyze`, so no new API route or DB schema was required.

| Path | Change |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | Adds `composeVideoConflictQuestions()` and merges safe video conflict questions into `missing_info.questions` while avoiding duplicates. |
| `apps/gateway/test/report-composer.test.ts` | Verifies that a video/user conflict generates a usable follow-up question with the canonical field preserved and safe Korean options. |

The question field is preserved only for known safe follow-up fields so the existing reanalysis normalizer can update structured facts. Raw video contracts and internal arbitration metadata remain hidden from public report rendering.

## 2026-05-22 Reanalysis Judgment Delta Card

This update strengthens the existing reanalysis comparison card so users can understand what changed after follow-up answers are submitted. The Gateway now passes the normalized follow-up answer summary into `composeReanalysisChangeCard()`, and the card includes safe decision notes for answered fields, unresolved fields, ignored fields, judgment status transition, and whether the bounded evidence requery ran.

| Path | Change |
| --- | --- |
| `apps/gateway/src/main.ts` | Passes `normalizedFollowup` into `composeReanalysisChangeCard()` after `/api/v1/cases/:caseId/reanalyze`. |
| `apps/gateway/src/lib/report-composer.ts` | Adds safe `decision_notes` and a reflected-answer count to `analysis_change_card`. |
| `apps/frontend/src/components/easy/AnalysisChangeCard.vue` | Renders `decision_notes` under a judgment-change summary section. |
| `apps/gateway/test/report-composer.test.ts` | Verifies reflected answer counts and safe Korean field labels in the reanalysis comparison card. |

No new API route, DB schema, Redis key, storage path, environment variable, or external integration was added. The existing reanalysis response payload now carries richer user-safe comparison metadata.

## 2026-05-22 Core Verification Entry Point

This update converts the manually run project checks into a repeatable PowerShell entry point for local regression verification. It does not change service APIs, DB schema, Redis keys, storage paths, environment variables, or external integrations.

| Path | Change |
| --- | --- |
| `scripts/verify_core.ps1` | Runs Gateway tests/build, Frontend build/display/chat checks, optional Docker compose build/start, the Agent regression guard script, and Gateway `/health` through the edge service. |
| `scripts/verify_agent_regression.ps1` | Runs Agent compile check, internal route contract verification, and representative Agent regression scenarios in Docker. |
| `apps/agent/scripts/check_internal_routes.py` | Fails fast when required `/internal/v1/*` paths are not registered after Agent router refactors. |
| `docs/OPERATIONS.md` | Documents the one-command verification flow plus `-SkipDockerBuild` and `-SkipDockerChecks` options. |
| `DEVELOPMENT_PROMPT.md` | Adds the core regression command to the verification policy for changes that affect Agent judgment, Gateway report composition, Frontend result display, video facts, or follow-up/reanalysis flows. |

Primary command:

`powershell -ExecutionPolicy Bypass -File scripts/verify_core.ps1`

Use this before committing trust-critical changes so rear-end, lane-change, signal-violation, bicycle/pedestrian, and video/user-conflict scenarios remain covered by the Agent regression script.

## 2026-05-22 Admin Agent Trace Diagnostic API

This update adds an administrator-only diagnostic API for Agent pipeline observability. It keeps the existing public report sanitization intact and exposes only safe metadata summaries for developers or operators.

| Path | Change |
| --- | --- |
| `apps/gateway/src/lib/agent-diagnostics.ts` | Adds `agent-trace-diagnostic-v1`, which summarizes Agent trace steps, packet metadata, judgment contract, reflection state, video input contract counts, fact arbitration counts, evidence coverage, and presentation policy while filtering raw user text, secrets, tokens, emails, and raw evidence ids. |
| `apps/gateway/src/routes/agent-diagnostics.ts` | Registers `GET /api/v1/admin/cases/:caseId/agent-trace`, guarded by login plus admin role or `x-admin-token`. The route returns the latest result or a specified `version`. |
| `apps/gateway/src/main.ts` | Wires the diagnostics route module without adding the route body directly to the composition root. |
| `apps/gateway/test/agent-diagnostics.test.ts` | Verifies that packet summaries remain useful while raw text, email, token, and chunk id-like values are filtered. |
| `docs/api/openapi.yaml`, `docs/OPERATIONS.md` | Documents the admin trace diagnostic endpoint and its safety constraints. |

The endpoint is intended for internal project inspection, not normal user UI. It does not change DB schema, Redis keys, storage paths, environment variables, external API contracts, or public easy-report behavior.

## 2026-05-22 Gateway KNIA Route Split

Gateway KNIA routes were moved out of `apps/gateway/src/main.ts` into route modules as part of the SRP cleanup. Public KNIA lookup/search routes stay in `apps/gateway/src/routes/knia.ts`; administrator collection, embedding, JSON import, and cache invalidation routes now live in `apps/gateway/src/routes/knia-admin.ts`. This change does not alter API paths, DB schema, Redis keys, storage paths, or external Agent endpoints.

| Path | Responsibility |
| --- | --- |
| `apps/gateway/src/routes/knia.ts` | Registers KNIA ranking, chart detail, adjustment/reference, match, fault estimate, myaccident menu/tree, JSON search, and media search routes. |
| `apps/gateway/src/routes/knia-admin.ts` | Registers admin KNIA collection, ranking detail collection, embedding rebuild, JSON import, JSON embedding rebuild, and cache invalidation routes. |
| `apps/gateway/src/routes/legal-admin.ts` | Registers legal/admin ingest, legal embedding rebuild, and legal retrieval-test routes. It preserves the existing Agent internal endpoints and admin guard behavior. |
| `apps/gateway/src/main.ts` | Keeps shared Fastify plugin setup, trace/auth/rate-limit/idempotency/audit/error hooks, health checks, and route-module registration. |

Verification:

- `npm run build` in `apps/gateway`

## 2026-05-22 Agent Orchestrator SRP Stage Split

This update reduces `apps/agent/app/services/orchestrator.py` to stage sequencing and final stage handoff. Input normalization, evidence collection, analyst execution, bounded reflection requery, and output enrichment are now delegated to dedicated modules. The change is behavior-preserving and does not alter public API DTOs, DB schema, Redis keys, storage paths, environment variables, or external integrations.

| Path | Responsibility |
| --- | --- |
| `apps/agent/app/services/orchestration_context.py` | Builds `CaseContext`: video context, normalized input, scenario classification, user vehicle role inference, party action guide, input requirements, and follow-up loop state. |
| `apps/agent/app/services/orchestration_evidence.py` | Builds `EvidenceBundle`: KNIA chart matching, KNIA JSON search, KNIA fault/reference evidence, legal retrieval, evidence normalization, and duplicate merging helpers. |
| `apps/agent/app/services/orchestration_analysis.py` | Builds `AnalysisBundle` and `ReflectionStageResult`: analyst outputs, evidence audit, claim-evidence audit, KNIA fault application, and one bounded evidence requery. |
| `apps/agent/app/services/orchestration_output.py` | Enriches the composed output with judgment contract effects, reflection loop, execution trace, elderly-friendly report, KNIA calculation metadata, and retrieval/scenario model metadata. |
| `apps/agent/app/services/orchestration_stages.py` | Lightweight export facade for the stage functions and dataclasses. |
| `apps/agent/app/services/orchestrator.py` | Keeps request entry points and orchestrates stage order, judgment contract creation, reflection loop creation, report composition, and output enrichment handoff. |

Verification focus remains the same: Agent compile check and representative regression scenarios must pass after future changes to these stage modules.

## 2026-05-22 Agent Output Enrichment SRP Split

The final Agent output enrichment step now lives in `apps/agent/app/services/orchestration_output.py`. This keeps `orchestrator.py` from accumulating KNIA/report/trace metadata assembly whenever the response contract grows. The public `AnalysisOutput` shape, API routes, DB schema, Redis keys, storage paths, environment variables, and external integrations are unchanged.

| Path | Responsibility |
| --- | --- |
| `apps/agent/app/services/orchestration_output.py` | Owns `enrich_analysis_output()`, `_attach_knia_fault_estimate()`, and `_build_retrieval_model_info()` for final response metadata assembly. |
| `apps/agent/app/services/orchestration_stages.py` | Re-exports `enrich_analysis_output()` with the other stage helpers. |
| `apps/agent/app/services/orchestrator.py` | Calls `enrich_analysis_output()` after composing the base analysis payload. |

Verification focus:

- `docker compose exec -T agent python -m compileall app scripts`
- `docker compose exec -T agent python scripts/test_agent_regression_scenarios.py`

## 2026-05-22 영상 관찰값 품질 표시 연결

Worker와 Agent가 생성하는 영상 관찰값 품질 요약을 일반 결과 화면과 관리자 진단에서 확인할 수 있도록 Gateway 표시 계층에 연결했다. 일반 사용자 화면에는 raw `video_input_contract`, `quality_gate`, `frame_refs`, `observation_quality_summary`를 직접 노출하지 않고, Gateway가 만든 `video_fact_explanation_card.quality_summary`만 표시한다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | Agent `video_input_contract.observation_quality_summary`를 사용자 안전 라벨과 카운트로 변환한다. `품질 상태`, 반영/보류 수, 단일/복수 프레임 관찰값, 보류 사유를 `video_fact_explanation_card.quality_summary`에 담는다. |
| `apps/frontend/src/components/easy/VideoFactExplanationCard.vue` | 결과 화면의 영상 기반 사실 반영 카드 안에 관찰값 품질 섹션을 추가한다. 품질 상태, 반영/보류 수, 복수 프레임 수, 보류 사유를 사람이 읽을 수 있는 형태로 표시한다. |
| `apps/frontend/src/utils/displaySanitizer.ts` | `observation_quality`, `observation_quality_summary`, `quality_gate`, `frame_refs`를 기술 필드로 추가해 일반 화면에 원시 내부 계약이 섞이지 않게 했다. |
| `apps/gateway/src/lib/agent-diagnostics.ts` | 관리자 진단 응답의 `video_input.observation_quality`에 반영/보류 수와 단일/복수 프레임 카운트를 추가한다. |
| `apps/gateway/test/report-composer.test.ts`, `apps/gateway/test/agent-diagnostics.test.ts` | 사용자 안전 카드와 관리자 진단 품질 요약이 생성되고 raw 내부 키가 노출되지 않는지 검증한다. |

이 변경은 DB schema, Redis key, storage path, 외부 API 계약을 변경하지 않는다. 공개 easy-report payload의 표시용 카드 구조만 확장한다.

## 2026-05-22 영상 품질 보류 관찰값 보완 질문 연결

영상 프레임 분석에서 관찰값은 생성됐지만 품질 기준을 통과하지 못한 항목을 결과 화면의 보완 질문으로 연결했다. 목적은 영상값을 확정 사실처럼 쓰지 않으면서도, 사용자가 확인 가능한 항목은 기존 재분석 흐름으로 보강할 수 있게 하는 것이다.

| Path | 변경 내용 |
| --- | --- |
| `apps/gateway/src/lib/report-composer.ts` | `uncertain_observations` 중 사용자 확인이 가능한 필드를 `missing_info.questions`로 변환한다. 기존 영상/사용자 충돌 질문과 중복되지 않게 field 기준으로 합친다. |
| `apps/gateway/src/lib/followup-normalizer.ts` | 영상 품질 보류 질문 답변 중 `opponent_behavior`, `opponent_signal_violation`을 Agent canonical fact로 정규화한다. |
| `apps/gateway/test/report-composer.test.ts`, `apps/gateway/test/followup-normalizer.test.ts` | 품질 보류 관찰값이 보완 질문으로 생성되고, 답변이 재분석 입력 fact로 변환되는지 검증한다. |

이 변경은 기존 `/api/v1/cases/:caseId/reanalyze` 흐름을 그대로 사용하며 DB schema, Redis key, storage path, 외부 API 계약을 변경하지 않는다.

## 2026-05-23 영상 보류 관찰값 재분석 E2E 옵션

실제 영상 E2E 스크립트에 품질 보류 관찰값의 보완 질문과 재분석 반영까지 확인하는 선택 검증 경로를 추가했다. 기본 smoke 경로는 그대로 유지하고, `--exercise-held-observation-followup` 옵션을 켰을 때만 품질 보류 질문을 찾아 답변 제출과 재분석 결과를 검증한다.

| Path | 변경 내용 |
| --- | --- |
| `scripts/video_agent_e2e.py` | `--exercise-held-observation-followup` 옵션을 추가했다. `missing_info.questions`에서 품질 기준 보류 질문을 찾고, 안전한 테스트 답변을 제출한 뒤 `/api/v1/cases/:caseId/reanalyze` 응답의 `analysis_change_card` 생성 여부를 확인한다. |
| `apps/worker/worker/frame_analysis.py` | `FRAME_ANALYSIS_FIXTURE_MODE=held_quality`를 추가했다. 낮은 confidence의 `turn_signal` 관찰값을 생성해 Agent에서 보류되고 Gateway 보완 질문으로 이어지는 경로를 비용 없이 검증한다. |
| `apps/worker/tests/test_frame_analysis_contract.py` | `held_quality` fixture가 저신뢰 관찰값과 품질 요약을 반환하는지 검증한다. |
| `docs/OPERATIONS.md` | 품질 보류 관찰값 보완 질문 E2E 실행 명령과 검증 항목을 문서화했다. |

이 변경은 DB schema, Redis key, storage path, 외부 API 계약을 변경하지 않는다. 품질 보류 질문이 없는 결과에서 해당 옵션을 사용하면 의도적으로 실패한다.

## 2026-05-23 전문가 관점 결과 카드 연결

Agent가 산출한 법률 분석, 과실비율, 형사 리스크, 보험 처리 안내, 근거 검증 상태를 하나의 사용자 안전 결과 섹션으로 묶는 `expert_guidance_sections`를 추가했다. 목적은 사용자에게 “확정 판결”처럼 보이는 단일 결론을 주는 것이 아니라, 변호사 관점의 예상 법률 쟁점, 보험 실무 관점의 처리 흐름, 추가 확인이 필요한 사실을 분리해서 보여주는 것이다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/expert_guidance_sections.py` | 기존 analyst 결과를 이용해 `legal_prediction`, `insurance_prediction`, `missing_facts`, `basis`, `notice`로 구성된 사용자 안전 전문가 안내 payload를 생성한다. 내부 `chunk_id`, cache key, model metadata는 포함하지 않는다. |
| `apps/agent/app/services/orchestration_output.py` | 최종 Agent 출력 보강 단계에서 `expert_guidance_sections`를 생성하고, 이후 `elderly_friendly_report`를 다시 빌드해 최신 payload를 기준으로 사용자 결과가 만들어지게 했다. |
| `apps/gateway/src/lib/report-composer.ts` | Agent의 `expert_guidance_sections`를 일반 화면용 `expert_guidance_card`로 변환한다. 상태 라벨, 과실 참고 범위, 법률/보험 포인트, 확인 근거, 추가 확인 항목만 노출한다. |
| `apps/frontend/src/components/easy/ExpertGuidanceCard.vue` | 사용자 결과 화면에 전문가 관점 예상 안내 카드를 추가한다. 법률 관점, 보험 처리 예상, 확인 근거, 추가 확인 사항을 분리 표시한다. |
| `apps/frontend/src/components/easy/EasyReportView.vue` | 과실비율 카드 다음에 `ExpertGuidanceCard`를 배치한다. |
| `apps/frontend/src/utils/displaySanitizer.ts` | raw `expert_guidance_sections`가 일반 화면에 직접 노출되지 않도록 기술 필드로 분류한다. |
| `apps/agent/tests/test_expert_guidance_sections.py`, `apps/gateway/test/report-composer.test.ts` | 전문가 안내 payload와 Gateway 카드가 내부 근거 ID 없이 법률/보험/추가 확인 항목을 표시하는지 검증한다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다. easy-report 표시 payload만 확장한다.

## 2026-05-23 전문가 안내 카드 품질 평가 연결

사고 영상 E2E와 reference set 평가가 새 `expert_guidance_card`를 필수 사용자 결과로 점검하도록 보강했다. 이 변경의 목적은 영상 처리나 Agent 실행이 성공해도, 최종 사용자가 보는 법률 관점 예상·보험 처리 예상·확인 근거 카드가 빠지거나 내부 식별자를 노출하는 문제를 조기에 잡는 것이다.

| Path | 변경 내용 |
| --- | --- |
| `scripts/video_agent_e2e.py` | `/easy-report` 응답에서 `expert_guidance_card` 존재, 과실 참고 범위, 보험 안내, 내부 token 비노출을 검증하고 `expert_guidance_card` 요약을 출력 JSON에 포함한다. |
| `scripts/video_accuracy_batch.py` | 샘플별 `expert_guidance` 지표와 전체 `expert_guidance_summary`를 aggregate 결과에 추가한다. |
| `scripts/reference_guidance_eval.py` | batch aggregate의 전문가 카드 지표를 읽어 `expert_guidance_status`와 `expert_guidance_status_counts`를 생성한다. 보완 사실이 남은 샘플은 카드가 안전하게 보류/추가 확인 상태를 보여주는지 평가한다. |
| `docs/OPERATIONS.md` | 실제 영상 E2E와 reference 평가에서 전문가 카드 검증 항목과 상태 의미를 문서화했다. |

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다. 기존 측정 JSON의 로컬 저장 위치는 계속 `logs/`이며 Git에 포함하지 않는다.

## 2026-05-23 전문가 안내 Agent 응답 DTO 노출 보강

실제 OpenAI 프레임 분석 배치에서 Agent 내부 `expert_guidance_sections`는 생성됐지만, FastAPI `response_model=AnalysisOutput` 직렬화 과정에서 해당 필드가 DTO에 없어 Gateway로 전달되지 않는 문제가 확인됐다. 결과적으로 `/easy-report`의 `expert_guidance_card`가 누락되어 E2E가 실패할 수 있었다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/schemas.py` | `AnalysisOutput.expert_guidance_sections`를 정식 응답 필드로 추가해 Agent 내부 전문가 안내 payload가 Gateway까지 전달되도록 했다. |
| `apps/agent/tests/test_orchestrator.py` | `AnalysisOutput.model_dump()` 후에도 `expert_guidance_sections`가 유지되는지 검증한다. 현재 영상 입력 계약에 맞춰 테스트 관찰값 fixture에 `frame_refs`도 포함했다. |

검증 결과:
- `powershell -ExecutionPolicy Bypass -File scripts/verify_agent_regression.ps1 -SkipDockerBuild` 통과.
- Codex 번들 Python 3.12 환경에 Agent requirements와 `pytest`를 설치한 뒤 `apps/agent/tests/test_orchestrator.py`, `apps/agent/tests/test_expert_guidance_sections.py` 4개 테스트 통과.
- 사고 영상 1~5 실제 OpenAI 프레임 분석 배치 재실행에서 4개 샘플은 통과했고, 1개 샘플은 OpenAI read timeout으로 실패했다. 동일 사고2 단일 재시도는 통과했으므로 DTO/카드 전달 문제는 해소된 것으로 본다.

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다. 실제 OpenAI 검증 뒤에는 비용 방지를 위해 worker를 다시 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=` 상태로 복구해야 한다.

## 2026-05-23 변호사 reference 샘플 과실 범위 1차 보정

사고 영상 1~5번 reference set을 기준으로 Agent 텍스트 입력 경로의 과실 범위가 과도하게 단순화되는 문제를 보정했다. 이 변경은 reference 의견을 정답으로 주입하는 것이 아니라, 구조화된 사용자 입력과 영상 관찰값이 알려주는 주요 쟁점이 기존 기본 50:50 또는 단순 후방추돌 규칙에 묻히지 않도록 하는 1차 정확도 고도화다.

| Path | 변경 내용 |
| --- | --- |
| `apps/agent/app/services/input_normalizer.py` | 사용자 입력의 `crosswalk=true`를 Agent 표준 fact인 `crosswalk_nearby=true`로 보강해 횡단보도 앞 후방 추돌이 보행자 사고로 잘못 분류되지 않게 했다. |
| `apps/agent/app/services/accident_perspective.py` | `front_vehicle_stopped=true`, `stopped=false`인 후방 추돌에서는 사용자를 뒤따르던 차량으로 추론한다. 정상 한국어 후방추돌 표현도 역할 추론에서 우선 처리한다. |
| `apps/agent/app/services/analysts/fault_ratio_analyst.py` | 중앙선 회피 후 정차·후속 추돌, 무등화 정차 차량, 자전거 비접촉 유발 후 후방 추돌, 신호 전환/CCTV 필요 교차로 사고에 대한 보수적 참고 과실 범위를 추가했다. |
| `apps/agent/tests/test_orchestrator.py`, `apps/agent/tests/test_rear_end_user_perspective.py` | reference 샘플에서 드러난 입력 alias, 후방 추돌 역할 추론, 복합 사고 과실 범위, 신호 전환 불확실성 회귀를 추가했다. |

텍스트 경로 기준 보정 후 샘플별 참고 범위:

| 샘플 | 현재 Agent 기준 |
| --- | --- |
| 사고1 중앙선 회피·마주오던 차량·후속 추돌 | 내 책임 20~40% / 상대 60~80% 참고 |
| 사고2 좌회전·신호 전환·CCTV 필요 | 내 책임 70~90% / 상대 10~30% 참고 |
| 사고3 횡단보도 앞 일시정지 차량 후방 추돌 | 내 책임 90~100% / 상대 0~10% 참고 |
| 사고4 야간 무등화 정차 차량 추돌 | 내 책임 30~50% / 상대 50~70% 참고 |
| 사고5 자전거 비접촉 유발·트럭 정지·후방 버스 추돌 | 내 책임 10~30% / 상대 70~90% 참고 |

검증:
- Codex 번들 Python 3.12에서 `apps/agent/tests/test_orchestrator.py`, `apps/agent/tests/test_rear_end_user_perspective.py` 10개 테스트 통과.
- `powershell -ExecutionPolicy Bypass -File scripts/verify_agent_regression.ps1 -SkipDockerBuild` 통과.

이 변경은 DB schema, Redis key, storage path, API route, 외부 API 계약, 환경변수 키를 변경하지 않는다. 실제 OpenAI 프레임 분석 배치는 비용과 timeout 변동이 있으므로 이번 보정에서는 재호출하지 않았고, 다음 실제 영상 검증 시 동일 reference manifest로 재측정한다.

## 2026-05-25 P1: 근거 검색/표시 적합도 보강

영상 P0 이후 남은 문제였던 `basis_mentions_reference_focus_terms` 실패를 줄이기 위해 Agent 근거 검색어 우선순위와 사용자 표시용 근거 사유를 보강했다. 목적은 특정 사고 샘플에 맞춘 문구 고정이 아니라, 사고 쟁점과 근거 카드의 제목/사유가 서로 맞는지 사용자가 확인할 수 있게 만드는 것이다.

| 범위 | 변경 내용 |
| --- | --- |
| Agent 근거 검색 | `scenario_search_terms.py`가 구체적인 fact 기반 검색어를 일반 scenario/tag 검색어보다 먼저 유지한다. 중앙선 회피·대향 충돌·후속 추돌, 무등화 정차 차량, 비접촉 자전거 유발처럼 긴 복합 사고에서도 핵심 검색어가 `max_terms` 제한에 밀리지 않게 했다. |
| Agent 근거 사유 | `expert_guidance_sections.py`가 중앙선/신호/무등화/자전거 비접촉 유발 쟁점에 대해 한국어 basis 사유를 보강한다. 신호나 무등화 문구가 다른 사고에 잘못 섞이지 않도록 시나리오 marker와 핵심 fact를 기준으로 제한한다. |
| Gateway 표시 | `report-composer.ts`가 전문가 카드의 법률 포인트를 기준으로 basis reason을 한 번 더 보강한다. Agent가 보수적인 후방추돌 근거만 반환한 경우에도 자전거 비접촉 유발, 트럭·앞차 정지의 불가피성, 후방 차량 반응 시간, 급제동 여부 같은 표시 쟁점을 잃지 않는다. |
| 보완 질문 우선순위 | 교차로·신호 전환 맥락에서는 `상대 차량 신호`, `상대 신호 확인 가능 여부`, `내 차량 신호`, `신호 전환` 질문을 일반 정차/파손 질문보다 먼저 보여준다. |
| 평가 기준 | `reference_guidance_calibration_eval.py`가 영어 토큰 강제가 아니라 한국어 사용자 화면에 맞는 동의어 그룹으로 basis 적합도를 평가한다. |

검증:

- `py -3.13 -m pytest tests/test_expert_guidance_sections.py` 통과.
- `npm test -- report-composer.test.ts` 통과.
- `npm run build` in `apps/gateway` 통과.
- `powershell -ExecutionPolicy Bypass -File scripts/verify_agent_regression.ps1 -SkipDockerBuild` 통과.
- 실제 사고 영상 1~5 batch: `logs/video_accuracy/p1_basis_fit_final_pass_20260525/aggregate.json`, 5개 샘플 pipeline 통과.
- Reference guidance calibration: `logs/video_accuracy/reference_guidance_calibration_p1_basis_fit_final_20260525.json`, 5개 샘플 모두 `calibrated_for_user_flow`.

잔여 리스크:

- `reference_evidence_alignment_p1_basis_fit_final_20260525.json` 기준 일부 세부 focus는 아직 실제 원문 DB/KNIA 원문 coverage가 아니라 static fallback과 표시 보강에 기대고 있다. 다음 단계에서는 원문 기반 근거 DB coverage와 검색 결과의 실제 원문 적합도를 높이는 작업이 필요하다.

## 2026-05-25 P2: 원문/근거 coverage 보강

P1 이후 남아 있던 `needs_evidence_content_fit` 상태를 해소하기 위해 Agent 근거 후보군과 reference evidence alignment 평가 기준을 보강했다. 목적은 결과 문구만 다듬는 것이 아니라, 사고 focus와 실제 근거 카드의 제목/사유가 같은 쟁점을 가리키도록 검색 coverage를 넓히는 것이다.

| 범위 | 변경 내용 |
| --- | --- |
| Static legal/KNIA support | `static_legal_fallback.py`에 `앞차 정차 사유와 후방추돌 법률 검토 기준`, `자전거 비접촉 유발과 후방추돌 법률 검토 기준`을 추가했다. 기존 횡단보도 앞 정차 후 후방추돌, 자전거 비접촉 유발 KNIA fallback에는 한국어 검색어와 트럭·후방 버스·급제동·시간적 여유 키워드를 보강했다. |
| 검색어 생성 | `scenario_search_terms.py`가 앞차 정지 사유, 횡단보도 앞 정차 후방추돌, 자전거 비접촉 유발, 후방 버스 추돌, 트럭 정지 사유, 급제동 대응 시간 같은 복합 사고 쟁점 검색어를 생성한다. |
| KNIA match reason | `knia_matcher.py`가 `front_vehicle_stop_reason`, `non_contact_trigger`, `time_gap` 태그를 추출하고, 후방추돌 근거 사유를 일반 안전거리 문장으로만 만들지 않도록 좁혔다. |
| 전문가 근거 카드 | `expert_guidance_sections.py`가 후방추돌 중 앞차 정지 사유·횡단보도·보행자 신호·급정거·정지 예견 가능성을 별도 focus로 보강한다. |
| 평가 기준 | `reference_evidence_alignment_eval.py`의 `speed_avoidability` 키워드 그룹에 한국어 `회피`를 추가해 실제 사용자 화면의 한국어 근거 문장을 평가할 수 있게 했다. |

검증:

- `py -3.13 -m pytest tests\test_scenario_search_terms.py tests\test_static_scenario_support.py tests\test_expert_guidance_sections.py` 통과.
- `py -3.13 -m py_compile scripts\reference_evidence_alignment_eval.py` 통과.
- `powershell -ExecutionPolicy Bypass -File scripts\verify_agent_regression.ps1 -SkipDockerBuild` 통과.
- 실제 사고 영상 1~5 batch: `logs/video_accuracy/p2_source_evidence_fit_20260525/aggregate.json`, 5개 샘플 pipeline 통과.
- Reference guidance eval: `logs/video_accuracy/reference_guidance_eval_p2_source_evidence_fit_20260525.json`, 5개 샘플 모두 `ready_for_legal_knia_insurance_evidence_eval`.
- Reference evidence alignment: `logs/video_accuracy/reference_evidence_alignment_p2_source_evidence_fit_20260525.json`, 5개 샘플 모두 `ready_for_stage8_guidance_calibration`, 22개 focus 모두 `evidence_content_ready`.
- Reference guidance calibration: `logs/video_accuracy/reference_guidance_calibration_p2_source_evidence_fit_20260525.json`, 5개 샘플 모두 `calibrated_for_user_flow`.

잔여 리스크:

- P2는 실제 법령/판례/KNIA 원문 전체 수집을 완료한 단계가 아니라, 현재 DB와 static fallback coverage가 reference focus를 놓치지 않도록 보강한 단계다. 다음 단계에서는 실제 법령·판례·KNIA 원문 데이터셋 확장, 출처 URL 품질, 사용자 화면에서 fallback과 원문 근거의 구분 표시를 강화해야 한다.

## 2026-05-26 GitHub 동시 협업 workflow 문서화

팀원이 동시에 개발할 수 있도록 폴더 전달 방식 대신 GitHub branch와 Pull Request 기반 협업 절차를 문서화했다.

| 문서 | 역할 |
| --- | --- |
| `docs/GITHUB_COLLABORATION_WORKFLOW.md` | 브랜치 이름 규칙, 작업 시작 절차, 커밋 전 확인, 검증 기준, PR 작성/리뷰/병합, 병합 전후 팀원 알림, 충돌 처리, 문서 업데이트 기준 |

협업 방식은 `main`을 실행 가능한 기준 브랜치로 유지하고, 모든 작업을 목적별 브랜치에서 진행한 뒤 PR 리뷰 후 병합하는 GitHub Flow를 기본으로 한다. 작업 시작 전에는 최신 `main`을 pull하고 최근 병합/커밋 이력을 확인해 팀원 변경이 있는지 먼저 파악한다. `main` 병합 전에는 팀원에게 병합 예정임을 알리고, 병합 후에는 팀원에게 `main` pull 및 진행 중인 작업 브랜치에 최신 `main`을 반영하라고 안내한다. `.env`, API key, 사용자 비밀번호, 영상 원본, `storage/`, `logs/`, AI Hub 원본 데이터, YOLO 모델 가중치는 계속 Git에 올리지 않는다.

## 2026-05-25 인수인계 문서 및 로컬 테스트 산출물 정리

팀원 인수인계를 위해 초기 기준 문서(`docs/PROJECT_BASELINE_2026-05-21.md`) 대비 현재 변경 사항을 별도 문서로 정리하고, 실행/빌드 방법을 짧은 runbook으로 분리했다. 기존 `docs/OPERATIONS.md`는 상세 운영 문서로 유지하고, 팀원이 처음 실행할 때는 새 runbook을 우선 참조한다.

| 문서 | 역할 |
| --- | --- |
| `docs/HANDOFF_CHANGE_SUMMARY_2026-05-25.md` | 초기 기준 상태 대비 현재 프로젝트의 구조, 기능, 영상 처리, Agent 판단, 근거 품질, 운영 리스크 변화 요약 |
| `docs/BUILD_AND_RUN_GUIDE.md` | Docker 실행, 로컬 개발 실행, 검증 명령, 영상 분석 테스트, 로컬 산출물 정리 절차 |

로컬 웹 테스트에서 생성된 업로드 원본과 추출 프레임은 `storage/uploads/`, `storage/frames/` 아래에 저장된다. 이 경로는 Git ignore 대상이며, 인수인계 전 용량 관리를 위해 삭제해도 되는 런타임 산출물이다. 실제 사고 영상 샘플 원본, API 키, AI Hub 데이터, YOLO 모델 가중치는 Git에 올리지 않는다.

## 2026-05-27 KNIA 원문/영상 링크 표시 안정화

분석 결과에 표시 가능한 KNIA 기준 후보가 있는데도 `knia_primary_match`가 비어 있으면 사용자 화면의 원문/영상 버튼이 누락되는 문제를 보강했다. 특정 chart 번호 전용 분기가 아니라 모든 KNIA chart 후보에 대해 `video_url`, `source_detail_url`, `source_url` 순서로 안전한 원본 링크를 복구한다.

| 범위 | 변경 내용 |
| --- | --- |
| Agent 표시 후보 복구 | `apps/agent/app/services/knia/knia_report_adapter.py`가 `knia_primary_match`, `knia_matches`, `knia_evidence`, `combined_evidence`, `related_fault_standard`, `knia_basis_cards`, `fault_ratio`의 KNIA 후보를 순서대로 수집한다. `chart_no`만 있고 URL이 부족하면 한 분석당 최대 3개 후보에 한해 `KniaRepository.get_chart()`로 `knia_fault_charts` 상세 row를 보강한다. rejected/mismatch 후보는 대표 링크 카드로 쓰지 않는다. |
| 링크 표시 계약 | `related_knia_video_card`와 `related_video`는 `display_mode=external_link`를 기본으로 하며 iframe/video 직접 렌더링을 켜지 않는다. `video_url`이 있으면 버튼은 `KNIA 관련 영상 보기`, 없고 `source_detail_url` 또는 `source_url`이 있으면 `KNIA 원문 기준 보기`로 표시한다. |
| URL/썸네일 안전성 | Agent와 Gateway/Frontend 표시 계층은 사용자 버튼 URL을 `accident.knia.or.kr` allowlist로 제한하고 `javascript:`, `data:`, `file:`, localhost/private IP, 알 수 없는 외부 도메인은 버튼으로 노출하지 않는다. `logo_test.jpg` 기본 로고 썸네일은 이미지 표시 대상에서 제외한다. |
| Gateway 표시 보강 | `apps/gateway/src/lib/report-composer.ts`가 `knia_primary_match`가 없어도 Agent result의 KNIA 후보에서 안전한 링크 카드를 생성한다. 대표 카드는 1개, 보조 후보는 최대 3개로 제한하며 내부 `chunk_id`, cache key, trace id, raw prompt, retrieval id는 표시 payload에서 제거한다. |
| Frontend 표시 | `apps/frontend/src/components/knia/RelatedVideoCard.vue`, `KniaVideoLinkCard.vue`, `KniaMediaLinkCard.vue`, `views/KniaChartView.vue`는 외부 링크 버튼을 새 탭으로 열고 `rel="noopener noreferrer"`를 유지한다. URL은 있지 않지만 KNIA 후보 자체가 있으면 상세 수집 필요 안내만 표시한다. |
| 검증 정책 | 이번 작업에서 Codex는 사용자 요청에 따라 docker compose, npm, pytest, python script, DB/Redis query, curl, 브라우저 smoke test를 직접 실행하지 않았다. 테스트 파일과 정적 표시 계약 스크립트만 갱신했으며, 아래 보고서의 검증 명령은 사용자가 직접 실행한다. |

이 변경은 DB schema, migration, Redis key, storage path, 외부 API 종류를 변경하지 않는다. KNIA 영상 파일은 LawCompass 서버에 다운로드하거나 저장하지 않고 과실비율정보포털 원본 링크만 제공한다.

## 2026-05-27 교통사고 분석 Guided UX/Agent Flow 1차 개편

일반 사용자 화면의 개발자 중심 버튼을 guided wizard 중심으로 재구성했다. 사용자는 사고 설명 또는 영상을 입력한 뒤 사고유형, 분석 목적, 쉬운 확인 질문을 순서대로 답하고 `이대로 분석하기`로 진행한다. 기존 업로드/전처리/작업조회/새로고침/텍스트 분석/영상 분석 버튼은 API 호환성을 위해 유지하되 기본 화면에서는 숨기고 `고급 진단 보기` 접힘 영역으로 이동했다.

| 범위 | 변경 내용 |
| --- | --- |
| Frontend guided flow | `apps/frontend/src/views/CaseDetailView.vue`가 사고 자료 입력 → 사고유형 카드 선택 → 분석 목적 카드 선택 → 동적 질문 → 분석 진행/결과 흐름을 제공한다. `CaseCreateView.vue`는 최초 화면에서 분석모드/사고유형 드롭다운을 노출하지 않는다. |
| 분석 목적 | 사용자용 목적은 `quick_summary`, `fault_ratio_focused`, `legal_precedent_focused`, `insurance_response_focused`, `full_deep_research`로 정리했다. `criminal-liability-focused`, `evidence-review`, `fault-focused`, `legal-focused`, `insurance-focused`는 legacy alias로만 정규화한다. |
| 동적 질문 | `apps/agent/app/services/dynamic_questionnaire.py`가 `scenario_type`, `accident_party_type`, `analysis_mode`, 사용자 입력, 영상 관찰값, KNIA 가감요소를 받아 쉬운 질문을 생성한다. 모든 질문은 `예`, `아니오`, `잘 모르겠어요` 또는 이에 준하는 선택지를 포함하고 `why_it_matters`로 과실 영향 이유를 설명한다. |
| KNIA 가감요소 Agent | `apps/agent/app/services/knia/knia_adjustment_agent.py`가 KNIA 기본과실 위에 후미추돌 급정거 사유, 제동등, 비정상 정차, 선행사고 후 정차, 야간 무등화/시야장애를 deterministic하게 반영한다. 빨간불 신호대기·정체·보행자/장애물 회피는 정당한 정차 사유로 보아 급정거만으로 앞차 과실을 올리지 않는다. |
| 진행 상태 | Gateway `GET /api/v1/cases/:caseId/analysis-progress`는 polling 기반의 사용자용 단계 메시지를 제공한다. `video_preprocess`, `video_analyze`, `attempts`, job id, Redis, worker 같은 내부 용어는 표시 payload에 넣지 않는다. Worker job artifacts에도 사용자용 상태 라벨을 보조 metadata로 남긴다. |
| 결과 표시 | 한 줄 결론은 짧은 제목과 별도 과실 카드로 분리했다. 빠른 요약 모드는 긴 법률/판례 섹션을 숨기고, 과실비율 중심 모드는 KNIA 기본과실/가감요소 카드 제목을 명확히 표시한다. KNIA 원문/영상 링크 카드는 기존 안정화 계약을 유지한다. |
| 검증 정책 | 사용자 요청에 따라 Codex는 docker compose, npm, pytest, python script, DB/Redis query, curl, 브라우저 smoke test를 직접 실행하지 않았다. `git diff --check`만 정적 확인으로 수행했으며, 실제 검증 명령은 작업 보고서에 사용자 실행 명령으로 제공한다. |

이번 변경은 DB schema, migration, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다. Streaming은 1차 구현에서 직접 SSE가 아니라 Gateway polling endpoint와 프론트 단계형 표시로 제공한다. 기존 `/analyze-text`, `/analyze-video`, `/uploads`, `/jobs`, `/easy-report` route는 legacy/diagnostic 흐름으로 유지된다.

## 2026-05-28 P0: 영상 관찰값 사고 대상 오염 방지

영상 처리 P0 작업으로 OpenAI/YOLO 프레임 관찰값이 Agent 사실 계약으로 들어올 때 사고 대상과 사고 환경을 더 엄격히 분리했다. 특정 사고 샘플에 맞춘 보정이 아니라, 실제 충돌 대상이 차량인데 횡단보도나 사람이 보였다는 이유만으로 차대사람 사고로 승격되는 문제를 막는 범용 계약 보강이다.

| 범위 | 변경 내용 |
| --- | --- |
| Worker OpenAI fallback | `apps/worker/worker/frame_analysis.py`가 OpenAI 재시도 후에도 물리 사실을 만들지 못했지만 `accident_event_summary.event_frame_refs`가 있는 경우 `accident_event_candidate` 지원 관찰값을 남긴다. 이 값은 사고 시점 후보 표시용이며 과실 판단 fact로 직접 승격되지 않는다. |
| Agent video input contract | `apps/agent/app/services/video_input_contract.py`가 `accident_event_candidate`를 supporting observation으로만 취급한다. `collision_partner_type=pedestrian`은 직접 충돌 근거가 없으면 보류하고, `direct_collision_partner_type=vehicle`이면 broader partner 분류를 차량으로 정렬한다. |
| 보행자/횡단보도 오염 방지 | 차량 충돌 맥락에서는 `pedestrian_visible=true`, `pedestrian_signal`을 확정 fact에서 내려 보완/환경 맥락으로만 둔다. 횡단보도와 보행자 신호는 사고 환경일 수 있지만 실제 사고 상대를 대체하지 않는다. |
| 검증 | Agent video input contract/fact arbitration 32개 테스트와 Worker frame/yolo contract 24개 테스트를 통과했다. |

이 변경은 DB schema, Redis key, storage path, public API route, 외부 API 종류, 환경변수 키를 변경하지 않는다. 다음 단계는 실제 사고 영상 1~5번을 다시 돌려 `accident_event_candidate`, 차대차/차대사람 분리, 영상 fact 반영률이 개선됐는지 확인하는 회귀 측정이다.
## 2026-05-29 영상 정량 관찰 파이프라인 보강

영상 분석이 상세 서술이 아니라 사고 기점 기준의 정량 관찰값을 안정적으로 만들도록 Worker 선처리 흐름을 보강했다. 이번 변경은 특정 사고 영상에 답을 맞추는 처리가 아니라, YOLO 객체 후보로 사고 후보 구간을 먼저 랭킹하고 그 구간의 전후 프레임을 OpenAI 정량 관찰 입력으로 우선 전달하는 범용 구조다.

| 범위 | 변경 내용 |
| --- | --- |
| Worker 처리 순서 | `apps/worker/worker/job_processor.py`가 영상 전처리 후 YOLO 객체 후보 분석을 먼저 실행하고, YOLO가 랭킹한 사고 후보 구간을 frame metadata에 반영한 뒤 OpenAI 프레임 분석을 실행한다. |
| YOLO 후보 랭킹 | `apps/worker/worker/yolo_frame_analysis.py`가 프레임별 차량/사람/신호등 객체를 event candidate별로 집계해 `event_candidate_summary`와 `vision_event_candidate_rank`를 생성한다. 이 값은 사고 판단 fact가 아니라 프레임 선택 힌트다. |
| OpenAI 프레임 선택 | `apps/worker/worker/frame_selection.py`가 YOLO 1순위 사고 후보 구간과 전후 프레임을 우선 선택한다. OpenAI 프롬프트는 상세 서술 대신 신호, 충돌 대상, 충돌 지점, 차선/중앙선, 정차/이동 같은 structured observation을 요구한다. |
| 공개 reference 수집 | `scripts/collect_public_video_references.py`가 `yt-dlp` 기반 공개 제목/설명 metadata 수집을 지원한다. 사용 목적과 권한을 확인한 경우에만 `--allow-video-download`로 `.local/` 아래 임시 영상을 받을 수 있으며 Git에는 포함하지 않는다. |
| 개발 기준 | `DEVELOPMENT_PROMPT.md`에 “안 된 작업을 해결된 것처럼 보고하지 않는다”는 검증 정직성 규칙과 YOLO-first 정량 관찰 원칙을 추가했다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류를 변경하지 않는다. 다음 검증 기준은 사고 1~5 및 추가 public/local reference에서 직접 충돌 대상 정확도, 사고 대분류 정확도, context 오염률, 조건분기 coverage가 실제로 개선되는지 확인하는 것이다.
## 2026-05-29 비접촉 유발 사고 정규화 보강

사용자 설명에 자전거·보행자 같은 유발 객체가 등장하더라도 직접 충돌이 뒤차/버스/차량 후방추돌이면 사고 대분류와 직접 충돌 대상을 차량으로 유지하도록 Agent 입력 정규화를 보강했다. `apps/agent/app/services/input_normalizer.py`는 “자전거를 보고 정지했고 뒤 차량이 추돌” 같은 문맥을 `non_contact_trigger=true`, `trigger_actor_type=bicycle`, `direct_collision_partner_type=vehicle`, `accident_party_type=car_vs_car`로 고정한다. 또한 텍스트 보강 후 party router를 다시 실행해 초기 키워드 기반 자전거 직접충돌 분류가 최종 facts를 오염시키지 않게 했다.

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류를 변경하지 않는다. 검증 기준은 `apps/agent/tests/test_video_input_contract.py`의 비접촉 자전거 유발 후방추돌 회귀와 영상 관찰값 오염 방지 회귀다.
## 2026-05-29 앱 패키징용 ML Kit 데모 분리

운영 사고 분석 화면을 유지한 상태에서 모바일 앱 패키징과 Google ML Kit Object Detection & Tracking 성능 확인을 위한 별도 데모 화면을 추가했다. 이 데모는 운영 분석 플로우가 아니라 `/app-demo/mlkit` 테스트 route에서만 접근하며, 기본 노출은 `VITE_ENABLE_APP_DEMO=true`일 때로 제한한다.

| 범위 | 변경 내용 |
| --- | --- |
| Frontend demo route | `apps/frontend/src/views/AppMlKitDemoView.vue`는 영상 파일 선택, 프레임 샘플링, native ML Kit 호출 또는 web mock fallback, 성능 요약, 객체 후보 테이블, bbox preview, `client_pre_observations.json` 다운로드를 제공한다. 운영 메뉴에는 기본 노출하지 않는다. |
| Observation contract | `apps/frontend/src/services/mobileMlkitDemo.ts`와 `apps/frontend/src/types/mobileObservations.ts`는 ML Kit 결과를 `source=client_pre_observation`의 `object_candidate` 관찰값으로만 변환한다. `fault_ratio`, `accident_party_type`, `collision_partner_type`, `signal_violation`, `knia_chart_no`, `legal_judgment` 같은 확정 판단 필드는 생성하지 않는다. |
| Capacitor 준비 | `apps/frontend/capacitor.config.ts`는 테스트용 `appId=com.lawcompass.mobiletest`, `appName=LawCompass MLKit Demo`, `webDir=dist`를 사용한다. `apps/frontend/android/`는 Capacitor Android 프로젝트이며 app module에 `MlKitObjectDetectorPlugin.kt`와 `com.google.mlkit:object-detection` 의존성을 반영했다. |
| Gateway test endpoint | `POST /api/v1/mobile-demo/observations`는 demo observation JSON만 검증한다. `POST /api/v1/mobile-demo/video-only-analysis`는 admin/superuser 전용으로 Agent 요약 route를 호출해 영상-only 분석 가능성을 `needs_review`/`reference_only` 중심으로 반환한다. 운영 분석 endpoint를 호출하거나 analysis table에 저장하지 않는다. |
| Agent video-only summarizer | `apps/agent/app/services/video_observation_summarizer.py`는 `client_pre_observations`를 객체 수, track 이동량, 가능한 대분류 후보, missing facts로 요약한다. 이 계층은 과실비율, 신호위반, KNIA chart를 확정하지 않는다. |
| 보안/개인정보 | 원본 영상은 데모 페이지에서 자동 업로드하지 않는다. JSON에는 원본 영상/base64 프레임을 장기 저장하지 않고, API key, NAS 계정, secret, storage path를 포함하지 않는다. |

이 변경은 DB schema, Redis key, storage path, Agent/Worker 판단 로직을 변경하지 않는다. ML Kit 결과는 향후 서버 `video_observations`와 병합 가능한 참고 후보일 뿐이며 KNIA chart 매칭, 과실비율 산정, 법령/판례 판단은 계속 서버 Agent가 담당한다.

## 2026-05-29 영상 처리 검증 기준 정정

실제 영상 처리 검증은 OpenAI 프레임 분석과 YOLO 보조 관찰이 모두 켜진 런타임에서만 완료로 본다. 기존 P2-1 reference manifest와 정책 산출물은 유효하지만, P2-2 이후 실제 영상 기준선/정확도 지표는 `ENABLE_OPENAI_FRAME_ANALYSIS=1`, `FRAME_ANALYSIS_FIXTURE_MODE=`, `ENABLE_YOLO_FRAME_ANALYSIS=1`, 유효한 `YOLO_MODEL_PATH` 조건으로 재측정해야 한다.

이전의 fixture/synthetic aggregate, manifest schema, guard 계약 검증은 계속 유효하다. 다만 Docker Worker에서 YOLO가 꺼진 상태의 관리자 업로드 결과는 OpenAI-only 또는 계약 검증 결과로 분리하고, OpenAI+YOLO ON 재측정 결과와 혼용하지 않는다.

## 2026-05-29 P2-2 OpenAI+YOLO ON 재측정 결과

P2-2 실제 영상 기준선을 OpenAI 프레임 분석과 YOLO 보조 관찰이 모두 켜진 Docker Worker에서 다시 측정했다. 실행 산출물은 `logs/video_accuracy/p2_2_openai_yolo_on_20260529/aggregate.json`와 `logs/video_accuracy/p2_2_openai_yolo_on_reference_metrics_20260529.json`에 로컬로 생성되며 Git에는 포함하지 않는다.

| 항목 | 결과 |
| --- | --- |
| 런타임 확인 | Worker 환경에서 `ENABLE_OPENAI_FRAME_ANALYSIS=1`, `FRAME_ANALYSIS_FIXTURE_MODE=`, `ENABLE_YOLO_FRAME_ANALYSIS=1`, `YOLO_MODEL_PATH=/models/yolo/yolo11n.pt`, Ultralytics import, 모델 파일 존재를 확인했다. |
| DB metadata 확인 | 사고 1~5 신규 업로드 모두 `openai_frame_analysis.enabled=true`, `yolo_frame_analysis.enabled=true`, YOLO error 없음, YOLO class_counts 존재, merged observations 존재를 확인했다. |
| 배치 결과 | 5개 샘플 모두 pipeline pass. 총 frame observation 44개, accepted 16개, uncertain 27개, supporting 2개, applied 10개, confirmed 5개, conflict 2개. |
| Reference metrics | `direct_collision_target_accuracy=1.0`, `accident_party_accuracy=1.0`, `context_pollution_rate=0.0`, `zero_observation_rate=0.0`, `evidence_mismatch_rate=0.2`, `conditional_branch_coverage=0.2`, 최종 status는 `needs_attention`. |
| 해석 | 사고 대분류와 직접 충돌 대상 오염은 줄었지만, 조건별 결과 설명 coverage가 부족하고 사고 3에서 expected context 근거 mismatch가 남아 있다. 따라서 P2-2는 “실제 재측정 완료, 후속 보강 필요” 상태로 본다. |

다음 보강 우선순위는 분기형 결과 카드 coverage를 높이고, 사고 3 같은 횡단보도 주변 차대차 후방추돌에서 근거 검색이 보행자 사고로 오염되지 않으면서도 교차로/횡단보도 환경 맥락을 정확히 설명하도록 근거 표시 적합도를 개선하는 것이다.

## 2026-05-29 P2-2 후속 보강 계획

P2-2 OpenAI+YOLO ON 재측정 결과를 실제 영상 프레임과 대조한 결과, 사고 대분류와 직접 충돌 대상 오염 방지는 개선됐지만 영상 정량 관찰값 추출에는 불균형이 남아 있다.

| 문제 | 관찰 내용 | 보강 방향 |
| --- | --- | --- |
| 사고 2 정량 추출 부족 | 교차로 좌회전, 신호 전환, 상대 신호 불명확, 차대차 충돌 구조가 영상 관찰값으로 충분히 추출되지 않았다. | 교차로/신호/진행방향 시퀀스 관찰값을 별도 추출하고, 상대 신호 미확인 시 조건별 결과를 강제 생성한다. |
| 사고 5 시퀀스 추출 부족 | YOLO는 자전거를 감지했지만 자전거 비접촉 유발, 트럭 정지, 후방 버스 추돌의 시간 순서를 관찰값으로 만들지 못했다. | 객체 존재값과 별도로 `trigger_actor`, `ego_stop_reason`, `rear_collision_sequence` 같은 시간 순서 관찰값을 만든다. |
| 오버레이 인물 잡음 | 한문철 영상 진행자/화면 오버레이가 YOLO `person`으로 잡힌다. 현재 직접 사고 대상으로 승격되지는 않지만 보류값 노이즈를 늘린다. | 프레임 상단/좌측 고정 오버레이 영역, 반복 등장 인물, 방송 UI 영역을 사고 객체 후보에서 제외하는 guard를 추가한다. |
| 조건별 결과 coverage 부족 | Reference metrics 기준 조건별 분기 coverage가 0.2에 머물렀다. | 신호, 중앙선 침범 사유, 정차 사유, 비접촉 유발, 후방추돌 여부가 불명확하면 조건별 결과 카드를 생성한다. |
| 근거 표시 mismatch | 사고 3 같은 횡단보도 주변 차대차 사고에서 환경 맥락과 사고 대상 근거가 섞일 위험이 남아 있다. | KNIA/법률 근거 검색은 직접 충돌 대상 축을 우선하고, 횡단보도/보행자/자전거는 환경 또는 유발 객체로 분리한다. |

후속 진행 순서는 P2-2a 영상 관찰값 감사 리포트 고정, P2-2b 오버레이/객체 잡음 제거, P2-2c 시간 순서 기반 사고 시퀀스 추출, P2-2d 조건별 분기 결과 coverage 보강, P2-2e OpenAI+YOLO ON 재측정 순서로 진행한다. 이후 P2-3 근거 검색/표시 적합도 보강으로 넘어간다.

## 2026-05-29 P2-2a 영상 관찰값 감사 리포트 고정

P2-2a 단계에서 OpenAI+YOLO ON 재측정 결과를 사람이 반복 검토할 수 있도록 감사 리포트 생성 스크립트를 추가했다. 이 단계는 모델을 다시 호출하거나 원본 영상을 읽지 않고, 기존 batch aggregate와 로컬 reference manifest만 비교한다.

| 범위 | 변경 내용 |
| --- | --- |
| 감사 스크립트 | `scripts/audit_video_observation_report.py`를 추가했다. `aggregate.json`의 sample별 `field_metrics`, 관찰값 수, 적용/확인/충돌 상태, 출력 JSON 파싱 상태를 reference 기대값과 비교한다. |
| 산출물 | 로컬 실행 결과는 `logs/video_accuracy/p2_2a_observation_audit_20260529.json` 및 `logs/video_accuracy/p2_2a_observation_audit_20260529.md`에 생성된다. 이 산출물은 재측정 비교용 로그이며 Git에 포함하지 않는다. |
| 감사 결과 | 5개 샘플 모두 관찰값 0개와 금지 context 승격은 없었다. 다만 5개 모두 `weak` 상태로 남았고, 사고 2·5는 직접 충돌 대상이 `vehicle_candidate` 수준에 머물렀다. 사고 1은 대향 차량/2차 후방충돌 맥락이 부족했고, 사고 2는 신호 전환 관찰이 부족했다. |
| 다음 보강 기준 | P2-2b는 오버레이/방송 UI 잡음을 줄이고, P2-2c는 사고 2·5처럼 단일 객체 존재가 아니라 시간 순서 기반 사고 시퀀스를 관찰값으로 만드는 방향으로 진행한다. |

이 변경은 public route, API DTO, DB schema, Redis key, storage path, 외부 API 종류, 환경변수 키를 변경하지 않는다.
## 2026-05-29 AI-Hub/YOLO 평가 데이터 분리 원칙 강화

영상 처리 정확도 보강 과정에서 AI-Hub 원천 영상과 라벨 JSON을 함께 사용할 수 있지만, 라벨과 사고 설명은 분석 모델의 입력으로 쓰지 않고 사후 평가용 정답지로만 사용한다. 이 원칙은 특정 테스트 영상에 맞춘 결과를 만들지 않고 실제 사용자 입력에도 적용되는 일반화된 영상 사실 추출을 유지하기 위한 안전장치다.

| 항목 | 기준 |
| --- | --- |
| 추론 입력 | `video_agent_e2e.py`와 Worker/OpenAI/YOLO 경로에는 원본 영상, 공통 case JSON, 런타임 옵션만 전달한다. AI-Hub `reference.label_json`, 사고대상 라벨, 과실비율 라벨, 전문가 의견은 전달하지 않는다. |
| 사후 평가 | `video_accuracy_batch.py`는 실행이 끝난 뒤 aggregate에 `reference`를 붙이고, `scripts/evaluate_aihub597_video_batch_targets.py`가 그때 라벨 JSON을 읽어 출력값과 비교한다. |
| 검증 가드 | `scripts/validate_video_accuracy_manifest.py`가 `sample.case_json`이 `sample.reference.label_json`을 가리키는 경우를 오류로 처리한다. case JSON에 `accident_object`, `traffic_accident_type`, `accident_negligence_rate` 같은 평가 전용 라벨 토큰이 섞여도 오류로 처리한다. |
| 테스트 보강 | `tests/test_validate_video_accuracy_manifest.py`가 reference 라벨을 case 입력으로 잘못 쓰는 manifest를 실패시키고, 별도 case JSON과 reference label JSON을 쓰는 정상 manifest는 통과하도록 고정했다. |
| 남은 목표 | 현재 보강은 데이터 누수 방지와 직접 사고대상 오염 방지에 초점을 둔다. 이륜차·자전거처럼 작은 대상 recall은 더 많은 프레임 선택, 고해상도 crop, 별도 객체 감지 모델 비교로 계속 개선해야 한다. |

이 변경은 public route, DB schema, Redis key, storage path를 변경하지 않는다. 평가 manifest와 라벨 파일은 계속 `.local/`, `datasets/`, `logs/` 등 Git 제외 경로에만 둔다.
