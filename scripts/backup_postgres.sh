#!/usr/bin/env bash
# Backup diario de "stratos" via pg_dump formato custom (PARTE 14, RPO 24h).
#
# Corre CONTRA el contenedor `postgres` de docker-compose (docker compose
# exec, socket unix interno -- nunca abre una conexion TCP nueva ni toca
# .env: POSTGRES_USER/POSTGRES_DB ya estan en el entorno del propio
# contenedor, puestos ahi por docker-compose.yml). Retencion configurable
# via BACKUP_RETENTION_DAYS (.env.example, G9) -- nunca hardcodeada.
#
# Pensado para invocarse desde un cron/systemd timer en el Nodo B Linux
# (docs/runbook.md); este script solo hace el dump + rotacion, la
# programacion periodica es responsabilidad del scheduler del SO.
#
# Uso: BACKUP_DIR=/ruta/a/backups scripts/backup_postgres.sh

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="${BACKUP_DIR}/stratos_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

docker compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" --format=custom "$POSTGRES_DB"' > "${DEST}"

echo "Backup escrito: ${DEST} ($(du -h "${DEST}" | cut -f1))"

find "${BACKUP_DIR}" -name 'stratos_*.dump' -mtime "+${RETENTION_DAYS}" -delete

echo "Retencion aplicada: se conservan los backups de los ultimos ${RETENTION_DAYS} dias"
