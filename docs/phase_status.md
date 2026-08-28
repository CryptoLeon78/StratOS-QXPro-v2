# Estado de fase — StratOS-QXPro

> Se actualiza SIEMPRE al cerrar trabajo (regla de continuidad entre sesiones). Al abrir sesión, leer esto + `CLAUDE.md` + `ASSUMPTIONS.md` antes de proponer nada.

## Fase actual: G10 — Cierre de huecos de negocio (docs/backlog.md) — EN CURSO, pausada por el operador

G0-G9 (PARTE 12, plan original) están cerradas — ver más abajo. G10 es trabajo nuevo, fuera de ese plan, iniciado a petición del operador para abordar el backlog de huecos de negocio acumulado en G4-G9 (plan aprobado, `~/.claude/plans/immutable-bouncing-cascade.md`).

**Backend cerrado (grupos a-l), CI verde 9/9 en cada checkpoint, último run [`33120563244`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33120563244)**. ~13 commits, todos TDD-first donde aplica (rojo confirmado antes de implementar), verificados contra Postgres/Redis reales:
- (a) Esquema: `Account.login` UNIQUE · `instrument_spec` (real desde SQX vía `spread_sqx`) · `symbol_currency`.
- (b) 7 fórmulas nuevas (Sortino/Calmar/Ulcer/RecoveryFactor/WinRateDrift/Payoff/AvgTradeDuration), 100% cobertura.
- (c) `services/bot_equity.py` — curva de P&L por bot + posiciones abiertas.
- (d) `Trade.r_multiple` — backfill real (15.944 trades) + wiring en ingest. Overflow real de columna corregido (`NUMERIC(8,4)→(12,4)`, hypertable comprimida).
- (e) `services/fx.py` — conversión real a EUR de exposición (sin FxRate poblado todavía, servicio funcional y probado).
- (f) `services/news.py` — News Shield retrospectivo (trades en ventana de noticias).
- (g) 5 endpoints aditivos (posiciones abiertas, MC histórico, episodio kill-switch, equity/balance de cuenta). "Graveyard fecha de inicio" investigado y confirmado irresoluble sin tabla de histórico nueva.
- (h) `services/ums.py` — evolución mensual real (trades/retorno/max DD).
- (i) `GET /audit/continuity-gaps` — tramos sin envío detallados.
- (j) `services/benchmark.py` — Portfolio vs S&P500 (CAGR/alfa/beta/IR/Batting/Capture).
- (k) Pipeline Backtest vs Forward — investigado, gap real confirmado (sin ingest de backtest, fuera de alcance).
- (l) `EaState.sizing_pct` + deriva de sizing — backend a spec, no verificado contra EA real.

**Detalle completo de las 14 decisiones/hallazgos en `ASSUMPTIONS.md` G10-00 a G10-13.**

