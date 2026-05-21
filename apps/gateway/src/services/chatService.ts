import { callInternalAgent } from "../lib/internal-client.js";

export type ChatServiceOptions = {
  db: any;
  agentUrl: string;
  internalToken: string;
  timeoutMs: number;
  retryCount: number;
};

const TECHNICAL_KEYS = new Set([
  "match_score",
  "chunk_id",
  "score",
  "embedding",
  "model_info",
  "raw_html",
  "raw_evidence",
  "cache_key",
  "evidence_cache_key",
  "scenario_classifier",
  "orchestrator",
  "rag_top_k",
  "llm_enabled",
  "security_flags",
  "evidence_support_level",
  "decision_status"
]);

function stripTechnical(value: any): any {
  if (Array.isArray(value)) return value.map(stripTechnical).filter((x) => x !== undefined);
  if (!value || typeof value !== "object") return value;
  const out: Record<string, any> = {};
  for (const [key, item] of Object.entries(value)) {
    if (TECHNICAL_KEYS.has(key)) continue;
    out[key] = stripTechnical(item);
  }
  return out;
}

function safeUuid(value: unknown): string | null {
  const text = String(value ?? "").trim();
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(text) ? text : null;
}

export async function createChatSession(opts: ChatServiceOptions, input: { userId?: string | null; caseId?: string | null; title?: string | null; context?: any }) {
  const caseId = safeUuid(input.caseId);
  const result = await opts.db.query(
    `INSERT INTO chat_sessions(user_id, case_id, title, metadata)
     VALUES($1,$2,$3,$4)
     RETURNING id, user_id, case_id, title, status, metadata, created_at, updated_at`,
    [input.userId ?? null, caseId, input.title ?? "AI 사고 상담", JSON.stringify(input.context ?? {})]
  );
  return result.rows[0];
}

export async function getChatSessionForAccess(opts: ChatServiceOptions, sessionId: string, userId?: string | null) {
  const result = await opts.db.query(`SELECT * FROM chat_sessions WHERE id=$1`, [sessionId]);
  if (!result.rowCount) return null;
  const session = result.rows[0];
  if (session.user_id && userId && session.user_id !== userId) return { forbidden: true };
  if (session.user_id && !userId) return { forbidden: true };
  return session;
}

export async function listChatMessages(opts: ChatServiceOptions, sessionId: string) {
  const rows = await opts.db.query(
    `SELECT id, role, content, intent, violation_flags, suggestions, draft_case, knia_matches, knia_primary_match, metadata, created_at
     FROM chat_messages
     WHERE session_id=$1
     ORDER BY created_at ASC`,
    [sessionId]
  );
  return rows.rows.map(stripTechnical);
}

async function recentHistory(opts: ChatServiceOptions, sessionId: string) {
  const rows = await opts.db.query(
    `SELECT role, content FROM chat_messages WHERE session_id=$1 ORDER BY created_at DESC LIMIT 12`,
    [sessionId]
  );
  return rows.rows.reverse();
}

export async function sendChatMessage(
  opts: ChatServiceOptions,
  input: { sessionId: string; userId?: string | null; caseId?: string | null; message: string; context?: any; traceId: string }
) {
  const userMessage = await opts.db.query(
    `INSERT INTO chat_messages(session_id, role, content, metadata)
     VALUES($1,'user',$2,$3)
     RETURNING id, created_at`,
    [input.sessionId, input.message, JSON.stringify({ context: input.context ?? {} })]
  );

  const history = await recentHistory(opts, input.sessionId);
  const agentResponse = await callInternalAgent(
    "/internal/v1/chat/message",
    {
      session_id: input.sessionId,
      user_id: input.userId ?? null,
      case_id: input.caseId ?? null,
      message: input.message,
      context: input.context ?? {},
      history
    },
    input.traceId,
    {
      baseUrl: opts.agentUrl,
      internalToken: opts.internalToken,
      timeoutMs: opts.timeoutMs,
      retryCount: opts.retryCount
    }
  );

  const safe = stripTechnical(agentResponse ?? {});
  const assistant = await opts.db.query(
    `INSERT INTO chat_messages(
       session_id, role, content, intent, violation_flags, suggestions,
       draft_case, knia_matches, knia_primary_match, metadata
     )
     VALUES($1,'assistant',$2,$3,$4,$5,$6,$7,$8,$9)
     RETURNING id, created_at`,
    [
      input.sessionId,
      safe.reply ?? "죄송합니다. 잠시 후 다시 시도해 주세요.",
      safe.intent ?? null,
      JSON.stringify(safe.safety?.flags ?? []),
      JSON.stringify(safe.suggestions ?? []),
      safe.draft_case ? JSON.stringify(safe.draft_case) : null,
      JSON.stringify(safe.knia_matches ?? []),
      safe.knia_primary_match ? JSON.stringify(safe.knia_primary_match) : null,
      JSON.stringify({ route_hint: safe.route_hint ?? null })
    ]
  );

  const safety = safe.safety ?? { allowed: true, flags: [] };
  if (safety.allowed === false || (safety.flags ?? []).length) {
    const flags = safety.flags?.length ? safety.flags : ["unknown"];
    for (const flag of flags) {
      await opts.db.query(
        `INSERT INTO chat_safety_logs(session_id, user_id, message_id, violation_type, severity, raw_text, action)
         VALUES($1,$2,$3,$4,$5,$6,$7)`,
        [input.sessionId, input.userId ?? null, userMessage.rows[0].id, flag, safety.severity ?? "low", input.message, safety.allowed === false ? "refused" : "warned"]
      ).catch(() => undefined);
    }
  }

  await opts.db.query(`UPDATE chat_sessions SET updated_at=now(), title=COALESCE(title,$2) WHERE id=$1`, [input.sessionId, input.message.slice(0, 80)]).catch(() => undefined);

  return stripTechnical({
    session_id: input.sessionId,
    user_message_id: userMessage.rows[0].id,
    assistant_message_id: assistant.rows[0].id,
    message: { role: "assistant", content: safe.reply, intent: safe.intent },
    reply: safe.reply,
    intent: safe.intent,
    suggestions: safe.suggestions ?? [],
    draft_case: safe.draft_case ?? null,
    knia_matches: safe.knia_matches ?? [],
    knia_primary_match: safe.knia_primary_match ?? null,
    safety,
    route_hint: safe.route_hint ?? null
  });
}


