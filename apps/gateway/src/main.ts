import Fastify from "fastify";
import cors from "@fastify/cors";
import cookie from "@fastify/cookie";
import jwt from "@fastify/jwt";
import multipart from "@fastify/multipart";
import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { Pool } from "pg";
import { Redis } from "ioredis";
import bcrypt from "bcryptjs";
import { callInternalAgent } from "./lib/internal-client.js";
import { composeClientReport, composeDebugReport, composeEasyFallback, sanitizeEasyReport } from "./lib/report-composer.js";
import { maskSensitive, sha256 } from "./lib/security.js";
import { errorPayload, requestErrorPayload, validationErrorPayload } from "./lib/errors.js";
import { selectVideoAiRoute } from "./lib/ai-router.js";
import { registerChatRoutes } from "./routes/chat.js";
import { LocalStorageProvider } from "./storage/provider.js";

const env = {
  port: Number(process.env.PORT ?? 3000),
  apiPrefix: process.env.API_PREFIX ?? "/api/v1",
  dbUrl: process.env.DATABASE_URL ?? "",
  redisUrl: process.env.REDIS_URL ?? "",
  jwtAccessSecret: process.env.JWT_ACCESS_SECRET ?? "access",
  jwtRefreshSecret: process.env.JWT_REFRESH_SECRET ?? "refresh",
  jwtAccessTtlSec: Number(process.env.JWT_ACCESS_TTL_SEC ?? 900),
  jwtRefreshTtlSec: Number(process.env.JWT_REFRESH_TTL_SEC ?? 1209600),
  agentUrl: process.env.INTERNAL_AGENT_URL ?? "http://agent:8000",
  internalToken: process.env.INTERNAL_SERVICE_TOKEN ?? "token",
  adminToken: process.env.INTERNAL_ADMIN_TOKEN ?? "",
  timeoutMs: Number(process.env.REQUEST_TIMEOUT_MS ?? 4000),
  analyzeTimeoutMs: Number(process.env.ANALYZE_TIMEOUT_MS ?? 25000),
  retryCount: Number(process.env.RETRY_COUNT ?? 2),
  localViewExpires: Number(process.env.LOCAL_VIEW_URL_EXPIRES_SEC ?? 120),
  localDownloadExpires: Number(process.env.LOCAL_DOWNLOAD_URL_EXPIRES_SEC ?? 60),
  storageRoot: process.env.LOCAL_STORAGE_ROOT ?? "/app/storage"
};
const cookieSecure = (process.env.NODE_ENV ?? "development") === "production";

const app = Fastify({ logger: { level: "info" } });
const db = new Pool({ connectionString: env.dbUrl, max: 10 });
const redis = new Redis(env.redisUrl, { maxRetriesPerRequest: 1 });
const storage = new LocalStorageProvider(env.storageRoot);

await app.register(cors, { origin: true, credentials: true });
await app.register(cookie);
await app.register(jwt, { secret: env.jwtAccessSecret, cookie: { cookieName: "lc_at", signed: false } });
await app.register(multipart, { limits: { fileSize: 200 * 1024 * 1024, files: 1 } });

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

function routeKey(req: any) {
  return req.routeOptions?.url ?? req.url;
}

function requireUser(req: any, reply: any) {
  const traceId = req.headers["x-correlation-id"] as string;
  if (!req.user?.id) {
    reply.code(401).send(errorPayload("UNAUTHORIZED", "로그인이 필요합니다.", traceId));
    return false;
  }
  return true;
}

function requireAdmin(req: any, reply: any) {
  const traceId = req.headers["x-correlation-id"] as string;
  const token = req.headers["x-admin-token"] as string | undefined;
  if (env.adminToken && token === env.adminToken) return true;
  if (req.user?.role === "admin") return true;
  reply.code(403).send(errorPayload("ADMIN_REQUIRED", "관리자 권한이 필요합니다.", traceId));
  return false;
}

function cleanKniaPublicText(value: any, fallback: string) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (!text) return fallback;
  if (text.length > 420 || text.includes("과실비율의 이해 과실비율 인정기준") || text.includes(" Main ")) return fallback;
  return text;
}

async function callInternalAgentGet(path: string, traceId: string) {
  const res = await fetch(`${env.agentUrl}${path}`, {
    method: "GET",
    headers: {
      "x-internal-token": env.internalToken,
      "x-correlation-id": traceId
    }
  });
  if (!res.ok) throw new Error(`internal_agent_get_error_${res.status}:${(await res.text()).slice(0, 300)}`);
  return await res.json();
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

app.post(`${env.apiPrefix}/auth/signup`, {
  schema: {
    body: {
      type: "object",
      required: ["email", "password", "display_name"],
      properties: {
        email: { type: "string", format: "email" },
        password: { type: "string", minLength: 8 },
        display_name: { type: "string", minLength: 1, maxLength: 80 }
      }
    }
  }
}, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  const body = req.body as any;
  const pwHash = await bcrypt.hash(body.password, 10);
  try {
    const inserted = await db.query(
      `INSERT INTO users(email,password_hash,display_name) VALUES ($1,$2,$3) RETURNING id,email,display_name,role`,
      [body.email.toLowerCase(), pwHash, body.display_name]
    );
    return { user: inserted.rows[0], trace_id: traceId };
  } catch {
    return reply.code(409).send(errorPayload("EMAIL_EXISTS", "이미 가입된 이메일입니다.", traceId));
  }
});

app.post(`${env.apiPrefix}/auth/login`, {
  schema: {
    body: {
      type: "object",
      required: ["email", "password"],
      properties: {
        email: { type: "string", format: "email" },
        password: { type: "string", minLength: 8 }
      }
    }
  }
}, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  const body = req.body as any;
  const userRes = await db.query(`SELECT id,email,password_hash,role,display_name FROM users WHERE email=$1 AND deleted_at IS NULL`, [body.email.toLowerCase()]);
  const user = userRes.rows[0];
  if (!user || !(await bcrypt.compare(body.password, user.password_hash))) {
    return reply.code(401).send(errorPayload("INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다.", traceId));
  }
  const accessToken = await app.jwt.sign({ sub: user.id, role: user.role }, { expiresIn: env.jwtAccessTtlSec });
  const refreshRaw = randomUUID() + randomUUID();
  const refreshHash = sha256(refreshRaw);
  await db.query(
    `INSERT INTO auth_refresh_tokens(user_id, token_hash, expires_at) VALUES($1,$2, now() + ($3 || ' seconds')::interval)`,
    [user.id, refreshHash, env.jwtRefreshTtlSec]
  );
  reply.setCookie("lc_at", accessToken, { httpOnly: true, sameSite: "lax", path: "/", secure: cookieSecure });
  reply.setCookie("lc_rt", refreshRaw, { httpOnly: true, sameSite: "lax", path: "/", secure: cookieSecure });
  return { access_token: accessToken, user: { id: user.id, email: user.email, role: user.role, display_name: user.display_name }, trace_id: traceId };
});

app.post(`${env.apiPrefix}/auth/refresh`, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  const refreshRaw = req.cookies.lc_rt;
  if (!refreshRaw) return reply.code(401).send(errorPayload("NO_REFRESH_TOKEN", "재로그인이 필요합니다.", traceId));
  const refreshHash = sha256(refreshRaw);
  const tokenRes = await db.query(
    `SELECT id,user_id FROM auth_refresh_tokens WHERE token_hash=$1 AND revoked_at IS NULL AND expires_at > now()`, [refreshHash]
  );
  if (!tokenRes.rowCount) return reply.code(401).send(errorPayload("INVALID_REFRESH", "세션이 만료되었습니다.", traceId));
  const row = tokenRes.rows[0];
  const newRaw = randomUUID() + randomUUID();
  const newHash = sha256(newRaw);
  await db.query("UPDATE auth_refresh_tokens SET revoked_at=now() WHERE id=$1", [row.id]);
  await db.query(
    `INSERT INTO auth_refresh_tokens(user_id, token_hash, expires_at, rotated_from) VALUES($1,$2, now() + ($3 || ' seconds')::interval, $4)`,
    [row.user_id, newHash, env.jwtRefreshTtlSec, row.id]
  );
  const user = await db.query(`SELECT id,email,role,display_name FROM users WHERE id=$1`, [row.user_id]);
  const accessToken = await app.jwt.sign({ sub: row.user_id, role: user.rows[0].role }, { expiresIn: env.jwtAccessTtlSec });
  reply.setCookie("lc_at", accessToken, { httpOnly: true, sameSite: "lax", path: "/", secure: cookieSecure });
  reply.setCookie("lc_rt", newRaw, { httpOnly: true, sameSite: "lax", path: "/", secure: cookieSecure });
  return { access_token: accessToken, user: user.rows[0], trace_id: traceId };
});

