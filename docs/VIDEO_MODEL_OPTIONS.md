# 영상 분석 모델 후보 정리

작성일: 2026-05-29

이 문서는 LawCompass 영상 처리 고도화 시 참고할 모델/SDK 후보를 정리한다. 목적은 특정 모델을 즉시 교체하는 것이 아니라, 영상에서 객관적인 관찰값을 얻는 경로와 사고 흐름을 이해하는 경로를 분리해 이후 개발 판단 기준으로 삼는 것이다.

## 기본 원칙

- YOLO, ML Kit, MediaPipe 같은 객체 감지 도구는 사고 판단 모델이 아니다.
- 영상 이해 모델은 사고 장면의 흐름과 맥락을 해석하는 보조 분석 모델이다.
- 최종 법률/과실/보험 안내는 Agent가 사용자 입력, 영상 관찰값, KNIA/법령/판례 근거를 함께 검토해 생성한다.
- 모델 출력은 바로 사용자 결론으로 쓰지 않고 `video_observations` 계약과 fact arbitration을 거쳐 확정/보류/충돌/참고 후보로 나눈다.
- 무료 또는 로컬 실행 후보도 라이선스, 데이터 전송, GPU/메모리 요구량, 유지보수 상태를 확인한 뒤 사용한다.

## 역할 구분

| 구분 | 대표 후보 | 역할 | 직접 판단 가능 여부 |
| --- | --- | --- | --- |
| 객체 감지/추적 | YOLO, Google ML Kit, MediaPipe Object Detector | 차량, 사람, 신호등, 자전거, 버스 등 객체 후보와 위치/추적 정보 추출 | 불가 |
| 영상 이해 모델 | Qwen2.5-VL, Gemini video understanding, OpenAI frame/video analysis | 여러 프레임 또는 영상 구간의 사고 흐름, 진행 방향, 충돌 맥락 해석 | 단독 판단 금지 |
| Agent 판단 계층 | LawCompass Agent | 사용자 입력, 영상 관찰값, KNIA/법령/판례 근거를 조율해 참고 가이드 생성 | 가능하나 근거 기반 참고 안내로 제한 |

## 무료 범위 우선 추천

### 1. YOLO + Qwen2.5-VL 로컬

현재 무료/로컬 중심 개발에서 가장 현실적인 기본 후보이다.

- YOLO는 객체 감지와 추적 후보를 만든다.
- Qwen2.5-VL은 프레임 묶음 또는 영상 구간을 보고 장면 흐름을 설명하는 후보로 사용한다.
- 외부 API 비용은 없지만, 로컬 GPU/VRAM과 설치 복잡도가 필요하다.
- Qwen2.5-VL 7B가 1차 후보이며, 자원이 부족하면 3B 또는 양자화 모델을 검토한다.
- Qwen2.5-VL은 Apache-2.0 라이선스 모델로 공개되어 있으며, 영상 이해와 dynamic FPS 처리 설명이 제공된다.

적합한 용도:

- 사고 1~5 같은 reference 영상으로 로컬 반복 검증
- 외부 API 비용 없이 provider 비교
- 영상 장면 의미 요약 후보 생성

주의:

- 로컬 모델의 환각 가능성을 전제로 결과를 확정하지 않는다.
- `collision_partner_type`, 신호위반, 과실비율은 Agent fact arbitration과 근거 검증 뒤에만 반영한다.

### 2. Gemini API Free Tier + YOLO

무료 tier가 있는 외부 API 비교 후보이다.

- Gemini API는 영상 입력, clipping interval, frame rate sampling을 공식 지원한다.
- 무료 tier는 테스트와 소규모 실험에 적합하지만 rate limit이 있다.
- 무료 tier에서 입력/출력은 무료일 수 있으나, 사용 데이터가 제품 개선에 쓰일 수 있는 정책이 표시되어 있으므로 민감 영상에는 주의한다.

적합한 용도:

- Qwen 로컬 결과와 외부 영상 이해 모델 비교
- 짧은 사고 영상의 장면 흐름 해석 품질 비교
- 무료 범위 내 제한적 회귀 샘플 테스트

주의:

- 무료 rate limit은 프로젝트/모델/tier에 따라 달라질 수 있으므로 AI Studio에서 현재 한도를 확인한다.
- 개인정보 또는 민감 영상은 사용자 동의와 보안 정책 없이는 외부 API로 보내지 않는다.

### 3. Google ML Kit / MediaPipe

모바일 또는 클라이언트 선처리 후보이다.

