import type { FastifyInstance, FastifyRequest } from "fastify";
import { randomUUID } from "node:crypto";
import { requireUser } from "../lib/request-guards.js";

export type CaseRouteOptions = {
  apiPrefix: string;
  db: any;
  errorPayload: (code: string, message: string, traceId: string) => any;
};

function trace(req: FastifyRequest) {
  return (req.headers["x-correlation-id"] as string) || randomUUID();
}

function normalizeAnalysisMode(mode: any) {
  const value = String(mode || "").trim();

  if (
    value === "expert" ||
    value === "legal_precedent_focused" ||
    value === "full_deep_research" ||
    value === "deep_research" ||
    value === "debug" ||
    value === "legal-focused" ||
    value === "criminal-liability-focused" ||
    value === "evidence-review"
  ) {
    return "expert";
  }

  return "user_friendly";
}

export function registerCaseRoutes(app: FastifyInstance, opts: CaseRouteOptions) {
  app.post(`${opts.apiPrefix}/cases`, {
    schema: {
      body: {
        type: "object",
        required: ["title"],
        properties: {
          title: { type: "string", minLength: 1, maxLength: 140 },
          description_text: { type: "string", maxLength: 10000 },
          happened_at: { type: "string", format: "date-time" },
          location_text: { type: "string", maxLength: 240 },
          structured_facts: { type: "object", additionalProperties: true },
          selected_keywords: { type: "array", items: { type: "string", maxLength: 80 }, maxItems: 30 },
          analysis_mode: { type: "string", maxLength: 40 }
        }
      }
    }
  }, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const body = req.body as any;
    const result = await opts.db.query(
      `INSERT INTO cases(owner_user_id, title, description_text, happened_at, location_text, status, structured_facts, selected_keywords, analysis_mode)
       VALUES($1,$2,$3,$4,$5,'ready',$6,$7,$8) RETURNING *`,
      [
        (req as any).user.id,
        body.title,
        body.description_text ?? null,
        body.happened_at ?? null,
        body.location_text ?? null,
        JSON.stringify(body.structured_facts ?? {}),
        body.selected_keywords ?? [],
        normalizeAnalysisMode(body.analysis_mode ?? "user_friendly")
      ]
    );
    return { case: result.rows[0], trace_id: traceId };
  });

  app.get(`${opts.apiPrefix}/cases`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const rows = await opts.db.query(
      `SELECT * FROM cases WHERE owner_user_id=$1 AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 50`,
      [(req as any).user.id]
    );
    return { items: rows.rows, trace_id: traceId };
  });

  app.get(`${opts.apiPrefix}/cases/:caseId`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { caseId } = req.params as any;
    const row = await opts.db.query(
      `SELECT * FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`,
      [caseId, (req as any).user.id]
    );
    if (!row.rowCount) return reply.code(404).send(opts.errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
    return { case: row.rows[0], trace_id: traceId };
  });

  app.patch(`${opts.apiPrefix}/cases/:caseId`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const { caseId } = req.params as any;
    const body = req.body as any;
    const updated = await opts.db.query(
      `UPDATE cases
       SET title=COALESCE($3,title),
           description_text=COALESCE($4,description_text),
           location_text=COALESCE($5,location_text),
           structured_facts=COALESCE($6::jsonb,structured_facts),
           selected_keywords=COALESCE($7,selected_keywords),
           analysis_mode=COALESCE($8,analysis_mode)
       WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL RETURNING *`,
      [
        caseId,
        (req as any).user.id,
        body.title ?? null,
        body.description_text ?? null,
        body.location_text ?? null,
        body.structured_facts ? JSON.stringify(body.structured_facts) : null,
        body.selected_keywords ?? null,
        body.analysis_mode === undefined ? null : normalizeAnalysisMode(body.analysis_mode)
      ]
    );
    if (!updated.rowCount) return reply.code(404).send(opts.errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
    return { case: updated.rows[0], trace_id: traceId };
  });
}