app.post(`${env.apiPrefix}/auth/logout`, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  const refreshRaw = req.cookies.lc_rt;
  if (refreshRaw) await db.query(`UPDATE auth_refresh_tokens SET revoked_at=now() WHERE token_hash=$1`, [sha256(refreshRaw)]);
  reply.clearCookie("lc_at");
  reply.clearCookie("lc_rt");
  return { ok: true, trace_id: traceId };
});

app.get(`${env.apiPrefix}/auth/me`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const row = await db.query(`SELECT id,email,role,display_name FROM users WHERE id=$1 AND deleted_at IS NULL`, [(req as any).user.id]);
  if (!row.rowCount) return reply.code(404).send(errorPayload("USER_NOT_FOUND", "사용자를 찾을 수 없습니다.", traceId));
  return { user: row.rows[0], trace_id: traceId };
});

app.post(`${env.apiPrefix}/cases`, {
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
  const traceId = req.headers["x-correlation-id"] as string;
  const body = req.body as any;
  const result = await db.query(
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
      body.analysis_mode ?? "quick_summary"
    ]
  );
  return { case: result.rows[0], trace_id: traceId };
});

app.get(`${env.apiPrefix}/cases`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const rows = await db.query(`SELECT * FROM cases WHERE owner_user_id=$1 AND deleted_at IS NULL ORDER BY created_at DESC LIMIT 50`, [(req as any).user.id]);
  return { items: rows.rows, trace_id: traceId };
});

app.get(`${env.apiPrefix}/cases/:caseId`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { caseId } = req.params as any;
  const row = await db.query(`SELECT * FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [caseId, (req as any).user.id]);
  if (!row.rowCount) return reply.code(404).send(errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
  return { case: row.rows[0], trace_id: traceId };
});

app.patch(`${env.apiPrefix}/cases/:caseId`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { caseId } = req.params as any;
  const body = req.body as any;
  const updated = await db.query(
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
      body.analysis_mode ?? null
    ]
  );
  if (!updated.rowCount) return reply.code(404).send(errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
  return { case: updated.rows[0], trace_id: traceId };
});

app.post(`${env.apiPrefix}/uploads/init`, {
  schema: {
    body: {
      type: "object",
      required: ["case_id", "file_name", "content_type", "file_size_bytes"],
      properties: {
        case_id: { type: "string", format: "uuid" },
        file_name: { type: "string", minLength: 1, maxLength: 255 },
        content_type: { type: "string", pattern: "^video/" },
        file_size_bytes: { type: "integer", minimum: 1, maximum: 104857600 }
      }
    }
  }
}, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  return reply.code(410).send(errorPayload("S3_DISABLED_USE_LOCAL_UPLOAD", "현재는 로컬 영상 업로드만 지원합니다.", traceId));
});

app.post(`${env.apiPrefix}/uploads/local`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const data = await (req as any).file();
  if (!data) return reply.code(400).send(errorPayload("FILE_REQUIRED", "영상 파일을 선택해 주세요.", traceId));

  const caseId = String(data.fields?.case_id?.value ?? "");
  if (!caseId) return reply.code(400).send(errorPayload("CASE_ID_REQUIRED", "케이스 정보가 필요합니다.", traceId));
  const ownerCase = await db.query(`SELECT id FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [caseId, (req as any).user.id]);
  if (!ownerCase.rowCount) return reply.code(404).send(errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));

  const uploadId = randomUUID();
  let stored;
  try {
    stored = await storage.putUpload({
      caseId,
      uploadId,
      fileName: data.filename,
      contentType: data.mimetype,
      stream: data.file
    });
  } catch (err: any) {
    if (err?.message === "INVALID_CONTENT_TYPE") {
      return reply.code(400).send(errorPayload("INVALID_CONTENT_TYPE", "영상 파일만 업로드할 수 있습니다.", traceId));
    }
    throw err;
  }

  await db.query(
    `INSERT INTO uploads(id, case_id, owner_user_id, s3_bucket, s3_key, storage_provider, storage_path, file_name, content_type, file_size_bytes, status, metadata)
     VALUES($1,$2,$3,'local',$4,'local',$5,$6,$7,$8,'uploaded',$9)`,
    [
      uploadId,
      caseId,
      (req as any).user.id,
      stored.storagePath,
      stored.storagePath,
      data.filename,
      data.mimetype,
      stored.sizeBytes,
      JSON.stringify({ storage_provider: "local", original_name: data.filename })
    ]
  );
  return { upload_id: uploadId, status: "uploaded", storage_provider: "local", trace_id: traceId };
});

async function enqueueVideoPreprocessJob(caseId: string, uploadId: string, ownerId: string, storagePath: string) {
  const jobRes = await db.query(
    `INSERT INTO jobs(case_id, upload_id, owner_user_id, type, status, payload)
     VALUES($1,$2,$3,'video_preprocess','queued',$4) RETURNING id`,
    [caseId, uploadId, ownerId, JSON.stringify({ upload_id: uploadId, case_id: caseId, storage_path: storagePath })]
  );
  await redis.xadd(
    process.env.REDIS_STREAM_KEY ?? "jobs:v1:stream",
    "MAXLEN",
    "~",
    "10000",
    "*",
    "job_id",
    jobRes.rows[0].id,
    "job_type",
    "video_preprocess"
  );
  return jobRes.rows[0].id as string;
}

app.post(`${env.apiPrefix}/uploads/complete`, {
  schema: {
    body: {
      type: "object",
      required: ["upload_id"],
      properties: {
        upload_id: { type: "string", format: "uuid" }
      }
    }
  }
}, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { upload_id } = req.body as any;
  const found = await db.query(
    `SELECT u.*, c.id as case_exists FROM uploads u
     JOIN cases c ON c.id=u.case_id
     WHERE u.id=$1 AND u.owner_user_id=$2 AND u.deleted_at IS NULL`,
    [upload_id, (req as any).user.id]
  );
  if (!found.rowCount) return reply.code(404).send(errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
  const upload = found.rows[0];

  if (upload.storage_provider !== "local") {
    return reply.code(409).send(errorPayload("LOCAL_UPLOAD_ONLY", "현재는 로컬 업로드만 완료 처리할 수 있습니다.", traceId));
  }
  if (!upload.storage_path) {
    return reply.code(400).send(errorPayload("UPLOAD_PATH_MISSING", "저장된 영상 경로를 찾을 수 없습니다.", traceId));
  }
  let info;
  try {
    info = await stat(upload.storage_path);
  } catch {
    return reply.code(400).send(errorPayload("LOCAL_FILE_NOT_FOUND", "로컬 업로드 파일을 확인하지 못했습니다.", traceId));
  }
  if (!upload.content_type?.startsWith("video/")) {
    return reply.code(400).send(errorPayload("INVALID_CONTENT_TYPE", "영상 파일만 업로드할 수 있습니다.", traceId));
  }

  await db.query(
    `UPDATE uploads
     SET status='verified',
         file_size_bytes=$2,
         metadata = metadata || $3::jsonb
     WHERE id=$1`,
    [
      upload_id,
      Number(info.size),
      JSON.stringify({ completed_at: new Date().toISOString(), local_verified: true })
    ]
  );

  const existingJob = await db.query(
    `SELECT id FROM jobs
     WHERE upload_id=$1 AND owner_user_id=$2 AND type='video_preprocess' AND status IN ('queued','running','retrying','succeeded')
     ORDER BY created_at DESC LIMIT 1`,
    [upload_id, (req as any).user.id]
  );
  const jobId = existingJob.rowCount
    ? existingJob.rows[0].id
    : await enqueueVideoPreprocessJob(upload.case_id, upload_id, (req as any).user.id, upload.storage_path);
  return { upload_id, job_id: jobId, status: "verified", trace_id: traceId };
});

