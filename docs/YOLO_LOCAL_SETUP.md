# YOLO 로컬 보조 관찰 검증

이 문서는 LawCompass 영상처리 고도화를 위해 Ultralytics YOLO를 로컬 보조 관찰 모델로 실행하는 방법을 정리한다.

YOLO는 사고 판단 모델이 아니다. 차량, 사람, 신호등 같은 객체 위치 후보를 뽑는 도구이며, 최종 판단은 기존 Agent가 `video_observations` 입력 계약과 fact arbitration을 거쳐 수행한다.

## 현재 원칙

- YOLO 가상환경, 모델 가중치, AI Hub 샘플 데이터, 추론 결과는 Git에 올리지 않는다.
- 프로젝트에는 팀원이 재현할 수 있는 실행 스크립트와 문서만 둔다.
- Ultralytics YOLO는 기본 AGPL-3.0 라이선스이며, 배포 제품이나 비공개 서비스에 포함하기 전에는 라이선스를 다시 검토한다.
- 객체가 보인다는 사실만으로 사고 대상이나 과실을 확정하지 않는다.

## 로컬 설치 위치

현재 로컬 검증 환경은 저장소 밖의 다음 경로를 기준으로 한다.

```text
C:/Users/yangbun/Documents/OSS/.venv-yolo
C:/Users/yangbun/Documents/OSS/yolo-models
C:/Users/yangbun/Documents/OSS/yolo-runs
```

## 설치

```powershell
cd C:\Users\yangbun\Documents\OSS

py -3.13 -m venv .venv-yolo
.\.venv-yolo\Scripts\python.exe -m pip install -U pip
.\.venv-yolo\Scripts\python.exe -m pip install -r C:\Users\yangbun\Documents\OSS\Law_Compass\tools\yolo\requirements-yolo.txt
```

GPU 사용을 위해 PyTorch CUDA wheel이 필요하면 다음 명령으로 교체한다.

```powershell
.\.venv-yolo\Scripts\python.exe -m pip install --force-reinstall --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

GPU 확인:

```powershell
.\.venv-yolo\Scripts\python.exe -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu')"
```

현재 확인된 로컬 결과:

```text
torch 2.11.0+cu128
cuda_available True
device_name NVIDIA GeForce RTX 5070 Ti
```

## Smoke Test

AI Hub 샘플 이미지나 사고 영상 경로를 `--source`에 넣어 실행한다.

```powershell
C:\Users\yangbun\Documents\OSS\.venv-yolo\Scripts\python.exe `
  C:\Users\yangbun\Documents\OSS\Law_Compass\tools\yolo\run_yolo_observation_smoke.py `
  --model C:\Users\yangbun\Documents\OSS\yolo-models\yolo11n.pt `
  --source "C:\path\to\sample-or-video.mp4" `
  --output-json C:\Users\yangbun\Documents\OSS\yolo-runs\lawcompass-smoke\observations.json `
  --device 0 `
  --save
```

출력 JSON은 다음 용도로만 사용한다.

- `detections`: YOLO 원시 객체 감지 결과
- `observations`: Agent 입력 계약으로 넘길 수 있는 보수적 후보 관찰값
- `notes`: 사고 판단에 직접 사용하지 않기 위한 제한 사항

## 영상처리 연결 구조

현재 목표 구조는 다음과 같다.

```text
업로드 영상
  -> ffmpeg 대표 프레임 추출
  -> OpenAI 프레임 분석: 사고 시점, 방향, 충돌 후보, 신호 등 문맥 관찰
  -> YOLO 로컬 보조 분석: 차량/사람/신호등 등 객체 위치 후보
  -> video_observations 계약으로 병합
  -> Agent fact arbitration에서 수용/보류/충돌 분리
  -> 법률/KNIA/보험 Agent 판단
```

YOLO는 충돌을 직접 판정하지 않는다. 예를 들어 사람 객체가 보여도 `차대사람 사고`로 승격하지 않고, `pedestrian_visible` 후보 관찰값으로만 전달한다. 차량 객체가 보여도 `collision_partner_type=vehicle`을 바로 확정하지 않는다.

## 현재 smoke test 해석

사고 영상 1번을 YOLO로 직접 돌렸을 때 많은 차량 객체와 일부 사람 후보가 잡혔다. 다만 블랙박스 영상이나 휴대폰 촬영 영상에서는 객체 탐지가 주변 간판, 화면 반사, 차내 물체를 잘못 잡을 수 있으므로 YOLO 단독 결과는 모두 보류 후보로 낮춰야 한다.

현재 스크립트는 YOLO 후보 confidence를 Agent의 확정 임계값보다 낮게 제한한다. 따라서 YOLO만으로는 `fact_patch`가 생성되지 않고, 사용자 입력 또는 OpenAI 프레임 문맥 분석과 결합된 뒤에만 판단에 반영된다.

## 다음 통합 단계

서비스 자동 파이프라인에 붙일 때는 `ENABLE_YOLO_FRAME_ANALYSIS=0` 같은 환경변수로 기본 비활성화하고, Worker provider adapter를 새로 둔다. adapter는 업로드 원본 영상을 직접 읽기보다 기존 ffmpeg가 추출한 대표 프레임 경로를 받아 분석하는 방식이 안전하다.
