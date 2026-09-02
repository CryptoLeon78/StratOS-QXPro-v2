# Auditoría de estado — StratOS-QXPro-v2 — 2026-09-02

> Auditoría ejecutada por Claude Code tras un periodo de trabajo en paralelo con Codex/ChatGPT.
> **Documento de referencia cruzada para Codex**: recoge qué se verificó, con qué comando, qué
> salió y qué queda pendiente. Todo lo marcado `verificado` se ejecutó en esta sesión; lo que no
> se pudo ejecutar se declara explícitamente como `no verificado`.
>
> Alcance: repositorio `Apps_entorno_SQX/StratOS-QXPro-v2` (rama `main`), más los puntos de
> contacto con `Apps_entorno_SQX/SQX_vs_MT5_Panel` y con los índices de contexto de la raíz
> (`CLAUDE.md` / `AGENTS.md`).

---

> ## Estado de este informe
>
> **El diagnóstico de las secciones 1-3 describe el estado ANTES de los arreglos.** Se conserva
> tal cual porque es lo que se encontró y el porqué de cada corrección — no como estado vigente.
>
> Cerrados en la misma sesión: **H1** (15 commits pusheados), **H2** (ruff, format y mypy
> limpios), **H3** (600 + 150 tests verdes), **H4** (exe regenerado, 0 scripts por detrás),
> **H5** (reclasificación persistida), **H6/H7** (numeración y contradicción resueltas),
> **H8/H9** (changelog del panel y extracción de símbolo), **H10/H11** (índices y README).
>
> Sigue abierto: **H12** (`SQX_Edge_Suite_v1` sin versionar) y los hallazgos nuevos que
> salieron al arreglar, en `docs/backlog.md` **A11-A18**. El orden de trabajo está en
> `docs/PLAN_CONTINUACION_2026-09-02.md`; el hand-off para Codex, en la **sección 5**.

---

## 1. Resumen ejecutivo

El sistema **funciona y su documentación de dominio es honesta y detallada** — `phase_status.md`,
`ASSUMPTIONS.md` y `backlog.md` describen G13 con precisión y sus cifras cuadran contra los
artefactos sellados en disco. El problema no es el contenido: es la **infraestructura de garantía**.

Cuatro hechos que bloquean declarar StratOS "productivo":

1. **G11, G12 y G13 completos están sin commitear.** El último commit del repo es `a55694c`
   (G10/G11 temprano). 194 ficheros viven sólo en el working tree. Sin historial, sin CI, sin
   posibilidad de revertir nada.
2. **CI fallaría hoy**: `lint-backend` rojo (7 errores ruff + 8 ficheros sin formatear) y
   `test-backend` rojo (1 test). Ninguna fase de G11-G13 pudo verificarse en CI real porque
   nunca se pusheó.
3. **El ejecutable operativo está desactualizado**: `dist/StratOS_Operational.exe` es del 30/08 y
   hay 23 scripts `.py` posteriores. Lanzarlo hoy ejecuta la lógica *anterior* al contrato
   direccional, a la cola alineada v2 y al post-scan de migración.
4. **La reclasificación direccional no está en el sistema**: vive en un JSON suelto, no como
   evento en `operational_asset_event`. El estado de la BD y el estado de la evidencia divergen.

---

## 2. Qué se verificó y qué salió

### 2.1 Stack operacional — VERDE

| Comprobación | Resultado |
|---|---|
| Contenedores `stratos_operational` | 7/7 arriba (postgres y redis `healthy`, resto `Up 31h`) |
| `GET :8300/health` (core) | 200 |
| `GET :8380/health` (gateway) | 200 |
| `GET :5473/` (frontend) | 200 |
| BD operacional | 2 cuentas, 40 bots, 4.304 trades |

Los 4.304 trades cuadran exactamente con los HTML sellados (JJTI 1.945 + BEPB 2.359) declarados
en `phase_status.md`. **Sin discrepancia.**

### 2.2 Tests