app.post(`${env.apiPrefix}/uploads/:uploadId/complete`, async (req, reply) => {
  (req as any).body = { upload_id: (req.params as any).uploadId };
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const uploadId = (req.params as any).uploadId;
  const found = await db.query(
    `SELECT u.*, c.id as case_exists FROM uploads u
     JOIN cases c ON c.id=u.case_id
     WHERE u.id=$1 AND u.owner_user_id=$2 AND u.deleted_at IS NULL`,
    [uploadId, (req as any).user.id]
  );
  if (!found.rowCount) return reply.code(404).send(errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
  const upload = found.rows[0];
  if (upload.storage_provider !== "local" || !upload.storage_path) {
    return reply.code(409).send(errorPayload("LOCAL_UPLOAD_ONLY", "현재는 로컬 업로드만 완료 처리할 수 있습니다.", traceId));
  }
  let info;
  try {
    info = await stat(upload.storage_path);
  } catch {
    return reply.code(400).send(errorPayload("LOCAL_FILE_NOT_FOUND", "로컬 업로드 파일을 확인하지 못했습니다.", traceId));
  }
  await db.query(
    `UPDATE uploads SET status='verified', file_size_bytes=$2, metadata = metadata || $3::jsonb WHERE id=$1`,
    [uploadId, Number(info.size), JSON.stringify({ completed_at: new Date().toISOString(), local_verified: true })]
  );
  const existingJob = await db.query(
    `SELECT id FROM jobs
     WHERE upload_id=$1 AND owner_user_id=$2 AND type='video_preprocess' AND status IN ('queued','running','retrying','succeeded')
     ORDER BY created_at DESC LIMIT 1`,
    [uploadId, (req as any).user.id]
  );
  const jobId = existingJob.rowCount
    ? existingJob.rows[0].id
    : await enqueueVideoPreprocessJob(upload.case_id, uploadId, (req as any).user.id, upload.storage_path);
  return { upload_id: uploadId, job_id: jobId, status: "verified", trace_id: traceId };
});

app.get(`${env.apiPrefix}/uploads/:uploadId`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { uploadId } = req.params as any;
  const row = await db.query(`SELECT * FROM uploads WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [uploadId, (req as any).user.id]);
  if (!row.rowCount) return reply.code(404).send(errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
  return { upload: row.rows[0], trace_id: traceId };
});

app.get(`${env.apiPrefix}/cases/:caseId/uploads`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { caseId } = req.params as any;
  const owner = await db.query(`SELECT id FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [caseId, (req as any).user.id]);
  if (!owner.rowCount) return reply.code(404).send(errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
  const rows = await db.query(
    `SELECT id,file_name,content_type,file_size_bytes,status,storage_provider,metadata,frame_dir,preprocess_summary,created_at FROM uploads
     WHERE case_id=$1 AND owner_user_id=$2 AND deleted_at IS NULL
     ORDER BY created_at DESC`,
    [caseId, (req as any).user.id]
  );
  return { items: rows.rows, trace_id: traceId };
});

async function createGetUrl(uploadId: string, ownerId: string, disposition: "inline" | "attachment", expiresIn: number) {
  const row = await db.query(`SELECT * FROM uploads WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [uploadId, ownerId]);
  if (!row.rowCount) return null;
  const upload = row.rows[0];
  if (!["verified", "processing", "ready"].includes(upload.status)) return { blocked: true } as any;
  if (upload.storage_provider !== "local") return { blocked: true } as any;
  return {
    upload,
    url: `/api/v1/uploads/${uploadId}/local-content?disposition=${disposition}`,
    local: true,
    expiresIn
  } as any;
}

app.get(`${env.apiPrefix}/uploads/:uploadId/local-content`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { uploadId } = req.params as any;
  const disposition = ((req.query as any)?.disposition === "attachment" ? "attachment" : "inline") as "inline" | "attachment";
  const row = await db.query(
    `SELECT * FROM uploads WHERE id=$1 AND owner_user_id=$2 AND storage_provider='local' AND deleted_at IS NULL`,
    [uploadId, (req as any).user.id]
  );
  if (!row.rowCount) return reply.code(404).send(errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
  const upload = row.rows[0];
  if (!["uploaded", "verified", "processing", "ready"].includes(upload.status)) {
    return reply.code(409).send(errorPayload("UPLOAD_NOT_READY", "아직 재생할 수 없는 업로드입니다.", traceId));
  }
  const info = await stat(upload.storage_path);
  reply.header("content-type", upload.content_type);
  reply.header("content-length", String(info.size));
  reply.header("content-disposition", `${disposition}; filename="${encodeURIComponent(upload.file_name)}"`);
  return reply.send(createReadStream(upload.storage_path));
});

app.get(`${env.apiPrefix}/uploads/:uploadId/view-url`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const result = await createGetUrl((req.params as any).uploadId, (req as any).user.id, "inline", env.localViewExpires);
  if (!result) return reply.code(404).send(errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
  if ((result as any).blocked) return reply.code(409).send(errorPayload("UPLOAD_NOT_READY", "아직 검증되지 않은 업로드입니다.", traceId));
  return { view_url: result.url, expires_in_sec: env.localViewExpires, trace_id: traceId };
});

app.get(`${env.apiPrefix}/uploads/:uploadId/download-url`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const result = await createGetUrl((req.params as any).uploadId, (req as any).user.id, "attachment", env.localDownloadExpires);
  if (!result) return reply.code(404).send(errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
  if ((result as any).blocked) return reply.code(409).send(errorPayload("UPLOAD_NOT_READY", "아직 검증되지 않은 업로드입니다.", traceId));
  return { download_url: result.url, expires_in_sec: env.localDownloadExpires, trace_id: traceId };
});

app.delete(`${env.apiPrefix}/uploads/:uploadId`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { uploadId } = req.params as any;
  const updated = await db.query(`UPDATE uploads SET status='deleted', deleted_at=now() WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL RETURNING id`, [uploadId, (req as any).user.id]);
  if (!updated.rowCount) return reply.code(404).send(errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
  return { ok: true, trace_id: traceId };
});

app.post(`${env.apiPrefix}/cases/:caseId/analyze-text`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { caseId } = req.params as any;
  const body = req.body as any;

  const caseRow = await db.query(`SELECT * FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [caseId, (req as any).user.id]);
  if (!caseRow.rowCount) return reply.code(404).send(errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));

  let agentResp;
  try {
    agentResp = await callInternalAgent("/internal/v1/analyze/text", {
      case_id: caseId,
      user_id: (req as any).user.id,
      description_text: maskSensitive(body?.description_text ?? caseRow.rows[0].description_text ?? ""),
      structured_facts: body?.structured_facts ?? caseRow.rows[0].structured_facts ?? {},
      selected_keywords: body?.selected_keywords ?? caseRow.rows[0].selected_keywords ?? [],
      analysis_mode: body?.analysis_mode ?? caseRow.rows[0].analysis_mode ?? "quick_summary",
      ai_profile: body?.ai_profile,
      specialist_roles: body?.specialist_roles
    }, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: env.analyzeTimeoutMs, retryCount: env.retryCount });
  } catch {
    return reply.code(502).send(errorPayload("AI_TEMPORARY_UNAVAILABLE", "AI 분석 서비스가 일시적으로 불안정합니다. 잠시 후 재시도해 주세요.", traceId));
  }

  const ver = await db.query(`SELECT COALESCE(MAX(version),0)+1 AS v FROM analysis_results WHERE case_id=$1`, [caseId]);
  const nextVersion = Number(ver.rows[0].v);
  const inserted = await db.query(
    `INSERT INTO analysis_results(
       case_id, owner_user_id, version, source_type, result, evidence, uncertainty, model_info,
       structured_facts, recommended_keywords, suggested_next_inputs, report_payload, elderly_friendly_report,
       legal_analysis, scenario_type, used_evidence_ids, legal_risk_flags, persona_outputs, evidence_audit
     )
     VALUES($1,$2,$3,'text',$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18) RETURNING id, version`,
    [
      caseId,
      (req as any).user.id,
      nextVersion,
      JSON.stringify(agentResp),
      JSON.stringify(agentResp.evidence ?? []),
      JSON.stringify(agentResp.uncertainty ?? {}),
      JSON.stringify(agentResp.model_info ?? {}),
      JSON.stringify(agentResp.structured_facts ?? {}),
      JSON.stringify(agentResp.recommended_keywords ?? []),
      JSON.stringify(agentResp.suggested_next_inputs ?? []),
      JSON.stringify(composeClientReport(agentResp, { case: caseRow.rows[0] })),
      JSON.stringify(agentResp.elderly_friendly_report ?? {}),
      JSON.stringify(agentResp.legal_analysis ?? {}),
      agentResp.scenario_type ?? null,
      JSON.stringify((agentResp.evidence ?? []).map((x: any) => x.chunk_id).filter(Boolean)),
      JSON.stringify(agentResp.legal_liability?.risk_flags ?? agentResp.legal_analysis?.risk_flags ?? []),
      JSON.stringify({ analysts: agentResp.recommended_specialists ?? [] }),
      JSON.stringify(agentResp.evidence_audit ?? {})
    ]
  );
  await db.query(`UPDATE cases SET status='completed', latest_result_id=$2 WHERE id=$1`, [caseId, inserted.rows[0].id]);
  await db.query(
    `UPDATE analysis_results SET knia_matches=$2, knia_primary_match=$3 WHERE id=$1`,
    [inserted.rows[0].id, JSON.stringify(agentResp.knia_matches ?? []), JSON.stringify(agentResp.knia_primary_match ?? null)]
  ).catch(() => undefined);
  const easyReport = sanitizeEasyReport(agentResp.elderly_friendly_report ?? composeEasyFallback(agentResp, { case: caseRow.rows[0] }));

  return {
    result_id: inserted.rows[0].id,
    version: nextVersion,
    result: easyReport,
    report: easyReport,
    trace_id: traceId
  };
});

