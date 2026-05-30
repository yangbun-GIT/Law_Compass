import Fastify from "fastify";
import { describe, expect, it } from "vitest";
import { errorPayload } from "../src/lib/errors.js";
import { registerKniaRoutes } from "../src/routes/knia.js";

function buildApp(db: { query: (sql: string, params?: any[]) => Promise<any> }) {
  const app = Fastify({ logger: false });
  registerKniaRoutes(app, {
    env: {
      apiPrefix: "/api/v1",
      agentUrl: "http://agent",
      internalToken: "internal",
      timeoutMs: 1000,
      retryCount: 0,
    },
    db,
    requireAdmin: async () => undefined,
    errorPayload,
  });
  return app;
}

describe("KNIA ranking route", () => {
  it("returns bicycle ranking rows and normalizes 자/거 chart prefixes even when stored party is wrong", async () => {
    const queries: Array<{ sql: string; params?: any[] }> = [];
    const app = buildApp({
      async query(sql: string, params?: any[]) {
        queries.push({ sql, params });
        return {
          rowCount: 1,
          rows: [
            {
              rank: 3,
              chart_no: "거33-1",
              chart_type: "1",
              title: "자전거도로 사고",
              source_category: "차대사람",
              accident_party_type: "car_vs_person",
              search_count: 120,
              percentage: 2.4,
              source_url: "https://accident.knia.or.kr/ranking",
              source_detail_url: "https://accident.knia.or.kr/myaccident-content?chartNo=거33-1&chartType=1",
              has_detail: true,
            },
          ],
        };
      },
    });

    const response = await app.inject({
      method: "GET",
      url: "/api/v1/knia/ranking?limit=20&accidentPartyType=car_vs_bicycle&q=%EC%9E%90%EC%A0%84%EA%B1%B0",
      headers: { "x-correlation-id": "trace-bike" },
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.items).toHaveLength(1);
    expect(body.items[0]).toMatchObject({
      chart_no: "거33-1",
      accident_party_type: "car_vs_bicycle",
      accident_party_label: "차대자전거 사고",
    });
    expect(queries[0].sql).toContain("r.chart_no LIKE '자%'");
    expect(queries[0].sql).toContain("r.chart_no LIKE '거%'");
    expect(queries[0].params).toEqual(expect.arrayContaining(["%자전거%"]));
    await app.close();
  });

  it("falls back to fault charts when ranking rows are empty", async () => {
    let callCount = 0;
    const app = buildApp({
      async query() {
        callCount += 1;
        if (callCount === 1) return { rowCount: 0, rows: [] };
        return {
          rowCount: 1,
          rows: [
            {
              chart_no: "자12",
              chart_type: "1",
              title: "차대자전거 사고",
              accident_party_type: "unknown",
              accident_summary: "자전거와 차량 충돌",
              source_url: "https://accident.knia.or.kr/",
              source_detail_url: "https://accident.knia.or.kr/myaccident-content?chartNo=자12&chartType=1",
              has_detail: false,
              matched_by: "chart_fallback",
            },
          ],
        };
      },
    });

    const response = await app.inject({
      method: "GET",
      url: "/api/v1/knia/ranking?accidentPartyType=car_vs_bicycle&q=%EC%9E%90%EC%A0%84%EA%B1%B0",
    });

    expect(response.statusCode).toBe(200);
    expect(response.json().items[0]).toMatchObject({
      chart_no: "자12",
      accident_party_type: "car_vs_bicycle",
      matched_by: "chart_fallback",
    });
    await app.close();
  });

  it("returns a friendly empty response instead of an error when no bicycle result exists", async () => {
    const app = buildApp({
      async query() {
        return { rowCount: 0, rows: [] };
      },
    });

    const response = await app.inject({
      method: "GET",
      url: "/api/v1/knia/ranking?accidentPartyType=car_vs_bicycle&q=%EC%97%86%EB%8A%94%EA%B2%80%EC%83%89%EC%96%B4",
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      items: [],
      empty_message: "관련 기준을 찾지 못했습니다. 검색어를 바꿔 다시 시도해 주세요.",
    });
    await app.close();
  });

  it("wraps database failures in a safe 200 payload so search UI does not show a raw 500", async () => {
    const app = buildApp({
      async query() {
        throw new Error("missing column source_detail_url");
      },
    });

    const response = await app.inject({
      method: "GET",
      url: "/api/v1/knia/ranking?accidentPartyType=car_vs_bicycle&q=%EC%9E%90%EC%A0%84%EA%B1%B0",
      headers: { "x-correlation-id": "trace-safe" },
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.items).toEqual([]);
    expect(body.error).toMatchObject({
      code: "KNIA_RANKING_UNAVAILABLE",
      trace_id: "trace-safe",
    });
    expect(JSON.stringify(body)).not.toContain("missing column");
    await app.close();
  });

  it("keeps existing car-vs-car prefix filtering behavior", async () => {
    const queries: Array<{ sql: string; params?: any[] }> = [];
    const app = buildApp({
      async query(sql: string, params?: any[]) {
        queries.push({ sql, params });
        return { rowCount: 0, rows: [] };
      },
    });

    const response = await app.inject({
      method: "GET",
      url: "/api/v1/knia/ranking?accidentPartyType=car_vs_car&q=%ED%9B%84%EB%AF%B8%EC%B6%94%EB%8F%8C",
    });

    expect(response.statusCode).toBe(200);
    expect(queries[0].sql).toContain("r.chart_no LIKE '차%'");
    expect(queries[0].sql).not.toContain("r.chart_no LIKE '거%'");
    await app.close();
  });
});
