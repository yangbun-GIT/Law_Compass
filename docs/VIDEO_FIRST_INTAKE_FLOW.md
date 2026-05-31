# Video-First Intake Flow

LawCompass 분석 입력은 긴 자유서술을 먼저 요구하지 않고, 사용자가 사고 대분류와 가능한 세부유형을 먼저 고른 뒤 영상과 선택 설명을 더하는 흐름을 사용한다.

## User Flow

1. **사고 대분류 선택**
   - `car_vs_car`
   - `car_vs_person`
   - `car_vs_bicycle`
   - `car_vs_two_wheeler`
   - `single_vehicle`
   - `parking_or_stationary`
   - `unknown`
2. **세부 사고유형 선택**
   - 대분류별 후보를 다르게 보여준다.
   - 모든 세트에는 `잘 모르겠어요`를 제공한다.
3. **영상 업로드**
   - 영상은 사고 판단의 핵심 근거로 사용한다.
   - 기존 text-only 분석 경로는 유지한다.
4. **선택 자연어 설명**
   - 자연어 설명은 `subjective_user_claim`이며 낮은 가중치로만 반영한다.
   - 고신뢰 영상 관찰값 또는 구조화된 후속 답변을 덮어쓰지 않는다.
5. **후속 질문**
   - Agent가 불확실한 핵심 사실만 최대 6개까지 생성한다.
   - 이미 사용자가 답했거나 영상에서 고신뢰로 확인된 항목은 다시 묻지 않는다.

## Payload Contract

```json
{
  "initial_intake": {
    "accident_major_category": "car_vs_car",
    "preliminary_accident_type": "lane_change_collision",
    "video_upload_id": "upload-id",
    "natural_language_description": "선택 입력",
    "natural_language_policy": {
      "weight": "low",
      "source_type": "subjective_user_claim",
      "can_override_video": false,
      "can_override_structured_followup": false
    }
  }
}
```

`car_vs_two_wheeler`는 사용자 입력 계약에서는 유지하고, Agent 내부 KNIA party guard에서는 `car_vs_motorcycle`로 정규화한다. `parking_or_stationary`는 주정차 사고 축을 강화하되 KNIA party guard는 `car_vs_car`로 둔다.

## Fact Priority

| Source | Weight | Note |
| --- | ---: | --- |
| selected_major_category | 0.85 | KNIA party guard prior |
| selected_preliminary_accident_type | 0.70 | scenario prior |
| video_observation | up to 0.90 | confidence and frame refs required |
| structured_followup_answer | 0.85 | higher than natural text |
| natural_language_claim | 0.30 | cannot override video or follow-up |
| knia_evidence | 0.55 | reference basis, not user fact |
| legal_evidence | 0.50 | explanatory basis |

## Agent Output Contract

When core facts remain unclear, the Agent returns:

```json
{
  "analysis_status": "provisional",
  "followup_required": true,
  "initial_intake_summary": {
    "accident_major_category": "car_vs_car",
    "preliminary_accident_type": "lane_change_collision",
    "natural_language_used_as": "low_weight_supporting_claim"
  },
  "uncertain_facts": [
    {
      "field": "turn_signal",
      "label": "방향지시등",
      "impact": "fault_adjustment",
      "reason": "차로변경 사고의 주요 가감요소입니다.",
      "confidence": 0.55
    }
  ],
  "followup_questions_structured": []
}
```

The frontend can display the existing guided questionnaire or `missing_info.questions` and submit answers through the existing reanalysis endpoint. Follow-up answers become structured facts and are weighted above the original natural language description.

## Limits

- Video may not show signal lights, turn signals, or counterpart behavior clearly.
- Natural language can clarify context but does not decide observable physical facts by itself.
- If high-confidence video evidence conflicts with user follow-up answers, the result should be presented as `needs_review` or conditional instead of silently overwriting one side.