app.post(`${env.apiPrefix}/cases/:caseId/analyze-video`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { caseId } = req.params as any;
  const body = req.body as any;
  const caseRow = await db.query(`SELECT id,title,description_text FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [caseId, (req as any).user.id]);
  if (!caseRow.rowCount) return reply.code(404).send(errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
  const uploadRow = await db.query(`SELECT id FROM uploads WHERE id=$1 AND case_id=$2 AND owner_user_id=$3 AND deleted_at IS NULL`, [body.upload_id, caseId, (req as any).user.id]);
  if (!uploadRow.rowCount) return reply.code(404).send(errorPayload("UPLOAD_NOT_FOUND", "업로드를 찾을 수 없습니다.", traceId));
  const uploadFull = await db.query(`SELECT file_name, metadata FROM uploads WHERE id=$1`, [body.upload_id]);
  const route = selectVideoAiRoute({
    caseTitle: caseRow.rows[0].title ?? "",
    caseDescription: `${caseRow.rows[0].description_text ?? ""} ${JSON.stringify(body.structured_facts ?? {})} ${(body.selected_keywords ?? []).join(" ")}`,
    fileName: uploadFull.rows[0]?.file_name ?? "",
    uploadMetadata: uploadFull.rows[0]?.metadata ?? {}
  });
  const job = await db.query(
    `INSERT INTO jobs(case_id, upload_id, owner_user_id, type, status, payload)
     VALUES($1,$2,$3,'video_analyze','queued',$4) RETURNING id`,
    [caseId, body.upload_id, (req as any).user.id, JSON.stringify({
      case_id: caseId,
      upload_id: body.upload_id,
      ai_profile: route.aiProfile,
      specialist_roles: route.specialistRoles,
      routing_reason: route.reason,
      structured_facts: body.structured_facts ?? {},
      selected_keywords: body.selected_keywords ?? [],
      analysis_mode: body.analysis_mode ?? "quick_summary"
    })]
  );
  await redis.xadd(process.env.REDIS_STREAM_KEY ?? "jobs:v1:stream", "MAXLEN", "~", "10000", "*", "job_id", job.rows[0].id, "job_type", "video_analyze");
  return { job_id: job.rows[0].id, status: "queued", ai_profile: route.aiProfile, specialist_roles: route.specialistRoles, trace_id: traceId };
});

app.get(`${env.apiPrefix}/cases/:caseId/jobs`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { caseId } = req.params as any;
  const rows = await db.query(
    `SELECT id,type,status,attempts,attempt,max_attempts,last_error,error_info,artifacts,created_at,updated_at
     FROM jobs WHERE case_id=$1 AND owner_user_id=$2 ORDER BY created_at DESC LIMIT 50`,
    [caseId, (req as any).user.id]
  );
  return { items: rows.rows, trace_id: traceId };
});

app.get(`${env.apiPrefix}/cases/:caseId/result`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { caseId } = req.params as any;
  const row = await db.query(`SELECT * FROM analysis_results WHERE case_id=$1 AND owner_user_id=$2 ORDER BY version DESC LIMIT 1`, [caseId, (req as any).user.id]);
  if (!row.rowCount) return reply.code(404).send(errorPayload("RESULT_NOT_FOUND", "분석 결과가 없습니다.", traceId));
  const context = await buildReportContext(caseId, (req as any).user.id, row.rows[0]);
  const debug = String((req.query as any)?.debug ?? "") === "1";
  const easyReport = sanitizeEasyReport(row.rows[0].elderly_friendly_report && Object.keys(row.rows[0].elderly_friendly_report).length ? row.rows[0].elderly_friendly_report : composeEasyFallback(row.rows[0].result, context));
  return debug
    ? { result: easyReport, report: easyReport, debug: composeDebugReport(row.rows[0].result, context), trace_id: traceId }
    : { result: easyReport, report: easyReport, trace_id: traceId };
});

app.get(`${env.apiPrefix}/cases/:caseId/report`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { caseId } = req.params as any;
  const row = await db.query(`SELECT * FROM analysis_results WHERE case_id=$1 AND owner_user_id=$2 ORDER BY version DESC LIMIT 1`, [caseId, (req as any).user.id]);
  if (!row.rowCount) return reply.code(404).send(errorPayload("RESULT_NOT_FOUND", "분석 결과가 없습니다.", traceId));
  const context = await buildReportContext(caseId, (req as any).user.id, row.rows[0]);
  const debug = String((req.query as any)?.debug ?? "") === "1";
  const report = sanitizeEasyReport(row.rows[0].elderly_friendly_report && Object.keys(row.rows[0].elderly_friendly_report).length ? row.rows[0].elderly_friendly_report : composeClientReport(row.rows[0].result, context));
  await db.query(`UPDATE analysis_results SET report_payload=$2 WHERE id=$1`, [row.rows[0].id, JSON.stringify(report)]).catch(() => undefined);
  return debug ? { report, debug: composeDebugReport(row.rows[0].result, context), trace_id: traceId } : { report, trace_id: traceId };
});

app.get(`${env.apiPrefix}/cases/:caseId/easy-report`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { caseId } = req.params as any;
  const row = await db.query(
    `SELECT * FROM analysis_results WHERE case_id=$1 AND owner_user_id=$2 ORDER BY version DESC LIMIT 1`,
    [caseId, (req as any).user.id]
  );
  if (!row.rowCount) return reply.code(404).send(errorPayload("RESULT_NOT_FOUND", "분석 결과가 없습니다.", traceId));
  const result = row.rows[0].result ?? {};
  const stored = row.rows[0].elderly_friendly_report;
  const easyReport = sanitizeEasyReport(
    stored && Object.keys(stored).length
      ? stored
      : result.elderly_friendly_report && Object.keys(result.elderly_friendly_report).length
        ? result.elderly_friendly_report
        : composeEasyFallback(result, await buildReportContext(caseId, (req as any).user.id, row.rows[0]))
  );
  await db.query(`UPDATE analysis_results SET elderly_friendly_report=$2 WHERE id=$1`, [row.rows[0].id, JSON.stringify(easyReport)]).catch(() => undefined);
  if (String((req.query as any)?.debug ?? "") === "1") {
    const context = await buildReportContext(caseId, (req as any).user.id, row.rows[0]);
    return { case_id: caseId, report_type: "elderly_friendly", ...easyReport, debug: composeDebugReport(result, context), trace_id: traceId };
  }
  return { case_id: caseId, report_type: "elderly_friendly", ...easyReport, trace_id: traceId };
});

async function buildReportContext(caseId: string, ownerId: string, resultRow: any) {
  const caseRes = await db.query(`SELECT * FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [caseId, ownerId]);
  const uploadRes = await db.query(
    `SELECT * FROM uploads WHERE case_id=$1 AND owner_user_id=$2 AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT 1`,
    [caseId, ownerId]
  );
  const jobsRes = await db.query(
    `SELECT id,type,status,attempts AS attempt,max_attempts,last_error,error_info,created_at,updated_at
     FROM jobs WHERE case_id=$1 AND owner_user_id=$2 ORDER BY created_at DESC LIMIT 10`,
    [caseId, ownerId]
  );
  return {
    case: caseRes.rows[0] ?? null,
    upload: uploadRes.rows[0] ?? null,
    jobs: jobsRes.rows,
    resultRow,
  };
}

