import type { ChatContext, ChatMessage, ChatResponse } from "../types/chat";

const RAW_API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const API_BASE = RAW_API_BASE.endsWith("/api/v1") ? RAW_API_BASE.slice(0, -"/api/v1".length) : RAW_API_BASE;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers || {});
  if (!headers.has("content-type") && init?.body && !(init.body instanceof FormData)) {
    headers.set("content-type", "application/json");
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, credentials: "include", headers });
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) {
    const err = new Error(data?.error?.message || "요청 처리 중 문제가 발생했습니다.") as Error & { code?: string; status?: number };
    err.code = data?.error?.code;
    err.status = res.status;
    throw err;
  }
  return data as T;
}

function idempo() {
  return { "Idempotency-Key": crypto.randomUUID() };
}

export const chatApi = {
  createSession: (payload: { case_id?: string | null; title?: string; context?: ChatContext }) =>
    request<{ session: { id: string }; trace_id: string }>("/api/v1/chat/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: idempo()
    }),
  getMessages: (sessionId: string) =>
    request<{ items: ChatMessage[]; trace_id: string }>(`/api/v1/chat/sessions/${sessionId}/messages`),
  sendMessage: (sessionId: string, payload: { message: string; context?: ChatContext }) =>
    request<ChatResponse>(`/api/v1/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify(payload),
      headers: idempo()
    }),
  quick: (payload: { message: string; case_id?: string | null; context?: ChatContext }) =>
    request<ChatResponse>("/api/v1/chat/quick", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: idempo()
    }),
  applyDraft: (draftCase: Record<string, any>) =>
    request<{ ok: boolean; draft_case: any; next_route: string }>("/api/v1/chat/apply-draft", {
      method: "POST",
      body: JSON.stringify({ draft_case: draftCase }),
      headers: idempo()
    })
};