**(m) frontend — EN CURSO** (reanudado tras el checkpoint de pausa, a petición explícita del operador "Continua con el frontend"):
- **Salud** (`ec0fc31`) — hecha, verificada en CI real.
- **Bots** (`f2d8d2f` backend + `b5bf044` loss_streak_baseline + `6e49f9c` frontend) — hecha, verificada en vivo (bot con baseline y bot sin trades) y en CI real. 2 bugs reales encontrados y arreglados via verificación en vivo: timestamps duplicados en `BotPnlChart.tsx` (lightweight-charts exige orden estrictamente ascendente) y `compute_portfolio_contribution()` crasheaba con 500 para cualquier bot sin trades (agregado SQL sin GROUP BY sobre el hypertable `trade` de TimescaleDB devuelve 0 filas en vez de la fila que garantiza el estándar SQL). Ver `ASSUMPTIONS.md` G10-15.
- **Hallazgo mayor de infraestructura E2E, resuelto** (`4f41df4`/`2bf52d3`/`1971978`, ver `ASSUMPTIONS.md` G10-14): `e2e-playwright` estaba roto de forma sistémica (fuente `Inter` no auto-hospedada, resuelta entre máquinas efímeras del runner de forma inconsistente — no era un baseline desactualizado por el trabajo de Salud) + 2 bugs de máscara reales (`headerMask()` sin el badge STALE, `resumen.spec.ts` con máscara duplicada sin el equity-chart cubierto). **`e2e-playwright` verde 12/12 en CI real**, confirmado de nuevo en el run del commit de Bots ([`33144135903`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33144135903)).
- **Hallazgo separado, documentado, NO resuelto (decisión explícita del operador)**: `e2e-acceptance-full` roto (criterio 9, Lyra×Phoenix redundante, perfil `full`) — confirmado pre-existente a G10-14, no relacionado con el trabajo de frontend, sigue rojo en cada run desde entonces. Ver `ASSUMPTIONS.md` G10-14 y `docs/backlog.md`.
- **Tarea aparte flageada, no bloqueante**: auditar los otros 14 usos de `.scalar_one()` en core-engine por el mismo riesgo de hypertable-sin-chunks (ver `ASSUMPTIONS.md` G10-15).
- **Riesgo** (`7c4c415`, m-03) — hecha, verificada en CI real (`e2e-playwright` verde, run [`33144739367`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33144739367)) y en vivo. 4 gaps de G10 cerrados en frontend (backend ya construido en grupos (g)/(c) antes del checkpoint de pausa): `KillSwitchPanel.tsx` (MAX DD/DURACIÓN DD del episodio), `ExposureCard.tsx` (subtotales por divisa, nativa no EUR), `NewsShieldPanel.tsx` (trades en ventana de noticias agrupado por bot), `MonteCarloList.tsx` (histórico de runs + fecha de firma del contrato).
- **Portfolio** (`1fc1351`, m-04) — hecha, verificada en CI real (`e2e-playwright` verde, run [`33146440551`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33146440551)) y en vivo. Último gap de G10 para esta pestaña: sección "¿Añade valor real el portfolio?" (`PortfolioBenchmarkCard.tsx`, 8 métricas + badge de veredicto + chart de 2 líneas). TDD real: `compare_to_benchmark()` calculaba la serie mensual alineada internamente pero la descartaba — nuevo campo `monthly_points` (test rojo confirmado antes de implementar).
- **Escalado** (`25415a9`, m-05) — hecha, verificada en CI real (`e2e-playwright` verde, run [`33146884718`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33146884718)) y en vivo (estados vacíos correctos, sin `UmsPhaseLog` sembrado en el dev DB local). `MonthlyEvolutionTable.tsx` añade Trades/Retorno/Max DD (backend ya construido en grupo (h)).
- **Graveyard** — revisado, SIN gap de G10 pendiente (fecha de inicio ya investigada y confirmada irresoluble en el checkpoint de pausa, ver `docs/adr/0006`; el resto ya estaba completo desde G7). No requirió commit.
- **Auditoría** (`1bdc6f5`, m-06) — hecha, verificada en CI real (`e2e-playwright` verde, run [`33147293299`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33147293299)) y en vivo. `ContinuityCard.tsx` lista los tramos sin envío detallados por cuenta (backend ya construido en grupo (i)).
- **Cuentas/EA** (`1544fc2` + `5016275` baseline, m-07) — hecha, verificada en CI real (`e2e-playwright` verde, run [`33148244916`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33148244916)) y en vivo (cuenta con snapshot parcial + cuenta sin snapshot). `AccountCard.tsx` añade el grid de 4 celdas Equity/Balance/Margen libre/Margin level (backend ya construido en grupo (g)) — grid siempre presente, "—" por celda faltante (mismo criterio anti-desplazamiento que G9-06/G9-07). Baseline `cuentas_ea.png` regenerado (cambio de altura real de la tarjeta, no flake).

**(m) COMPLETO — las 7 pestañas regulares del plan cerradas y verificadas en CI real** (Salud/Bots/Riesgo/Portfolio/Escalado/Graveyard[sin gap]/Auditoría/Cuentas-EA).