| Suite | Resultado | Comando |
|---|---|---|
| `core-engine/tests` | **598 pasan, 1 falla** | `pytest tests --ignore=tests/e2e/test_g8_acceptance_criteria.py` contra Postgres/Redis efímeros |
| `scripts/tests` | **120 pasan, 1 falla** | `pytest scripts/tests` |
| `frontend` (vitest) | **50/50 verde** (21 ficheros) | `npx vitest run` |
| `SQX_vs_MT5_Panel/tests` | **8/8 verde** | `pytest tests` |
| `e2e-playwright` | **no ejecutado** | requiere seed + navegador; los baselines son de G10 |
| `e2e-acceptance-full` | **no ejecutado**; criterio 9 sigue documentado como roto desde G10-14 |

Los dos fallos, en detalle, en la sección 3.

### 2.3 Lint y typecheck — ROJO (bloquearía CI)

| Comprobación | Resultado |
|---|---|
| `ruff check core-engine/` | **7 errores** (3 `I001`, 4 `E501`) |
| `ruff format --check core-engine/` | **8 ficheros** se reformatearían |
| `mypy --strict core-engine/src/` | **7 errores en 3 ficheros** |
| `ruff check scripts/` | 189 errores (162 `E501`) — CI **no** cubre `scripts/`, deuda no bloqueante |

Ficheros afectados, todos tocados por G11-G13: `db/models/__init__.py`, `db/sa_enums.py`,
`routers/pipeline.py`, `services/config_drift.py`, `services/tca.py`, `routers/bots.py`.

### 2.4 `scan_hardcoding` (MCP `stratos`)

340 hallazgos en `scripts/`. La mayoría (~250) están en `seed_lib/`, deuda de fixture conocida y
aceptada desde G8. Hay falsos positivos claros (índices de columna, colores nativos MT5 como
`16777215`, codec `utf-16` de los `.chr`) y algunos de ellos ya están justificados nominalmente en
`ASSUMPTIONS.md` G13-19 y G13-22. **Lo que no existe es un barrido consolidado de G12/G13 con cada
hallazgo clasificado**, como sí se hizo para G10 en el grupo (o).

### 2.5 Coherencia de las cifras de dominio — VERDE

Todo lo que `phase_status.md` afirma sobre G13 y pude contrastar contra artefactos, cuadra:

| Afirmación en la doc | Artefacto | Cuadra |
|---|---|---|
| Prefiltro: 237 inventario, 4 ya testeados, 2 en cola | `analysis-prefilter.json` (`summary`) | Sí |
| Cola F7 alineada: 13 fuentes resueltas | `queue_aligned_20260828_v2.json` (13 `READY_FOR_TICK_BACKTEST` de 56) | Sí |
| Preflight: 6 `PREFLIGHT_OK`, 7 `WITHHELD_TICKS` | `preflight_aligned_20260828_v2.jsonl` | Sí |
| Reclasificación: 11 corridas, 3 cambios de veredicto | `directional_reclassification_20260901.json` (`summary`) | Sí |
| Registro append-only intacto | `operational_asset_event`: 227 `STATIC_VALIDATED` + 24 `WITHHELD` | Sí |

Los 2 expedientes `PREFLIGHT_OK` pendientes de lanzar son `USDJPYH1Lcity_3.16.113` y
`USDJPYH1Lcity_2.22.171`.

---

## 3. Hallazgos

### H1 — G11/G12/G13 sin commitear · CRÍTICO

`git log` del repo termina en `a55694c` ("feat(scripts): register_real_account_bot.py").
`git status`: 194 entradas — 40 modificados, 154 sin trackear, incluidos **7 migraciones Alembic**,
**53 scripts nuevos**, **11 documentos** y **2 docker-compose**.

Consecuencias reales:
- No hay punto de retorno. Un `git checkout` accidental borra tres fases.
- El CI nunca ha visto este código. Las afirmaciones de "verde" de G12/G13 son locales.
- Los ADRs 0008/0009 y las 40 entradas G12/G13 de `ASSUMPTIONS.md` no tienen commit que las ancle.

