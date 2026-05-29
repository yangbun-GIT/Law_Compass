import type { FastifyInstance } from "fastify";
import { callInternalAgent, type AgentCallOptions } from "../lib/internal-client.js";
import { requireUser } from "../lib/request-guards.js";

type MobileDemoRouteOptions = {
  apiPrefix: string;
  errorPayload: (code: string, message: string, traceId: string, details?: any) => any;
  agentUrl?: string;
  internalToken?: string;
  timeoutMs?: number;
  retryCount?: number;
  agentCaller?: (path: string, payload: unknown, traceId: string, opts: AgentCallOptions) => Promise<any>;
};

const FORBIDDEN_FIELDS = new Set([
  "fault_ratio",
  "accident_party_type",
  "collision_partner_type",
  "signal_violation",
  "knia_chart_no",
  "legal_judgment",
]);

function trace(req: any) {
  return (req.headers["x-correlation-id"] as string) || "";
}

function findForbiddenFields(value: unknown, path = "$"): string[] {
  if (!value || typeof value !== "object") return [];
  if (Array.isArray(value)) {
    return value.flatMap((item, index) => findForbiddenFields(item, `${path}[${index}]`));
  }

  const found: string[] = [];
  for (const [key, nested] of Object.entries(value as Record<string, unknown>)) {
    const nextPath = `${path}.${key}`;
    if (FORBIDDEN_FIELDS.has(key)) found.push(nextPath);
    found.push(...findForbiddenFields(nested, nextPath));
  }
  return found;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isDemoAdmin(req: any) {
  const role = String(req.user?.role || "");
  return role === "admin" || role === "superuser";
}

function agentOptions(opts: MobileDemoRouteOptions): AgentCallOptions {
  return {
    baseUrl: opts.agentUrl || process.env.INTERNAL_AGENT_URL || "http://agent:8000",
    internalToken: opts.internalToken || process.env.INTERNAL_SERVICE_TOKEN || "",
    timeoutMs: Number(opts.timeoutMs ?? 15000),
    retryCount: Number(opts.retryCount ?? 0),
  };
}

export function registerMobileDemoRoutes(app: FastifyInstance, opts: MobileDemoRouteOptions) {
  app.post(`${opts.apiPrefix}/mobile-demo/observations`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;

    const traceId = trace(req);
    const body = req.body;
    if (!isObject(body)) {
      return reply
        .code(400)
        .send(opts.errorPayload("INVALID_DEMO_OBSERVATIONS", "관찰값 JSON 형식을 확인해 주세요.", traceId));
    }

    const forbidden = findForbiddenFields(body);
    if (forbidden.length) {
      return reply.code(400).send(
        opts.errorPayload("FORBIDDEN_DEMO_JUDGMENT_FIELDS", "ML Kit 데모 관찰값에는 판단 확정 필드를 넣을 수 없습니다.", traceId, {
          forbidden_fields: forbidden.slice(0, 20),
        })
      );
    }

    const observations = Array.isArray((body as any).observations) ? (body as any).observations : [];
    const warnings = Array.isArray((body as any).warnings) ? (body as any).warnings.slice(0, 10) : [];
    if (!observations.length) {
      warnings.push("observations 배열이 비어 있습니다. 성능 검증용 빈 결과로만 처리했습니다.");
    }

    return {
      ok: true,
      accepted: true,
      source: "mobile_demo",
      received_count: observations.length,
      warnings,
      trace_id: traceId,
    };
  });

  app.post(`${opts.apiPrefix}/mobile-demo/video-only-analysis`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;

    const traceId = trace(req);
    if (!isDemoAdmin(req as any)) {
      return reply.code(403).send(opts.errorPayload("ADMIN_REQUIRED", "관리자 권한이 필요합니다.", traceId));
    }

    const body = req.body;
    if (!isObject(body)) {
      return reply
        .code(400)
        .send(opts.errorPayload("INVALID_DEMO_ANALYSIS_REQUEST", "영상-only 데모 분석 요청 형식을 확인해 주세요.", traceId));
    }

    const forbidden = findForbiddenFields(body);
    if (forbidden.length) {
      return reply.code(400).send(
        opts.errorPayload("FORBIDDEN_DEMO_JUDGMENT_FIELDS", "ML Kit 데모 관찰값에는 판단 확정 필드를 넣을 수 없습니다.", traceId, {
          forbidden_fields: forbidden.slice(0, 20),
        })
      );
    }

    if (body.mode && body.mode !== "video_only_mlkit_demo") {
      return reply.code(400).send(
        opts.errorPayload("INVALID_DEMO_ANALYSIS_MODE", "mode는 video_only_mlkit_demo만 사용할 수 있습니다.", traceId)
      );
    }

    const caller = opts.agentCaller ?? callInternalAgent;
    const result = await caller(
      "/internal/v1/mobile-demo/video-only-analysis",
      {
        mode: "video_only_mlkit_demo",
        upload_id: body.upload_id ?? null,
        video_metadata: isObject(body.video_metadata) ? body.video_metadata : {},
        client_pre_observations: isObject(body.client_pre_observations) ? body.client_pre_observations : {},
        user_text: typeof body.user_text === "string" ? body.user_text : "",
      },
      traceId,
      agentOptions(opts)
    );

    return {
      ...result,
      trace_id: traceId,
    };
  });
}
