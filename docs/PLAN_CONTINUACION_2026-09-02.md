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

## P0 — Recuperar las garantías · EJECUTADO 2026-09-02

### P0.1 — Commitear G11/G12/G13 · `backlog A1` — HECHO

Nueve commits temáticos sobre `main`, de 194 ficheros pendientes a 0 (salvo lo que Codex
tenía abierto en ese momento): esquema y migraciones · procedencia/admisión/TCA en la API ·
campaña demo G12 · stack operacional G13 · identidad de magics y cola F7 · conector, reporter
e importadores · frontend · seed y configuración de entorno · documentación.

**Dos correcciones de `.gitignore` que salieron al preparar el push**, ambas verificadas con
`git check-ignore`:

- `.env.operational.example` **estaba ignorado**: la regla `.env.*` lo capturaba y
  `!.env.example` no lo desexcluía. `phase_status.md` afirma que es la única plantilla
  versionada, y no se estaba versionando. Corregido con `!.env.*.example`.
- `docs/history_deals_*.csv` **se habrían commiteado**: 9.082 deals de dos cuentas Darwinex
  reales con precio, volumen, profit, comisión y swap. Es evidencia operativa, no
  documentación; su sitio es `runtime/operational/history/`. Ignorados donde están mientras
  la ingesta los lea de `docs/`.

Los `docs/registro_*_MN_*.md` sí se versionan: el repo es privado y un test depende de ellos.

**Pendiente**: `git push` y confirmar el primer CI real de G11-G13. **Higiene aparte**: el
repo padre `SQX_144_Full2` tiene ficheros de StratOS en su índice a la vez que StratOS es un
repo anidado con remoto propio. Decidir un modelo —submódulo, o ignorar
`StratOS-QXPro-v2/` en el padre— y aplicarlo.

### P0.2 — CI verde · `backlog A2, A3, A4, A5` — HECHO

| Comprobación | Antes | Ahora |
|---|---|---|
| `ruff check core-engine/` | 7 errores | **All checks passed** |
| `ruff format --check core-engine/` | 8 ficheros | **210 already formatted** |
| `mypy --strict core-engine/src/` | 7 errores | **Success, 108 ficheros** |
| `pytest core-engine/tests` | 598 + 1 fallo | **600 passed** |
| `pytest scripts/tests` | 120 + 1 fallo | **126 passed** |
| `pytest frontend` (vitest) | 50/50 | 50/50 |

De los arreglos, dos merecen mención por lo que revelaron:

- **`routers/bots.py::get_bot` accedía a `account.data_origin` sin comprobar `None`.** No es
  explotable hoy (`Bot.account_id` es `NOT NULL` con FK), pero se añadió la guarda: si algún
  día ocurre, la procedencia es desconocida y se declara ausente en vez de reventar.
- **`test_migration.py` pasa de contar tablas a nombrarlas.** El recuento suelto no decía
  cuál faltaba; ahora un test aparte verifica las 6 tablas de G11/G13 por nombre.

**A5 resuelto, y con un hallazgo positivo**: el test que fallaba verificaba la colisión BEPB
`magic=10827` leyendo el registro post-migración. **La migración MN resolvió esa colisión** —
`DAX40H1stat_5.29.24` pasó a `10829` y `5.27.28` conservó `10827`. Cada propiedad se verifica
ahora contra la fuente que de verdad la afirma: la colisión pre-migración contra el
manifiesto sellado (evidencia inmutable), la unicidad de magics y la coherencia
`comment == <label>_MN<magic>` contra los registros post-migración. Ambos documentos llevan
ya una cabecera que declara a qué momento corresponden.

### P0.3 — Retirar o regenerar el `.exe` · `backlog A6` — PENDIENTE

`dist/StratOS_Operational.exe` sigue siendo del 30/08, ahora **con más scripts por detrás**.
Regenerarlo con `scripts/build_stratos_operational_exe.ps1` tras el push, o dejar de
presentarlo como punto de entrada. Es la vía más probable de que una decisión se tome con el
criterio anterior al contrato direccional.

---

## P0-bis — Correcciones extra aplicadas 2026-09-02

Fuera del plan original, salieron al trabajar y están hechas y probadas.

### Salvaguarda de símbolo en el flujo de lote · panel v1.3.1

