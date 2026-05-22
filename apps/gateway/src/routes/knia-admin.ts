import type { FastifyInstance } from "fastify";
import { callInternalAgent } from "../lib/internal-client.js";
import { requireUser } from "../lib/request-guards.js";
import type { KniaRouteOptions } from "./knia.js";

export function registerKniaAdminRoutes(app: FastifyInstance, opts: KniaRouteOptions) {
  const { env, requireAdmin, errorPayload } = opts;

  app.post(`${env.apiPrefix}/admin/knia/collect`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    const body = (req.body ?? {}) as any;
    const rankingOnly = body.ranking === true && body.menu === false && body.charts === false;
    if (!rankingOnly && !requireAdmin(req as any, reply)) return;
    const result: any = {};
    try {
      if (body.menu !== false) {
        result.menu = await callInternalAgent("/internal/v1/knia/collect/menu-pages", {}, traceId, {
          baseUrl: env.agentUrl,
          internalToken: env.internalToken,
          timeoutMs: 180000,
          retryCount: 0
        });
      }
      if (body.ranking !== false) {
        result.ranking = await callInternalAgent("/internal/v1/knia/collect/ranking", {}, traceId, {
          baseUrl: env.agentUrl,
          internalToken: env.internalToken,
          timeoutMs: 180000,
          retryCount: 0
        });
      }
      if (body.charts !== false) {
        result.charts = await callInternalAgent(
          "/internal/v1/knia/collect/charts",
          { chart_nos: body.chart_nos, max_charts: body.max_charts },
          traceId,
          { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 240000, retryCount: 0 }
        );
      }
      return { result, trace_id: traceId };
    } catch (err: any) {
      return reply.code(502).send(errorPayload("KNIA_COLLECT_FAILED", err?.message || "KNIA 데이터 수집에 실패했습니다.", traceId));
    }
  });

  app.post(`${env.apiPrefix}/admin/knia/collect-ranking-details`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!requireAdmin(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/knia/collect/ranking-details", req.body ?? {}, traceId, {
        baseUrl: env.agentUrl,
        internalToken: env.internalToken,
        timeoutMs: 600000,
        retryCount: 0
      });
      return { result, trace_id: traceId };
    } catch (err: any) {
      return reply.code(502).send(errorPayload("KNIA_RANKING_DETAIL_COLLECT_FAILED", err?.message || "KNIA 상세 기준 수집에 실패했습니다.", traceId));
    }
  });

  app.post(`${env.apiPrefix}/admin/knia/rebuild-embeddings`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!requireAdmin(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/knia/rebuild-embeddings", req.body ?? {}, traceId, {
        baseUrl: env.agentUrl,
        internalToken: env.internalToken,
        timeoutMs: 240000,
        retryCount: 0
      });
      return { result, trace_id: traceId };
    } catch {
      return reply.code(502).send(errorPayload("KNIA_EMBEDDING_FAILED", "KNIA 임베딩 재생성에 실패했습니다.", traceId));
    }
  });

  app.post(`${env.apiPrefix}/admin/knia/import-json`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!requireAdmin(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/knia/import-json", req.body ?? {}, traceId, {
        baseUrl: env.agentUrl,
        internalToken: env.internalToken,
        timeoutMs: 600000,
        retryCount: 0
      });
      return { result, trace_id: traceId };
    } catch {
      return reply.code(502).send(errorPayload("KNIA_JSON_IMPORT_FAILED", "KNIA JSON 데이터를 가져오지 못했습니다. 파일 경로와 데이터 형식을 확인해 주세요.", traceId));
    }
  });

  app.post(`${env.apiPrefix}/admin/knia/json/rebuild-embeddings`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!requireAdmin(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/knia/json/rebuild-embeddings", req.body ?? {}, traceId, {
        baseUrl: env.agentUrl,
        internalToken: env.internalToken,
        timeoutMs: 600000,
        retryCount: 0
      });
      return { result, trace_id: traceId };
    } catch {
      return reply.code(502).send(errorPayload("KNIA_JSON_EMBEDDING_FAILED", "KNIA JSON 임베딩 재생성에 실패했습니다.", traceId));
    }
  });

  app.post(`${env.apiPrefix}/admin/cache/invalidate`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!requireAdmin(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/cache/invalidate", req.body ?? { scope: "knia_json" }, traceId, {
        baseUrl: env.agentUrl,
        internalToken: env.internalToken,
        timeoutMs: 60000,
        retryCount: 0
      });
      return { result, trace_id: traceId };
    } catch {
      return reply.code(502).send(errorPayload("CACHE_INVALIDATE_FAILED", "캐시 무효화에 실패했습니다.", traceId));
    }
  });
}