**Nota adicional de higiene**: el repo padre `SQX_144_Full2` tiene ficheros de StratOS en su propio
índice (84 `M` + 676 `D` incluyen rutas de `StratOS-QXPro-v2/`), a la vez que StratOS es un repo git
anidado con su propio remoto. Los dos índices se pisan. Los 676 borrados del padre corresponden en su
mayoría al renombrado MN de `user/Estrategias_script_mt5_real_BEPB_y_JJTI/` y a artefactos de
`user/reports/` y `SyntheticRetestAnalyzer/data/`, no a pérdida real de código.

### H2 — CI rojo: lint y mypy · ALTO

7 errores de ruff y 7 de mypy `--strict`, todos en ficheros tocados por G11-G13. Detalle de mypy:

```
services/tca.py:60      Need type annotation for "account_brokers"  [var-annotated]
services/tca.py:60      Argument 1 to "dict" has incompatible type  [arg-type]
routers/pipeline.py:250 Incompatible return value type (CandidateResponse vs PipelineCandidate)
routers/pipeline.py:276 idem
routers/pipeline.py:319 idem
routers/bots.py:172     Incompatible return value type (BotResponse vs Bot)
routers/bots.py:172     Item "None" of "Account | None" has no attribute "data_origin"
```

Los de `pipeline.py`/`bots.py` son anotaciones de retorno que quedaron desfasadas al introducir la
procedencia (`-> Bot` cuando ya devuelve `BotResponse`). El último es el único con riesgo de runtime:
`get_bot` hace `account.data_origin` sin comprobar `None`. En la práctica `Bot.account_id` es
`NOT NULL` con FK, así que no es explotable hoy — pero es exactamente el patrón que mypy `--strict`
existe para atrapar.

### H3 — Dos tests rojos · ALTO

**`core-engine/tests/test_migration.py::test_all_tables_created`**
`EXPECTED_TABLE_COUNT = 30`, el esquema real tiene 36. Las 6 nuevas son de G11/G13
(`import_artifact`, `execution_fill`, `pipeline_phase_transition`, `external_ea_inventory`,
`operational_asset`, `operational_asset_event`). Es un test de guardia de esquema que nadie
actualizó al añadir las migraciones. Arreglo trivial, pero mientras siga rojo el guardia no protege.

**`scripts/tests/test_import_external_ea_inventory_records.py::test_parses_operator_bepb_magic_records`**
```
assert sum(record.magic_number == 10827 for record in records) == 2
E  assert 1 == 2
```
Más interesante: el test verifica la **colisión BEPB `magic=10827`**, la que `ASSUMPTIONS.md` G13-14
sella como "retenida para ambas filas". `docs/registro_BEPB_MN_bots_real_mt5_vps.md` fue reescrito
el 01/09 con los magics **post-migración MN** y ya sólo contiene una fila con ese magic.

La evidencia original **no se ha perdido**: `runtime/operational/external_inventory/bepb_magic_manifest.json`
(30/08) conserva el duplicado. Pero el fichero `docs/registro_*_MN_*.md` **cambió de significado** —
de "observación pre-migración" a "estado post-migración" — sin que el test ni la documentación lo
reflejen. Hay que decidir cuál de los dos roles cumple ese fichero y separar el otro.

### H4 — `StratOS_Operational.exe` desactualizado · ALTO

`dist/StratOS_Operational.exe` es del **30/08 15:58**. Hay **23 scripts `.py` posteriores**, entre
ellos `reclassify_external_f7_backtests.py`, `refresh_live_backtest_queue_sources.py`,
`run_live_backtest_queue.py`, `scan_magic_identity_post_migration.py` y todo el módulo
`magic_identity`.

`phase_status.md` lo describe como "el punto de entrada guiado" del stack operacional. Es el binario
que el operador lanzaría para trabajar. Hoy ejecuta la lógica anterior al contrato direccional
(umbrales simétricos), a la cola alineada v2 y al post-scan. **Es la vía más probable de que una
decisión se tome con el criterio viejo.**

### H5 — Reclasificación direccional no persistida · MEDIO-ALTO

`directional_reclassification_20260901.json` cambia 3 veredictos de 11:

