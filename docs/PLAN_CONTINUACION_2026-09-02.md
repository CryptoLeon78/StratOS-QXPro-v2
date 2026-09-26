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

### P0.3 — Regenerar el `.exe` · `backlog A6` — HECHO

Regenerado con `scripts/build_stratos_operational_exe.ps1` tras conservar copia del binario
anterior. **0 scripts por detrás** (antes 23) y arranque verificado sin abrir MT5. Ya no es
una vía por la que una decisión pueda tomarse con el criterio anterior al contrato
direccional.

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

## P1 — Cerrar lo que corrompe decisiones · EJECUTADO 2026-09-02

### P1.1 — Persistir la reclasificación direccional · `backlog A7` — HECHO

`record_directional_reclassification.py` añade un evento append-only por cada corrida cuyo
veredicto **cambió**, enlazado al `run_id`, al hash del manifiesto original y al del propio
payload de reclasificación. No reescribe nada; reafirmar un veredicto idéntico no se
registra. Un F7 externo se mantiene `WITHHELD` aunque suba a `VALIDADA`: la reclasificación
es contractual, no una promoción.

Aplicado al stack operacional: **2 eventos persistidos** (`asset_id=244`
TOLERABLE→VALIDADA, `asset_id=246` DISCREPANTE→TOLERABLE), idempotencia verificada con una
segunda ejecución.

**Hallazgo nuevo**: la tercera corrida con cambio, `20260830T210536Z_91538465c20a`
(TOLERABLE→VALIDADA), quedó **RETENIDA** — su evidencia está sellada en disco pero **nunca
se registró en la base**. Hay una comparación completada que el sistema no conoce. El
fail-closed es por entrada, no por lote: se retiene y se reporta, sin impedir que las demás
se persistan y sin inventar el evento que falta. Registrarla con
`record_operational_backtest.py` es tarea pendiente (`backlog A15`).

### P1.2 — Arreglar la extracción de símbolo · `backlog A9` — HECHO

La causa raíz no era el alias: **el campo `symbol` de la cabecera binaria del `.sqx` no
siempre contiene un símbolo**. En **27 de 73** `.sqx` reales del stock trae el nombre de la
estrategia (`AUDNZDH4BUY_edge_1.16.34`, `EURGBP_H1_LS_volumen_Strategy 2.4.18`), mientras el
`Chart` de `lastSettings.xml` sí declara el instrumento (`AUDNZD_darwinex`,
`EURGBP_darwinex`). El 37 % de los `.sqx`, no un caso aislado.

`resolver_simbolo_del_sqx()` hace que **mande `lastSettings.xml`**, con la cabecera como
único fallback, y deja aviso en el informe cuando discrepan para que la sustitución no sea
silenciosa. `alias_simbolos` queda limpio con sus **3 alias reales** (`NASDAQ→NDX`,
`DAX40→GDAXI`, `USA30IDXUSD→WS30`); las entradas parche desaparecen. Verificado: **73/73
`.sqx` resuelven su símbolo sin ningún alias parche**.

### P1.3 — `scan_hardcoding` consolidado · `backlog A8` — HECHO

Barrido clasificado uno a uno, como el de G10 en su grupo (o). Cinco literales migrados a
constante con nombre y origen (`SECRET_TOKEN_BYTES`, `MIN_OPERATOR_PASSWORD_LENGTH`,
`EXPECTED_SURVIVOR_COUNT`, `EXPECTED_READY_COUNT`, `MT5_CHART_ID_BASE`). El resto,
clasificado y justificado en `ASSUMPTIONS.md` G13-28: formato de fichero ajeno (la plantilla
`.chr` de MetaTrader y el codec `utf-16`), estructura de datos externos (tipos de registro
del parser binario SQX, celdas del HTML de Darwinex, timeout de subproceso) y el prefijo de
hash ya justificado en G13-19. Los ~250 de `seed_lib/` siguen siendo deuda de fixture
aceptada desde G8.

**El único hallazgo que resultó ser un umbral real** —y no un falso positivo— fue el tope de
diversidad del prefiltro, corregido en P5.0.

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

1. **El histórico NO llega a 2018 — DECIDIDO 2026-09-02.** El caché de deals del terminal
   empieza en feb/mar de 2025: unos 19 meses, no 8 años. `docs/backlog.md` y
   `phase_status.md` daban por hecho "sellar su importación desde 2018". **El operador
   confirma que 19 meses bastan**: no se busca otra fuente para el tramo anterior, la ventana
   real es la ventana del sistema y la documentación que prometía 2018 queda corregida.
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

