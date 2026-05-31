import { describe, expect, it } from "vitest";
import { composeAgentTraceDiagnostic } from "../src/lib/agent-diagnostics.js";

describe("agent diagnostics", () => {
  it("summarizes agent trace packets without exposing raw text or secrets", () => {
    const diagnostic = composeAgentTraceDiagnostic({
      id: "result-1",
      case_id: "case-1",
      version: 3,
      source_type: "video",
      created_at: "2026-05-22T00:00:00.000Z",
      result: {
        agent_trace: {
          version: "agent-execution-trace-v1",
          trace_id: "trace-diagnostic",
          trace_policy: "safe_metadata_only_no_raw_user_text",
          overall_status: "needs_review",
          step_count: 2,
          steps: [
            {
              id: "input_normalization",
              phase: "perceive",
              status: "completed",
              packet: {
                fact_count: 5,
                raw_text: "stopped at signal and got hit from behind",
                email: "driver@example.com",
                token: "secret-token",
                chunk_id: "law-1",
              },
            },
            {
              id: "reflection_loop",
              phase: "recover",
              status: "resolved",
              packet: { requery_attempted: true, requery_added_evidence_count: 1 },
            },
          ],
        },
        reflection_loop: {
          status: "resolved",
          next_action: "present_reference_only",
          requery_attempted: true,
          requery_added_evidence_count: 1,
          iterations_used: 1,
          final_missing_requirements: ["family:knia"],
        },
        video_input_contract: {
          version: "agent-video-input-contract-v1",
          accepted_observations: [{ field: "stopped" }],
          uncertain_observations: [{ field: "turn_signal" }],
          ignored_observations: [],
          confirmation_candidates: [{ field: "turn_signal" }],
          confirmation_groups: [],
          fact_patch: { stopped: true },
          observation_quality_summary: {
            accepted_count: 1,
            uncertain_count: 1,
            ignored_count: 0,
            accepted_single_frame_count: 1,
            accepted_multi_frame_count: 0,
            confirmation_candidate_count: 1,
            confirmation_group_count: 0,
            uncertain_reasons: { missing_frame_reference: 1 },
          },
        },
        fact_arbitration: {
          version: "agent-fact-arbitration-v1",
          applied_video_fields: ["stopped"],
          kept_user_fields: ["injury"],
          conflicts: [{ field: "stopped", winner: "video", video_confidence: 0.91, frame_refs: ["frame_1.jpg"], user_value: false, video_value: true }],
          requires_confirmation: [],
        },
        evidence_audit: {
          scenario_evidence_coverage: {
            coverage_level: "medium",
            decision_ready: false,
            scenario_relevant_count: 2,
            missing_requirements: ["family:knia"],
            evidence_family_counts: { legal: 2, knia: 0, general: 1 },
          },
        },
        agent_judgment: {
          overall_status: "needs_review",
          must_not_present_as_final: true,
          decision_blockers: ["scenario_relevant_evidence"],
          stage_statuses: [{ name: "evidence_retrieval", status: "needs_review" }],
        },
        presentation_policy: {
          finality: "reference_only",
          user_reference_allowed: true,
          restricted_sections: ["fault_ratio"],
        },
      },
      model_info: {
        llm_policy: {
          version: "llm-policy-v1",
          provider_enabled: true,
          used_sections: [],
          blocked_sections: ["fault_ratio_analysis"],
          failed_sections: [],
          cost_metadata: {
            used_section_count: 0,
            blocked_section_count: 1,
            failed_section_count: 0,
            token_usage_available: false,
            usage_event_version: "ai-usage-event-v1",
          },
          failure_observations: [
            {
              section: "fault_ratio_analysis",
              version: "failure-observation-v1",
              code: "llm_output_unavailable",
              source: "agent_llm_policy",
              stage: "fault_ratio_analysis",
              severity: "warning",
              recoverable: true,
              retryable: false,
              safe_message: "LLM output was unavailable or rejected, so deterministic fallback was used.",
            },
          ],
          sections: {
            fault_ratio_analysis: {
              ai_usage_event: {
                version: "ai-usage-event-v1",
                provider: "openai",
                endpoint: "chat.completions",
                model: "gpt-4.1-mini",
                enabled: true,
                allowed: false,
                used: false,
                success: false,
                reason: "required_knia_evidence_missing",
                token_usage_available: false,
                timeout_sec: 18,
              },
            },
          },
        },
      },
    });

    expect(diagnostic.diagnostic_version).toBe("agent-trace-diagnostic-v1");
    expect(diagnostic.trace.trace_id).toBe("trace-diagnostic");
    expect(diagnostic.pipeline.steps[0].packet_summary.fact_count).toBe(5);
    expect(diagnostic.pipeline.steps[0].packet_summary.raw_text).toBeUndefined();
    expect(diagnostic.reflection.next_action).toBe("present_reference_only");
    expect(diagnostic.video_input.accepted_observation_count).toBe(1);
    expect(diagnostic.video_input.confirmation_candidate_count).toBe(1);
    expect(diagnostic.video_input.observation_quality.accepted_single_frame_count).toBe(1);
    expect(diagnostic.video_input.observation_quality.confirmation_candidate_count).toBe(1);
    expect(diagnostic.video_input.observation_quality.uncertain_reason_counts.missing_frame_reference).toBe(1);
    expect(diagnostic.fact_arbitration.conflict_count).toBe(1);
    expect(diagnostic.evidence.family_counts).toEqual({ legal: 2, knia: 0, general: 1 });
    expect(diagnostic.usage.usage_event_version).toBe("ai-usage-event-v1");
    expect(diagnostic.usage.blocked_section_count).toBe(1);
    expect(diagnostic.usage.section_events[0].model).toBe("gpt-4.1-mini");
    expect(diagnostic.usage.section_events[0].token_usage_available).toBe(false);
    expect(diagnostic.usage.failure_observation_count).toBe(1);
    expect(diagnostic.usage.failure_observations[0].code).toBe("llm_output_unavailable");
    expect(JSON.stringify(diagnostic)).not.toContain("driver@example.com");
    expect(JSON.stringify(diagnostic)).not.toContain("secret-token");
    expect(JSON.stringify(diagnostic)).not.toContain("law-1");
    expect(JSON.stringify(diagnostic)).not.toContain("stopped at signal");
  });
});
