const isProduction = (process.env.NODE_ENV ?? "development") === "production";

function readEnv(name: string, fallback = "") {
  const value = process.env[name]?.trim();
  return value || fallback;
}

function readProductionSecret(name: string, devFallback: string) {
  const value = readEnv(name);
  if (isProduction && (!value || value === devFallback || value.length < 32 || /^<[^>]+>$/.test(value))) {
    throw new Error(`${name} must be set to a strong non-placeholder value in production`);
  }
  return value || devFallback;
}

function readCorsOrigins() {
  return readEnv("CORS_ORIGINS")
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);
}

function readCookieSameSite(): "lax" | "strict" | "none" {
  const value = readEnv("COOKIE_SAME_SITE", "lax").toLowerCase();
  return value === "strict" || value === "none" ? value : "lax";
}

export const env = {
  port: Number(process.env.PORT ?? 3000),
  apiPrefix: process.env.API_PREFIX ?? "/api/v1",
  dbUrl: process.env.DATABASE_URL ?? "",
  redisUrl: process.env.REDIS_URL ?? "",
  jwtAccessSecret: readProductionSecret("JWT_ACCESS_SECRET", "access"),
  jwtRefreshSecret: readProductionSecret("JWT_REFRESH_SECRET", "refresh"),
  jwtAccessTtlSec: Number(process.env.JWT_ACCESS_TTL_SEC ?? 900),
  jwtRefreshTtlSec: Number(process.env.JWT_REFRESH_TTL_SEC ?? 1209600),
  agentUrl: process.env.INTERNAL_AGENT_URL ?? "http://agent:8000",
  internalToken: readProductionSecret("INTERNAL_SERVICE_TOKEN", "token"),
  adminToken: process.env.INTERNAL_ADMIN_TOKEN ?? "",
  corsOrigins: readCorsOrigins(),
  cookieSameSite: readCookieSameSite(),
  timeoutMs: Number(process.env.REQUEST_TIMEOUT_MS ?? 4000),
  analyzeTimeoutMs: Number(process.env.ANALYZE_TIMEOUT_MS ?? 25000),
  retryCount: Number(process.env.RETRY_COUNT ?? 2),
  localViewExpires: Number(process.env.LOCAL_VIEW_URL_EXPIRES_SEC ?? 120),
  localDownloadExpires: Number(process.env.LOCAL_DOWNLOAD_URL_EXPIRES_SEC ?? 60),
  storageRoot: process.env.LOCAL_STORAGE_ROOT ?? "/app/storage",
  storageDriver: process.env.STORAGE_DRIVER ?? process.env.STORAGE_PROVIDER ?? "local",
  maxUploadMb: Number(process.env.MAX_UPLOAD_MB ?? 500)
};

export const cookieSecure = isProduction;
