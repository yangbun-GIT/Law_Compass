# LawCompass 운영 리스크 보강 로드맵

이 문서는 정확도 고도화 이후 제품 완성 단계에서 반드시 관리해야 하는 운영 리스크를 정리한다. 목적은 기능을 새로 늘리기 전에 OpenAI 비용, 정적 fallback 의존, 원문 데이터 부족, 저장소 전환, API 사용량 제한, UI 수용성 점검을 같은 기준으로 추적하는 것이다.

기준일: 2026-05-24

## 현재 코드 책임 경계

| 영역 | 현재 책임 파일 | 현재 상태 | 남은 리스크 |
| --- | --- | --- | --- |
| OpenAI 프레임 분석 | `apps/worker/worker/frame_analysis.py` | `ENABLE_OPENAI_FRAME_ANALYSIS=0` 기본값, 최대 프레임/출력 토큰/detail/timeout 제한, Responses API `store=false`, 응답 `usage` 수집 경로 존재 | 사용량이 DB에 누적되지 않고 관리자 화면에서 비용 추이를 볼 수 없다 |
| Agent LLM 사용 정책 | `apps/agent/app/services/llm_policy.py`, `apps/agent/app/services/agent_quality_packet.py` | LLM 허용/차단/실패/fallback 이유와 `cost_observability` 요약을 남긴다 | 실제 token usage는 guarded analyst client에서 영속화하지 않는다 |
| 근거 fallback 상태 | `apps/agent/app/services/rag_client.py`, `apps/agent/app/services/evidence_source_status.py`, `apps/agent/app/services/static_legal_fallback.py` | DB/외부 API 근거가 부족할 때 정적 fallback 근거와 degraded 상태를 표시한다 | 정적 fallback이 제품 품질을 대신하면 실제 KNIA/법령/판례 원문 기반성이 약해진다 |
| KNIA/법령/판례 원문 데이터 | `apps/agent/app/services/knia/*`, `apps/agent/app/services/legal/*`, `infra/postgres/migrations/*` | KNIA/법률 KB 적재, 검색, 임베딩, fallback 보조 근거가 있다 | 현재 DB 수집량은 MVP 수준이며 사고 유형별 원문 coverage를 제품 기준으로 증명해야 한다 |
| 업로드 저장소 | `apps/gateway/src/storage/provider.ts` | 로컬 저장소가 실제 동작 경로이고 `S3StorageProvider`는 `S3_STORAGE_NOT_ENABLED`로 비활성이다 | 대용량 영상/협업/배포 환경에서는 직접 업로드와 lifecycle 관리가 필요하다 |
| API 사용량 제한 | `apps/gateway/src/main.ts`, `apps/gateway/src/lib/internal-client.ts` | Gateway rate limit, 내부 호출 timeout/retry, Agent/Worker의 bounded 실행 정책이 있다 | 사용자/기능별 quota, OpenAI 월간 예산 cap, 관리자 알림은 없다 |
| UI 수용성 | `apps/frontend/src/components/easy/*`, `apps/gateway/src/lib/report-composer.ts` | 원시 trace/token/내부 키를 숨기고 영상 상태, 보완 질문, 전문가 안내 카드를 표시한다 | 일반 사용자 기준에서 경고 문구 과다, 판단 보류 이해도, 모바일 흐름 수용성 검증이 더 필요하다 |
| 전문 CV 모델 도입 | `apps/worker/worker/frame_analysis.py`, 향후 provider adapter | 현재는 ffmpeg 프레임 추출 후 OpenAI 프레임 관찰값을 구조화한다 | 사고 대상 추적, 상대 속도/궤적, 차선/신호/객체 tracking은 전용 object detection/tracking 모델 또는 외부 Video Intelligence API가 필요하다 |

## 리스크별 제품 완성 로드맵

