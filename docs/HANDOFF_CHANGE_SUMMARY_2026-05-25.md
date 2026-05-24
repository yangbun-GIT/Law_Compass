# LawCompass Handoff Change Summary

작성일: 2026-05-25  
비교 기준: `docs/PROJECT_BASELINE_2026-05-21.md`  
목적: 팀원이 이어서 개발할 때 초기 기준 상태 대비 현재 프로젝트가 어디까지 바뀌었는지 빠르게 파악하기 위한 인수인계 문서입니다.

이 문서는 최초로 프로젝트를 받았을 때의 폴더 구조가 아니라, 별도로 고정해 둔 초기 기준 문서(`PROJECT_BASELINE_2026-05-21.md`)를 기준으로 변화량을 정리합니다. 실제 API 키, 사용자 비밀번호, 내부 토큰 값은 기록하지 않습니다.

## 1. 전체 변화 요약

| 영역 | 초기 기준 상태 | 현재 상태 |
| --- | --- | --- |
| 개발 기준 문서 | `DEVELOPMENT_PROMPT.md`, `SYSTEM_OVERVIEW.md`, `STACK_DECISION_REVIEW.md`, `OPERATIONS.md` 중심 | 영상 분석, Agent 판단, 근거 품질, 운영 리스크, YOLO/AI Hub 로컬 검증 문서가 추가됨 |
| Frontend | 사용자 서비스 화면, 케이스/결과/KNIA/채팅 화면 중심 | 관리자 Agent 테스트 페이지, 조건부 결과 카드, 영상 근거 반영 카드, 근거 출처 품질 표시, 보완 질문 재분석 UI 보강 |
| Gateway | 인증, 케이스, 업로드, Agent 호출, KNIA 조회 중심 | easy-report 조합 책임 보강, 재분석 route 연결, 조건부 판단/근거 품질/영상 관찰값 표시 payload 확장 |
| Agent | 텍스트/영상 요약 기반 사고 분석, KNIA/RAG/fallback 근거 사용 | 사고 대상 판별, 영상 관찰값 중재, 조건부 과실 시나리오, 근거 품질 평가, reference guidance 평가 골격 보강 |
| Worker | ffmpeg/ffprobe 기반 영상 전처리와 Agent 호출 | OpenAI 프레임 분석, bounded retry, 사고 시점 후보, YOLO optional provider adapter, token usage 안전 메타데이터 보강 |
| 데이터/근거 | PostgreSQL, Redis, KNIA/법령 KB, static fallback 혼재 | 원문 근거와 보조 fallback 근거를 구분하는 표시/평가 구조 추가. 실제 원문 DB 확장은 아직 미완료 |
| 운영 검증 | 개별 smoke/회귀 스크립트 중심 | `scripts/verify_final_readiness.ps1`로 핵심 검증 묶음 추가, 운영 리스크 요약 스크립트 추가 |

## 2. 주요 기능 변화

### 2.1 관리자 Agent 테스트 페이지

- `/admin/agent-test`에서 입력만, 영상만, 입력+영상 테스트를 분리해 확인할 수 있게 했다.
- 분석 모드는 사고 사실이 아니라 출력 강조 방식으로 취급하도록 분리했다.
- 일반 사용자가 정확한 사고 유형을 모르는 상황을 고려해 대분류와 세부 유형 입력 폭을 넓혔다.
- 서비스 화면 이동은 새 탭으로 열리도록 하여 관리자 테스트 흐름이 끊기지 않게 했다.

### 2.2 영상 처리와 관찰값 계약

- 기존 ffmpeg 대표 프레임 추출을 유지하면서 OpenAI 프레임 분석을 선택적으로 연결했다.
- 프레임 분석은 전체 제공 프레임을 시간 순서로 보고 실제 사고 시점 후보를 찾도록 프롬프트와 메타데이터를 보강했다.
- 관찰값이 0개인데 프레임은 충분한 경우 1회 bounded retry를 수행한다.
- timeout 같은 일시 오류에서도 조건부 1회 retry를 수행한다.
- 분석 결과에는 사고 판단에 바로 쓰는 fact와, 확인이 필요한 후보 관찰값을 분리한다.
- YOLO는 사고 판단 모델이 아니라 차량, 사람, 신호등 등 객체 위치를 보조로 뽑는 optional provider adapter로 연결했다.
- 기본 운영값은 `ENABLE_OPENAI_FRAME_ANALYSIS=0`, `ENABLE_YOLO_FRAME_ANALYSIS=0`이다.

### 2.3 사고 판단 구조

- 횡단보도나 보행자가 보인다는 이유만으로 차대사람 사고로 승격하지 않도록 했다.
- 실제 충돌 대상과 사고 유발 객체를 분리했다.
- 교차로 좌회전/직진 사고처럼 상대 신호가 보이지 않는 경우, 단일 결론 대신 조건부 결과를 표시하도록 했다.
- 중앙선 침범, 도로 장애물, 불법 주정차, 대향차 충돌, 후속 추돌을 분리해 판단하도록 보강했다.
- 후방추돌, 우회전 중 앞차 정차, 무등화 정차 차량, 비접촉 유발자 등 반복적으로 문제가 된 사고군에 대해 일반화된 판단 규칙을 추가했다.

### 2.4 근거 검색과 표시 품질

