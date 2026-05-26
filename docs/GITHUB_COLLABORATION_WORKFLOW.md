# GitHub Collaboration Workflow

작성일: 2026-05-26  
대상: LawCompass를 2명이 동시에 개발할 때 따를 협업 기준입니다.

이 문서는 폴더를 주고받는 방식에서 GitHub 기반 동시 개발 방식으로 전환하기 위한 운영 규칙입니다. 실제 API 키, `.env` 값, 사용자 비밀번호, 동영상 원본, AI Hub 원본 데이터는 절대 GitHub에 올리지 않습니다.

## 1. 기본 원칙

- `main` 브랜치는 항상 실행 가능한 기준 상태로 유지합니다.
- 모든 작업은 개인 작업 브랜치에서 진행합니다.
- 작업 완료 후 GitHub Pull Request(PR)를 만들고, 상대가 변경 내용을 확인한 뒤 `main`에 병합합니다.
- 작업 시작 전에는 항상 최신 `main`을 가져옵니다.
- 같은 파일을 동시에 크게 수정하지 않도록 작업 범위를 먼저 공유합니다.
- `main` 병합 전에는 팀원에게 병합 예정임을 알리고, 병합 후에는 최신 `main`을 pull하라고 알립니다.

## 2. 브랜치 이름 규칙

브랜치 이름은 작업 목적이 바로 보이도록 짧게 작성합니다.

```text
feature/agent-evidence-ranking
feature/video-analysis-ui
fix/login-session
fix/knia-filter
docs/handoff-guide
chore/docker-cleanup
```

권장 prefix:

| Prefix | 용도 |
| --- | --- |
| `feature/` | 새 기능 또는 큰 흐름 보강 |
| `fix/` | 버그 수정 |
| `docs/` | 문서만 변경 |
| `test/` | 테스트 추가 또는 회귀 검증 |
| `chore/` | 설정, 빌드, 정리 작업 |

## 3. 작업 시작 절차

항상 `main`을 최신화한 뒤 새 브랜치를 만듭니다.

```powershell
git checkout main
git pull origin main
git checkout -b feature/my-task
```

이미 만든 브랜치에서 계속 작업할 때도 먼저 `main` 변경을 반영합니다.

```powershell
git checkout main
git pull origin main
git checkout feature/my-task
git merge main
```

충돌이 나면 충돌 파일을 직접 확인하고 해결한 뒤 커밋합니다. 이해하지 못한 충돌을 임의로 덮어쓰지 않습니다.

## 4. 작업 중 공유 규칙

작업 시작 전에 팀원에게 아래 내용을 공유합니다.

```text
오늘 작업 브랜치: feature/video-analysis-ui
수정 예정 범위: apps/frontend/src/components/easy, apps/gateway/src/lib/report-composer.ts
건드리지 않을 범위: Agent 판단 로직, DB migration
예상 완료 시점: 오늘 밤
```

동시에 수정하면 충돌 가능성이 큰 범위:

- `apps/gateway/src/lib/report-composer.ts`
- `apps/agent/app/services/scenario_classifier.py`
- `apps/agent/app/services/fact_arbitration.py`
- `apps/agent/app/services/analysts/fault_ratio_analyst.py`
- `apps/worker/worker/frame_analysis.py`
- `SYSTEM_OVERVIEW.md`
- `DEVELOPMENT_PROMPT.md`

이 파일들을 수정할 때는 먼저 말하고 작업합니다.

## 5. 커밋 전 확인

커밋 전에는 변경 범위를 확인합니다.

```powershell
git status --short
git diff --stat
```

절대 커밋하면 안 되는 항목:

- `.env`, `.env.dev`, `.env.prod`
- API key, JWT secret, internal token
- 사용자 비밀번호, refresh token
- `storage/`, `logs/`
- 사고 영상 원본, AI Hub 원본 데이터
- YOLO 모델 가중치
- `node_modules/`, `dist/`, `__pycache__/`

실수로 들어갔는지 확인합니다.

```powershell
git status --short --ignored
```

## 6. 검증 기준

작업 성격에 맞게 최소 검증을 수행합니다.

문서만 수정:

```powershell
git diff --check
```

Frontend 수정:

```powershell
cd apps/frontend
npm run build
```

Gateway 수정:

```powershell
cd apps/gateway
npm test
npm run build
```

Agent/Worker/전체 흐름 수정:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_final_readiness.ps1 -SkipDockerBuild
```

Docker 실행 상태까지 확인:

```powershell
docker compose up --build -d
Invoke-WebRequest -UseBasicParsing http://localhost/health
```

검증을 못 했거나 실패가 남아 있으면 PR 설명에 반드시 적습니다.

## 7. 커밋과 Push

커밋 메시지는 작업 내용을 한 문장으로 요약합니다.

```powershell
git add .
git commit -m "Improve video evidence display"
git push origin feature/my-task
```

좋은 커밋 메시지 예시:

```text
Add GitHub collaboration workflow
Fix vehicle collision evidence filtering
Improve admin agent test input modes
Document build and run handoff steps
```

피해야 할 메시지:

```text
update
fix
asdf
final
```

## 8. Pull Request 규칙

PR에는 아래 내용을 적습니다.

```markdown
## Summary
- 무엇을 바꿨는지 요약