- 예전 Firebase ML Kit의 on-device API는 standalone Google ML Kit SDK로 이동했다.
- 현재는 Firebase ML Kit 대신 Google ML Kit 또는 MediaPipe로 보는 것이 맞다.
- ML Kit on-device API는 기기 내 처리 중심이며 개발자에게 무료로 제공되는 경로가 있다.
- MediaPipe Object Detector는 이미지, 비디오, 라이브 스트림 모드를 지원하며 Python/Web/Android/iOS에 걸쳐 사용할 수 있다.

적합한 용도:

- 나중에 Capacitor 기반 모바일 앱을 만들 때, 업로드 전 기기 내 1차 객체 관찰
- 개인정보 영상의 외부 전송 최소화
- 서버 비용 절감 목적의 선처리

현재 프로젝트에서의 위치:

- 지금 Docker Worker 중심 서버 구조에 ML Kit Android/iOS SDK를 바로 붙이는 것은 적합하지 않다.
- 현재 단계에서는 YOLO/MediaPipe Python처럼 서버나 로컬 worker에서 실행 가능한 도구가 더 자연스럽다.
- ML Kit은 모바일 앱 단계에서 `client_pre_observations` 같은 별도 입력으로 Agent에 넘기는 방식이 적합하다.

주의:

- ML Kit 객체 감지는 객체 후보/추적용이지 사고 원인 또는 과실 판단용이 아니다.
- 사람이 보였다고 차대사람 사고로 승격하거나, 신호등이 보였다고 상대 신호를 확정하지 않는다.

## 현재 프로젝트 권장 구조

```text
업로드 영상
  -> ffmpeg/ffprobe 전처리와 대표 프레임/사고시점 후보 추출
  -> YOLO: 객체 후보와 위치/추적 후보
  -> Qwen2.5-VL 또는 Gemini: 사고 흐름/장면 의미 후보
  -> video_observations 계약으로 병합
  -> Agent fact arbitration: 확정/보류/충돌/참고 분리
  -> KNIA/법령/판례/보험 Agent 판단
```

모바일 앱 단계에서는 다음 경로를 추가할 수 있다.

```text
모바일 기기
  -> ML Kit 또는 MediaPipe 온디바이스 1차 관찰
  -> 서버 업로드 시 client_pre_observations 첨부
  -> 서버 YOLO/Qwen/Gemini 분석과 비교
  -> Agent fact arbitration
```

## 우선순위

| 우선순위 | 작업 | 이유 |
| --- | --- | --- |
| P0 | 현재 OpenAI 프레임 분석과 YOLO 관찰값이 오염 없이 Agent 계약으로 들어가는지 검증 | 이미 연결된 경로의 신뢰도 확보가 먼저다 |
| P1 | 영상 provider 인터페이스 추상화 | OpenAI, Qwen, Gemini, YOLO 결과를 같은 계약으로 비교하기 위해 필요하다 |
| P2 | Qwen2.5-VL 로컬 provider smoke test | 무료/로컬 영상 이해 후보의 실제 품질 확인 |
| P3 | Gemini Free Tier provider 비교 실험 | 외부 영상 이해 모델과 로컬 모델의 품질 차이 확인 |
| P4 | 모바일 앱 단계에서 ML Kit/MediaPipe 선처리 설계 | 현재 서버 구조보다 모바일 클라이언트 단계에 더 적합하다 |

## 판단 메모

- 지금 당장 ML Kit을 핵심 Worker에 붙이는 것은 권장하지 않는다.
- ML Kit은 나중에 모바일 앱을 만들 때 사용 가능하고, 그때가 가장 효율적이다.
- 현재 서버/로컬 개발에서는 YOLO와 Qwen2.5-VL 로컬 실험이 우선이다.
- 기업 API를 쓰더라도 무료 tier는 정책과 한도가 바뀔 수 있으므로 운영 의존성을 낮게 둔다.
- 무료 tier를 제품 핵심 경로로 고정하지 말고, provider 교체 가능한 구조로 둔다.

## 참고한 공식 문서

- Google ML Kit migration guide: https://developers.google.com/ml-kit/migration
- Google ML Kit object detection and tracking: https://developers.google.com/ml-kit/vision/object-detection/android
- Google AI Edge MediaPipe Object Detector: https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector
- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini API rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Gemini video understanding: https://ai.google.dev/gemini-api/docs/video-understanding
- Qwen2.5-VL 7B model card: https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct
- Ultralytics license: https://www.ultralytics.com/license