A petición del operador. El backtest individual ya bloqueaba el Tester cuando el símbolo MT5
no coincidía con el del `.sqx` y exigía confirmación —**eso ya estaba**—, pero **el lote no
la pedía**: corre desatendido, así que cada estrategia con alias se saltaba con `ERROR` una a
una y el operador se enteraba al final de una corrida larga.

- `POST /api/lote_simbolos` clasifica el databank **antes** de arrancar, leyendo sólo
  símbolo/timeframe del `lastSettings.xml` de cada `.sqx` — sin parsear operaciones y sin
  tocar el terminal. Devuelve `sustituciones`, `sin_resolver` e `ilegibles`.
- El panel enseña la lista exacta y pide **una sola confirmación informada** para todo el
  lote. Diálogo dibujado en la página, nunca `window.confirm()`.

**Y un fallo de diseño que apareció al probarlo contra un databank real**:
`simbolo_distinto_de_sqx` comparaba los símbolos **crudos**, así que `SPA35_darwinex` frente
a `SPA35` contaba como sustitución que requiere aprobación humana. Es el mismo instrumento —
el sufijo lo pega SQX al importar del bróker— y **la mayoría de los símbolos lo llevan**: la
salvaguarda saltaba en 3 de 3 estrategias del databank probado. Una alerta que salta siempre
entrena al operador a confirmar por costumbre y deja de proteger contra el caso que sí
importa. Ahora se comparan los símbolos **normalizados**: `SPA35_darwinex → SPA35` y
`GDAXIdarwinex → GDAXI` pasan sin preguntar; `DAX40 → GDAXI` y `NASDAQ → NDX` siguen
exigiendo confirmación.

7 casos nuevos en `tests/test_lote_simbolos.py` (17/17 en el panel) y verificado contra un
databank del disco. Uno de esos tests encontró un fallo real en la primera implementación: se
capturaba `SystemExit` donde `abortar()` lanza `ErrorComparacion`, así que un `.sqx` ilegible
habría tumbado el preflight entero.

### Documentación