app.post(`${env.apiPrefix}/cases/:caseId/reanalyze`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { caseId } = req.params as any;
  const body = req.body as any;
  const caseRow = await db.query(`SELECT description_text FROM cases WHERE id=$1 AND owner_user_id=$2 AND deleted_at IS NULL`, [caseId, (req as any).user.id]);
  if (!caseRow.rowCount) return reply.code(404).send(errorPayload("CASE_NOT_FOUND", "케이스를 찾을 수 없습니다.", traceId));
  let agentResp;
  try {
    agentResp = await callInternalAgent("/internal/v1/analyze/text", {
      case_id: caseId,
      user_id: (req as any).user.id,
      description_text: maskSensitive(body?.description_text ?? caseRow.rows[0].description_text ?? "")
    }, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: env.analyzeTimeoutMs, retryCount: env.retryCount });
  } catch {
    return reply.code(502).send(errorPayload("AI_TEMPORARY_UNAVAILABLE", "AI 분석 서비스가 일시적으로 불안정합니다. 잠시 후 재시도해 주세요.", traceId));
  }
  const ver = await db.query(`SELECT COALESCE(MAX(version),0)+1 AS v FROM analysis_results WHERE case_id=$1`, [caseId]);
  const nextVersion = Number(ver.rows[0].v);
  const inserted = await db.query(
    `INSERT INTO analysis_results(
       case_id, owner_user_id, version, source_type, result, evidence, uncertainty, model_info,
       structured_facts, recommended_keywords, suggested_next_inputs, report_payload, elderly_friendly_report,
       legal_analysis, scenario_type, used_evidence_ids, legal_risk_flags, persona_outputs, evidence_audit
     )
     VALUES($1,$2,$3,'text',$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18) RETURNING id, version`,
    [
      caseId,
      (req as any).user.id,
      nextVersion,
      JSON.stringify(agentResp),
      JSON.stringify(agentResp.evidence ?? []),
      JSON.stringify(agentResp.uncertainty ?? {}),
      JSON.stringify(agentResp.model_info ?? {}),
      JSON.stringify(agentResp.structured_facts ?? {}),
      JSON.stringify(agentResp.recommended_keywords ?? []),
      JSON.stringify(agentResp.suggested_next_inputs ?? []),
      JSON.stringify(composeClientReport(agentResp, { case: caseRow.rows[0] })),
      JSON.stringify(agentResp.elderly_friendly_report ?? {}),
      JSON.stringify(agentResp.legal_analysis ?? {}),
      agentResp.scenario_type ?? null,
      JSON.stringify((agentResp.evidence ?? []).map((x: any) => x.chunk_id).filter(Boolean)),
      JSON.stringify(agentResp.legal_liability?.risk_flags ?? agentResp.legal_analysis?.risk_flags ?? []),
      JSON.stringify({ analysts: agentResp.recommended_specialists ?? [] }),
      JSON.stringify(agentResp.evidence_audit ?? {})
    ]
  );
  await db.query(
    `UPDATE analysis_results SET knia_matches=$2, knia_primary_match=$3 WHERE id=$1`,
    [inserted.rows[0].id, JSON.stringify(agentResp.knia_matches ?? []), JSON.stringify(agentResp.knia_primary_match ?? null)]
  ).catch(() => undefined);
  return { result_id: inserted.rows[0].id, version: nextVersion, trace_id: traceId };
});

app.get(`${env.apiPrefix}/cases/:caseId/evidence`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { caseId } = req.params as any;
  const row = await db.query(`SELECT evidence FROM analysis_results WHERE case_id=$1 AND owner_user_id=$2 ORDER BY version DESC LIMIT 1`, [caseId, (req as any).user.id]);
  if (!row.rowCount) return reply.code(404).send(errorPayload("EVIDENCE_NOT_FOUND", "근거 데이터를 찾을 수 없습니다.", traceId));
  return { evidence: row.rows[0].evidence, trace_id: traceId };
});

app.get(`${env.apiPrefix}/evidence/:chunkId`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { chunkId } = req.params as any;
  const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  if (!uuidPattern.test(chunkId)) {
    return {
      chunk: {
        id: chunkId,
        chunk_summary: "정적 fallback 근거입니다. 외부 법률 API 또는 KB 적재가 부족할 때 최소 근거로 사용됩니다.",
        chunk_text: "국가법령정보센터/공공데이터 API 승인 또는 KB ingest 후에는 PostgreSQL에 저장된 실제 chunk 상세가 표시됩니다.",
        document_title: "Static Legal Fallback",
        source_name: "local-static-fallback",
        source_type: "static"
      },
      trace_id: traceId
    };
  }
  const row = await db.query(
    `SELECT kc.id, kc.chunk_text, kc.chunk_summary, kc.metadata AS chunk_metadata,
            kd.id AS document_id, kd.title AS document_title, kd.doc_type, kd.metadata AS document_metadata,
            ks.name AS source_name, ks.source_type, ks.source_uri
     FROM kb_chunks kc
     JOIN kb_documents kd ON kd.id=kc.document_id
     JOIN kb_sources ks ON ks.id=kd.source_id
     WHERE kc.id=$1`,
    [chunkId]
  );
  if (!row.rowCount) return reply.code(404).send(errorPayload("CHUNK_NOT_FOUND", "근거 문서를 찾을 수 없습니다.", traceId));
  return { chunk: row.rows[0], trace_id: traceId };
});

app.get(`${env.apiPrefix}/legal/evidence/:chunkId`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const { chunkId } = req.params as any;
  const row = await db.query(
    `SELECT kc.id, kc.chunk_text, kc.chunk_summary, kc.article_no, kc.clause_no,
            kc.scenario_tags, kc.keywords, kc.metadata AS chunk_metadata,
            kd.id AS document_id, kd.title AS document_title, kd.doc_type, kd.summary AS document_summary,
            kd.metadata AS document_metadata, ks.name AS source_name, ks.source_type, ks.source_uri
     FROM kb_chunks kc
     JOIN kb_documents kd ON kd.id=kc.document_id
     JOIN kb_sources ks ON ks.id=kd.source_id
     WHERE kc.id=$1`,
    [chunkId]
  );
  if (!row.rowCount) return reply.code(404).send(errorPayload("CHUNK_NOT_FOUND", "근거 문서를 찾을 수 없습니다.", traceId));
  return { chunk: row.rows[0], trace_id: traceId };
});


