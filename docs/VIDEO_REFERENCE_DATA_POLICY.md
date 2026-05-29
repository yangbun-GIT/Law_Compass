# 영상 reference 데이터 수집 및 사용 정책

이 문서는 영상/입력 사실 추출 정확도를 높이기 위해 사고 영상과 사고 설명이 함께 있는 reference 데이터를 어떻게 수집하고 테스트에 사용할지 정리한다. 목적은 특정 샘플에 맞춘 답변을 만드는 것이 아니라, 영상에서 추출한 관찰값이 실제 사고 상황과 어긋나거나 오염되는 경로를 발견하고 회귀 테스트로 고정하는 것이다.

## 적용 범위

- 기존 사고 영상 1~5번처럼 사용자가 직접 제공한 로컬 테스트 영상
- AI Hub 승인 데이터의 샘플, 라벨, 소량 선택 파일
- 공개 영상 플랫폼의 사고 영상 링크와 수동 요약 정보
- KNIA, 법령, 판례, 공공 API처럼 근거 검증에 쓰이는 공식/준공식 텍스트 자료

## 핵심 원칙

1. 원본 영상 파일은 Git에 커밋하지 않는다.
2. 공개 플랫폼 영상은 기본적으로 링크와 공개 메타데이터/수동 요약만 manifest에 기록한다.
3. 공개 영상 원본을 다운로드하거나 재배포하는 흐름은 기본 개발 경로로 두지 않는다. 단, 사용 목적과 권한을 확인한 비상업 로컬 평가에서는 `.local/` 아래 임시 다운로드를 허용할 수 있으며 Git에 올리지 않는다.
4. 대회/강의 과제 목적의 비상업 테스트라도 출처별 약관, 저작권, 개인정보, 초상권 제한을 무시하지 않는다.
5. 변호사 의견, 유튜브 설명, 댓글, 보험/경찰 처리 결과는 Agent 입력 사실로 주입하지 않는다. 평가용 reference와 calibration 기대값으로만 사용한다.
6. AI Hub 원본 데이터, shell 다운로드 결과, 대용량 라벨/영상, API key는 Git에 넣지 않는다.
7. reference 데이터는 “정답 주입”이 아니라 “오염 탐지와 회귀 검증”에 사용한다.

## 데이터 등급

| 등급 | 예시 | 사용 목적 | Git 포함 여부 |
| --- | --- | --- | --- |
| `local_user_provided` | 사용자가 제공한 사고 1~5 영상 | 실제 영상 파이프라인 기준선, 사고 시점 후보, 관찰값 오염 검증 | 영상 제외, manifest만 가능 |
| `aihub_sample` | AI Hub 교통사고 영상 데이터 샘플, 차량 및 사람 인지 영상 샘플 | 객체/사람/차량/도로 환경 관찰값 검증, YOLO/OpenAI 보조 평가 | 원본 제외, 파일 목록/요약/fixture만 가능 |
| `public_reference_link` | 한문철TV 등 공개 사고 영상 링크 | 사고 설명과 전문가 의견을 reference로 삼아 Agent 판단 범위 calibration | 링크/요약만 가능 |
| `official_evidence` | KNIA 기준, 법령, 판례, 공공 API | 사용자 결과의 근거 검색/표시 적합도 검증 | 라이선스 허용 범위 내 텍스트/메타데이터만 가능 |

## 공개 영상 reference 사용 기준

공개 영상 플랫폼 자료는 테스트 품질을 높이는 데 유용하지만 공식 판례나 공공 근거가 아니다. 따라서 아래 방식으로만 사용한다.

- 허용: URL, 제목, 공개 설명의 짧은 요약, 전문가 의견의 짧은 요약, 실제 결과가 공개된 경우 결과 여부, 평가 focus 기록
- 허용: 사용자가 권한과 용도를 확인하고 로컬에 제공한 테스트용 영상 파일을 로컬에서만 분석
- 제한 허용: 비상업 과제/대회 목적의 로컬 평가에서 `yt-dlp` 등으로 임시 영상 파일을 받아 정량 관찰값 회귀를 확인. 이 경우 `.local/` 또는 `storage/` 아래에만 두고 테스트 후 삭제 가능해야 한다.
- 금지: 무단 대량 다운로드, 무단 스크래핑, 원본 영상 재배포, 학습 데이터셋으로 편입, Git 커밋
- 주의: 전문가 의견은 참고 범위이며 법원 판결이나 보험 분쟁심의 결과와 동일하게 취급하지 않는다.

## 공개 reference 후보 자동 수집

외부 사고 영상과 사고 설명은 사용자가 매번 직접 올리지 않아도 후보를 수집할 수 있다. 단, 자동 수집의 대상은 원본 영상 파일이 아니라 공개 링크와 공개 메타데이터다.

