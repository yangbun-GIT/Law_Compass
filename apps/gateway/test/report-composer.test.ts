import { describe, expect, it } from "vitest";
import { composeReanalysisChangeCard, enrichEasyReport, sanitizeEasyReport } from "../src/lib/report-composer.js";

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
    expect(question.question).toContain("영상 기준 정차 여부: 주행 중");
    expect(question.question).toContain("기존 입력: 정차 중");
    expect(question.options).toContain("정차 중");
    expect(question.options).toContain("주행 중");
    expect(JSON.stringify(card)).not.toContain("user_value");
    expect(JSON.stringify(card)).not.toContain("video_value");
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
    expect(card?.stats.find((item: any) => item.label === "관련 근거")?.value).toBe("3개");
    expect(card?.evidence_notes.join(" ")).toContain("현재 대표 KNIA 기준");
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
});
