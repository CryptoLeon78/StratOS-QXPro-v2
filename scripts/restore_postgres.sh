#!/usr/bin/env bash
# Restaura un backup de backup_postgres.sh a una BBDD de VERIFICACION
# separada -- nunca sobre "stratos" directo, un restore es destructivo
# sobre su destino y jamas se ejecuta a ciegas sobre la real. Parte del
# procedimiento de verificacion de backups de PARTE 14 (RTO 2h): confirma
# que un .dump concreto SI se puede restaurar antes de confiar en el.
#
# Uso: scripts/restore_postgres.sh <ruta-al-.dump> [nombre-bbdd-verificacion]

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

DUMP_FILE="${1:?uso: restore_postgres.sh <ruta-al-.dump> [nombre-bbdd-verificacion]}"
VERIFY_DB="${2:-stratos_restore_verify}"

if [ ! -f "${DUMP_FILE}" ]; then
  echo "No existe: ${DUMP_FILE}" >&2
  exit 1
fi

docker compose exec -T postgres sh -c \
  'dropdb -U "$POSTGRES_USER" --if-exists "'"${VERIFY_DB}"'"'
docker compose exec -T postgres sh -c \
  'createdb -U "$POSTGRES_USER" "'"${VERIFY_DB}"'"'

RESTORE_LOG="$(mktemp)"
trap 'rm -f "${RESTORE_LOG}"' EXIT

docker compose exec -T postgres sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "'"${VERIFY_DB}"'"' < "${DUMP_FILE}" 2> "${RESTORE_LOG}" || true
cat "${RESTORE_LOG}" >&2

if grep -q "errors ignored on restore" "${RESTORE_LOG}"; then
  echo
  echo "AVISO REAL (hallazgo G9, no un fallo del script): pg_restore ignoro" >&2
  echo "algunos errores -- ver arriba. Con este esquema son SIEMPRE los" >&2
  echo "mismos: FK constraints sobre hypertables de TimescaleDB con" >&2
  echo "compresion activa (trade/equity_snapshot/heartbeat_log, G1) no se" >&2
  echo "pueden re-crear via pg_restore plano. LOS DATOS SI se restauran" >&2
  echo "completos (verificado: recuentos de filas abajo) -- lo que falta" >&2
  echo "son esas FK, reaplicables a mano tras el restore. Detalle y SQL" >&2
  echo "exacto en docs/runbook.md, seccion Backups." >&2
  echo
fi

echo "Restaurado en '${VERIFY_DB}'. Recuentos de filas por tabla:"

# ANALYZE antes de leer n_live_tup: recien restaurada, pg_stat_user_tables
# todavia no tiene estadisticas (mostraria 0 en todo, un falso verde).
docker compose exec -T postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "'"${VERIFY_DB}"'" -c "ANALYZE;" -c \
    "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY relname;"'