- 법령/KNIA/판례 근거 카드에 `source_quality`, `source_quality_label`, `needs_original_source_review`, `source_url` 같은 출처 품질 정보를 붙인다.
- static fallback 근거는 원문 근거처럼 보이지 않게 `보조 참고 근거`로 구분한다.
- 원문 URL이 있는 근거는 원문 보기 버튼을 제공한다.
- 차대차 사고에서 보행자 기준, 어린이보호구역 기준, 차대사람 기준이 대표 근거로 섞이지 않도록 필터를 강화했다.
- KNIA 관련 영상/썸네일은 깨진 이미지를 보여주지 않고 원본 사이트 링크 중심으로 정리했다.

### 2.5 운영 검증과 리스크 관리

- `docs/OPERATING_RISK_ROADMAP.md`로 OpenAI 비용, static fallback 의존, 원문 DB 부족, S3 전환, API 사용량 제한, UI 수용성 점검을 제품 완성 로드맵으로 분리했다.
- OpenAI 응답 usage가 제공될 경우 token usage 숫자만 안전 메타데이터로 남긴다.
- `scripts/summarize_operating_risk.py`로 batch 결과와 reference 평가 결과를 묶어 운영 리스크를 요약한다.
- `scripts/verify_final_readiness.ps1`로 핵심 검증을 한 번에 재현할 수 있게 했다.

## 3. 새로 보강된 주요 파일

| 경로 | 역할 |
| --- | --- |
| `apps/frontend/public/admin/agent-test.html` | 독립 관리자 Agent 테스트 페이지 |
| `apps/frontend/src/components/easy/*` | 쉬운 결과, 보완 질문, 조건부 결과, 영상 근거 반영 UI |
| `apps/gateway/src/lib/report-composer.ts` | Agent 결과를 사용자 표시용 easy-report로 조합 |
| `apps/agent/app/services/video_input_contract.py` | Worker 영상 관찰값을 Agent fact 후보로 정규화 |
| `apps/agent/app/services/fact_arbitration.py` | 사용자 입력과 영상 관찰값의 반영/보류/충돌 중재 |
| `apps/agent/app/services/scenario_classifier.py` | 사고 대분류와 세부 시나리오 분류 |
| `apps/agent/app/services/analysts/fault_ratio_analyst.py` | 과실비율 참고 추정과 조건부 결과 생성 |
| `apps/agent/app/services/expert_guidance_sections.py` | 전문가 안내, 근거 품질, 원문/보조 근거 구분 |
| `apps/worker/worker/frame_analysis.py` | OpenAI 프레임 분석, retry, 사고 시점 후보 메타데이터 |
| `apps/worker/worker/yolo_frame_analysis.py` | optional YOLO 객체 관찰 provider adapter |
| `scripts/verify_final_readiness.ps1` | 최종 준비 상태 검증 묶음 |
| `scripts/summarize_operating_risk.py` | 운영 리스크 요약 |
| `docs/YOLO_LOCAL_SETUP.md` | YOLO 로컬 검증 절차 |
| `docs/OPERATING_RISK_ROADMAP.md` | 운영 리스크와 제품 완성 로드맵 |

## 4. 현재 완료된 수준

- 서비스는 Docker Compose 기준으로 `http://localhost`에서 실행된다.
- 사용자 웹, 관리자 Agent 테스트 웹, Gateway, Agent, Worker, PostgreSQL, Redis, Caddy edge 구조가 연결되어 있다.
- 영상 업로드부터 전처리, 선택적 OpenAI/YOLO 관찰값 생성, Agent 분석, 결과 카드 표시까지 E2E 골격은 연결되어 있다.
- 사고 판단은 “판결 확정”이 아니라 유사 근거 기반 예상 가이드로 표현하도록 구조가 잡혀 있다.
- 테스트 영상 1~5 기반 회귀와 reference guidance/evidence/calibration 평가 골격이 만들어져 있다.

## 5. 아직 남은 핵심 리스크

| 리스크 | 현재 상태 | 다음 작업 방향 |
| --- | --- | --- |
| 실제 원문 DB 부족 | static fallback과 일부 수집 KNIA/법령 근거가 혼재 | KNIA 원문, 법령, 판례 원문 수집/색인 확대 |
| OpenAI 비용/사용량 | token usage 메타데이터 보존은 시작됨 | DB 단위 사용량 집계, 관리자 화면 표시, 사용량 제한 정책 필요 |
| YOLO 운영 연결 | adapter와 smoke는 있음. 기본 비활성 | Docker image/override, 모델 가중치 관리, 라이선스 검토 필요 |
| S3 직접 업로드 | provider 골격만 있음. 현재 local storage | 팀원 환경과 합의 후 S3 presigned upload 전환 |
| UI 수용성 | 카드/문구 구조는 개선됨 | 실제 사용자 테스트로 문구와 보완 질문 우선순위 조정 |
| 법률 정확도 | 평가 골격은 있음 | 실제 판례/KNIA 원문 coverage와 전문가 검수 샘플 확장 필요 |

## 6. 인수인계 시 주의사항

- `.env`, API 키, AI Hub 키, OpenAI 키, JWT secret, 사용자 비밀번호는 Git이나 문서에 기록하지 않는다.
- `storage/`, `logs/`, `datasets/aihub/*`의 실제 데이터는 로컬 산출물이며 Git에 올리지 않는다.
- 영상 분석 정확도 테스트는 비용이 발생할 수 있으므로 OpenAI 프레임 분석을 켤 때만 명시적으로 실행한다.
- YOLO는 AGPL-3.0 조건과 배포 범위를 확인해야 하며, 현재는 교내 대회/로컬 검증 기준의 optional 보조 모델로 둔다.
- 팀원이 이어받을 때는 `DEVELOPMENT_PROMPT.md`와 `SYSTEM_OVERVIEW.md`를 먼저 읽고, 실행은 `docs/BUILD_AND_RUN_GUIDE.md`를 따르면 된다.