- **MIGRACIÓN CERRADA 2026-09-02**: el operador revisó ambos terminales y confirma que la
  configuración es correcta. Los dos EAs que se midieron emitiendo su magic anterior
  (`2004262` y `2084`) y los tres magics fuera del lote (`9519`, `90727`, `0`) no son un
  fallo de la migración: corresponden a EAs desplegados que no entraron en la propuesta y a
  operaciones sin EA. Lo que sigue es el detalle de la medición, conservado como evidencia.
- La migración estaba aplicada casi por completo cuando se midió: **dos EAs seguían
  emitiendo su magic anterior**, `2004262` (el de `EUUSH1Seof_7.30.121_MN5`) y `2084` (el de
  `EURJPYM15L_1.29.59_MN9`). Se revisaron esos dos
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

### P2.2 — Atribución del histórico · HECHO 2026-09-02

`build_legacy_magic_map()` traduce los magics anteriores a la migración usando
**exclusivamente** los `legacy_magic_numbers` del registro append-only aprobado — nunca por
nombre ni por comentario. Si dos identidades declarasen el mismo legacy, ese magic no
traduce: una atribución ambigua es peor que ninguna. 34 magics resultan traducibles.

`import_mt5_history_export.py` acepta `--identity-registry` y **sella la traducción en el
artefacto** (`legacy_magic_translations`, con el recuento por magic viejo), para que la
atribución quede auditable en vez de aplicarse en silencio. Sin el flag, el magic entra tal
cual y nada cambia.

`report_history_attribution.py` mide la cobertura **antes** de importar, en cuatro
categorías excluyentes. Sobre el export real:

| | Deals | Sin traducir | Traduciendo | Sin identidad |
|---|---|---|---|---|
| BEPB | 4.993 | 2,3 % | **10,3 %** | 87,2 % |
| JJTI | 4.087 | 1,1 % | **8,2 %** | 90,4 % |

**La traducción triplica la cobertura, y aun así el 87-90 % del histórico queda huérfano.**
No es un fallo del importador: son EAs ya retirados, lo que hay en un portfolio con años de
rotación. Conviene tenerlo medido antes de prometer métricas por bot sobre el histórico
completo — las métricas por bot de cuentas reales sólo cubrirán, de forma realista, a los EAs
vivos y su ventana desde 2025.

**Falta ejecutar la importación** contra el stack operacional. La pieza está construida y
probada; el paso es una decisión de cuándo, no de si se puede.

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

## P4 — UI: procedencia completa · PARCIALMENTE EJECUTADO 2026-09-02

### P4.1 — Procedencia en las 5 vistas agregadas — HECHO

El hallazgo abierto de G12 era que Portfolio, Salud, Riesgo, Auditoría y Dominical sumaban
fixture y telemetría real en la misma cifra sin que nada lo dijera. En esas superficies **la
procedencia no es un campo de una fila** —como en Bots o Pipeline— sino una propiedad del
agregado, y por eso no bastaba con replicar el patrón existente.

`GET /data-provenance` declara la composición real: cuentas y bots por `data_origin`, más un
`is_mixed` que es el dato accionable. Con un solo origen las cifras significan una cosa; con
varios, cualquier total agrega universos distintos. Una base vacía es ausencia, no mezcla.
`ProvenanceBadge` lo muestra en las cinco páginas y no afirma nada mientras carga.

De paso, `CandidateCard` mostraba el enum en bruto (`BROKER_REAL · EXTERNAL_PRODUCTION`) sin
pasar por `ui_strings`, contra P11.

TDD real: los 3 tests del endpoint se confirmaron rojos (404) antes de implementarlo.
**Verificado en vivo** contra el stack operacional tras reconstruir la imagen:
`{"data_origin":"BROKER_REAL","accounts":2,"bots":40}`, `is_mixed=false` — correcto, el perfil
operacional rechaza fixture por diseño.

### P4.2 — Recorrido autenticado y WebSocket — PENDIENTE, REQUIERE AL OPERADOR

**La vista autenticada no se ha comprobado en navegador**: `/login` exige credenciales que se
entregaron una sola vez fuera del repositorio. Un agente no debe introducirlas. Queda para el
operador: abrir las cinco pestañas y confirmar que el badge aparece donde debe.

### P4.3 — Retirar el fixture del stack operacional — NO APLICA

El perfil `operational` ya rechaza `seed full` por guardia, y el endpoint confirma que sólo hay
`BROKER_REAL`. El fixture mezclado es un problema del stack `stratos_g12`, que no está
levantado. Si se vuelve a levantar, el badge ahora lo declarará.

### P4.4 — Baselines de Playwright — PENDIENTE

Siguen siendo de G10 y `e2e-playwright` sigue rojo en CI por eso. Regenerarlos exige un
recorrido con seed y navegador; no es un arreglo de código.

