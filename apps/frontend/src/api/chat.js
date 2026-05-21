const RAW_API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const API_BASE = RAW_API_BASE.endsWith("/api/v1") ? RAW_API_BASE.slice(0, -"/api/v1".length) : RAW_API_BASE;
function makeApiError(message, code, status, traceId) {
    const err = new Error(message);
    err.code = code;
    err.status = status;
    err.traceId = traceId;
    return err;
}
async function request(path, init) {
    const headers = new Headers(init?.headers || {});
    if (!headers.has("content-type") && init?.body && !(init.body instanceof FormData)) {
        headers.set("content-type", "application/json");
    }
    let res;
    try {
        res = await fetch(`${API_BASE}${path}`, { ...init, credentials: "include", headers });
    }
    catch {
        throw makeApiError("서버에 연결하지 못했습니다. Docker Compose와 gateway/edge 실행 상태를 확인해 주세요.", "NETWORK_ERROR");
    }
    const text = await res.text();
    let data = {};
    try {
        data = text ? JSON.parse(text) : {};
    }
    catch {
        throw makeApiError("서버 응답을 읽지 못했습니다. 잠시 후 다시 시도해 주세요.", "INVALID_JSON_RESPONSE", res.status);
    }
    if (!res.ok) {
        throw makeApiError(data?.error?.message || "요청 처리 중 문제가 발생했습니다.", data?.error?.code, res.status, data?.error?.trace_id);
    }
    return data;
}
function idempo() {
    return { "Idempotency-Key": crypto.randomUUID() };
}
export const chatApi = {
    createSession: (payload) => request("/api/v1/chat/sessions", {
        method: "POST",
        body: JSON.stringify(payload),
        headers: idempo()
    }),
    getMessages: (sessionId) => request(`/api/v1/chat/sessions/${sessionId}/messages`),
    sendMessage: (sessionId, payload) => request(`/api/v1/chat/sessions/${sessionId}/messages`, {
        method: "POST",
        body: JSON.stringify(payload),
        headers: idempo()
    }),
    quick: (payload) => request("/api/v1/chat/quick", {
        method: "POST",
        body: JSON.stringify(payload),
        headers: idempo()
    }),
    applyDraft: (draftCase) => request("/api/v1/chat/apply-draft", {
        method: "POST",
        body: JSON.stringify({ draft_case: draftCase }),
        headers: idempo()
    })
};
