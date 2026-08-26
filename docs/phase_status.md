# Estado de fase — StratOS-QXPro

> Se actualiza SIEMPRE al cerrar trabajo (regla de continuidad entre sesiones). Al abrir sesión, leer esto + `CLAUDE.md` + `ASSUMPTIONS.md` antes de proponer nada.

## Fase actual: G2 — Fórmulas (TDD)

**Estado**: **cerrada por completo**. Los 20 fórmulas de PARTE 8 implementadas con TDD real (rojo confirmado con comandos reales antes de cada implementación, nunca narrado) y CI en GitHub Actions verde 3/3 (run [`32939959347`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions)).

### Verde (verificado con comandos reales en esta sesión)
- `core-engine/src/core/formulas/` (6 módulos: `types`, `trading`, `portfolio`, `pipeline`, `monitoring`, `audit`) — **100 % de cobertura, 217/217 statements, 87/87 tests** (exige PARTE 12: ≥95 %). Suite completa del proyecto: 103/103 en verde (sin regresión de G0/G1).
- Property-based con `hypothesis` en las 4 propiedades que PARTE 8 cita explícitamente: `max_drawdown_pct ≥ 0`, `|correlation_matrix| ≤ 1`, `walk_forward_efficiency` acotada con inputs acotados, `decision_eta_days` monótona (no creciente) en `freq_week`.
- Nuevas dependencias reales (pandas/numpy/statsmodels) verificadas con `ols_alpha_beta` (regresión OLS real) y `daily_returns`/`correlation_matrix` (`pd.Series`/`pd.DataFrame` tal cual exige la firma de PARTE 8).
- `ruff check` + `ruff format --check` + `mypy --config-file core-engine/pyproject.toml ... --strict` limpios. `scan_hardcoding`: solo defaults de parámetro que PARTE 8 fija literalmente en su propia firma (categorías G2-01/04, no umbrales de negocio).

### 7 bugs reales encontrados y corregidos en esta sesión (detalle en ASSUMPTIONS G2-02/03/05/06/07 + hallazgos sin número propio)
`mypy` resuelve su config contra el *cwd*, no la ruta analizada — `ci.yml` nunca cargaba el override de `statsmodels` (habría roto CI, corregido con `--config-file` antes de pushear) · `pandas.ffill(limit=0)` lanza en vez de ser no-op · `monte_carlo_maxdd` necesitaba una base de equity que PARTE 8 no incluye en la firma (`initial_equity` añadido) · `page_hinkley` de un solo lado (formulación clásica) no detectaba bajadas de la media — solo subidas; reimplementado como detector de dos lados tras verlo fallar con una serie de caída fuerte · una rama muerta en `historical_cvar` (el umbral de percentil nunca deja la cola vacía) · dos mensajes de error inconsistentes con el patrón "vac..." del resto del catálogo.

### Pendiente — depende del operador, no de más trabajo de agente
- Revisar los defaults/diseños propios en `ASSUMPTIONS.md` (G0-05 a G0-08, G1-05/06/07, y ahora G2-06/07: la fórmula de `sustainable_withdrawal` y el reparto de `counterfactual_impulse` por tipo de impulso son diseño propio sin cifra exacta de PARTE 8 que contrastar) antes de que G3 los use en las máquinas de estado.

## Fases cerradas

### G1 — Modelo de datos (cerrada)
25/25 tablas de PARTE 5.2, migraciones Alembic 0001/0002, rol `stratos_app` con grants exactos, 16/16 tests contra Postgres/TimescaleDB real. Detalle en `ASSUMPTIONS.md` G1-01 a G1-14 y el historial de commits.

### G0 — Scaffold + tooling de gobierno (cerrada)
Repo git independiente en `https://github.com/CryptoLeon78/StratOS-QXPro-v2` (privado), `.mcp.json` operativo, `docker compose up -d postgres redis` healthy, CI verde, `config/thresholds.seed.json` (61 claves), scaffolds de `core-engine`/`api-gateway`/`frontend`. Detalle en `ASSUMPTIONS.md` G0-01 a G0-14.

## Fases futuras (PARTE 12)
G3 Máquinas de estado · G4 mt5-connector + simulador · G5 core-engine (servicios/API/WS) · G6 Frontend shell + Resumen · G7 Frontend resto de pestañas · G8 Seed + E2E · G9 Hardening.
