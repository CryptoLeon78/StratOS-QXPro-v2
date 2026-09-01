# Plan de continuación — StratOS a producción — 2026-09-02

Derivado de [`AUDITORIA_2026-09-02.md`](AUDITORIA_2026-09-02.md). Ordenado por **prioridad de
implementación**, no por esfuerzo: cada bloque desbloquea al siguiente.

## Qué significa aquí "productivo"

Conviene separar dos metas que se confunden, porque tienen gates distintos:

- **Productivo como observatorio** — StratOS refleja con fidelidad lo que hacen JJTI y BEPB: cada
  trade atribuido a su bot, semáforos evaluando sobre datos reales, alertas y auditoría con
  significado. **Alcanzable ahora.** No requiere que StratOS opere nada.
- **Productivo como gestor** — la Incubadora admite candidatos, el kill-switch y las promociones
  actúan. **Requiere cuenta `BROKER_DEMO` y gates de backtest/baseline**, ninguno de los cuales
  existe hoy.

El camino corto a valor real es el primero. El segundo se construye encima.

---

## P0 — Recuperar las garantías · BLOQUEA TODO LO DEMÁS

Sin esto, cualquier trabajo posterior se apila sobre una base que nadie puede revisar ni revertir.

### P0.1 — Commitear G11/G12/G13 · `backlog A1`

194 ficheros en el working tree. **Por unidades temáticas, no en un commit único**:

1. `feat(core): esquema y migraciones G11/G13` — las 7 revisiones Alembic + `db/models/operations.py`
   + `db/enums.py`/`sa_enums.py`.
2. `feat(core): procedencia y admisión operacional` — routers/servicios con `data_origin`,
   `admin_imports.py`, `pipeline_history.py`, `sqx_baseline_parser.py`, `tca.py`.
3. `feat(scripts): campaña demo G12` — todo `*_g12_*`.
4. `feat(scripts): stack operacional G13` — inventario, prefiltro, resolutor, extractor de evidencia.
5. `feat(scripts): identidad de magics y cola F7` — `magic_identity*`, `*_live_backtest_queue*`,
   `scan_mt5_chart_identity.py`, `reclassify_external_f7_backtests.py`.
6. `feat(mt5-connector): reporter outbox y exportador de histórico`.
7. `feat(frontend): procedencia en Bots/Pipeline/Cuentas-EA`.
8. `docs: G12/G13 + auditoría 2026-09-02`.

**Antes de pushear**, revisar que `.gitignore` cubre `runtime/`, `.env*` reales, `dist/` y las
capturas de evidencia. Un push que arrastre `runtime/operational/` publicaría rutas y hashes de
cuentas reales en un repo de GitHub.

**Higiene aparte**: el repo padre `SQX_144_Full2` tiene ficheros de StratOS en su propio índice a la
vez que StratOS es un repo anidado con remoto propio. Decidir uno de los dos modelos —submódulo, o
ignorar `StratOS-QXPro-v2/` en el padre— y aplicarlo. Hoy los dos índices se pisan.

### P0.2 — CI verde · `backlog A2, A3, A4, A5`

En este orden, porque los tres primeros son mecánicos y el cuarto exige una decisión:

1. `ruff check --fix core-engine/` + `ruff format core-engine/` (7 + 8).
2. mypy: corregir las anotaciones de retorno de `routers/pipeline.py` (3) y `routers/bots.py`
   (`-> PipelineCandidate`/`-> Bot` cuando devuelven la respuesta Pydantic), anotar
   `account_brokers` en `services/tca.py`, y **añadir la guarda de `None`** en `get_bot` antes de
   `account.data_origin` — no porque sea explotable hoy, sino porque es el contrato que `--strict`
   está comprobando.
3. `EXPECTED_TABLE_COUNT` de 30 → 36 en `test_migration.py`, con las 6 tablas nuevas nombradas en el
   propio test para que el siguiente cambio de esquema falle con un mensaje útil.
4. **Decisión de Ivan** sobre `docs/registro_BEPB_MN_bots_real_mt5_vps.md`: ¿es la observación
   pre-migración (evidencia histórica) o el estado post-migración? Si es lo segundo, el test debe
   verificar la colisión `magic=10827` contra `runtime/.../bepb_magic_manifest.json`, que sí la
   conserva, y el documento necesita una cabecera que declare a qué momento corresponde.