## Verification
- 실행한 검증 명령
- 실패하거나 생략한 검증이 있으면 이유

## Notes
- 팀원이 특히 봐야 하는 파일
- 남은 리스크나 다음 작업
```

PR 크기는 작게 유지합니다. 가능하면 한 PR은 하나의 목적만 갖습니다.

좋은 PR 단위:

- 영상 관찰값 UI 표시 개선
- KNIA 근거 필터 보강
- Agent 보완 질문 우선순위 수정
- 실행 문서 정리

나쁜 PR 단위:

- Frontend, Agent, Worker, DB, 문서를 한 번에 크게 수정
- 리팩토링과 기능 추가와 버그 수정을 한 PR에 섞기

## 9. main 병합 전/후 알림 규칙

PR을 `main`에 병합하기 전에는 반드시 팀원에게 알립니다.

병합 전 알림 예시:

```text
내 PR을 main에 병합하려고 해.
수정 범위: apps/gateway/src/lib/report-composer.ts, EasyReportView.vue
지금 같은 파일 작업 중이면 말해줘.
```

팀원이 같은 파일을 작업 중이면 바로 병합하지 말고 먼저 조율합니다. 특히 아래 파일은 충돌 가능성이 높습니다.

- `apps/gateway/src/lib/report-composer.ts`
- `apps/agent/app/services/scenario_classifier.py`
- `apps/agent/app/services/fact_arbitration.py`
- `apps/agent/app/services/analysts/fault_ratio_analyst.py`
- `apps/worker/worker/frame_analysis.py`
- `SYSTEM_OVERVIEW.md`
- `DEVELOPMENT_PROMPT.md`

병합 후에는 팀원에게 최신 `main`을 가져오라고 알립니다.

병합 후 알림 예시:

```text
main 병합 완료.
작업 시작 전 또는 진행 중인 브랜치에서 아래 순서로 최신 main 반영해줘.

git checkout main
git pull origin main
git checkout feature/your-task
git merge main
```

팀원이 아직 자기 브랜치를 만들지 않았다면 아래처럼 시작합니다.

```powershell
git checkout main
git pull origin main
git checkout -b feature/your-task
```

작업 완료 응답이나 인수인계 메시지에는 필요할 때 아래 한 줄을 포함합니다.

```text
main 병합 전에는 팀원에게 병합 예정임을 알리고, 병합 후에는 팀원에게 main pull 후 작업 브랜치에 반영하라고 안내하세요.
```

## 10. PR 리뷰 기준

리뷰할 때는 아래를 우선 확인합니다.

- 사용자가 보는 결과가 의도대로 바뀌었는지
- Agent 판단 구조가 특정 테스트 케이스에만 맞춰지지 않았는지
- 법률/KNIA/판례 근거가 사고 유형과 맞는지
- `.env`나 키, 영상 원본 같은 민감/대용량 파일이 들어가지 않았는지
- `SYSTEM_OVERVIEW.md` 또는 `DEVELOPMENT_PROMPT.md` 업데이트가 필요한 변경인지
- 검증 명령이 충분한지

문제가 있으면 GitHub PR에 코멘트를 남기고, 수정 후 다시 확인합니다.

## 11. 병합 후 절차

PR이 `main`에 병합되면 각자 로컬을 최신화합니다.

```powershell
git checkout main
git pull origin main
```

이미 끝난 작업 브랜치는 필요하면 삭제합니다.

```powershell
git branch -d feature/my-task
git push origin --delete feature/my-task
```

삭제는 선택입니다. 아직 이어서 작업할 브랜치라면 유지합니다.

## 12. 충돌이 났을 때

충돌이 나면 아래 순서로 처리합니다.

1. 충돌 파일을 열어 양쪽 변경 내용을 비교합니다.
2. 내가 만든 변경과 팀원이 만든 변경 중 어떤 것이 최신 의도인지 확인합니다.
3. 둘 다 필요한 경우 직접 합칩니다.
4. 실행 또는 테스트로 깨지지 않았는지 확인합니다.
5. 충돌 해결 커밋을 남깁니다.

주의:

- `git reset --hard`를 함부로 사용하지 않습니다.
- 상대 작업을 이해하지 못한 상태에서 한쪽 변경을 통째로 버리지 않습니다.
- 충돌 파일이 `SYSTEM_OVERVIEW.md`나 `DEVELOPMENT_PROMPT.md`라면 문서 순서와 최신 내용을 함께 정리합니다.

## 13. 문서 업데이트 기준

아래가 바뀌면 `SYSTEM_OVERVIEW.md`를 함께 수정합니다.

- 서비스 책임 경계
- API route, DTO, DB schema
- Redis key, storage path
- 외부 API, 환경변수
- 실행 방법, 검증 방법
- 알려진 문제 또는 운영 리스크

아래가 바뀌면 `DEVELOPMENT_PROMPT.md`를 함께 수정합니다.

- 개발 진행 방식
- 역할 정의
- 검증 정책
- 보안 규칙
- 문서 동기화 규칙
- 서비스 책임 경계

협업 방식 자체가 바뀌면 이 문서(`docs/GITHUB_COLLABORATION_WORKFLOW.md`)도 같이 업데이트합니다.