## P5 — Incubadora: abrir la puerta a más candidatas, y de observatorio a gestor

### P5.0 — El tope de diversidad, separado · HECHO 2026-09-02

El tope mezclaba dos decisiones distintas: cuántas estrategias se **validan** contra MT5 (un
presupuesto de CPU) y cuántas pueden **convivir** en Incubadora (una restricción de riesgo de
portfolio). Un solo número hacía las dos, y por eso 215 de 217 candidatas estaban paradas.

La política `operational-prefilter-v3` los separa:

- **`validation_queue`** — `max_queue` y un `max_per_symbol_timeframe` que admite `null`.
  Con `null`, **la cola pasa de 2 a 24** y las 193 restantes esperan por presupuesto de cola
  (`HOLD_QUEUE_CAP`), no por diversidad. Validar veinte `AUDCAD/H4` no concentra riesgo.
- **`incubator_admission`** — `max_per_symbol_timeframe` y `max_concurrent`. **Declarado y no
  aplicado**: la Incubadora sigue bloqueada y ningún código admite todavía. El prefiltro se
  limita a anotar `admission_bucket_rank` y `exceeds_incubator_admission_cap` en cada entrada
  de la cola —**22 de las 24 lo excederían**— para que la concentración no se pierda cuando
  llegue la admisión.

Una política v2 se sigue leyendo con su comportamiento anterior, sin cambiar en silencio.

**Pendiente para cuando exista admisión**: el filtro de correlación entre curvas de equity,
que es lo que mide diversidad de verdad. Dos `AUDCAD/H4` con correlación 0,2 diversifican;
dos con 0,9 no, aunque el tope por símbolo las deje pasar. La pieza ya existe
(`services/correlations.py`, `is_redundant_pair`, G8 criterio 9).

**Esto resuelve el atasco, no la concentración.** Que 215 de 217 candidatas sean el mismo par
y marco temporal es una conclusión sobre el universo de Análisis, y se corrige minando otros
activos, no ajustando la cola.

### P5.1 — Gates hacia gestor

Sólo después de P0-P4. En orden:

1. Registrar una cuenta `BROKER_DEMO` real y su terminal.
2. Implementar el adjunto demo por gráfico (hoy el lanzador termina declarando la Incubadora
   bloqueada precisamente aquí).
3. Consumir la cola FIFO hasta el tope de 8, con el contrato de gracia ya definido: sizing
   10 %, riesgo 0,2 %, DD contractual 5 %.
4. Sólo entonces, semáforos y kill-switch actuando de verdad.

## P6 — Higiene de entorno · EJECUTADO 2026-09-02

- **`.codex/config.toml`** ahora registra el MCP `stratos` además de `sqx_forja`. Es el que
  expone `scan_hardcoding`, obligatorio por P11 antes de cerrar unidad; Codex trabajaba sin él.
- **`PIPELINE_MINADO_A_FINALISTAS.md`** decía "inventario completo de `Apps_entorno_SQX/`"
  sobre una tabla de 9 apps cuando hay **14 directorios**, y ubicaba `SQX_vs_MT5_Panel` "en la
  raíz, fuera de `Apps_entorno_SQX`" cuando vive dentro. Corregido: la tabla se declara como
  las apps **del pipeline de minado**, y las cinco restantes (`StratOS-QXPro-v2`,
  `SQX_Edge_Suite_v1`, `pipeline_hub`, `PortfolioLive_Pro`, `mt5_bridge`, más `_common`) se
  listan aparte con lo que son. Rango de puertos corregido a 8770-8777.
- **`SQX_Edge_Suite_v1`** (`backlog A10`): documentado en los índices de la raíz y en
  `PIPELINE_MINADO_A_FINALISTAS.md` como proyecto con gobierno propio, sin git e inactivo
  desde 2026-08-14. **Versionarlo o archivarlo sigue siendo decisión del operador**: no se
  toca un proyecto ajeno al pipeline sin que lo pida.

## Estado final del plan — verificado 2026-09-02

Verificación ejecutada sobre el plan completo, punto por punto:

