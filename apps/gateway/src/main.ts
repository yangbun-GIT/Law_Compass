import Fastify from "fastify";
import cors from "@fastify/cors";
import cookie from "@fastify/cookie";
import jwt from "@fastify/jwt";
import multipart from "@fastify/multipart";
import { randomUUID } from "node:crypto";
import { Pool } from "pg";
import { Redis } from "ioredis";
import { sha256 } from "./lib/security.js";
import { errorPayload, requestErrorPayload, validationErrorPayload } from "./lib/errors.js";
import { env, cookieSecure } from "./config/env.js";
import { routeKey, requireAdmin as requireAdminGuard } from "./lib/request-guards.js";
import { registerAuthRoutes } from "./routes/auth.js";
import { registerChatRoutes } from "./routes/chat.js";
import { registerCaseRoutes } from "./routes/cases.js";
import { registerUploadRoutes } from "./routes/uploads.js";
import { registerAnalysisRoutes } from "./routes/analysis.js";
import { registerKniaRoutes } from "./routes/knia.js";
import { registerKniaAdminRoutes } from "./routes/knia-admin.js";
import { registerLegalAdminRoutes } from "./routes/legal-admin.js";
import { registerAgentDiagnosticsRoutes } from "./routes/agent-diagnostics.js";
import { registerMobileDemoRoutes } from "./routes/mobile-demo.js";
import { createStorageAdapter } from "./lib/storage/index.js";

const app = Fastify({ logger: { level: "info" } });
const db = new Pool({ connectionString: env.dbUrl, max: 10 });
const redis = new Redis(env.redisUrl, { maxRetriesPerRequest: 1 });
const storage = createStorageAdapter(process.env);

await app.register(cors, { origin: true, credentials: true });
await app.register(cookie);
await app.register(jwt, { secret: env.jwtAccessSecret, cookie: { cookieName: "lc_at", signed: false } });
await app.register(multipart, { limits: { fileSize: env.maxUploadMb * 1024 * 1024, files: 1 } });

app.addHook("onRequest", async (req, reply) => {
  const traceId = (req.headers["x-correlation-id"] as string) || randomUUID();
  req.headers["x-correlation-id"] = traceId;
  reply.header("x-correlation-id", traceId);
});

app.addHook("onRequest", async (req, reply) => {
  if (!req.url.startsWith(env.apiPrefix)) return;
  if (req.url.startsWith(`${env.apiPrefix}/auth/login`) || req.url.startsWith(`${env.apiPrefix}/auth/signup`)) return;
  const auth = req.headers.authorization;
  const token = auth?.startsWith("Bearer ") ? auth.slice(7) : req.cookies.lc_at;
  if (!token) return;
  try {
    const payload = await app.jwt.verify<{ sub: string; role: string }>(token);
    (req as any).user = { id: payload.sub, role: payload.role };
  } catch {
    reply.clearCookie("lc_at");
  }
});

function requireAdmin(req: any, reply: any) {
  return requireAdminGuard(req, reply, env.adminToken);
}

async function rateLimit(req: any, reply: any) {
  const traceId = req.headers["x-correlation-id"] as string;
  const key = `rl:v1:${req.user?.id ?? "anon"}:${routeKey(req)}:${Math.floor(Date.now() / 60000)}`;
  const count = await redis.incr(key);
  if (count === 1) await redis.expire(key, 65);
  if (count > 90) {
    reply.code(429).send(errorPayload("RATE_LIMITED", "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.", traceId));
  }
}

async function idempotency(req: any, reply: any) {
  if (!["POST", "PATCH", "DELETE"].includes(req.method)) return;
  if (!req.user?.id) return;
  const key = req.headers["idempotency-key"] as string | undefined;
  if (!key) return;
  const keyHash = sha256(key);
  const reqHash = sha256(JSON.stringify(req.body ?? {}));
  const exists = await db.query(
    `SELECT response_code, response_body FROM idempotency_keys WHERE key_hash=$1 AND user_id=$2 AND route=$3 AND expires_at > now()`,
    [keyHash, req.user.id, routeKey(req)]
  );
  if (exists.rowCount) {
    reply.code(exists.rows[0].response_code).send(exists.rows[0].response_body);
    return reply;
  }
  (req as any).idempo = { keyHash, reqHash };
}

app.addHook("preHandler", rateLimit);
app.addHook("preHandler", idempotency);
app.addHook("onSend", async (req, _reply, payload) => {
  try {
    const raw = typeof payload === "string" ? payload : payload?.toString?.() ?? "{}";
    (req as any).__responseBody = JSON.parse(raw);
  } catch {
    (req as any).__responseBody = { ok: true };
  }
  return payload;
});

