# PROMPT MAESTRO v3.0 — "StratOS-QXPro"
## Plataforma profesional de gestión de portfolios de trading bots (MetaTrader 5)
### Edición Claude Code — con diseño 1:1 donde compara bots en demo que estan validandose sobre su historial de trades y se comparan contra los de la cuenta real , anti-hardcoding, skill y MCP dedicados

> **Destinatario**: Claude Code (CLI agentic coding) trabajando en el repo local del operador.
> **Cómo usar**: coloca este archivo en `C:\BOTS\SCRIPTS\StratOS-QXPro\doc_app\PROMPT_MAESTRO.md`,
> arranca Claude Code en `C:\BOTS\SCRIPTS\StratOS-QXPro\` y di: *"Lee doc_app\PROMPT_MAESTRO.md y arranca en la FASE G0"*.
> `CLAUDE.md`, `.claude\skills\stratos-guardian\SKILL.md`, `mcp\stratos_mcp_server.py` y `doc_app\design_tokens.json`
> se instalan en G0 desde los archivos entregados junto a este prompt.

---

## PARTE 0 — CONTEXTO DE EJECUCIÓN EN CLAUDE CODE

### 0.1. Archivos de referencia locales (LEER ANTES DE CODIFICAR)

```
C:\BOTS\SCRIPTS\StratOS-QXPro\
├── doc_app\
│   ├── PROMPT_MAESTRO.md                  ← este documento
│   ├── design_tokens.json                 ← tokens de diseño contractual (PARTE 11)
│   └── transcripcion_video_SIN__minutaje_donde_explica_funcionamiento_StratOS-13.md
│                                          ← fuente de verdad funcional (vídeo original)
├── capturas_proyecto_dashboard\           ← fuente de verdad VISUAL 1:1
│   ├── pestana-Resumen-3.jpg
│   ├── pestana-Portfolio-2.jpg
│   ├── pestana-Riesgo-4.jpg
│   ├── pestana-Salud-5.jpg
│   ├── pestana-Auditoria-6.jpg
│   ├── pestana-Bots-7.jpg
│   ├── pestana-Ejecucion-8.jpg
│   ├── pestana-Escalado-9.jpg
│   ├── pestana-Graveyard-10.jpg
│   ├── pestana-Pipeline_parte_Paper-12.jpg
│   ├── pestana-Pipeline_parte_CapitalReal-11.jpg
│   └── pestana-Pipeline_parte_Paper-CapitalReal.jpg
└── (el repo se genera aquí)
```

Reglas de uso de referencias:
- Antes de implementar CUALQUIER vista, lee la captura correspondiente con la herramienta Read y reproduce su layout, textos literales, densidad y jerarquía. La captura manda; este documento resuelve lo que la captura no muestra (estados vacíos, responsive, errores).
- No existe captura de la pestaña **Cuentas/EA**: su spec completa está en 7.2 (diseño original documentado, marcado como "diseño derivado, sin captura de referencia").
- La transcripción del vídeo es la fuente de verdad de negocio: cifras, ejemplos y filosofía citados en este documento provienen de ahí.

### 0.2. Modo de trabajo (comportamiento del agente)

1. **Plan antes de código**: al inicio de cada fase, entra en plan mode y presenta el plan de archivos. No escribas código de una fase sin plan aprobado.
2. **TDD estricto**: en `formulas/` y `state_machines/` escribe primero los tests (rojo), luego la implementación (verde), luego refactor. En el resto, tests en el mismo commit que el código.
3. **Commits por unidad**: un commit por componente/módulo completado, mensaje conventional commits (`feat(core): semaphore state machine`), nunca commits gigantes de fase entera.
4. **PHASE REPORT** al cerrar cada fase: (a) archivos creados, (b) tests ejecutados y resultado, (c) criterios de salida verificados uno a uno, (d) entradas nuevas en `ASSUMPTIONS.md`, (e) screenshot-diff visual si la fase toca UI (PARTE 12).
5. **Subagentes**: usa subagentes para (a) generación de tests una vez definida una interfaz, (b) escaneo anti-hardcoding antes de cada commit de fase, (c) verificación visual contra capturas. El hilo principal conserva el contexto de arquitectura.
6. **Anti-alucinación**: prohibido inventar APIs, paquetes o firmas. Si dudas de la API del paquete `MetaTrader5` o de TimescaleDB, declara la incertidumbre en `ASSUMPTIONS.md` y usa la forma más documentada. Todo umbral numérico debe ser trazable a este documento o a `SystemConfig`.
7. **Ambigüedad**: ambigüedad no bloqueante → `ASSUMPTIONS.md` (`[ID] decisión + justificación, 1 línea`) y continúa. Solo detente a preguntar si bloquea una decisión de arquitectura (máx. 5 preguntas, antes de escribir código, nunca a mitad de fase).
8. **Idioma**: identificadores y comentarios en inglés; docstrings, README, runbook y textos de UI en español (los literales de UI de las capturas se respetan EXACTOS); logs en inglés estructurado.
9. **Skill y MCP del proyecto**: en G0 instalas la skill `stratos-guardian` y el MCP `stratos` (PARTE 16). Úsalos: la skill se invoca sola cuando toques semáforos/kill-switch/pipeline/fórmulas/UI; el MCP es tu fuente consultable de umbrales, tokens, specs y criterios.

### 0.3. REGLA OPERATIVA CERO-HARDCODING (comportamiento, construcción y planificación)

Esta regla gobierna TODAS tus decisiones como agente, no solo el código:

- **En planificación**: antes de escribir una función, pregunta "¿qué números, textos, rutas, colores o umbrales lleva dentro?" y decide dónde vive cada uno (SystemConfig / settings / design_tokens.json / i18n / constante de módulo nombrada). Si no tiene hogar declarado, no se escribe.
- **En construcción**: prohibido cualquier literal mágico en lógica. Umbrales → `SystemConfig` (BBDD, con default). Parámetros de despliegue → `Settings` (env). Colores/espaciados/tipografía → `design_tokens.json` importado (Tailwind theme se GENERA desde ese JSON; ningún color suelto en componentes). Textos de UI → catálogo `ui_strings.es.json`. Plantillas de instrucciones ("EA magic {magic}: desactivar…") → `instruction_templates` en config con interpolación.
- **Excepción permitida**: constantes matemáticas puras (p.ej. `TRADING_DAYS_PER_YEAR = 252`) como constante nombrada de módulo con comentario de justificación. Nunca un número desnudo inline.
- **En verificación**: antes de cada commit de fase, ejecuta la tool MCP `scan_hardcoding` sobre los archivos tocados. Todo hallazgo se corrige o se justifica en `ASSUMPTIONS.md`.
- **En comportamiento**: si el operador te pide "cambia el umbral X a Y", NO editas el valor en código: verificas que vive en config y cambias el default en un solo sitio (migración o seed de SystemConfig). Si encuentras el valor duplicado en varios sitios, lo refactorizas a fuente única antes de cambiarlo.

---

## PARTE 1 — CONTEXTO Y FILOSOFÍA (fuente: transcripción del vídeo)

Se construye la réplica production-grade de "StratOS", el panel que Ignacio Lago muestra pestaña a pestaña en el vídeo: una cuenta real desde el **4 de enero de 2021**, capital inicial **30.000 €**, equity actual **179.642,70 €**, **32 bots en producción** (>120 entre todas sus cuentas), operativa 24/7 en un **VPS en Alemania**, uptime 7 días **99,6 %**, y el operador **lleva meses sin tocar una orden**.

**Filosofía rectora**: la diferencia entre esto y una cuenta quemada no son los bots, es el sistema que los vigila. La rutina diaria son 10 minutos con el café mirando tres números: equity, drawdown y decisiones pendientes. Nada de gráficos de precio, indicadores, líneas de tendencia ni SMC. El sistema observa, calcula, decide y emite INSTRUCCIONES exactas; el humano ejecuta y confirma. El componente más peligroso del sistema es el propio operador, y el sistema existe también para proteger el portfolio de él (diario de impulsos, calendario, cementerio sin retorno).

**Cifras contractuales del sistema original** (validan seed y tests; viven en seed/config, nunca hardcodeadas en lógica):
- Track record: 37,31 % anual compuesto vs 11,90 % S&P 500 en 60 meses; beta 0,18; t-stat del alfa 3,42; 14 meses negativos de 66 (~1 de cada 5)
- DD máximo histórico del portfolio: 4,8 % en 5,5 años (kill-switch nunca activado); DD actual de referencia 0,4 %
- Retorno medio mensual 2,69 % vs max DD 4,76 % (base de la nómina mensual)
- Correlación media del portfolio 0,16 sobre 1.240 días; par redundante real: Lyra Scalper EURUSD vs Phoenix Scalper SP500 = 0,52 (3× la media, "medio gemelos")
- Estructura macro objetivo 40/40/20; foto real 45,7 / 32,6 / 21,7 (desviada pero dentro de banda)
- Semáforo en directo: Poseidón Trend GER40 (magic 118685), 12 días en naranja, PF rodante 1,18 vs baseline 1,94; Vega Grid GBPUSD amarillo 6 días, sizing al 50 %
- Monte Carlo: Atlas Trend EURUSD, DD histórico 2,20 %, P95 3,94 % → contrato firmado 3,9 %
- Pipeline: Estige Trend con PF 32,75 y 9 trades → RETENIDO; Sigma MR SPX con PF 2,6, 51 trades OOS, 95 días → GO a Staging al 10 %
- Impulsos: 3/trimestre, coste evitado 654,80 € (418 € + 236 €)
- Auditoría: balance inicial 30.000,00 + Σ flujos 147.616,18 = 177.616,18 reportado; descuadre 0,00 (0,00 %) sobre 15.486 operaciones; 137.296 lotes sellados SHA-256
- Watchdog: Atlas espera ~7 trades/mes y lleva 6; Lyra espera 58 y lleva 59; los 32 en verde técnico

---

## PARTE 2 — PRINCIPIOS NO NEGOCIABLES (P1–P12)

- **P1. CERO introducción manual de datos de trading**: todo trade entra desde MT5 vía conector, identificado por `(account_id, magic_number)` ("matrícula"). Entrada manual permitida solo para: metadatos de candidatos F1, impulsos, confirmaciones firmadas, checklists y noticias (fallback).
- **P2. Cálculo 100 % automático** en core-engine desde datos crudos del terminal.
- **P3. Alerta proactiva**: si un dato no cuadra, el sistema avisa antes de que el operador lo note (WebSocket + Telegram).
- **P4. Instrucciones, no opiniones**: instrucción exacta con magic number y acción concreta; el humano ejecuta y confirma (Confirmar / Posponer / Descartar). El conector es ESTRICTAMENTE READ-ONLY: jamás envía órdenes.
- **P5. Ninguna posición sin stop loss**: validación en cada snapshot; posición sin SL → alerta CRÍTICA inmediata.
- **P6. Inmutabilidad con sellado**: `DecisionLog` append-only con hash-chain; además, cada LOTE de ingesta se sella con SHA-256 + timestamp de servidor (tabla `IngestBatch`), como muestra la pestaña Auditoría ("los datos no pueden alterarse después de su recepción sin dejar rastro; los trades cerrados son inmutables"). Prohibido UPDATE/DELETE en tablas de auditoría, reforzado con permisos de BBDD.
- **P7. Testabilidad total**: core-engine funciona y se testea sin MT5 real (simulador G4).
- **P8. UTC interno / Europe-Madrid en UI; EUR como divisa base** (conversión vía `FxRate` si una cuenta opera en otra divisa).
- **P9. Idempotencia**: ingesta reejecutable sin duplicar; tolerancia a reinicios, reenvíos y dobles entregas.
- **P10. Degradación elegante**: si MT5 cae, el panel sigue con el último dato y lo marca ("DATOS STALE").
- **P11. CERO HARDCODING** (regla operativa 0.3): umbrales en SystemConfig, despliegue en Settings, diseño en design_tokens.json, textos en catálogo i18n, plantillas de instrucción en config. Un valor = una fuente.
- **P12. Fidelidad visual 1:1**: las 10 pestañas con captura se reproducen pixel-fieles en layout, textos y componentes (PARTE 11). Cualquier desviación necesaria se documenta como ADR en `docs/adr/`. Cuentas/EA sigue la spec 7.2.

---

## PARTE 3 — TOPOLOGÍA DE DESPLIEGUE (2 NODOS)

El paquete `MetaTrader5` solo funciona en Windows con la terminal instalada. Arquitectura de dos nodos (Wine documentado como NO recomendado, fuera de scope):

- **Nodo A — VPS Windows** (el VPS en Alemania del sistema original): 1..N terminales MT5 (mínimo REAL de producción + DEMO de cantera para validacion e incubacion) + `mt5-connector` como servicio de Windows (`install_service.ps1` con NSSM). El conector INICIA conexión outbound HTTPS hacia el Nodo B: cero puertos entrantes.
- **Nodo B — VPS Linux** (docker-compose): `core-engine`, `api-gateway`, `frontend` (React), `postgres` (16 + TimescaleDB), `redis` 7, `worker` + `scheduler` (ARQ), `nginx` (+Certbot), `prometheus`+`grafana` (perfil opcional).

```
┌─────────────────────┐                 ┌──────────────────────────────────┐
│   VPS WINDOWS (DE)  │   HTTPS +       │   VPS LINUX (docker-compose)     │
│  ┌───────────────┐  │   API key       │  ┌────────────┐   ┌───────────┐  │
│  │ MT5 REAL      │  │  (outbound      │  │ api-gateway│──▶│core-engine│  │
│  │ MT5 DEMO      │──┼─▶mt5-connector──┼─▶└─────┬──────┘   └─────┬─────┘  │
│  │ (cantera)     │  │  read-only,     │        │                │        │
│  └───────────────┘  │  buffer SQLite) │   ┌────▼─────┐   ┌──────▼─────┐  │
└─────────────────────┘                 │   │  nginx   │   │ postgres+  │  │
                                        │   └──────────┘   │ timescale  │  │
