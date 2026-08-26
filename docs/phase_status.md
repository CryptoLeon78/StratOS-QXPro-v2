# Estado de fase — StratOS-QXPro

> Se actualiza SIEMPRE al cerrar trabajo (regla de continuidad entre sesiones). Al abrir sesión, leer esto + `CLAUDE.md` + `ASSUMPTIONS.md` antes de proponer nada.

## Fase actual: G6 — Frontend shell + Resumen

**Estado**: sin empezar. Plan en curso con el operador (plan mode) tras cerrar G5.

## Fases cerradas

### G5 — Servicios, jobs ARQ, API 9.2, WS, Telegram, Prometheus (cerrada, CI verde 7/7)
Auth JWT completo (login/refresh/401 sin token) · 14 servicios de dominio (`watchdog`, `correlations`, `montecarlo`, `risk`, `audit`, `impulses`, `ums`, `withdrawals`, `checklists`, `config_drift`, `staging`/SIZING_CAP, `pipeline_gate`, `semaphore_sweep`, `killswitch_sweep`) · ARQ (10 cron jobs, `tasks.py`+`worker.py`+`scheduler.py`) · API 9.2 (16 routers) · WS (4 endpoints) · Telegram + Prometheus. **440 tests, 98% cobertura agregada** (3624 statements) — único caveat real: `ws/router.py` mide 53-74% pese a que sus 4 endpoints SÍ se ejercitan (`tests/ws/test_router.py`), déficit de instrumentación de `coverage.py` con TestClient basado en hilos, no código sin probar. Criterios de salida literales cumplidos uno a uno (auth, validaciones, 409 cementerio, SIZING_CAP, deriva EA, posición sin SL+Telegram<60s — este último un hueco real cerrado en el cierre de fase). OpenAPI sin warnings (`tests/test_openapi.py`) · `scan_hardcoding` limpio o justificado (207 hallazgos, 2 reales corregidos) · `ruff`/`mypy --strict` limpios.

CI verde run [`33018969105`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33018969105) — pero el primer push (run `33018551295`) SÍ falló de verdad: `RuntimeError: Form data requires "python-multipart" to be installed` (`auth/router.py::POST /token` usa `OAuth2PasswordRequestForm`, resuelto por FastAPI en runtime). El paquete estaba instalado en el venv local de forma incidental, nunca declarado en `pyproject.toml` — 440/440 pasaban en local sin que nadie lo notara, el runner limpio de GitHub lo destapó. Corregido (commit `7c45c6f`), reproducido y verificado en local antes de repushear.

Pendiente para más adelante (no bloquea G6): investigar el déficit de cobertura de `ws/router.py` si algún día hace falta un número real · 5 gaps de negocio en `docs/backlog.md` (chips de Salud sin fórmula, `r_multiple` nunca poblado, sin equity/Sharpe por bot, `ea_state` sin sizing, exposición sin conversión de divisa) · `ums_max_dd_gate_pct=8` aún sin confirmar por el operador. Detalle completo en `ASSUMPTIONS.md` G5-00 a G5-14.

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
G7 Frontend resto de pestañas · G8 Seed + E2E · G9 Hardening.
