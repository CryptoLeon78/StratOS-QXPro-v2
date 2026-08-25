# Estado de fase — StratOS-QXPro

> Se actualiza SIEMPRE al cerrar trabajo (regla de continuidad entre sesiones). Al abrir sesión, leer esto + `CLAUDE.md` + `ASSUMPTIONS.md` antes de proponer nada.

## Fase actual: G0 — Scaffold + tooling de gobierno

**Estado**: cerrada (ver PHASE REPORT en el chat / commit history). Todo lo de la checklist de PARTE 12 está creado y verificado en esta sesión salvo las dos acciones que dependen del operador (abajo).

### Verde (verificado con comandos reales en esta sesión)
- Repo git independiente, `main`, 9 commits por unidad (conventional commits).
- `docker compose up -d postgres redis` → ambos `healthy`; extensión `timescaledb` confirmada con `\dx` dentro del contenedor.
- `core-engine`: `ruff check` limpio, `mypy --strict` limpio, `pytest` 1/1 verde (smoke test `/health`).
- `api-gateway`: instala editable, `ruff check` limpio.
- `frontend`: `npm install` + `npm run build` (tsc + vite build) verde; `npm audit` en 0 tras el salto a vite 8.
- `scan_hardcoding` repo-wide: 5 hallazgos, los 5 falsos positivos en código entregado (`mcp\stratos_mcp_server.py`, ver ASSUMPTIONS G0-14); `core-engine/` y `frontend/` en 0.
- `config\thresholds.seed.json` (61 claves) cargado y legible por `get_thresholds()`; `get_project_status()` confirma instalado: prompt_maestro, design_tokens, thresholds_seed, claude_md, skill, assumptions, core_engine, frontend. `connector` en `false` es correcto (mt5-connector es G4).
- `.mcp.json` registra `stratos`; el proceso arranca limpio (verificado con stdin cerrado, exit 0, sin traceback) en el venv del proyecto con `mcp<2` instalado.

### Pendiente — depende del operador, no de más trabajo de agente
- **Reiniciar la sesión de Claude Code** (o `/mcp`) para que el servidor `stratos` recién registrado quede disponible como tool en el chat — no se puede invocar dentro de la sesión que lo registró.
- **Autorizar el push a un remoto de GitHub** cuando se quiera que `ci.yml` corra de verdad (no se hace sin permiso explícito, es una acción visible).
- **Revisar los defaults inventados** en `ASSUMPTIONS.md` (G0-05 a G0-08: Page-Hinkley, UMS min months/Sharpe) y confirmarlos o corregirlos antes de que G2/G3 los consuman.

## Fases futuras (PARTE 12)
G1 Modelo de datos · G2 Fórmulas (TDD) · G3 Máquinas de estado · G4 mt5-connector + simulador · G5 core-engine (servicios/API/WS) · G6 Frontend shell + Resumen · G7 Frontend resto de pestañas · G8 Seed + E2E · G9 Hardening.
