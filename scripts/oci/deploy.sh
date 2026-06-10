#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${LAWCOMPASS_ENV_FILE:-.env}"
export LAWCOMPASS_ENV_FILE="$ENV_FILE"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"
IMPORT_KNIA="${IMPORT_KNIA:-1}"
SKIP_BUILD="${SKIP_BUILD:-0}"
ALLOW_REMOTE_STORAGE="${LAWCOMPASS_ALLOW_REMOTE_STORAGE:-0}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[lawcompass-oci] missing $ENV_FILE. Copy env.oci.example to .env and fill server-local values." >&2
  exit 1
fi

if awk 'BEGIN { found=0 } /^[[:space:]]*#/ || /^[[:space:]]*$/ { next } /<[^>]+>/ { print FNR ":" $0; found=1 } END { exit found ? 0 : 1 }' "$ENV_FILE" >/tmp/lawcompass-env-placeholders.txt; then
  echo "[lawcompass-oci] unresolved placeholder values remain in $ENV_FILE:" >&2
  cat /tmp/lawcompass-env-placeholders.txt >&2
  echo "[lawcompass-oci] replace placeholders with server-local values or empty strings before deployment." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[lawcompass-oci] docker is not installed or not on PATH." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[lawcompass-oci] Docker Compose V2 is required." >&2
  exit 1
fi

if [[ "$ALLOW_REMOTE_STORAGE" != "1" ]]; then
  if ! grep -Eq '^STORAGE_DRIVER=local$' "$ENV_FILE"; then
    echo "[lawcompass-oci] OCI single-VM deployment expects STORAGE_DRIVER=local." >&2
    echo "[lawcompass-oci] Set LAWCOMPASS_ALLOW_REMOTE_STORAGE=1 only if you intentionally configured NAS/S3." >&2
    exit 1
  fi
fi

mkdir -p storage logs/gateway logs/agent logs/worker backups
chmod 700 storage logs backups || true

COMPOSE=(docker compose --env-file "$ENV_FILE" -f compose.yaml -f compose.prod.yaml)

echo "[lawcompass-oci] validating compose config"
"${COMPOSE[@]}" config >/dev/null

if [[ "$SKIP_BUILD" != "1" ]]; then
  echo "[lawcompass-oci] building images"
  "${COMPOSE[@]}" build
fi

echo "[lawcompass-oci] starting services"
"${COMPOSE[@]}" up -d

if [[ "$RUN_MIGRATIONS" == "1" ]]; then
  echo "[lawcompass-oci] applying database migrations"
  "${COMPOSE[@]}" --profile migrate run --rm db-migrate
fi

if [[ "$IMPORT_KNIA" == "1" ]]; then
  echo "[lawcompass-oci] importing structured KNIA JSON if available"
  "${COMPOSE[@]}" exec -T agent python scripts/import_knia_fault_ratio_json.py \
    --path /app/project_scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_review.json \
    --rebuild-embeddings
fi

echo "[lawcompass-oci] service status"
"${COMPOSE[@]}" ps

echo "[lawcompass-oci] checking local health endpoint"
if command -v curl >/dev/null 2>&1; then
  curl -fsS http://localhost/health >/dev/null
  echo "[lawcompass-oci] /health OK"
else
  echo "[lawcompass-oci] curl not found; skipped HTTP health check"
fi