**(n) COMPLETO — Vista `/dominical`** (`7376513`), aprobada explícitamente por el operador antes de construirla, verificada en CI real (`e2e-playwright` verde, run [`33149603328`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33149603328)) y en vivo. Ruta de nivel superior (NO en `RootLayout`, NO en `TabBar`), punto de entrada: enlace discreto en `AppHeader`. Backend nuevo `GET /alerts` (TDD, gap real: `Alert(module="config_drift")` nunca se listaba). Reusa `HeartbeatCard`/`WatchdogTable` (desconexiones) y `NewsShieldPanel` con `hours=168` (noticias semana entrante, ahora prop configurable). "Órdenes rechazadas" documentado pendiente (v1.1 EA reporter). Criterio literal PARTE 16 #14 verificado con test de contenido real (`vista_dominical.spec.ts`): EQUITY/P&L DÍA/DRAWDOWN nunca aparecen.

**Siguiente y último paso de G10: (o) Cierre de fase.**

**Pendiente**:
- (o) Cierre: `scan_hardcoding` completo sobre todo lo tocado en G10 (ya verificado limpio en cada commit, falta el pase final consolidado), `docs/backlog.md`/`ASSUMPTIONS.md` finales, PHASE REPORT de toda la fase G10.

**Al retomar**: releer este bloque + `ASSUMPTIONS.md` G10-00 a G10-15 + `docs/backlog.md` (ya actualizado con cada gap resuelto/investigado, incluida la vista dominical) antes de escribir el PHASE REPORT final de (o). El plan aprobado completo sigue en `~/.claude/plans/immutable-bouncing-cascade.md`.

## Fases cerradas (G0-G9, PARTE 12, plan original)

### G9 — Hardening (cerrada, CI verde 9/9)

**Estado**: 29 commits, pusheados en 9 tandas (una por checkpoint de grupos relacionados, más 4 rondas extra de diagnóstico/fix cuando `e2e-playwright` volvió a romper tras el push del grupo (j) por un motivo no relacionado con el código de G9 — ver hallazgos 6-8 abajo), cada tanda confirmada con CI real antes de continuar a la siguiente — mismo estándar que G8. Todos los grupos previstos en el plan (a-j) completos. **Última confirmación, definitiva: CI verde 9/9 real con el workflow en su forma normal (sin ningún paso temporal), run [`33105823894`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33105823894)**.

**Los 3 items que el backlog de G4-G8 ya había prometido "para G9-hardening" están resueltos**: `api-gateway/` real (proxy transparente + rate-limit + WS broker, deja de ser el placeholder de G0) · revocación de JWT vía denylist Redis (rotación de refresh + `POST /auth/logout`) · code-splitting del bundle de frontend (1.007kB→329kB, sin aviso de Rollup). Más la línea literal de G9: backups `pg_dump`+WAL (verificados de verdad contra Postgres real) · rotación de API keys (documentación, ya soportado desde G4) · playbook de alertas · `config/small_scale.yaml` · `docs/runbook.md` completo · ADRs cerrados (0007 nuevo, primero de arquitectura).