app.get(`${env.apiPrefix}/knia/ranking`, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  const limit = Math.min(Number((req.query as any)?.limit ?? 20), 50);
  const rawType = String((req.query as any)?.accidentPartyType ?? "all").trim() || "all";
  const q = String((req.query as any)?.q ?? "").trim();
  const categories = [
    { label: "\uC804\uCCB4", value: "all", source_value: "\uC804\uCCB4" },
    { label: "\uCC28\uB300\uCC28", value: "car_vs_car", source_value: "\uCC28\uB300\uCC28" },
    { label: "\uCC28\uB300\uC0AC\uB78C", value: "car_vs_person", source_value: "\uCC28\uB300\uC0AC\uB78C" },
    { label: "\uCC28\uB300\uC790\uC804\uAC70", value: "car_vs_bicycle", source_value: "\uCC28\uB300\uC790\uC804\uAC70" }
  ];
  const typeMap: Record<string, { value: string; source: string }> = {};
  for (const category of categories) {
    typeMap[category.value] = { value: category.value, source: category.source_value };
    typeMap[category.source_value] = { value: category.value, source: category.source_value };
  }
  const selected = typeMap[rawType] ?? typeMap.all;
  const params: any[] = [selected.source];
  let where = `source_category=$1`;
  if (q) {
    params.push(`%${q}%`);
    where += ` AND (title ILIKE $${params.length} OR chart_no ILIKE $${params.length})`;
  }
  params.push(limit);
  const rows = await db.query(
    `SELECT knia_ranking_items.rank, knia_ranking_items.chart_no, knia_ranking_items.chart_type, knia_ranking_items.title,
            knia_ranking_items.search_count, knia_ranking_items.percentage, knia_ranking_items.source_category,
            knia_ranking_items.accident_party_type, knia_ranking_items.source_url, knia_ranking_items.source_detail_url,
            knia_ranking_items.local_chart_url, knia_ranking_items.source_onclick, knia_ranking_items.chart_url,
            knia_ranking_items.collected_at,
            c.base_fault_a, c.base_fault_b,
            CASE WHEN c.detail_collected_at IS NOT NULL THEN true ELSE false END AS has_detail,
            (SELECT COUNT(*)::int FROM knia_adjustment_factors af
              WHERE af.chart_no=knia_ranking_items.chart_no AND af.chart_type=COALESCE(knia_ranking_items.chart_type, '1')) AS adjustment_factor_count,
            (SELECT COUNT(*)::int FROM knia_chart_reference_sections rs
              WHERE rs.chart_no=knia_ranking_items.chart_no AND rs.chart_type=COALESCE(knia_ranking_items.chart_type, '1')) AS reference_section_count
     FROM knia_ranking_items
     LEFT JOIN knia_fault_charts c
       ON c.chart_no=knia_ranking_items.chart_no AND c.chart_type=COALESCE(knia_ranking_items.chart_type, '1')
     WHERE ${where}
     ORDER BY rank ASC
     LIMIT $${params.length}`,
    params,
  );
  return reply.send({
    items: rows.rows.map((row: any) => ({
      rank: Number(row.rank),
      rank_no: Number(row.rank),
      chart_no: row.chart_no,
      chart_type: row.chart_type ?? "1",
      title: row.title,
      search_count: row.search_count == null ? null : Number(row.search_count),
      percentage: row.percentage == null ? null : Number(row.percentage),
      source_category: row.source_category,
      accident_party_type: row.accident_party_type,
      source_url: row.source_url,
      source_detail_url: row.source_detail_url,
      local_chart_url: row.local_chart_url ?? row.chart_url ?? `/knia/charts/${encodeURIComponent(row.chart_no)}?chartType=${encodeURIComponent(row.chart_type ?? "1")}`,
      source_onclick: row.source_onclick,
      chart_url: row.chart_url ?? row.local_chart_url ?? `/knia/charts/${encodeURIComponent(row.chart_no)}?chartType=${encodeURIComponent(row.chart_type ?? "1")}`,
      has_detail: !!row.has_detail,
      base_fault_a: row.base_fault_a == null ? null : Number(row.base_fault_a),
      base_fault_b: row.base_fault_b == null ? null : Number(row.base_fault_b),
      adjustment_factor_count: Number(row.adjustment_factor_count ?? 0),
      reference_section_count: Number(row.reference_section_count ?? 0),
      collected_at: row.collected_at,
    })),
    categories,
    trace_id: traceId,
    empty_message: rows.rowCount === 0 ? "\uC544\uC9C1 \uC218\uC9D1\uB41C \uAC80\uC0C9\uC21C\uC704\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4. \uAD00\uB9AC\uC790 \uC218\uC9D1\uC744 \uBA3C\uC800 \uC2E4\uD589\uD558\uC138\uC694." : undefined,
  });
});

