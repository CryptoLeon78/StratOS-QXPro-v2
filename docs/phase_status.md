# Estado de fase — StratOS-QXPro

> Se actualiza SIEMPRE al cerrar trabajo (regla de continuidad entre sesiones). Al abrir sesión, leer esto + `CLAUDE.md` + `ASSUMPTIONS.md` antes de proponer nada.

## Fase actual: G7 — Frontend resto de pestañas

**Estado**: implementación completa (14/14 commits locales), **pendiente de 2 confirmaciones del operador antes del cierre formal**: (1) aprobación explícita de la pestaña Cuentas/EA (diseño derivado, sin captura de referencia — criterio de salida literal de PARTE 12); (2) push a `origin/main` + confirmación de CI verde (no hecho todavía en esta sesión).

Las 10 pestañas (Portfolio, Salud, Riesgo, Bots, Pipeline, Ejecución, Escalado, Graveyard, Auditoría, Cuentas/EA) tienen contenido real, cada una verificada en vivo contra `core-engine` real con datos de prueba sembrados vía scripts desechables (nunca commiteados). Prerequisito: nuevo router `core/routers/config.py` (solo lectura, expone la escalera Kill-Switch, las 6 fases UMS, los umbrales del gate y las instrucciones de semáforo — ninguno tenía endpoint antes de G7).

**6 ADRs** (`docs/adr/0001`-`0006`, primeros del proyecto) documentan desviaciones de fidelidad visual respecto a las capturas: fusión GRID/SCALPING en Portfolio, PH booleano en Salud, "Historial de semáforo" en vez de "del pipeline" en Bots, 7 criterios reales del gate (no Sortino/Asymmetry del mockup) en Pipeline, botones reales en vez de "Mover a…" en Pipeline, sin fecha de inicio en Graveyard.

**Huecos de negocio reales, documentados y omitidos (no inventados)**: decisión explícita del operador antes de empezar la fase (ver ASSUMPTIONS G7-01) de mantener G7 estrictamente frontend — el grupo más grande de huecos cae en Bots (Métricas completas Sortino/Calmar/Ulcer/Recovery Factor, posiciones abiertas, histograma de retornos, P&L acumulado por bot), seguido de Riesgo/Portfolio/Escalado/Auditoría/Cuentas-EA con huecos puntuales. Lista completa por pestaña en `docs/backlog.md`.

**48 tests de Vitest** (24 nuevos sobre los de G6) + **447 tests de pytest** de core-engine (sin regresión), `tsc --noEmit`/`npx eslint .`/`npx vite build` limpios en cada commit. `scan_hardcoding` sobre `frontend/src/` limpio o justificado (100 hallazgos nuevos, mismas 4 categorías de precedente de G6-02 + 1 constante matemática de interpolación de color sin categoría de negocio — ver ASSUMPTIONS G7-09).

**Caveats reales, no ocultados**:
- Bundle de producción sube a ~1 MB (311 kB gzip) con `recharts` añadido para Portfolio — code-splitting sigue siendo tarea de G9.
- Screenshot-diff automatizado de las 10 pestañas nuevas queda para G8 (mismo patrón que G6: el spec mínimo de Playwright no está wireado en CI todavía) — la verificación visual de G7 fue manual en vivo, no automatizada.
- CI **no confirmado todavía** en esta sesión — pendiente de push.

Detalle completo (11 decisiones/hallazgos) en `ASSUMPTIONS.md` G7-00 a G7-11.

## Fases cerradas

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
G8 Seed + E2E · G9 Hardening.
