export const env = {
  port: Number(process.env.PORT ?? 3000),
  apiPrefix: process.env.API_PREFIX ?? "/api/v1",
  dbUrl: process.env.DATABASE_URL ?? "",
  redisUrl: process.env.REDIS_URL ?? "",
  jwtAccessSecret: process.env.JWT_ACCESS_SECRET ?? "access",
  jwtRefreshSecret: process.env.JWT_REFRESH_SECRET ?? "refresh",
  jwtAccessTtlSec: Number(process.env.JWT_ACCESS_TTL_SEC ?? 900),
  jwtRefreshTtlSec: Number(process.env.JWT_REFRESH_TTL_SEC ?? 1209600),
  agentUrl: process.env.INTERNAL_AGENT_URL ?? "http://agent:8000",
  internalToken: process.env.INTERNAL_SERVICE_TOKEN ?? "token",
  adminToken: process.env.INTERNAL_ADMIN_TOKEN ?? "",
  timeoutMs: Number(process.env.REQUEST_TIMEOUT_MS ?? 4000),
  analyzeTimeoutMs: Number(process.env.ANALYZE_TIMEOUT_MS ?? 25000),
  retryCount: Number(process.env.RETRY_COUNT ?? 2),
  localViewExpires: Number(process.env.LOCAL_VIEW_URL_EXPIRES_SEC ?? 120),
  localDownloadExpires: Number(process.env.LOCAL_DOWNLOAD_URL_EXPIRES_SEC ?? 60),
  storageRoot: process.env.LOCAL_STORAGE_ROOT ?? "/app/storage"
};

export const cookieSecure = (process.env.NODE_ENV ?? "development") === "production";