app.get(`${env.apiPrefix}/knia/charts/:chartNo`, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  const chartNo = decodeURIComponent(String((req.params as any).chartNo));
  const chartType = String((req.query as any)?.chartType ?? "1");
  const row = await db.query(
    `SELECT chart_no, chart_type, title, vehicle_a_label, vehicle_b_label, category_path,
            accident_summary, applicable_text, non_applicable_text, basic_fault_text,
            base_fault_a, base_fault_b, applied_fault_a, applied_fault_b,
            accident_explanation, accident_situation_lines, adjustment_factors,
            adjustment_explanations, related_laws, case_references,
            source_url, source_detail_url, thumbnail_url, video_url, media_embed_url,
            media_provider, license_status, attribution, updated_at,
            accident_party_type, accident_party_label, vehicle_a_role, vehicle_b_role,
            vulnerable_road_user_type, object_type, scenario_summary_easy,
            recommended_user_actions, display_tags, detail_collected_at
     FROM knia_fault_charts
     WHERE chart_no=$1 AND chart_type=$2
     LIMIT 1`,
    [chartNo, chartType]
  ).catch(() => ({ rowCount: 0, rows: [] as any[] }));
  if (!row.rowCount) {
    const rankingRow = await db.query(
      `SELECT chart_no, COALESCE(chart_type, '1') AS chart_type, title, source_category,
              accident_party_type, source_url, source_detail_url, local_chart_url, chart_url, collected_at
       FROM knia_ranking_items
       WHERE chart_no=$1 AND COALESCE(chart_type, '1')=$2
       ORDER BY collected_at DESC, rank ASC
       LIMIT 1`,
      [chartNo, chartType]
    ).catch(() => ({ rowCount: 0, rows: [] as any[] }));
    if (!rankingRow.rowCount) {
      return reply.code(404).send(errorPayload("KNIA_CHART_NOT_FOUND", "과실비율 기준을 찾을 수 없습니다. 먼저 KNIA 수집을 실행해 주세요.", traceId));
    }
    const ranking = rankingRow.rows[0];
    const sourceDetailUrl = ranking.source_detail_url || ranking.source_url;
    return {
      chart: {
        chart_no: ranking.chart_no,
        chart_type: ranking.chart_type,
        title: ranking.title || `KNIA 과실비율 인정기준 ${ranking.chart_no}`,
        vehicle_a_label: null,
        vehicle_b_label: null,
        category_path: [ranking.source_category].filter(Boolean),
        accident_party_type: ranking.accident_party_type ?? "unknown",
        accident_party_label: ranking.source_category ?? "사고유형 확인 필요",
        vehicle_a_role: null,
        vehicle_b_role: null,
        vulnerable_road_user_type: null,
        object_type: null,
        scenario_summary_easy: "검색순위에는 포함되어 있지만 상세 기준 본문은 아직 로컬 DB에 수집되지 않았습니다.",
        recommended_user_actions: ["관리자 권한으로 상세 기준 수집을 실행한 뒤 다시 확인해 주세요."],
        display_tags: ["ranking_only"],
        accident_summary: "검색순위에는 포함되어 있지만 상세 기준 본문은 아직 로컬 DB에 수집되지 않았습니다.",
        applicable_text: "상세 기준 수집 후 KNIA 원문 적용 조건을 표시합니다.",
        non_applicable_text: "상세 기준 수집 후 예외 조건과 주의 사항을 표시합니다.",
        basic_fault_text: "상세 기준 수집 후 기본 과실비율을 표시합니다.",
        base_fault_a: null,
        base_fault_b: null,
        applied_fault_a: null,
        applied_fault_b: null,
        accident_explanation: "상세 기준 수집이 필요한 KNIA 검색순위 항목입니다.",
        accident_situation_lines: [],
        adjustment_factors: [],
        adjustment_explanations: [],
        related_laws: [],
        case_references: [],
        source_url: ranking.source_url,
        source_detail_url: sourceDetailUrl,
        thumbnail_url: null,
        video_url: null,
        media_embed_url: null,
        media_provider: "external_url",
        related_video: {
          display_mode: "external_link",
          source_url: sourceDetailUrl || ranking.source_url,
          embed_url: null,
          thumbnail_url: null,
          button_label: "KNIA 원문 보기",
          attribution: "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털"
        },
        license_status: "source_link_only",
        attribution: "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털",
        updated_at: ranking.collected_at,
        detail_collected_at: null,
        is_ranking_placeholder: true,
        adjustment_summary: {
          adjustment_factor_count: 0,
          adjustment_explanation_count: 0,
          related_law_count: 0,
          case_reference_count: 0,
        }
      },
      trace_id: traceId
    };
  }
  const chart = row.rows[0];
  return {
    chart: {
      chart_no: chart.chart_no,
      chart_type: chart.chart_type,
      title: chart.title,
      vehicle_a_label: chart.vehicle_a_label,
      vehicle_b_label: chart.vehicle_b_label,
      category_path: chart.category_path ?? [],
      accident_party_type: chart.accident_party_type ?? "unknown",
      accident_party_label: chart.accident_party_label ?? "사고유형 확인 필요",
      vehicle_a_role: chart.vehicle_a_role,
      vehicle_b_role: chart.vehicle_b_role,
      vulnerable_road_user_type: chart.vulnerable_road_user_type,
      object_type: chart.object_type,
      scenario_summary_easy: chart.scenario_summary_easy,
      recommended_user_actions: chart.recommended_user_actions ?? [],
      display_tags: chart.display_tags ?? [],
      accident_summary: chart.accident_summary,
      applicable_text: cleanKniaPublicText(chart.applicable_text, chart.accident_summary ?? "원문 기준에서 상세 적용 조건을 확인해 주세요."),
      non_applicable_text: cleanKniaPublicText(chart.non_applicable_text, "급정거, 끼어들기 직후 사고 등 세부 상황에 따라 다른 기준이 적용될 수 있습니다."),
      basic_fault_text: cleanKniaPublicText(chart.basic_fault_text, "기본 과실은 사고 상황에 따라 달라질 수 있습니다."),
      base_fault_a: chart.base_fault_a,
      base_fault_b: chart.base_fault_b,
      applied_fault_a: chart.applied_fault_a,
      applied_fault_b: chart.applied_fault_b,
      accident_explanation: chart.accident_explanation,
      accident_situation_lines: chart.accident_situation_lines ?? [],
      adjustment_factors: chart.adjustment_factors ?? [],
      adjustment_explanations: chart.adjustment_explanations ?? [],
      related_laws: chart.related_laws ?? [],
      case_references: chart.case_references ?? [],
      source_url: chart.source_url,
      source_detail_url: chart.source_detail_url ?? chart.source_url,
      thumbnail_url: chart.thumbnail_url,
      video_url: chart.video_url,
      media_embed_url: chart.media_embed_url,
      media_provider: "external_url",
      related_video: {
        display_mode: chart.media_embed_url ? "embed" : "external_link",
        source_url: chart.video_url || chart.source_url,
        embed_url: chart.media_embed_url,
        thumbnail_url: chart.thumbnail_url,
        button_label: chart.video_url ? "관련 영상 보기" : "원문 기준 보기",
        attribution: chart.attribution ?? "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털"
      },
      license_status: "source_link_only",
      attribution: chart.attribution ?? "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털",
      updated_at: chart.updated_at,
      detail_collected_at: chart.detail_collected_at,
      adjustment_summary: {
        adjustment_factor_count: Array.isArray(chart.adjustment_factors) ? chart.adjustment_factors.length : 0,
        adjustment_explanation_count: Array.isArray(chart.adjustment_explanations) ? chart.adjustment_explanations.length : 0,
        related_law_count: Array.isArray(chart.related_laws) ? chart.related_laws.length : 0,
        case_reference_count: Array.isArray(chart.case_references) ? chart.case_references.length : 0,
      }
    },
    trace_id: traceId
  };
});

app.post(`${env.apiPrefix}/knia/match`, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  try {
    const result = await callInternalAgent("/internal/v1/knia/match", req.body ?? {}, traceId, {
      baseUrl: env.agentUrl,
      internalToken: env.internalToken,
      timeoutMs: env.timeoutMs,
      retryCount: env.retryCount
    });
    const safeItems = (result.items ?? []).map((x: any) => ({
      chart_no: x.chart_no,
      chart_type: x.chart_type,
      title: x.title,
      accident_party_type: x.accident_party_type,
      accident_party_label: x.accident_party_label,
      display_tags: x.display_tags ?? [],
      recommended_user_actions: x.recommended_user_actions ?? [],
      match_label: x.match_label,
      match_reason: x.match_reason,
      base_fault_a: x.base_fault_a,
      base_fault_b: x.base_fault_b,
      accident_summary: x.accident_summary,
      basic_fault_text: x.basic_fault_text,
      source_url: x.source_url,
      thumbnail_url: x.thumbnail_url,
      video_url: x.video_url,
      media: x.media,
      attribution: x.attribution
    }));
    return { items: safeItems, source: "과실비율정보포털", trace_id: traceId };
  } catch {
    return reply.code(502).send(errorPayload("KNIA_MATCH_FAILED", "과실비율 기준 매칭에 실패했습니다.", traceId));
  }
});

app.post(`${env.apiPrefix}/knia/fault/estimate`, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  try {
    const result = await callInternalAgent("/internal/v1/knia/fault/estimate", req.body ?? {}, traceId, {
      baseUrl: env.agentUrl,
      internalToken: env.internalToken,
      timeoutMs: env.timeoutMs,
      retryCount: env.retryCount
    });
    return { ...result, trace_id: traceId };
  } catch (err: any) {
    return reply.code(502).send(errorPayload("KNIA_FAULT_ESTIMATE_FAILED", err?.message || "KNIA 가감요소 기반 과실 산정에 실패했습니다.", traceId));
  }
});

app.get(`${env.apiPrefix}/knia/charts/:chartNo/adjustments`, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  const chartNo = decodeURIComponent(String((req.params as any).chartNo));
  const chartType = String((req.query as any)?.chartType ?? "1");
  const rows = await db.query(
    `SELECT label, condition_code, checkbox_value, delta_a, delta_b, source_case_id, factor_order, source_detail_url
     FROM knia_adjustment_factors
     WHERE chart_no=$1 AND chart_type=$2
     ORDER BY factor_order ASC, id ASC`,
    [chartNo, chartType]
  );
  return { chart_no: chartNo, chart_type: chartType, items: rows.rows, trace_id: traceId };
});

