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
      },
      agent_judgment: { overall_status: "evidence_supported", decision_blockers: [] },
    });

    const processCard = enriched.agent_process_card!;
    expect(processCard.status_label).toBe("해결됨");
    expect(processCard.stats.find((item: any) => item.label === "추가 근거")?.value).toBe("1개");
    expect(processCard.steps.map((item: any) => item.label)).toContain("입력 정리");
    expect(processCard.steps.map((item: any) => item.label)).toContain("근거 보강 검토");
    expect(JSON.stringify(processCard)).not.toContain("packet");
    expect(JSON.stringify(processCard)).not.toContain("input_normalization");
    expect(JSON.stringify(processCard)).not.toContain("next_action");
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
    expect(card.uncertain_items[0].label).toBe("방향지시등 사용");
    const videoQuestion = (enriched as any).missing_info.questions[0];
    expect(videoQuestion.field).toBe("lane_change_actor");
    expect(videoQuestion.question).toContain(card.applied_items[0].label);
    expect(videoQuestion.options).toContain(card.applied_items[0].value);
    expect(text).not.toContain("video_input_contract");
    expect(text).not.toContain("fact_arbitration");
    expect(text).not.toContain("frame_analysis:openai");
    expect(text).not.toContain("user_value");
    expect(text).not.toContain("video_value");
    expect(text).not.toContain("reason");
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
    expect(JSON.stringify(card)).not.toContain("agent_judgment");
    expect(JSON.stringify(card)).not.toContain("evidence_supported");
    expect(JSON.stringify(card)).not.toContain("source_type");
    expect(JSON.stringify(card)).not.toContain("chunk_id");
    expect(JSON.stringify(card)).not.toContain("next-law-2");
  });
});
