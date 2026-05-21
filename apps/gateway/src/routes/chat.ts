import type { FastifyInstance } from "fastify";
import { randomUUID } from "node:crypto";
import { createChatSessionSchema, quickChatSchema, sendChatMessageSchema } from "../schemas/chatSchemas.js";
import { createChatSession, getChatSessionForAccess, listChatMessages, sendChatMessage } from "../services/chatService.js";

export type ChatRouteOptions = {
  apiPrefix: string;
  db: any;
  agentUrl: string;
  internalToken: string;
  timeoutMs: number;
  retryCount: number;
  errorPayload: (code: string, message: string, traceId: string) => any;
};

function trace(req: any) {
  return (req.headers["x-correlation-id"] as string) || randomUUID();
}

function userId(req: any) {
  return req.user?.id ?? null;
}

export function registerChatRoutes(app: FastifyInstance, opts: ChatRouteOptions) {
  const svc = {
    db: opts.db,
    agentUrl: opts.agentUrl,
    internalToken: opts.internalToken,
    timeoutMs: opts.timeoutMs,
    retryCount: opts.retryCount
  };

  app.post(`${opts.apiPrefix}/chat/sessions`, { schema: createChatSessionSchema }, async (req, reply) => {
    const body = (req.body ?? {}) as any;
    const session = await createChatSession(svc, {
      userId: userId(req),
      caseId: body.case_id ?? body.context?.case_id ?? null,
      title: body.title ?? "AI 사고 상담",
      context: body.context ?? {}
    });
    return { session, trace_id: trace(req) };
  });

  app.get(`${opts.apiPrefix}/chat/sessions/:sessionId/messages`, async (req, reply) => {
    const sessionId = String((req.params as any).sessionId);
    const session = await getChatSessionForAccess(svc, sessionId, userId(req));
    if (!session) return reply.code(404).send(opts.errorPayload("CHAT_SESSION_NOT_FOUND", "채팅 세션을 찾을 수 없습니다.", trace(req)));
    if ((session as any).forbidden) return reply.code(403).send(opts.errorPayload("CHAT_SESSION_FORBIDDEN", "이 채팅을 볼 권한이 없습니다.", trace(req)));
    return { items: await listChatMessages(svc, sessionId), trace_id: trace(req) };
  });

  app.post(`${opts.apiPrefix}/chat/sessions/:sessionId/messages`, { schema: sendChatMessageSchema }, async (req, reply) => {
    const sessionId = String((req.params as any).sessionId);
    const body = req.body as any;
    const session = await getChatSessionForAccess(svc, sessionId, userId(req));
    if (!session) return reply.code(404).send(opts.errorPayload("CHAT_SESSION_NOT_FOUND", "채팅 세션을 찾을 수 없습니다.", trace(req)));
    if ((session as any).forbidden) return reply.code(403).send(opts.errorPayload("CHAT_SESSION_FORBIDDEN", "이 채팅을 볼 권한이 없습니다.", trace(req)));
    try {
      return await sendChatMessage(svc, {
        sessionId,
        userId: userId(req),
        caseId: (session as any).case_id ?? body.context?.case_id ?? null,
        message: body.message,
        context: body.context ?? {},
        traceId: trace(req)
      });
    } catch (err) {
      req.log.error({ err }, "chat_agent_failed");
      return reply.code(502).send(opts.errorPayload("CHAT_AGENT_UNAVAILABLE", "AI 사고 도우미가 잠시 불안정합니다. 잠시 후 다시 시도해 주세요.", trace(req)));
    }
  });

  app.post(`${opts.apiPrefix}/chat/quick`, { schema: quickChatSchema }, async (req, reply) => {
    const body = req.body as any;
    const session = await createChatSession(svc, {
      userId: userId(req),
      caseId: body.case_id ?? body.context?.case_id ?? null,
      title: "빠른 사고 상담",
      context: body.context ?? {}
    });
    try {
      return await sendChatMessage(svc, {
        sessionId: session.id,
        userId: userId(req),
        caseId: session.case_id,
        message: body.message,
        context: body.context ?? {},
        traceId: trace(req)
      });
    } catch (err) {
      req.log.error({ err }, "quick_chat_agent_failed");
      return reply.code(502).send(opts.errorPayload("CHAT_AGENT_UNAVAILABLE", "AI 사고 도우미가 잠시 불안정합니다. 잠시 후 다시 시도해 주세요.", trace(req)));
    }
  });

  app.post(`${opts.apiPrefix}/chat/apply-draft`, async (req) => {
    const body = (req.body ?? {}) as any;
    return {
      ok: true,
      draft_case: body.draft_case ?? body,
      next_route: "/cases/new",
      trace_id: trace(req)
    };
  });
}


