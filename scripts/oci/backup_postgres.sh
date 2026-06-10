#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${LAWCOMPASS_ENV_FILE:-.env}"
BACKUP_DIR="${LAWCOMPASS_BACKUP_DIR:-backups}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[lawcompass-oci-backup] missing $ENV_FILE" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR" || true

COMPOSE=(docker compose --env-file "$ENV_FILE" -f compose.yaml -f compose.prod.yaml)
STAMP="$(date +%F_%H%M%S)"
OUT="$BACKUP_DIR/lawcompass_${STAMP}.sql.gz"

echo "[lawcompass-oci-backup] writing $OUT"
"${COMPOSE[@]}" exec -T postgres \
  sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  | gzip > "$OUT"

echo "[lawcompass-oci-backup] done: $OUT"