app.get("/health", async () => ({ ok: true }));
app.get("/ready", async () => {
  await db.query("SELECT 1");
  await redis.ping();
  return { ready: true };
});

registerChatRoutes(app, {
  apiPrefix: env.apiPrefix,
  db,
  agentUrl: env.agentUrl,
  internalToken: env.internalToken,
  timeoutMs: env.analyzeTimeoutMs,
  retryCount: env.retryCount,
  errorPayload
});

registerAuthRoutes(app, {
  apiPrefix: env.apiPrefix,
  db,
  cookieSecure,
  jwtAccessTtlSec: env.jwtAccessTtlSec,
  jwtRefreshTtlSec: env.jwtRefreshTtlSec,
  errorPayload
});

registerAgentDiagnosticsRoutes(app, {
  apiPrefix: env.apiPrefix,
  db,
  requireAdmin,
  errorPayload
});

registerCaseRoutes(app, {
  apiPrefix: env.apiPrefix,
  db,
  errorPayload
});

registerUploadRoutes(app, {
  apiPrefix: env.apiPrefix,
  db,
  redis,
  storage,
  localViewExpires: env.localViewExpires,
  localDownloadExpires: env.localDownloadExpires,
  errorPayload
});

registerAnalysisRoutes(app, {
  apiPrefix: env.apiPrefix,
  db,
  redis,
  agentUrl: env.agentUrl,
  internalToken: env.internalToken,
  analyzeTimeoutMs: env.analyzeTimeoutMs,
  retryCount: env.retryCount,
  errorPayload
});

registerKniaRoutes(app, {
  env,
  db,
  requireAdmin,
  errorPayload
});

registerKniaAdminRoutes(app, {
  env,
  db,
  requireAdmin,
  errorPayload
});

registerLegalAdminRoutes(app, {
  apiPrefix: env.apiPrefix,
  agentUrl: env.agentUrl,
  internalToken: env.internalToken,
  requireAdmin,
  errorPayload
});

registerMobileDemoRoutes(app, {
  apiPrefix: env.apiPrefix,
  errorPayload,
  agentUrl: env.agentUrl,
  internalToken: env.internalToken,
  timeoutMs: env.analyzeTimeoutMs,
  retryCount: env.retryCount
});

app.addHook("onResponse", async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  const actorId = (req as any).user?.id ?? null;
  const actorRole = (req as any).user?.role ?? null;
  const reqHash = sha256(JSON.stringify(req.body ?? {}));
  const resBody = (req as any).__responseBody ?? {};
  const resHash = sha256(JSON.stringify(resBody));
  await db.query(
    `INSERT INTO audit_logs(trace_id, actor_user_id, actor_role, action, target_type, status_code, req_hash, res_hash, extra)
     VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)`,
    [traceId, actorId, actorRole, `${req.method} ${routeKey(req)}`, "api", reply.statusCode, reqHash, resHash, JSON.stringify({ ua: req.headers["user-agent"] ?? null })]
  ).catch(() => undefined);

  const idempo = (req as any).idempo;
  if (idempo && actorId && reply.statusCode < 500) {
    await db.query(
      `INSERT INTO idempotency_keys(key_hash,user_id,route,request_hash,response_code,response_body,expires_at)
       VALUES($1,$2,$3,$4,$5,$6, now() + interval '24 hours')
       ON CONFLICT (key_hash,user_id,route) DO NOTHING`,
      [idempo.keyHash, actorId, routeKey(req), idempo.reqHash, reply.statusCode, JSON.stringify(resBody)]
    ).catch(() => undefined);
  }
});

app.setErrorHandler((err, req, reply) => {
  const traceId = (req.headers["x-correlation-id"] as string) || randomUUID();
  if (Array.isArray((err as any).validation)) {
    req.log.warn({ err, traceId }, "request_validation_failed");
    return reply.code(400).send(validationErrorPayload(err, traceId));
  }
  const statusCode = Number((err as any).statusCode ?? (err as any).status);
  if (Number.isInteger(statusCode) && statusCode >= 400 && statusCode < 500) {
    req.log.warn({ err, traceId }, "request_rejected");
    return reply.code(statusCode).send(requestErrorPayload(err, traceId));
  }
  req.log.error({ err, traceId }, "request_failed");
  return reply.code(500).send(errorPayload("INTERNAL_ERROR", "요청 처리 중 문제가 발생했습니다.", traceId));
});

await app.listen({ port: env.port, host: "0.0.0.0" });


