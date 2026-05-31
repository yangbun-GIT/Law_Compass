import { describe, expect, it } from "vitest";
import { composeVideoPreprocessDiagnostic } from "../src/lib/video-preprocess-diagnostics.js";

describe("video preprocess diagnostics", () => {
  it("shows safe failure observations without exposing raw provider errors", () => {
    const diagnostic = composeVideoPreprocessDiagnostic({
      id: "upload-1",
      case_id: "case-1",
      file_name: "dashcam.mp4",
      metadata: {
        trace_id: "trace-video",
        openai_frame_analysis: {
          enabled: true,
          provider: "openai",
          model: "gpt-4.1-mini",
          error: "secret stack trace with Authorization bearer token",
          observations: [],
          failure_observations: [
            {
              version: "failure-observation-v1",
              code: "openai_frame_analysis_unavailable",
              source: "openai_frame_analysis",
              stage: "responses",
              severity: "error",
              recoverable: true,
              retryable: true,
              fallback_reason: "openai_error",
              error_type: "TimeoutError",
              safe_message: "OpenAI 프레임 분석이 실패해 영상 관찰값을 만들지 못했습니다.",
            },
          ],
          ai_usage_event: {
            version: "ai-usage-event-v1",
            provider: "openai",
            endpoint: "responses",
            model: "gpt-4.1-mini",
            enabled: true,
            success: false,
            error_type: "openai_frame_analysis_error",
            fallback_reason: "openai_error",
          },
        },
      },
    });

    expect(diagnostic.openai_frame_analysis.has_error).toBe(true);
    expect(diagnostic.openai_frame_analysis.failure_observation_count).toBe(1);
    expect(diagnostic.openai_frame_analysis.failure_observations[0].code).toBe("openai_frame_analysis_unavailable");
    expect(diagnostic.openai_frame_analysis.safe_error_message).toContain("영상 관찰값");
    expect(JSON.stringify(diagnostic)).not.toContain("secret stack trace");
    expect(JSON.stringify(diagnostic)).not.toContain("Authorization");
    expect(JSON.stringify(diagnostic)).not.toContain("bearer token");
  });
});