│  Operador ────────────────────────────┼─▶ https://panel  └────────────┘  │
                                        │   redis (cache+PS+broker ARQ)    │
└───────────────────────────────────────┘
```

| Origen | Destino | Protocolo | Auth | Propósito |
|---|---|---|---|---|
| mt5-connector | core `/ingest/*` | HTTPS REST | `X-API-Key` + TLS | trades, posiciones, equity, heartbeat, señales virtuales |
| api-gateway | core-engine | HTTP red docker | token de servicio | proxy/agregación |
| Navegador | api-gateway | HTTPS + WSS | JWT access+refresh | UI |
| core/worker | redis / postgres | TCP | password / roles | cache, Pub/Sub, broker; persistencia |
| core-engine | Telegram | HTTPS outbound | bot token | notificaciones |
| worker | noticias/benchmark | HTTPS o fichero | según proveedor | escudo y benchmark |

---

## PARTE 4 — STACK TÉCNICO (fijado)

- Python 3.12, FastAPI async, Pydantic v2 (`strict=True` en DTOs de ingesta), SQLAlchemy 2.0 async (`Mapped[]`) + Alembic, PostgreSQL 16 + TimescaleDB, Redis 7, **ARQ** (tareas + cron), WebSockets nativos, httpx async, structlog (JSON), Prometheus client, Sentry opcional, argon2-cffi, JWT (access 15 min + refresh 30 días con rotación).
- **Frontend (único, contractual)**: React 18 + TypeScript + Vite, TailwindCSS + shadcn/ui (tema generado desde `design_tokens.json`), TanStack Query, Zustand, Recharts + TradingView Lightweight Charts (solo equity/P&L), heatmap de correlaciones con canvas propio o plotly.js aislado, React Hook Form + Zod, react-router. **NO hay fase Streamlit**: el diseño de las capturas es contractual y Streamlit no puede fidelizarlo; el MVP visual es directamente React por pestañas (PARTE 12).
- Testing: pytest + pytest-asyncio + httpx + factory_boy + hypothesis; Vitest + RTL; Playwright (E2E + screenshot-diff contra capturas).
- CI: GitHub Actions (ruff, mypy strict en core, eslint, tsc, pytest, vitest, build imágenes).
- Docker multi-stage; docker-compose dev + override prod; Nginx + Certbot.
- Config: Pydantic Settings por entorno; `.env.example` completo; secretos fuera del repo.

---

## PARTE 5 — MODELO DE DATOS (SQLAlchemy 2.0 + TimescaleDB)

### 5.1. Enums

```python
BotProfile      = TREND | MOMENTUM | MEAN_REVERSION | GRID | SCALPING | SMART_MONEY | AI_ML
                  # 7 perfiles micro; mapeo a bloque macro en config (PARTE 10.3):
                  # CONVEXO = {TREND, MOMENTUM} · CONCAVO = {MEAN_REVERSION, GRID, SCALPING} · HIBRIDO = {SMART_MONEY, AI_ML}
BotRole         = CHAMPION | CHALLENGER
PipelinePhase   = F1 | F2 | F3 | F4 | F5 | F6 | F7 | PRODUCCION | CEMENTERIO
SemaphoreState  = VERDE | AMARILLO | NARANJA
AlertLevel      = INFO | SUAVE | CRITICA
BaselineSource  = BACKTEST | HISTORICO
Verdict         = GO | HOLD | KILL
TradeType       = BUY | SELL
ImpulseAction   = PAUSE_BOT | CLOSE_POSITION | INCREASE_RISK | DECREASE_RISK | OTHER
ImpulseStatus   = PENDING | EVALUATING | CLOSED
CemeteryCause   = ALPHA_DECAY | OVERFITTING | REGIME_CHANGE | BROKER_UNFAVORABLE
                  | OUTPERFORMED_BY_CHALLENGER | COMPETITIVE_NOT_SUPERIOR | OTHER
ChecklistType   = SUNDAY | BIWEEKLY | MONTHLY | QUARTERLY | ANNUAL
ActorType       = SYSTEM | HUMAN
NewsImpact      = LOW | MEDIUM | HIGH
DecisionStatus  = PENDING | CONFIRMED | POSTPONED | DISMISSED
```

### 5.2. Tablas

**Account**(id PK, name, broker, login, server, currency CHAR(3), is_demo BOOL, connector_instance_id, is_active BOOL DEFAULT TRUE)

**Bot**(id PK, account_id FK, magic_number INT, name, market, timeframe, profile BotProfile, role BotRole, slot TEXT NULL, pipeline_phase PipelinePhase, semaphore_state SemaphoreState DEFAULT VERDE, entered_state_at, capital_allocated_pct NUMERIC(5,2), risk_per_trade_pct NUMERIC(4,3), sizing_multiplier NUMERIC(4,2) DEFAULT 1.0, sizing_current_pct NUMERIC(4,2) DEFAULT 100.0, kelly_fraction NUMERIC(4,2) NULL, created_at, baseline_id FK NULL, UNIQUE(account_id, magic_number))
> `slot`: plaza de portfolio que ocupa un champion (p.ej. "trend-eurusd-h4"); la rotación darwiniana se evalúa challenger vs champion DEL MISMO slot. `entered_state_at` alimenta el contador "N días en estado/fase".

**Baseline**(id PK, bot_id FK, source, profit_factor, expectancy_r, sharpe, max_dd_pct, win_rate, payoff, avg_trade_duration_min, max_consec_losses, expected_trades_30d INT, dd_contract_pct, created_at, is_active) — versionada, append-only.

**Trade** — HYPERTABLE por `open_time`: (id BIGSERIAL, bot_id FK NULL, account_id FK, magic_number, ticket_mt5 BIGINT, symbol, open_time timestamptz, close_time NULL, type, volume, open_price, close_price NULL, sl NULL, tp NULL, profit, commission, swap, r_multiple NULL, ingest_batch_id FK, ingested_at, **UNIQUE(ticket_mt5, open_time)**)
> UNIQUE incluye la partición (exigencia TimescaleDB); dedupe real por ticket vía `ON CONFLICT DO NOTHING` + métrica `trades_duplicated_total`. `bot_id NULL` = huérfano. Compresión a 90 días; sin borrado.

**EquitySnapshot** — HYPERTABLE por `ts`: (ts, account_id FK, equity, balance, drawdown_pct, margin_level NULL, free_margin NULL, PK(ts, account_id)). Continuous aggregate `equity_daily`. Compresión a 30 días.

**HeartbeatLog** — HYPERTABLE por `ts`: (ts, connector_instance_id, account_id FK, latency_ms, status, PK(ts, connector_instance_id, account_id)). Retención 30 días.

**IngestBatch**(id PK, ts, connector_instance_id, account_id FK, batch_type TEXT, records INT, sha256 CHAR(64), server_ts)
> Sello por lote (pestaña Auditoría: "lotes sellados (hash+ts)"). El hash cubre el payload canónico del lote.

**Alert**(id PK, ts, level, module, message, action_required NULL, dedup_key NULL, resolved BOOL DEFAULT FALSE, resolved_at NULL, resolved_by NULL)

**Decision**(id PK, ts, module, title, description, instruction_text, evidence JSONB NULL, status DecisionStatus DEFAULT PENDING, decided_at NULL, decided_by NULL, postpone_until NULL)
> Alimenta "Requiere acción (N)" del Resumen y el badge de la cabecera. Los tres botones de la captura (Confirmar/Posponer/Descartar) escriben aquí y en `DecisionLog`.

**ImpulseLog**(id PK, ts, bot_id FK, description, desired_action ImpulseAction, executed BOOL DEFAULT FALSE, status ImpulseStatus DEFAULT PENDING, counterfactual_result_7d_eur NULL, avoided_cost_eur NULL, evaluated_at NULL)

**CemeteryEntry**(id PK, bot_id FK UNIQUE, retired_at, cause CemeteryCause, autopsy_text TEXT NOT NULL, lesson TEXT NOT NULL, revalidation_from_phase PipelinePhase DEFAULT F3, reactivation_blocked BOOL DEFAULT TRUE)
> Regla de oro según el banner del Graveyard: "Un bot retirado nunca se reactiva sin re-validación completa (**pipeline desde Fase 3**)". No es F1: la reincorporación exige repetir desde F3 (validación estadística) con identidad NUEVA (nuevo `Bot.id`), jamás resucitar el registro.

**PipelineCandidate**(id PK, bot_id FK UNIQUE, current_phase, entered_phase_at, incubation_days INT, oos_trades INT, profit_factor NULL, expectancy_r NULL, sharpe NULL, max_dd_pct NULL, wfe NULL, trades_per_week NULL, gates_passed INT DEFAULT 0, gates_total INT DEFAULT 7, provisional BOOL DEFAULT TRUE, verdict NULL, verdict_reason NULL, decision_eta_days INT NULL, evaluated_at NULL)
> `decision_eta_days` alimenta "Decisión habilitada en ~N días" / "Faltan N trades y N días" (proyección desde frecuencia observada).

**ChallengerEvaluation**(id PK, ts, challenger_bot_id FK, champion_bot_id FK, slot, criteria JSONB, passed BOOL, p_value NULL, notes TEXT)
> Rotación darwiniana: challenger en F6 >6 meses sin superar al champion → alerta OVERSTAY ("valorar retirar y liberar plaza").

**WithdrawalLog**(id PK, ts, amount, equity_before, checklist_completed JSONB)

**CorrelationMatrix**(id PK, ts, bot_a_id FK, bot_b_id FK, correlation, is_redundant_pair BOOL, window_days INT, UNIQUE(ts, bot_a_id, bot_b_id))

**MonteCarloRun**(id PK, bot_id FK, ts, n_simulations INT, dd_p50, dd_p75, dd_p95, dd_contract_pct, seed BIGINT)

**UmsPhaseLog**(id PK, ts, phase INT, equity_at, metrics JSONB, ready_to_advance BOOL)

**NewsEvent**(id PK, ts, currency CHAR(3), impact, title, source, blackout_before_min INT DEFAULT 30, blackout_after_min INT DEFAULT 30)

**ChecklistRun**(id PK, ts, checklist_type, period_key, items JSONB, completed BOOL, signed_by NULL, signature_hash NULL, UNIQUE(checklist_type, period_key))

**FxRate**(ts, base CHAR(3), quote CHAR(3), rate, PK(ts, base, quote))

**User**(id PK, email UNIQUE, hashed_password, role TEXT DEFAULT 'operator', created_at)

**DecisionLog** — APPEND-ONLY con hash-chain: (id BIGSERIAL PK, ts, actor, module, decision_type, payload JSONB, prev_hash CHAR(64), hash CHAR(64))

**SemaphoreTransition**(id PK, bot_id FK, ts, from_state, to_state, trigger_metrics JSONB, instruction_text, confirmed_at NULL, confirmed_by NULL)

**KillSwitchEvent**(id PK, ts, level INT, portfolio_dd_pct, actions JSONB, instruction_text, confirmed_at NULL, confirmed_by NULL)

**SystemConfig**(key TEXT PK, value JSONB, updated_at) — única fuente de umbrales (PARTE 10.3).

### 5.3. Índices
`Trade(bot_id, open_time DESC)`, `Trade(magic_number)`, `Alert(resolved, level)`, `Decision(status)`, `SemaphoreTransition(bot_id, ts DESC)`, `DecisionLog(module, ts DESC)`, `PipelineCandidate(current_phase)`.

---

## PARTE 6 — MÁQUINAS DE ESTADO FORMALES

Implementación: `core-engine/src/core/state_machines/` con transición = función pura `(state, event, metrics, config) -> TransitionResult`; persistencia aparte. Toda transición: historial + `DecisionLog` + evento Redis + `Alert`/`Decision` si aplica + Telegram según severidad.

### 6.1. Semáforo (por bot) — VERDE / AMARILLO / NARANJA

| Desde | Hasta | Guard (defaults en SystemConfig) | Acciones |
|---|---|---|---|
| VERDE | AMARILLO | `pf_rolling < 0.75×baseline` O `exp_rolling < 0.60×baseline` O `loss_streak > streak_p99(baseline)` O Page-Hinkley disparado | `sizing_current_pct=50`; Decision "Reducir sizing al 50% (bajar fraction Kelly). Aumentar frecuencia de revisión." |
| AMARILLO | VERDE | `pf_rolling ≥ 0.90×baseline` Y `exp_rolling ≥ 0.80×baseline` durante `semaphore_recovery_days` (10) | `sizing_current_pct=100`; INFO |
| AMARILLO | NARANJA | `pf_rolling < 0.60×baseline` O 15 días en AMARILLO sin recuperación O `dd_bot > 0.80×dd_contract` | Decision PAPER: "En el EA magic {magic}: desactivar apertura de nuevas posiciones (modo paper) y dejar cerrar las existentes por sus reglas."; CRITICA + Telegram |
| cualquiera | NARANJA | `dd_bot > dd_contract` (incumplimiento de contrato MC) | igual, `decision_type=CONTRACT_BREACH` |
| NARANJA | VERDE | 30 trades virtuales limpios Y `pf_virtual ≥ 0.90×baseline` Y `exp_virtual > 0` | reactivación con confirmación firmada |

Reglas: VERDE = "Mantener. No tocar nada." (ni subidas por buen mes). Contador de días en estado visible. Instrucción pendiente >24 h → recordatorio SUAVE diario. Trades virtuales de NARANJA: vía `/ingest/signals` del EA en modo señal; sin fuente virtual, el contador de 30 no avanza y la UI lo muestra ("contador congelado").

### 6.2. Kill-switch del portfolio (4 niveles, "cuadro de diferenciales")

| Nivel | DD portfolio | Texto UI (literal de captura) | Severidad |
|---|---|---|---|
| L1 | ≥ 8 % | "Notificar. Vigilar sin intervenir." | INFO + Telegram |
| L2 | ≥ 12 % | "Reducir sizing 50% en todos los bots." | CRITICA + Telegram |
| L3 | ≥ 15 % | "Cerrar todas las posiciones abiertas." | CRITICA + Telegram |
| L4 | ≥ 20 % | "Cerrar posiciones y DESACTIVAR todos los EAs." | CRITICA + Telegram |

Escalado automático (detección → instrucción + registro); desescalado solo manual con DD < umbral − 2 pp de histéresis Y firma. DD calculado sobre equity agregado de cuentas REALES. Nota de UI (literal): "El panel avisa e instruye; la ejecución de cierres vive en MetaTrader". Referencia visible: "KS L0: Sin activación" / DD máx histórico 4,8 %.

### 6.3. Pipeline F1→F7 + rotación champion/challenger + CEMENTERIO

Fases (literales de la captura): **F1 Ideación y prototipado → F2 Filtrado de robustez → F3 Validación estadística → F4 Forward testing → F5 Incubación OOS → F6 Staging (10% sizing) → F7 Producción (Champion)**.

- **F1–F3 (paper)**: metadatos + backtest. La puerta de F2 exige robustez de backtest: **WFE (walk-forward efficiency) ≥ 0,5** (lección de Caronte: "endurecer el mínimo de WFE a 0,5 antes de staging"), Monte Carlo de backtest sin ruina en P95, y costes realistas por sesión para scalpers (lección de Ligeia).
- **Gate de 7 criterios (desde F4, automáticos, calculados con datos MT5 de la cuenta DEMO)** — la UI muestra "Gate: X/7 criterios":

| # | Criterio | Default |
|---|---|---|
| 1 | Profit Factor | > 1,5 |
| 2 | Expectancy por operación | > 0,15R |
| 3 | Sharpe | > 1 |
| 4 | Max Drawdown | < 20 % |
| 5 | Muestra | ≥ 30 trades OOS (PF 32,75 con 9 trades = RETENIDO) |
| 6 | Incubación | ≥ 60 días (referencia GO: 95 días / 51 trades) |
| 7 | Frecuencia | ≥ 2 trades/semana (alerta literal: "Frecuencia <2 trades/semana: mínimo absoluto 30 trades con fiabilidad estadística baja") |

- Veredicto: GO (7/7), HOLD (muestra/tiempo insuficiente o 1 criterio marginal <10 % del umbral), KILL (≥2 fallan, o maxDD ≥20 %, o PF <1,1). Badge PROVISIONAL mientras la muestra < mínimo absoluto.
- **F6 Staging**: entra al 10 % del tamaño objetivo; escalado 10→25→50→100 % con ≥20 trades y gate re-verificado en cada salto. Validador de sizing global: activar un bot que empuje el sizing total >89 % → HOLD con motivo `SIZING_CAP`.
- **Rotación darwiniana (champion/challenger)**: un challenger en F6 que aspire a un slot ocupado debe superar **5 criterios** frente al champion (referencia real: "Helios superó los 5 criterios en la evaluación de febrero — Sharpe ×1,22, p=0,03 — rotación limpia: mismo slot, correlación 0,31"): Sharpe ≥ 1,22× champion, significación estadística p < 0,05, correlación con el bloque no superior, maxDD no superior, expectancy no inferior. Victoria → champion al CEMENTERIO con causa `OUTPERFORMED_BY_CHALLENGER` y el challenger ocupa el slot. **OVERSTAY**: challenger >6 meses en F6 sin superar al champion → alerta "Competitivo pero no superior — valorar retirar y liberar plaza" (regla de los 6 meses).
- **CEMENTERIO**: autopsia escrita OBLIGATORIA (causa + lección, NOT NULL) antes de archivar. Reactivación: API 409 siempre; sin control en UI; reincorporación solo como candidato NUEVO desde F3 (`revalidation_from_phase`). Causas reales del seed: alpha decay, overfitting, cambio de régimen (BoJ / Page-Hinkley), broker desfavorable (spread nocturno 0,19R→0,04R), superado por challenger, competitivo pero no superior.

---

## PARTE 7 — LAS 11 PESTAÑAS (spec funcional + visual)

La app es una SPA con cabecera persistente y 11 pestañas: **Resumen · Cuentas/EA · Pipeline · Bots · Portfolio · Salud · Riesgo · Ejecución · Escalado · Graveyard · Auditoría**. Título: "Panel Maestro de Portfolio — Copiloto de decisiones · StratOS". Badge de rol arriba a la derecha ("Ingeniero"). Cada pestaña indica: objetivo / datos / jobs / endpoints / eventos / spec visual (captura de referencia) / reglas / casos límite. La lógica vive SIEMPRE en core-engine.

### 7.1. Resumen — `capturas\pestana-Resumen-3.jpg`
- **Cabecera global persistente (6 tarjetas, en TODAS las pestañas)**: EQUITY (179.642,70) · P&L DÍA (+37,36; subtexto "Sem: 2.444,14 · Mes: 10.525,70") · DRAWDOWN (0,4 %; subtexto "KS L0: Sin activación") · SEMÁFORO GLOBAL (Naranja = PEOR estado de cualquier bot) · MT (Conectado; "3 pos. abiertas") · ALERTAS (2; "2 decisiones", badge clicable).
- **Contenido**: tarjeta "Equity del portfolio (todos los bots)": cifra grande, "+23.321 (+14,92 %)", "DD máx. periodo: 1,43 %", selectores 30 días/90 días/180 días/1 año/Todo, curva de área verde. Panel "Requiere acción (2)": tarjetas de decisión con título ("Poseidón Trend GER40 en NARANJA sostenido: pasar a PAPER"), descripción, instrucción MT literal, "Ver evidencia" colapsable, botones **Confirmar / Posponer / Descartar**. Panel lateral "Pipeline": contadores F1: 6 · F2: 5 · F3: 4 · F4: 4 · F5: 3 · F6: 3 · F7: 22 y lista de novedades con prefijos de color (GO / OVERSTAY / NARANJA).
- **Reglas**: respuesta <2 s (cache Redis + invalidación por evento); WS `equity`+`alerts` con fallback polling 5 s; conector caído → badge "DATOS STALE (hace X min)".
- **Casos límite**: sin decisiones → panel en estado vacío ("Sin decisiones pendientes. El sistema está al día."); equity sin snapshot reciente → cifra atenuada + aviso.

### 7.2. Cuentas/EA — SIN CAPTURA (diseño derivado, creatividad guiada)
Objetivo: inventario y deriva de configuración de cuentas y EAs — la respuesta a "¿lo que el sistema ordenó está realmente aplicado en el terminal?".
- **Grid de tarjetas de cuenta**: nombre, badge REAL/DEMO, broker · servidor, login, divisa, equity/balance, margen libre y margin level, estado de conexión (punto verde/gris), último heartbeat, latencia, uptime 7 días.
- **Tabla de EAs por cuenta**: magic, nombre de bot, fase/rol, versión del EA reportada vs `ea_required_version` (badge ámbar "v desactualizada" si difiere), modo esperado vs reportado (REAL / PAPER por semáforo NARANJA — deriva → alerta CRITICA "EA en modo incorrecto"), AutoTrading esperado vs reportado, filtro horario activo, ventanas de noticias cargadas (las copiadas en el checklist dominical), última señal/trade.
- **Panel "Deriva de configuración"**: diff entre estado ordenado (Decisiones confirmadas) y estado reportado: sizing aplicado vs `sizing_current_pct`, EAs que deberían estar en paper y no lo están, magics en terminal no registrados (huérfanos) y magics registrados ausentes del terminal.
- **Bloque roadmap TCA** (coherente con Ejecución): estado del EA reporter v1.1 por cuenta.
- **Reglas**: todo read-only; ninguna acción operativa desde aquí (solo navegación a la Decision asociada). Estilo: mismos tokens, densidad y componentes de tarjeta que Salud; marcar en código como "diseño derivado, sin captura de referencia" (comentario en el componente raíz).

### 7.3. Pipeline — `capturas\pestana-Pipeline_parte_Paper-12.jpg`, `pestana-Pipeline_parte_CapitalReal-11.jpg`, `pestana-Pipeline_parte_Paper-CapitalReal.jpg`
- **Kanban de 7 columnas** con títulos y contadores literales (F1 IDEACIÓN Y PROTOTIPADO … F7 PRODUCCIÓN (CHAMPION)). Zona PAPER (F1–F3) y zona CAPITAL REAL (F4–F7) visualmente diferenciadas.
- **Tarjeta de candidato**: nombre, magic, perfil, badge paper/real y PROVISIONAL/GO/HOLD; línea de estado ("Sin muestra · 9 días en fase" / "Verde · 95 días en fase"); "Gate: X/7 criterios" con barras de progreso (trades y días); "Decisión habilitada en ~N días" o "Faltan N trades y N días"; alertas inline ámbar (frecuencia <2 trades/semana; overstay "Competitivo pero no superior…"); botón primario "Promover a F{X+1}" (deshabilitado si el gate no da GO) + dropdown "Mover a…" (mover manual F1–F3; desde F4 solo lo mueve el sistema; "Retirar" exige autopsia).
- **Reglas**: ascensos F4+ solo por gate automático (el botón Promover en F4+ se bloquea con tooltip del criterio que falta); KILL abre formulario de autopsia bloqueante; candidatos en DEMO pausados por caída de cuenta → días sin datos no cuentan incubación.
- **Casos límite**: proyección ETA con frecuencia ~0 → "ETA no estimable"; columna vacía → estado vacío discreto.

### 7.4. Bots — `capturas\pestana-Bots-7.jpg`
- **Layout maestro-detalle**: lista lateral izquierda con buscador y grupo "PRODUCCIÓN (28)"; cada item: nombre, magic, perfil, badge de semáforo. Detalle: cabecera con nombre, magic, mercado, timeframe, perfil, "F7 · champion", badge semáforo + instrucción ("Mantener. No tocar nada."), selectores 30d/90d/180d/Todo y botón **"Tengo el impulso de intervenir"** (abre el formulario del diario de impulsos, M7).
- **Bloques del detalle**: "P&L acumulado del bot (N trades)" (área); "Rolling vs Baseline (alpha decay)" — tabla de métricas rodantes vs baseline con punto verde/ámbar/rojo por fila (Sharpe rolling, Expectancy, Win Rate drift, Payoff, Duración trade, Racha pérdidas, DD rolling); "Métricas completas" — grid 3×5 (Profit Factor, Expectancy (R), Sharpe, Sortino, Calmar, Max DD, DD actual, Recovery F., Ulcer, Win rate, Payoff, MCL, Dur. media (min), Trades/mes, P&L neto); "Contribución al portfolio" (% del P&L total, correlación c/ resto, sizing objetivo, P&L bot/cuenta); "Posiciones abiertas (N)" con badge SL ✓/✗; "Histograma de retornos (R)"; "Historial del pipeline" (timeline de fases).
- **Casos límite**: bot sin baseline → métricas "—" y nota; bot en NARANJA → banner con instrucción y contador de trades virtuales.

### 7.5. Portfolio — `capturas\pestana-Portfolio-2.jpg`
- **"Estructura macro 40/40/20"**: barras horizontales objetivo vs real por bloque + tabla (Bloque/Objetivo/Real/Δ/Bots: Convexo 40/45,7/+5,7/21 · Cóncavo 40/32,6/−7,4/16 · Híbrido 20/21,7/+1,7/10). Alerta SUAVE si |Δ| > 10 pp; rebalanceo solo en revisión mensual (texto recordatorio).
- **"Los 6 perfiles (micro)"**: tabla Trend Following 30/27,2/−2,8/12 · Reversión 25/22,8/−2,2/10 · Momentum 15/18,5/+3,5/9 · Smart Money 10/8,7/−1,3/4 · Grid/Scalping 10/9,8/−0,2/6 · ML/IA 10/13,0/+3,0/6. Nota literal: "Los objetivos por perfil son los de la formación (30/25/15/10/10/10). Los slots libres indican dónde puede entrar un challenger."
- **"Matriz de correlaciones (P&L diario)"** con badge "media 0,16": heatmap N×N rojo/negro; celda redundante (>3× media) con borde y tooltip con ambos bots ("medio gemelos": Lyra Scalper EURUSD × Phoenix Scalper SP500 = 0,52). KPIs vs benchmark: CAGR 37,31 % vs 11,90 % SP500, beta 0,18, alfa t=3,42, meses negativos 14/66.
- **Jobs**: recálculo semanal (domingo 06:00 UTC) + bajo demanda; cache Redis por (set de bots, ventana).
- **Casos límite**: bot con <30 días → excluido con nota; varianza cero → celda "n/a".

### 7.6. Salud — `capturas\pestana-Salud-5.jpg`
- **Grid de tarjetas por bot**: nombre, magic, perfil, "F7 · champion", "N días en estado", badge Verde/Amarillo/Naranja; chips de métricas (Sharpe rolling · Profit Factor / Expectancy · Win Rate drift · Payoff (AvgWin/AvgLoss) · Duración media · Máx. pérdidas consecutivas · DD rolling · PH = estadístico Page-Hinkley de régimen); pie con la instrucción literal del estado: VERDE "Mantener. No tocar nada." · AMARILLO "Reducir sizing al 50% (bajar fraction Kelly). Aumentar frecuencia de revisión." · NARANJA instrucción paper con magic.
- **Reglas**: toda transición genera Decision con Confirmar/Posponer/Descartar; baseline recién recalculada → `baseline_grace_days` (5) sin transiciones.

### 7.7. Riesgo — `capturas\pestana-Riesgo-4.jpg`
- **"Drawdown y kill-switch"**: DD actual 0,4 % · Max DD 4,8 % · Duración DD 4d; escalera L1–L4 con textos literales (6.2); nota "El panel avisa e instruye; la ejecución de cierres vive en MetaTrader".
- **"Tail Risk (VaR / CVaR, 60d)"** badge GREEN: VaR 95 % 0,54 % · VaR 99 % 0,91 % · CVaR 99 % 0,78 % · CVaR 95 % 1,12 % · VaR 99 % mensual 5,13 % · CVaR 99 % anual 17,78 %; veredicto literal "Colas dentro de los gates (CVaR99 diario < 3 % y mensual < 15 %). Mantener." (umbrales en SystemConfig).
- **"Exposición en vivo (N posiciones)"**: tabla Símbolo/Net/Gross/P&L (BTCUSD +0,46/0,46/−59,13 · GER40 −1,24/1,24/−91,76 · USOIL +0,63/0,63/+2.177,41) + agregados por activo/divisa; badge SL ✓/✗ por posición (✗ = CRITICA P5).
- **"News Shield — calendario económico (próximas 48 h)"**: divisas del portfolio (EUR·USD·GBP·JPY·AUD); tabla Evento/Divisa/Cuándo ("en 40h 41m")/Ventana (UTC)/Bots afectados; botón **"Copiar ventanas"** con las ventanas de exclusión (−30 min/+30 min) en texto plano para pegar en el filtro horario del EA; subsección "TRADES EN VENTANA DE NOTICIAS (30 DÍAS)" ("Lyra Scalper EURUSD: 2 trade(s) ejecutado(s) en ventana (último: CPI (YoY))").
- **"Drawdown esperado (Monte Carlo) y contrato de drawdown"**: por bot: "Atlas Trend EURUSD · magic 118231 · 300 trades", barra DD actual vs P50 2,3 % / P75 3,0 % / P95 3,9 % / Histórico 2,2 %, badge "Dentro del perfil esperado — no intervenir" o "INCUMPLIMIENTO DE CONTRATO", línea "Contrato firmado: acepta hasta −3,9 % (fecha de firma)". Recálculo mensual + cada 50 trades; seed persistida.

### 7.8. Ejecución — `capturas\pestana-Ejecucion-8.jpg`
- **Heartbeat**: "Terminal reportando. Último reporte: 26/7/2026, 17:04:10 · 3 posiciones abiertas" + uptime 7 días y latencia (M1).
- **"TCA / Perfil de broker"** (roadmap, texto literal): "TCA (§10.1) y Broker Profile (§10.2) requieren la v1.1 del EA reporter (precio solicitado vs ejecutado + spread por ejecución). Cuando el EA reporte slippage y spread por ejecución, aquí verás: slippage P50/P95/P99, Asymmetry Index, Implementation Shortfall y el mapa de spread por sesión." → implementar como panel "pendiente de datos" con el contrato de ingesta `POST /ingest/execution` ya definido (v1.1), sin UI inventada.
- **"Watchdog de bots (frecuencia observada vs esperada, 30 días)"**: tabla Bot (nombre + #magic)/Esperado mes/Observado 30d/Último trade/Estado (OK · MUERTO · DESBOCADO · FUERA DE TOLERANCIA). Defaults: tolerancia ±25 %, muerto si observado ≈0 con esperado >0, desbocado si >3×.
- **Casos límite**: baseline sin frecuencia esperada → "INSUFFICIENT_DATA" (sin alerta); drift horario VPS >120 s → SUAVE.

### 7.9. Escalado — `capturas\pestana-Escalado-9.jpg`
- **"Fase UMS actual"**: "4 · Semi-Profesional. Equity: 180k · 32 bots · riesgo/op: 0,3–0,7 % · Kelly 0,25" + badge de estado ("GREEN — Listo para subir de fase UMS (métricas sostenidas.)").
- **"Las 6 fases UMS"** (tabla contractual, vive en config):

| Fase | Nombre | Equity | Riesgo/op | Kelly |
|---|---|---|---|---|
| 1 | Validación Personal | 0–5k | micro-lotes | 0,5 |
| 2 | Track Record | 5k–25k | 1–1,5 % | 0,5 |
| 3 | Portfolio Maduro | 25k–100k | 0,5–1 % | 0,33 |
| 4 | Semi-Profesional | 100k–500k | 0,3–0,7 % | 0,25 |
| 5 | Semi-Institucional | 500k–1,0M | — | 0,2 |
| 6 | Institucional | 1,0M+ | — | 0,2 |

- **Regla de avance UMS**: subir de fase exige métricas sostenidas (config: `ums_min_months`, Sharpe mínimo, DD dentro de gate) + firma humana; bajar de fase es automático si equity cae bajo el rango (protección, no discrecional).
- **"Evolución mensual"**: tabla Mes/Equity/Trades/Retorno/Max DD/Sharpe/Fase (seed: 2026-06 169k · 289 · 3,8 % · 3,1 % · 1,77 · F4, etc.).

### 7.10. Graveyard — `capturas\pestana-Graveyard-10.jpg`
- **Banner ámbar literal**: "Un bot retirado nunca se reactiva sin re-validación completa (pipeline desde Fase 3)."
- **Filtros** "Todos los perfiles" / "Todos los motivos" + contador "9/9".
- **Tarjetas lápida**: nombre + #magic, línea perfil ("trend · convex · F7"), fechas "2021-03-01 → 2022-09-12", badge de motivo, autopsia entre comillas con lección. Las 9 lápidas del seed (textos literales en PARTE 13): Prometeo, Ligeia, Dédalo, Caronte, Niobe, Egeo, Anfitrite, Morfeo, Tique.
- **Reglas**: sin controles de reactivación; cada lápida enlaza (solo lectura) al historial del bot.

### 7.11. Auditoría — `capturas\pestana-Auditoria-6.jpg`
- **"Verificado"** (verde): "Nivel de verificación técnica de la cuenta (datos recibidos directamente del terminal, sin intervención manual)."
- **"Sincronización histórica: completada"**: "Todo el historial de operaciones ya está volcado. El % de continuidad de abajo mide la calidad del canal, no la carga de datos."
- **"Reconciliación contable" OK**: Balance en el primer snapshot 30.000,00 · Σ flujo posterior (P&L + swaps + comisiones + depósitos) 147.616,18 · Esperado 177.616,18 · Reportado 177.616,18 · **Descuadre 0,00 (0,00 %)**. Discrepancia >0,01 % → CRITICA.
- **"Continuidad del envío (7 días)"**: 99,6 % con barra; "167 h 19 min con envío de 168 h · primer snapshot: 2021-01-04"; "Tramos sin envío (1): 22 jul, 07:21 → 22 jul, 08:02 — 41 min".
- **"Sellos de integridad"**: LOTES SELLADOS (HASH+TS) 137.296 · TRADES ARCHIVADOS 15.486 · TICKETS 3000112 → 4292034 · HISTORIAL 2021-01-04 → 2026-07-26; nota literal sobre SHA-256 e inmutabilidad; disclaimer literal: "Verificación técnica de integridad de datos desde su recepción. NO constituye una auditoría contable, financiera ni legal. La exactitud última depende del terminal y del broker."
- **Módulo transversal — Diario de impulsos** (se accede desde el botón "Tengo el impulso de intervenir" en Bots y desde Resumen): formulario (bot, descripción, acción deseada) → monitorización contrafactual a 7 días (PARTE 8) → informe trimestral (referencia: 3 impulsos, 654,80 € evitados). Si se prefiere como sub-vista dentro de Auditoría, documentarlo como ADR; el comportamiento es idéntico.

---

## PARTE 8 — CATÁLOGO DE FÓRMULAS (exactas, con tests)

`core-engine/src/core/formulas/`: puras, `Decimal` para dinero, `float` para ratios, sin I/O. Doctests + pytest + hypothesis.

```python
def r_multiple(profit_net, entry, sl, volume, tick_value, tick_size) -> Decimal | None
    # riesgo_inicial = |entry-sl|/tick_size*tick_value*volume; sl None o riesgo 0 -> None (r_multiple NULL)
def expectancy_r(r_multiples) -> float                      # media; ventana vacía -> ValueError
def rolling_profit_factor(profits, window) -> float | None  # gross_loss==0 y profit>0 -> inf (cap visual 99); ambos 0 -> None
def daily_returns(equity_curve) -> pd.Series
def correlation_matrix(returns_by_bot, ffill_limit=3) -> pd.DataFrame  # alinear por día UTC, día sin trade = 0
def historical_var(returns, level=0.95) -> float
def historical_cvar(returns, level=0.99) -> float
def monte_carlo_maxdd(trade_pnls, n_sims=300, seed=42) -> MonteCarloResult  # p50/p75/p95, reproducible por seed
def ols_alpha_beta(portfolio_monthly, benchmark_monthly) -> AlphaBetaResult  # alpha, beta, t_stat, p, n
def watchdog_deviation(observed, expected, tolerance=0.25) -> WatchdogState  # OK|DEAD|RUNAWAY|OUT_OF_TOLERANCE|INSUFFICIENT_DATA
def audit_discrepancy(initial, flows, final) -> Decimal     # |initial+Σflows-final|/final; final==0 -> CRITICA estructural
def max_drawdown_pct(equity_curve) -> Decimal
def loss_streak(r_multiples) -> int
def streak_p99_threshold(r_multiples_baseline, n_boot=10_000, seed=42) -> int
def walk_forward_efficiency(oos_return, is_return) -> float  # WFE = OOS/IS; gate F2 >= 0.5
def page_hinkley(returns, delta, lambda_) -> PHResult        # detector de cambio de régimen (autopsia Niobe); params en config
def trades_per_week(trades, window_days=30) -> float         # gate 7 del pipeline
def decision_eta_days(oos_trades, min_trades, entered_phase_at, min_days, freq_week) -> int | None
    # proyección "Decisión habilitada en ~N días"; freq ~0 -> None ("ETA no estimable")
def counterfactual_impulse(bot_trades_after, desired_action, snapshot_at_impulse) -> Decimal
    # A los 7 días: resultado real del bot vs resultado simulado de haber ejecutado la acción
    # (posiciones que se habrían cerrado se valoran a su cierre real posterior; cambios de riesgo
    #  se evalúan con trades reales posteriores a sizing hipotético). avoided_cost = real - simulado (signo documentado).
def sustainable_withdrawal(avg_monthly_return, max_dd, equity, config) -> Decimal  # nómina mensual propuesta
```

Tests obligatorios por fórmula: nominal, ventana vacía, división por cero, un elemento, extremos, reproducibilidad MC por seed, property-based (`max_dd ≥ 0`, `|corr| ≤ 1`, WFE acotado con inputs acotados, ETA monótona en frecuencia).

---

## PARTE 9 — CONTRATOS DE API Y EVENTOS

### 9.1. Ingesta (conector → core, `X-API-Key`, idempotente, todo lote sella `IngestBatch`)
```
POST /ingest/trades      {account_login, trades:[...]}   -> {accepted, duplicated, batch_id, server_time}
POST /ingest/positions   {account_login, ts, positions:[...]}   # evalúa P5 (SL) al vuelo
POST /ingest/equity      {account_login, ts, equity, balance, margin_level, free_margin}
POST /ingest/heartbeat   {connector_instance_id, account_login, latency_ms}
POST /ingest/signals     {account_login, magic, signals:[...]}  # trades virtuales (NARANJA)
POST /ingest/execution   {account_login, magic, fills:[...]}    # v1.1 EA reporter: TCA (requested vs executed, spread) - contrato ya definido, sin consumidor aún
POST /ingest/ea_state    {account_login, eas:[{magic, ea_version, mode, autotrading, schedule_filter, news_windows}]}  # alimenta Cuentas/EA y deriva
```

### 9.2. API pública (gateway, JWT)
```
POST /auth/token  /auth/refresh
GET  /api/v1/header/summary            -> {equity_eur, pnl_day, pnl_week, pnl_month, portfolio_dd_pct, ks_level, global_semaphore, mt_connected, open_positions, alerts, pending_decisions, data_stale_seconds}
GET  /api/v1/summary/equity-curve?range=30d|90d|180d|1y|all
GET  /api/v1/decisions  POST /api/v1/decisions/{id}/confirm|postpone|dismiss
GET  /api/v1/accounts  GET /api/v1/accounts/{id}/eas  GET /api/v1/accounts/drift
GET  /api/v1/bots  GET /api/v1/bots/{id}  GET /api/v1/bots/{id}/semaphore-history
GET  /api/v1/portfolio/blocks  GET /api/v1/portfolio/profiles  GET /api/v1/portfolio/correlations?window_days=
GET  /api/v1/health/bots               # tarjetas de Salud
GET  /api/v1/risk/tail  GET /api/v1/risk/exposure  GET /api/v1/risk/montecarlo?bot_id=
GET  /api/v1/killswitch/status  POST /api/v1/killswitch/confirm
GET  /api/v1/news/shield?hours=48  GET /api/v1/news/shield/windows?format=text|csv|json
GET  /api/v1/execution/watchdog  GET /api/v1/execution/heartbeat
GET  /api/v1/pipeline/board  POST /api/v1/pipeline/candidates  POST /api/v1/pipeline/{id}/promote  POST /api/v1/pipeline/{id}/kill {autopsy}
GET  /api/v1/pipeline/{id}/gate        # detalle 7 criterios
GET  /api/v1/cemetery                  # reactivación: 409 siempre
GET/POST /api/v1/impulses  GET /api/v1/impulses/report?quarter=
GET  /api/v1/scaling/ums  GET /api/v1/scaling/monthly
GET  /api/v1/audit/status  POST /api/v1/audit/run  GET /api/v1/audit/seals
GET  /api/v1/withdrawals/calculator  POST /api/v1/withdrawals
GET  /api/v1/checklists/current  POST /api/v1/checklists/{id}/items/{item}/sign
```

### 9.3. WS y Redis Pub/Sub
WS: `/ws/equity`, `/ws/alerts`, `/ws/pipeline`, `/ws/health`. Topics: `events:equity`, `events:alert`, `events:decision`, `events:semaphore`, `events:killswitch`, `events:pipeline`, `events:trade`, `events:heartbeat`. Esquema de evento:
```json
{"type":"semaphore.transition","ts":"2026-08-22T09:00:00Z","bot_id":7,"magic_number":118685,
 "from":"AMARILLO","to":"NARANJA",
 "instruction":"En el EA magic 118685: desactivar apertura de nuevas posiciones (modo paper) y dejar cerrar las existentes por sus reglas.",
 "requires_confirmation":true}
```

### 9.4. Telegram
CRITICA → inmediata; SUAVE → inmediata o digest diario (`telegram_soft_digest`); INFO → solo panel. Backoff con reintentos; fallo nunca bloquea lógica (`telegram_failures_total`).

---

## PARTE 10 — CONFIGURACIÓN Y PROVEEDORES (hogar de TODOS los valores)

### 10.1. Settings (env): `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `JWT_ACCESS_TTL_MIN=15`, `JWT_REFRESH_TTL_DAYS=30`, `INGEST_API_KEYS`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SENTRY_DSN?`, `DEPLOYMENT_PROFILE=full|small_scale`, `TZ_DISPLAY=Europe/Madrid`, `BASE_CURRENCY=EUR`, `NEWS_PROVIDER=ics|csv|http`, `NEWS_SOURCE_URL`, `BENCHMARK_PROVIDER=csv|http`, `BENCHMARK_SYMBOL=^SPX`, `OPERATOR_EMAIL`, `OPERATOR_PASSWORD_HASH`.

### 10.2. Proveedores (protocolos; el sistema funciona COMPLETO sin APIs de pago)
```python
class NewsProvider(Protocol):    async def fetch_events(self, horizon_hours: int) -> list[NewsEventIn]
class BenchmarkProvider(Protocol): async def monthly_returns(self, symbol: str, since: date) -> pd.Series
# ICSProvider/CSVProvider/ManualProvider (fallback dominical) + HTTPProvider opt-in (Finnhub/TradingEconomics)
```

### 10.3. SystemConfig (defaults contractuales; única fuente)
`semaphore_pf_warn=0.75`, `semaphore_pf_orange=0.60`, `semaphore_exp_warn=0.60`, `semaphore_exp_recover=0.80`, `semaphore_recovery_days=10`, `semaphore_orange_days=15`, `orange_virtual_trades=30`, `baseline_grace_days=5`, `ph_delta`, `ph_lambda`, `kill_l1=8`, `kill_l2=12`, `kill_l3=15`, `kill_l4=20`, `kill_hysteresis_pp=2`, `sizing_total_cap=89`, `bot_capital_pct_min=3`, `bot_capital_pct_max=5`, `risk_per_trade_min=0.3`, `risk_per_trade_max=0.6`, `block_target={CONVEXO:40,CONCAVE:40,HIBRIDO:20}`, `profile_target={TREND:30,MEAN_REVERSION:25,MOMENTUM:15,SMART_MONEY:10,GRID:5,SCALPING:5,AI_ML:10}` (Grid+Scalping suman el 10 de la captura), `profile_block_map`, `block_tolerance_pp=10`, `corr_window_days=1240`, `corr_redundant_factor=3`, `mc_sims=300`, `mc_seed=42`, `pipeline_min_trades=30`, `pipeline_min_days=60`, `pipeline_pf=1.5`, `pipeline_exp=0.15`, `pipeline_sharpe=1.0`, `pipeline_maxdd=20`, `pipeline_min_freq_week=2`, `wfe_min=0.5`, `staging_steps=[10,25,50,100]`, `challenger_sharpe_ratio=1.22`, `challenger_p_max=0.05`, `challenger_overstay_months=6`, `tail_cvar99_daily_gate=3`, `tail_cvar99_monthly_gate=15`, `watchdog_tolerance=0.25`, `watchdog_runaway_factor=3`, `audit_tolerance=0.0001`, `impulse_eval_days=7`, `heartbeat_interval_s=60`, `uptime_target_7d=99.5`, `ums_phases=[...tabla 7.9...]`, `ums_min_months`, `instruction_templates={...}`, `ui_strings_catalog="ui_strings.es.json"`.

---

## PARTE 11 — DESIGN SYSTEM 1:1 (contractual)

### 11.1. Fuente y verificación
- Tokens en `doc_app\design_tokens.json` (instalado en G0 y importado por Tailwind; NINGÚN color/espaciado suelto en componentes — P11).
- Verificación: en G7/G8, Playwright captura cada pestaña con el seed cargado y se hace screenshot-diff contra `capturas_proyecto_dashboard\*.jpg` (umbral de similitud estructural en config; el diff valida layout, no contenido dinámico). Desviaciones → ADR en `docs\adr\`.

### 11.2. Tema (extraído de las capturas)
Dark slate casi negro: fondo app `#0B0D12`, superficie/tarjeta `#14171F`–`#161A23`, borde sutil `#232838`, texto primario `#E6E9F0`, secundario `#8B93A7`. Acento primario violeta `#7C6CF5` (botones, tabs activos, links). Semáforo: verde `#22C55E`, ámbar `#F59E0B`, naranja `#F97316`, rojo `#EF4444`. P&L: positivo verde, negativo rojo. Heatmap: escala divergente negro→rojo intenso (correlación alta = rojo). Tipografía Inter/system-ui; cifras tabulares (`font-variant-numeric: tabular-nums`); radios 10–12 px; sombras suaves; densidad compacta de panel profesional (paddings 12–16 px en tarjetas). Barras de progreso finas con track oscuro y fill violeta/verde. Badges redondeados pequeños con fondo translúcido del color semántico. Scrollbars discretos. Todo en `design_tokens.json`.

### 11.3. Componentes contractuales (nombre → spec)
`AppHeader` (6 `StatCard`: EQUITY / P&L DÍA / DRAWDOWN / SEMÁFORO GLOBAL / MT / ALERTAS) · `TabBar` (11 tabs, activo subrayado violeta) · `DecisionCard` (título, descripción, instrucción MT en bloque mono, "Ver evidencia", Confirmar/Posponer/Descartar) · `EquityAreaChart` (selectores de rango) · `PipelineKanban` + `CandidateCard` (barras gate, ETA, badges) · `BotListItem` + `BotDetail` · `BlockBars` + `ProfileTable` · `CorrelationHeatmap` · `HealthCard` (chips de métricas + pie de instrucción) · `KillSwitchLadder` · `TailRiskPanel` · `ExposureTable` · `NewsShieldTable` + botón "Copiar ventanas" · `MonteCarloContractRow` · `WatchdogTable` · `UmsPhaseCard` + `UmsTable` + `MonthlyEvolutionTable` · `TombstoneCard` · `AuditPanels` (reconciliación, continuidad, sellos) · `ImpulseDialog`.

### 11.4. Literales de UI
Todos los textos visibles de las capturas son contractuales y viven en `ui_strings.es.json` (nunca inline — P11): "Mantener. No tocar nada.", "Reducir sizing al 50% (bajar fraction Kelly). Aumentar frecuencia de revisión.", "Tengo el impulso de intervenir", "Requiere acción (N)", "Ver evidencia", "Copiar ventanas", "Dentro del perfil esperado — no intervenir", etc.

---

## PARTE 12 — PROTOCOLO DE GENERACIÓN POR FASES (Claude Code)

Al inicio de cada fase: plan mode → plan de archivos → ejecutar → PHASE REPORT (0.2.4). Un commit por unidad. `scan_hardcoding` (MCP) antes de cada commit de fase.

**G0 — Scaffold + tooling de gobierno**: árbol de repo; docker-compose completo; Dockerfiles; `.env.example`; `pyproject.toml`/`package.json`; pre-commit; CI; `README.md` y `ASSUMPTIONS.md` esqueletos; **instala `CLAUDE.md`, `.claude\skills\stratos-guardian\SKILL.md`, `mcp\stratos_mcp_server.py`, `.mcp.json`, `doc_app\design_tokens.json`, `config\thresholds.seed.json`, `frontend\src\styles\ui_strings.es.json`**; verifica que el MCP `stratos` responde (`get_thresholds`).
*Salida*: `docker compose up -d postgres redis` OK; CI verde; MCP operativo.

**G1 — Modelo de datos**: PARTE 5 completa + Alembic 0001 (extensión timescaledb, hypertables, compresión/retención, `equity_daily`, rol app sin UPDATE/DELETE en inmutables) + factories.
*Salida*: migración limpia; test de inmutabilidad por permisos; test de sello `IngestBatch`.

**G2 — Fórmulas**: PARTE 8 con TDD (rojo→verde), hypothesis incluido.
*Salida*: 100 % verde; cobertura ≥95 % en el módulo.

**G3 — Máquinas de estado**: PARTE 6 puras + persistencia + eventos (Redis fake). Tests de TODAS las transiciones + property-based (ninguna transición inválida alcanzable; kill-switch nunca desescala sin firma; cementerio sin retorno).
*Salida*: demo en test: PF 1,18 vs 1,94 → instrucción literal correcta con magic.

**G4 — mt5-connector + simulador**: conector Windows read-only (polling posiciones 5 s / deals incremental / equity 30 s / heartbeat 60 s; backoff exponencial máx 5 min; buffer SQLite store-and-forward; sello SHA-256 por lote; `install_service.ps1`) + `mt5-simulator` con escenarios (bot degradado, crash_21, posición sin SL, corte de red 10 min, huérfanos).
*Salida*: integración conector↔core con simulador; corte de 10 min sin pérdidas ni duplicados.

**G5 — core-engine**: servicios (watchdog, semáforos, kill-switch, correlaciones, MC, VaR/CVaR, auditoría, contrafactual, gate 7 criterios, challenger, UMS, retiros, checklists, deriva de configuración), jobs ARQ + schedules, API 9.1/9.2, WS, Telegram, Prometheus.
*Salida*: tests de API (auth, validaciones, 409 cementerio, SIZING_CAP, deriva EA modo incorrecto); OpenAPI sin warnings.

**G6 — Frontend shell + Resumen**: Vite + Tailwind desde `design_tokens.json`; router 11 tabs; `AppHeader` + `TabBar`; login JWT; pestaña Resumen 1:1 con `pestana-Resumen-3.jpg`; WS con fallback.
*Salida*: screenshot-diff Resumen dentro de umbral; cabecera <2 s.

**G7 — Frontend pestañas 2–11** (una por unidad de commit, en este orden): Portfolio, Salud, Riesgo, Bots, Pipeline, Ejecución, Escalado, Graveyard, Auditoría, Cuentas/EA. Cada una: leer captura → implementar → screenshot-diff → ADR si hay desviación.
*Salida*: 10 pestañas dentro de umbral; Cuentas/EA aprobada por el operador (diseño derivado).

**G8 — Seed + E2E**: `scripts\seed.py` (PARTE 13) + ejecución automatizada de los 16 criterios de aceptación (PARTE 15) + Playwright E2E (login → confirmar decisión → firmar checklist → registrar impulso).
*Salida*: PARTE 15 verde al 100 %; README final (instalación VPS + runbook).

**G9 — Hardening**: perfiles prod, backups `pg_dump` + WAL, rotación de API keys, playbook de alertas, `config\small_scale.yaml`, docs finales y ADRs cerrados.

---

## PARTE 13 — SEED Y ESCENARIOS (`scripts\seed.py`, idempotente, `--profile full|small_scale`)

**Cuentas**: REAL "Prod" (capital inicial 30.000 €, 2021-01-04) + DEMO "Quarry".
**Producción (28–32 bots, nombres/magics de las capturas)**: Atlas Trend EURUSD #118231 (trend, F7 champion; baseline PF 1,94; contrato MC 3,9 %; espera 7 trades/mes) · Helios Momentum DAX #118247 · Ariadna MeanRev SPX #118102 · Vega Grid GBPUSD #118318 (grid; AMARILLO 6 días, sizing 50 %) · Orion Breakout XAU #118344 · Selene MeanRev XAG · Titan Trend US30 #118396 · Nova SmartFlow EURUSD · Cronos Swing USDJPY · Minerva AI SPX · Boreas Trend USOIL · Lyra Scalper EURUSD #118423 (scalping, WR ~87 %, espera 58/mes, correlación 0,52 con Phoenix Scalper SPX) · Phoenix Scalper SPX · Perseo Momentum NAS · Danae MeanRev · Hermes OrderFlow · Rhea Trend XAG · Poseidón Trend GER40 #118685 (NARANJA 12 días, PF rodante 1,18) · … hasta 32 con perfiles coherentes 40/40/20 (foto real 45,7/32,6/21,7) y 6 perfiles micro (30/25/15/10/10/10).
**Cantera (~25)**: F1: Zephyr Trend AUDUSD, Boreal MR GER40, Kairos Momentum XAG, Lete Grid USDJPY, Talos AI US30, Eco SmartFlow SPX · F2: Umbra MR USTEC, Draco Trend USOIL, Nix Scalper GBPUSD, Ceres Momentum EURUSD, Hera AI XAG · F3: Janus MR EURUSD, Tetis Trend SPX, Electra SmartFlow GBPUSD, Ofión Momentum USOIL · F4: Cefiro MR XAU, Palas Trend USTEC (alerta frecuencia <2/sem), Ninfa Grid EURUSD · F5: Sigma MR SPX (GO: PF 2,6, 51 trades, 95 días → promoción a F6 disponible), Delfos Momentum XAU, Estige Trend GBPUSD (PROVISIONAL; PF 32,75 con 9 trades → HOLD), Vulcano Momentum US30 · F6: Helios Trend v2 (HOLD/OVERSTAY >6 meses), Ariadna MR v3.
**Graveyard (9 lápidas, textos literales de la captura)**: Prometeo Trend EURUSD #117021 (Alpha decay) · Ligeia Grid EURUSD #117044 (Broker desfavorable: spread nocturno 0,19R→0,04R) · Dédalo Momentum GER40 #117069 (Superado por Challenger: Helios, Sharpe ×1,22, p=0,03) · Caronte MR US30 #117088 (Overfitting: WFE 0,34 → mínimo 0,5) · Niobe Swing USDJPY #117105 (Cambio de régimen: BoJ, Page-Hinkley) · Egeo Breakout XAG #117131 (Alpha decay: PF forward 1,05 vs 1,9) · Anfitrite MR GBPUSD #117152 (Superado por Challenger: Danae, RF 4,1 vs 2,6) · Morfeo AI USTEC #117170 (Overfitting ML) · Tique Scalper US30 #117198 (Competitivo pero no superior, regla 6 meses).
**Historia**: 15.486 trades desde 2021-01-04; equity diaria con DD máx 4,8 %, retorno medio mensual 2,69 %, 14/66 meses negativos, correlación media 0,16, beta 0,18 (benchmark `scripts\data\sp500_monthly.csv`); 137.296 lotes sellados; continuidad 7d 99,6 % con 1 tramo sin envío de 41 min.
**Escenarios**: posición sin SL (CRITICA P5) · 3 trades huérfanos · bot muerto (0/12) · bot desbocado (3,4×) · `--inject-audit-error` (0,02 %) · `crash_21` (DD 21 % para kill-switch) · 3 impulsos cerrados (418 €, 236 €, 0,80 €) + 1 pendiente · noticias HIGH 48 h (IFO EUR, Durable Goods USD) · decisiones pendientes: Poseidón a PAPER + Sigma MR a F6 · estado cabecera: equity 179.642,70 · P&L día +37,36 (sem 2.444,14 · mes 10.525,70) · DD 0,4 % · KS L0 · MT conectado 3 pos. · 2 alertas.

---

## PARTE 14 — RUNBOOK Y MODO PEQUEÑA ESCALA

`docs\runbook.md`: instalación en ambos VPS (Windows: Python 3.12 + terminal MT5 + servicio; Linux: compose + nginx + certbot + backups `pg_dump` diario + WAL; RPO 24 h / RTO 2 h), rotación de API keys, actualizaciones (Alembic con backup previo), playbook por alerta CRITICA, y el **calendario de decisiones** (literal del vídeo) como checklist imprimible:
- **Domingo (20 min, mercado cerrado)**: revisión TÉCNICA (errores de EA, desconexiones, órdenes rechazadas) + copiar noticias de la semana entrante al filtro horario. PROHIBIDO mirar rentabilidad (la vista dominical la OCULTA).
- **Cada 15 días**: semáforos vs baseline; confirmar amarillos al 50 %.
- **Primer domingo del mes**: bots vs backtest; rebalanceo de bloques si |Δ|>10 pp; correlaciones; EJECUTAR EL RETIRO (una línea más del checklist, nunca un impulso; retiro mensual SIN EXCEPCIÓN aunque el mes sea negativo — es nómina: retorno medio 2,69 % vs max DD 4,76 %).
- **Trimestral**: robustez, alpha decay, informe de coste de impulsos.
- **Enero**: reestructuración anual (resolver pares redundantes, contratos MC, overstay de challengers).

`config\small_scale.yaml` (M9): ~5.000 €, 3 bots (1 tendencial + 1 reversión + 1 libre), correlación medida con rechazo >0,5, riesgo 0,5 %/op, semáforo simple, escalera 8/12/15, revisión dominical 20 min, retiro solo primer domingo. Mensaje: "No necesitas 32 bots, necesitas el protocolo. El tamaño llega después."

---

## PARTE 15 — RESTRICCIONES NEGATIVAS

1. Ningún gráfico de precio, indicador, línea de tendencia o SMC en ninguna vista.
2. Ningún formulario de entrada manual de trades/posiciones/equity.
3. Ningún UPDATE/DELETE en `DecisionLog`, `SemaphoreTransition`, `KillSwitchEvent`, `WithdrawalLog`, `ChecklistRun`, `IngestBatch` (permisos BBDD).
4. El conector NUNCA envía órdenes (read-only).
5. El frontend solo habla con api-gateway.
6. Ningún rebalanceo fuera de revisión mensual/anual.
7. Ninguna reactivación desde el cementerio (409 siempre).
8. **Ningún valor hardcodeado**: umbrales → SystemConfig; despliegue → Settings; colores/espaciados → design_tokens.json; textos → ui_strings.es.json; plantillas de instrucción → config. `scan_hardcoding` limpio o justificado.
9. Ningún secreto en el repo.
10. La vista dominical NUNCA muestra rentabilidad.
11. Ninguna dependencia de pago obligatoria.
12. Nada de `except: pass`; todo error logueado con contexto.
13. Ninguna desviación visual de las capturas sin ADR.
14. Ningún ascenso F4+ manual: solo gate automático.

---

## PARTE 16 — CRITERIOS DE ACEPTACIÓN (automatizables en G8)

1. Cabecera <2 s con las 6 tarjetas y datos del seed exactos.
2. Poseidón Trend GER40 (PF 1,18 vs 1,94) en NARANJA con instrucción literal y Decision Confirmar/Posponer/Descartar.
3. Kill-switch: `crash_21` recorre L1→L4; sin desescalado sin firma + histéresis.
4. Cementerio: 409 + sin control UI + banner "pipeline desde Fase 3".
5. Impulso pendiente del seed se cierra a 7 días con `avoided_cost_eur` coherente.
6. Auditoría: seed limpio 0,00 %; `--inject-audit-error` → CRITICA.
7. Watchdog: muerto/desbocado/OK correctos (Atlas 7/6 OK; Lyra 58/59 OK).
8. Huérfanos listados; reenvío de lote no duplica y el sello SHA-256 verifica.
9. Par Lyra×Phoenix 0,52 marcado redundante con SUAVE.
10. Estige (PF 32,75/9 trades) HOLD; Sigma MR (95 d/51) GO; botón Promover bloqueado sin GO.
11. SIZING_CAP bloquea activación >89 %.
12. Posición sin SL → CRITICA + Telegram (mock) <60 s.
13. Corte 10 min: cero pérdidas, cero duplicados, badge DATOS STALE.
14. Vista dominical sin ninguna cifra de rentabilidad (test de contenido).
15. Screenshot-diff de las 10 pestañas con captura dentro de umbral; Cuentas/EA aprobada por el operador.
16. `scan_hardcoding` sobre todo el repo: cero hallazgos sin justificar en `ASSUMPTIONS.md`.
17. `docker compose up` + seed = panel navegable completo en <10 min.

---

## PARTE 17 — SKILL Y MCP DEL PROYECTO (instalación en G0)

- **Skill** `.claude\skills\stratos-guardian\SKILL.md` (entregada con este prompt): guardián de dominio. Se activa al tocar semáforos, kill-switch, pipeline, fórmulas, auditoría o UI; impone checklists (umbrales desde MCP, transiciones con persistencia+evento+Decision, instrucciones con plantilla, diseño 1:1 con captura, scan anti-hardcoding).
- **MCP** `stratos` (`mcp\stratos_mcp_server.py` + `.mcp.json`, entregados): tools `get_thresholds`, `get_module_spec`, `get_design_tokens`, `get_formula_signature`, `get_acceptance_criteria`, `get_seed_scenario`, `scan_hardcoding`. Es la fuente consultable del proyecto: si el código y el MCP discrepan, manda el MCP y se corrige el código (o se actualiza el threshold vía PR documentado).

---

**INICIO**: lee `doc_app\PROMPT_MAESTRO.md` completo, instala el tooling de gobierno y arranca en **FASE G0** (PARTE 12). Entrega el plan de G0 en plan mode antes de escribir el primer archivo.
