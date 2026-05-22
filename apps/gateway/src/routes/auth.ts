import type { FastifyInstance, FastifyReply, FastifyRequest } from "fastify";
import { randomUUID } from "node:crypto";
import bcrypt from "bcryptjs";
import { sha256 } from "../lib/security.js";
import { requireUser } from "../lib/request-guards.js";

export type AuthRouteOptions = {
  apiPrefix: string;
  db: any;
  cookieSecure: boolean;
  jwtAccessTtlSec: number;
  jwtRefreshTtlSec: number;
  errorPayload: (code: string, message: string, traceId: string) => any;
};

function trace(req: FastifyRequest) {
  return (req.headers["x-correlation-id"] as string) || randomUUID();
}

function authCookies(reply: FastifyReply, accessToken: string, refreshRaw: string, secure: boolean) {
  reply.setCookie("lc_at", accessToken, { httpOnly: true, sameSite: "lax", path: "/", secure });
  reply.setCookie("lc_rt", refreshRaw, { httpOnly: true, sameSite: "lax", path: "/", secure });
}

export function registerAuthRoutes(app: FastifyInstance, opts: AuthRouteOptions) {
  app.post(`${opts.apiPrefix}/auth/signup`, {
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
    const traceId = trace(req);
    const body = req.body as any;
    const pwHash = await bcrypt.hash(body.password, 10);
    try {
      const inserted = await opts.db.query(
        `INSERT INTO users(email,password_hash,display_name) VALUES ($1,$2,$3) RETURNING id,email,display_name,role`,
        [body.email.toLowerCase(), pwHash, body.display_name]
      );
      return { user: inserted.rows[0], trace_id: traceId };
    } catch {
      return reply.code(409).send(opts.errorPayload("EMAIL_EXISTS", "이미 가입된 이메일입니다.", traceId));
    }
  });

  app.post(`${opts.apiPrefix}/auth/login`, {
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
    const traceId = trace(req);
    const body = req.body as any;
    const userRes = await opts.db.query(
      `SELECT id,email,password_hash,role,display_name FROM users WHERE email=$1 AND deleted_at IS NULL`,
      [body.email.toLowerCase()]
    );
    const user = userRes.rows[0];
    if (!user || !(await bcrypt.compare(body.password, user.password_hash))) {
      return reply.code(401).send(opts.errorPayload("INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다.", traceId));
    }

    const accessToken = await app.jwt.sign({ sub: user.id, role: user.role }, { expiresIn: opts.jwtAccessTtlSec });
    const refreshRaw = randomUUID() + randomUUID();
    const refreshHash = sha256(refreshRaw);
    await opts.db.query(
      `INSERT INTO auth_refresh_tokens(user_id, token_hash, expires_at) VALUES($1,$2, now() + ($3 || ' seconds')::interval)`,
      [user.id, refreshHash, opts.jwtRefreshTtlSec]
    );
    authCookies(reply, accessToken, refreshRaw, opts.cookieSecure);
    return { access_token: accessToken, user: { id: user.id, email: user.email, role: user.role, display_name: user.display_name }, trace_id: traceId };
  });

  app.post(`${opts.apiPrefix}/auth/refresh`, async (req, reply) => {
    const traceId = trace(req);
    const refreshRaw = (req as any).cookies.lc_rt;
    if (!refreshRaw) return reply.code(401).send(opts.errorPayload("NO_REFRESH_TOKEN", "재로그인이 필요합니다.", traceId));

    const refreshHash = sha256(refreshRaw);
    const tokenRes = await opts.db.query(
      `SELECT id,user_id FROM auth_refresh_tokens WHERE token_hash=$1 AND revoked_at IS NULL AND expires_at > now()`,
      [refreshHash]
    );
    if (!tokenRes.rowCount) return reply.code(401).send(opts.errorPayload("INVALID_REFRESH", "세션이 만료되었습니다.", traceId));

    const row = tokenRes.rows[0];
    const newRaw = randomUUID() + randomUUID();
    const newHash = sha256(newRaw);
    await opts.db.query("UPDATE auth_refresh_tokens SET revoked_at=now() WHERE id=$1", [row.id]);
    await opts.db.query(
      `INSERT INTO auth_refresh_tokens(user_id, token_hash, expires_at, rotated_from) VALUES($1,$2, now() + ($3 || ' seconds')::interval, $4)`,
      [row.user_id, newHash, opts.jwtRefreshTtlSec, row.id]
    );
    const user = await opts.db.query(`SELECT id,email,role,display_name FROM users WHERE id=$1`, [row.user_id]);
    const accessToken = await app.jwt.sign({ sub: row.user_id, role: user.rows[0].role }, { expiresIn: opts.jwtAccessTtlSec });
    authCookies(reply, accessToken, newRaw, opts.cookieSecure);
    return { access_token: accessToken, user: user.rows[0], trace_id: traceId };
  });

  app.post(`${opts.apiPrefix}/auth/logout`, async (req, reply) => {
    const traceId = trace(req);
    const refreshRaw = (req as any).cookies.lc_rt;
    if (refreshRaw) await opts.db.query(`UPDATE auth_refresh_tokens SET revoked_at=now() WHERE token_hash=$1`, [sha256(refreshRaw)]);
    reply.clearCookie("lc_at");
    reply.clearCookie("lc_rt");
    return { ok: true, trace_id: traceId };
  });

  app.get(`${opts.apiPrefix}/auth/me`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = trace(req);
    const row = await opts.db.query(`SELECT id,email,role,display_name FROM users WHERE id=$1 AND deleted_at IS NULL`, [(req as any).user.id]);
    if (!row.rowCount) return reply.code(404).send(opts.errorPayload("USER_NOT_FOUND", "사용자를 찾을 수 없습니다.", traceId));
    return { user: row.rows[0], trace_id: traceId };
  });
}
