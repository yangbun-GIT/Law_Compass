import type { FastifyReply, FastifyRequest } from "fastify";
import { errorPayload } from "./errors.js";

export function routeKey(req: any) {
  return req.routeOptions?.url ?? req.url;
}

export function requireUser(req: any, reply: FastifyReply) {
  const traceId = req.headers["x-correlation-id"] as string;
  if (!req.user?.id) {
    reply.code(401).send(errorPayload("UNAUTHORIZED", "\uB85C\uADF8\uC778\uC774 \uD544\uC694\uD569\uB2C8\uB2E4.", traceId));
    return false;
  }
  return true;
}

export function requireAdmin(req: FastifyRequest & { user?: any }, reply: FastifyReply, adminToken = "") {
  const traceId = req.headers["x-correlation-id"] as string;
  const token = req.headers["x-admin-token"] as string | undefined;
  if (adminToken && token === adminToken) return true;
  if (req.user?.role === "admin") return true;
  reply.code(403).send(errorPayload("ADMIN_REQUIRED", "\uAD00\uB9AC\uC790 \uAD8C\uD55C\uC774 \uD544\uC694\uD569\uB2C8\uB2E4.", traceId));
  return false;
}