**8 bugs reales encontrados y corregidos, todos verificados contra infraestructura real (no simulados)**:
1. WS broker del gateway no propagaba el código de cierre real de core-engine (1008 con token inválido) — el cliente veía siempre el 1000 genérico.
2. `pydantic-settings` sin declarar en `api-gateway/pyproject.toml` — pasaba en el venv compartido del repo, rompía en CI (instalación aislada) y en un venv aislado real que se usó para reproducirlo antes de repushear.
3. `pg_restore` ignora 6 FK constraints sobre hypertables comprimidas de TimescaleDB (`trade`/`equity_snapshot`/`heartbeat_log`) — los datos restauran al 100%, esas FK se reaplican a mano (SQL exacto en el runbook); el script ahora lo señala explícito en vez de quedar "verde" en silencio.
4. `frontend/Dockerfile` nunca fijaba `VITE_API_BASE_URL`/`VITE_WS_BASE_URL` en tiempo de build — la imagen de producción arrancaba con los defaults de desarrollo (`http://localhost:8100`) horneados en el JS, rotos para cualquier visitante real.
5. El nginx interno del contenedor `frontend` no tenía `try_files $uri /index.html` — cualquier ruta de React Router navegada directa devolvía 404. (Los bugs 4/5 solo salieron a la luz al levantar `docker compose --profile prod up` de punta a punta con un navegador real por primera vez desde que existen los Dockerfiles — G8-13 solo había verificado que los builds compilaban, nunca el runtime del bundle servido.)
6. `scripts/seed.py::bulk_insert_heartbeats` anclaba el último heartbeat al `now` del INICIO del script completo, no al momento real de inserción — reducía pero no eliminaba una carrera de tiempo real (ver 7).
7. **`AppHeader.tsx`/`AccountCard.tsx` montaban/desmontaban el badge "DATOS STALE" y el bloque heartbeat/latencia/uptime según el estado en vivo** (no el seed) — cuando cualquiera cambiaba de presente→ausente entre la captura del baseline de Playwright y la corrida del test, la página entera se desplazaba verticalmente. Confirmado con evidencia directa (no solo teoría): un intento de regenerar los 11 baselines vía CI dio los 11 ficheros byte-idénticos a los ya commiteados — esa corrida coincidió por pura casualidad. Rompió `e2e-playwright` real 2 veces, incluida una vez sobre un push puramente de documentación.
8. **Fix de raíz de (7), a petición explícita del operador tras el 2º fallo real**: los 2 componentes ahora reservan SIEMPRE su altura (`invisible` en vez de ausentes). **Determinismo probado con tiempo real transcurrido**: mismo baseline, antes y después de esperar 130+ segundos reales cruzando a propósito el umbral de 120s que antes causaba el fallo — sigue pasando. Confirmado además en Linux CI real tras el fix (run `33105823894`, workflow normal, sin trucos).

**1 desviación de arquitectura documentada formalmente**: PROMPT_MAESTRO PARTE 3 especifica que `api-gateway`↔`core-engine` debería usar un "token de servicio" propio; se construyó y verificó un proxy pass-through más simple (reenvía el JWT del usuario intacto, sin `JWT_SECRET` en el gateway) — decisión confirmada con el operador, documentada en `docs/adr/0007-gateway-sin-token-de-servicio.md` (primer ADR de arquitectura del proyecto, los 6 anteriores eran de fidelidad visual).

**Verificado end-to-end de verdad, con navegador real, contra la topología de producción completa** (`docker compose --profile prod build/up`: core-engine+worker+scheduler+api-gateway+frontend+nginx+postgres+redis, los 4 servicios con Dockerfile propio construidos de cero): login real por `http://localhost/` → dashboard Resumen completo con datos reales → navegación directa a `/portfolio` sin 404 → WS a través de nginx con un cliente real → consola sin errores. Además: backup/restore de Postgres real (4.6MB, recuentos de filas confirmados) y todo el flujo HTTP/WS del gateway verificado contra `core-engine` real antes de tocar Docker.

**Caveats reales, no ocultados**:
- Instalación de los 2 nodos (Windows+MT5/Linux+certbot) escrita a spec en `docs/runbook.md`, **no ejecutada contra infraestructura real** en ninguna sesión (mismo patrón que `install_service.ps1` desde G4) — ni un VPS real, ni un terminal MT5 real, ni un dominio real han existido en este proyecto.
- `config/small_scale.yaml` es un documento de referencia sin efecto en el sistema (decisión ya tomada con el operador, no wireado en runtime).
- Coste de UX aceptado explícitamente por el fix de (8): el badge "DATOS STALE" y la línea de heartbeat de una cuenta ahora reservan siempre su espacio (invisible cuando no aplican) — un hueco vacío mínimo en vez de un layout que se re-acomoda. No se ha visto ninguna captura de referencia que lo prohíba.

