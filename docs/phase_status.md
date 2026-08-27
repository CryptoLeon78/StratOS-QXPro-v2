# Estado de fase — StratOS-QXPro

> Se actualiza SIEMPRE al cerrar trabajo (regla de continuidad entre sesiones). Al abrir sesión, leer esto + `CLAUDE.md` + `ASSUMPTIONS.md` antes de proponer nada.

## Fase actual: G8 — Seed + E2E

**Estado**: en curso, plan aprobado por el operador (`C:\Users\Ivan SQX\.claude\plans\immutable-bouncing-cascade.md`). G7 cerrado en sesión previa (14/14 commits), pusheado y con CI verde 7/7 (run [`33048222928`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33048222928)).

**Commits reales de G8 hasta ahora** (de los ~17 previstos) — `scripts/seed.py` está COMPLETO y corre de punta a punta con auto-verificación:
1. `279a308` estructura `seed_lib/` + CLI `seed.py`
2. `59442fd` `accounts.py` + `bots_production.py` + baselines
3. `b717f4d` fix: renombra bots de relleno (colisión de nombres con cantera)
4. `3a27835` `bots_pipeline.py` (cantera F1-F6) + `graveyard.py`
5. `7805a75` `trades_history.py` — generador determinista + bulk insert sellado
6. `71aaf03` `equity_curve.py` — EquitySnapshot diaria + heartbeats sellados
7. `81ce29d` `scenarios.py` — huérfanos, bot muerto/desbocado, impulsos, noticias, SL
8. `0793d24` `derived_states.py` — invoca los sweeps reales del portfolio
9. `4e5d280` `audit_error.py` + `header_state.py` — cierre y auto-verificación del seed

**Verificado contra Postgres real tras el commit 9** (`python scripts/seed.py --profile full --reset [--inject-audit-error]`, ambos casos pasan `verify_header_state`): 32 bots producción + 24 cantera + 9 graveyard · ~15.850 trades (objetivo 15.486) · DD 2,56% (objetivo 4,8%, aproximado, ASSUMPTIONS G8-04) · 14/68 meses negativos · retorno medio 2,63% (objetivo 2,69%) · correlación media 0,16 · par Lyra×Phoenix 0,50 redundante=True (criterio 9) · reconciliación contable exacta sin injectar (`discrepancy_pct=0`, criterio 6) y rota con `--inject-audit-error` (Alert CRITICA real) · 89.359 lotes sellados de 137.296 objetivo (~65%, gap conocido, ASSUMPTIONS G8-05) · **Poseidón NARANJA + Decision Confirmar/Posponer/Descartar pendiente con instrucción literal correcta (criterio 2)** · Sigma MR=GO / Estige-Palas-Helios=HOLD (criterio 10) · watchdog 29/32 OK + Hipnos=DEAD + Baco=RUNAWAY forzados (criterio 7, aproximado) · idempotencia (`--reset` ausente + seed ya hecho → no-op) verificada.

**Hallazgo real documentado, no corregido** (ASSUMPTIONS G8-07): 28/32 bots de producción caen en AMARILLO en el sweep de semáforo (vía `loss_streak`/`page_hinkley` sobre el historial COMPLETO de 400-600 trades, no una ventana reciente) — desajuste real entre la calibración de `semaphore_sweep.py` (pensada para un historial de producción normal) y los 5,5 años densos que exige el seed. No bloquea ningún criterio de PARTE 16 (solo Poseidón/Vega tienen estado exigido literalmente); corregirlo tocaría lógica de G3/G5 ya cerrada, fuera de alcance de G8 sin autorización del operador.

**Pendiente** (orden del plan): `scripts/data/sp500_monthly.csv` a 66 meses → suite de criterios de aceptación (`test_g8_acceptance_criteria.py`) → specs Playwright (pipeline/graveyard/7 pestañas restantes/vista dominical/flujo operativo) → 2 jobs CI nuevos → README/backlog/ASSUMPTIONS de cierre → PHASE REPORT.

