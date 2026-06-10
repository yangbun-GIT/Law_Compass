const RAW_API_BASE = import.meta.env.VITE_API_BASE_URL || "";

function normalizeApiBase(value: string) {
  const trimmed = value.trim().replace(/\/+$/, "");
  if (!trimmed) return "";
  return trimmed.endsWith("/api/v1") ? trimmed.slice(0, -"/api/v1".length) : trimmed;
}

export const API_BASE = normalizeApiBase(RAW_API_BASE);

export function apiUrl(path: string) {
  return `${API_BASE}${path}`;
}
