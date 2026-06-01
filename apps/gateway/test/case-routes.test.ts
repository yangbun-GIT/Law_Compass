import Fastify from "fastify";
import { describe, expect, it } from "vitest";
import { errorPayload } from "../src/lib/errors.js";
import { registerCaseRoutes } from "../src/routes/cases.js";

function buildApp(db: { query: (sql: string, params?: any[]) => Promise<any> }) {
  const app = Fastify({ logger: false });
  app.addHook("onRequest", async (req) => {
    (req as any).user = { id: "user-1", role: "user" };
  });
  registerCaseRoutes(app, {
    apiPrefix: "/api/v1",
    db,
    errorPayload,
  });
  return app;
}

describe("case routes", () => {
  it("soft deletes an owned case and hides related uploads", async () => {
    const queries: Array<{ sql: string; params?: any[] }> = [];
    const app = buildApp({
      async query(sql: string, params?: any[]) {
        queries.push({ sql, params });
        if (sql.includes("UPDATE cases")) {
          return { rowCount: 1, rows: [{ id: "case-1" }] };
        }
        if (sql.includes("UPDATE uploads")) {
          return { rowCount: 2, rows: [] };
        }
        return { rowCount: 0, rows: [] };
      },
    });

    const response = await app.inject({
      method: "DELETE",
      url: "/api/v1/cases/case-1",
      headers: { "x-correlation-id": "trace-delete-case" },
    });

    expect(response.statusCode).toBe(200);
    expect(response.json()).toMatchObject({
      ok: true,
      case_id: "case-1",
      trace_id: "trace-delete-case",
    });
    expect(queries).toHaveLength(2);
    expect(queries[0].sql).toContain("deleted_at=now()");
    expect(queries[0].sql).toContain("owner_user_id=$2");
    expect(queries[0].params).toEqual(["case-1", "user-1"]);
    expect(queries[1].sql).toContain("UPDATE uploads");
    expect(queries[1].sql).toContain("status='deleted'");
    expect(queries[1].params).toEqual(["case-1", "user-1"]);
    await app.close();
  });

  it("returns not found when deleting a missing or already deleted case", async () => {
    const queries: Array<{ sql: string; params?: any[] }> = [];
    const app = buildApp({
      async query(sql: string, params?: any[]) {
        queries.push({ sql, params });
        return { rowCount: 0, rows: [] };
      },
    });

    const response = await app.inject({
      method: "DELETE",
      url: "/api/v1/cases/missing-case",
      headers: { "x-correlation-id": "trace-missing-case" },
    });

    expect(response.statusCode).toBe(404);
    expect(response.json()).toMatchObject({
      error: {
        code: "CASE_NOT_FOUND",
        trace_id: "trace-missing-case",
      },
    });
    expect(queries).toHaveLength(1);
    expect(queries[0].sql).toContain("UPDATE cases");
    await app.close();
  });
});
