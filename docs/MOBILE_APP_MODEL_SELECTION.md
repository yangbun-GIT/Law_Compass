# 모바일 앱 패키징 단계 모델 선택 가이드

작성 기준일: 2026-05-29

이 문서는 LawCompass를 나중에 Capacitor 기반 모바일 앱으로 패키징할 때, 영상/프레임 분석 모델을 어떤 기준으로 선택할지 정리한 팀원 공유용 문서다. 현재 서버 Worker에 바로 적용하는 구현 지시서가 아니라, 모바일 앱 단계에서 검토할 모델 선택 기준이다.

## 결론

앱 패키징 단계에서는 `Google ML Kit` 또는 `MediaPipe`를 업로드 전 온디바이스 1차 관찰 도구로 검토한다. 단, 이 도구들은 사고 판단 모델이 아니다. 차량, 사람, 신호등, 자전거, 객체 위치 후보를 만들고, 최종 판단은 서버의 Agent가 사용자 입력, 영상 관찰값, KNIA/법령/판례 근거를 함께 검토해 수행한다.

현재 추천 순서는 다음과 같다.

| 우선순위 | 선택지 | 추천 용도 | 판단 |
| --- | --- | --- | --- |
| 1 | Google ML Kit Object Detection & Tracking | 모바일 기기에서 빠르게 객체 후보와 tracking id 추출 | 앱 패키징 시 1차 후보 |
| 2 | MediaPipe Object Detector | Android/iOS/Web/Python까지 비슷한 구조로 확장 가능한 객체 감지 | ML Kit 한계가 보이면 비교 후보 |
| 3 | TensorFlow Lite custom model | AI Hub 또는 별도 데이터로 학습한 교통사고 특화 모델 탑재 | 데이터셋/학습 파이프라인 확보 후 검토 |
| 4 | 서버 YOLO + OpenAI/Qwen/Gemini | 업로드 후 서버/로컬 Worker에서 정밀 분석 | 현재 서버 측 보조 분석 경로 |

## Firebase ML Kit이 아니라 Google ML Kit으로 봐야 하는 이유

기존 기획서에는 Firebase ML Kit이 적혀 있었지만, 현재 공식 문서 기준으로 온디바이스 API는 standalone `ML Kit` SDK로 분리되어 있다. Firebase 쪽은 클라우드 API와 모델 배포 성격으로 남아 있고, 객체 감지/추적 같은 온디바이스 기능은 Google ML Kit SDK 기준으로 검토하는 것이 맞다.

따라서 앞으로 문서나 회의에서 “Firebase ML Kit”이라고 부르기보다 다음처럼 구분한다.

| 표현 | 현재 기준 해석 |
| --- | --- |
| Firebase ML Kit | 과거 표현. 온디바이스 API는 새 구현 기준으로 부적합한 명칭 |
| Google ML Kit | Android/iOS 온디바이스 객체 감지/추적 1차 후보 |
| Firebase Machine Learning | 클라우드 API 또는 custom model deployment 관련 영역 |
| TensorFlow Lite | 직접 모델을 탑재하거나 커스텀 추론 파이프라인이 필요할 때 |

## 모바일 앱에서 맡길 책임

모바일 앱 단계에서 ML Kit 또는 MediaPipe가 맡을 책임은 아래 정도로 제한한다.

| 책임 | 모바일 모델 사용 여부 | 설명 |
| --- | --- | --- |
| 차량/사람/자전거/신호등 후보 감지 | 사용 가능 | bounding box, confidence, tracking id를 만든다. |
| 사고 시점 후보 보조 | 제한적 사용 | 객체 이동, 급격한 위치 변화, 프레임 변화량을 참고 후보로만 쓴다. |
| 직접 충돌 대상 확정 | 단독 금지 | 사람이나 횡단보도가 보인다고 차대사람 사고로 확정하지 않는다. |
| 신호위반 확정 | 단독 금지 | 신호등 색상 후보는 만들 수 있지만, 상대 신호·진입 시점은 별도 확인이 필요하다. |
| 과실비율 산정 | 금지 | KNIA/법령/판례 근거와 Agent 판단 계약을 거쳐야 한다. |
| 법률/보험 대응 안내 | 금지 | 서버 Agent의 전문가 안내 영역이다. |

