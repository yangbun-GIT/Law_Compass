# 프로젝트 원칙 준수 점검 및 보강 백로그

작성 기준일: 2026-05-31
반영 상태 업데이트: 2026-06-10

이 문서는 외부 공유 파일로 관리되던 `PROJECT_PRINCIPLE_COMPLIANCE_BACKLOG.md`의 내용을 저장소 안에서 추적하기 위해 추가했다. 목적은 당장 대규모 리팩터링을 강제하는 것이 아니라, LawCompass의 기존 구조를 유지하면서 원칙 위반 가능성이 커지는 지점을 자동 점검과 문서 동기화로 줄이는 것이다.

## 현재 판단

- Frontend, Gateway, Agent, Worker, DB/Infra 경계는 현재 구조와 맞다.
- Agent 내부도 입력 정규화, 대분류 라우팅, KNIA/RAG, evidence, judgment, report 흐름으로 분리되어 있다.
- 다만 문서 위치 안내, 링크 점검, 큰 파일 감시, fallback finality 점검, staged secret 점검은 반복 가능한 도구가 부족했다.

## P0. 문서 시작점과 링크 신뢰도

| 항목 | 상태 | 처리 |
| --- | --- | --- |
| 문서 선택 기준 부재 | 보강 완료 | [README.md](README.md)에 문서 선택 가이드와 새 문서 배치 규칙을 추가했다. |
| 문서 링크 깨짐 점검 부재 | 보강 완료 | `scripts/check_markdown_links.py`를 추가했다. 기본은 보고 모드이고 `--strict`로 실패 처리할 수 있다. |
| 문서-코드 동기화 점검 확장 | 보강 완료 | `scripts/check_document_code_sync.py`가 새 문서와 원칙 점검 스크립트를 확인한다. |

## P1. SRP 위험 파일 감시

| 항목 | 상태 | 처리 |
| --- | --- | --- |
| 대형 파일 즉시 분리 강제 위험 | 정책 유지 | 라인 수만으로 즉시 리팩터링하지 않는다. 기능을 수정할 때 SRP 기준으로 작게 분리한다. |
| SRP 위험 파일 반복 확인 부재 | 보강 완료 | `scripts/check_srp_file_sizes.py`를 추가해 watchlist 기반 경고를 출력한다. |

주요 watchlist:

- `apps/gateway/src/lib/report-composer.ts`
- `apps/frontend/src/composables/useCaseWorkspace.ts`
- `apps/frontend/src/views/AdminAgentTestView.vue`
- `apps/agent/app/services/input_normalizer.py`
- `apps/agent/app/services/scenario_classifier.py`
- `apps/agent/app/services/fact_arbitration.py`
- `apps/agent/app/services/knia/knia_matcher.py`
- `apps/agent/app/services/knia/knia_json_repository.py`
- `apps/worker/worker/frame_analysis.py`
- `apps/worker/worker/yolo_frame_analysis.py`

## P2. Agent 안전성 원칙

| 항목 | 상태 | 처리 |
| --- | --- | --- |
| bounded ReAct / Task-Plan-Goal / MCP-like registry 원칙 | 유지 | [AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md](AGENT_MCP_TASK_PLAN_GOAL_ROADMAP.md)를 작업 시작 문서로 유지한다. |
| fallback이 final처럼 보이는 문제 | 지속 감시 | judgment/evidence/report 변경 시 기존 Agent regression과 사용자 가치 점검을 유지한다. |
| 영상 관찰값 오염 가능성 | 지속 감시 | video observation은 직접 접촉 근거와 context-only 구분을 유지한다. |

## P3. 자동 점검 보강

| 항목 | 상태 | 처리 |
| --- | --- | --- |
| 문서-코드 동기화 | 기존 + 확장 | `scripts/check_document_code_sync.py` |
| Markdown link check | 추가 완료 | `scripts/check_markdown_links.py` |
| SRP line count warning | 추가 완료 | `scripts/check_srp_file_sizes.py` |
| staged secret / 금지 파일 점검 | 추가 완료 | `scripts/check_staged_safety.py` |
| 통합 원칙 점검 | 추가 완료 | `scripts/check_principle_compliance.py` |

## 실행 기준

일반 문서/원칙 작업 후:

```powershell
python scripts/check_principle_compliance.py
git diff --check
```

문서 이동이나 링크가 많은 작업 후:

```powershell
python scripts/check_markdown_links.py --strict
```

커밋 직전:

```powershell
python scripts/check_staged_safety.py
```

## 비변경 범위

이번 백로그 반영은 API route, DTO, DB schema, Redis key, storage path, 외부 API 계약, Agent 판단 로직을 변경하지 않는다. 목적은 구조 변경이 아니라 원칙 준수 상태를 반복 확인할 수 있게 만드는 것이다.
