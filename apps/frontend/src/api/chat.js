const RAW_API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const API_BASE = RAW_API_BASE.endsWith("/api/v1") ? RAW_API_BASE.slice(0, -"/api/v1".length) : RAW_API_BASE;
async function request(path, init) {
    const headers = new Headers(init?.headers || {});
    if (!headers.has("content-type") && init?.body && !(init.body instanceof FormData)) {
        headers.set("content-type", "application/json");
    }
    const res = await fetch(`${API_BASE}${path}`, { ...init, credentials: "include", headers });
    const text = await res.text();
    const data = text ? JSON.parse(text) : {};
    if (!res.ok) {
        const err = new Error(data?.error?.message || "요청 처리 중 문제가 발생했습니다.");
        err.code = data?.error?.code;
        err.status = res.status;
        throw err;
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