| Corrida | Antes | Después |
|---|---|---|
| `20260830T210536Z` (AUDCAD H4 `4.25.70_wfm520`) | TOLERABLE | **VALIDADA** |
| `20260901T162135Z` (`XAUH1BUYSTOPeof_1.8.81_MN1`) | TOLERABLE | **VALIDADA** |
| `20260901T201156Z` (`USDJPYH1L_5.15.110_MN8`) | DISCREPANTE | **TOLERABLE** |

En `operational_asset_event` los eventos siguen siendo los originales (`WITHHELD`). Esto es correcto
como append-only — pero **no se añadió ningún evento nuevo** que registre la reclasificación. El
resultado es que la verdad contractual vigente vive en un fichero suelto y el sistema no la conoce.

Para F7 externos el `WITHHELD` sigue siendo el estado correcto (no hay promoción), así que **no hay
riesgo operativo inmediato**; el problema es de trazabilidad: dentro de un mes nadie sabrá que esas
tres corridas se releyeron.

### H6 — Colisión de numeración `G13-24` · MEDIO

| Documento | `G13-24` significa |
|---|---|
| `ASSUMPTIONS.md:363` | "Serializaciones duplicadas de perfiles MT5" |
| `docs/phase_status.md:45` | "Contrato direccional SQX↔MT5" |

Además, **el contrato direccional no tiene entrada propia en `ASSUMPTIONS.md`** (`grep -ci
"direccional" ASSUMPTIONS.md` → 0) ni ADR. Es la decisión de negocio más importante de los últimos
días: redefine qué se considera una estrategia validada, con asimetría deliberada entre desviación
adversa y favorable. Merece más que un párrafo en el estado de fase.

**Corregido en esta auditoría**: se añade `ASSUMPTIONS.md` G13-25 y se renumera la referencia en
`phase_status.md`.

### H7 — `phase_status.md` G13-21 contradice G13-24 · MEDIO

G13-21 narra los veredictos originales de las cuatro comparaciones renovadas
(`XAUH1BUYSTOPeof_1.8.81_MN1` → TOLERABLE, `USDJPYH1L_5.15.110_MN8` → DISCREPANTE). Tras la
reclasificación de G13-24 esos dos son VALIDADA y TOLERABLE. Leídos por separado, los dos párrafos
se contradicen sin que ninguno diga que el primero quedó supersedido.

**Corregido en esta auditoría**: nota de supersesión explícita en G13-21.

### H8 — `SQX_vs_MT5_Panel`: cambio de contrato sin changelog · MEDIO

`sqx_mt5_panel.json` y `sqx_mt5_config.py` pasaron de umbrales escalares a
`{adverse, favorable}` y, de paso, `num_trades` subió de **5 % a 20 %** — un aflojamiento de 4×.
El `CHANGELOG_panel.md` se queda en `v1.2.3 (2026-08-29)`, que documenta la CLI y el bloqueo por
instancia, pero **no menciona ni el contrato direccional ni el cambio de `num_trades`**.
`sqx_mt5_config.VERSION` sigue en `'1.2.3'`.

El código está bien hecho (retrocompatibilidad explícita con configuraciones escalares, comentario
de intención, y `tests/test_directional_verdict.py` cubriéndolo, 8/8 verde). Lo que falta es el
registro.

**Corregido en esta auditoría**: entrada `v1.3.0` en `CHANGELOG_panel.md`.

### H9 — `alias_simbolos` contaminado con un nombre de estrategia · MEDIO

En `sqx_mt5_panel.json`:
```json
"alias_simbolos": {
  "NASDAQ": "NDX",
  "DAX40": "GDAXI",
  "USA30IDXUSD": "WS30",
  "USDJPY": "USDJPY",                          // alias identidad, redundante
  "AUDNZDH4BUY_edge_1.16.34": "AUDNZD"         // NO es un símbolo
}
```
El contrato del diccionario es símbolo SQX → símbolo broker. `AUDNZDH4BUY_edge_1.16.34` es un
**nombre de estrategia**, y `USDJPY: USDJPY` es una identidad que no debería hacer falta. Los dos
son parches puntuales que sugieren que el resolutor de símbolos falla al extraer el símbolo de esa
estrategia concreta, y que se tapó por configuración en lugar de arreglar la extracción. Cada
estrategia futura con el mismo patrón necesitará su propia línea.

