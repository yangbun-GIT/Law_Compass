import type { FastifyInstance } from "fastify";
import { callInternalAgent } from "../lib/internal-client.js";
import { requireUser } from "../lib/request-guards.js";

export type LegalAdminRouteOptions = {
  apiPrefix: string;
  agentUrl: string;
  internalToken: string;
  requireAdmin: (req: any, reply: any) => any;
  errorPayload: (code: string, message: string, traceId: string) => any;
};

async function callInternalAgentGet(path: string, traceId: string, opts: LegalAdminRouteOptions) {
  const res = await fetch(`${opts.agentUrl}${path}`, {
    method: "GET",
    headers: {
      "x-internal-token": opts.internalToken,
      "x-correlation-id": traceId
    }
  });
  if (!res.ok) throw new Error(`internal_agent_get_error_${res.status}:${(await res.text()).slice(0, 300)}`);
  return await res.json();
}

export function registerLegalAdminRoutes(app: FastifyInstance, opts: LegalAdminRouteOptions) {
  app.post(`${opts.apiPrefix}/admin/legal/ingest`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!opts.requireAdmin(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/legal/ingest", {}, traceId, {
        baseUrl: opts.agentUrl,
        internalToken: opts.internalToken,
        timeoutMs: 120000,
        retryCount: 0
      });
      return { result, trace_id: traceId };
    } catch {
      return reply.code(502).send(opts.errorPayload("LEGAL_INGEST_FAILED", "법률정보 적재에 실패했습니다.", traceId));
    }
  });

  app.post(`${opts.apiPrefix}/admin/legal/rebuild-embeddings`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!opts.requireAdmin(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/legal/rebuild-embeddings", {}, traceId, {
        baseUrl: opts.agentUrl,
        internalToken: opts.internalToken,
        timeoutMs: 120000,
        retryCount: 0
      });
      return { result, trace_id: traceId };
    } catch {
      return reply.code(502).send(opts.errorPayload("LEGAL_EMBEDDING_REBUILD_FAILED", "법률 임베딩 재생성에 실패했습니다.", traceId));
    }
  });

  app.get(`${opts.apiPrefix}/admin/legal/retrieval-test`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!opts.requireAdmin(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    const q = encodeURIComponent(String((req.query as any)?.q ?? "후미추돌 안전거리 과실비율"));
    try {
      const result = await callInternalAgentGet(`/internal/v1/legal/retrieval-test?q=${q}`, traceId, opts);
      return { result, trace_id: traceId };
    } catch {
      return reply.code(502).send(opts.errorPayload("LEGAL_RETRIEVAL_TEST_FAILED", "법률 RAG 테스트에 실패했습니다.", traceId));
    }
  });
}
