export type User = {
  id: string;
  email: string;
  role: "user" | "admin";
  display_name: string;
};

export type AccidentFacts = {
  accident_type?: string;
  school_zone?: boolean;
  victim_is_child?: boolean;
  crosswalk_nearby?: boolean;
  opponent_signal_violation?: boolean;
  turn_signal?: boolean;
  side_collision?: boolean;
  signal_state?: string;
  lane_change?: boolean;
  intersection?: boolean;
  pedestrian?: boolean;
  stopped?: boolean;
  sudden_brake?: boolean;
  weather?: string;
  light_condition?: string;
  opponent_behavior?: string;
  injury?: boolean | null;
  injury_level?: string;
  damage_level?: string;
  lane_change_actor?: string;
  user_signal?: string;
  opponent_signal?: string;
  pedestrian_signal?: string;
  bicycle_location?: string;
  bicycle_direction?: string;
};

export type CaseItem = {
  id: string;
  title: string;
  description_text?: string;
  status: string;
  structured_facts?: AccidentFacts;
  selected_keywords?: string[];
  analysis_mode?: string;
  created_at: string;
};

export type UploadItem = {
  id: string;
  file_name: string;
  content_type: string;
  file_size_bytes: number;
  status: string;
  storage_provider?: string;
  metadata?: Record<string, any>;
  created_at: string;
};

const RAW_API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const API_BASE = RAW_API_BASE.endsWith("/api/v1") ? RAW_API_BASE.slice(0, -"/api/v1".length) : RAW_API_BASE;

export type ApiValidationIssue = {
  field: string;
  message: string;
  keyword?: string;
};

export type ApiError = Error & {
  code?: string;
  status?: number;
  traceId?: string;
  validation?: ApiValidationIssue[];
};

const FIELD_LABELS: Record<string, string> = {
  "body.email": "이메일",
  "body.password": "비밀번호",
  "body.display_name": "표시 이름",
  "body.title": "케이스 제목",
  "body.description_text": "사고 설명",
  "body.case_id": "케이스",
  "body.file_name": "파일 이름",
  "body.content_type": "파일 형식",
  "body.file_size_bytes": "파일 크기",
  "body.upload_id": "업로드"
};

function normalizeValidation(value: unknown): ApiValidationIssue[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const issues = value
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const raw = item as Record<string, unknown>;
      const field = typeof raw.field === "string" ? raw.field : "";
      const message = typeof raw.message === "string" ? raw.message : "";
      const keyword = typeof raw.keyword === "string" ? raw.keyword : undefined;
      if (!field || !message) return null;
      const issue: ApiValidationIssue = { field, message };
      if (keyword) issue.keyword = keyword;
      return issue;
    })
    .filter((item): item is ApiValidationIssue => item !== null);
  return issues.length ? issues : undefined;
}

function fieldLabel(field: string) {
  return FIELD_LABELS[field] || field.replace(/^body\./, "");
}

export function formatApiError(error: unknown, fallback = "요청 처리에 실패했습니다.") {
  const apiError = error as Partial<ApiError> | undefined;
  const message = typeof apiError?.message === "string" && apiError.message.trim() ? apiError.message : fallback;
  if (!apiError?.validation?.length) return message;
  const validationText = apiError.validation.map((issue) => `- ${fieldLabel(issue.field)}: ${issue.message}`).join("\n");
  return `${message}\n${validationText}`;
}

function makeApiError(message: string, code?: string, status?: number, traceId?: string, validation?: ApiValidationIssue[]) {
  const err = new Error(message) as ApiError;
  err.code = code;
  err.status = status;
  err.traceId = traceId;
  err.validation = validation;
  return err;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers || {});
  if (!headers.has("content-type") && init?.body && !(init.body instanceof FormData)) {
    headers.set("content-type", "application/json");
  }
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, credentials: "include", headers });
  } catch {
    throw makeApiError("서버에 연결하지 못했습니다. Docker Compose와 gateway/edge 실행 상태를 확인해 주세요.", "NETWORK_ERROR");
  }
  const text = await res.text();
  let data: any = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw makeApiError("서버 응답을 읽지 못했습니다. 잠시 후 다시 시도해 주세요.", "INVALID_JSON_RESPONSE", res.status);
  }
  if (!res.ok) {
    throw makeApiError(
      data?.error?.message || "요청 처리에 실패했습니다.",
      data?.error?.code,
      res.status,
      data?.error?.trace_id,
      normalizeValidation(data?.error?.details?.validation)
    );
  }
  return data as T;
}