- `scripts/collect_public_video_references.py`는 YouTube Data API key가 로컬 환경 변수에 있을 때 검색어 기반 후보를 수집한다.
- API key가 없으면 `--urls`로 받은 공개 URL만 manifest 후보로 변환할 수 있다.
- 로컬에 `yt-dlp`가 있으면 `--yt-dlp-search`로 검색 후보를 찾거나 `--yt-dlp-metadata`로 공개 제목/설명란을 가져오고, 사용 목적과 권한을 확인한 경우에만 `--allow-video-download`로 로컬 임시 영상을 받을 수 있다.
- 수집 결과는 `.local/video_reference_candidates.json`처럼 Git ignore 대상 경로에 저장한다.
- 자동 수집된 후보는 모두 `candidate_requires_manual_review` 상태이며, 사고 상황 요약과 기대 관찰값을 검토하기 전에는 평가 정답으로 쓰지 않는다.
- 수집 절차와 명령은 `docs/PUBLIC_VIDEO_REFERENCE_COLLECTION.md`를 따른다.

## AI Hub 사용 기준

AI Hub는 API key와 데이터셋 승인 후 `aihubshell`로 데이터셋 목록과 filekey를 조회하고 선택 다운로드할 수 있다. 전체 원본 데이터는 용량이 크므로 기본적으로 받지 않는다.

- 먼저 `list` 모드로 dataset/file 구조와 filekey를 확인한다.
- 필요한 경우 샘플 또는 작은 라벨 파일부터 선택 다운로드한다.
- 원본 영상과 라벨은 `datasets/aihub/**/samples/` 또는 로컬 전용 작업 폴더에 두되 Git에 올리지 않는다.
- API key는 `.env` 또는 개인 로컬 환경 변수에만 보관한다.

## Manifest 운용

reference case는 `tests/fixtures/video_accuracy/reference_case_manifest.example.json` 형식을 따른다. 실제 영상 경로가 들어간 개인 manifest는 Git에 올리지 않고, 공유가 필요한 경우 경로를 placeholder로 바꾼 example 또는 synthetic fixture만 커밋한다.

필수 항목:

- `id`: reference case 고유 id
- `source_type`: `local_user_provided`, `aihub_sample`, `public_reference_link`, `official_evidence` 중 하나
- `reference_role`: `evaluation_only_not_agent_input`, `calibration_reference_only`, `official_evidence_reference_only` 중 하나. 공개 영상과 전문가 의견은 Agent 입력 사실이 아니라 평가/보정 reference임을 명시한다.
- `review_status`: `candidate_requires_manual_review`, `reviewed_for_evaluation`, `rejected` 중 하나. 자동 수집 후보는 기본적으로 수동 검토 전 상태다.
- `source_url`: 공개 링크 또는 공식 자료 URL. 로컬 파일만 있으면 생략 가능
- `local_video_path`: 로컬 테스트 영상 경로. 커밋 금지 manifest에서만 사용
- `scenario_summary`: 사고 상황의 짧은 요약
- `reference_outcome`: 전문가 의견 요약, 실제 처리 결과 공개 여부, 신뢰도 메모. 이 항목은 calibration용이며 Agent 사용자 입력으로 주입하지 않는다.
- `reference_expectations`: 영상 관찰값이 맞춰야 하는 사고 대상, 사고 시점, 환경 맥락, 오염 방지 항목
- `evaluation_focus`: 이번 case가 검증하려는 오염 유형 또는 판단 축
- `usage_policy`: 비상업 과제/대회 테스트, 링크만 기록, 원본 미커밋 같은 사용 제한

커밋 전에 example 또는 공유용 manifest는 아래 명령으로 검증한다.

```powershell
py -3 scripts\validate_reference_case_manifest.py `
  --manifest tests\fixtures\video_accuracy\reference_case_manifest.example.json `
  --output logs\video_accuracy\reference_case_manifest_example_preflight.json
```

로컬 전용 후보 manifest도 같은 스크립트로 검사할 수 있다. 경고는 수동 검토가 덜 된 후보를 알려주는 용도이며, 오류가 있으면 해당 manifest를 평가에 사용하지 않는다.

## P0-2 적용 방식

P0-2 기준선 재측정은 아래 순서로 진행한다.

1. 기존 사고 1~5번을 먼저 측정한다.
2. 공개 reference 후보는 `scripts/collect_public_video_references.py`로 링크/메타데이터 manifest를 먼저 만든다.
3. 확보된 public reference link는 먼저 설명/기대 관찰값 manifest만 만든다.
4. 사용 목적과 권한이 확인되어 로컬 임시 영상 파일이 준비된 public reference만 영상 파이프라인에 포함한다.
5. AI Hub는 샘플 또는 작은 라벨 파일이 준비된 경우에만 보조 측정에 포함한다.
6. 측정 결과는 관찰값 0개, 사고 시점 후보, 직접 충돌 대상, 사고 환경 오염 여부, 근거 검색 오염 여부를 중심으로 기록한다.

## 커밋 금지 항목

- 원본 사고 영상
- AI Hub 원본 데이터와 대용량 라벨
- 공개 영상 플랫폼에서 받은 원본 파일
- API key, 사용자 계정, 비밀번호
- 다운로드 로그 중 token, key, 개인 경로, 개인정보가 포함된 내용
- `storage/`, `logs/`, `datasets/aihub/**/samples/`의 실제 원본 산출물