### H10 — Índices de contexto desactualizados · MEDIO

- **`CLAUDE.md` de la raíz no menciona StratOS-QXPro-v2 en absoluto** (`grep -ni stratos` → 0
  resultados). Es el proyecto donde vive todo el trabajo reciente y el único con gobierno propio.
- **`AGENTS.md` de la raíz es una copia mecánica de `CLAUDE.md`** con `Claude`→`Codex` sustituido
  sólo en el texto plano: afirma que la base de conocimiento vive en `instrucciones para Codex\`
  (**ese directorio no existe**) mientras sus 24 enlaces apuntan correctamente a
  `instrucciones para Claude/`. También referencia `instrucciones para Codex/AGENTS.md`, que
  tampoco existe (el fichero real es `instrucciones para Claude/CLAUDE.md`).
- **No hay `AGENTS.md` dentro de `StratOS-QXPro-v2/`**. Codex, trabajando ahí, hereda sólo el
  `AGENTS.md` de la raíz — que ni menciona el subproyecto — y no ve `CLAUDE.md`,
  `docs/phase_status.md` ni `ASSUMPTIONS.md` salvo que se le indique. Es la causa estructural más
  probable de divergencia entre los dos agentes.
- `.codex/config.toml` sólo registra el MCP `sqx_forja`. No tiene `stratos` (y por tanto **no tiene
  `scan_hardcoding`**) ni `mt5_bridge`.

**Corregido en esta auditoría**: los cuatro puntos.

### H11 — `README.md` y `architecture.md` congelados en G11 · BAJO

`README.md:263` y `docs/architecture.md:46` describen G11 como la fase en curso. G12 y G13 existen
en el README sólo como sección de arranque del stack operacional, no en el relato de fases.

**Corregido en esta auditoría.**

### H12 — `SQX_Edge_Suite_v1` fuera de todo control · INFORMATIVO

`Apps_entorno_SQX/SQX_Edge_Suite_v1/` es un proyecto grande (backend, app, tests, `node_modules`,
gobierno propio con `DISCIPLINA_OPERATIVA.md` y `PROJECT_GOVERNANCE.md`, y su propio `AGENTS.md`
con política "gbrain-first").

- **Sin git propio** y sin commitear en el padre.
- **Última actividad: 14/08/2026** — inactivo desde hace ~3 semanas, no lo tocó esta campaña.
- No aparece en `CLAUDE.md`, ni en la memoria, ni en `PIPELINE_MINADO_A_FINALISTAS.md` (que sigue
  hablando de "9 apps de entorno" cuando `Apps_entorno_SQX/` ya tiene 14 directorios).

Su `AGENTS.md` instruye a los agentes a consultar un sistema de memoria "gbrain" antes de responder.
No interfiere con StratOS porque está en otro directorio, pero conviene saber que existe: si Codex
abre una sesión ahí, cambia de reglas de gobierno sin avisar.

---

## 4. Lo que queda pendiente (dominio)

Estado real de los gates de G13, sin cambios respecto a lo que ya declara `phase_status.md` —
lo confirmo aquí para que sirva de índice:

| Gate | Estado |
|---|---|
| Cola F7 tick-real | **En pausa por decisión del operador** (2026-08-31). 2 expedientes `PREFLIGHT_OK` sin lanzar: `USDJPYH1Lcity_3.16.113`, `USDJPYH1Lcity_2.22.171` |
| Cola F7 retenida | 7 `WITHHELD_TICKS` (alias/cobertura Darwinex) + 43 retenidas por fuente en la cola de 56 |
| Prefiltro Análisis | 217 superan criterios; sólo 2 expuestas por tope de diversidad `AUDCAD/H4`; 215 en `HOLD_DIVERSITY_CAP` |
| Histórico real 2018+ | Exportador MQL5 escrito y probado, **nunca ejecutado** en JJTI/BEPB. Los 4.304 trades HTML son huérfanos (sin magic) |
| Incubadora | **Bloqueada**. Sin cuenta `BROKER_DEMO` registrada, sin adjunto por gráfico, 0 candidatos elegibles |
| Reconstrucción AlgoWizard | 3 retenidas con plan; `EURUSD_SELL_STOP_H4_LC_3.8.141` bloqueada (sólo `.ex5`) |
| Procedencia en UI | Bots/Pipeline/Cuentas-EA hechas. Faltan Portfolio, Salud, Riesgo, Auditoría, Dominical |
| Recorrido autenticado + WS | No realizado |
| FX en EUR | Servicio funcional, `FxRate` sin poblar — falta el CSV del operador |
| `e2e-acceptance-full` criterio 9 | Roto desde G10-14, decisión explícita de no investigar |

---

## 5. Para Codex — qué pasó en esta sesión y qué cambia para ti

Esta sección es el hand-off. Trabajamos en paralelo sobre el mismo repo: mientras tú cerrabas
G13 (cola local auditada, estado en Pipeline, ingesta del CSV de histórico), esta sesión hizo
la auditoría y ejecutó los bloques P0-P2 del plan. **Nada de lo que hiciste se ha revertido.**

### Lo que toqué de tu trabajo

- **Tres líneas largas** en el router de cola operacional de `routers/pipeline.py` (commit
  `bcb94aa`, `style(core)`). Sólo formato, ninguna expresión cambia — el `ruff check` de CI
  las habría rechazado.
- **`parse_closed_positions()`** de `import_mt5_history_export.py` ahora devuelve **tres**
  valores en vez de dos (el tercero son las traducciones de magic aplicadas) y acepta un
  `legacy_magic_map` opcional. Si tenías código llamándola, ajusta el desempaquetado.
- Nada más. `PipelinePage.tsx`, `useOperationalQueue.ts`, `docker-compose.operational.yml` y
  las migraciones que estabas escribiendo quedaron intactas y sin commitear por mí.

### Lo que cambió a tu alrededor

1. **El repo ya tiene historial.** 15 commits temáticos pusheados a `origin/main`, desde el
   esquema de G11 hasta esta auditoría. Antes de seguir, `git pull`. Y **commitea a menudo**:
   194 ficheros sin commitear fue el hallazgo más grave de la auditoría.
2. **CI está verde y hay que mantenerlo así.** `ruff check core-engine/`,
   `ruff format --check core-engine/` y `mypy --strict core-engine/src/` pasan limpios; 600
   tests en core-engine y 150 en scripts. Antes de cerrar cualquier unidad, corre los cuatro.
3. **`.gitignore` cambió.** `.env.*.example` se versiona (antes la regla `.env.*` se comía
   `.env.operational.example`, que la doc declara versionada) y `docs/history_deals_*.csv` se
   ignora: son 9.082 deals de cuentas reales, evidencia operativa que pertenece a `runtime/`.
   **No los muevas de `docs/` mientras tu ingesta los lea de ahí**, pero tenlo en cuenta.
4. **La política del prefiltro es `v3`.** `max_per_symbol_timeframe` y `max_mt5_queue` planos
   ya no existen: ahora hay `validation_queue` e `incubator_admission` (G13-29). Una política
   v2 se sigue leyendo con su comportamiento anterior, pero el fichero del repo es v3.
5. **La numeración de `ASSUMPTIONS.md` llega a G13-29.** Comprueba el último número real antes
   de añadir la tuya: `grep -o 'G13-[0-9]*' ASSUMPTIONS.md | sort -u | tail -1`. Ya hubo una
   colisión (`G13-24` significaba dos cosas distintas).

### Lo que te ahorra trabajo directamente

- **`build_legacy_magic_map()`** en `scripts/magic_identity.py`: traduce magics anteriores a
  la migración MN a la identidad vigente, desde los `legacy_magic_numbers` del registro
  aprobado. 34 magics traducibles. Si estás atribuyendo el histórico, es la pieza que
  necesitas — y ya está cableada en `import_mt5_history_export.py --identity-registry`.
- **`scripts/report_history_attribution.py`**: mide la cobertura de atribución **antes** de
  importar. Correlo sobre los CSV antes de prometer nada: la respuesta es 10,3 % en BEPB y
  8,2 % en JJTI, porque el 87-90 % del histórico es de EAs ya retirados.
- **`scripts/record_directional_reclassification.py`**: persiste una reclasificación sellada
  como evento append-only. Ya aplicado; idempotente si lo reejecutas.

### Tres cosas que descubrí y que afectan a lo que estás haciendo

1. **El histórico no llega a 2018.** Empieza en `2025-02-03` (BEPB) y `2025-03-20` (JJTI).
   Si tu ingesta asume una ventana desde 2018, no la va a encontrar.
2. **Dos EAs siguen emitiendo su magic legacy** tras la migración (`2004262` en BEPB, `2084`
   en JJTI), y tres magics desplegados no están en el lote de 40 (`9519`, `90727`, `0`).
   Medido sobre los deals del 1-2 de septiembre, no deducido de documentos.
3. **La corrida `20260830T210536Z_91538465c20a` tiene evidencia sellada y ningún evento en la
   base.** Si tu cola local la da por registrada, no lo está (`backlog A15`).

### Convenciones que se rompieron una vez y conviene no repetir

- **Toda decisión de contrato va a `ASSUMPTIONS.md`**, no sólo a `phase_status.md`. El
  contrato direccional redefine qué se considera validado y sólo estaba en el estado de fase.
- **Si actualizas un párrafo que otro anterior contradice**, marca el anterior como
  supersedido en el mismo cambio. G13-21 narraba veredictos que G13-25 ya había cambiado.
- **Si un artefacto deja de significar lo que decía, dilo.**
  `docs/registro_BEPB_MN_bots_real_mt5_vps.md` pasó de "observación pre-migración" a "estado
  post-migración" y dejó un test rojo verificando la realidad anterior. Ambos registros llevan
  ya una cabecera que declara a qué momento corresponden — mantenla si los regeneras.
- **Antes de tocar StratOS, lee `AGENTS.md`** (nuevo, en la raíz del subproyecto):
  `docs/phase_status.md` → `ASSUMPTIONS.md` → `docs/backlog.md` → esta auditoría.

### Segunda tanda — lo que cambió después del primer hand-off

El operador desbloqueó casi todo lo que dependía de él y se cerraron A15-A19 más el primer
gate de P5.1. Lo que te afecta directamente:

**Contratos que cambiaron y puedes estar usando**

- **`parse_closed_positions()`** (`import_mt5_history_export.py`) devuelve **tres** valores, no
  dos: el tercero son las traducciones de magic aplicadas. Acepta un `legacy_magic_map`
  opcional.
- **`config/operational_prefilter.json` es `v3`**: `max_per_symbol_timeframe` y `max_mt5_queue`
  planos ya no existen. Ahora hay `validation_queue` e `incubator_admission`, y este último
  incorpora **`max_abs_correlation`** (0.7). Una política v2 se sigue leyendo con su
  comportamiento anterior.
- **`GET /data-provenance`** añade `trade_attribution` (total, atribuidos a bot vivo, de EA
  retirado, sin EA, cobertura). Si lo consumes, el shape creció.
- **`register_external_account.py`** acepta `--data-origin` (`BROKER_REAL` por defecto,
  `BROKER_DEMO` para la Incubadora). `is_demo` se deriva de la procedencia.
- **`reclassify_external_f7_backtests.py`** ya no reevalúa campañas superseded: filtra por
  existencia de la fuente. Su informe trae `superseded_runs` y `summary.superseded`.
- **`ASSUMPTIONS.md` llega a G13-32.** Comprueba el último número antes de añadir el tuyo.
- **Panel `SQX_vs_MT5` en v1.3.3**, con `build_panel_exe.ps1` para regenerar su `.exe`. El
  binario de `dist_legacy` (v1.2.2) está marcado obsoleto: lanzarlo reproduce el `TypeError`
  float/dict porque lleva el código anterior al contrato direccional.

**Piezas nuevas que te ahorran trabajo**

- **`core/services/incubator_admission.py`** — gate con los dos criterios de descorrelación
  (estructural y estadístico), función pura con 13 tests. **Nadie lo llama todavía**: se cablea
  cuando exista el adjunto demo (`backlog A21`).
- **`scripts/sync_bot_magics_to_migration.py`** — alinea el magic de los bots con la identidad
  vigente y, con `--reattribute-orphans`, completa el `bot_id` de los trades que quedaron
  huérfanos por el desfase. **Si vuelves a migrar la identidad de un EA, hay que correrlo
  después**: el registro de identidad y la tabla `bot` no se sincronizan solos.
- **`scripts/report_history_attribution.py`** — mide la cobertura de atribución antes de
  importar nada.

**Tres hallazgos de esta tanda**

1. **Los bots se dieron de alta con los magics de antes de la migración MN.** La atribución
   estaba rota *hacia adelante*: cada operación nueva de un EA migrado entraba huérfana.
   Corregido (34 bots, 26 trades), pero es el patrón a vigilar.
2. **7 de las 11 corridas del informe de reclasificación eran de la campaña anterior** al
   renombrado. Si tu cola las daba por vigentes, no lo son.
3. **La cola F7 regenerada con los retests actualizados no cambió**: mismos 13 `READY` y
   mismos hashes que la del 28-08. Los 2 `PREFLIGHT_OK` pendientes siguen siendo los mismos.

**Estado de la Incubadora**: cuenta `account_id=3` (`5055093171`, `MetaQuotes-Demo`,
`BROKER_DEMO`) registrada, con metadatos leídos del terminal. Faltan el adjunto demo por
gráfico y el consumo de la cola FIFO (`backlog A20`). El operador autorizó a ti y a esta
sesión **cualquier movimiento sobre esa cuenta demo** — no sobre las reales.

**Lo que sigue bloqueado y por qué**: el terminal **Darwinex** está abierto con JJTI/BEPB
conectadas, así que la cola F7 no se puede lanzar sin que el operador lo cierre (`A22`); y los
MCP `mt5_bepb`/`mt5_jjti`/`mt5-darwinex` devuelven `ConnectionRefused`, lo que bloquea la
telemetría viva (`A23`).

### Añade el MCP `stratos` a `.codex/config.toml`

Hoy sólo registra `sqx_forja`. `stratos` es el que expone `scan_hardcoding`, obligatorio por
P11 antes de cerrar unidad.

## 6. Comandos de reproducción

```bash
# Tests de core-engine (Postgres/Redis efímeros, no toca el stack operacional)
docker run -d --name stratos_audit_pg -e POSTGRES_DB=stratos -e POSTGRES_USER=stratos_user \
  -e POSTGRES_PASSWORD=stratos_secret_2026 -p 59432:5432 timescale/timescaledb:2.17.2-pg16
