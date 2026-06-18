import { createHash } from "node:crypto";

function sortForStableJson(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortForStableJson);
  if (!value || typeof value !== "object") return value;
  const record = value as Record<string, unknown>;
  return Object.keys(record)
    .sort()
    .reduce<Record<string, unknown>>((acc, key) => {
      acc[key] = sortForStableJson(record[key]);
      return acc;
    }, {});
}

export function stableJson(value: unknown): string {
  return JSON.stringify(sortForStableJson(value));
}

export function redisCacheKey(namespace: string, value: unknown): string {
  const digest = createHash("sha256").update(stableJson(value)).digest("hex").slice(0, 32);
  return `${namespace}:${digest}`;
}

export async function getCachedJson<T = any>(redis: any, key: string): Promise<T | null> {
  if (!redis) return null;
  try {
    const raw = await redis.get(key);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export async function setCachedJson(redis: any, key: string, value: unknown, ttlSeconds: number): Promise<void> {
  if (!redis || ttlSeconds <= 0) return;
  try {
    await redis.setex(key, ttlSeconds, JSON.stringify(value));
  } catch {
    // Cache failures must not block the user-facing request path.
  }
}

export function stripTraceId<T extends Record<string, unknown>>(payload: T): Omit<T, "trace_id"> {
  const { trace_id: _traceId, ...rest } = payload;
  return rest;
}
