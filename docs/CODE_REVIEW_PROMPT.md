# LawCompass 코드 리뷰 프롬프트

상태: active/reference
용도: 교수님, 팀원, 또는 사용자가 코드 리뷰를 요청했을 때 우선 적용하는 리뷰 기준

## 적용 조건

사용자가 아래와 같이 요청하면 이 문서를 먼저 읽고 리뷰를 시작한다.

- 코드 리뷰
- PR 리뷰
- 변경사항 검토
- 교수님 리뷰 대비 점검
- 팀원 커밋이 제대로 반영됐는지 확인
- 특정 커밋, 브랜치, 파일, 기능의 문제점 점검

리뷰 요청이 명확하면 바로 코드를 수정하지 않는다. 먼저 결함, 회귀 위험, 누락된 검증, 문서 불일치, 운영 리스크를 찾고 사용자에게 결과를 보고한다. 사용자가 수정까지 요청했거나, 치명적 결함을 즉시 고쳐야 하는 상황이면 리뷰 결과를 근거로 최소 수정한다.

## 리뷰 역할

리뷰어는 LawCompass의 Principal Software Architect 관점에서 판단한다. 단순 스타일 점검보다 실제 동작 실패, 사고 분석 품질 저하, 보안 문제, 협업 충돌, 배포 실패 가능성을 우선한다.

필요한 경우 아래 관점을 짧게 적용한다.

| 관점 | 집중 지점 |
| --- | --- |
| Product Flow Reviewer | 사용자가 케이스 생성, 영상 업로드, 분석 결과 확인을 끝까지 진행할 수 있는지 |
| Backend/API Reviewer | Gateway route, DTO, DB query, Redis, 내부 Agent 호출 계약이 깨지지 않았는지 |
| Agent Quality Reviewer | 영상 관찰값, Task-Plan-Goal, evidence routing, 과실비율 판단이 특정 케이스에 과적합되지 않았는지 |
| Frontend Reviewer | 화면 상태, 라우팅, API base URL, 오류 표시, 모바일/정적 배포 경로가 안전한지 |
| DevOps/SRE Reviewer | Docker Compose, Caddy, OCI/GitHub Pages, env, health check, migration, 배포 스크립트가 재현 가능한지 |
| Security Reviewer | secret, 사용자 비밀번호, 원본 영상, 내부 경로, NAS/SFTP 정보가 노출되지 않는지 |
| Test/Regression Reviewer | 변경 범위에 맞는 테스트가 있고 기존 핵심 회귀를 깨지 않는지 |

## 필수 사전 확인

1. `DEVELOPMENT_PROMPT.md`, `SYSTEM_OVERVIEW.md`, `docs/GITHUB_COLLABORATION_WORKFLOW.md`, `docs/README.md`를 읽는다.
2. 리뷰 대상이 Agent, MCP-like tool, Task-Plan-Goal, video observation, judgment contract를 건드리면 `docs/AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md`를 읽는다.
3. 배포, OCI, GitHub Pages, 운영 스크립트가 대상이면 `ORACLE_CLOUD_FREE_TIER_DEPLOYMENT.md`, `GITHUB_PAGES_FRONTEND_DEPLOYMENT.md`, `docs/OPERATIONS.md`, `docs/VERIFICATION_COMMANDS.md`를 필요한 만큼 읽는다.
4. 리뷰 대상 commit range를 명확히 잡는다. 예: `git diff --stat base..HEAD`, `git log --oneline base..HEAD`.
5. 리뷰 전 `git status --short --branch`로 로컬 미커밋 변경과 stash 존재 여부를 확인한다.

## 리뷰 우선순위

리뷰 결과는 아래 순서로 찾고 보고한다.

1. 실제 런타임 오류, 빌드 실패, 테스트 실패, 배포 실패
2. 인증/권한, secret 노출, 원본 영상/로그/대용량 파일 커밋
3. DB schema, migration, Redis key, storage path, env 변경 누락
4. API/DTO 계약 불일치, Frontend-Gateway-Agent-Worker 간 payload 불일치
5. Agent 판단 품질 저하, 근거 오염, 차대차/차대사람 오분류, 특정 테스트 케이스 과적합
6. GitHub Pages/OCI 같은 배포 문서와 실제 코드 설정 불일치
7. 단일 책임 원칙 위반, 불필요한 대규모 리팩터링, 중복 로직
8. 검증 부족, 문서 업데이트 누락, 팀원 협업 충돌 가능성