**Nota de higiene del working tree**: hay cambios ajenos a G8 sin commitear en `doc_app/` (6 ficheros borrados, movidos por el operador a otra carpeta según el propio `docs/backlog.md`) y ruido no rastreado bajo `.github/workflows/` (`bin/`, `micromamba/`, `rcc*.yaml*`, `temp/` — artefactos de alguna herramienta externa, no generados por esta sesión). Ninguno de los dos se ha tocado ni commiteado desde aquí — no pertenecen a G8 y `doc_app\` está bloqueado para el agente (regla de comportamiento §7).

## Fases cerradas

### G7 — Frontend pestañas 2–11 (cerrada, CI verde 7/7)

Las 10 pestañas (Portfolio, Salud, Riesgo, Bots, Pipeline, Ejecución, Escalado, Graveyard, Auditoría, Cuentas/EA) tienen contenido real, cada una verificada en vivo contra `core-engine` real con datos de prueba sembrados vía scripts desechables (nunca commiteados). Prerequisito: nuevo router `core/routers/config.py` (solo lectura, expone la escalera Kill-Switch, las 6 fases UMS, los umbrales del gate y las instrucciones de semáforo — ninguno tenía endpoint antes de G7).

**6 ADRs** (`docs/adr/0001`-`0006`, primeros del proyecto) documentan desviaciones de fidelidad visual respecto a las capturas: fusión GRID/SCALPING en Portfolio, PH booleano en Salud, "Historial de semáforo" en vez de "del pipeline" en Bots, 7 criterios reales del gate (no Sortino/Asymmetry del mockup) en Pipeline, botones reales en vez de "Mover a…" en Pipeline, sin fecha de inicio en Graveyard.

**Huecos de negocio reales, documentados y omitidos (no inventados)**: decisión explícita del operador antes de empezar la fase (ver ASSUMPTIONS G7-01) de mantener G7 estrictamente frontend — el grupo más grande de huecos cae en Bots (Métricas completas Sortino/Calmar/Ulcer/Recovery Factor, posiciones abiertas, histograma de retornos, P&L acumulado por bot), seguido de Riesgo/Portfolio/Escalado/Auditoría/Cuentas-EA con huecos puntuales. Lista completa por pestaña en `docs/backlog.md`.

**48 tests de Vitest** (24 nuevos sobre los de G6) + **447 tests de pytest** de core-engine (sin regresión), `tsc --noEmit`/`npx eslint .`/`npx vite build` limpios en cada commit. `scan_hardcoding` sobre `frontend/src/` limpio o justificado (100 hallazgos nuevos, mismas 4 categorías de precedente de G6-02 + 1 constante matemática de interpolación de color sin categoría de negocio — ver ASSUMPTIONS G7-09).

**Caveats reales, no ocultados**:
- Bundle de producción sube a ~1 MB (311 kB gzip) con `recharts` añadido para Portfolio — code-splitting sigue siendo tarea de G9.
- Screenshot-diff automatizado de las 10 pestañas nuevas queda para G8 (mismo patrón que G6: el spec mínimo de Playwright no está wireado en CI todavía) — la verificación visual de G7 fue manual en vivo, no automatizada.

CI verde run [`33048222928`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33048222928) — los 7 jobs.

Detalle completo (11 decisiones/hallazgos) en `ASSUMPTIONS.md` G7-00 a G7-11.

### G6 — Frontend shell + pestaña Resumen (cerrada, CI verde 7/7)
Stack de PARTE 4 instalado sobre el scaffold de G0: Tailwind v3 (theme generado 1:1 desde `design_tokens.json`) · shadcn/ui vendorizado y adaptado a tokens (8 componentes: button/card/badge/collapsible/input/label/form/dialog) · TanStack Query + Zustand + react-router-dom v7 (Data Router) · React Hook Form + Zod · Lightweight Charts v5 (equity) · Vitest+RTL+MSW + ESLint 10 + Playwright. Router de 11 pestañas + `/login` (solo Resumen con contenido real, las otras 10 placeholders navegables para G7). Login JWT completo (RHF+Zod, `authStore` con persist, `api/client.ts` con refresh-on-401 deduplicado). `AppHeader` con las 6 StatCard reales + WS (`/ws/equity`+`/ws/alerts`, reconexión con backoff, fallback a polling 5s ya existente). Pestaña Resumen completa: card de equity + selector de rango + panel "Requiere acción" (DecisionCard+PostponeDialog+mutations) + panel Pipeline (contadores F1-F7 + novedades).

**24 tests de Vitest + 1 de Playwright (verificado localmente 3 veces, no en CI todavía), 0 errores/0 warnings de ESLint, `scan_hardcoding` limpio o justificado** (~40 hallazgos nuevos, todos en 5 categorías con precedente ya establecido — ver ASSUMPTIONS G6-02). Criterios de salida literales cumplidos: cabecera <2s (asegurado con aserción dura de Playwright + medido en vivo), screenshot-diff de Resumen dentro de umbral (`maxDiffPixelRatio=0.02`, nuevo, sin cifra contractual — a confirmar por el operador, G6-03). `npx tsc --noEmit` y `npx vite build` limpios en cada commit.

**Todo verificado end-to-end contra `core-engine` real en el navegador de este entorno** (no solo mocks): login real, refresh-on-401 disparado de verdad por un token expirado durante la sesión, WS conectando (`[accepted]`/`connection open` en el log del servidor), mutations de decisiones (confirm/postpone) contra la API real con persistencia confirmada en Postgres.

**Caveats reales, no ocultados**:
- Playwright (`tests/e2e/resumen.spec.ts`) **no está wireado en CI** — el job `lint-and-build-frontend` no levanta Postgres/Redis/core-engine; verificado solo localmente (3 corridas deterministas). Wireado completo es tarea de G8 ("Seed + E2E").
- Bundle de producción >500 kB (aviso de Rollup, `lightweight-charts` es el mayor contribuyente) — code-splitting es tarea de G9.
- Un icono pequeño no perteneciente a la app aparece en la esquina de la baseline de Playwright — confirmado que no es del DOM, consistente con un artefacto de renderizado por software del Chrome for Testing headless de este entorno (ASSUMPTIONS G6-04), dentro de tolerancia.
CI verde run [`33039521500`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33039521500) — los 7 jobs, incluido el `lint-and-build-frontend` ampliado con Lint (ESLint) + Unit tests (Vitest) además del build que ya tenía.

Detalle completo (15 decisiones de diseño, `scan_hardcoding` categorizado, artefactos de test) en `ASSUMPTIONS.md` G6-00 a G6-04.

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
G9 Hardening.