function idempo() {
  return { "Idempotency-Key": crypto.randomUUID() };
}

export const api = {
  signup: (payload: { email: string; password: string; display_name: string }) =>
    request<{ user: User; trace_id: string }>("/api/v1/auth/signup", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
  login: (payload: { email: string; password: string }) =>
    request<{ access_token: string; user: User; trace_id: string }>("/api/v1/auth/login", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
  refresh: () => request<{ access_token: string; user: User; trace_id: string }>("/api/v1/auth/refresh", { method: "POST", headers: idempo() }),
  me: () => request<{ user: User; trace_id: string }>("/api/v1/auth/me"),
  logout: () => request<{ ok: boolean; trace_id: string }>("/api/v1/auth/logout", { method: "POST", headers: idempo() }),

  createCase: (payload: { title: string; description_text?: string; structured_facts?: AccidentFacts; selected_keywords?: string[]; analysis_mode?: string }) =>
    request<{ case: CaseItem; trace_id: string }>("/api/v1/cases", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
  updateCase: (caseId: string, payload: { title?: string; description_text?: string; structured_facts?: AccidentFacts; selected_keywords?: string[]; analysis_mode?: string }) =>
    request<{ case: CaseItem; trace_id: string }>(`/api/v1/cases/${caseId}`, { method: "PATCH", body: JSON.stringify(payload), headers: idempo() }),
  listCases: () => request<{ items: CaseItem[]; trace_id: string }>("/api/v1/cases"),
  getCase: (caseId: string) => request<{ case: CaseItem; trace_id: string }>(`/api/v1/cases/${caseId}`),

  localUpload: async (caseId: string, file: File) => {
    const form = new FormData();
    form.append("case_id", caseId);
    form.append("file", file);
    return request<{ upload_id: string; status: string; trace_id: string }>("/api/v1/uploads/local", { method: "POST", body: form, headers: idempo() });
  },
  completeUpload: (upload_id: string) =>
    request<{ upload_id: string; job_id: string; status: string; trace_id: string }>("/api/v1/uploads/complete", { method: "POST", body: JSON.stringify({ upload_id }), headers: idempo() }),
  getUpload: (uploadId: string) => request<{ upload: UploadItem; trace_id: string }>(`/api/v1/uploads/${uploadId}`),
  getCaseUploads: (caseId: string) => request<{ items: UploadItem[]; trace_id: string }>(`/api/v1/cases/${caseId}/uploads`),
  getViewUrl: (uploadId: string) => request<{ view_url: string; expires_in_sec: number }>(`/api/v1/uploads/${uploadId}/view-url`),
  getDownloadUrl: (uploadId: string) => request<{ download_url: string; expires_in_sec: number }>(`/api/v1/uploads/${uploadId}/download-url`),

  analyzeText: (caseId: string, payload: { description_text: string; structured_facts?: AccidentFacts; selected_keywords?: string[]; analysis_mode?: string; ai_profile?: string; specialist_roles?: string[] }) =>
    request<any>(`/api/v1/cases/${caseId}/analyze-text`, { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
  reanalyzeText: (caseId: string, payload: { description_text?: string; structured_facts?: AccidentFacts; selected_keywords?: string[]; analysis_mode?: string; ai_profile?: string; specialist_roles?: string[] }) =>
    request<any>(`/api/v1/cases/${caseId}/reanalyze`, { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
  analyzeVideo: (caseId: string, payload: { upload_id: string; structured_facts?: AccidentFacts; selected_keywords?: string[]; analysis_mode?: string; specialist_roles?: string[] }) =>
    request<any>(`/api/v1/cases/${caseId}/analyze-video`, { method: "POST", body: JSON.stringify(payload), headers: idempo() }),

  getJobs: (caseId: string) => request<{ items: any[]; trace_id: string }>(`/api/v1/cases/${caseId}/jobs`),
  getResult: (caseId: string) => request<{ result: any; report: any; trace_id: string }>(`/api/v1/cases/${caseId}/result`),
  getReport: (caseId: string) => request<{ report: any; trace_id: string }>(`/api/v1/cases/${caseId}/report`),
  getEasyReport: (caseId: string) => request<any>(`/api/v1/cases/${caseId}/easy-report`),
  getEvidence: (caseId: string) => request<{ evidence: any[]; trace_id: string }>(`/api/v1/cases/${caseId}/evidence`),
  getEvidenceChunk: (chunkId: string) => request<{ chunk: any; trace_id: string }>(`/api/v1/legal/evidence/${chunkId}`),

  adminLegalIngest: () => request<any>("/api/v1/admin/legal/ingest", { method: "POST", headers: idempo() }),
  adminRebuildLegalEmbeddings: () => request<any>("/api/v1/admin/legal/rebuild-embeddings", { method: "POST", headers: idempo() }),
  adminLegalRetrievalTest: (q: string) => request<any>(`/api/v1/admin/legal/retrieval-test?q=${encodeURIComponent(q)}`),

  getKniaRanking: (limit = 20, accidentPartyType = "all", q = "") => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (accidentPartyType && accidentPartyType !== "all") params.set("accidentPartyType", accidentPartyType);
    if (q) params.set("q", q);
    return request<any>(`/api/v1/knia/ranking?${params.toString()}`);
  },
  getKniaChart: (chartNo: string, chartType = "1") => request<any>(`/api/v1/knia/charts/${encodeURIComponent(chartNo)}?chartType=${encodeURIComponent(chartType)}`),
  getKniaChartAdjustments: (chartNo: string, chartType = "1") => request<any>(`/api/v1/knia/charts/${encodeURIComponent(chartNo)}/adjustments?chartType=${encodeURIComponent(chartType)}`),
  getKniaChartReferences: (chartNo: string, chartType = "1") => request<any>(`/api/v1/knia/charts/${encodeURIComponent(chartNo)}/references?chartType=${encodeURIComponent(chartType)}`),
  estimateKniaFault: (payload: any) =>
    request<any>("/api/v1/knia/fault/estimate", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
  matchKniaChart: (payload: { description_text: string; structured_facts?: AccidentFacts; selected_keywords?: string[]; accident_party_type?: string }) =>
    request<any>("/api/v1/knia/match", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
  adminCollectKnia: (payload: { menu?: boolean; ranking?: boolean; charts?: boolean; chart_nos?: string[]; max_charts?: number } = {}) =>
    request<any>("/api/v1/admin/knia/collect", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
  adminCollectKniaRankingDetails: (payload: { limit?: number | null; force?: boolean } = {}) =>
    request<any>("/api/v1/admin/knia/collect-ranking-details", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
  adminRebuildKniaEmbeddings: (limit = 1000) =>
    request<any>("/api/v1/admin/knia/rebuild-embeddings", { method: "POST", body: JSON.stringify({ limit }), headers: idempo() }),

  getKniaMyAccidentPages: () => request<any>("/api/v1/knia/myaccident-pages"),
  getKniaMyAccidentTree: (myaccidentNo: number) => request<any>(`/api/v1/knia/myaccident/${myaccidentNo}/tree`),
  searchKniaJson: (q: string, accidentPartyType = "", limit = 5) => {
    const params = new URLSearchParams({ q, limit: String(limit) });
    if (accidentPartyType && accidentPartyType !== "all") params.set("accidentPartyType", accidentPartyType);
    return request<any>(`/api/v1/knia/json/search?${params.toString()}`);
  },
  searchKniaMedia: (q: string, accidentPartyType = "") => {
    const params = new URLSearchParams({ q });
    if (accidentPartyType && accidentPartyType !== "all") params.set("accidentPartyType", accidentPartyType);
    return request<any>(`/api/v1/knia/media/search?${params.toString()}`);
  },
  adminImportKniaJson: (payload: { path?: string; force?: boolean; rebuild_embeddings?: boolean } = {}) =>
    request<any>("/api/v1/admin/knia/import-json", { method: "POST", body: JSON.stringify(payload), headers: idempo() }),
  adminRebuildKniaJsonEmbeddings: (payload: { force?: boolean; limit?: number | null } = {}) =>
    request<any>("/api/v1/admin/knia/json/rebuild-embeddings", { method: "POST", body: JSON.stringify(payload), headers: idempo() })
};