| 우선순위 | 리스크 | 제품 완성 기준 | 첫 구현 범위 |
| --- | --- | --- | --- |
| P0 | OpenAI token/cost 사용량 기록 부족 | 분석 1회마다 provider, model, endpoint, enabled, success, token usage, frame count, output cap, fallback reason을 안전 메타데이터로 남긴다 | `ai_usage_event` 계약을 먼저 정의하고 Worker 프레임 분석과 Agent LLM 정책 요약에 공통 필드를 맞춘다 |
| P0 | 정적 fallback 의존 과다 | 결과 화면과 관리자 진단에서 “원문 근거 충분”, “fallback 보조”, “근거 부족”이 구분된다 | `evidence_source_status` 요약을 운영 체크리스트와 평가 스크립트에 계속 연결한다 |
| P1 | 실제 KNIA/법령/판례 원문 DB 부족 | 대표 사고 유형별로 직접 관련 KNIA/법령/판례 원문 coverage를 측정하고 부족 유형을 backlog로 남긴다 | 영상 reference manifest와 별도 evidence coverage manifest를 만들어 검색 품질을 반복 측정한다 |
| P1 | API 사용량 제한 | 사용자/관리자/외부 API/OpenAI 경로별 rate limit과 timeout이 운영 문서에 정리되고, 초과 시 안전한 오류를 반환한다 | 현재 Gateway rate limit과 OpenAI bounded env를 기준으로 사용자별 quota 설계를 추가한다 |
| P1 | UI 수용성 | 일반 사용자가 “예상/참고/보류/추가 확인”의 차이를 이해하고 다음 행동을 할 수 있다 | 5개 reference 샘플 easy-report를 기준으로 문구 중복과 경고 과다 여부를 점검한다 |
| P1 | 전문 CV 모델 후보 검증 | OpenAI 프레임 VLM이 놓치는 차량/자전거/보행자/신호/차선 객체를 별도 detection/tracking 결과로 보강한다 | YOLO/ByteTrack 계열 로컬 PoC와 Roboflow 또는 Google Video Intelligence API PoC 중 하나를 provider adapter로 비교한다 |
| P2 | S3 직접 업로드 전환 | 서버 메모리를 거치지 않는 직접 업로드, signed URL, lifecycle, 접근권한, 비용 관리가 문서와 코드로 정리된다 | `S3StorageProvider` 구현 전에 local/S3 공통 metadata 계약과 migration 필요 여부를 확정한다 |
| P2 | 비용/사용량 대시보드 | 관리자 화면에서 일/월 사용량, 실패율, fallback율, OpenAI ON/OFF 상태를 볼 수 있다 | usage event 저장 이후 aggregate endpoint와 관리자 카드로 확장한다 |

## 비용/사용량 계측 첫 구현 범위

첫 구현은 “정확한 원화 비용 계산”이 아니라 “비용 산정이 가능한 안전한 사용량 원장”이다. 모델 가격은 변경될 수 있으므로 가격표를 코드에 고정하기 전에 공식 문서 확인 절차를 별도로 둔다.

### 공통 이벤트 필드 초안

| 필드 | 설명 |
| --- | --- |
| `event_version` | `ai-usage-event-v1` |
| `provider` | `openai` 또는 향후 provider 이름 |
| `service` | `worker`, `agent`, `gateway` 중 발생 서비스 |
| `endpoint` | `frame_analysis`, `traffic_law_analysis`, `fault_ratio_analysis`, `final_report` 등 내부 안전 라벨 |
| `model` | 호출 모델명. API key나 prompt는 저장하지 않는다 |
| `enabled` | 해당 경로가 켜져 있었는지 |
| `attempted` | 실제 외부 호출을 시도했는지 |
| `success` | 정상 응답을 받았는지 |
| `input_tokens`, `output_tokens`, `total_tokens` | provider 응답에 있을 때만 저장 |
| `frame_count` | 영상 프레임 분석의 선택 프레임 수 |
| `max_output_tokens` | 호출 시 설정된 출력 상한 |
| `timeout_sec` | 호출 timeout |
| `fallback_reason` | 비활성, quota, 오류, JSON 파싱 실패, 근거 부족 등 안전한 이유 |
| `case_id`, `analysis_version`, `trace_id` | 내부 추적용 식별자. 사용자 원문, 이메일, 비밀번호, API key는 저장하지 않는다 |
| `created_at` | 서버 생성 시각 |

### 단계별 적용

1. Phase A: 기존 trace와 quality packet에 위 필드명과 의미를 맞춘다. DB migration 없이도 로그와 관리자 진단에서 확인 가능해야 한다.
2. Phase B: PostgreSQL에 `ai_usage_events` 테이블을 추가해 분석 단위 사용량을 누적한다. 저장값은 safe metadata로 제한한다.
3. Phase C: 관리자 API와 관리자 테스트 화면에 일/월 집계, 실패율, fallback율, OpenAI ON/OFF 상태를 표시한다.
4. Phase D: 공식 가격표 확인 후 비용 추정 레이어를 추가한다. 가격표 변경 가능성을 고려해 모델별 단가 설정은 환경값 또는 관리 테이블로 분리한다.

## 전문 CV 모델 도입 기준

현재 OpenAI 프레임 분석은 장면 설명과 구조화 관찰값 추출에는 유용하지만, 블랙박스 사고의 핵심인 “객체가 몇 초 동안 어디서 와서 어디에 충돌했는가”를 안정적으로 추적하는 모델은 아니다. 영상 완성도를 높이려면 OpenAI VLM을 단독 판단기로 쓰지 말고, 아래 순서로 provider를 붙인다.

