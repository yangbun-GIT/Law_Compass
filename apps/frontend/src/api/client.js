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
        throw makeApiError(data?.error?.message || "요청 처리에 실패했습니다.", data?.error?.code, res.status, data?.error?.trace_id);
    }
    return data;
}
function idempo() {
    return { "Idempotency-Key": crypto.randomUUID() };
}
export const api = {
    signup: (payload) => request("/api/v1/auth/signup", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
    login: (payload) => request("/api/v1/auth/login", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
    refresh: () => request("/api/v1/auth/refresh", { method: "POST", headers: idempo() }),
    me: () => request("/api/v1/auth/me"),
    logout: () => request("/api/v1/auth/logout", { method: "POST", headers: idempo() }),
    createCase: (payload) => request("/api/v1/cases", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
    updateCase: (caseId, payload) => request(`/api/v1/cases/${caseId}`, { method: "PATCH", body: JSON.stringify(payload), headers: idempo() }),
    listCases: () => request("/api/v1/cases"),
    getCase: (caseId) => request(`/api/v1/cases/${caseId}`),
    localUpload: async (caseId, file) => {
        const form = new FormData();
        form.append("case_id", caseId);
        form.append("file", file);
        return request("/api/v1/uploads/local", { method: "POST", body: form, headers: idempo() });
    },
    completeUpload: (upload_id) => request("/api/v1/uploads/complete", { method: "POST", body: JSON.stringify({ upload_id }), headers: idempo() }),
    getUpload: (uploadId) => request(`/api/v1/uploads/${uploadId}`),
    getCaseUploads: (caseId) => request(`/api/v1/cases/${caseId}/uploads`),
    getViewUrl: (uploadId) => request(`/api/v1/uploads/${uploadId}/view-url`),
    getDownloadUrl: (uploadId) => request(`/api/v1/uploads/${uploadId}/download-url`),
    analyzeText: (caseId, payload) => request(`/api/v1/cases/${caseId}/analyze-text`, { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
    analyzeVideo: (caseId, payload) => request(`/api/v1/cases/${caseId}/analyze-video`, { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
    getJobs: (caseId) => request(`/api/v1/cases/${caseId}/jobs`),
    getResult: (caseId) => request(`/api/v1/cases/${caseId}/result`),
    getReport: (caseId) => request(`/api/v1/cases/${caseId}/report`),
    getEasyReport: (caseId) => request(`/api/v1/cases/${caseId}/easy-report`),
    getEvidence: (caseId) => request(`/api/v1/cases/${caseId}/evidence`),
    getEvidenceChunk: (chunkId) => request(`/api/v1/legal/evidence/${chunkId}`),
    adminLegalIngest: () => request("/api/v1/admin/legal/ingest", { method: "POST", headers: idempo() }),
    adminRebuildLegalEmbeddings: () => request("/api/v1/admin/legal/rebuild-embeddings", { method: "POST", headers: idempo() }),
    adminLegalRetrievalTest: (q) => request(`/api/v1/admin/legal/retrieval-test?q=${encodeURIComponent(q)}`),
    getKniaRanking: (limit = 20, accidentPartyType = "all", q = "") => {
        const params = new URLSearchParams({ limit: String(limit) });
        if (accidentPartyType && accidentPartyType !== "all")
            params.set("accidentPartyType", accidentPartyType);
        if (q)
            params.set("q", q);
        return request(`/api/v1/knia/ranking?${params.toString()}`);
    },
    getKniaChart: (chartNo, chartType = "1") => request(`/api/v1/knia/charts/${encodeURIComponent(chartNo)}?chartType=${encodeURIComponent(chartType)}`),
    getKniaChartAdjustments: (chartNo, chartType = "1") => request(`/api/v1/knia/charts/${encodeURIComponent(chartNo)}/adjustments?chartType=${encodeURIComponent(chartType)}`),
    getKniaChartReferences: (chartNo, chartType = "1") => request(`/api/v1/knia/charts/${encodeURIComponent(chartNo)}/references?chartType=${encodeURIComponent(chartType)}`),
    estimateKniaFault: (payload) => request("/api/v1/knia/fault/estimate", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
    matchKniaChart: (payload) => request("/api/v1/knia/match", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
    adminCollectKnia: (payload = {}) => request("/api/v1/admin/knia/collect", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
    adminCollectKniaRankingDetails: (payload = {}) => request("/api/v1/admin/knia/collect-ranking-details", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
    adminRebuildKniaEmbeddings: (limit = 1000) => request("/api/v1/admin/knia/rebuild-embeddings", { method: "POST", body: JSON.stringify({ limit }), headers: idempo() }),
    getKniaMyAccidentPages: () => request("/api/v1/knia/myaccident-pages"),
    getKniaMyAccidentTree: (myaccidentNo) => request(`/api/v1/knia/myaccident/${myaccidentNo}/tree`),
    searchKniaJson: (q, accidentPartyType = "", limit = 5) => {
        const params = new URLSearchParams({ q, limit: String(limit) });
        if (accidentPartyType && accidentPartyType !== "all")
            params.set("accidentPartyType", accidentPartyType);
        return request(`/api/v1/knia/json/search?${params.toString()}`);
    },
    searchKniaMedia: (q, accidentPartyType = "") => {
        const params = new URLSearchParams({ q });
        if (accidentPartyType && accidentPartyType !== "all")
            params.set("accidentPartyType", accidentPartyType);
        return request(`/api/v1/knia/media/search?${params.toString()}`);
    },
    adminImportKniaJson: (payload = {}) => request("/api/v1/admin/knia/import-json", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
    adminRebuildKniaJsonEmbeddings: (payload = {}) => request("/api/v1/admin/knia/json/rebuild-embeddings", { method: "POST", body: JSON.stringify(payload), headers: idempo() })
};