| Bloque | Estado | Comprobado con |
|---|---|---|
| P0.1 commitear | **HECHO** | 24 commits sobre `a55694c`, pusheados |
| P0.2 CI verde | **HECHO** | ruff/format/mypy limpios; 618 + 160 + 64 + 57 + 25 tests |
| P0.3 exe operacional | **HECHO** | regenerado; 0 scripts por detrás, `--help` responde |
| P0-bis salvaguarda de símbolo | **HECHO** | panel v1.3.3, verificado contra databank real |
| P1.1 reclasificación persistida | **HECHO** | 2 eventos `DIRECTIONAL_*` en la base |
| P1.2 extracción de símbolo | **HECHO** | 73/73 `.sqx` resuelven sin alias parche |
| P1.3 scan consolidado | **HECHO** | `ASSUMPTIONS.md` G13-28 |
| P2.0/P2.1 export medido | **HECHO** | ventana y migración cerradas por el operador |
| P2.2 atribución del histórico | **HECHO** | 34 bots sincronizados, 26 trades reatribuidos |
| P4.1 procedencia en 5 vistas | **HECHO** | endpoint verificado en vivo |
| P5.0 tope de validación | **HECHO** | política v3, cola de 2 a 24 |
| P6 higiene | **HECHO** | MCP `stratos` en Codex, inventario de apps corregido |
| **A17 métricas sobre EAs vivos** | **HECHO** | `trade_attribution` en vivo: 377 de 8.831 |
| **A18 filtro de correlación** | **HECHO** | los dos criterios, 13 tests |
| **A19 reclasificador** | **HECHO** | 7 corridas superseded filtradas, 0 retenciones |
| **P5.1 cuenta de Incubadora** | **PARCIAL** | `account_id=3` dada de alta; falta el adjunto |
| **P3 cola F7** | **PARCIAL** | cola regenerada: no cambió; falta cerrar el Darwinex |
| P4.2 recorrido autenticado | pendiente | el panel queda abierto en `/login` para el operador |
| P4.4 baselines Playwright | pendiente | el operador lo hará más tarde |
| P2.3 telemetría viva | **HECHO** | ~~BLOQUEADO~~ — diagnóstico corregido 2026-09-26: nunca dependió de los MCP de este agente. El conector real (NSSM `StratOSMt5Readonly_*`) ingiere en continuo; verificado en vivo (`backlog A23`) |

### Lo que hace falta para cerrar los tres parciales

1. **P3** — el terminal **Darwinex** sigue abierto (PID 36776) y mantiene conectadas JJTI y
   BEPB. El lanzador exige cierre limpio de esa instancia y no fuerza procesos; cerrarlo
   detiene temporalmente las cuentas reales, así que es decisión del operador. Con él cerrado,
   quedan 2 expedientes `PREFLIGHT_OK` por correr.
2. **P5.1** — la cuenta está registrada y el gate de admisión construido, pero faltan el
   **adjunto demo por gráfico** y el **consumo de la cola FIFO** (`backlog A20`). Ninguna
   estrategia de Análisis es todavía `BACKTEST_VALIDATED`, así que no hay candidato que
   admitir aunque el mecanismo existiera.
3. ~~**P2.3**~~ — ya no es un pendiente: era un diagnóstico erróneo que confundía la
   telemetría del producto (el conector NSSM, en marcha desde A35/A40) con la conectividad
   MCP de este agente a los terminales. Corregido en `backlog A23` el 2026-09-26.


## Addendum 2026-09-02 (tarde) — por qué la cola seguía siendo toda AUDCAD

Tras exportar el operador las 22 parejas de XAUUSD H4 y correr RETEST OOS + Monte Carlo en
DAX40 M30 y NASDAQ, el inventario subió de 375 a **397 STATIC_VALIDATED**, pero la cola de
validación seguía siendo 24 de `AUDCAD/H4`. La causa no era el reparto por turnos ni los
umbrales: **dos bugs de emparejamiento míos ocultaban evidencia que ya estaba en disco.**

| bug | efecto | cierre |
| --- | --- | --- |
| El resolutor trataba `PortfolioSeleccion` como origen posible | 8 retenidas `AMBIGUOUS_PROJECT_HASH_MATCH` | `A32` — desempate por tarea `Build` |
| El extractor comparaba el databank byte a byte (`Forward` ≠ `FORWARD`) | 57 retenidas con la evidencia delante | `A33` — comparación en casefold |

Con los dos cerrados: **fuentes 397/397 resueltas (0 retenidas)** y el motivo de retención se
desplaza al gate siguiente, que ya es un hueco de datos real y no un fallo de código.

**Lo que queda es trabajo en SQX, no en StratOS.** Ver la tabla por proyecto en `backlog A30`.
El hallazgo que importa: un databank `WFM` con `.sqx` dentro **no** prueba que la matriz se
corriera. El `.sqx` de AUDCAD que sí valida lleva 30 corridas `Results/WF: N runs : X % OOS`;
los de XAUUSD H1 (0 de 113) y DAX40 SesionTarde (0 de 14) sólo llevan `Results/Main`. Están
depositados en un databank llamado WFM sin haber pasado por la tarea.

Mientras tanto `AUDCAD/H4` es el único grupo con evidencia completa (232 de 397), así que
llena la cola por mérito propio, no por un sesgo del reparto.