Detalle completo (9 decisiones/hallazgos numerados) en `ASSUMPTIONS.md` G9-00 a G9-07.

### G8 — Seed + E2E (cerrada, CI verde 9/9)

**Estado**: 21 commits, pusheado y confirmado con **3 runs reales de GitHub Actions** tras el push inicial (no solo verificación local). El primer push (`4f7cbf5`+`c3da7d0`..) destapó 3 bugs reales que la verificación local no había visto — los 3 corregidos y confirmados con CI verde 9/9 en el run [`33078966721`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33078966721):
1. **`test-backend` rompía** (9 fallos, `relation "bot" does not exist`) — `test_g8_acceptance_criteria.py` se conecta directo a `stratos` sin migrar en ese job; local llevaba la BBDD ya migrada toda la sesión, el runner limpio lo destapó. Fix: `--ignore` en `test-backend` (G8-14).
2. **`e2e-playwright` sin baselines `-linux.png`** — los 11 capturados en esta sesión son `-win32.png` (Windows), el runner es `ubuntu-latest`. Generados vía el propio CI real (`--update-snapshots` temporal + `upload-artifact`, 2 pushes, `gh run download`, revertido) — un intento previo de replicarlo con Docker local (`host.docker.internal`) conectaba pero el login nunca renderizaba, causa no diagnosticada, abandonado por no ser el entorno real (G8-15).
3. **2 bugs reales en los specs de Playwright**, enmascarados hasta entonces por el fallo de snapshot en TODOS los tests: `flujo_operativo.spec.ts` apuntaba a "Hipnos" (solo dispara `Alert`, nunca `Decision`) en vez de "Poseidón" (sí genera `Decision` confirmable vía el sweep real); `portfolio.spec.ts` asertaba la calibración de correlación a ~0,16 que solo aplica bajo `--profile full`, pero el job siembra `--profile ci` (G8-15).

**Los 17 criterios de aceptación de PARTE 16 están verificados**: `scripts/seed.py` completo y auto-verificado (`--profile full|ci`, `--inject-audit-error`) · 9 tests de aceptación (`test_g8_acceptance_criteria.py`, 9/9 verde en CI real, perfil `full`) · 11 specs de Playwright (12 tests, 12/12 verde en CI real, perfil `ci`) · 2 jobs de CI nuevos (`e2e-playwright`/`e2e-acceptance-full`) · `docker compose up` + seed timado de verdad (~101s, <10min).

**9 bugs reales en total encontrados y corregidos en esta fase** (6 en verificación local + 3 solo visibles en CI real — ver arriba): `Trade.r_multiple` nunca poblado disparaba AMARILLO en los 32 bots de producción (G8-07) · `_already_seeded()` nunca escribía su propia marca de idempotencia (G8-08) · CORS bloqueaba el harness E2E completo (G8-11) · 3 bugs en los Dockerfiles de `core-engine`/`frontend` (G8-13) · los 3 de CI real de arriba (G8-14/G8-15).

**Hallazgo real documentado, no corregido** (G8-07): 28/32 bots de producción caen en AMARILLO en el sweep de semáforo — desajuste real entre la calibración de `semaphore_sweep.py` y los 5,5 años densos que exige el seed. No bloquea ningún criterio; fuera de alcance sin autorización del operador.

**"Vista dominical" (criterio 14) confirmada ausente como superficie de UI** — mismo tratamiento que la UI de checklist: construirla es frontend nuevo, fuera de "Seed + E2E". Entrada en `docs/backlog.md`.

Detalle completo (15 decisiones/hallazgos) en `ASSUMPTIONS.md` G8-00 a G8-15.

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

Ninguna dentro de PARTE 12 — G0 a G9 era el plan original completo, ya cerrado. G10 (ver arriba, en curso) es trabajo nuevo fuera de ese marco. Trabajo futuro más allá de G10 (nuevas features, bugs reales que aparezcan en operación, ADRs revisados si cambian las circunstancias que los motivaron) se planifica cuando llegue.
