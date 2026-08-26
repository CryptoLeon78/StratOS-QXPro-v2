# Estado de fase — StratOS-QXPro

> Se actualiza SIEMPRE al cerrar trabajo (regla de continuidad entre sesiones). Al abrir sesión, leer esto + `CLAUDE.md` + `ASSUMPTIONS.md` antes de proponer nada.

## Fase actual: G5 — Servicios, jobs ARQ, API 9.2, WS, Telegram, Prometheus

**Estado**: **verificado localmente, sin pushear (45 commits por delante de `origin/main`), CI sin ejecutar en esta sesión** — la decisión de hacer `git push` (acción visible/compartida) se deja al operador, no se ha hecho de forma autónoma.

### Verde (verificado con comandos reales en esta sesión)
- **Suite completa de `core-engine`: 440 tests, 98% de cobertura agregada (3624 statements, 85 sin cubrir)**. Por paquete/módulo nuevo de G5: `auth/` (JWT completo, hash/verify, login+refresh) · 14 servicios de dominio (`watchdog`, `correlations`, `montecarlo`, `risk`, `audit`, `impulses`, `ums`, `withdrawals`, `checklists`, `config_drift`, `staging`/SIZING_CAP, `pipeline_gate`, `semaphore_sweep`, `killswitch_sweep`) al 91-100% (los huecos son ramas de error/edge no alcanzadas por los escenarios de test actuales, no código sin probar en el camino principal) · `jobs/` (ARQ `tasks.py`+`worker.py`+`scheduler.py`) · `notifications/` (Telegram + dispatch) al 100% · `metrics.py` (Prometheus) al 100% · 16 routers de la API 9.2 al 95-100% · `ws/` (bridge/auth al 100%, `router.py` al 53-74% — ver caveat abajo).
- **Caveat de cobertura real, no resuelto esta sesión**: `ws/router.py` mide 53% en la suite completa (74% en aislamiento) pese a que sus 4 endpoints SÍ se ejercitan en `tests/ws/test_router.py` (incluido el gauge `ws_connections_active` de Prometheus) — los tests WS end-to-end usan `fastapi.testclient.TestClient` + `redis` síncrono en un hilo separado (para evitar el mismatch de event loop entre pytest-asyncio y el WS real), y `coverage.py` no sigue la ejecución a través de ese hilo sin configuración adicional (misma familia de problema que `concurrency=["greenlet"]` en G4-10, pero no investigado a fondo aquí). No es código sin probar — es un déficit de instrumentación de medición.
- **Criterio de salida literal de G5 cumplido**: auth (login/refresh/401 sin token, `tests/auth/`) · validaciones (Pydantic strict en los 7 payloads de ingesta, ya de G4, más los DTOs nuevos de la API 9.2) · 409 cementerio (`tests/routers/test_cemetery.py::test_always_returns_409`) · SIZING_CAP (`tests/services/test_staging.py::test_sizing_cap_blocks_escalation_above_89_percent`) · deriva EA modo incorrecto (`tests/services/test_config_drift.py::test_mode_drift_creates_critica_alert`) · posición sin SL + Telegram <60s, hueco real encontrado y cerrado en el cierre de fase (`tests/e2e/test_g5_exit_criteria.py`, ver ASSUMPTIONS G5-03).
- **OpenAPI sin warnings**: `app.openapi()` genera sin ningún `Warning` de Python, 55 operaciones sin `operationId` duplicado, los 18 routers con `tags` (`tests/test_openapi.py`).
- **`scan_hardcoding` limpio o justificado**: 207 hallazgos sobre el repo completo, todos categorizados (ASSUMPTIONS G5-01/02, mayoría heredada de G0-G4 ya justificada) — 2 hallazgos reales de G5 corregidos (no solo justificados), ver G5-02.
- `ruff check` + `ruff format --check` + `mypy --strict` limpios en `core-engine/` completo (96 ficheros de `src/`).

