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
mypy --config-file core-engine\pyproject.toml core-engine\src\ --strict

# Frontend
cd frontend; npm run build; npm run test

# Gobierno / anti-hardcoding
python scripts\guardrails\pre_commit_scan.py < payload.json   # hook de pre-commit
# MCP stratos (una vez registrado en .mcp.json y con la sesión de Claude Code reiniciada):
#   get_thresholds | get_module_spec | get_design_tokens | get_formula_signature
#   get_acceptance_criteria | get_seed_scenario | scan_hardcoding | get_project_status
```

## Seed y escenarios

`scripts\seed.py` puebla el portfolio completo de PARTE 13 contra Postgres+Redis reales: 32 bots de producción con historia de trades determinista (~15.500 trades, DD/retorno/correlación calibrados contra las fórmulas reales), ~25 candidatos de cantera F1-F6, 9 lápidas de Graveyard, y los escenarios del enunciado (posición sin SL, trades huérfanos, bot muerto/desbocado, impulsos, noticias HIGH). Los estados derivados (semáforo, veredicto de pipeline, correlaciones, auditoría) los calcula invocando los sweeps REALES de `core/services/*` sobre esos datos crudos — nunca se escriben a mano.

```powershell
# Requiere Postgres+Redis arriba (docker compose up -d postgres redis) y el
# esquema migrado (alembic -c core-engine\alembic.ini upgrade head).
python scripts\seed.py --profile full --reset          # ~5,5 años de historia, cifras de PARTE 13
python scripts\seed.py --profile ci --reset             # ~4 meses, para iterar rápido en desarrollo/CI
python scripts\seed.py --profile full --reset --inject-audit-error   # fuerza un descuadre contable (criterio 6)

# Crea además un usuario de login para el harness E2E si estas dos variables
# están en el entorno (nunca hardcodeadas, no-op silencioso si faltan):
$env:PLAYWRIGHT_TEST_EMAIL = "tu-email@ejemplo.local"
$env:PLAYWRIGHT_TEST_PASSWORD = "tu-contraseña"
```

Sin `--reset`, una segunda corrida del mismo perfil no hace nada (`SystemConfig["seed_profile"]` ya marcado) — protege un `docker compose up` repetido en desarrollo. El seed se auto-verifica al cerrar (`header_state.py`): si algo queda incoherente, aborta con `AssertionError` en vez de dejar datos a medias.

Aproximaciones documentadas (no se persiguen las cifras literales exactas de PARTE 13 al céntimo — ver `ASSUMPTIONS.md`, sección G8): recuento de trades/lotes sellados, DD máximo, beta contra el S&P 500 sintético post-2021, y el estado semáforo del resto del roster fuera de Poseidón/Vega (citados por nombre en el enunciado).

## End-to-end (Playwright)

11 specs (`frontend\tests\e2e\*.spec.ts`) cubren las 11 pestañas + un flujo operativo compuesto (confirmar decisión → firmar checklist → registrar impulso). Corren contra los dev servers reales (`uvicorn` + `vite`), no contra `docker compose`.

```powershell
# 1. Sembrar (perfil ci es mas rapido para iterar) con el usuario de prueba:
$env:PLAYWRIGHT_TEST_EMAIL = "e2e@stratos.local"; $env:PLAYWRIGHT_TEST_PASSWORD = "una-contraseña-cualquiera"
python scripts\seed.py --profile ci --reset

# 2. Arrancar ambos servidores (en dos terminales, o en background)
.venv\Scripts\python -m uvicorn core.main:app --app-dir core-engine/src --port 8100
cd frontend; npm run dev -- --port 5175 --strictPort

# 3. Correr los specs (mismas credenciales que el paso 1)
cd frontend
npx playwright install --with-deps chromium   # solo la primera vez
npx playwright test --workers=1               # serial: el screenshot-diff es sensible a la contención de CPU en paralelo
```

Sin `PLAYWRIGHT_TEST_EMAIL`/`PLAYWRIGHT_TEST_PASSWORD`, los specs se saltan solos (`test.skip`) — no hay credenciales por defecto en el repo. En CI (`.github/workflows/ci.yml`, jobs `e2e-playwright`/`e2e-acceptance-full`) los 3 pasos ya están automatizados.

## Calendario de decisiones (resumen)

PARTE 14 define el ritmo operativo completo (instalación, backups, rotación de claves — eso vive en `docs\runbook.md`, pendiente de G9/hardening). El calendario en sí, sí construido y verificable hoy contra el seed:

- **Domingo (20 min, mercado cerrado)**: revisión técnica (errores de EA, desconexiones, órdenes rechazadas) + copiar noticias de la semana al filtro horario. La vista dominical **nunca** muestra rentabilidad — ítem de checklist, sin UI dedicada todavía (`docs\backlog.md`).
- **Cada 15 días**: semáforos vs baseline; confirmar los AMARILLO al 50 % de sizing.
- **Primer domingo del mes**: bots vs backtest (rebalanceo si |Δ|>10 pp); correlaciones; ejecutar el retiro mensual (nunca un impulso — nómina, sin excepción aunque el mes sea negativo).
- **Trimestral**: robustez, alpha decay, coste de impulsos.
- **Enero**: reestructuración anual (pares redundantes, contratos Monte Carlo, overstay de challengers).

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
├── core-engine\                (FastAPI; formulas/+state_machines/ puros, servicios, API 9.x, WS, Telegram — G1-G5)
├── api-gateway\                (placeholder: el frontend habla directo con core-engine, decisión G5-00/G6-00)
├── frontend\                   (React 18 + TS + Vite + Tailwind desde design_tokens.json — G6-G7, 11 pestañas)
├── mt5-connector\ · mt5-simulator\  (conector Windows read-only + simulador de escenarios — G4)
├── shared-ingest-seal\         (sellado SHA-256 stdlib-only, compartido por core-engine y mt5-connector — G4)
├── infra\                      (nginx, postgres init, prometheus)
├── scripts\seed.py · scripts\seed_lib\ · scripts\guardrails\pre_commit_scan.py  (seed real, G8)
└── docs\ (phase_status.md, backlog.md, architecture.md, adr\)
```

## Fases de construcción

El proyecto se construye G0→G9 (`PROMPT_MAESTRO.md` PARTE 12): G0 Scaffold+gobierno · G1 Modelo de datos · G2 Fórmulas (TDD) · G3 Máquinas de estado · G4 mt5-connector+simulador · G5 core-engine (servicios/API/WS) · G6 Frontend shell+Resumen · G7 Frontend resto de pestañas · G8 Seed+E2E · G9 Hardening. Un PHASE REPORT cierra cada fase.
