# CLAUDE.md — StratOS-QXPro

Panel maestro de gestión de portfolios de bots MT5. Réplica production-grade del sistema del vídeo
(`doc_app\transcripcion_video_SIN__minutaje_donde_explica_funcionamiento_StratOS-13.md`).
La especificación contractual completa está en `doc_app\PROMPT_MAESTRO.md` (PARTES 0–17). Léela antes de cualquier fase.

## Fuentes de verdad (en este orden)

1. `doc_app\PROMPT_MAESTRO.md` — spec funcional y técnica (15 partes + skill/MCP).
2. `capturas_proyecto_dashboard\*.jpg` — spec VISUAL 1:1 de 10 pestañas (léelas con Read antes de tocar UI).
3. MCP `stratos` — umbrales, tokens, specs y criterios consultables en caliente (PARTE 17).
4. `ASSUMPTIONS.md` — decisiones tomadas ante ambigüedades (apéndice continuo).

## Reglas operativas inquebrantables

- **CERO HARDCODING** (P11): umbrales → `SystemConfig`; despliegue → `Settings`/env; colores y espaciados → `doc_app\design_tokens.json` (Tailwind se genera desde ahí); textos de UI → `frontend\src\styles\ui_strings.es.json`; plantillas de instrucción → `instruction_templates` en config. Antes de escribir una función, decide dónde vive cada literal. Antes de cada commit de fase: `scan_hardcoding` (MCP) limpio o justificado en `ASSUMPTIONS.md`.
- **Conector MT5 read-only**: jamás se envían órdenes. El sistema instruye; el humano ejecuta y confirma (Confirmar/Posponer/Descartar).
- **Inmutabilidad**: `DecisionLog` (hash-chain), `IngestBatch` (sello SHA-256 por lote), `SemaphoreTransition`, `KillSwitchEvent`, `WithdrawalLog`, `ChecklistRun` son append-only (permisos BBDD sin UPDATE/DELETE).
- **Cero datos manuales de trading**: todo trade entra por ingesta con `(account_id, magic_number)`.
- **Fidelidad visual 1:1**: ninguna desviación de las capturas sin ADR en `docs\adr\`. Cuentas/EA no tiene captura: seguir spec 7.2 (diseño derivado).
- **TDD** en `formulas/` y `state_machines/` (rojo→verde→refactor). Cobertura ≥95 % en esos módulos, ≥85 % en el resto del core.
- **Idioma**: código/comentarios en inglés; docstrings, docs y textos UI en español (literales de capturas EXACTOS).

## Workflow por fases

El proyecto se construye en fases G0→G9 (PARTE 12 del prompt maestro). En cada fase:
1. Plan mode → plan de archivos → aprobación del operador.
2. Implementación en commits pequeños (conventional commits: `feat(core): ...`, `test(formulas): ...`, `fix(frontend): ...`).
3. `scan_hardcoding` + tests + lint antes de cerrar.
4. PHASE REPORT: archivos, tests, criterios de salida verificados, assumptions nuevos, screenshot-diff si toca UI.

## Comandos

```powershell
# Backend
cd core-engine; uvicorn src.core.main:app --reload --port 8000
pytest core-engine\tests -q                 # suite backend
pytest core-engine\tests -k formulas -q     # solo fórmulas
alembic -c core-engine\alembic.ini upgrade head

# Frontend
cd frontend; npm run dev                    # Vite dev server
npm run test; npm run e2e                   # Vitest / Playwright

# Infra
docker compose up -d postgres redis
python scripts\seed.py --profile full       # seed completo (32 bots, 15.486 trades)
python scripts\seed.py --inject-audit-error # escenario de discrepancia 0,02 %

# Gobierno
# MCP stratos: get_thresholds | get_module_spec | get_design_tokens |
#              get_formula_signature | get_acceptance_criteria | scan_hardcoding
```

## Estructura del repo

```
stratos-qxpro/                 (raíz = C:\BOTS\SCRIPTS\StratOS-QXPro)
├── CLAUDE.md · ASSUMPTIONS.md · README.md · docker-compose.yml · .mcp.json
├── doc_app\                   (prompt maestro, transcripción, design tokens)
├── capturas_proyecto_dashboard\
├── .claude\skills\stratos-guardian\SKILL.md
├── mcp\stratos_mcp_server.py
├── mt5-connector\             (Windows, read-only, buffer SQLite, sellos SHA-256)
├── mt5-simulator\             (escenarios: crash_21, bot degradado, sin SL, cortes)
├── core-engine\               (FastAPI; formulas/ y state_machines/ puros)
├── api-gateway\               (JWT, rate limit, WS broker)
├── frontend\                  (React 18 + TS + Vite + Tailwind desde tokens)
├── scripts\seed.py · scripts\data\sp500_monthly.csv
├── config\thresholds.seed.json · config\small_scale.yaml
├── docs\ (runbook.md, adr\, architecture.md, screenshots\)
└── infra\ (nginx, postgres init, prometheus)
```

## Dominio en 30 segundos

32 bots reales + cantera en demo. Semáforos VERDE/AMARILLO/NARANJA por bot contra baseline (AMARILLO = sizing 50 %; NARANJA = paper hasta 30 trades limpios). Kill-switch de portfolio en 8/12/15/20 % de DD (desescalado solo firmado, histéresis 2 pp). Pipeline F1–F7 con gate automático de 7 criterios desde F4 (PF>1,5 · exp>0,15R · Sharpe>1 · DD<20 % · ≥30 trades · ≥60 días · ≥2 trades/sem; WFE≥0,5 en F2). Rotación champion/challenger por slot (5 criterios, Sharpe ×1,22, p<0,05; overstay 6 meses). Monte Carlo 300 sims → contrato de DD (P95); superarlo = incumplimiento → NARANJA. Correlación media 0,16; par >3× media = redundante. Auditoría balance+flujos=balance (tol. 0,01 %) con lotes sellados SHA-256. Diario de impulsos con contrafactual a 7 días. Retiro mensual-nómina sin excepción. Escalado UMS en 6 fases (equity/riesgo/Kelly en config). Cementerio: re-validación solo desde F3, jamás reactivación directa.
