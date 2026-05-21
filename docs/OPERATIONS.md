# LawCompass Quick Ops

## 0) 환경값 준비
- 기본 실행 파일: `.env`
- 개발용 참고: `.env.dev`
- 아래 값 확인
  - `OPENAI_API_KEY` (실제 키)
  - `OPENAI_MODEL` (기본 `gpt-4.1-mini`)
  - `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
  - `LAW_API_OC`, `LAW_API_TARGETS`
  - `DATA_GO_SERVICE_KEY`, `DATA_GO_TRAFFIC_URL`

## 1) 개발 기동
```bash
docker compose --env-file .env up --build
```

## 2) KB 샘플 적재
```bash
docker compose exec agent python scripts/ingest_kb.py
```

## 2-1) 외부 법률 API 기반 KB 적재(선택)
사전 조건:
- `.env`에 `LAW_API_OC` 설정(국가법령정보센터 OPEN API 사용자 OC)
- 필요 시 `DATA_GO_SERVICE_KEY`, `DATA_GO_TRAFFIC_URL` 설정

```bash
docker compose exec agent python scripts/ingest_legal_apis.py
```

## 2-2) 외부 API 키/권한 점검
```bash
docker compose exec -T agent sh -lc "PYTHONPATH=/app python scripts/check_external_apis.py"
```

주의:
- 국가법령정보센터 OPEN API는 호출 서버의 IP/도메인 등록이 맞지 않으면 `사용자 정보 검증 실패`가 반환됩니다.
- 공공데이터포털 API는 활용신청 승인 상태/엔드포인트별 권한/요청 파라미터가 맞지 않으면 `Forbidden` 또는 `Unexpected errors`가 반환될 수 있습니다.

## 3) E2E 스모크 테스트
PowerShell:
```powershell
./scripts/smoke_e2e.ps1 -BaseUrl http://localhost
```

## 4) 프론트에서 기능 확인
1. 회원가입
2. 로그인
3. 케이스 생성
4. 영상 업로드(init -> S3 direct upload -> complete)
5. 텍스트 분석
6. 영상 분석 큐 등록 후 작업 상태 자동 갱신
7. 결과 리포트/근거 펼쳐보기
8. 업로드 영상 재생 URL/다운로드 URL 발급

## 5) 재배포 루틴(단일 서버)
1. 새 이미지 빌드
2. `docker compose pull` 또는 `up --build`
3. `docker compose up -d --remove-orphans`
4. `docker compose ps` + `/ready` 확인
5. 장애 시 이전 이미지 태그로 롤백

## 6) 보안 주의
- `OPENAI_API_KEY`는 절대 외부에 공개하지 말고 서버 환경변수로만 관리
- 키가 노출되었으면 즉시 OpenAI 콘솔에서 회전(재발급) 권장