## 추천 아키텍처

```text
모바일 앱
  -> 사용자가 영상 선택 또는 촬영
  -> ML Kit 또는 MediaPipe로 기기 내 1차 객체 후보 추출
  -> client_pre_observations 생성
  -> 영상 원본 또는 압축본과 함께 서버 업로드

서버 Worker
  -> ffmpeg/ffprobe metadata, 대표 프레임, 사고 후보 구간 생성
  -> YOLO/OpenAI/Qwen/Gemini 같은 서버 측 provider 분석
  -> mobile observation과 server observation을 같은 video_observations 계약으로 병합

Agent
  -> fact arbitration에서 확정/보류/충돌/참고 후보 분리
  -> KNIA/법령/판례 근거 검색
  -> 법률/보험/대응 가이드 생성
```

## 입력 계약 초안

모바일 앱에서 서버로 넘기는 값은 최종 판단값이 아니라 관찰 후보여야 한다.

```json
{
  "source": "client_pre_observation",
  "provider": "google_mlkit",
  "provider_version": "record-at-runtime",
  "video_id": "local-upload-id",
  "observations": [
    {
      "field": "object_candidate",
      "value": "vehicle",
      "confidence": 0.82,
      "frame_time_sec": 3.4,
      "bbox": [0.12, 0.34, 0.42, 0.78],
      "track_id": 7
    }
  ]
}
```

중요한 제한:

- `accident_party_type`, `collision_partner_type`, `fault_ratio`, `signal_violation` 같은 판단 필드를 모바일 모델이 직접 확정하면 안 된다.
- 모바일 모델 출력은 `video_observations` 또는 `client_pre_observations`로 들어가고, Agent fact arbitration을 반드시 거친다.
- 사용자의 원본 영상, 위치정보, 차량번호, 얼굴 등 민감 데이터는 앱 단계에서 마스킹 또는 저장 최소화를 우선 검토한다.

## Google ML Kit 선택 기준

Google ML Kit은 앱 패키징 단계의 1차 후보로 적합하다.

장점:

- Android/iOS 온디바이스 처리에 맞춰져 있어 서버 비용과 업로드 전송량을 줄일 수 있다.
- 객체 감지와 추적을 제공하고, video stream에서는 객체별 tracking id를 사용할 수 있다.
- Firebase 프로젝트 없이 온디바이스 API를 사용할 수 있는 방향으로 분리되어 있다.

한계:

- 기본 객체 분류는 넓은 범주 중심이라 “교통사고 원인”을 이해하지 못한다.
- 보행자, 차량, 신호등이 보이는 것과 실제 사고 대상은 다르다.
- streaming mode에서는 기기 성능에 따라 첫 감지까지 여러 프레임이 필요할 수 있다.

적합한 사용:

- 업로드 전 프레임 일부에서 차량/사람/자전거/신호등 후보 추출
- 같은 객체가 몇 프레임 동안 이동했는지 tracking id로 기록
- 서버 분석이 놓친 후보를 보완하는 참고 관찰값 생성

부적합한 사용:

- 과실비율 직접 계산
- 사고 유형 확정
- 법률 근거 선택
- 경찰/보험/민형사 책임 판단

## MediaPipe 선택 기준

MediaPipe는 ML Kit보다 더 넓은 플랫폼 확장성과 모델 선택권이 필요할 때 비교한다.

장점:

- Android, Web, Python 등 여러 환경에서 유사한 구조로 실험하기 좋다.
- 이미지, 비디오 파일, live stream running mode를 구분할 수 있다.
- 모델 파일을 앱 asset에 포함하는 형태로 운영 가능하다.

한계:

- 모델 선택, asset 관리, threshold 튜닝 책임이 커진다.
- 기본 모델만으로 교통사고 특화 판단이 되지는 않는다.
- 앱 패키지 크기와 기기별 성능 차이를 별도로 관리해야 한다.

적합한 사용:

