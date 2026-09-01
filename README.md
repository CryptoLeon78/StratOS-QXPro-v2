# StratOS-QXPro

Panel maestro de gestión de portfolios de bots de trading MetaTrader 5. Réplica production-grade del sistema mostrado en el vídeo de referencia (`doc_app\transcripcion_video_SIN__minutaje_donde_explica_funcionamiento_StratOS.md`): semáforos de salud por bot, kill-switch de portfolio, pipeline de validación F1→F7, rotación champion/challenger, auditoría inmutable con sellado SHA-256, escalado UMS y diario de impulsos.

La especificación contractual completa está en [`doc_app\PROMPT_MAESTRO.md`](doc_app/PROMPT_MAESTRO.md) (PARTES 0–17). Léela antes de tocar cualquier fase. El estado de avance vive en [`docs\phase_status.md`](docs/phase_status.md); las decisiones ante ambigüedades, en [`ASSUMPTIONS.md`](ASSUMPTIONS.md). El estado de las garantías (CI, tests, lint) y la deuda abierta, en [`docs\AUDITORIA_2026-09-02.md`](docs/AUDITORIA_2026-09-02.md); el orden de trabajo hacia producción, en [`docs\PLAN_CONTINUACION_2026-09-02.md`](docs/PLAN_CONTINUACION_2026-09-02.md). Los agentes leen [`AGENTS.md`](AGENTS.md) (Codex) o [`CLAUDE.md`](CLAUDE.md) (Claude) antes de tocar nada.

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

## Stack operacional (G13)

El stack operacional está aislado de G12 y no admite fixtures. Cree una configuración nueva con secretos propios en `.env.operational` a partir de `.env.operational.example`; no copie secretos ni URLs de una campaña anterior. Declare las rutas privadas en `runtime\operational\sources.yaml` a partir de `config\operational_sources.example.yaml`.

```powershell
# No ejecutar seed: DEPLOYMENT_PROFILE=operational lo rechaza expresamente.
docker compose -p stratos_operational -f docker-compose.yml -f docker-compose.operational.yml --env-file .env.operational up -d
.venv\Scripts\python.exe -m alembic -c core-engine\alembic.ini upgrade head

# Inventario de Análisis: sólo escribe un manifiesto; --apply requiere la
# base operacional ya migrada y persiste eventos de admisión append-only.
$env:PYTHONPATH = "core-engine\src"
.venv\Scripts\python.exe scripts\operational_inventory.py --root "C:\ruta\privada\Analisis" --source-group ANALYSIS --manifest runtime\operational\analysis-inventory.json
```

Para validar una pareja admitida de Análisis con el Strategy Tester, use el
lanzador operacional. Antes, construya el prefiltro: usa los mínimos únicos de
`config\thresholds.seed.json`, excluye hashes ya probados y sólo genera cola
cuando existen evidencias selladas de Monte Carlo P95 y costes por sesión. La
razón OOS/IS de WFM se conserva como `DERIVED_UNMAPPED`: es informativa y no
activa el gate F2 mientras no haya una equivalencia validada o evidencia
forward/MT5 correspondiente.
Una frecuencia menor a dos trades semanales se marca para revisión, pero no se
descarta si supera el mínimo contractual de trades. La plantilla de evidencia
es `config\operational_quality_evidence.example.json`; sus rutas reales se
guardan fuera de Git.

```powershell
$env:PYTHONPATH = "core-engine\src;scripts"
.venv\Scripts\python.exe scripts\resolve_operational_validation_sources.py `
  --inventory runtime\operational\analysis-inventory.json `
  --projects-root "C:\ruta\privada\user\projects" `
  --output runtime\operational\analysis-validation-sources.json

# El resolutor exige SHA exacto o firma histórica SQX (orders.bin +
# lastSettings.xml); si varias copias coinciden, usa el linaje de la carpeta
# de Análisis y retiene cualquier resultado que no sea único.
.venv\Scripts\python.exe scripts\extract_operational_validation_evidence.py `
  --sources-manifest runtime\operational\analysis-validation-sources.json `
  --thresholds config\thresholds.seed.json `
  --output runtime\operational\analysis-validation-evidence.json

# El extractor verifica el hash de cada SQX usado y registra el pase SQX como
# STATIC_VALIDATED_WFM, con la tarea y criterios reales de project.cfx. Conserva
# la razón OOS/IS de la celda WFM como DERIVED_UNMAPPED; Monte Carlo se recalcula
# de RETEST OOS con mc_sims/mc_seed y los costes se leen del Setup efectivo de
# lastSettings.xml. No usa nombres de carpetas como veredicto.
.venv\Scripts\python.exe scripts\operational_prefilter.py `
  --inventory runtime\operational\analysis-inventory.json `
  --quality-evidence runtime\operational\analysis-validation-evidence.json `
  --completed-backtests runtime\operational\backtests `
  --output runtime\operational\analysis-prefilter.json
```

El primer comando de Tester es sólo preflight; `--launch` es el
único que compila el EA y abre MT5 para el Tester. El lanzador no despliega,
no consulta `terminal_despliegue`, requiere AutoTrading desactivado, ticks
reales de todo el rango y que la instancia de backtest esté cerrada. Nunca
cierra procesos por sí mismo.

