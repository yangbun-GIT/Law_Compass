# 교통사고 영상 데이터

AI-Hub `교통사고 영상 데이터` 로컬 작업 위치입니다. 실제 데이터 파일은 Git에 올리지 않습니다.

| 폴더 | 용도 |
| --- | --- |
| `aihubshell/` | AI-Hub Shell 실행 파일과 README만 보관 |
| `labels/video/` | TL/VL 영상 라벨 ZIP과 JSON을 정리한 로컬 전용 폴더 |
| `samples/` | AI-Hub에서 받은 경량 샘플 데이터 보관 |

다운로드 직후 AI-Hub 공식 폴더 구조가 깊게 생성되면 아래 명령으로 정리합니다.

```powershell
py -3.13 scripts\organize_aihub597_labels.py
```

정리된 라벨 구조:

```text
labels/video/
  training/zips/
  training/json/
  validation/zips/
  validation/json/
  index.json
```

`index.json`은 라벨 JSON과 원래 ZIP 파일의 대응 관계를 기록합니다. API key, 원천 영상, 라벨 ZIP/JSON, 샘플 데이터는 모두 로컬 전용이며 Git에 커밋하지 않습니다.
