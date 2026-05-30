import type { FastifyInstance, FastifyReply, FastifyRequest } from "fastify";
import { randomUUID } from "node:crypto";
import { composeAgentTraceDiagnostic } from "../lib/agent-diagnostics.js";
import { composeVideoPreprocessDiagnostic } from "../lib/video-preprocess-diagnostics.js";
import { requireUser } from "../lib/request-guards.js";

export type AgentDiagnosticsRouteOptions = {
  apiPrefix: string;
  db: any;
  requireAdmin: (req: FastifyRequest & { user?: any }, reply: FastifyReply) => boolean;
  errorPayload: (code: string, message: string, traceId: string) => any;
};

function trace(req: FastifyRequest) {
  return (req.headers["x-correlation-id"] as string) || randomUUID();
}

export function registerAgentDiagnosticsRoutes(app: FastifyInstance, opts: AgentDiagnosticsRouteOptions) {
  app.get(`${opts.apiPrefix}/admin/cases/:caseId/agent-trace`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!opts.requireAdmin(req as any, reply)) return;
    const traceId = trace(req);
    const caseId = String((req.params as any).caseId ?? "");
    const version = Number((req.query as any)?.version ?? 0);
    const params: any[] = [caseId];
    let versionFilter = "";
    if (Number.isInteger(version) && version > 0) {
      params.push(version);
      versionFilter = ` AND ar.version=$${params.length}`;
    }
    const row = await opts.db.query(
      `SELECT ar.id, ar.case_id, ar.owner_user_id, ar.version, ar.source_type, ar.result, ar.evidence_audit, ar.model_info, ar.created_at,
              c.status AS case_status
       FROM analysis_results ar
       JOIN cases c ON c.id=ar.case_id
       WHERE ar.case_id=$1${versionFilter}
       ORDER BY ar.version DESC
       LIMIT 1`,
      params
    );
    if (!row.rowCount) {
      return reply.code(404).send(opts.errorPayload("AGENT_TRACE_NOT_FOUND", "Agent trace diagnostic result was not found.", traceId));
    }
    return {
      case_id: caseId,
      case_status: row.rows[0].case_status,
      diagnostic: composeAgentTraceDiagnostic(row.rows[0]),
      trace_id: traceId,
    };
  });

  app.get(`${opts.apiPrefix}/admin/uploads/:uploadId/video-preprocess`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!opts.requireAdmin(req as any, reply)) return;
    const traceId = trace(req);
    const uploadId = String((req.params as any).uploadId ?? "");
    const row = await opts.db.query(
      `SELECT id, case_id, owner_user_id, file_name, content_type, file_size_bytes,
              status, metadata, preprocess_summary, created_at, updated_at
       FROM uploads
       WHERE id=$1 AND deleted_at IS NULL
       LIMIT 1`,
      [uploadId]
    );
    if (!row.rowCount) {
      return reply.code(404).send(opts.errorPayload("UPLOAD_NOT_FOUND", "Video preprocess diagnostic upload was not found.", traceId));
    }
    return {
      upload_id: uploadId,
      diagnostic: composeVideoPreprocessDiagnostic(row.rows[0]),
      trace_id: traceId,
    };
  });
}