`ASSUMPTIONS.md` G13-25 (contrato direccional, que no tenía entrada propia), colisión de
numeración `G13-24` resuelta, veredictos supersedidos marcados en `phase_status.md` G13-21,
`README`/`architecture` desbloqueados de G11, `AGENTS.md` propio del subproyecto, índices de
la raíz corregidos (apuntaban a un `instrucciones para Codex\` inexistente) y
`CHANGELOG_panel.md` v1.3.0/v1.3.1.

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

**ACTUALIZADO 2026-09-02**: el operador ya ejecutó `StratOSHistoryExport.mq5` en los dos
terminales. Los CSV están en `docs/history_deals_BEPB.csv` y `docs/history_deals_JJTI.csv`
(ignorados por Git: son evidencia operativa, su sitio es `runtime/operational/history/`).
Codex está analizándolos. Lo que sigue son los hechos medidos sobre esos ficheros, para que
la ingesta no se construya sobre supuestos.

### P2.0 — Lo que el export dice de verdad

| | BEPB | JJTI |
|---|---|---|
| Deals | 4.993 | 4.087 |
| Magics distintos | 203 | 128 |
| `magic=0` (sin EA) | 124 (2,5 %) | 58 (1,4 %) |
| Rango temporal | 2025-02-03 → 2026-09-01 | 2025-03-20 → 2026-09-01 |

**Tres consecuencias que cambian el plan:**

1. **El histórico NO llega a 2018.** El caché de deals del terminal empieza en feb/mar de
   2025 — unos 19 meses, no 8 años. `docs/backlog.md` y `phase_status.md` daban por hecho
   "sellar su importación desde 2018"; eso **no es alcanzable con este export**. La ventana
   real hay que declararla como tal y decidir si se busca otra fuente (estados de cuenta de
   Darwinex) o si 19 meses bastan para el propósito.
2. **Hay 203 y 128 magics distintos frente a 32 y 24 EAs registrados.** Es lo esperable
   tras años de rotación y tras la migración MN, pero significa que la atribución **no puede
   ser un `JOIN` por magic actual**: la mayoría de los deals históricos llevan magics de EAs
   ya retirados o el magic *anterior* a la migración.
3. **El mapeo existe**: `magic_identity_registry.jsonl` guarda `legacy_magic_numbers` por
   cada `ASSIGNED`, así que un deal con magic viejo se puede atribuir a la identidad actual.
   Lo que no cubra ese mapeo se queda huérfano y se declara, no se adivina.

### P2.1 — Estado real de la migración MN, medido sobre los deals · NUEVO

Contrastando los magics emitidos en los deals del **1-2 de septiembre** (ya con los perfiles
guardados) contra los 40 `ASSIGNED` aprobados:

| Cuenta | Magic nuevo | Legacy rezagado | Fuera del lote |
|---|---|---|---|
| BEPB | 14 deals | 1 (`2004262`) | `9519`, `0` |
| JJTI | 14 deals | 1 (`2084`) | `90727` |

- **La migración está aplicada casi por completo**, pero quedan **dos EAs rezagados** que
  siguen emitiendo su magic anterior: `2004262` (debería emitir el de
  `EUUSH1Seof_7.30.121_MN5`) y `2084` (el de `EURJPYM15L_1.29.59_MN9`). Revisar esos dos
  gráficos en el terminal.
- **Tres magics no pertenecen al lote aprobado de 40**: `9519` y `90727` corresponden a EAs
  desplegados que no entraron en la propuesta, y `0` son operaciones sin EA (manuales o del
  bróker). No son un error de la migración, pero sí un hueco de inventario.
- **Aviso para el cierre de G13**: ninguno de los 40 `comment_identity` aprobados coincide
  literalmente con los de `docs/registro_*_MN_*.md`, porque esos documentos registran el
  comment con el magic *legacy* (`XAUH1BUYSTOPeof_1.8.81_MN7786`) mientras la propuesta
  aprobada asigna magics cortos (`..._MN1`). Los deals reales demuestran que lo desplegado
  usa los magics **nuevos**, así que son los registros `_MN_*.md` los que están
  desactualizados respecto al despliegue, no al revés. **Conviene regenerarlos desde el
  post-scan** en vez de mantenerlos a mano.

### P2.2 — Ingesta y reconciliación

Con los CSV sellados por `import_mt5_history_export.py` (que ya convierte
`Europe/Helsinki`→UTC y archiva el CSV como evidencia inmutable):

- Atribuir cada deal vía magic actual **o** `legacy_magic_numbers`, registrando por cuál de
  los dos caminos se resolvió. Lo que no resuelva ninguno queda huérfano y se declara.
- Contrastar contra los 4.304 trades HTML ya importados: donde coincidan posición, símbolo,
  volumen, hora y precio, el CSV aporta el magic que al HTML le falta. **Sin heurística de
  nombre ni de comentario** — se mantiene el criterio de G13-12.
- Cuidado con el solape: el HTML y el CSV cubren periodos que se pisan. La ingesta tiene que
  ser idempotente por `deal_ticket`/`position_id`, no crear duplicados.

### P2.3 — Telemetría viva de las cuentas reales

Con el histórico atribuido, decidir con el operador si el conector read-only pasa a leer
JJTI/BEPB en continuo (heartbeat, equity, posiciones abiertas), como ya hizo en la demo de
G12. **No requiere tocar ningún EA** ni habilitar AutoTrading. Es lo que hace que los
semáforos y la vista Dominical tengan sentido sobre cuentas reales.

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

## P5 — Incubadora: abrir la puerta a más candidatas, y de observatorio a gestor

### P5.0 — El tope de diversidad, decidido · ACLARADO POR EL OPERADOR 2026-09-02

Hoy 217 estrategias superan el prefiltro y sólo **2** llegan a la cola: el tope de
diversidad por `símbolo/timeframe` deja 215 en `HOLD_DIVERSITY_CAP` porque todas son
`AUDCAD/H4`. El operador pide abrir la puerta a más candidatas.

**Lo importante es no confundir dos cosas que el tope actual mezcla:** limitar cuántas
estrategias *entran a la Incubadora* (una restricción de portfolio, correcta y necesaria) y
limitar cuántas *se comparan contra MT5* (una restricción de CPU, que no tiene por qué ser
la misma). Hoy un solo número hace las dos, y por eso 215 candidatas están paradas.

**Propuesta — separar el tope en dos, ambos configurables en `operational_prefilter.json`:**

1. **Tope de validación** (cuántas van al Strategy Tester por tanda). Sube de 2 a lo que
   admita el presupuesto de CPU, sin límite por símbolo: validar 20 `AUDCAD/H4` no
   concentra riesgo, sólo gasta cómputo. Es reversible y no toca ninguna cuenta.
2. **Tope de admisión a Incubadora** (cuántas de las validadas pueden convivir). **Aquí sí**
   se conserva el límite por `símbolo/timeframe`, porque ocho bots del mismo par en el mismo
   marco temporal no son ocho apuestas: son una apuesta con ocho nombres, y el kill-switch
   las vería caer juntas.

**Además, un criterio de diversidad que hoy no existe y es el que de verdad importa**: la
correlación entre curvas de equity. Dos `AUDCAD/H4` con reglas distintas y correlación 0,2
diversifican; dos con correlación 0,9 no, aunque el tope por símbolo las deje pasar. El
sistema **ya tiene la pieza**: `services/correlations.py` y `is_redundant_pair` (G8, criterio
9). Reutilizarla en la admisión es más trabajo que subir un número, pero es la diferencia
entre un tope que aproxima la diversidad y uno que la mide.

**Orden sugerido**: (1) subir el tope de validación ya — desbloquea las 215 sin ningún riesgo;
(2) al admitir a Incubadora, aplicar tope por símbolo/TF **más** el filtro de correlación.

**Conclusión de negocio que no hay que perder de vista**: que 215 de 217 candidatas sean el
mismo par y marco temporal dice que el universo de Análisis está mucho más concentrado de lo
que un portfolio debería aceptar. Subir el tope resuelve el atasco; **no** resuelve la
concentración. Eso se arregla minando otros activos, no ajustando la cola.

### P5.1 — Gates hacia gestor

Sólo después de P0-P4. En orden:

1. Registrar una cuenta `BROKER_DEMO` real y su terminal.
2. Implementar el adjunto demo por gráfico (hoy el lanzador termina declarando la Incubadora
   bloqueada precisamente aquí).
3. Consumir la cola FIFO hasta el tope de 8, con el contrato de gracia ya definido: sizing
   10 %, riesgo 0,2 %, DD contractual 5 %.
4. Sólo entonces, semáforos y kill-switch actuando de verdad.

## P6 — Higiene de entorno · sin urgencia, sin bloqueo

- **`SQX_Edge_Suite_v1`** (`backlog A10`): proyecto grande, sin git, inactivo desde 2026-08-14, con
  gobierno propio y ausente de todos los índices. Decidir: versionar, archivar o retirar.
- **`PIPELINE_MINADO_A_FINALISTAS.md`** sigue hablando de "9 apps de entorno" cuando
  `Apps_entorno_SQX/` tiene 14 directorios.
- **`.codex/config.toml`** sólo registra el MCP `sqx_forja`. Añadir `stratos` (es el que expone
  `scan_hardcoding`, obligatorio por P11) y `mt5_bridge`.

---

## Secuencia recomendada

| Orden | Bloque | Estado | Quién |
|---|---|---|---|
| 1 | P0.1 commit + P0.2 CI verde | **HECHO 2026-09-02** (falta el `push`) | agente |
| 2 | P0-bis salvaguarda de símbolo en lote | **HECHO 2026-09-02** | agente |
| 3 | P2.1 exportador de histórico | **HECHO** — CSV en `docs/`, analizándose | **Ivan** |
| 4 | P0.3 exe, P1.1 persistir reclasificación, P1.2 alias | pendiente | agente |
| 5 | P2.2 ingesta y reconciliación del histórico | pendiente | agente |
| 6 | **P5.0 subir el tope de validación** | pendiente — desbloquea 215 candidatas sin riesgo | agente |
| 7 | P1.3 scan consolidado | pendiente | agente |
| 8 | P3 cola F7 | esperando confirmación de Ivan sobre los retests SQX | agente + Ivan |
| 9 | P2.3 telemetría viva + P4 UI y retirada del fixture | pendiente | agente |
| 10 | P5.1 Incubadora | pendiente — necesita cuenta demo | agente + Ivan |

**Lo más rentable ahora mismo**: (4) y (5) — la reclasificación y el alias corrompen
decisiones, y la ingesta del histórico es lo que convierte a StratOS en observatorio real.
**Y (6), que es una línea de configuración y libera 215 candidatas paradas.**

## Dos cosas que exigen decisión del operador

1. **El histórico no llega a 2018, sino a feb/mar 2025** (P2.0). ¿Se busca otra fuente para
   el tramo anterior, o 19 meses bastan? La documentación actual promete 2018 y eso hay que
   corregirlo en cualquier caso.
2. **Dos EAs rezagados siguen emitiendo su magic legacy** tras la migración MN (P2.1), y
   tres magics desplegados no pertenecen al lote aprobado de 40. Revisar en el terminal
   antes de dar la migración por cerrada.