app.get(`${env.apiPrefix}/knia/charts/:chartNo/references`, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  const chartNo = decodeURIComponent(String((req.params as any).chartNo));
  const chartType = String((req.query as any)?.chartType ?? "1");
  const rows = await db.query(
    `SELECT section_type, title, body, law_title, law_text, case_title, case_body, decision_summary, item_order, source_detail_url
     FROM knia_chart_reference_sections
     WHERE chart_no=$1 AND chart_type=$2
     ORDER BY section_type ASC, item_order ASC, id ASC`,
    [chartNo, chartType]
  );
  const grouped: any = { adjustment_explanations: [], related_laws: [], case_references: [] };
  for (const row of rows.rows) {
    if (row.section_type === "adjustment_explanation") grouped.adjustment_explanations.push(row);
    if (row.section_type === "related_law") grouped.related_laws.push(row);
    if (row.section_type === "case_reference") grouped.case_references.push(row);
  }
  return { chart_no: chartNo, chart_type: chartType, ...grouped, trace_id: traceId };
});

app.post(`${env.apiPrefix}/admin/knia/collect`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const body = (req.body ?? {}) as any;
  const rankingOnly = body.ranking === true && body.menu === false && body.charts === false;
  if (!rankingOnly && !requireAdmin(req as any, reply)) return;
  const result: any = {};
  try {
    if (body.menu !== false) result.menu = await callInternalAgent("/internal/v1/knia/collect/menu-pages", {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 180000, retryCount: 0 });
    if (body.ranking !== false) result.ranking = await callInternalAgent("/internal/v1/knia/collect/ranking", {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 180000, retryCount: 0 });
    if (body.charts !== false) result.charts = await callInternalAgent("/internal/v1/knia/collect/charts", { chart_nos: body.chart_nos, max_charts: body.max_charts }, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 240000, retryCount: 0 });
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
    const result = await callInternalAgent("/internal/v1/knia/collect/ranking-details", req.body ?? {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 600000, retryCount: 0 });
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
    const result = await callInternalAgent("/internal/v1/knia/rebuild-embeddings", req.body ?? {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 240000, retryCount: 0 });
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
    const result = await callInternalAgent("/internal/v1/knia/import-json", req.body ?? {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 600000, retryCount: 0 });
    return { result, trace_id: traceId };
  } catch (err: any) {
    return reply.code(502).send(errorPayload("KNIA_JSON_IMPORT_FAILED", "KNIA JSON 데이터를 가져오지 못했습니다. 파일 경로와 데이터 형식을 확인해 주세요.", traceId));
  }
});

app.post(`${env.apiPrefix}/admin/knia/json/rebuild-embeddings`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  if (!requireAdmin(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  try {
    const result = await callInternalAgent("/internal/v1/knia/json/rebuild-embeddings", req.body ?? {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 600000, retryCount: 0 });
    return { result, trace_id: traceId };
  } catch {
    return reply.code(502).send(errorPayload("KNIA_JSON_EMBEDDING_FAILED", "KNIA JSON 임베딩 재생성에 실패했습니다.", traceId));
  }
});

app.get(`${env.apiPrefix}/knia/myaccident-pages`, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  try {
    const result = await callInternalAgentGet("/internal/v1/knia/myaccident-pages", traceId);
    return { items: result.items ?? [], trace_id: traceId };
  } catch {
    return reply.code(502).send(errorPayload("KNIA_MENU_FAILED", "KNIA 메뉴 목록을 불러오지 못했습니다.", traceId));
  }
});

app.get(`${env.apiPrefix}/knia/myaccident/:myaccidentNo/tree`, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  const myaccidentNo = Number((req.params as any).myaccidentNo);
  try {
    const result = await callInternalAgentGet(`/internal/v1/knia/myaccident/${myaccidentNo}/tree`, traceId);
    return { ...result, trace_id: traceId };
  } catch {
    return reply.code(502).send(errorPayload("KNIA_TREE_FAILED", "KNIA 사고유형 트리를 불러오지 못했습니다.", traceId));
  }
});

app.get(`${env.apiPrefix}/knia/json/search`, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  const q = String((req.query as any)?.q ?? "");
  const accidentPartyType = String((req.query as any)?.accidentPartyType ?? "");
  const limit = Math.min(Number((req.query as any)?.limit ?? 5), 20);
  try {
    const path = `/internal/v1/knia/json/search?q=${encodeURIComponent(q)}&limit=${limit}${accidentPartyType ? `&accidentPartyType=${encodeURIComponent(accidentPartyType)}` : ""}`;
    const result = await callInternalAgentGet(path, traceId);
    const items = (result.items ?? []).map((x: any) => ({
      title: x.title,
      summary: x.summary,
      source_url: x.source_url,
      accident_party_label: x.accident_party_label,
      display_tags: x.display_tags ?? [],
      attribution: x.attribution ?? "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회"
    }));
    return { items, cache: result.cache ? { exact_hit: !!result.cache.exact_hit, semantic_hit: !!result.cache.semantic_hit } : undefined, trace_id: traceId };
  } catch {
    return reply.code(502).send(errorPayload("KNIA_JSON_SEARCH_FAILED", "KNIA JSON 검색에 실패했습니다.", traceId));
  }
});

app.get(`${env.apiPrefix}/knia/media/search`, async (req, reply) => {
  const traceId = req.headers["x-correlation-id"] as string;
  const q = String((req.query as any)?.q ?? "");
  const accidentPartyType = String((req.query as any)?.accidentPartyType ?? "");
  try {
    const path = `/internal/v1/knia/media/search?q=${encodeURIComponent(q)}${accidentPartyType ? `&accidentPartyType=${encodeURIComponent(accidentPartyType)}` : ""}`;
    const result = await callInternalAgentGet(path, traceId);
    return { items: result.items ?? [], trace_id: traceId };
  } catch {
    return reply.code(502).send(errorPayload("KNIA_MEDIA_SEARCH_FAILED", "KNIA 영상/문서 검색에 실패했습니다.", traceId));
  }
});

app.post(`${env.apiPrefix}/admin/cache/invalidate`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  if (!requireAdmin(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  try {
    const result = await callInternalAgent("/internal/v1/cache/invalidate", req.body ?? { scope: "knia_json" }, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 60000, retryCount: 0 });
    return { result, trace_id: traceId };
  } catch {
    return reply.code(502).send(errorPayload("CACHE_INVALIDATE_FAILED", "캐시 무효화에 실패했습니다.", traceId));
  }
});

app.post(`${env.apiPrefix}/admin/legal/ingest`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  if (!requireAdmin(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  try {
    const result = await callInternalAgent("/internal/v1/legal/ingest", {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 120000, retryCount: 0 });
    return { result, trace_id: traceId };
  } catch {
    return reply.code(502).send(errorPayload("LEGAL_INGEST_FAILED", "법률정보 적재에 실패했습니다.", traceId));
  }
});

app.post(`${env.apiPrefix}/admin/legal/rebuild-embeddings`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  if (!requireAdmin(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  try {
    const result = await callInternalAgent("/internal/v1/legal/rebuild-embeddings", {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 120000, retryCount: 0 });
    return { result, trace_id: traceId };
  } catch {
    return reply.code(502).send(errorPayload("LEGAL_EMBEDDING_REBUILD_FAILED", "법률 임베딩 재생성에 실패했습니다.", traceId));
  }
});

app.get(`${env.apiPrefix}/admin/legal/retrieval-test`, async (req, reply) => {
  if (!requireUser(req as any, reply)) return;
  if (!requireAdmin(req as any, reply)) return;
  const traceId = req.headers["x-correlation-id"] as string;
  const q = encodeURIComponent(String((req.query as any)?.q ?? "후미추돌 안전거리 과실비율"));
  try {
    const result = await callInternalAgentGet(`/internal/v1/legal/retrieval-test?q=${q}`, traceId);
    return { result, trace_id: traceId };
  } catch {
    return reply.code(502).send(errorPayload("LEGAL_RETRIEVAL_TEST_FAILED", "법률 RAG 테스트에 실패했습니다.", traceId));
  }
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