| 후보 | 적용 방식 | 장점 | 주의점 |
| --- | --- | --- | --- |
| Ultralytics YOLO + ByteTrack/BoT-SORT | Worker에서 로컬 또는 별도 GPU 환경으로 차량, 버스, 트럭, 자전거, 보행자, 신호등 객체를 탐지/추적하고 time offset별 track을 생성한다 | API 키 없이 PoC 가능, 긴 영상도 streaming 처리 가능, 추적 ID로 충돌 전후 움직임을 만들 수 있다 | 2GB 서버에서는 무거울 수 있어 로컬 CPU 모델은 검증용, 운영은 별도 worker/GPU 또는 경량 모델 필요. 라이선스/상용 사용 조건 확인 필요 |
| Roboflow Hosted/Inference | fine-tuned object detection 모델을 Hosted API 또는 self-hosted Inference로 호출한다 | 교통사고 객체 데이터셋을 만들고 빠르게 모델을 배포/교체할 수 있다 | Roboflow 계정/API key와 모델 학습/배포가 필요하며, 무료/요금/라이선스 조건을 확인해야 한다 |
| Google Cloud Video Intelligence | Cloud Storage 영상에 대해 object tracking을 요청하고 object label, bounding box, time offset을 받는다 | 영상 단위 object tracking API가 있어 프레임별 수동 호출보다 구조화가 쉽다 | GCP 프로젝트, Cloud Storage, service account, 과금 설정이 필요하고 교통사고 특화 판단은 별도 후처리가 필요하다 |
| NVIDIA VILA/Video VLM 계열 | 영상 또는 프레임 묶음에 대한 설명/요약을 보조 관찰값으로 받는다 | OpenAI 대체 VLM 후보로 비교 가능 | 교통사고 물리 추적 모델은 아니므로 detector/tracker 결과를 대체하지 말고 설명 보조로 사용한다 |

도입 시 Agent 입력 계약은 그대로 유지한다. 새 provider는 `video_observations`에 객체 track, time offset, confidence, frame refs를 추가하고, `fact_arbitration`이 기존 사용자 입력·OpenAI 관찰값·전문 CV 관찰값을 같은 기준으로 반영/보류/충돌 처리해야 한다. 특정 사고 샘플의 정답을 맞추기 위한 규칙은 금지하고, 사고 대상, 충돌 지점, 진행 방향, 신호 가시성, 차선/중앙선/도로 장애물 같은 보편 필드로만 승격한다.

## 운영 체크리스트

### 실제 OpenAI 프레임 분석을 켜기 전

- `scripts/validate_video_accuracy_manifest.py --require-reference --min-samples 5`로 manifest를 먼저 검증한다.
- `ENABLE_OPENAI_FRAME_ANALYSIS=1`, `FRAME_ANALYSIS_FIXTURE_MODE=`, `OPENAI_FRAME_ANALYSIS_MAX_FRAMES`, `OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS`, `OPENAI_FRAME_ANALYSIS_DETAIL`, `OPENAI_TIMEOUT_SEC`를 확인한다.
- 실행 결과는 `logs/video_accuracy/` 아래에 저장하고 Git에 포함하지 않는다.
- 테스트가 끝나면 worker를 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `FRAME_ANALYSIS_FIXTURE_MODE=`로 되돌린다.

### 근거 품질을 점검할 때

- 정적 fallback 근거가 표시되면 제품 완료로 보지 않고 “원문 DB 부족을 안전하게 보완한 상태”로 분류한다.
- KNIA/법령/판례 원문 coverage가 부족한 사고 유형은 fallback을 늘리기 전에 실제 원문 수집 또는 import 계획을 먼저 세운다.
- `reference_evidence_alignment_eval.py`와 `reference_guidance_calibration_eval.py` 결과가 통과하더라도 실제 판결 확정 표현으로 바꾸지 않는다.

### 제품 데모 또는 배포 전

- OpenAI 사용량 원장이 최소 Phase A 수준으로 남는지 확인한다.
- 사용자별/API별 rate limit과 오류 문구가 사용자 화면에서 과도하게 기술적이지 않은지 확인한다.
- 로컬 저장소를 유지할지 S3 직접 업로드로 전환할지 배포 환경 기준으로 결정한다.
- 관리자 진단 화면에는 raw prompt, raw user text, token, secret, evidence chunk id가 노출되지 않아야 한다.

## 이번 단계의 결론

현재 코드는 비용 상한, 기본 비활성화, fallback 표시, 영상 reference 평가 골격까지 갖췄다. 그러나 제품 완성 기준에서는 OpenAI token/cost 영속 기록, 실제 KNIA/법령/판례 원문 coverage, S3 전환, API quota, UI 수용성 검증이 아직 후속 개발 항목이다. 다음 실제 개발은 비용/사용량 이벤트 계약을 Phase A로 맞추는 작업부터 시작하는 것이 가장 안전하다.
## 2026-05-25 P7 운영 계측 보강

- `apps/worker/worker/frame_analysis.py`는 OpenAI Responses API 응답에 `usage`가 포함될 경우 `input_tokens`, `output_tokens`, `total_tokens`만 안전 메타데이터로 보존한다. API key, raw prompt, raw user text는 저장하지 않는다.
- `scripts/summarize_operating_risk.py`는 reference guidance/evidence/calibration 결과와 video batch 결과를 묶어 token usage, static fallback 의존, 원문 대조 필요 근거, zero-observation 영상 샘플을 제출 전 점검한다.
- 이 단계는 비용 원화 계산이나 사용자별 과금 대시보드가 아니다. 실제 가격표 기반 비용 추정과 DB 영속화는 `ai_usage_events` Phase B 이후로 둔다.