```powershell
$panel = "C:\ruta\a\SQX_vs_MT5_Panel"
$sqx = "C:\ruta\privada\Analisis\candidate.sqx"
$mq5 = "C:\ruta\privada\Analisis\candidate.mq5"
$terminal = "terminal_backtest configurado en SQX_vs_MT5"

# Preflight sellado, sin compilar ni iniciar MT5.
.venv\Scripts\python.exe scripts\run_operational_sqx_mt5_backtest.py `
  --panel-dir $panel --sqx $sqx --mq5 $mq5 `
  --output-root runtime\operational\backtests `
  --expected-terminal $terminal --allow-real-strategy-tester

# Sólo tras un preflight correcto y con la instancia objetivo cerrada.
# Añada --launch al mismo comando para abrir el Strategy Tester.
# Si la instancia objetivo quedó abierta, --manage-backtest-terminal solicita
# únicamente su cierre limpio; no mata procesos ni toca otras instalaciones MT5.
```

JJTI y BEPB son observabilidad read-only. El exportador `mt5-connector\mql5\StratOSHistoryExport.mq5` sólo puede usarse para generar CSV de histórico con `HistorySelect`/`HistoryDealGet*`; no envía ni modifica órdenes. Ningún EA se adjunta a la Incubadora hasta que un candidato tenga resultado reproducible de `SQX_vs_MT5`, baseline importada y plaza libre dentro del límite de ocho.

Para cuentas reales externas, el alta de cuenta y la recuperación de evidencia
están separadas del alta F7 del bot: no se infiere perfil, sizing o identidad
de EA desde un filename o un deal aislado.

```powershell
# Sólo registra la cuenta como BROKER_REAL; no crea bots ni toca MT5.
docker compose -p stratos_operational -f docker-compose.yml -f docker-compose.operational.yml --env-file .env.operational run --rm -T --no-deps `
  --volume "${PWD}:/workspace:ro" core-engine python /workspace/scripts/register_external_account.py `
  --login <login> --account-name <name> --broker Darwinex --server Darwinex-Live --currency USD --apply

# Descarga un fichero existente vía SSH/SFTP en lectura y conserva sus bytes.
.venv\Scripts\python.exe scripts\fetch_mt5_history_artifact.py `
  --bridge-root "C:\BOTS\Versiones\SQX_144_Full2\Apps_entorno_SQX\mt5_bridge" `
  --terminal contabo_jjti --remote-mql5-path "Files\Detallado_....csv" `
  --output-dir runtime\operational\history\JJTI
```

Los `Detallado_*` heredados se guardan como artefactos `MT5_DETAILED_LEGACY`
sellados y nunca se convierten en trades si les falta `DEAL_ENTRY`. El CSV
canónico de `StratOSHistoryExport.mq5` conserva `position_id`, entrada/salida
y ticket; sólo ese formato puede pasar a `import_mt5_history_export.py`.

### Ejecutable guiado para nuevos candidatos

`dist\StratOS_Operational.exe` es un asistente de consola para el host
operacional, no un ejecutable autónomo: usa el repositorio, `.venv`, Docker y
el terminal Darwinex que ya están configurados localmente. La primera vez se
genera la configuración privada (sin secretos en el binario):

```powershell
Copy-Item config\operational_launcher.example.json runtime\operational\launcher.json
notepad runtime\operational\launcher.json

# Sólo inventario, evidencias y prefiltro: no abre MT5.
dist\StratOS_Operational.exe --refresh-only

# Modo guiado: solicita escribir SI antes de CADA backtest MT5.
dist\StratOS_Operational.exe
```

Al terminar cada Tester correcto, el asistente localiza su manifiesto sellado y
lo registra append-only en `stratos_operational`. La Incubadora permanece
explícitamente bloqueada: esta versión no adjunta EAs ni puede enviar órdenes;
se habilitará sólo tras registrar una cuenta `BROKER_DEMO`, implementar el
attach por gráfico y validar su contrato de riesgo. Para reconstruir el binario
tras cambios: `powershell -ExecutionPolicy Bypass -File scripts\build_stratos_operational_exe.ps1`.

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

PARTE 14 define el ritmo operativo completo (instalación, backups, rotación de claves — eso vive en `docs\runbook.md`, construido en G9). El calendario en sí, sí construido y verificable hoy contra el seed:

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
├── api-gateway\                (proxy transparente, rate-limit y broker WebSocket; G9)
├── frontend\                   (React 18 + TS + Vite + Tailwind desde design_tokens.json — G6-G7, 11 pestañas)
├── mt5-connector\ · mt5-simulator\  (conector Windows read-only + simulador de escenarios — G4)
├── shared-ingest-seal\         (sellado SHA-256 stdlib-only, compartido por core-engine y mt5-connector — G4)
├── infra\                      (nginx, postgres init, prometheus)
├── scripts\seed.py · scripts\seed_lib\ · scripts\guardrails\pre_commit_scan.py  (seed real, G8)
└── docs\ (phase_status.md, backlog.md, architecture.md, adr\)
```

## Fases de construcción

El plan contractual G0→G9 (`PROMPT_MAESTRO.md` PARTE 12) está cerrado, igual que el cierre de huecos G10. G11 cerró coherencia documental, determinismo de fixtures, trazabilidad de datos y reporter v1.1. G12 levantó la campaña de validación demo aislada (`stratos_g12`) y G13 —la fase activa— construye el stack operacional real/incubadora/análisis (`stratos_operational`), con procedencia persistente, admisión append-only y comparación SQX↔MT5 a tick real. El estado vivo está en `docs\phase_status.md`; la auditoría de garantías, en `docs\AUDITORIA_2026-09-02.md`. Un PHASE REPORT cierra cada bloque.