### Diseño propio documentado en ASSUMPTIONS (G5-00 a G5-14)
Puntos más significativos: alcance de G5 confinado a `core-engine` (api-gateway sigue placeholder, G5-00) · tabla de staging `checklist_item_signature` + `ums_phase_log.signed_by` aprobadas por el operador (G5-05) · migración correctiva `sizing_current_pct NUMERIC(4,2)→NUMERIC(5,2)` (inconsistencia real de PARTE 5.2, G5-06) · refresh JWT stateless sin revocación (G5-07) · VaR/CVaR escalado por raíz del tiempo + `compute_exposure()` sin conversión de divisa (G5-08) · cadencias de los 10 cron jobs son diseño propio salvo correlaciones/MC (G5-09) · el hueco real de Telegram en `/ingest/positions` (G5-03, cerrado en este cierre de fase).

### Pendiente — depende del operador, no de más trabajo de agente
- Decidir si hacer `git push` de los 45 commits acumulados (G5 completo) y, tras eso, confirmar CI verde en GitHub Actions — no se ha intentado en esta sesión.
- Investigar el déficit de cobertura de `ws/router.py` (thread-based TestClient no trackeado por `coverage.py`) si en algún momento hace falta un número de cobertura real para ese módulo, no solo saber que sí está probado funcionalmente.
- Revisar los 5 gaps de negocio anotados en `docs/backlog.md` durante G5 (chips de Salud sin fórmula, `r_multiple` nunca poblado, sin equity/Sharpe por bot, `ea_state` sin sizing, exposición sin conversión de divisa) antes de que G6/G7 (frontend) los necesiten de verdad.
- `ums_max_dd_gate_pct=8` (ASSUMPTIONS previo, aún sin confirmar por el operador) sigue gobernando el downgrade automático de UMS (`services/ums.py`) — mismo estado que al sembrarse, no resuelto en G5.

## Fases cerradas

### G4 — mt5-connector + mt5-simulador + ingesta real (cerrada)
5 paquetes nuevos/tocados, 299 tests, 100% en 3 de ellos (`core-engine/ingest/` 213 statements, `shared-ingest-seal` 17, `mt5-simulator` 97) · `mt5-connector` 94% (371 statements, 100% salvo `real_adapter.py`/`main.py`, no verificables sin Windows+MT5 real) · criterio de salida (corte de red, cero pérdidas/duplicados) probado contra Postgres real. CI: run [`32986481038`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/32986481038) falló por congestión de runners de GitHub (jobs nunca llegaron a `queued`→ejecutar), no por el código — nunca se confirmó CI verde para G4 antes de que G5 empezara. Detalle en `ASSUMPTIONS.md` G4-01 a G4-21.

### G3 — Máquinas de estado (cerrada)
3 máquinas de estado (semáforo/kill-switch/pipeline+challenger), 100% cobertura (357/357 statements, 66/66 tests), CI verde 3/3 (run [`32956020786`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/32956020786)). Detalle en `ASSUMPTIONS.md` G3-01 a G3-06.

### G2 — Fórmulas (cerrada)
20 fórmulas de PARTE 8, 100% cobertura (217/217 statements, 87/87 tests), CI verde 3/3 (run [`32939959347`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/32939959347)). Detalle en `ASSUMPTIONS.md` G2-01 a G2-07.

### G1 — Modelo de datos (cerrada)
25/25 tablas de PARTE 5.2, migraciones Alembic 0001/0002, rol `stratos_app` con grants exactos, 16/16 tests contra Postgres/TimescaleDB real. Detalle en `ASSUMPTIONS.md` G1-01 a G1-14 y el historial de commits.

### G0 — Scaffold + tooling de gobierno (cerrada)
Repo git independiente en `https://github.com/CryptoLeon78/StratOS-QXPro-v2` (privado), `.mcp.json` operativo, `docker compose up -d postgres redis` healthy, CI verde, `config/thresholds.seed.json` (61 claves), scaffolds de `core-engine`/`api-gateway`/`frontend`. Detalle en `ASSUMPTIONS.md` G0-01 a G0-14.

## Fases futuras (PARTE 12)
G6 Frontend shell + Resumen · G7 Frontend resto de pestañas · G8 Seed + E2E · G9 Hardening.