docker run -d --name stratos_audit_redis -p 59379:6379 redis:7-alpine
docker exec stratos_audit_pg psql -U stratos_user -d stratos \
  -c "CREATE USER stratos_app WITH PASSWORD 'stratos_app_secret_2026'; GRANT ALL ON DATABASE stratos TO stratos_app;"

cd core-engine
DATABASE_URL="postgresql+asyncpg://stratos_user:stratos_secret_2026@localhost:59432/stratos" \
APP_DATABASE_URL="postgresql+asyncpg://stratos_app:stratos_app_secret_2026@localhost:59432/stratos" \
REDIS_URL="redis://localhost:59379/0" JWT_SECRET="audit_only" \
../.venv/Scripts/python.exe -m pytest tests -q --ignore=tests/e2e/test_g8_acceptance_criteria.py

docker rm -f stratos_audit_pg stratos_audit_redis
```

```bash
# Lint / typecheck / resto de suites
.venv/Scripts/python.exe -m ruff check core-engine/
.venv/Scripts/python.exe -m ruff format --check core-engine/
.venv/Scripts/python.exe -m mypy --config-file core-engine/pyproject.toml core-engine/src/ --strict
.venv/Scripts/python.exe -m pytest scripts/tests -q
cd frontend && npx vitest run
```
