import { describe, expect, it } from "vitest";
import { composeEasyFallback, composeReanalysisChangeCard, enrichEasyReport, sanitizeEasyReport } from "../src/lib/report-composer.js";

describe("report composer", () => {
  it("adds a user-safe evidence reliability card without raw claim internals", () => {
    const report = sanitizeEasyReport({ headline: "테스트 리포트" });
    const enriched = enrichEasyReport(report, {
      claim_evidence: {
        coverage_level: "high",
        coverage_ratio: 0.9,
        claim_count: 10,
        supported_claim_count: 9,
        unsupported_claim_count: 0,
        weak_claim_count: 1,
        unsupported_claims: [{ claim_id: "x", support_level: "unsupported" }],
        warnings: ["일부 판단은 간접 근거만 있어 추가 확인이 필요합니다."],
      },
      evidence_audit: {
        claim_evidence_coverage: { level: "high", ratio: 0.9 },
      },
    });

    const text = JSON.stringify(enriched);
    const reliabilityCard = enriched.evidence_reliability_card!;
    expect(reliabilityCard.level_label).toBe("높음");
    expect(reliabilityCard.summary).toContain("주요 판단 10개");
    expect(reliabilityCard.notice).toBe("이 카드는 판단 문장과 근거 문서가 얼마나 연결됐는지 보여줍니다.");
    expect(text).not.toContain("claim_id");
    expect(text).not.toContain("evidence_refs");
    expect(text).not.toContain("support_level");
  });

  it("adds expert guidance sections as a user-safe legal and insurance card", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      expert_guidance_sections: {
        version: "expert-guidance-sections-v1",
        status: "needs_more_facts",
        summary: "후미추돌 사고에 대해 참고용 예상 범위를 정리했습니다.",
        legal_prediction: {
          title: "법률 관점 예상",
          summary: "안전거리 유지 의무와 정차 사유를 함께 봅니다.",
          fault_range_label: "내 책임 10~30% / 상대 70~90% 참고",
          civil_points: ["정차 여부", "후방 추돌 여부"],
          criminal_points: ["인명피해 여부 확인"],
          basis: [
            {
              family_label: "KNIA 기준",
              title: "후방 추돌 기준",
              reason: "정차 차량 후방 추돌과 연결됩니다.",
              chunk_id: "internal-knia-id",
            },
          ],
          limits: ["확정 판단이 아닌 참고용 예상입니다."],
        },
        insurance_prediction: {
          title: "보험 처리 예상",
          summary: "대물 접수와 과실비율 협의를 준비합니다.",
          expected_steps: ["보험사 사고 접수", "블랙박스 원본 제출"],
          documents: ["블랙박스 원본", "차량 파손 사진"],
        },
        missing_facts: {
          title: "추가 확인 필요",
          items: ["정차 사유", "충돌 직전 속도"],
        },
        notice: "실제 결과는 보험사와 법원의 판단에 따라 달라질 수 있습니다.",
      },
    });

    const card = (enriched as any).expert_guidance_card;
    const text = JSON.stringify(card);
    expect(card.status_label).toBe("추가 확인 필요");
    expect(card.legal.fault_range_label).toBe("내 책임 10~30% / 상대 70~90% 참고");
    expect(card.insurance.steps).toContain("보험사 사고 접수");
    expect(card.basis[0].family_label).toBe("KNIA 기준");
    expect(card.missing_items).toContain("정차 사유");
    expect(text).not.toContain("expert-guidance-sections-v1");
    expect(text).not.toContain("chunk_id");
    expect(text).not.toContain("internal-knia-id");
  });

  it("adds case-focus notes to expert basis display from legal points", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      expert_guidance_sections: {
        status: "needs_more_facts",
        legal_prediction: {
          summary: "후방 차량 안전거리와 비접촉 유발 가능성을 검토합니다.",
          fault_range_label: "내 책임 10~30% / 상대 70~90% 참고",
          civil_points: ["자전거 비접촉 유발", "후방 차량 안전거리", "시간적 여유"],
          criminal_points: [],
          basis: [
            {
              family_label: "법률 근거",
              title: "도로교통법 안전거리 유지 의무",
              reason: "정차 또는 감속 중 뒤에서 추돌된 사고와 직접 관련된 확인 기준입니다.",
            },
          ],
          limits: ["확정 판단이 아닌 참고용 예상입니다."],
        },
        insurance_prediction: {},
        missing_facts: { items: [] },
      },
    });

    const reason = (enriched as any).expert_guidance_card.basis[0].reason;
    expect(reason).toContain("자전거의 비접촉 유발 여부");
    expect(reason).toContain("뒤차의 반응 시간");
  });

  it("preserves expert basis source quality without exposing internal ids", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      expert_guidance_sections: {
        status: "needs_more_facts",
        legal_prediction: {
          summary: "review",
          fault_range_label: "my 10~30",
          civil_points: ["safe distance"],
          criminal_points: [],
          basis: [
            {
              family_label: "KNIA 기준",
              title: "Collected KNIA reference",
              reason: "A collected source basis.",
              source_quality: "collected_original",
              source_quality_label: "수집 KNIA 원문 기준",
              source_review_note: "원문 링크가 있는 근거입니다.",
              source_url: "https://accident.knia.or.kr/myaccident-content?chartNo=car41-1",
              needs_original_source_review: false,
              chunk_id: "internal-knia-id",
            },
          ],
        },
        insurance_prediction: {},
        missing_facts: { items: [] },
      },
    });

    const card = (enriched as any).expert_guidance_card;
    const text = JSON.stringify(card);
    expect(card.basis[0].source_quality).toBe("collected_original");
    expect(card.basis[0].source_quality_label).toBe("수집 KNIA 원문 기준");
    expect(card.source_summary).toBe("원문 링크가 있는 근거를 우선 표시했습니다.");
    expect(card.basis[0].source_url).toContain("https://accident.knia.or.kr");
    expect(text).not.toContain("chunk_id");
    expect(text).not.toContain("internal-knia-id");
  });

  it("keeps user-safe missing-info questions usable after sanitizing", () => {
    const report = sanitizeEasyReport({
      missing_info: {
        title: "더 정확한 분석을 위해 필요한 정보",
        questions: [
          {
            field: "injury",
            label: "인명피해 여부",
            question: "다친 사람이 있나요?",
            input_type: "single_choice",
            options: ["다친 사람 없음", "내가 다침"],
          },
        ],
      },
      input_requirements: { blocking_fields: ["injury"] },
    });

    expect(report.missing_info.questions[0].field).toBe("injury");
    expect(report.missing_info.questions[0].question).toBe("다친 사람이 있나요?");
    expect(JSON.stringify(report)).not.toContain("input_requirements");
    expect(JSON.stringify(report)).not.toContain("blocking_fields");
  });

  it("prioritizes remaining missing-info questions for the next user action", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({
      headline: "report",
      missing_info: {
        title: "더 정확한 분석을 위해 필요한 정보",
        questions: [
          { field: "turn_signal", label: "방향지시등 사용", question: "방향지시등을 켰나요?", options: ["켰음", "켜지 않음"] },
          { field: "stopped", label: "정차 여부", question: "정차 중이었나요?", options: ["정차 중", "주행 중"] },
          { field: "unknown_internal_field", label: "internal", question: "raw?" },
          { field: "injury", label: "인명피해 여부", question: "다친 사람이 있나요?", options: ["없음", "있음"] },
        ],
      },
    }), {});

    const questions = (enriched as any).missing_info.questions;
    expect(questions.map((item: any) => item.field)).toEqual(["stopped", "injury", "turn_signal"]);
    expect((enriched as any).missing_info.items ?? []).not.toContain("정차 중이었나요?");
    expect((enriched as any).missing_info.items ?? []).not.toContain("다친 사람이 있나요?");
    expect(questions[0].priority_label).toBe("우선 확인");
    expect((enriched as any).missing_info.next_focus.label).toBe("정차 여부");
    expect((enriched as any).missing_info.priority_items[0].reason).toContain("후방 추돌");
    expect(JSON.stringify(enriched)).not.toContain("unknown_internal_field");
  });

  it("prioritizes rear-end decision facts before follow-up damage details", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({
      headline: "report",
      missing_info: {
        questions: [
          { field: "damage_level", label: "파손 정도", question: "파손 정도는 어느 정도인가요?", options: ["경미", "심함"] },
          { field: "sudden_brake", label: "급정거 여부", question: "충돌 직전 급정거가 있었나요?", options: ["예", "아니오"] },
          { field: "injury", label: "인명피해 여부", question: "다친 사람이 있나요?", options: ["예", "아니오"] },
          { field: "opponent_behavior", label: "상대 차량 행동", question: "상대 차량은 어떻게 움직였나요?", options: ["뒤에서 추돌", "차선 변경"] },
        ],
      },
    }), {});

    expect((enriched as any).missing_info.questions.map((item: any) => item.field)).toEqual([
      "opponent_behavior",
      "sudden_brake",
      "injury",
      "damage_level",
    ]);
    expect((enriched as any).missing_info.next_focus.label).toBe("상대 차량 행동");
  });

  it("prioritizes party-specific signal questions over generic follow-up details", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({
      headline: "report",
      missing_info: {
        questions: [
          { field: "injury", label: "인명피해 여부", question: "다친 사람이 있나요?", options: ["예", "아니오"] },
          { field: "signal_state", label: "신호 상태", question: "사고 당시 전체 신호 상태는 어땠나요?", options: ["녹색", "황색", "적색"] },
          { field: "opponent_signal", label: "상대 차량 신호", question: "상대 차량이 교차로에 진입할 때 신호는 무엇이었나요?", options: ["녹색", "황색", "적색"] },
          { field: "user_signal", label: "내 차량 신호", question: "내 차량이 교차로에 진입할 때 신호는 무엇이었나요?", options: ["녹색", "황색", "적색"] },
        ],
      },
    }), {});

    expect((enriched as any).missing_info.questions.map((item: any) => item.field)).toEqual([
      "opponent_signal",
      "signal_state",
      "user_signal",
      "injury",
    ]);
    expect((enriched as any).missing_info.next_focus.label).toBe("상대 차량 신호");
  });

  it("keeps signal-state follow-up ahead of injury in signal-context accidents", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({
      headline: "report",
      missing_info: {
        questions: [
          { field: "signal_state", label: "신호 상태", question: "사고 당시 신호 상태는 어땠나요?", options: ["녹색", "황색", "적색"] },
          { field: "injury", label: "인명피해 여부", question: "다친 사람이 있나요?", options: ["예", "아니오"] },
        ],
      },
    }), {});

    expect((enriched as any).missing_info.questions.map((item: any) => item.field)).toEqual([
      "signal_state",
      "injury",
    ]);
  });

  it("maps raw required-input fields to safe Korean labels before prioritizing", () => {
    const enriched: any = composeEasyFallback({
      headline: "report",
      input_requirements: {
        questions: [
          { field: "stopped", label: "stopped", question: "정차 중이었나요?", input_type: "single_choice" },
          { field: "reported_speed_kmh", label: "reported_speed_kmh", question: "속도는 몇 km/h였나요?" },
        ],
      },
    }, {});

    const text = JSON.stringify(enriched);
    expect((enriched as any).missing_info.questions.map((item: any) => item.field)).toEqual(["stopped"]);
    expect((enriched as any).missing_info.priority_items[0].label).toBe("정차 여부");
    expect(text).not.toContain("reported_speed_kmh");
    expect(text).not.toContain("\"label\":\"stopped\"");
  });

  it("uses centerline obstacle context instead of generic extra-facts wording", () => {
    const enriched: any = composeEasyFallback({
      scenario_type: "parking_or_stopped_vehicle_accident",
      accident_summary: "중앙선 장애물 회피 중 대향 차량과 충돌한 사고",
      structured_facts: {
        accident_party_type: "car_vs_car",
        accident_type: "centerline_obstacle_collision",
        centerline_crossed: true,
        road_obstruction: true,
        illegal_parking_obstruction: true,
        opponent_behavior: "마주오던 차량이 그대로 진행해 충돌",
      },
      fault_ratio: {
        my: 30,
        other: 70,
        key_factors: ["중앙선 침범 사유", "상대 차량 회피 가능성"],
      },
    }, {});

    expect(enriched.headline).toContain("중앙선");
    expect(enriched.headline).toContain("대향 차량");
    expect(enriched.headline).not.toContain("추가 사실");
    expect(Number((enriched as any).fault_explanation.my_percent)).toBe(30);
    expect(Number((enriched as any).fault_explanation.other_percent)).toBe(70);
    expect((enriched as any).fault_explanation.easy_explanation).toContain("도로 장애물");
  });

  it("shows conditional signal outcomes and hides pedestrian-target evidence for car-vs-car intersection crashes", () => {
    const enriched: any = composeEasyFallback({
      scenario_type: "intersection_signal_violation",
      accident_summary: "좌회전 중 황색 신호 전환 후 직진 차량과 충돌",
      structured_facts: {
        accident_party_type: "car_vs_car",
        collision_partner_type: "vehicle",
        intersection: true,
        ego_turn_direction: "left",
        user_signal: "yellow",
        signal_transition: "yellow_to_red",
        opponent_signal_visible: false,
        pedestrian_visible: true,
      },
      fault_ratio: {
        my: 80,
        other: 20,
        key_factors: ["신호 전환 시점", "상대 차량 진입 신호"],
        conditional_outcomes: [
          {
            label: "상대 차량 신호가 녹색 또는 정상 진행 신호인 경우",
            my_range: "70~90%",
            other_range: "10~30%",
            explanation: "내 차량의 황색 진입과 좌회전 양보 의무가 중심 쟁점입니다.",
            basis: ["내 차량 정지선 통과 시점", "상대 차량 신호"],
          },
          {
            label: "상대 차량도 적색 또는 신호위반으로 진입한 경우",
            my_range: "20~40%",
            other_range: "60~80%",
            explanation: "상대 차량 신호위반이 확인되면 상대 책임이 커질 수 있습니다.",
            basis: ["상대 차량 신호", "CCTV"],
          },
        ],
      },
      evidence: [
        { source_type: "legal", title: "신호 준수 의무", plain_summary: "교차로 신호와 진입 시점을 확인합니다." },
        { source_type: "legal", title: "보행자 보호 의무", plain_summary: "보행자 사고 기준입니다." },
      ],
    }, {});

    expect(enriched.headline).toContain("교차로");
    expect(enriched.headline).not.toContain("추가 사실");
    expect(enriched.conditional_outcome_card.cases).toHaveLength(2);
    expect(JSON.stringify(enriched.conditional_outcome_card)).toContain("70~90%");
    expect(JSON.stringify(enriched.legal_basis_cards)).toContain("교차로 신호");
    expect(JSON.stringify(enriched.legal_basis_cards)).not.toContain("보행자 보호");
  });

  it("removes raw field tokens from missing-info priority text", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({
      headline: "report",
      missing_info: {
        questions: [
          {
            field: "stopped",
            label: "stopped",
            question: "stopped 값을 확인해 주세요.",
            priority_reason: "stopped는 후방 추돌 판단에 필요합니다.",
          },
        ],
      },
    }), {});

    const text = JSON.stringify((enriched as any).missing_info.priority_items);
    expect(text).not.toContain("stopped");
    expect(text).toContain("정차 여부");
  });

  it("keeps missing-info checklist separate from selectable questions", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({
      headline: "report",
      missing_info: {
        title: "더 정확한 분석을 위해 필요한 정보",
        items: [
          "정차 중이었나요?",
          "사고 당시 블랙박스 원본을 보관해 주세요.",
          "정차 중이었나요?",
        ],
        questions: [
          { field: "stopped", label: "정차 여부", question: "정차 중이었나요?", options: ["정차 중", "주행 중"] },
        ],
      },
    }), {});

    expect((enriched as any).missing_info.questions.map((item: any) => item.question)).toEqual(["정차 중이었나요?"]);
    expect((enriched as any).missing_info.items).toEqual(["사고 당시 블랙박스 원본을 보관해 주세요."]);
  });

  it("replaces raw stored questions when a safer video question exists for the same field", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({
      headline: "report",
      missing_info: {
        questions: [
          {
            field: "opponent_behavior",
            label: "raw",
            question: "raw?",
            input_type: "single_choice",
            options: ["front"],
          },
        ],
      },
    }), {
      video_input_contract: {
        uncertain_observations: [
          {
            field: "opponent_behavior",
            value: "rear_collision",
            confidence: 0.8,
            frame_refs: ["frame_10.jpg", "frame_12.jpg"],
          },
        ],
        observation_quality_summary: {
          accepted_count: 0,
          uncertain_count: 1,
          ignored_count: 0,
          uncertain_reasons: { confidence_below_field_threshold: 1 },
        },
      },
    });

    const question = (enriched as any).missing_info.questions.find((item: any) => item.field === "opponent_behavior");
    expect(question.question).not.toBe("raw?");
    expect(question.question).toContain("상대 차량 행동");
    expect(question.options).not.toContain("front");
    expect(question.options.length).toBeGreaterThan(1);
    expect(JSON.stringify((enriched as any).missing_info)).not.toContain("front");
  });

  it("adds a user-safe agent process card without raw trace packets", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      agent_trace: {
        step_count: 2,
        steps: [
          { id: "input_normalization", phase: "perceive", status: "completed", packet: { fact_count: 3 } },
          { id: "reflection_loop", phase: "recover", status: "resolved", packet: { next_action: "finalize" } },
        ],
      },
      reflection_loop: {
        status: "resolved",
        next_action: "finalize",
        requery_attempted: true,
        requery_added_evidence_count: 1,
        final_missing_requirements: [],
        user_message: "부족한 근거를 재검색해 추가 근거 1개를 확인했고 판단 조건을 통과했습니다.",
        recovery_suggestions: ["보강할 항목은 없습니다."],
      },
      agent_judgment: { overall_status: "evidence_supported", decision_blockers: [] },
    });

    const processCard = enriched.agent_process_card!;
    expect(processCard.status_label).toBe("해결됨");
    expect(processCard.stats.find((item: any) => item.label === "추가 근거")?.value).toBe("1개");
    expect(processCard.steps.map((item: any) => item.label)).toContain("입력 정리");
    expect(processCard.steps.map((item: any) => item.label)).toContain("근거 보강 검토");
    expect(processCard.decision_notes.join(" ")).toContain("추가 근거 1개");
    expect(JSON.stringify(processCard)).not.toContain("packet");
    expect(JSON.stringify(processCard)).not.toContain("input_normalization");
    expect(JSON.stringify(processCard)).not.toContain("next_action");
  });

  it("summarizes reflection gaps with safe Korean labels", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      reflection_loop: {
        status: "reference_only",
        next_action: "present_reference_only",
        requery_attempted: true,
        requery_added_evidence_count: 0,
        final_missing_requirements: ["family:knia", "scenario_relevant_evidence"],
        blocking_fields: ["injury"],
        user_message: "확정 판단에 필요한 근거 조건이 남아 참고용으로 표시합니다.",
        recovery_suggestions: ["KNIA 과실비율 기준이 부족하면 사고 유형과 기준번호를 더 좁혀 확인해야 합니다."],
        initial_query_terms: ["rear_end_collision_internal_key"],
      },
      agent_judgment: { overall_status: "blocked_for_final", decision_blockers: ["missing evidence"] },
    });

    const processCard = enriched.agent_process_card!;
    const text = JSON.stringify(processCard);
    expect(processCard.status_label).toBe("참고용");
    expect(processCard.decision_notes.join(" ")).toContain("KNIA 과실 기준");
    expect(processCard.decision_notes.join(" ")).toContain("사고 유형 직접 근거");
    expect(processCard.decision_notes.join(" ")).toContain("인명피해 여부");
    expect(text).not.toContain("family:knia");
    expect(text).not.toContain("scenario_relevant_evidence");
    expect(text).not.toContain("rear_end_collision_internal_key");
  });

  it("adds a user-safe video fact explanation card without raw arbitration contracts", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      video_input_contract: {
        accepted_observations: [
          {
            field: "lane_change_actor",
            value: "opponent",
            confidence: 0.91,
            source: "frame_analysis:openai",
            frame_refs: ["frame_6.jpg", "frame_7.jpg"],
            reason: "opponent vehicle crossed lane marker",
          },
        ],
        uncertain_observations: [
          { field: "turn_signal", value: "unknown", confidence: 0.42, reason: "not visible" },
        ],
        fact_patch: { lane_change_actor: "opponent" },
        observation_quality_summary: {
          accepted_count: 1,
          uncertain_count: 1,
          ignored_count: 0,
          uncertain_reasons: { missing_frame_reference: 1 },
          accepted_single_frame_count: 0,
          accepted_multi_frame_count: 1,
        },
      },
      fact_arbitration: {
        applied_video_fields: ["lane_change_actor"],
        conflicts: [
          {
            field: "lane_change_actor",
            user_value: "user",
            video_value: "opponent",
            winner: "video",
            video_confidence: 0.91,
            frame_refs: ["frame_6.jpg"],
            reason: "video primary field",
          },
        ],
      },
    });

    const card = enriched.video_fact_explanation_card!;
    const text = JSON.stringify(card);
    expect(card.title).toBe("영상 기반 사실 반영");
    expect(card.applied_items[0].label).toBe("차선변경 주체");
    expect(card.applied_items[0].value).toBe("상대 차량");
    expect(card.applied_items[0].confidence).toBe("91%");
    expect(card.review_items[0].selected_source).toBe("영상");
    expect(card.review_items[0].status_label).toBe("영상 기준 반영");
    expect(card.review_items[0].input_label).toBe("내 차량");
    expect(card.review_items[0].video_label).toBe("상대 차량");
    expect(card.review_items[0].comparison).toContain("사용자 입력은 내 차량");
    expect(card.uncertain_items[0].label).toBe("방향지시등 사용");
    expect(card.quality_summary.status_label).toBe("일부 반영");
    expect(card.quality_summary.multi_frame_count).toBe(1);
    expect(card.quality_summary.hold_items[0].label).toBe("프레임 근거 없음");
    expect(card.stats[0]).toEqual({ label: "영상 관찰 후보", value: "2개" });
    const videoQuestion = (enriched as any).missing_info.questions[0];
    expect(videoQuestion.field).toBe("lane_change_actor");
    expect(videoQuestion.question).toContain(card.applied_items[0].label);
    expect(videoQuestion.options).toContain(card.applied_items[0].value);
    const qualityQuestion = (enriched as any).missing_info.questions.find((item: any) => item.field === "turn_signal");
    expect(qualityQuestion.question).toContain("충분히 확인하지 못했습니다");
    expect(qualityQuestion.options).toContain("켰음");
    expect(text).not.toContain("video_input_contract");
    expect(text).not.toContain("fact_arbitration");
    expect(text).not.toContain("frame_analysis:openai");
    expect(text).not.toContain("observation_quality_summary");
    expect(text).not.toContain("quality_gate");
    expect(text).not.toContain("frame_refs");
    expect(text).not.toContain("user_value");
    expect(text).not.toContain("video_value");
    expect(text).not.toContain("reason");
  });

  it("explains processed video with zero observations as no confirmed video fact", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      video_input_contract: {
        version: "agent-video-input-contract-v1",
        technical_metadata: {
          representative_frame_count: 12,
          duration_sec: 11.167,
        },
        accepted_observations: [],
        uncertain_observations: [],
        ignored_observations: [],
        observation_quality_summary: {
          accepted_count: 0,
          uncertain_count: 0,
          ignored_count: 0,
          uncertain_reasons: {},
        },
      },
    });

    const card = enriched.video_fact_explanation_card!;
    expect(card.summary).toContain("바로 판단에 반영할 수 있는 물리 사실은 확인되지 않았습니다");
    expect(card.quality_summary.status_label).toBe("확정 사실 없음");
    expect(card.quality_summary.representative_frame_count).toBe(12);
    expect(card.stats).toContainEqual({ label: "대표 프레임", value: "12장" });
    expect(card.stats).toContainEqual({ label: "영상 관찰 후보", value: "0개" });
    expect(card.applied_items).toEqual([]);
    expect(card.review_items).toEqual([]);
    expect(card.uncertain_items).toEqual([]);
  });

  it("surfaces accident event candidate even when no frame observation passes fact gates", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      video_input_contract: {
        version: "agent-video-input-contract-v1",
        technical_metadata: {
          representative_frame_count: 13,
          accident_event_summary: {
            impact_visible: true,
            event_frame_count: 4,
            pre_impact_frame_count: 2,
            post_impact_frame_count: 2,
          },
        },
        accepted_observations: [],
        uncertain_observations: [],
        ignored_observations: [],
        observation_quality_summary: {
          accepted_count: 0,
          uncertain_count: 0,
          ignored_count: 0,
          uncertain_reasons: {},
        },
      },
    });

    const card = enriched.video_fact_explanation_card!;
    expect(card.event_candidate).toBeTruthy();
    expect(card.event_candidate!.status_label).toBe("충돌 구간 후보 확인");
    expect(card.event_candidate!.frame_label).toBe("4장");
    expect(card.summary).toContain("사고 발생 구간 후보");
    expect(card.stats).toContainEqual({ label: "사고 시점 후보", value: "4장" });
    expect(card.applied_items).toEqual([]);
  });

  it("explains high-confidence video conflicts without applying them as final facts", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      video_input_contract: {
        accepted_observations: [
          {
            field: "stopped",
            value: false,
            confidence: 0.9,
            frame_refs: ["frame_1.jpg", "frame_3.jpg", "frame_5.jpg"],
          },
        ],
        fact_patch: { stopped: false },
        observation_quality_summary: {
          accepted_count: 1,
          uncertain_count: 0,
          ignored_count: 0,
          accepted_multi_frame_count: 1,
        },
      },
      fact_arbitration: {
        applied_video_fields: [],
        conflicts: [
          {
            field: "stopped",
            user_value: true,
            video_value: false,
            winner: "user",
            video_confidence: 0.9,
            frame_refs: ["frame_1.jpg", "frame_3.jpg", "frame_5.jpg"],
          },
        ],
      },
    });

    const card = enriched.video_fact_explanation_card!;
    const conflict = card.review_items[0];
    expect(conflict.label).toBe("정차 여부");
    expect(conflict.selected_source).toBe("사용자 입력");
    expect(conflict.selected_value).toBe("정차 중");
    expect(conflict.input_label).toBe("정차 중");
    expect(conflict.video_label).toBe("주행 중");
    expect(conflict.status_label).toBe("확인 후 사용자 입력 유지");
    expect(conflict.comparison).toContain("영상 관찰은 주행 중");
    expect(conflict.explanation).toContain("확인 질문");
    expect(conflict.confidence).toBe("90%");
    const question = (enriched as any).missing_info.questions[0];
    expect(question.field).toBe("stopped");
    expect(question.question).toContain("충돌 직전 내 차량이 완전히 정차 중이었나요");
    expect(question.question).toContain("영상 관찰은 주행 중");
    expect(question.question).toContain("기존 입력은 정차 중");
    expect(question.options).toContain("정차 중");
    expect(question.options).toContain("주행 중");
    expect(JSON.stringify(card)).not.toContain("user_value");
    expect(JSON.stringify(card)).not.toContain("video_value");
    expect(JSON.stringify(card)).not.toContain("frame_refs");
  });

  it("keeps direction-only video observations as supporting display items", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "direction-support" }), {
      video_input_contract: {
        version: "agent-video-input-contract-v1",
        technical_metadata: { representative_frame_count: 5 },
        accepted_observations: [],
        uncertain_observations: [],
        supporting_observations: [
          {
            field: "collision_direction",
            value: "front",
            confidence: 0.91,
            source: "frame_analysis:openai",
            frame_refs: ["frame_002.jpg"],
          },
        ],
        ignored_observations: [],
        observation_quality_summary: {
          accepted_count: 0,
          uncertain_count: 0,
          supporting_count: 1,
          ignored_count: 0,
          uncertain_reasons: {},
        },
      },
    });

    const card = (enriched as any).video_fact_explanation_card;
    const statMap = Object.fromEntries((card.stats || []).map((item: any) => [item.label, item.value]));
    expect(card.summary).toContain("참고 관찰값");
    expect(card.supporting_items[0].label).toBe("충돌 방향 참고");
    expect(card.supporting_items[0].value).toBe("앞쪽");
    expect(statMap["영상 관찰 후보"]).toBe("1개");
    expect(statMap["참고 관찰"]).toBe("1개");
    expect((enriched as any).missing_info?.questions ?? []).toEqual([]);
    expect(JSON.stringify(card)).not.toContain("frame_analysis:openai");
    expect(JSON.stringify(card)).not.toContain("frame_refs");
  });

  it("shows limited visual evidence as a supporting item without creating questions", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "limited-video" }), {
      video_input_contract: {
        version: "agent-video-input-contract-v1",
        technical_metadata: { representative_frame_count: 18 },
        accepted_observations: [],
        uncertain_observations: [],
        supporting_observations: [
          {
            field: "visual_evidence_limited",
            value: true,
            confidence: 1,
            source: "frame_analysis:openai",
            frame_refs: ["frame_001.jpg", "frame_002.jpg"],
          },
        ],
        ignored_observations: [],
        observation_quality_summary: {
          accepted_count: 0,
          uncertain_count: 0,
          supporting_count: 1,
          ignored_count: 0,
          uncertain_reasons: {},
        },
      },
    });

    const card = (enriched as any).video_fact_explanation_card;
    expect(card.summary).toContain("참고 관찰값");
    expect(card.supporting_items[0].label).toBe("영상 근거 제한");
    expect(card.supporting_items[0].value).toBe("직접 반영할 영상 사실 부족");
    expect(card.supporting_items[0].explanation).toContain("직접 판단에 반영");
    expect((enriched as any).missing_info?.questions ?? []).toEqual([]);
    expect(JSON.stringify(card)).not.toContain("frame_analysis:openai");
    expect(JSON.stringify(card)).not.toContain("frame_refs");
  });

  it("orders uncertain video questions by accident-flow priority", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      video_input_contract: {
        uncertain_observations: [
          { field: "turn_signal", value: "no", confidence: 0.9, frame_refs: ["frame_7.jpg", "frame_8.jpg"] },
          { field: "stopped", value: false, confidence: 0.6, frame_refs: ["frame_1.jpg"] },
          { field: "lane_change_actor", value: "opponent", confidence: 0.7, frame_refs: ["frame_5.jpg"] },
        ],
        observation_quality_summary: {
          accepted_count: 0,
          uncertain_count: 3,
          ignored_count: 0,
          uncertain_reasons: { confidence_below_field_threshold: 3 },
        },
      },
    });

    const fields = (enriched as any).missing_info.questions.map((item: any) => item.field);
    expect(fields.slice(0, 3)).toEqual(["stopped", "lane_change_actor", "turn_signal"]);
    expect((enriched as any).missing_info.priority_items[0].label).toBe("정차 여부");
    expect((enriched as any).missing_info.priority_items[0].priority_label).toBe("우선 확인");
    expect((enriched as any).video_fact_explanation_card.quality_summary.status_label).toBe("확인 필요");
  });

  it("prioritizes accident target and signal visibility before injury followups", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({
      headline: "report",
      missing_info: {
        questions: [
          { field: "injury", label: "injury", question: "injury?", options: ["yes", "no"] },
        ],
      },
    }), {
      video_input_contract: {
        uncertain_observations: [
          { field: "opponent_signal_visible", value: false, confidence: 0.72, frame_refs: ["frame_3.jpg"] },
          { field: "front_vehicle_stopped", value: true, confidence: 0.77, frame_refs: ["frame_4.jpg"] },
          { field: "pedestrian_visible", value: false, confidence: 0.75, frame_refs: ["frame_4.jpg"] },
        ],
      },
    });

    const fields = (enriched as any).missing_info.questions.map((item: any) => item.field);
    expect(fields.indexOf("opponent_signal_visible")).toBeLessThan(fields.indexOf("front_vehicle_stopped"));
    expect(fields.indexOf("front_vehicle_stopped")).toBeLessThan(fields.indexOf("pedestrian_visible"));
    expect(fields.indexOf("pedestrian_visible")).toBeLessThan(fields.indexOf("injury"));
  });

  it("shows video-confirmed fields separately from newly applied fields", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "confirmed" }), {
      video_input_contract: {
        version: "agent-video-input-contract-v1",
        technical_metadata: { representative_frame_count: 6 },
        accepted_observations: [
          {
            field: "opponent_behavior",
            value: "rear_collision",
            confidence: 0.9,
            source: "frame_analysis:openai",
            frame_refs: ["frame_008.jpg", "frame_012.jpg"],
          },
          {
            field: "stopped",
            value: true,
            confidence: 0.92,
            source: "frame_analysis:openai",
            frame_refs: ["frame_005.jpg", "frame_006.jpg"],
          },
        ],
        uncertain_observations: [],
        ignored_observations: [],
        fact_patch: { opponent_behavior: "rear_collision", stopped: true },
        observation_quality_summary: {
          accepted_count: 2,
          uncertain_count: 0,
          ignored_count: 0,
          uncertain_reasons: {},
          accepted_multi_frame_count: 2,
        },
      },
      fact_arbitration: {
        applied_video_fields: [],
        confirmed_fields: ["opponent_behavior", "stopped"],
        conflicts: [],
      },
    });

    const card = (enriched as any).video_fact_explanation_card;
    const statMap = Object.fromEntries((card.stats || []).map((item: any) => [item.label, item.value]));

    expect(card.summary).toContain("기존 입력과 같은 사실");
    expect(card.applied_items).toHaveLength(0);
    expect(card.confirmed_items).toHaveLength(2);
    expect(statMap["판단 반영"]).toBe("0개");
    expect(statMap["영상 확인"]).toBe("2개");
    expect(JSON.stringify(card.confirmed_items)).toContain("영상 관찰값이 기존 입력과 같은 방향");
    expect(JSON.stringify(card)).not.toContain("frame_analysis:openai");
    expect(JSON.stringify(card)).not.toContain("confirmed_fields");
  });

  it("keeps OpenAI frame-analysis display states consistent across zero, held, conflict, and applied samples", () => {
    const samples = [
      {
        name: "zero",
        result: {
          video_input_contract: {
            version: "agent-video-input-contract-v1",
            technical_metadata: { representative_frame_count: 12 },
            accepted_observations: [],
            uncertain_observations: [],
            ignored_observations: [],
            observation_quality_summary: { accepted_count: 0, uncertain_count: 0, ignored_count: 0, uncertain_reasons: {} },
          },
        },
        expected: { status: "확정 사실 없음", observed: "0개", applied: "0개", conflicts: "0개", held: "0개" },
      },
      {
        name: "held",
        result: {
          video_input_contract: {
            version: "agent-video-input-contract-v1",
            technical_metadata: { representative_frame_count: 6 },
            accepted_observations: [],
            uncertain_observations: [
              {
                field: "stopped",
                value: false,
                confidence: 0.81,
                source: "frame_analysis:openai",
                frame_refs: ["frame_001.jpg", "frame_003.jpg", "frame_005.jpg"],
                reason: "confidence_below_field_threshold",
              },
            ],
            ignored_observations: [],
            observation_quality_summary: {
              accepted_count: 0,
              uncertain_count: 1,
              ignored_count: 0,
              uncertain_reasons: { confidence_below_field_threshold: 1 },
            },
          },
        },
        expected: { status: "확인 필요", observed: "1개", applied: "0개", conflicts: "0개", held: "1개" },
        questionField: "stopped",
      },
      {
        name: "conflict",
        result: {
          video_input_contract: {
            version: "agent-video-input-contract-v1",
            technical_metadata: { representative_frame_count: 6 },
            accepted_observations: [
              {
                field: "stopped",
                value: false,
                confidence: 0.93,
                source: "frame_analysis:openai",
                frame_refs: ["frame_001.jpg", "frame_003.jpg", "frame_005.jpg"],
              },
            ],
            uncertain_observations: [],
            ignored_observations: [],
            fact_patch: { stopped: false },
            observation_quality_summary: {
              accepted_count: 1,
              uncertain_count: 0,
              ignored_count: 0,
              uncertain_reasons: {},
              accepted_multi_frame_count: 1,
            },
          },
          fact_arbitration: {
            applied_video_fields: [],
            conflicts: [
              {
                field: "stopped",
                user_value: true,
                video_value: false,
                winner: "user",
                video_confidence: 0.93,
                frame_refs: ["frame_001.jpg", "frame_003.jpg", "frame_005.jpg"],
              },
            ],
          },
        },
        expected: { status: "반영 가능", observed: "1개", applied: "0개", conflicts: "1개", held: "0개" },
        questionField: "stopped",
      },
      {
        name: "applied",
        result: {
          video_input_contract: {
            version: "agent-video-input-contract-v1",
            technical_metadata: { representative_frame_count: 6 },
            accepted_observations: [
              {
                field: "lane_change_actor",
                value: "opponent",
                confidence: 0.91,
                source: "frame_analysis:openai",
                frame_refs: ["frame_002.jpg", "frame_004.jpg"],
              },
            ],
            uncertain_observations: [],
            ignored_observations: [],
            fact_patch: { lane_change_actor: "opponent" },
            observation_quality_summary: {
              accepted_count: 1,
              uncertain_count: 0,
              ignored_count: 0,
              uncertain_reasons: {},
              accepted_multi_frame_count: 1,
            },
          },
          fact_arbitration: {
            applied_video_fields: ["lane_change_actor"],
            conflicts: [],
          },
        },
        expected: { status: "반영 가능", observed: "1개", applied: "1개", conflicts: "0개", held: "0개" },
      },
    ];

    for (const sample of samples) {
      const enriched = enrichEasyReport(sanitizeEasyReport({ headline: sample.name }), sample.result);
      const card = (enriched as any).video_fact_explanation_card;
      const statMap = Object.fromEntries((card.stats || []).map((item: any) => [item.label, item.value]));
      expect(card.title).toBe("영상 기반 사실 반영");
      expect(card.quality_summary.status_label).toBe(sample.expected.status);
      expect(statMap["영상 관찰 후보"]).toBe(sample.expected.observed);
      expect(statMap["판단 반영"]).toBe(sample.expected.applied);
      expect(statMap["입력 충돌 검토"]).toBe(sample.expected.conflicts);
      expect(statMap["확인 필요"]).toBe(sample.expected.held);
      expect(statMap["품질 상태"]).toBe(sample.expected.status);
      if (sample.questionField) {
        expect((enriched as any).missing_info.questions.some((item: any) => item.field === sample.questionField)).toBe(true);
      }
      const text = JSON.stringify(card);
      expect(text).not.toContain("frame_analysis:openai");
      expect(text).not.toContain("video_input_contract");
      expect(text).not.toContain("fact_arbitration");
      expect(text).not.toContain("frame_refs");
      expect(text).not.toContain("user_value");
      expect(text).not.toContain("video_value");
    }
  });

  it("summarizes reanalysis changes without exposing judgment internals", () => {
    const card = composeReanalysisChangeCard(
      {
        scenario_type: "rear_end_collision",
        fault_ratio: { my: 30, other: 70 },
        knia_primary_match: { chart_no: "차41-1", title: "후방 추돌" },
        knia_base_fault: { A: 0, B: 100 },
        knia_final_fault: { A: 0, B: 100 },
        knia_applied_adjustments: [],
        evidence: [
          { chunk_id: "prev-knia-1", source_type: "knia_fault_standard", title: "차41-1 후방 추돌" },
          { chunk_id: "prev-law-1", law_name: "도로교통법", title: "안전거리" },
        ],
        evidence_audit: {
          scenario_evidence_coverage: {
            coverage_level: "low",
            scenario_relevant_count: 1,
            missing_requirements: ["total_evidence", "family:knia"],
          },
        },
        agent_judgment: { overall_status: "needs_review" },
        required_input_questions: [{ field: "injury", question: "다친 사람이 있나요?" }],
      },
      {
        scenario_type: "rear_end_collision",
        fault_ratio: { my: 10, other: 90 },
        knia_primary_match: { chart_no: "차41-1", title: "후방 추돌" },
        knia_base_fault: { A: 0, B: 100 },
        knia_final_fault: { A: 10, B: 90 },
        knia_applied_adjustments: [
          { label: "상대 차량의 현저한 과실", applied_effect: { A: 10, B: -10 }, matched_by: ["급제동 입력"] },
        ],
        evidence: [
          { chunk_id: "prev-knia-1", source_type: "knia_fault_standard", title: "차41-1 후방 추돌" },
          { chunk_id: "next-knia-law", source_type: "knia_related_law", title: "KNIA 관련 법규" },
          { chunk_id: "prev-law-1", law_name: "도로교통법", title: "안전거리" },
          { chunk_id: "next-law-2", law_name: "도로교통법", title: "사고 후 조치" },
        ],
        evidence_audit: {
          scenario_evidence_coverage: {
            coverage_level: "high",
            scenario_relevant_count: 3,
            missing_requirements: [],
          },
        },
        agent_judgment: { overall_status: "evidence_supported" },
        required_input_questions: [],
      },
      {
        answered_fields: ["injury", "lane_change_actor"],
        unresolved_fields: ["turn_signal"],
        ignored_fields: ["unknown_internal_field"],
      }
    );

    expect(card?.changes.map((item: any) => item.label)).toContain("과실비율");
    expect(card?.changes.map((item: any) => item.label)).toContain("근거 구성");
    expect(card?.changes.map((item: any) => item.label)).toContain("KNIA 가감 후 과실");
    expect(card?.changes.map((item: any) => item.label)).toContain("적용된 가감요소");
    expect(card?.status_label).toBe("답변 처리 완료");
    expect(card?.answer_items.map((item: any) => item.label)).toContain("인명피해 여부");
    expect(card?.answer_items.map((item: any) => item.label)).toContain("차선변경 주체");
    expect(card?.answer_items.map((item: any) => item.label)).toContain("방향지시등 사용");
    expect(card?.answer_items.map((item: any) => item.label)).toContain("반영 제외 답변");
    expect(card?.answer_items.map((item: any) => item.status_label)).toContain("분석 반영");
    expect(card?.answer_items.map((item: any) => item.status_label)).toContain("추가 확인 필요");
    expect(card?.stats.find((item: any) => item.label === "남은 질문")?.value).toBe("0개");
    expect(card?.stats.find((item: any) => item.label === "질문 변화")?.value).toBe("1개 감소");
    expect(card?.stats.find((item: any) => item.label === "관련 근거")?.value).toBe("3개");
    expect(card?.question_flow).toEqual({
      before_count: 1,
      after_count: 0,
      answered_count: 2,
      unresolved_count: 1,
      ignored_count: 1,
      status_label: "질문 감소",
    });
    expect(card?.evidence_notes.join(" ")).toContain("현재 대표 KNIA 기준");
    expect(card?.decision_notes.join(" ")).toContain("남은 보완 질문이 1개에서 0개로 바뀌었습니다.");
    expect(card?.evidence_notes.join(" ")).toContain("현재 적용된 KNIA 가감요소: 1개");
    expect(card?.knia_adjustment_changes.added.map((item: any) => item.label)).toContain("상대 차량의 현저한 과실");
    expect(card?.evidence_changes.added.map((item: any) => item.title)).toContain("KNIA 관련 법규");
    expect(card?.evidence_changes.added.map((item: any) => item.family_label)).toContain("KNIA 기준");
    expect(card?.stats.find((item: any) => item.label === "반영 답변")?.value).toBe("2개");
    expect(card?.decision_notes.join(" ")).toContain("인명피해 여부");
    expect(card?.decision_notes.join(" ")).toContain("차선변경 주체");
    expect(card?.decision_notes.join(" ")).toContain("방향지시등 사용");
    expect(card?.decision_notes.join(" ")).toContain("분석 입력으로 쓰이지 않은 답변 1개");
    expect(JSON.stringify(card)).not.toContain("agent_judgment");
    expect(JSON.stringify(card)).not.toContain("evidence_supported");
    expect(JSON.stringify(card)).not.toContain("source_type");
    expect(JSON.stringify(card)).not.toContain("chunk_id");
    expect(JSON.stringify(card)).not.toContain("next-law-2");
    expect(JSON.stringify(card)).not.toContain("unknown_internal_field");
  });

  it("uses visible report question counts when composing reanalysis flow", () => {
    const card = composeReanalysisChangeCard(
      {
        scenario_type: "rear_end_collision",
        fault_ratio: { my: 20, other: 80 },
        required_input_questions: [],
      },
      {
        scenario_type: "rear_end_collision",
        fault_ratio: { my: 20, other: 80 },
        required_input_questions: [],
      },
      {
        answered_fields: ["turn_signal"],
        before_question_count: 1,
        after_question_count: 0,
      }
    );

    expect(card?.question_flow).toMatchObject({
      before_count: 1,
      after_count: 0,
      answered_count: 1,
      status_label: "질문 감소",
    });
    expect(card?.stats.find((item: any) => item.label === "질문 변화")?.value).toBe("1개 감소");
  });

  it("uses clear independent wording for video follow-up questions", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      video_input_contract: {
        uncertain_observations: [
          { field: "collision_point_visible", value: true, confidence: 0.62, frame_refs: ["frame_1.jpg"] },
          { field: "user_signal", value: "yellow", confidence: 0.55, frame_refs: ["frame_2.jpg"] },
          { field: "opponent_signal", value: "unknown", confidence: 0.2, frame_refs: [] },
          { field: "damage_level", value: "moderate", confidence: 0.5, frame_refs: ["frame_3.jpg"] },
        ],
      },
    });

    const questions = (enriched as any).missing_info.questions;
    const byField = Object.fromEntries(questions.map((item: any) => [item.field, item]));
    expect(byField.collision_point_visible.question).toBe("영상에서 실제 충돌 지점이 보이나요?");
    expect(byField.user_signal.question).toBe("내 차량이 교차로에 진입할 때 신호는 무엇이었나요?");
    expect(byField.opponent_signal.question).toBe("상대 차량이 교차로에 진입할 때 신호는 무엇이었나요?");
    expect(byField.damage_level.question).toBe("차량 파손 정도는 어느 정도인가요?");
    expect(JSON.stringify(questions)).not.toContain("이(가)");
    expect(new Set(questions.map((item: any) => item.field)).size).toBe(questions.length);
  });

  it("adds conditional signal guidance when opponent signal is unclear", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      scenario_type: "intersection_signal_violation",
      accident_summary: "교차로 좌회전 중 상대 직진 차량과 충돌했습니다.",
      structured_facts: {
        accident_party_type: "car_vs_car",
        intersection: true,
        user_signal: "yellow",
        opponent_signal_visible: false,
      },
      input_requirements: {
        questions: [
          { field: "opponent_signal", label: "상대 차량 신호", question: "상대 차량 신호는 무엇이었나요?" },
        ],
      },
    });

    const card = (enriched as any).conditional_outcome_card;
    expect(card.title).toBe("신호 확인에 따라 달라지는 판단");
    expect(card.cases).toHaveLength(2);
    expect(card.cases[0].label).toContain("정상 진행 신호");
    expect(card.cases[1].label).toContain("신호위반");
    expect(card.needed_evidence).toContain("교차로 CCTV");
    expect(JSON.stringify(card)).not.toContain("opponent_signal_visible");
  });

  it("prioritizes non-contact trigger questions before pedestrian context details", () => {
    const enriched = enrichEasyReport(sanitizeEasyReport({ headline: "report" }), {
      video_input_contract: {
        uncertain_observations: [
          { field: "pedestrian_visible", value: false, confidence: 0.74, frame_refs: ["frame_3.jpg"] },
          { field: "trigger_actor_type", value: "bicycle", confidence: 0.74, frame_refs: ["frame_8.jpg", "frame_9.jpg"] },
          { field: "direct_collision_partner_type", value: "vehicle", confidence: 0.8, frame_refs: ["frame_12.jpg", "frame_13.jpg"] },
          { field: "rear_vehicle_collision", value: true, confidence: 0.8, frame_refs: ["frame_12.jpg", "frame_13.jpg"] },
        ],
      },
    });

    const fields = (enriched as any).missing_info.questions.map((item: any) => item.field);
    expect(fields.indexOf("trigger_actor_type")).toBeLessThan(fields.indexOf("pedestrian_visible"));
    expect(fields.indexOf("direct_collision_partner_type")).toBeLessThan(fields.indexOf("pedestrian_visible"));
    expect(fields.indexOf("rear_vehicle_collision")).toBeLessThan(fields.indexOf("pedestrian_visible"));
    expect((enriched as any).missing_info.next_focus.label).toBe("사고 유발 대상");
  });
});
