# Estado de fase — StratOS-QXPro

> Se actualiza SIEMPRE al cerrar trabajo (regla de continuidad entre sesiones). Al abrir sesión, leer esto + `CLAUDE.md` + `ASSUMPTIONS.md` antes de proponer nada.

## Fase actual: G0 — Scaffold + tooling de gobierno

**Estado**: en progreso.

### Verde (verificado en esta sesión)
- Repo git independiente inicializado (`main`), primer commit con el input de gobierno ya entregado (PROMPT_MAESTRO, capturas, CLAUDE.md, skill, MCP server, settings.json, pre-commit, CI).

### Pendiente dentro de G0
- `docker-compose.yml` + `docker-compose.override.prod.yml` + `infra/` (nginx, postgres init, prometheus).
- `config/thresholds.seed.json` (SystemConfig completo, PARTE 10.3).
- `core-engine/` scaffold (pyproject.toml, FastAPI stub, smoke test, Dockerfile).
- `api-gateway/` placeholder mínimo.
- `frontend/` scaffold (Vite+React+TS, `ui_strings.es.json` semilla).
- `.env.example`, `README.md`.
- `.mcp.json` + `.venv` (Python 3.12) con `mcp` instalado.
- Verificación real: `docker compose up -d postgres redis`, lint+test backend, build frontend, `scan_hardcoding`.

### Decisiones pendientes del operador
- Revisar y confirmar/corregir los defaults inventados en `ASSUMPTIONS.md` (G0-05 a G0-08: Page-Hinkley, UMS).
- Autorizar el push a un remoto de GitHub cuando quiera que el job `ci.yml` corra de verdad (no se hace sin permiso explícito).
- Reiniciar la sesión de Claude Code (o `/mcp`) para que el servidor `stratos` recién registrado en `.mcp.json` quede disponible como tool.

## Fases futuras (PARTE 12)
G1 Modelo de datos · G2 Fórmulas (TDD) · G3 Máquinas de estado · G4 mt5-connector + simulador · G5 core-engine (servicios/API/WS) · G6 Frontend shell + Resumen · G7 Frontend resto de pestañas · G8 Seed + E2E · G9 Hardening.
