# 사용자 가치 점검 기준

이 문서는 Agent/MCP/Task-Plan-Goal 로드맵의 P12-3 단계에서 사용하는 사용자 가치 점검 기준이다. P12-3은 새 기능 개발이 아니라 P0~P11에서 만든 구조가 실제 사용자에게 사고 대응에 필요한 결과로 전달되는지 확인하는 최종 점검 단계다.

## 점검 범위

- Agent 결과가 법률 관점, 보험 처리, 확인 근거, 추가 확인 항목으로 분리되어 있는지 확인한다.
- 단순히 "확인 필요"만 반복하지 않고, 확인된 사고축이 있으면 가능한 판단 범위와 조건부 분기를 제시하는지 확인한다.
- KNIA, 법령, 영상 관찰값이 사고 대분류와 직접 충돌 대상에 맞게 표시되는지 확인한다.
- Gateway easy-report 조립 과정에서 내부 trace, raw key, 모델 메타데이터가 사용자 화면에 노출되지 않는지 확인한다.
- Frontend 표시 계층에서 기술 키, 영어 fallback, raw JSON이 사용자 문구로 새지 않는지 확인한다.
- Reference metrics fixture로 직접 충돌 대상, 사고 대분류, 오염 방지, 조건부 분기 coverage를 반복 확인한다.

## 실행 방법

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_user_value_readiness.ps1 -SkipDockerBuild
```

Docker 서비스가 꺼져 있거나 최신 이미지가 필요한 경우 `-SkipDockerBuild`를 빼고 실행한다.

## 완료 기준

- Agent 사용자 가치 계약 테스트가 통과한다.
- Reference metrics fixture가 threshold 기준을 통과한다.
- Gateway 테스트와 빌드가 통과한다.
- Frontend display/chat 표시 점검과 빌드가 통과한다.
- 실패한 항목이 있으면 P12-3 완료로 처리하지 않고 같은 단계의 보정 작업으로 남긴다.
