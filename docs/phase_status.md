# Estado de fase — StratOS-QXPro

> Se actualiza SIEMPRE al cerrar trabajo (regla de continuidad entre sesiones). Al abrir sesión, leer esto + `CLAUDE.md` + `ASSUMPTIONS.md` antes de proponer nada.

## Fase actual: G1 — Modelo de datos

**Estado**: **cerrada por completo**. Los 3 criterios de salida de PARTE 12 verificados con ejecución real contra Postgres/TimescaleDB (no mockeado) y con CI en GitHub Actions verde (3/3 jobs — run [`32934145617`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions)).

### Verde (verificado con comandos reales en esta sesión)
- 25/25 tablas de PARTE 5.2 en el modelo SQLAlchemy (`core-engine/src/core/db/models/`, 5 módulos temáticos) + 15 enums + registro compartido de tipos `Enum`/`Numeric`.
- Migración Alembic `0001` (25 tablas + 3 hypertables + compresión/retención + continuous aggregate `equity_daily` + rol `stratos_app` con grants exactos: SELECT/INSERT/UPDATE/DELETE en mutables, solo SELECT/INSERT en las 6 inmutables) y `0002` (fix de precisión `sizing_current_pct`). Roundtrip `upgrade → downgrade → upgrade` verificado limpio, incluso con `stratos_test` ya montada.
- 16/16 tests verdes contra `stratos_test` real: `test_migration.py` (catálogo de Postgres/Timescale), `test_immutability_permissions.py` (las 6 inmutables + control negativo), `test_ingest_batch_seal.py` (sello sha256, NOT NULL real).
- `ruff check` + `ruff format --check` + `mypy --strict` limpios (verificado sin caché tras el hallazgo de G1-14). `scan_hardcoding`: 15 hallazgos, todos falsos positivos de categorías ya documentadas (G1-01/02/03).
- `docker-compose.yml`/`.env.example` ampliados con `APP_DATABASE_URL`/`APP_DB_PASSWORD` (rol de aplicación). `ci.yml` ampliado con las 4 vars nuevas que `Settings` exige.

### 7 bugs reales encontrados y corregidos en esta sesión (detalle en ASSUMPTIONS G1-05 a G1-14)
Postgres no acepta bind params en DDL (`CREATE ROLE`) · `op.drop_table` no limpia tipos ENUM · `CREATE ROLE` no era idempotente entre bases del mismo cluster · `Settings.env_file` relativo rompía con `cwd=core-engine/` · fixture de tests necesitaba subproceso para Alembic (no la API Python, por el `lru_cache` de `get_settings`) · `PARTE 5.2` tiene una inconsistencia real (`NUMERIC(4,2) DEFAULT 100.0` desborda) · `DROP ROLE` en downgrade rompía con una segunda base en el cluster · `tests/` necesitaba `__init__.py` para que `pytest` (ejecutable a secas, como lo invoca CI) resolviera imports · caché de `ruff` desactualizada tras cambiar límites de paquete.

### Pendiente — depende del operador, no de más trabajo de agente
- Revisar los defaults inventados en `ASSUMPTIONS.md` (G0-05 a G0-08: Page-Hinkley, UMS min months/Sharpe; G1-05/06/07 password del rol de aplicación si se necesita rotación real en producción) antes de que G2/G3 los consuman en serio.

## Fases cerradas

### G0 — Scaffold + tooling de gobierno (cerrada)
Repo git independiente en `https://github.com/CryptoLeon78/StratOS-QXPro-v2` (privado), `.mcp.json` operativo (registrado también en el raíz de `SQX_144_Full2`), `docker compose up -d postgres redis` healthy, CI verde, `config/thresholds.seed.json` (61 claves), scaffolds de `core-engine`/`api-gateway`/`frontend`. Detalle completo en el historial de commits y `ASSUMPTIONS.md` G0-01 a G0-14.

## Fases futuras (PARTE 12)
G2 Fórmulas (TDD) · G3 Máquinas de estado · G4 mt5-connector + simulador · G5 core-engine (servicios/API/WS) · G6 Frontend shell + Resumen · G7 Frontend resto de pestañas · G8 Seed + E2E · G9 Hardening.
