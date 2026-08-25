# StratOS-QXPro

Panel maestro de gestión de portfolios de bots de trading MetaTrader 5. Réplica production-grade del sistema mostrado en el vídeo de referencia (`doc_app\transcripcion_video_SIN__minutaje_donde_explica_funcionamiento_StratOS.md`): semáforos de salud por bot, kill-switch de portfolio, pipeline de validación F1→F7, rotación champion/challenger, auditoría inmutable con sellado SHA-256, escalado UMS y diario de impulsos.

La especificación contractual completa está en [`doc_app\PROMPT_MAESTRO.md`](doc_app/PROMPT_MAESTRO.md) (PARTES 0–17). Léela antes de tocar cualquier fase. El estado de avance vive en [`docs\phase_status.md`](docs/phase_status.md); las decisiones ante ambigüedades, en [`ASSUMPTIONS.md`](ASSUMPTIONS.md).

## Requisitos

- Python 3.12 (el proyecto fija esta versión en `pyproject.toml`; en Windows, si el `python` del PATH es otra versión, apunta el venv al intérprete 3.12 explícitamente).
- Node.js 20+ / npm.
- Docker + Docker Compose v2.
- (Opcional, para el MCP `stratos`) paquete `mcp<2` instalado en el mismo venv que `core-engine` (`stratos_mcp_server.py` usa la API `FastMCP` de mcp 1.x; `mcp` 2.x la renombró a `MCPServer` y rompe el import).

## Arranque rápido

```powershell
# 1. Entorno Python del core-engine
python -m venv .venv
.venv\Scripts\pip install -e "core-engine[dev]" "mcp<2"

# 2. Infra local (Postgres+TimescaleDB, Redis)
docker compose up -d postgres redis

# 3. Backend (una vez exista el modelo de datos, G1+)
.venv\Scripts\python -m uvicorn core.main:app --app-dir core-engine/src --reload --port 8100

# 4. Frontend
cd frontend
npm install
npm run dev
```

## Comandos habituales

```powershell
# Backend
pytest core-engine\tests -q
ruff check core-engine\
mypy core-engine\src\ --strict

# Frontend
cd frontend; npm run build; npm run test

# Gobierno / anti-hardcoding
python scripts\guardrails\pre_commit_scan.py < payload.json   # hook de pre-commit
# MCP stratos (una vez registrado en .mcp.json y con la sesión de Claude Code reiniciada):
#   get_thresholds | get_module_spec | get_design_tokens | get_formula_signature
#   get_acceptance_criteria | get_seed_scenario | scan_hardcoding | get_project_status
```

## Reglas no negociables

- **Cero hardcoding (P11)**: umbrales → `config\thresholds.seed.json`/`SystemConfig`; despliegue → `.env`/`Settings`; diseño → `doc_app\design_tokens.json`; textos de UI → `frontend\src\styles\ui_strings.es.json`. Ver `scripts\guardrails\pre_commit_scan.py` y la tool MCP `scan_hardcoding`.
- **Conector MT5 read-only**: nunca envía órdenes. El sistema instruye, el humano ejecuta y confirma.
- **Fidelidad visual 1:1**: ninguna vista se implementa sin leer antes la captura correspondiente en `capturas_proyecto_dashboard\`; cualquier desviación necesita un ADR en `docs\adr\`.
- **Inmutabilidad**: `DecisionLog`, `IngestBatch`, `SemaphoreTransition`, `KillSwitchEvent`, `WithdrawalLog`, `ChecklistRun` son append-only.

Detalle completo de todas las reglas: `CLAUDE.md` y `.claude\skills\stratos-guardian\SKILL.md`.

## Estructura del repo

Ver el árbol completo y el estado de cada pieza en `docs\phase_status.md`. Resumen:

```
StratOS-QXPro\
├── CLAUDE.md · ASSUMPTIONS.md · README.md · docker-compose.yml · .mcp.json
├── doc_app\                    (prompt maestro, transcripción, design tokens — contractual, solo lectura)
├── capturas_proyecto_dashboard\ (spec visual 1:1 — contractual, solo lectura)
├── .claude\skills\stratos-guardian\SKILL.md
├── mcp\stratos_mcp_server.py
├── config\thresholds.seed.json
├── core-engine\                (FastAPI; formulas/ y state_machines/ puros — G1-G5)
├── api-gateway\                (JWT, rate limit, WS broker — placeholder en G0, real en G5)
├── frontend\                   (React 18 + TS + Vite + Tailwind desde design_tokens.json — G6-G7)
├── mt5-connector\ · mt5-simulator\  (se crean en G4)
├── infra\                      (nginx, postgres init, prometheus)
├── scripts\seed.py · scripts\guardrails\pre_commit_scan.py
└── docs\ (phase_status.md, backlog.md, architecture.md, adr\)
```

## Fases de construcción

El proyecto se construye G0→G9 (`PROMPT_MAESTRO.md` PARTE 12): G0 Scaffold+gobierno · G1 Modelo de datos · G2 Fórmulas (TDD) · G3 Máquinas de estado · G4 mt5-connector+simulador · G5 core-engine (servicios/API/WS) · G6 Frontend shell+Resumen · G7 Frontend resto de pestañas · G8 Seed+E2E · G9 Hardening. Un PHASE REPORT cierra cada fase.