- ML Kit보다 custom detector를 더 쉽게 비교하고 싶을 때
- 서버 Python 실험과 모바일 앱 실험의 모델 계열을 맞추고 싶을 때
- 이후 TFLite custom model로 넘어갈 가능성이 높을 때

## TensorFlow Lite custom model 선택 기준

TFLite custom model은 바로 도입할 후보가 아니라, 데이터셋과 학습 목표가 명확해진 뒤 검토한다.

검토 조건:

- AI Hub 또는 별도 라벨링 데이터에서 사고 객체/차선/신호/충돌 지점 라벨을 확보했다.
- 모델이 출력해야 할 정량 필드가 명확하다.
- 모바일 앱 패키지 크기와 추론 시간 기준을 정했다.
- 잘못된 판단을 Agent가 보류/충돌로 처리하는 계약이 준비되어 있다.

가능한 역할:

- 교통사고 특화 객체 감지
- 차선/중앙선/정지선 후보 감지
- 충돌 지점 후보 감지
- 야간 무등화 차량, 정차 차량 후보 감지

단독으로 하면 안 되는 역할:

- 사고 법률 판단
- 과실비율 확정
- 실제 판례 유사도 판단

## 서버 모델과의 관계

모바일 모델과 서버 모델은 대체 관계가 아니라 보완 관계다.

| 영역 | 모바일 ML Kit/MediaPipe | 서버 YOLO/OpenAI/Qwen/Gemini |
| --- | --- | --- |
| 실행 위치 | 사용자 기기 | 서버 Worker 또는 로컬 GPU worker |
| 장점 | 빠름, 저비용, 개인정보 전송 최소화 | 더 많은 프레임/모델 조합/후처리 가능 |
| 단점 | 기기 성능 차이, 모델 한계 | 비용, 지연, 서버 리소스 부담 |
| 출력 | 객체 후보, tracking 후보 | 사고 시점 후보, 장면 이해 후보, 구조화 관찰값 |
| 최종 판단 | 불가 | 단독 불가, Agent 검증 필요 |

모바일에서 관찰한 값과 서버에서 관찰한 값이 충돌하면 서버값을 무조건 우선하지 않는다. Agent가 confidence, frame reference, 사용자 입력, KNIA/법령/판례 근거와 함께 판단해 확정/보류/충돌로 나눈다.

## 앱 패키징 시 적용 단계

| 단계 | 작업 | 산출물 |
| --- | --- | --- |
| App P0 | Capacitor 패키징 결정 | Android/iOS 프로젝트 생성 여부 결정 |
| App P1 | ML Kit object detection PoC | 실제 블랙박스/휴대폰 재촬영 영상에서 객체 후보 추출 가능 여부 확인 |
| App P2 | client_pre_observations 계약 구현 | 모바일 관찰값을 서버 DTO로 전달 |
| App P3 | 서버 video_observations와 병합 | 모바일/서버 관찰값 conflict 처리 |
| App P4 | 개인정보/성능 정책 확정 | 얼굴/번호판/위치정보 처리, 프레임 수, 배터리 영향 기준 |
| App P5 | TFLite custom model 검토 | 데이터셋과 라벨링 기준이 생긴 뒤 진행 |

## 팀원 작업 시 주의사항

- ML Kit을 붙이더라도 기존 Worker/Agent 판단 구조를 우회하지 않는다.
- 모바일 모델 결과를 사용자 화면에 “확정 사실”처럼 보여주지 않는다.
- 모델명, SDK 버전, frame count, confidence, 처리 실패 사유는 안전 메타데이터로 남긴다.
- 원본 영상, API key, 모델 가중치, AI Hub 원본 데이터는 Git에 올리지 않는다.
- 앱 패키징 전까지는 현재 서버 Worker의 YOLO/OpenAI 경로와 충돌하지 않게 문서/계약 중심으로 준비한다.

## 참고 공식 문서

- Google ML Kit migration guide: https://developers.google.com/ml-kit/migration
- Google ML Kit object detection and tracking: https://developers.google.com/ml-kit/vision/object-detection/android
- MediaPipe Object Detector for Android: https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector/android
- TensorFlow Lite object detection overview: https://www.tensorflow.org/lite/models/object_detection/overview
