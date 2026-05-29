import Fastify from "fastify";
import { describe, expect, it } from "vitest";
import { errorPayload } from "../src/lib/errors.js";
import { registerMobileDemoRoutes } from "../src/routes/mobile-demo.js";

function buildApp(role: string | null = "user") {
  const app = Fastify({ logger: false });
  app.addHook("onRequest", async (req) => {
    req.headers["x-correlation-id"] = "trace-mobile-demo";
    if (role) {
      (req as any).user = { id: "user-1", role };
    }
  });
  registerMobileDemoRoutes(app, {
    apiPrefix: "/api/v1",
    errorPayload,
    agentCaller: async () => ({
      mode: "video_only_mlkit_demo",
      status: "ok",
      analysis_readiness: {
        can_infer_accident_context: true,
        can_estimate_fault_ratio: false,
        reason: "차량 객체 후보는 있으나 충돌 시점과 역할 정보가 부족합니다.",
      },
      observation_summary: {
        vehicles_detected: 2,
        persons_detected: 0,
        bicycles_detected: 0,
        traffic_lights_detected: 0,
        moving_tracks: 2,
        stationary_tracks: 0,
      },
      candidate_accident_context: {
        possible_party_type: "car_vs_car",
        confidence: 0.42,
        evidence: ["차량 객체 후보 2개가 여러 프레임에서 추적됨"],
        missing_facts: ["충돌 시점"],
      },
      fault_ratio_result: {
        judgment_status: "needs_review",
        presentation_status: "reference_only",
      },
    }),
  });
  return app;
}

describe("mobile demo observations route", () => {
  it("accepts client pre-observations without storing operational analysis judgments", async () => {
    const app = buildApp();
    const response = await app.inject({
      method: "POST",
      url: "/api/v1/mobile-demo/observations",
      payload: {
        source: "client_pre_observation",
        provider: "mock_mlkit_web_fallback",
        observations: [
          {
            field: "object_candidate",
            value: "vehicle",
            confidence: 0.81,
            frame_time_sec: 1.2,
            bbox: [0.1, 0.2, 0.4, 0.5],
            metadata: { label: "vehicle", frame_index: 1 },
          },
        ],
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      ok: true,
      accepted: true,
      source: "mobile_demo",
      received_count: 1,
    });
    await app.close();
  });

  it("rejects forbidden judgment fields from ML Kit demo payloads", async () => {
    const app = buildApp();
    const response = await app.inject({
      method: "POST",
      url: "/api/v1/mobile-demo/observations",
      payload: {
        source: "client_pre_observation",
        provider: "mock_mlkit_web_fallback",
        fault_ratio: { my: 0, other: 100 },
        observations: [],
      },
    });

    expect(response.statusCode).toBe(400);
    expect(response.json().error.code).toBe("FORBIDDEN_DEMO_JUDGMENT_FIELDS");
    expect(JSON.stringify(response.json())).toContain("$.fault_ratio");
    await app.close();
  });

  it("handles empty observations as a non-crashing validation response", async () => {
    const app = buildApp();
    const response = await app.inject({
      method: "POST",
      url: "/api/v1/mobile-demo/observations",
      payload: {
        source: "client_pre_observation",
        provider: "mock_mlkit_web_fallback",
        observations: [],
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json().received_count).toBe(0);
    expect(response.json().warnings[0]).toContain("observations");
    await app.close();
  });

  it("requires authentication for video-only demo analysis", async () => {
    const app = buildApp(null);
    const response = await app.inject({
      method: "POST",
      url: "/api/v1/mobile-demo/video-only-analysis",
      payload: { mode: "video_only_mlkit_demo", client_pre_observations: { observations: [] } },
    });

    expect(response.statusCode).toBe(401);
    await app.close();
  });

  it("requires admin or superuser role for video-only demo analysis", async () => {
    const app = buildApp("user");
    const response = await app.inject({
      method: "POST",
      url: "/api/v1/mobile-demo/video-only-analysis",
      payload: { mode: "video_only_mlkit_demo", client_pre_observations: { observations: [] } },
    });

    expect(response.statusCode).toBe(403);
    await app.close();
  });

  it("returns video-only analysis readiness for admin without user text", async () => {
    const app = buildApp("admin");
    const response = await app.inject({
      method: "POST",
      url: "/api/v1/mobile-demo/video-only-analysis",
      payload: {
        mode: "video_only_mlkit_demo",
        client_pre_observations: {
          source: "client_pre_observation",
          observations: [
            { field: "object_candidate", value: "vehicle", confidence: 0.8, frame_time_sec: 1, track_id: 1, bbox: [0.1, 0.1, 0.3, 0.3] },
          ],
        },
      },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      mode: "video_only_mlkit_demo",
      status: "ok",
      fault_ratio_result: {
        judgment_status: "needs_review",
        presentation_status: "reference_only",
      },
    });
    await app.close();
  });

  it("rejects forbidden fields in video-only demo analysis", async () => {
    const app = buildApp("superuser");
    const response = await app.inject({
      method: "POST",
      url: "/api/v1/mobile-demo/video-only-analysis",
      payload: {
        mode: "video_only_mlkit_demo",
        client_pre_observations: { observations: [] },
        signal_violation: true,
      },
    });

    expect(response.statusCode).toBe(400);
    expect(response.json().error.code).toBe("FORBIDDEN_DEMO_JUDGMENT_FIELDS");
    await app.close();
  });
});