스타일, 문구, 파일 정렬 문제는 위 항목을 가리는 수준이 아니면 후순위로 둔다.

## LawCompass 특화 체크리스트

### 구조와 책임

- Frontend는 표시와 사용자 입력에 집중하고, 판단 로직을 임의로 확정하지 않는가?
- Gateway는 인증, DB, 내부 호출 조율을 담당하고, Agent 판단을 중복 구현하지 않는가?
- Agent는 사고 판단, evidence routing, KNIA/법령/판례 근거 품질을 담당하는가?
- Worker는 영상 파일 검사, 프레임 추출, YOLO/OpenAI 관찰값 생성을 담당하는가?
- 변경이 서비스 경계를 바꿨다면 `SYSTEM_OVERVIEW.md`가 갱신됐는가?

### Agent와 영상 판단

- 영상 관찰값은 사고 대상, 충돌 지점, 진행 방향, 신호 가시성, 차선/중앙선 같은 보편 필드로 일반화됐는가?
- 횡단보도, 사람, 자전거, 신호등이 화면에 보인다는 이유만으로 사고 당사자로 승격하지 않는가?
- 사용자 입력과 영상 관찰값이 충돌할 때 한쪽을 조용히 덮어쓰지 않고 보류/확인/조건부로 처리하는가?
- KNIA/법령/판례 근거가 사고축과 맞지 않으면 1차 근거처럼 표시하지 않는가?
- 특정 사고 샘플을 맞추기 위한 하드코딩이나 키워드 과적합이 없는가?

### 배포와 운영

- GitHub Pages는 정적 프론트만 배포하고, Gateway/Agent/Worker/DB/Redis는 별도 서버가 필요하다는 한계가 문서와 env에 반영됐는가?
- OCI 배포 문서와 스크립트가 실제 compose 파일, env 파일, Caddy 설정과 맞는가?
- 운영 문서가 실제 secret 값을 포함하지 않고 placeholder만 사용하는가?
- Docker compose, migration, KNIA import, health check 순서가 재현 가능한가?

### 보안과 협업

- `.env`, API key, JWT secret, NAS password, 원본 영상, AI-Hub 원천 데이터, YOLO 가중치가 커밋되지 않았는가?
- 커밋 메시지와 PR 제목은 한국어로 이해 가능한가?
- 팀원이 웹 디자인을 수정 중이면 Agent/영상 작업이 frontend 표시 변경을 덮어쓰지 않는가?

## 검증 기준

리뷰는 가능한 한 실제 명령으로 근거를 확보한다.

문서/설정 중심 변경:

```powershell
git diff --check
python scripts/check_markdown_links.py --strict
python scripts/check_principle_compliance.py
python scripts/check_staged_safety.py
```

Frontend 변경:

```powershell
cd apps/frontend
npm run build
npm run test:display
```

Gateway 변경:

```powershell
cd apps/gateway
npm test
npm run build
```

Agent/Worker/전체 흐름 변경:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_agent_regression.ps1 -SkipDockerBuild
powershell -ExecutionPolicy Bypass -File scripts\verify_core.ps1 -SkipDockerBuild
```

검증을 실행하지 못하면 이유와 남은 리스크를 명확히 적는다.

## 출력 형식

리뷰 결과는 findings를 먼저 쓴다.

```text
Findings
- [심각도] 파일:라인 - 문제 설명, 실제 영향, 수정 방향

Open Questions
- 확인이 필요한 의사결정이나 외부 조건

Verification
- 실행한 명령과 결과
- 실행하지 못한 명령과 이유

Summary
- 변경 범위에 대한 짧은 총평
```

심각도 기준:

| 심각도 | 의미 |
| --- | --- |
| Critical | 실행 불가, 데이터 손상, secret 노출, 인증 우회, 핵심 분석 결과 붕괴 |
| High | 주요 사용자 흐름 실패, 배포 실패, Agent 근거/사고축 오염, DB/API 계약 깨짐 |
| Medium | 특정 조건에서 오동작, 검증 누락, 문서와 코드 불일치, 유지보수 위험 |
| Low | 스타일, 문구, 작은 중복, 후속 정리 권장 |

문제가 없으면 "명확한 결함은 발견하지 못했다"라고 말하고, 남은 테스트 공백이나 확인하지 못한 영역을 적는다.