Después: **push y confirmar CI verde real**. Es la primera vez que G11-G13 pasarían por CI.

### P0.3 — Retirar o regenerar el `.exe` · `backlog A6`

`dist/StratOS_Operational.exe` es del 30/08, 23 scripts por detrás. Mientras no se regenere con
`scripts/build_stratos_operational_exe.ps1`, **dejar de presentarlo como punto de entrada** en
`phase_status.md` y en el README. Es la vía más probable de que una decisión se tome con el criterio
anterior al contrato direccional.

---

## P1 — Cerrar lo que corrompe decisiones

### P1.1 — Persistir la reclasificación direccional · `backlog A7`

Añadir un evento append-only a `operational_asset_event` por cada corrida reevaluada, con el
veredicto nuevo, el hash del manifiesto original y la referencia a G13-25. No sustituye a los
eventos previos: los complementa. Hoy la verdad contractual vigente vive en un JSON suelto y el
sistema no la conoce.

### P1.2 — Arreglar la extracción de símbolo · `backlog A9`

Quitar de `alias_simbolos` las dos entradas que no son alias (`AUDNZDH4BUY_edge_1.16.34` y la
identidad `USDJPY: USDJPY`) y arreglar el resolutor que las hizo necesarias. Con test sobre la
estrategia que falló. Cada estrategia futura con ese patrón necesitaría hoy su propia línea de
configuración.

### P1.3 — `scan_hardcoding` consolidado de G12/G13 · `backlog A8`

Barrido clasificado uno a uno, como el que cerró G10 en su grupo (o): cada hallazgo o se migra a
configuración, o se justifica en `ASSUMPTIONS.md` con su origen. Los de `seed_lib/` ya están
aceptados como deuda de fixture; los de los scripts operacionales nuevos, no.

---

## P2 — Observatorio fiel: atribuir los trades reales a sus bots

**Este es el bloque que convierte StratOS en algo con valor diario.** Hoy los 4.304 trades
importados son **huérfanos**: el HTML de Darwinex no publica magic, así que ninguno está atribuido a
un bot y todas las métricas por bot de cuentas reales están vacías.

### P2.1 — Ejecutar el exportador de histórico · acción de Ivan

`StratOSHistoryExport.mq5` usa `HistorySelect`/`HistoryDealGet*`, que **sí exponen el magic real de
cada deal**. Está escrito, compilado y con tests de seguridad; nunca se ha ejecutado. Está bloqueado
a propósito: lanzarlo por `terminal64.exe /config` abriría/cerraría la instancia de producción.

La vía segura es **manual**, desde la sesión MT5 ya abierta de cada terminal: adjuntar el script a
un gráfico, dejarlo escribir su CSV y sellarlo con `import_mt5_history_export.py` (que ya convierte
`Europe/Helsinki`→UTC y archiva el CSV como evidencia inmutable). Requiere 15 minutos de Ivan en
cada VPS, no automatización.

Resultado: histórico desde 2018 **con magic**, atribuible a los 40 bots F7 vía la identidad MN
aprobada. Es el desbloqueo con mejor relación valor/esfuerzo de todo este plan.

### P2.2 — Reconciliar los huérfanos existentes

Con el histórico CSV sellado, contrastar contra los 4.304 trades HTML. Donde coincidan posición,
símbolo, volumen, hora y precio, el CSV aporta el magic que al HTML le falta. **Sin heurística de
nombre ni de comentario** — el criterio de G13-12 se mantiene: lo que no reconcilie de forma única
sigue huérfano y se declara como tal.

### P2.3 — Telemetría viva de las cuentas reales

Con el histórico atribuido, decidir con Ivan si el conector read-only pasa a leer JJTI/BEPB en
continuo (heartbeat, equity, posiciones abiertas), como ya hizo en la demo de G12. **No requiere
tocar ningún EA** ni habilitar AutoTrading. Es lo que hace que los semáforos y la vista Dominical
tengan sentido sobre cuentas reales.

---

## P3 — Cerrar el veredicto de alpha decay de la cola F7

Reanudable **sólo cuando Ivan confirme** que los retests SQX están alineados; la cola sigue en pausa
explícita desde el 2026-08-31.

