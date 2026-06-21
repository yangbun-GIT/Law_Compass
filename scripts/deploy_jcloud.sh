#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${LAWCOMPASS_ENV_FILE:-.env}"
SKIP_BUILD="${SKIP_BUILD:-0}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"
IMPORT_KNIA="${IMPORT_KNIA:-0}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[lawcompass-jcloud] missing $ENV_FILE. The JCloud VM keeps real secrets in a server-local .env file." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[lawcompass-jcloud] docker is not installed or not on PATH." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[lawcompass-jcloud] Docker Compose V2 is required." >&2
  exit 1
fi

mkdir -p storage logs/gateway logs/agent logs/worker
chmod 700 storage logs || true

COMPOSE=(docker compose --env-file "$ENV_FILE" -f compose.yaml -f compose.jcloud.yaml)

echo "[lawcompass-jcloud] validating compose config"
"${COMPOSE[@]}" config >/dev/null

if [[ "$SKIP_BUILD" != "1" ]]; then
  echo "[lawcompass-jcloud] building images"
  "${COMPOSE[@]}" build
fi

echo "[lawcompass-jcloud] starting services"
"${COMPOSE[@]}" up -d

if [[ "$RUN_MIGRATIONS" == "1" ]]; then
  echo "[lawcompass-jcloud] applying database migrations"
  "${COMPOSE[@]}" --profile migrate run --rm db-migrate
fi

if [[ "$IMPORT_KNIA" == "1" ]]; then
  echo "[lawcompass-jcloud] importing structured KNIA JSON"
  "${COMPOSE[@]}" exec -T agent python scripts/import_knia_fault_ratio_json.py \
    --path /app/project_scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_review.json \
    --rebuild-embeddings
fi

echo "[lawcompass-jcloud] service status"
"${COMPOSE[@]}" ps

echo "[lawcompass-jcloud] checking local health endpoint"
if command -v curl >/dev/null 2>&1; then
  curl -fsS http://localhost:8080/health >/dev/null
  echo "[lawcompass-jcloud] /health OK"
else
  echo "[lawcompass-jcloud] curl not found; skipped HTTP health check"
fi