- 2 expedientes `PREFLIGHT_OK` sin lanzar: `USDJPYH1Lcity_3.16.113`, `USDJPYH1Lcity_2.22.171`.
- 7 `WITHHELD_TICKS` por alias/cobertura Darwinex: revisar si el arreglo de P1.2 desbloquea alguno.
- 43 retenidas por fuente en la cola de 56 (ventana, identidad, ambigüedad).

Al cerrar la campaña, **el entregable es un veredicto por bot del stock real**, no una lista de
corridas: qué estrategias siguen reproduciendo su backtest en tick real y cuáles no. Eso es lo que
alimenta las decisiones de retirada que el registro de veredictos ya empezó en agosto.

---

## P4 — UI: procedencia completa y recorrido autenticado

- Etiquetas y filtros de procedencia (`BROKER_REAL` / `BROKER_DEMO` / `FIXTURE` / `DERIVED` /
  `ABSENT`) en las 5 pestañas que faltan: Portfolio, Salud, Riesgo, Auditoría, Dominical. Bots,
  Pipeline y Cuentas/EA ya las tienen.
- Recorrido autenticado con WebSocket contra `stratos_operational`, que nunca se hizo.
- Con procedencia en todas las superficies, **retirar el fixture `full` del stack operacional**: hoy
  varias vistas agregan fixture y telemetría real en la misma cifra, que es el hallazgo abierto de
  G12 y la razón por la que el operador no se fía de los números del Resumen.
- Regenerar los baselines de Playwright (son de G10) y volver a poner `e2e-playwright` en verde.

---

## P5 — Incubadora: de observatorio a gestor

Sólo después de P0-P4. Gates en orden:

1. Registrar una cuenta `BROKER_DEMO` real y su terminal.
2. Implementar el adjunto demo por gráfico (hoy el lanzador termina declarando la Incubadora
   bloqueada precisamente aquí).
3. Consumir la cola FIFO hasta el tope de 8, con el contrato de gracia ya definido: sizing 10 %,
   riesgo 0,2 %, DD contractual 5 %.
4. Sólo entonces, semáforos y kill-switch actuando de verdad.

El prefiltro tiene 217 estrategias que superan criterios pero sólo expone 2 por el tope de
diversidad `AUDCAD/H4`. **Antes de P5 conviene revisar ese tope con Ivan**: 215 en
`HOLD_DIVERSITY_CAP` sobre un solo par/timeframe sugiere que el universo de Análisis está mucho más
concentrado de lo que un portfolio debería aceptar, y eso es una conclusión de negocio, no un
parámetro de cola.

---

## P6 — Higiene de entorno · sin urgencia, sin bloqueo

- **`SQX_Edge_Suite_v1`** (`backlog A10`): proyecto grande, sin git, inactivo desde 2026-08-14, con
  gobierno propio y ausente de todos los índices. Decidir: versionar, archivar o retirar.
- **`PIPELINE_MINADO_A_FINALISTAS.md`** sigue hablando de "9 apps de entorno" cuando
  `Apps_entorno_SQX/` tiene 14 directorios.
- **`.codex/config.toml`** sólo registra el MCP `sqx_forja`. Añadir `stratos` (es el que expone
  `scan_hardcoding`, obligatorio por P11) y `mt5_bridge`.

---

## Secuencia recomendada

| Orden | Bloque | Depende de | Quién |
|---|---|---|---|
| 1 | P0.1 commit + P0.2 CI verde | — | agente |
| 2 | P0.3 exe, P1.1 persistir reclasificación, P1.2 alias | P0.1 | agente |
| 3 | **P2.1 exportador de histórico** | — (paralelizable con 1-2) | **Ivan, manual en cada VPS** |
| 4 | P2.2 reconciliación + P2.3 telemetría viva | P2.1 | agente |
| 5 | P1.3 scan consolidado | P0.2 | agente |
| 6 | P3 cola F7 | confirmación de Ivan sobre retests SQX | agente + Ivan |
| 7 | P4 UI y retirada del fixture | P2 | agente |
| 8 | P5 Incubadora | P4 + cuenta demo | agente + Ivan |

**P2.1 no depende de nada y lo tiene que hacer Ivan**: conviene arrancarlo ya, en paralelo con P0.
Es el único paso del plan con un cuello de botella humano y el que más valor libera.
