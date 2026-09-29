# Backlog — StratOS-QXPro

- ~~**[G13-75] Por qué se acumularon 52.512 filas duplicadas de `ingest_batch` para un solo
  sello**~~ **CAUSA RAÍZ CONFIRMADA 2026-09-28 — no es un bug de este repo, es deriva de
  despliegue ya diagnosticada antes y nunca corregida.** Investigación completa:
  - Los 52.512 duplicados (cuenta real BEPB, `batch_type=trades`) comparten **el mismo
    `connector_instance_id`** durante 21 días (7 al 28 de septiembre) — descarta que el
    buffer SQLite local se reinicie o se pierda entre reinicios (el `connector_instance_id`
    se persiste en la misma tabla `meta` que el watermark `last_deal_ts`, y sobrevivió
    intacto).
  - El histograma diario muestra un patrón claro: ~280 filas/día (7-10 sept, cadencia normal
    ~5 min) → salta a 1.600-5.800 filas/día (11-25 sept) → cae a 0 el 27 sept → 1 fila el 28.
  - **Ya estaba diagnosticado**: este mismo fichero documentaba desde el 2026-09-26 (ver
    entrada de arriba sobre "141 lotes... 20 minutos"): *"Queda una causa aguas arriba: el
    conector del repo lleva watermark correcto (`poll_deals_incremental_once` persiste
    `last_deal_ts` en `buffer.meta`), así que el del VPS debe correr una versión anterior o
    perder su buffer al arrancar. Conviene comprobarlo allí."* — nunca se comprobó, y el
    mismo patrón volvió a reventar el 2026-09-28, esta vez 375× más grande (52.512 vs 141).
  - Verificado en el código de este repo: `mt5-connector/src/connector/poller.py::
    poll_deals_incremental_once` SÍ implementa el watermark incremental correctamente
    (persiste `last_deal_ts`, solo pide deals nuevos).
  - **Corrección tras acceso directo al VPS real (RDP, 2026-09-28 tarde) — el diagnóstico
    de "conector desactualizado" era correcto SOLO como explicación histórica, ya no como
    estado actual.** Verificado con acceso interactivo real (`C:\StratOS\readonly-connector\
    mt5-connector\` en el VPS, servicios NSSM `StratOSMt5Readonly_bepb/jjti/incubadora`,
    los tres `Running`): **los 4 ficheros clave del conector
    (`poller.py`/`buffer.py`/`sender.py`/`main.py`) son BYTE A BYTE IDÉNTICOS** al código de
    este repo (comparación por `Get-FileHash` SHA-256 contra el hash local, no visual). El
    watermark real en `buffer.sqlite` de BEPB (`last_deal_ts`) estaba avanzando con
    normalidad, actualizado a los pocos minutos de la consulta. Los 4 procesos Python del
    conector (uno por servicio + su hilo) tienen `StartTime` **2026-09-26 09:43 AM** — casi
    exactamente el momento en que el histograma diario de duplicados se desploma (última
    entrada masiva a las 07:17 esa misma mañana). **Conclusión: alguien ya reinició/corrigió
    el conector el 2026-09-26 por la mañana, dos días antes de que esta sesión empezara a
    investigar** — el código nunca estuvo desactualizado hoy, solo lo estuvo ANTES de esa
    fecha. No hace falta ninguna acción de redeploy: ya está hecho. Los 52.512 duplicados son
    puramente evidencia histórica de la ventana rota (7-26 sept), no un problema activo.
  - **Lo que sí se arregló aquí, con lógica** (commit `34c0939`, sigue siendo válido pase lo
    que pase con el conector): la falta de observabilidad que dejó crecer esto 21 días en
    silencio. `seal_and_create_batch()` genera ahora una `Alert` (nivel SUAVE, una sola vez
    por sello vía `dedup_key`) cuando un mismo sello se reenvía 50+ veces — muy por debajo
    del volumen real y del escenario tolerado por diseño ("141 en 20 minutos"), para que
    esto sea visible en Auditoría el mismo día en vez de 3 semanas después. 5/5 tests
    contra BD real, desplegado en el stack operacional real.
  - **Nada pendiente del operador en este punto** — corrección de lo que se le pidió en la
    sesión anterior: no hacía falta redesplegar nada porque ya estaba hecho.
- ~~**[G13-73] Cola de prefiltro en 0 tras rebuild del exe**~~ **CERRADO 2026-09-28 — no es
  bug, es hueco real de datos en SQX (mismo patrón ya documentado para otros proyectos,
  ver A30 arriba).** Diagnóstico completo: de las 230 fuentes "resueltas" (hash de
  `Forward` coincide con un proyecto real), **227 apuntan a un único proyecto**,
  `Project_AUDCAD_H4_S_BS_ForexMinorLateral_capa2`. Ese proyecto tiene en disco
  `databanks/RETEST OOS/` con **0 ficheros** — de ahí el `EXTRACTION_FAILED:RETEST OOS:
  artefacto no resuelto` uniforme en las 230. No es fallo del extractor ni de la
  resolución de fuentes (ambos funcionan correctamente; `source_selection:
  UNIQUE_HISTORY_SIGNATURE` es una coincidencia de hash real, no una mala ruta).
  **Mecanismo encontrado por timestamps de disco**: `MC`, `MC2`, `OPTIMIZED`, `RETEST
  OOS`, `TICK`, `TICK OPT` y `Results` de ese proyecto se vaciaron TODOS a la vez el
  **2026-09-18 ~15:10** (operación en bloque — la firma típica de SQX invalidando etapas
  posteriores de la cadena al re-ejecutar una etapa anterior). Después, `WFM` (27
  ficheros) y `SPP` (7 ficheros) se repoblaron el **2026-09-22**, pero `RETEST OOS` no se
  ha vuelto a correr desde entonces — el proyecto está a mitad de cadena de validación,
  no roto. Esto es exactamente la regresión de los 232 candidatos que `backlog.md` (A30,
  entrada de arriba) documentaba como el ÚNICO grupo con evidencia completa a fecha
  2026-09-02 — ya no lo es, porque el proyecto avanzó de fase desde entonces sin
  completar RETEST OOS todavía. **No se toca SQX ni se relanza nada desde aquí** (mismo
  criterio que el resto de huecos de esta lista): si el operador quiere que esas 227
  candidatas vuelvan a la cola, tiene que correr RETEST OOS sobre
  `Project_AUDCAD_H4_S_BS_ForexMinorLateral_capa2` él mismo en la UI de SQX.
- ~~**[G13-49] Cierre de F3 a F4 para las dos candidatas AUDCAD**~~ **DESACTUALIZADO, verificado
  contra la BD real 2026-09-27**: esta entrada quedó obsoleta — el registro del adjunto y el
  `ea_state` posterior ya ocurrieron (ver `phase_status.md` G13-49, 2026-09-10,
  `DEMO_ATTACHMENT_AND_REPORTER_VERIFIED`). Consulta read-only a `stratos_operational` (no la
  base de test que usa pytest, que solo contiene un seed `ANALYSIS` sin estas dos candidatas)
  confirma `bot.id` 42 (magic 295) y 43 (magic 243) en `pipeline_candidate.current_phase='F5'`
  desde `entered_phase_at=2026-09-10T05:26`, `incubation_days=14`, `oos_trades=0` — coincide
  con G13-51 (F5, 0 trades demo). No hay nada pendiente de F3→F4; lo que sigue abierto es
  F5→F6 por evidencia de mercado (ver `docs/PLAN_CONTINUACION_2026-09-27.md` §4.1.2).

## 2026-09-26 (tarde) — CI verde por primera vez, y el trabajo de Codex adoptado

El operador cierra la etapa con Codex: a partir de ahora el orquestador y ejecutor es uno solo.
Se adoptan sus 87 ficheros sin commitear tras dejarlos verdes, y **el CI pasa de rojo permanente
—ni un solo run verde desde el 2 de septiembre— a 10/10**.

- ~~**[A41] 87 ficheros de Codex fuera de git y de CI**~~ **RESUELTO 2026-09-26**: 40 modificados
  y 47 nuevos, incluidas 5 migraciones Alembic, 3 ADR y 12 ficheros de frontend. Commiteados por
  áreas (base de datos, core, frontend, scripts, pipeline-agent, documentación), no en bloque.
  Antes de adoptarlos hubo que arreglar lo que dejaba el pipeline en rojo: 11 errores de ruff,
  17 ficheros sin formatear y 3 de `mypy --strict`. `alembic heads` devuelve un único head, así
  que la cadena de migraciones no quedó ramificada.
- ~~**[A42] mypy pasaba en local y fallaba en CI**~~ **RESUELTO 2026-09-26**: el venv local tenía
  SQLAlchemy **2.0.52** y el CI instala **2.1.1**, que tipa mejor las columnas nullable — 0
  errores aquí, 11 allí. Se alineó el entorno local con el del pipeline y se arreglaron de
  verdad (`pipeline_gate`, `portfolio`, `correlations`, `f6_*`): se reafirma en Python el filtro
  que ya hace SQL, en vez de castear a ciegas. **Mantener el venv local en la versión del CI**, o
  esta clase de error vuelve a pasar desapercibida.
- ~~**[A43] El seed no terminaba: `baseline_grace_days` excluía a todos los bots**~~ **RESUELTO
  2026-09-26**: `semaphore_sweep` se salta todo bot cuya baseline no haya superado 5 días, y el
  seed las creaba con `created_at=now`. Resultado: **el barrido no evaluaba a ninguno de los 32
  bots**, cero transiciones, Poseidón se quedaba en AMARILLO en vez de avanzar a NARANJA y el
  seed abortaba con "cero decisiones pendientes". Era la causa de que `e2e-acceptance-full` y
  `e2e-playwright` llevaran rojos desde el 2 de septiembre: ambos arrancan sembrando. La
  baseline pasa a nacer con `profile.history_start`; la gracia no se toca.
- ~~**[A44] La pestaña Portfolio perdió el título de la matriz**~~ **RESUELTO 2026-09-26**:
  dividir la matriz en una tarjeta por procedencia está cubierto por su ADR, pero el título pasó
  a ser sólo `aria-label`. `pestaña Portfolio.jpg` lo muestra **visible**, así que se restauró
  como `<h2>`. Un título que sólo existe para el lector de pantalla no cumple la fidelidad 1:1.
- ~~**[A45] El seed escribía la matriz de correlación legacy que ya nadie lee**~~ **RESUELTO
  2026-09-26**: la UI y `compute_portfolio_contribution` leen `CorrelationSnapshot` sellado, y el
  seed sólo llamaba a `run_correlation_job`. Ahora escribe ambas, como el barrido real. La fuente
  observada sigue retenida en el fixture y **es correcto**: sólo mira cuentas `BROKER_REAL`
  —"fixture y demo no se consultan ni siquiera como relleno"— y el seed es `FIXTURE`.
- ~~**[A46] Los specs de Playwright validaban una UI retirada**~~ **RESUELTO 2026-09-26**:
  `pipeline_bots` exigía el kanban F1–F7 que el **ADR 0012** retiró por decisión del operador; se
  reescribió sobre lo que ese ADR promete (banner, tres carriles y ausencia de cualquier botón de
  despliegue sobre BEPB/JJTI). Las tres capturas de referencia se regeneraron **desde el propio
  runner**, no en local: en Windows las fuentes no coinciden y la baseline sería falsa. El CI
  ahora sube `test-results/` al fallar, que es lo que permite hacerlo sin reproducir su entorno.

## Hallazgos 2026-09-26 — el panel no se podía usar

El operador pidió "un solo acceso, el definitivo". Al cablearlo apareció que **nadie había
entrado nunca al panel**, y por tres causas encadenadas. Las tres estaban ocultas porque el
síntoma era siempre el mismo: la pantalla de login no hacía nada.

- ~~**[A36] El pool de conexiones usaba el default implícito de SQLAlchemy**~~ **RESUELTO
  2026-09-26**: `create_async_engine` no declaraba tamaño, así que heredaba 5 + 10. La ingesta
  de las dos cuentas reales agotaba las 15 conexiones y `/auth/token` tardaba **31,8 s** en
  devolver un 500 —sin que nada dijera por qué—. Medido: 14 conexiones activas, la más antigua
  de 3m33s. Ahora vive en `Settings` (`DB_POOL_SIZE`/`DB_MAX_OVERFLOW`, 20 + 20). Verificado
  contra el stack real: **0,39 s y 200**, y login completo por la UI.
- ~~**[A37] El hash del operador llevaba los `$` duplicados**~~ **RESUELTO 2026-09-26** (la
  detección; el valor lo arregla el operador): `.env.operational` guarda
  `$$argon2id$$v=...` —102 caracteres, 10 `$`—. Es un hash correcto **escapado para docker
  compose**: el mismo fichero se pasa como `--env-file` (donde compose interpola `$`) y como
  `env_file:` del servicio (donde llega literal), así que silenciar el warning de compose rompe
  el valor que recibe la aplicación. `bootstrap_operational_operator.py` ahora nombra el caso en
  vez de mandar a regenerar un hash que ya era bueno. **El login lee de la base, no del env**,
  así que esto sólo muerde en el próximo bootstrap.
- ~~**[A40] El backoff del conector desbordaba y congelaba la telemetría**~~ **RESUELTO
  2026-09-26**. Es la causa **raíz** de A35, encontrada en el VPS. `next_delay` calculaba
  `min(base * multiplier**attempts, max_seconds)`: la potencia se evalúa entera **antes** del
  `min()`, así que el tope no protegía de nada. La cadena completa:

  1. El 2026-09-07 a las 17:09 un lote de `trades` de BEPB falla. El último trade en la base es
     de ese mismo día a las 17:19 — encaja.
  2. Reintentos con backoff exponencial: `attempts` crece sin freno.
  3. Al intento **1025**, `2**1025` supera el rango del float y `next_delay` lanza
     `OverflowError: (34, 'Result too large')`. Medido en el buffer: `max(attempts)=1025`.
  4. El conector ya no puede calcular el retardo, así que **deja de drenar**.
  5. Detrás se apilan 19 días de telemetría: 257.899 `positions`, 43.094 `equity` y 21.552
     `heartbeat` desde el 11-sep, con `avg(attempts)=0,003` — no eran reintentos, era
     acumulación detrás de un único registro atascado. Buffers de 326/274/127 MB y 66 MB de la
     misma traza repetida.

  Arquitectura del VPS (`vmi2101908`, Contabo): **tres servicios Windows bajo NSSM**
  —`StratOSMt5Readonly_bepb`, `_jjti`, `_incubadora`—, cada uno con su propio buffer en
  `C:\ProgramData\StratOSQXPro\operational\<cuenta>\`. El código de allí es idéntico al del
  repo; no era una versión antigua, como se supuso en A35.

  Corregido en `http_client.py` (se calcula antes a partir de qué intento se alcanza el techo),
  desplegado por SSH y los tres servicios reiniciados. Verificado: el `OverflowError` desaparece
  de los logs, que pasan a `HTTP 200 OK`, y la cola drena a ~229 registros/minuto. **Quedan unas
  24 h de drenaje** de los 966.484 registros acumulados; no se purga nada, es telemetría real.
  Los ficheros `.sqlite` no encogerán hasta un `VACUUM` (SQLite no libera páginas al borrar).

- ~~**[A35] La ingesta se serializaba sobre las mismas filas y no avanzaba**~~ **RESUELTO
  2026-09-26**, en dos movimientos:
  1. `post_trades` y `post_equity` hacían el upsert y **después** evaluaban F4/F5/F6, todo en la
     misma transacción, reteniendo los locks de las filas de `trade` durante todo el pipeline.
     Ahora confirman antes de evaluar, por el mismo criterio que ya seguía `post_positions`.
  2. El conector reenviaba su histórico completo en cada ciclo: **141 lotes y 317.670 registros
     en 20 minutos para cero filas nuevas**, con 102.034 lotes acumulados. Un sello SHA-256
     repetido es el mismo lote byte a byte, así que no hay nada que ingerir: se sella igual —la
     traza append-only no se toca, y es lo que deja ver que un conector reenvía— pero no se
     reprocesan sus registros.

  Medido de punta a punta: conexiones activas **35 → 1**, login **31,8 s/500 → 0,3-1,7 s/200**,
  y el bucle de reenvío se cortó solo (al recibir respuesta a tiempo el conector dejó de
  reintentar). El panel pasó de `DATOS STALE (hace 21431 min)` a `hace 0 min`.

  **Queda una causa aguas arriba**: el conector del repo lleva watermark correcto
  (`poll_deals_incremental_once` persiste `last_deal_ts` en `buffer.meta`), así que el del VPS
  debe correr una versión anterior o perder su buffer al arrancar. Conviene comprobarlo allí.

- ~~**[A38] El worker compite con el scheduler por los jobs de cron**~~ **RESUELTO
  2026-09-26**. El diagnóstico inicial era falso: dije que el kill-switch, el barrido de
  semáforos y el watchdog llevaban sin ejecutarse, leyendo sólo los logs del worker
  (`function 'cron:task_run_killswitch_sweep' not found`, cada minuto). Los logs del
  **scheduler** mostraban lo contrario: `← cron:task_run_killswitch_sweep ●` cada minuto, en
  0,4-0,5 s. **Los barridos sí se ejecutaban.** Lo real era que worker y scheduler compartían la
  cola ARQ por defecto: el worker veía encolados unos `cron:*` que no declara y los descartaba
  con ese mensaje, con el riesgo de que se adelantara y un barrido concreto se perdiera.
  Corregido dándole al scheduler su propia `queue_name` (`arq:scheduler`). Verificado tras
  desplegar: 0 mensajes `not found` en el worker, el scheduler sigue ejecutando sus 10 crons.

- ~~**[A39] Tres accesos distintos y ninguno abría la aplicación**~~ **RESUELTO 2026-09-26**:
  `StratOS_Operacional.bat` (refresca admisión), `StratOS_Backtests.bat` (comparaciones) y
  `StratOS_Stack_Operacional.bat` (abría **Swagger**, `8300/docs`, que es herramienta de
  desarrollo). La aplicación real —el panel React con sus 11 pestañas— es **`localhost:5473`**, y
  no tenía acceso. Ahora `StratOS.bat` es el único: si el panel ya responde entra directo, y si
  no levanta el stack, espera a que sirva de verdad y lo abre. Los otros dos siguen en disco y
  sus accesos directos están recogidos en *"StratOS - otras herramientas"* del escritorio.

## Deuda de garantía — abierta desde la auditoría 2026-09-02

Detalle y comandos en [`AUDITORIA_2026-09-02.md`](historico/AUDITORIA_2026-09-02.md) (movido a
`docs/historico/` el 2026-09-27). Nada de esto es un hueco
de negocio: es infraestructura de garantía que G11-G13 dejaron atrás.

- ~~**[A1] G11/G12/G13 sin commitear**~~ **CERRADO 2026-09-02**: 9 commits temáticos; falta el `push` y el primer CI real. Salieron dos fugas de `.gitignore`: `.env.operational.example` estaba ignorado pese a declararse versionada, y `docs/history_deals_*.csv` (9.082 deals de cuentas reales) se habrían commiteado. Antes decía: — 194 ficheros en el working tree, último commit `a55694c`.
  Incluye 7 migraciones Alembic, 53 scripts y 11 documentos. Bloquea cualquier CI, cualquier
  revisión y cualquier vuelta atrás. Prioridad máxima; el resto de esta lista depende de ello para
  poder verificarse en CI real.
- ~~**[A2] `lint-backend` rojo**~~ **CERRADO 2026-09-02**: `ruff check` y `ruff format --check` limpios. Antes: — 7 errores de ruff en `db/models/__init__.py`, `db/sa_enums.py`,
  `routers/pipeline.py`, `services/config_drift.py`; 8 ficheros que `ruff format` reescribiría.
- ~~**[A3] `mypy --strict` rojo**~~ **CERRADO 2026-09-02**: Success en 108 ficheros; `get_bot` tiene ya su guarda de `None`. Antes: — 7 errores. `services/tca.py:60` sin anotación de `account_brokers`;
  `routers/pipeline.py:250/276/319` y `routers/bots.py:172` declaran `-> PipelineCandidate` / `-> Bot`
  pero devuelven la respuesta Pydantic; `routers/bots.py:172` accede a `account.data_origin` sin
  guarda de `None` (no explotable hoy porque `Bot.account_id` es `NOT NULL` con FK, pero es el patrón
  exacto que `--strict` existe para atrapar).
- ~~**[A4] `test_migration.py::test_all_tables_created` rojo**~~ **CERRADO 2026-09-02**: 36 tablas, y un test aparte las verifica por nombre. Antes: — `EXPECTED_TABLE_COUNT = 30` contra 36
  tablas reales; faltan las 6 de G11/G13 (`import_artifact`, `execution_fill`,
  `pipeline_phase_transition`, `external_ea_inventory`, `operational_asset`,
  `operational_asset_event`). Mientras siga rojo, el guardia de esquema no protege nada.
- ~~**[A5] test rojo y ambigüedad de rol documental**~~ **CERRADO 2026-09-02**: la migración MN resolvió la colisión (`5.29.24`→`10829`); cada propiedad se verifica contra su fuente real y ambos registros llevan cabecera de momento. Antes: —
  el test verifica la colisión BEPB `magic=10827` que `ASSUMPTIONS.md` G13-14 sella como retenida;
  `docs/registro_BEPB_MN_bots_real_mt5_vps.md` se reescribió con los magics post-migración y ya sólo
  tiene una fila. Hay que decidir si ese fichero es la observación pre-migración (evidencia, y
  entonces el registro post-MN va a otro fichero) o el estado actual (y entonces el test debe apuntar
  al manifiesto sellado `bepb_magic_manifest.json`, que sí conserva el duplicado).
- ~~**[A6] `dist/StratOS_Operational.exe` desfasado**~~ **CERRADO 2026-09-02**: regenerado, 0 scripts por detrás, arranque verificado sin abrir MT5. Antes: — binario del 30/08 frente a 23 scripts
  posteriores, entre ellos el contrato direccional y toda la cola alineada v2. Regenerarlo con
  `scripts/build_stratos_operational_exe.ps1` tras cerrar A1-A4, o retirarlo de la documentación
  como punto de entrada hasta entonces.
- ~~**[A7] Reclasificación direccional no persistida**~~ **CERRADO 2026-09-02**: `record_directional_reclassification.py`, 2 eventos persistidos e idempotencia verificada; la tercera quedó retenida (ver A15). Antes: — `directional_reclassification_20260901.json`
  cambia 3 veredictos de 11 y no existe como evento en `operational_asset_event`. No hay riesgo
  operativo (los F7 externos siguen `WITHHELD` correctamente) pero sí de trazabilidad. Ver G13-25.
- ~~**[A8] `scan_hardcoding` de G12/G13 sin consolidar**~~ **CERRADO 2026-09-02**: barrido clasificado en ASSUMPTIONS G13-28; 5 literales migrados a constante, el resto justificado por categoría. Antes: — 340 hallazgos en `scripts/`, mayoría deuda
  conocida de `seed_lib/` y falsos positivos (índices de columna, colores nativos MT5, codec
  `utf-16` de los `.chr`, algunos ya justificados en G13-19/G13-22). Falta el barrido clasificado
  uno a uno que G10 sí cerró en su grupo (o).
- ~~**[A9] `alias_simbolos` contaminado**~~ **CERRADO 2026-09-02**: la causa raíz era que 27 de 73 `.sqx` traen el nombre de la estrategia en el campo `symbol` de la cabecera binaria; ahora manda `lastSettings.xml` y 73/73 resuelven sin alias parche. Antes: — contiene
  `"AUDNZDH4BUY_edge_1.16.34": "AUDNZD"` (un nombre de estrategia, no un símbolo) y
  `"USDJPY": "USDJPY"` (alias identidad redundante). Son parches puntuales sobre un fallo de
  extracción de símbolo; cada estrategia futura con el mismo patrón necesitaría su propia línea.
  Arreglar la extracción y limpiar el diccionario.
- ~~**[A15] Una comparación SQX↔MT5 completada no está registrada**~~ **RESUELTO 2026-09-02,
  y el diagnóstico inicial era incorrecto**: la corrida `20260830T210536Z_91538465c20a` no es
  un registro perdido. Es una comparación de la campaña **anterior al renombrado MN**, y su
  `sqx_path`/`mq5_path` ya no existen —la migración renombró la carpeta—. La misma estrategia
  se volvió a comparar el 2026-09-01 sobre la ruta MN (`20260901T155216Z_cc6bc7d013a4`,
  `XAU1H1BUYSTP_3.10.66_MN28`, `VALIDADA`) y **esa sí está registrada** como `asset_id=243`.
  No hay nada que registrar: está deliberadamente fuera, como declara G13-21 al dar las rutas
  antiguas por obsoletas. El fail-closed por entrada de
  `record_directional_reclassification.py` hizo exactamente lo correcto al retenerla.
- ~~**[A19] `reclassify_external_f7_backtests.py` reevalúa manifiestos obsoletos**~~ **RESUELTO 2026-09-02**: filtra por existencia de la fuente, no por nombre. De 11 corridas, 7 eran de la campaña anterior; quedan las 4 vigentes con 0 retenciones. Antes: — barre todos
  los `run-manifest.json` de disco, incluidos los de campañas superseded por el renombrado MN
  cuya fuente ya no existe. Por eso su informe dice "11 corridas" cuando sólo 10 corresponden
  a la campaña vigente. No es un error de veredicto —cada uno se recalcula sobre su propio
  manifiesto sellado— pero infla el recuento y obliga a retener una entrada en cada
  reclasificación. Filtrar por existencia de la fuente, o por pertenencia a la cola alineada.
- ~~**[A16] La importación del histórico estaba construida pero sin ejecutar**~~ **RESUELTO
  2026-09-26, con un hallazgo real por el camino**: re-ejecutar
  `import_mt5_history_export.py --identity-registry` como decía este ítem **no habría hecho
  nada**. Los dos CSV se importaron el 2026-09-01 sin el flag y sus posiciones quedaron
  cerradas; `ingest_trades` es idempotente por diseño (`ON CONFLICT ... WHERE close_time IS
  NULL`), así que un reenvío nunca toca el `magic_number` de una fila ya cerrada — repetir la
  importación es un no-op silencioso sobre datos ya asentados.

  Se escribió `scripts/backfill_legacy_magic_attribution.py`, el caso legítimo de mutar una
  fila cerrada (traducción de identidad aprobada, no un reenvío del conector). El dry-run
  contra el stack real descubrió algo que la asunción inicial no contemplaba: 184 trades BEPB
  y 133 JJTI ya tenían `bot_id` asignado bajo un magic legacy — no por error, sino porque
  `sync_bot_magics_to_migration.py` ya había corregido el `Bot.magic_number` de legacy a
  vigente antes, dejando el `magic_number` del trade como único campo obsoleto. Verificado uno
  a uno para los 21 magics legacy de BEPB: todos traducían exactamente al magic vigente del
  bot al que ya apuntaban. El diseño se corrigió para distinguir esa corrección de campo
  (segura) de un conflicto real (`bot_id` que traduciría a un bot *distinto* — eso sí se
  retiene y se declara).

  Aplicado y verificado contra `stratos_operational`: **BEPB 297→480 trades atribuidos**
  (401 `magic_number` corregidos, 0 conflictos), **JJTI 217→351** (291 corregidos, 0
  conflictos). Idempotente: una segunda corrida con `--apply` da 0 en ambas cuentas. Un caso
  quedó correctamente huérfano y declarado (34 trades BEPB bajo magic 12,
  `XAUH1D1L__3.12.88_MN12`): ese bot existe para JJTI pero no está registrado para BEPB — no
  se inventó una atribución.

  **INCIDENTE POSTERIOR, mismo día 2026-09-26, corregido en la misma sesión**: lo anterior se
  dio por cerrado sin ver un segundo bug. `build_legacy_magic_map()` (`magic_identity.py`)
  devuelve un mapa **global** de magic legacy → identidad vigente; cada entrada declara
  `accounts` (a qué cuenta real pertenece la traducción), pero `backfill_legacy_magic_attribution.py`
  lo aplicaba tal cual, sin filtrar. Como BEPB y JJTI reutilizan magics legacy con destinos
  distintos, esto escribió el `magic_number` de una cuenta en trades de la otra: BEPB
  magic=12 (destino real 7508, aprobado solo para JJTI) y JJTI magics=28/38/40 (destinos
  reales 7507/120726/333335, aprobados solo para BEPB).

  Al corregirlo con un script puntual (`fix_a16_cross_account_magic_bug.py`, `WHERE
  magic_number=X AND bot_id IS NULL` por cuenta), ese mismo script introdujo un **tercer
  bug**: la selección no distinguía por ticket, así que en JJTI capturó también 15 trades
  **genuinamente nativos** en magic=40 (nunca tocados por el bug original) y los revirtió a
  333335 por error. Se detectó por un bug en el propio script de auditoría
  (`json.dump`/`json.load` convierte claves int a string; el lookup hacía
  `mapa.get(int(ticket))` contra un dict con claves string, así que siempre daba `None` y
  ocultaba las filas nativas entre las "seguras").

  Corregido y verificado en la misma sesión, contra `stratos_operational` real:
  - Los 15 tickets nativos JJTI revertidos a mano por `ticket_mt5` explícito (nunca por
    magic) con `fix_own_overreach_native_jjti_40.py`, dry-run + `--apply`.
  - Recuento final por cuenta/magic confirmado sin residuo en ningún valor intermedio erróneo:
    `BEPB {7508:35, 40:27, 28:23, 38:11}` (0 en 12/120726/333335) y
    `JJTI {333335:6, 40:30, 120726:10, 7507:10, 12:101}` (0 en 38/28).
  - Causa raíz corregida de fondo: `magic_identity.py` gana `entry_matches_account()`
    (mismo criterio que ya usaba `sync_bot_magics_to_migration.py`, el único consumidor que
    lo hacía bien desde el principio); `backfill_legacy_magic_attribution.py`,
    `regenerate_mn_registry_docs.py` (A13) e `import_mt5_history_export.py` (mismo bug
    latente, nunca disparado) ahora filtran el mapa por cuenta antes de usarlo. Tests de
    regresión en `scripts/tests/test_magic_identity.py` y
    `scripts/tests/test_regenerate_mn_registry_docs.py` reproduciendo el caso real
    (10827→10, aprobado solo para JJTI). Ver `ASSUMPTIONS.md` G13-64.
- ~~**[A17] El 87-90 % del histórico es de EAs ya retirados**~~ **RESUELTO 2026-09-02**: decisión del operador — los retirados no se inventarían ni se presentan. Las métricas por bot ya lo cumplían; los agregados ahora declaran la cobertura vía `trade_attribution` en `/data-provenance` (377 de 8.831). ASSUMPTIONS G13-31. Antes: — medido con
  `report_history_attribution.py`: 4.355 deals BEPB y 3.694 JJTI con un magic que no está en
  el registro de identidad. No es un fallo: es la rotación real del portfolio. Decidir si las
  métricas por bot se presentan sólo sobre los EAs vivos o si merece la pena inventariar los
  retirados; hasta entonces, no prometer métricas por bot sobre el histórico completo.
- ~~**[A18] El filtro de correlación no participa en la admisión**~~ **RESUELTO 2026-09-02**: `core/services/incubator_admission.py` aplica los **dos** criterios (estructural y estadístico, este en valor absoluto), fail-closed en las dos direcciones, con el umbral en `config/operational_prefilter.json`. ASSUMPTIONS G13-30. Antes: — el tope por
  símbolo/timeframe aproxima la diversidad; la correlación entre curvas de equity la mide.
  Dos `AUDCAD/H4` con correlación 0,2 diversifican y dos con 0,9 no, aunque el tope los trate
  igual. La pieza existe (`services/correlations.py`, `is_redundant_pair`) y hay que cablearla
  cuando exista admisión a Incubadora (ver `incubator_admission` en
  `config/operational_prefilter.json`, hoy declarado y no aplicado).
- ~~**[A11] El histórico exportado no llega a 2018**~~ **RESUELTO POR DECISIÓN DEL OPERADOR
  2026-09-02**: la ventana real del export es `2025-02-03` → `2026-09-01` (BEPB) y
  `2025-03-20` → `2026-09-01` (JJTI) — unos 19 meses, porque el caché de deals del terminal
  no guarda más. **El operador confirma que 19 meses bastan**: no se busca otra fuente para el
  tramo anterior. La ventana real es la ventana del sistema, y toda promesa de "importación
  desde 2018" queda corregida en esta documentación.
- ~~**[A12] Dos EAs rezagados tras la migración MN**~~ **CERRADO POR REVISIÓN DEL OPERADOR
  2026-09-02**: se midió sobre los deals del 1-2 de septiembre que `2004262` (BEPB) y `2084`
  (JJTI) seguían emitiendo su magic anterior, y que `9519`, `90727` y `0` no pertenecen al
  lote aprobado de 40. El operador revisó los terminales y confirma que la configuración es
  correcta. **La migración MN se da por cerrada.** Los magics fuera del lote corresponden a
  EAs desplegados que no entraron en la propuesta y a operaciones sin EA (`magic=0`), no a un
  fallo de la migración.
- ~~**[A13] Los `docs/registro_*_MN_*.md` se mantienen a mano y divergen del despliegue**~~
  **RESUELTO 2026-09-26**: ninguno de sus 56 `comment_identity` coincidía con los 40
  `ASSIGNED` aprobados, porque registraban el comment con el magic *legacy* mientras la
  propuesta asigna magics cortos. Los deals reales demuestran que lo desplegado usa los
  magics **nuevos**, así que eran esos documentos los que estaban desactualizados. Se escribió
  `scripts/regenerate_mn_registry_docs.py` (con tests, `scripts/tests/test_regenerate_mn_registry_docs.py`)
  para regenerarlos desde el registro append-only en vez de mantenerlos a mano. Su primer
  dry-run, antes de aplicarse, disparó una regresión real en
  `test_import_external_ea_inventory_records.py` que llevó a descubrir el bug de
  account-scoping documentado en el incidente de A16 — se corrigió ahí primero. Aplicado y
  verificado: BEPB 23/32 entradas traducidas, JJTI 11/24, cero contaminación cruzada
  (confirmado contra el dry-run: BEPB no toca 7508/10827/10828 propios de JJTI, JJTI no toca
  120726/333335/333336/333337 propios de BEPB).
- ~~**[A14] `docs/history_deals_*.csv` viven en `docs/`**~~ **RESUELTO 2026-09-26**: eran
  evidencia operativa (9.082 deals de cuentas Darwinex reales), no documentación. Movidos a
  `runtime/operational/history/history_deals_{BEPB,JJTI}.csv` (mismo directorio donde ya
  vivían sus copias selladas `history_deals.csv.<sha>.raw` de `ImportArtifact` 49/47, junto a
  las carpetas `BEPB/`/`JJTI/`); ya no hace falta ningún comando funcional que lea de
  `docs/` — `--csv` siempre fue un argumento explícito en `import_mt5_history_export.py`,
  `report_history_attribution.py` y los scripts del incidente A16, nunca un default
  hardcodeado. Se retiró la regla `docs/history_deals_*.csv` de `.gitignore` (ya cubierta por
  `runtime/`, línea 41) y se actualizaron las 4 menciones de ruta en docstrings/ejemplos de
  uso de esos scripts. Las referencias históricas en `docs/historico/AUDITORIA_2026-09-02.md`,
  `docs/historico/PLAN_CONTINUACION_2026-09-02.md` y las entradas ya cerradas de este mismo backlog no
  se tocan: describen un estado real de esa fecha, no la ubicación actual.
- ~~**[A48] `record_operational_backtest.py` y `report_history_attribution.py` usan
  `build_legacy_magic_map()` sin el filtro de `entry_matches_account()`**~~ **RESUELTO
  2026-09-27**: `resolve_external_magic()` (en `record_operational_backtest.py`) y
  `classify()` (en `report_history_attribution.py`) ahora reciben el nombre de cuenta y
  filtran el mapa igual que los tres consumidores de escritura del incidente A16. El segundo
  gana un `--account` obligatorio en su CLI (repetido 1:1 con `--csv`, en el mismo orden) —
  antes no tenía ninguna forma de saber a qué cuenta pertenecía cada CSV. 2 tests de
  regresión nuevos reproducen el caso real (magic aprobado solo para una cuenta, pedido para
  la otra) en ambos scripts; suite `scripts/` completa: 266/266 verde.
- ~~**[A10] `SQX_Edge_Suite_v1` sin versionar ni indexar**~~ **RETIRADO DEL BACKLOG G13
  2026-09-02**: Edge Suite es una aplicación independiente, con método, documentación y plan
  propios. No existe trabajo de integración ni dependencia de StratOS que mantener en este backlog.

## Pendiente tras el cierre de A15-A19 — 2026-09-02

- ~~**[G13 pipeline-agent] Helper F4 sellado**~~ **RESUELTO 2026-09-10**: el helper de Contabo consume el plan SHA-256 antes de modificar el perfil demo y preserva 243/295. Los dos adjuntos existentes se declararon mediante manifiestos sellados y su `ea_state` autenticado promovió los candidatos 42/43 de F3 a F4. La recuperación excepcional del reporter está acotada al replay auditado de `ea_state` de Incubadora; no toca MT5, JSONL, JJTI ni BEPB.
- ~~**[G13 F5/F6] Observación contractual y decisión de Incubadora**~~ **IMPLEMENTADO 2026-09-10**: la lectura F5 incluye baseline Tester separado, trades demo posteriores a la entrada F5, estado del reporter, heartbeat y equity. Un día sólo cuenta con ambos streams demo. El Kanban no tiene controles de ascenso. `f6_evaluation` conserva cada decisión con hash de evidencia/configuración: `POSTPONE` mantiene F5 mientras falten muestra, días o telemetría; sólo `APPROVE` 7/7 promueve F5→F6 automáticamente; `REJECT` queda auditado y requiere autopsia antes de Cementerio. No modifica MT5. Pendiente: implementar la evaluación challenger/champion del mismo slot y el escalado F6 contractual, manteniendo F7 como decisión humana.

- ~~**[A24] El ejecutor de cola F7 no conoce las corridas lanzadas a mano**~~ **RESUELTO
  2026-09-02**: `sealed_identities()` deriva lo ya comparado de los **manifiestos sellados**
  de `backtests_live/`, no sólo del log de la cola, cruzando por `sqx_sha256` —la identidad
  del artefacto— porque el renombrado MN movió las carpetas y un cruce por ruta perdería
  comparaciones válidas. No cuentan como comparación: un `mode=preflight`, un `returncode`
  distinto de 0 ni un hash que la cola no declare. Un manifiesto ilegible se salta en vez de
  abortar el barrido. Efecto medido: la cola pasa de 6 candidatos a **1**
  (`USDJPYH1Lcity_2.22.171`), reconociendo 9 identidades ya selladas.
- ~~**[A25] La cola y los manifiestos F7 usan magics legacy; la base usa los vigentes**~~
  **RESUELTO 2026-09-02**: `resolve_external_magic()` traduce con los `legacy_magic_numbers`
  del registro aprobado antes de buscar el bot F7; sin registro o con un magic desconocido se
  usa tal cual, para no inventar correspondencias. La evidencia guarda las dos caras
  (`magic_number` vigente, `declared_magic_number` el de la cola y
  `resolved_via_legacy_magic`), de modo que la asociación no parezca una coincidencia exacta.
  **Comprobado de punta a punta con `USDJPYH1Lcity_2.22.171`**: sin `--identity-registry` el
  registro falla con el error original; con él traduce `200730 -> 13` y sella `asset_id=248`.

- ~~**[A26] 95 candidatas de otros activos bloqueadas por el export a MQL5**~~ **CERRADO
  2026-09-02**: el operador exportó y dejó los pares en `Analisis/`. El inventario pasa de
  237 a **424 candidatas** en cinco grupos (AUDCAD/H4 232, XAUUSD/H1 100, DAX40/M30 56,
  XAUUSD/H4 22, NASDAQ/H1 1) y de 227 a **375 `STATIC_VALIDATED`**. Ninguna venía de un
  proyecto `capa1`: se verificó cruzando cada fichero con su databank de origen.
- ~~**[A29] SQX exporta en lote con el mismo `MagicNumber`**~~ **RESUELTO 2026-09-02**: 28
  EAs de `DAX40_m30` salieron con `11111`, el valor por defecto, y el inventario los retenía
  con `DUPLICATE_MAGIC_NUMBER`. `scripts/assign_unique_magics.py` reasigna sólo los
  duplicados, de forma determinista e idempotente, sin reutilizar un magic presente en el
  conjunto. 40 reasignados; 388 magics únicos en 388 EAs. El export de las 22 de XAUUSD H4
  volvió a traer `11111` en todas: 22 más reasignadas, **410 únicos en 410 EAs**. **Correrlo
  después de cada export en lote**, o el inventario retendrá el lote entero.
- ~~**[A28] La cola de validación se la llevaba el grupo más numeroso**~~ **RESUELTO
  2026-09-02**: con 205 candidatas superando criterios, las 24 plazas eran **todas**
  `AUDCAD/H4`. El orden por mérito global favorece al grupo grande, no al mejor portfolio.
  Ahora se reparte por turnos entre grupos, conservando el mérito dentro de cada uno; un
  grupo único sigue llenando la cola entera.
- ~~**[A34] El operador del stack operacional no podía iniciar sesión**~~ **RESUELTO
  2026-09-26**: su fila en `user` guardaba **13 caracteres en claro** donde va un hash Argon2
  (`hashed_password` no empezaba por `$argon2`). `verify_password` llama a `Argon2.verify`, que
  lanzaba `InvalidHashError` con un texto plano y devolvía `False`: ningún login podía
  funcionar, y fallaba sin decir por qué. Era la causa real de que P4.2 (recorrido autenticado)
  siguiera pendiente. `bootstrap_operational_operator.py` ya rechaza el alta si el valor no es
  un hash Argon2 y da el comando para generarlo (evita que se repita en el próximo bootstrap).
  La fila se reparó con una contraseña nueva, hasheada y aplicada en `.env.operational` y en la
  base. **Verificado en vivo tras el cierre de A35/A40** (la ingesta ya no agota el pool):
  `POST /auth/token` responde `200` en <1 s. La credencial **nunca llegó al historial de git**
  (auditado: `.env.operational` jamás rastreado, el `.example` siempre con placeholders); sí se
  escribió por error en `.env.operational.example`, revertido antes de comitear.

- ~~**[A32] El resolutor retenía 8 candidatas por un empate que no era tal**~~ **RESUELTO
  2026-09-02**: `PortfolioSeleccion` importa los `.sqx` ya construidos, así que su hash coincide
  igual que en el proyecto que los minó, y el resolutor retenía con
  `AMBIGUOUS_PROJECT_HASH_MATCH`. Un proyecto sin tarea `Build` no pudo minar la estrategia: se
  descarta como origen. Sólo se descarta lo demostrable — una definición ilegible deja la
  ambigüedad intacta. **397/397 candidatas resueltas, 0 retenidas.**
- ~~**[A33] El extractor comparaba el nombre del databank byte a byte**~~ **RESUELTO
  2026-09-02**: SQX no impone el nombre y cada proyecto lo escribe a su manera —NASDAQ tiene
  `Forward`, DAX40 y XAUUSD H4 tienen `FORWARD`—, así que 57 candidatas de dos activos enteros
  se retenían con `Forward: artefacto no resuelto` teniendo la evidencia delante. Se compara en
  casefold el nombre completo, nunca por prefijo: `RETEST OOS Darwinex` sigue siendo otro
  databank.
- ~~**[A30] Falta correr RETEST OOS y Walk-Forward Matrix en varios proyectos**~~ **CERRADO
  2026-09-27, sin ejecutar**: —
  *reformulado 2026-09-02 tras cerrar A32/A33*: con los dos bugs de emparejamiento fuera, el
  bloqueo restante es hueco de datos real en SQX, no código. **Un databank `WFM` con `.sqx`
  dentro no prueba que la matriz se corriera**: el `.sqx` de AUDCAD que sí funciona lleva 30
  corridas `Results/WF: N runs : X % OOS`; los de XAUUSD H1 y DAX40 SesionTarde sólo llevan
  `Results/Main`. Estado original (2026-09-02):

  | proyecto | retenidas | falta |
  | --- | --- | --- |
  | `XAUUSD_H1_Reemplazo2_KER_LinReg_noTP_EOD` | 99 | WFM (101 `.sqx`, **0 con matriz**) |
  | `Project_DAX40_M30_..._ORB_L_SesionManana` | 28 | RETEST OOS (0 `.sqx`) |
  | `Project_XAUUSD_H4_..._DiaEntero ( copia... )` | 22 | RETEST OOS **y** WFM (ambos a 0) |
  | `Project_DAX40_M30_..._v7_L_SesionTarde` | 14 | WFM (14 `.sqx`, **0 con matriz**) |
  | `Project_NASDAQ_H1_BS_Volumen_v7_L_Capa2` | 1 | WFM (0 `.sqx`) |
  | `XAUUSD_H1_Reemplazo1_ATR_LinReg Copia de Trabajo` | 1 | WFM (13 `.sqx`, **0 con matriz**) |

  **Reverificado 2026-09-26** (solo lectura contra disco; SQX estaba abierto y volcando
  databanks en ese momento, `seguro_para_escribir=false`, así que no se lanzó nada):
  - **`XAUUSD_H1_Reemplazo1/2`, RETIRADAS de esta tabla por decisión del operador**: ya no
    existen en `user/projects/` (solo sobreviven sus blocksettings en
    `user/BlockSettings_propios/`). Coherente con el cierre 2026-08-20 del mining de
    reemplazo XAUUSD sin candidata viable (previo a esta misma entrada A30) — no hay proyecto
    sobre el que correr nada.
  - **`Project_XAUUSD_H4_..._DiaEntero ( copia... )` no se localizó** con ese nombre exacto
    (existen `Project_XAUUSD_H4_BreakoutStop_{EOF_,}v7_L_DiaEntero{,_CapaMixta}`, ninguna
    "copia"); a diferencia de las dos Reemplazo, esto NO está confirmado por el operador como
    cierre — pendiente de aclarar si es la misma limpieza o un proyecto realmente perdido.
  - **`DAX40_M30_..._ORB_L_SesionManana`**: sigue en 0 `.sqx` en RETEST OOS, sin cambio.
  - **`DAX40_M30_..._v7_L_SesionTarde`**: la carpeta WFM pasó de 14 `.sqx` (sin matriz) a
    **0 `.sqx`**, tocada 2026-09-18. El operador confirma que conoce la causa (no requiere
    investigación); no se relanza sin que él lo pida.
  - **`NASDAQ_H1_BS_Volumen_v7_L_Capa2`**: sigue en 0 `.sqx` en WFM, sin cambio.

  Quedan 3 proyectos reales con el hueco abierto (2 RETEST OOS, 2 WFM — SesionManana solo
  RETEST OOS, SesionTarde y NASDAQ solo WFM) más 1 sin localizar. Retener sin evidencia de
  robustez sigue siendo lo correcto; no es un fallo del prefiltro. Mientras no se corran, la
  cola de validación la llena `AUDCAD/H4`, el único grupo con evidencia completa (232 de 397
  a fecha 2026-09-02).

  **Verificación final 2026-09-27, antes de intentar ejecutar**: el operador confirmó que el
  proyecto XAUUSD H4 no localizado es la misma limpieza que las dos Reemplazo (todo XAUUSD
  del mining de reemplazo cerrado 2026-08-20 queda fuera de esta entrada). Al comprobar los 3
  proyectos reales restantes vía `mcp__sqx__list_databanks` (motor SQX vivo, no solo disco),
  la databank `Results` — donde vivían las 28/14/1 estrategias retenidas que A30 daba por
  supervivientes — está **vacía en los tres, en vivo y en disco** (el operador confirma que
  fue intencional, mismo criterio que el WFM de SesionTarde). Sin estrategias retenidas no
  hay nada sobre lo que correr RETEST OOS/WFM: la única acción posible sería reminar la
  cadena completa desde `Build` en los 3 proyectos, que el operador decide hacer **él mismo,
  manualmente, en la UI de SQX** (retest sobre el databank afectado, cambiando el databank
  source para que las estrategias nuevas sustituyan a las viejas) — no vía este agente ni
  vía MCP. Se cierra sin ejecutar: no queda ninguna acción pendiente de Claude en A30.
- ~~**[A31] 22 XAUUSD H4 sin `.mq5`**~~ **RESUELTO 2026-09-02**: el operador exportó las 22
  parejas. Inventario de 375 a **397 STATIC_VALIDATED** (424 candidatas, 27 retenidas). Quedan
  13 sin símbolo (`None/H1`, `None/H4`) y 8 que fallan el parseo SQX144, sin cambio.
- ~~**[A27] `pipeline_min_freq_week=2` no encaja con el estilo minado**~~ **RESUELTO
  2026-09-02 por decisión del operador**: baja a **0,8** op/semana. Dentro del rango que fijó
  (0,8–1,0) es el único que preserva diversidad —a 0,8 pasan 43 candidatas de tres grupos
  (`DAX40/M30` 31, `XAUUSD/H4` 7, `XAUUSD/H1` 5); a 1,0 sólo 5 de dos grupos—. **El gate F4
  pasa de 0 a 43 candidatas.** La validez estadística no se relaja: la sostienen `min_trades=30`
  y `min_days=60`, que a 0,8/semana implican ~9 meses de historia. Aplicado en
  `PipelineGateConfig.min_freq_week` y en `thresholds.seed.json`. ASSUMPTIONS G13-33.

- ~~**[A23] Los MCP de MT5 no conectan en esta sesión**~~ **CORREGIDO EL DIAGNÓSTICO
  2026-09-26**: esta entrada afirmaba que bloqueaba P2.3 (telemetría viva). **Era falso** —
  mezclaba dos cosas distintas. Los `mt5_bepb`/`mt5_jjti`/`mt5-darwinex` son herramientas MCP
  de **este agente** para inspeccionar los terminales a mano (compilar, lanzar backtests,
  leer ficheros); P2.3 es el conector read-only del propio producto (servicios NSSM
  `StratOSMt5Readonly_*` en el VPS), que es un proceso totalmente distinto y **lleva
  funcionando de forma autónoma desde su arreglo en A35/A40**. Verificado en vivo: 313
  `equity`, 156 `heartbeat` y 1.884 `positions` ingeridos en los últimos 5 minutos.
  **P2.3 nunca estuvo bloqueado por esto.**

  La causa real del `ConnectionRefused` de los MCP: los tres apuntan a `127.0.0.1:2234[678]`
  y esos puertos sólo existen si hay un túnel SSH local reenviándolos al VPS — los servicios
  (los propios `terminal64.exe` de BEPB/JJTI/Incubadora, que sirven el bridge in-process) sí
  están vivos allí. Sin el túnel abierto en esta máquina, esos puertos locales no existen. Se
  abrió el túnel (`ssh -L 22346:127.0.0.1:22346 -L 22347:... -L 22348:...`) y los tres
  endpoints ya respondieron a través de él (401, no `ConnectionRefused` — el protocolo llega).

  **Addendum — el 401 no era de red, era de token, y ahí se detiene por decisión del
  operador:** tras reconectar con `/mcp`, los tres seguían rechazando la `Authorization`
  configurada. El bridge que sirve esos puertos vive **dentro** de los propios `terminal64.exe`
  de BEPB/JJTI (`FigaroBridgeLib.dll`, cargada como Library, 41 KB, sin coincidencia en todo
  `Apps_entorno_SQX`) — un componente de terceros sin documentación en este repo. Se buscó el
  token/config por lectura en `MQL5\Files`, `MQL5\Experts`, `MQL5\Services` (vacía),
  `MQL5\Logs` (Experts), el Journal del terminal (fuera de `MQL5\`, vía SSH) y `Terminal\Common\Files`
  compartida: **ninguno lo menciona**. El valor en `.mcp.json` viene del primer commit del
  repo (`284fb08`, 2026-08-25) sin mensaje que explique su origen — el operador tampoco sabe de
  dónde salió ("debió ser algo que Codex hizo"). **El operador decide dejarlo así** (opción 1):
  no bloquea nada real (P2.3 es independiente, ver arriba), y seguir habría exigido inspeccionar
  el binario de un componente de terceros contra terminales con dinero real, sin saber qué es.
  El túnel SSH que se abrió para probarlo se cerró (era un proceso huérfano tras un corte de
  sesión, PID confirmado y matado). **Si se retoma en el futuro**, no repetir esta búsqueda:
  empezar preguntando al operador si identifica "Figaro" como algo que instaló él mismo, o
  revisando el terminal por RDP en vivo (Herramientas → Opciones, o inputs de un EA/indicador
  en algún gráfico).

- ~~**[A47] Admisión contractual de las tres observaciones externas de Incubadora**~~ **CERRADO
  POR DECISIÓN DEL OPERADOR 2026-09-26** — *replanteado, no implementado*: al comprobar el
  estado real antes de escribir código, `SPH4L_1.26.31_4.2.29_MN24`, `USDJPYH1L_2.22.171_MN13`
  y `USDJPYH1L_5.15.110_MN8` resultaron ser bots `EXTERNAL_PRODUCTION` **ya en F7 sobre cuentas
  reales** (`bot.id` 31/9/7, BEPB/JJTI, semáforo VERDE, sizing 100 %), no candidatas nuevas.
  El operador confirma: la observación en la cuenta demo es **vigilancia paralela, sin
  intención de que pasen por F3–F7 de nuevo**. Admitirlas crearía un segundo `Bot` duplicando
  una identidad ya en F7 real — modelo de datos contradictorio, no una mejora. Sus filas en
  `external_ea_inventory` (81/82/83) permanecen como observación de identidad, sin
  `OperationalAsset`, baseline ni `PipelineCandidate`, de forma permanente y deliberada. La
  ruta general `incubator_admission` de ADR 0012 **ya existe y ya se usó** (bots 42/43 de
  AUDCAD, `scripts/admit_incubator_candidate.py`, 2026-09-08/10): sigue disponible para
  candidatas nuevas genuinas. ASSUMPTIONS G13-62.

## Estado activo G13 — operación separada

- **G13 F6 challenger/champion y staging:** implementado y desplegado como ledger y endpoint de lectura `GET /api/v1/pipeline-orchestrator/f6/staging-evaluations`; migración `b7c8d9e0f1a2` aplicada y salud HTTP 200. Falta observar una F6 real. Las candidatas 42/43 siguen F5, por lo que no se ha generado un plan ni se ha modificado Contabo. Próxima dependencia de datos: declarar un slot explícito y disponer de un champion único con matriz de correlación y R-multiples comparables. F7 queda exclusivamente humano.

- **G13 correlación de Portfolio:** migración `c8d9e0f1a2b3` aplicada; Portfolio y F6 ya no consumen `correlation_matrix` legacy. Los snapshots `MT5_BACKTEST` id=1 (candidatas 42/43, `Europe/Helsinki`, 3.178 días) y `MT5_REAL` id=2 (trades atribuidos de BEPB/JJTI, 1.240 días) están sellados y ambos tienen un par. Repeticiones idempotentes verificadas. Si una próxima ejecución carece de cobertura, la UI mostrará `WITHHELD`; no se debe usar la matriz legacy como sustituto. Pendiente de diseño posterior: sustituir el gate de admisión que actualmente hace una comparación cross-source por una comparación contractual homogénea o una comparación explícitamente emparejada, sin mezclar snapshots.

- **G13 bootstrap local:** falta materializar `.env.operational` con secretos propios y crear el usuario operador de la base nueva; queda prohibido copiar o leer los secretos de G12.
- **G13 histórico real — cerrado para la exportación disponible:** los HTML MT5 sellados importaron 4.304 posiciones cerradas reconciliadas (JJTI 1.945, BEPB 2.359) y retuvieron 205 ambiguas; el magic no expuesto queda huérfano auditable. El exportador read-only ya produjo/importó CSV sellados: JJTI 2.041 trades completos + 5 retenidos (`cedc0cb8174c…`) y BEPB 2.486 + 15 (`3804c3ea5ff6…`), ambos idempotentes al reimportar. La ventana efectiva observada empieza en 2025, pese a solicitar 2018: no se afirma cobertura anterior inexistente. Magics grandes se preservan como histórico `BIGINT` sin mapearlos al rango compacto de bots.
- **G13 cola de candidatas:** `StratOS_Operational` ya crea la vista FIFO sellada `runtime/operational/operational-tester-queue.json` y el diario append-only `operational-tester-queue-events.jsonl`; Pipeline sólo puede leer la vista. Cada apertura del Tester requiere confirmación individual en el ejecutable. El contrato de manifiesto/telemetría para adjunto demo ya está implementado; el próximo dato funcional es un paquete `VALIDADA` y un adjunto humano realmente observado por reporter, no abrir testers desde la UI.
- **G13 evidencia manual de Análisis — importador operativo:** `scripts/import_manual_sqx_mt5_run.py` y `Importar_corrida_manual_G13.bat` sellan de forma idempotente informe MT5, gráficas asociadas, configuración/CSV opcionales y fuentes verificadas contra inventario. `SQX_vs_MT5` v1.3.4 ya archiva automáticamente el CSV MT5, HTML nativo y sidecars, `.ini` efectivo y comparación TXT/HTML con hashes para que una corrida futura pueda pasar al importador sin relanzar el Tester. Los dos AUDCAD históricos permanecen `REPORT_ONLY`, porque sus CSV ya no existen y no se fabrica evidencia retrospectiva. Próximo dato necesario para ellos: una comparación voluntaria que genere/entregue CSV y TXT con `VEREDICTO`; no se registra `BACKTEST_VALIDATED` desde un HTML nativo.
- **G13 alpha decay real:** el inventario de gráfico, magic y fuente EA de JJTI/BEPB ya ancla las 40 altas F7 externas. El preflight de 35 pares dejó 8 aptos, 25 `WITHHELD_TICKS` y 2 `WITHHELD_SOURCE`; una sola corrida apta está iniciada en el Tester Darwinex aislado. Tras cada resultado sellado se compararán baseline/backtest, OOS real sellado y ventana forward creciente. El histórico HTML sin magic permanece huérfano, y ningún resultado implica promoción ni altera cuentas reales.
- **G13 reconstrucción AlgoWizard de retenidos:** `OROLONGLIMITSPPSTRH1D1 4.7.77` (BEPB/JJTI), `SP500LONGD1 REVERSION SL 2.86.54` y `SPA35LONGD1 REVERSION SL 1.31.56` tienen fuente `.mq5` y un plan de reconstrucción semántica sellada; los nuevos `.sqx` llevarán procedencia `RECONSTRUCTED_FROM_MQL5` y exigirán comparación fuente-vs-reconstruido antes del OOS real. `EURUSD_SELL_STOP_H4_LC_3.8.141` sólo conserva `.ex5`: queda bloqueada hasta recuperar un `.mq5` verificable, sin ingeniería inversa ni aproximación. Ver `docs/g13_algowizard_reconstruction_plan.md`.
- **G13 inventario EA externo:** los dos registros de magic del operador ya están sellados; las 40 asociaciones verificadas se incorporaron idempotentemente a F7 como `EXTERNAL_PRODUCTION` y a `external_ea_inventory` (BEPB 26, JJTI 14), con cuenta, comentario, magic, archivo/ruta `.ex5` y SHA-256. Quedan fuera 13 asociaciones ambiguas entre binarios con misma versión y hash distinto, una sin versión contrastable y dos filas BEPB con colisión `magic=10827`; no se seleccionan por nombre.
- **G13 identidad compacta de magics/comments:** Fase B quedó registrada tras aprobar el hash de propuesta: el registro local append-only contiene 40 `ASSIGNED` y 40 `MIGRATION_PLANNED`, con cadena validada e idempotencia comprobada. El comentario y nombre de archivo son idénticos: `<label histórico>_MN<nuevo_magic>`. Los dos hashes EX5 compartidos se desdoblan por cuenta (`a` BEPB, `b` JJTI) y conservan su `technical_strategy_key` común. StratOS no autoriza ni ejecuta cambios de EA, gráfico, Forja o cuenta.
- **G13 post-scan de migración — COMPLETADO EN LECTURA:** la lectura SSH/SFTP tras la persistencia manual observa los 40 pares aprobados cuenta+magic como `MIGRATION_OBSERVED`. JJTI conserva dos pares de ficheros `.chr` que serializan respectivamente el mismo gráfico interno: `chart17`/`chart19` (magic `30`) y `chart18`/`chart20` (magic `19`); EA, magic, comment y símbolo son idénticos y sólo cambia información visual. El escáner los deduplica por ID raíz MT5, mantiene todas las rutas como evidencia y falla cerradamente si un mismo ID declara otra identidad. El NQ de JJTI magic `38` queda sellado como `OPERATOR_RETAINED_OUT_OF_PROPOSAL`, sin reasignar ese magic ni alterar el lote aprobado. El comparador acepta sólo las formas exactas `.`/`_` de `CustomComment` y conserva el alias explícito Darwinex `DAX|DAX40` → `GDAXI`, manteniendo ambos símbolos. Hash EX5 y timeframe se heredan del F7 sellado bajo la confirmación del operador de que sólo variaron archivo/magic/comment; cuenta, gráfico, archivo, magic, comment y símbolo se vuelven a observar. Referencias: `docs/g13_magic_identity_migration_plan.md`, `docs/g13_magic_identity_operator_review.md` e informe local `runtime/operational/magic_identity/post_migration_scan_report.json`.
- **G13 análisis/backtest:** 227 parejas mantienen la admisión de inventario `STATIC_VALIDATED` y además su fuente WFM queda registrada como `STATIC_VALIDATED_WFM`, con criterios extraídos del `project.cfx` sellado. Esto no es `BACKTEST_VALIDATED`: falta ejecutar `SQX_vs_MT5` secuencialmente desde 2018 hasta la fecha de cada corrida, sellar report/trades/comparación y aplicar el veredicto propio de la herramienta. La razón WFM OOS/IS es `DERIVED_UNMAPPED` hasta validar su equivalencia con F2 o disponer de evidencia forward/MT5.
- **G13 terminal de backtest:** el operador autorizó el terminal Darwinex seleccionado en `SQX_vs_MT5` para Strategy Tester exclusivamente. El lanzador exige manifiesto F7, preflight `PREFLIGHT_OK`, `--max-runs` positivo, AutoTrading desactivado, identidad exacta de terminal y ticks completos; no usa ni cambia `terminal_despliegue`. El primer arranque fue rechazado antes del Tester porque la instancia configurada no aceptó cierre limpio; hay que liberar o corregir sólo ese terminal, nunca forzar el cierre de JJTI/BEPB.
- **G13 costes SQX↔Tester:** contrato G13-59 revisado con autorización del operador (2026-09-24): el `Comm/Swap` combinado nativo de SQX puede satisfacer la equivalencia del total sólo con conciliación 1:1 del set completo contra comisión+swap MT5, dirección/volumen iguales y diferencia ≤ 0,01 en cada trade. La igualdad agregada con divergencias individuales bloquea. La corrida excepcional única de `AUDCADH4L_ForexMinorLateral_Strategy 2.92.87` dio rendimiento `VALIDADA`, costes `BLOCKED`, sin `BACKTEST_VALIDATED` ni admisión a Incubadora. Los CSV originales están sellados en `runtime/operational/backtests_diagnostic/20260924T063537Z_28e633a9a3f7/`. El emparejador estricto ya exige ambos extremos y correspondencia unívoca: 177 pares de 204/198; los 177 discrepan, delta +435,75 USD. Revisión del `.sqx` exacto confirma `SizeBased=5` y swap long en dinero −0,5, mientras los deals MT5 acumulan +324,73 USD de swap y 173 créditos; la tarifa pública actual de Darwinex también lista swap long AUDCAD positivo y comisión 2,50 AUD por orden/contrato. La configuración SQX de swap no equivale a la evidencia MT5. El requisito de paridad histórica de G13-59 se mantiene cuando se afirme equivalencia SQX↔MT5; G13-61 autoriza una vía de sensibilidad independiente para la decisión bajo tarifas vigentes.

  **Actualización 2026-09-27 (G13-67)**: la causa no era el rollover — era el swap de
  `data.db` con el signo invertido (`-0,5` configurado vs `+3,93` real). Corregido en
  `data.db` para AUDCAD y 14 instrumentos más; relanzada la corrida
  (`runtime/operational/backtests_diagnostic/20260927T093208Z_ed75e0ea14f9/`): delta cae
  de 759,34 a **125,57 USD** (−83 %), delta máxima por trade de 6,18 a 2,19. El operador
  señaló que exigir exactitud al céntimo en el 100 % de la muestra era irreal —
  implementada tolerancia híbrida por trade (suelo 2,00 USD o 30 % del coste) + cobertura
  mínima del 90 % (política `PAIRED_TRADE_COST_TOTALS_CENTS_V4_HYBRID_TOLERANCE_COVERAGE`,
  en `compare_sqx_vs_mt5.py` y `cost_gate.py`). Recalculado sobre la evidencia ya sellada:
  **`PROVEN`, cobertura real 92,09 %** (163/177). Detalle completo en `ASSUMPTIONS.md`
  G13-67.
- **G13 incubadora:** la cuenta `BROKER_DEMO` ya existe. Tres EAs manualmente adjuntados (`SPH4L_1.26.31_4.2.29_MN24`, `USDJPYH1L_2.22.171_MN13`, `USDJPYH1L_5.15.110_MN8`) quedaron registrados como observaciones externas append-only, con ruta y SHA-256 `.ex5` contrastados en lectura y `bot_id=NULL`; no son `BACKTEST_VALIDATED`, baseline, bot ni F5. Ver `docs/g13_incubator_external_observations_2026-09-14.md`. La cola FIFO y el límite de 8 sólo pueden actuar después del gate de backtest/baseline y de la admisión sellada explícita por EA; el contrato demo será 10 % de capital, 0,2 % por trade y DD contractual 5 % durante la gracia explícita. Ver `docs/g13_closure_gate_matrix.md`.
- ~~**G13 UI:** Faltan selectores/etiquetas de procedencia para Portfolio, Salud, Riesgo,
  Auditoría y Dominical.~~ **YA ESTABA HECHO desde G10, verificado 2026-09-28**: `git log`
  confirma `0d877b0 feat: procedencia declarada en las 5 vistas agregadas que faltaban` +
  `0a47edc feat: los agregados declaran que parte pertenece a un bot vivo`. `<ProvenanceBadge
  />` (`frontend/src/components/domain/ProvenanceBadge.tsx`) está montado en las 5 páginas
  exactas (`PortfolioPage.tsx`, `SaludPage.tsx`, `RiesgoPage.tsx`, `AuditoriaPage.tsx`,
  `DominicalPage.tsx`, y también en `PipelinePage.tsx`), consume `GET /data-provenance`
  (`header.py`) y distingue `BROKER_REAL`/`BROKER_DEMO`/`FIXTURE` + `is_mixed` +
  atribución a bot vivo. 7/7 tests de `ProvenanceBadge.test.tsx` y 58/58 de la suite
  completa de frontend, ambos verdes en esta sesión. Nadie tachó esta entrada cuando se
  cerró en G10 — puro desfase documental, no trabajo pendiente. **Sigue sin hacer**: el
  recorrido autenticado/WebSocket end-to-end contra sesión real (P4.2 del plan de
  continuación) y los estados `DERIVED`/`ABSENT` explícitos (hoy la badge solo cubre
  `BROKER_REAL`/`BROKER_DEMO`/`FIXTURE` + mixto, no un cuarto/quinto estado).
- **G13 Pipeline, fidelidad de estructura:** superado por ADR 0012. Ya no se preserva el Kanban F1--F7 como objetivo de producto; la superficie de operación se limita a Incubadora y portfolios reales.
- **G13 Pipeline operacional (ADR 0012):** el operador ha retirado F1--F3 del producto visible. Sustituir la tarea anterior de fidelidad F1--F7 por un E2E de Incubadora → evaluación → propuesta humana de cartera, más telemetría read-only separada de BEPB/JJTI. Implementar `incubator_admission` como ledger sellado que acepte sólo identidad, perfil y evidencia explícita; no reutilizar las acciones F1/F2/F3 ni inferir admisiones desde HTML, nombres o carpetas.
- **G13 ejecución segura del histórico:** el terminal remoto JJTI tiene EAs reales en funcionamiento. No se debe usar `terminal64.exe /config` para lanzar un script de exportación sobre esa instancia hasta contar con un procedimiento que no abra/cierre ni cambie el perfil de la terminal activa; el CSV legado no se importa porque no cumple el contrato de deduplicación sellada.

- **G13-59 costes — autorización posterior y bloqueo probatorio:** el operador autorizó el 2026-09-24 una segunda corrida diagnóstica excepcional en copia aislada de `AUDCADH4L_ForexMinorLateral_Strategy 2.92.87`, fuera de cola/Incubadora. No se ejecutó porque no existe proyecto/databank duplicado recalculable para reexportar la List of Trades con ajustes y no se dispone de costes históricos Darwinex para el rango completo. No editar sólo `lastSettings.xml` ni calibrar contra el CSV del Tester: eso mezcla costes de una configuración con resultados de otra o introduce circularidad. Reanudar cuando haya copia reproducible y fuente histórica de comisiones/swaps; entonces una única corrida, veredicto de costes independiente, y sello sólo si el gate queda `PROVEN`.
- ~~**[Propuesta, sin implementar] Cablear `economia.py`/`darwinex.py` (spread_sqx) en `capa2_candidate_selector/cost_gate.py::build_audit()`**~~ **IMPLEMENTADO 2026-09-27 (G13-69):** `cost_gate.py` añade `cross_validate_swap_against_live_sources()` (importa `spread_sqx` por ruta relativa entre apps hermanas, sin paquete instalado) que reconstruye el XML del swap del `.sqx` y reutiliza `economia.diagnostico()`/`darwinex.activo()` sin duplicar su lógica de tolerancia/moneda. `build_audit()` acepta `swap_live_check` como **resultado ya calculado** (no un callable): el preflight nunca debe tocar MT5, así que solo `run_operational_sqx_mt5_backtest.py` lo ejecuta, y solo cuando `--launch` es real. Como esa consulta puede relanzar el terminal si lo encuentra cerrado (mismo efecto de G13-68), el lanzador vuelve a cerrarlo con `close_target_terminal` justo después. Fail-closed: cualquier estado que no sea `"ok"` (incluida una fuente inalcanzable) añade `SQX_SWAP_NOT_CONFIRMED_AGAINST_LIVE_MT5_AND_DARWINEX` y bloquea. 8 tests nuevos en `capa2_candidate_selector/test_cost_gate.py` con dobles de `economia`/`darwinex`/`mt5_spread` (sin red ni MT5 real); suites completas verificadas: 49/49 (`capa2_candidate_selector`), 268/268 (`StratOS-QXPro-v2/scripts`).

- **[G13-61] Sensibilidad de tarifa vigente como gate alternativo — gate implementado; persistencia pendiente:** el operador autorizó aceptar el escenario tarifario vigente para `BACKTEST_VALIDATED`, pues refleja mejor las condiciones actuales. Implementado en `scripts/build_current_tariff_sensitivity.py` y `scripts/record_operational_backtest.py`: paquete derivado y sellado que enlaza corrida padre inmutable, snapshot oficial fechado, export real de deals y `REAL_TICKS`, sin reclamar equivalencia histórica SQX↔MT5. Paquete generado y dry-run `VALIDADA`: `runtime/operational/backtests_diagnostic/current_tariff_sensitivity_20260924_077d74f1cd98/run-manifest.json`; 245 tests scripts pasan. La escritura del evento no se completó: `stratos_operational` no existe en Postgres local; no se creó base, inventario, F3 ni admisión a Incubadora. Reanudar sólo cuando esté disponible el Postgres operacional y verificar el activo por hashes exactos.

## Estado activo G12

### Defectos a corregir

- ~~G12 Cuentas/EA: modo operativo, permiso por gráfico, sizing y panel de deriva.~~ **RESUELTO Y REPETIDO EN G12-02**: 11/11 `PAPER`/OFF/50 %, alerta de deriva de tres campos y cobertura de contrato documentadas.
- ~~G12 procedencia de pestañas~~ **SUPERADO, verificado 2026-09-28**: el recorrido de
  `docs/g12_tabs_provenance_validation.md` (2026-08-29) era contra el stack `stratos_g12`,
  formalmente retirado. De sus 5 gates: (1) procedencia explícita — hecha vía
  `ProvenanceBadge` en las 5 vistas agregadas (ver entrada de arriba, G10); (2) desfase
  `USDJPYH1Lcity_5.15.110` — ya no aplica, el bot/candidato no existe en `stratos_operational`;
  (3) benchmark `FileNotFoundError` — ya marcado RESUELTO 2026-09-02 más abajo en este mismo
  fichero; (4) aislar por cuenta Portfolio/Salud/Riesgo/Auditoría — cubierto por el mismo
  `ProvenanceBadge` (declara mezcla vía `is_mixed`, no aísla series completas, pero declara
  la procedencia); (5) repetir con sesión autenticada — sigue sin hacer (mismo P4.2 ya
  anotado). No queda ningún gate de este documento bloqueando activamente.
- ~~G12 Pipeline: `USDJPYH1Lcity_5.15.110` tiene candidato F4 y bot F3.~~ **YA NO APLICA,
  verificado 2026-09-28** (no "resuelto" — obsoleto por retirada arquitectónica, no por una
  transición append-only): consulta read-only a `stratos_operational` (la BD real, no
  `stratos_g12`, ya retirado) confirma cero bots en fase F3 y ningún bot con ese nombre;
  las únicas combinaciones `origin_kind`/`pipeline_phase` que existen hoy son
  `EXTERNAL_PRODUCTION`/F7 (40 bots) e `INCUBATION`/F5 (2, las AUDCAD). La inconsistencia
  vivía en el fixture del incubador G12, retirado formalmente
  (`runtime/operational/g12-incubator-retirement.json`) — no sobrevivió a la transición a
  G13. Ninguna transición append-only que aplicar: no hay filas que corregir.
- ~~G12 Portfolio: el benchmark devuelve `FileNotFoundError` dentro del contenedor en vez de
  un estado de ausencia controlada.~~ **RESUELTO 2026-09-02**, encontrado por el recorrido
  autenticado: el CSV no viajaba en la imagen (`_DEFAULT_CSV_PATH` usa `parents[4]`, que en
  el contenedor resuelve a `/scripts/data/...`) y el loader reventaba en vez de declarar
  ausencia. Ahora el Dockerfile lo copia, el compose declara `BENCHMARK_CSV_PATH` y el
  endpoint responde `null`. Verificado en vivo: 200.
- `e2e-acceptance-full`, criterio 9 Lyra×Phoenix: fixture `full` no determinista respecto al umbral de redundancia.
- Precios sintéticos no realistas para GDAXI/NDX/SPX500/US30: degradan la interpretabilidad de `r_multiple`.
- Auditoría de agregados `.scalar_one()` sobre hypertables: cada uso debe clasificarse y los agregados que pueden no devolver fila física deben tener regresión contra TimescaleDB real.
- Fixture de salud: 28/32 bots quedan AMARILLO por aplicar métricas acumulativas a 5,5 años sintéticos. G11 lo corrige solo en el fixture, sin cambiar la política productiva.

### Capacidades bloqueadas por datos o artefactos externos

- Backtest vs Forward: RESUELTO EN CÓDIGO. El importador local SQX144 crea baselines append-only con SHA-256 y procedencia; Pipeline/UI comparan baseline con forward y muestran ausencia sin inventar métricas.
- FX en EUR: RESUELTO EN CÓDIGO. El importador local sellado de CSV fechado preserva procedencia, falla cerrado ante conflicto y Riesgo conserva `unconverted_currencies` sin tasa válida. Falta únicamente el CSV operativo del operador.
- Fecha de entrada a pipeline/Graveyard: las transiciones nuevas ya se conservan append-only; no existe dato histórico que se pueda backfillear con honestidad.
- EA reporter v1.1: estados `ea_state`, heartbeat, equity y posiciones ya llegan desde MT5 demo con sellos válidos. Faltan fills/rechazos reales de EA para TCA; no se inventa esa evidencia.

### Decisiones deliberadamente fuera de G11

- `small_scale.yaml` sigue siendo una guía manual, no una configuración runtime.
- Tipos de API generados manualmente se reevaluarán solo si la superficie vuelve a crecer de forma sustancial.
- El paso a producción no forma parte de G11; exige confirmación posterior tras la validación demo.

## Evidencia y contexto histórico

Las entradas siguientes preservan el detalle de hallazgos y decisiones previas. Los elementos tachados están resueltos; los abiertos se reflejan en las categorías de G11 anteriores.

- **Docs sueltos en `doc_app\` ajenos al prompt maestro**: `Documento_Auditoria_Estrategias_SQX.md`, `Documento_Auditoria_Estrategias_SQX (1).md` y `Strategy_Robustness_Auditor_SRA_Especificacion_Proyecto.md` pertenecen a otro proyecto ("SQX Analyzer Pro"), no al árbol de referencias de PARTE 0.1. Ver `ASSUMPTIONS.md` G0-09. Han sido movidos a su carpeta ( `doc_app` es solo lectura para el agente).
- ~~**`api-gateway\` real**~~ **RESUELTO en G9** (ver `ASSUMPTIONS.md` G9-00): proxy transparente + rate-limit + WS broker, con CI propio.
- ~~**Página `docs\runbook.md` completa**~~ **RESUELTO en G9** (ver `ASSUMPTIONS.md` G9-02/G9-03).
- ~~**`Account.login` sin `UNIQUE`**~~ **RESUELTO en G10**: `UniqueConstraint` añadido (migración `0c2dfc843cea`), 0 duplicados verificado antes de aplicar.
- ~~**Chips de `routers/health.py` sin fórmula propia**~~ **RESUELTO en G10** (ver entrada de "Salud" más abajo, sección G7).
- ~~**`Trade.r_multiple` nunca poblado**~~ **RESUELTO en G10**: `instrument_spec` (tick_value/tick_size reales importados de `Apps_entorno_SQX/spread_sqx` vía SQX, `scripts/import_instrument_specs.py`) + `formulas/trading.py::r_multiple_net_of_costs` (`profit_net = profit+commission+swap`, decisión propia) — backfill real (`scripts/backfill_r_multiple.py`, 15.944 trades) + wiring en `core/ingest/services/trades.py` para los nuevos. Símbolo sin spec o sin `sl` se queda NULL, no se inventa. Ver también el hallazgo de precios de seed no realistas más abajo.
- **Sin curva de equity ni Sharpe por bot individual**: PARTE 8/G2 solo define `historical_var`/`historical_cvar`/`monte_carlo_maxdd` sobre equity de **portfolio** (`real_portfolio_equity_curve`, G5). No existe un equivalente por bot — cualquier vista futura que quiera "Sharpe de este bot" o "curva de equity de este bot" necesita fórmula y agregación nuevas, no reutilizables de lo ya construido.
- ~~**`POST /ingest/ea_state` no reporta el sizing aplicado**~~ **RESUELTO en G10 (backend, sin verificar contra EA real)**: `EaState.sizing_pct` (columna nueva, opcional, migración `3960d7d19b0d`) + `config_drift.py::compute_drift()` compara contra `Bot.sizing_current_pct` cuando llega. **El conector/EA real sigue sin mandarlo** (`mt5-connector/src/connector/protocol.py`, sin cambios) — `sizing_drift` queda en `None` (no comparable) hasta que lo reporte, nunca se inventa la comparación. Backend construido a spec, no verificable sin hardware real (mismo patrón que G4).
- ~~**`services/risk.py::compute_exposure()` sin conversión de divisa**~~ **RESUELTO en G10**: `symbol_currency` + `exposure_subtotals_by_currency()` (unidad nativa) y, además, `services/fx.py::eur_converted_pnl()` + `GET /risk/exposure/eur` (conversión REAL a EUR vía `FxRate`, esquema desde G1). **Caveat honesto**: `FxRate` no la puebla ningún proceso todavía (no hay feed de FX real ni histórico ingerido) — el servicio funciona correctamente cuando hay una tasa (probado con datos sembrados a mano), pero en producción hoy devolvería todas las divisas no-EUR como `unconverted_currencies` hasta que exista una fuente real de tasas (misma naturaleza de gap que `ea_state` sizing, backend construido y probado, sin poblar con dato real).
- ~~**Refresh JWT sin revocación**~~ **RESUELTO en G9** (ver `ASSUMPTIONS.md` G9-01): denylist real vía Redis, rotación revoca el refresh usado, `POST /auth/logout` revoca ambos tokens.
- ~~**Bundle de `frontend` >500 kB**~~ **RESUELTO en G9** (ver `ASSUMPTIONS.md` G9-05): code-splitting por ruta + `manualChunks`, bundle principal 329kB (104kB gzip), sin aviso de Rollup.
- **Tipos de API generados a mano, no desde `/openapi.json`** (decisión de G6, reevaluada en G7): con la superficie completa de endpoints consumidos (~14 archivos de `api/endpoints/`, todos verificados campo a campo contra el Pydantic real de cada router), seguir escribiendo los tipos a mano siguió siendo más simple que introducir un paso de codegen nuevo — sin fricción real detectada. Reevaluar en G8/G9 si la superficie vuelve a crecer de forma significativa.
- ~~**"Vista dominical" (PARTE 14/16 criterio 14) sin construir**~~ **RESUELTO en G10 (grupo n)**: ruta `/dominical` nueva, de nivel superior (NO anidada bajo `RootLayout`, NO en la `TabBar` — enlace discreto en `AppHeader` junto al badge de rol). Errores de EA (`GET /alerts`, nuevo — gap real: `Alert(module="config_drift")` ya se poblaba desde G5 pero ningún router lo listaba), desconexiones (reusa `HeartbeatCard`/`WatchdogTable` de Ejecución) y noticias de la semana entrante (reusa `NewsShieldPanel` con `hours=168`, ahora prop configurable). "Órdenes rechazadas" documentado como pendiente de la v1.1 del EA reporter (mismo estado que TCA). Criterio de salida verificado con test de contenido real (`vista_dominical.spec.ts`): confirma que EQUITY/P&L DÍA/DRAWDOWN nunca aparecen — la página nunca importa `AppHeader`/`StatCard`/`formatAmount`.
- **Screenshot-diff de G8 sensible a re-siembras y a paralelismo alto**: los 10 specs nuevos de pestañas pasan 12/12 en serial (`--workers=1`) contra un seed fijo, pero regenerar el seed (datos aleatorios + contenido relativo a `now`, PARTE 13) o correr con muchos workers en paralelo bajo contención de CPU puede desviar 1-2 pestañas por encima del umbral del 2% en regiones no enmascaradas (fechas de heartbeat, ventana de News Shield, tablas de correlación/watchdog). Las aserciones de CONTENIDO (la parte que prueba corrección funcional) son 100% estables — no es un bug de la app. Mitigado en CI con `--workers=1` + `retries: 2` (ya en `playwright.config.ts`); si en el futuro se quiere paralelismo real, habría que enmascarar más regiones por pestaña o fijar el seed con una fecha `now` congelada en vez de `datetime.now(UTC)`.
  - ~~**Mecanismo exacto identificado en G9**~~ **RESUELTO en G9-07** (ver `ASSUMPTIONS.md`): 2 elementos condicionados a la hora REAL de ejecución (no al seed) que ninguna máscara podía cubrir sin antes arreglar esto — el badge "DATOS STALE" de `AppHeader.tsx` y el bloque heartbeat/latencia/uptime de `AccountCard.tsx` se montaban/desmontaban según el estado en vivo, desplazando la página entera. Fix de raíz: los 2 componentes ahora reservan SIEMPRE su altura (`invisible` en vez de ausentes) — determinismo verificado con tiempo real transcurrido (130+s cruzando el umbral de staleness, mismo baseline sigue pasando). Coste aceptado: un hueco reservado, invisible, cuando el badge/detalle no aplica.
- ~~**[G13-74] `e2e-acceptance-full` inestable en local (criterios 6/7/8/9)**~~ **CERRADO
  2026-09-28 — diagnóstico de ayer corregido con evidencia empírica, no era lo que parecía.**
  El análisis de código del 2026-09-27 (leído `services/correlations.py`, `seed.py`,
  `scenarios.py`) identificó dos mecanismos DISTINTOS que se habían mezclado en una sola
  entrada:
  1. **Criterios 6/7/8: NO es un bug de código.** `test_criterion_7` llama
     `datetime.now(UTC)` **en vivo dentro del propio test** (no lee un valor persistido) y
     evalúa el watchdog contra trades sembrados hace tiempo; `test_criterion_6` lee el
     recuento de `Alert` que dejó el `run_audit_daily` de la ÚLTIMA vez que se sembró. El
     propio docstring del fichero de test ya lo advierte: "el seed real... ya corrido ANTES
     de esta suite" — el contrato es sembrar y testear en el mismo momento, exactamente
     como hace CI (`e2e-acceptance-full`: checkout→migrate→seed→test, todo en el mismo job,
     segundos de diferencia). **Verificado empíricamente 2026-09-28**: el Postgres local
     llevaba `seeded_at=2026-08-27` (**32 días** sin resembrar) — causa real de los 3
     fallos. `python scripts/seed.py --profile full --reset` fresco +
     `pytest tests/e2e/test_g8_acceptance_criteria.py` inmediatamente después → **9/9
     passed**, sin tocar una sola línea de código. No hay nada que arreglar aquí; es
     higiene de entorno local, no deuda de código.
  2. **Criterio 9 (correlación): riesgo estructural real, pero de plazo largo (no urgente).**
     Este SÍ lee un valor persistido (`CorrelationMatrix`, calculado una vez al sembrar con
     el `now` de ESE momento) contra una ventana de `window_days=1240` sobre una historia de
     trades fija en `FULL_HISTORY_END=2026-06-30`. Mientras la ventana siga cubriendo una
     porción sustancial de esos 5,5 años de historia — hoy, 90 días después de
     `FULL_HISTORY_END`, sigue pasando con margen —, no hay problema práctico. Solo
     empezaría a fallar de verdad cuando `now` real se aleje lo bastante de
     `FULL_HISTORY_END` como para que la ventana de 1240 días deje de capturar suficiente
     historia correlacionada — del orden de años, no de días. No se arregla ahora
     (sería ingeniería prematura para un riesgo a años vista); revisar si algún día
     `e2e-acceptance-full` empieza a fallar SOLO el criterio 9 con una BD recién sembrada
     (eso sí sería la señal de que ha llegado el momento).
  **Lección operativa para sesiones futuras**: antes de investigar cualquier fallo de
  `test_g8_acceptance_criteria.py` en local, comprobar primero `seeded_at` en
  `system_config` (`key='seed_profile'`) y resembrar si tiene más de unas horas —
  ahorra la mayor parte de las falsas alarmas de este fichero.
- **Precios de seed no realistas en GDAXI/NDX/SPX500/US30** (encontrado en G10 al correr `backfill_r_multiple.py` contra Postgres real): varios trades sembrados de estos 4 índices tienen `open_price`/`sl` en una escala que no corresponde al price level real del instrumento (p.ej. `open_price=1.00000`/`sl=0.99000` para `US30`, que en realidad cotiza en el orden de 30.000-40.000) — probablemente `scripts/seed_lib/trades_history.py` generó el rango de SL sin tener en cuenta la escala de precio real de cada símbolo. Consecuencia real: `r_multiple` calculado sobre esos trades da magnitudes absurdas (hasta ~6,8x10⁴ en `US30`, miles en `GDAXI`/`NDX`/`SPX500`), lo que ya obligó a ampliar `RMultiple` de `NUMERIC(8,4)` a `NUMERIC(12,4)` (ver `column_types.py`) solo para poder escribirlo sin overflow — el valor en sí sigue sin ser interpretable como un R real hasta que el seed use precios realistas por símbolo. No se corrige aquí (fuera de alcance de G10, que no toca `scripts/seed.py`).

## G7 — huecos de negocio por pestaña (backend no calcula el dato, no es solo falta de exponerlo)

Decisión del operador antes de empezar G7 (ver `ASSUMPTIONS.md` G7-01): estos huecos se documentan y se omiten en la UI, no se inventan. Cada uno requeriría una fórmula/servicio/endpoint nuevo en core-engine — fuera de alcance de una fase de frontend.

- ~~**Portfolio**: sección "¿Añade valor real el portfolio?"~~ **RESUELTO en G10**: `services/benchmark.py` (nuevo) — `portfolio_monthly_returns()` (EquitySnapshot real) + `load_sp500_monthly()` + `compare_to_benchmark()` (CAGR/alfa/beta/t-stat/Information Ratio/Batting Average/Up-Down capture, reutiliza `ols_alpha_beta` de G2). `GET /portfolio/benchmark`. **Caveat heredado de G8** (`scripts/tests/test_sp500_benchmark.py`): el CSV solo tiene datos de mercado reales para 2021, el resto es sintético — comparar contra el seed real de este sistema puede dar una correlación espuria, no es un bug del cálculo (documentado en el propio docstring del servicio). **Wiring de frontend: RESUELTO en G10 (m-04)** — `PortfolioBenchmarkCard.tsx` consume el endpoint completo (8 celdas de métricas + badge de veredicto + chart de 2 líneas), incluido `monthly_points` (campo nuevo, la serie mensual alineada ya se calculaba internamente y se descartaba antes de esta unidad).
- ~~**Salud**: Sharpe rolling, Win Rate drift, Payoff, Duración media de trade~~ **RESUELTO en G10**: `formulas/trading.py::rolling_sharpe()` (nueva, refactor DRY sobre `pipeline_gate.py::_trade_sharpe`) + `win_rate_drift`/`payoff_ratio`/`avg_trade_duration` (ya en el grupo (b) de G10) — `services/semaphore_sweep.py::assemble_health_chips()` las ensambla, `HealthCard.tsx` las muestra en el mismo orden que la captura. **Bots** sigue con el mismo gap pendiente para su propia vista (ver más abajo, "panel Métricas completas").
- ~~**Bots**: panel "Métricas completas" (Sortino, Calmar, Ulcer Index, Recovery Factor, MCL)~~ **RESUELTO en G10**: `formulas/trading.py`/`formulas/portfolio.py` (Sortino, Calmar, Ulcer, RecoveryFactor, TDD 100%) + `services/bot_equity.py::bot_pnl_curve()` como base de curva por bot (base nominal 100, no es equity real por bot — ver su docstring); MCL ya existía (`loss_streak()`, G2). ~~"Posiciones abiertas" por bot~~ **RESUELTO en G10** (`GET /bots/{id}/open-positions`). ~~"Histograma de retornos (R)"~~ **RESUELTO en G10** (`Trade.r_multiple` poblado, ver entrada más arriba). ~~P&L acumulado por bot~~ **RESUELTO en G10** (`bot_pnl_curve()`). ~~"Contribución al portfolio" más allá de `capital_allocated_pct`~~ **RESUELTO en G10 (m-02a/m-02b)**: `compute_portfolio_contribution()` (`services/bot_equity.py`) — `pct_of_total_pnl`/`correlation_vs_rest`/`pnl_bot`/`pnl_account`, `GET /bots/{id}/metrics`. `BotDetail.tsx` consume todo el endpoint (Rolling vs Baseline de 7 filas, Métricas completas de 15 celdas, Contribución, Posiciones abiertas, Histograma de retornos R, P&L acumulado con selector de rango).
- ~~**Riesgo**: "Histórico" DD% ... de Monte Carlo~~ **RESUELTO en G10** (`GET /risk/montecarlo/history`; la fecha de firma, `ts`, ya estaba en `MonteCarloResponse` desde G5). ~~"Trades en ventana de noticias (30 días)" de News Shield~~ **RESUELTO en G10** (`services/news.py::trades_in_news_window()` + `GET /news/shield/trades`, cruza trades reales contra `NewsEvent` por `symbol_currency`). ~~MAX DD/DURACIÓN DD del panel de kill-switch~~ **RESUELTO en G10** (`services/killswitch_sweep.py::current_episode_stats()` + `KillSwitchStatusResponse.episode_max_dd_pct`/`episode_duration_seconds`). ~~subtotales por divisa de Exposición~~ **RESUELTO en G10** (ver entrada de `compute_exposure()` más arriba). **Wiring de frontend de los 4 cierres de arriba: RESUELTO en G10 (m-03)** — `KillSwitchPanel.tsx`/`ExposureCard.tsx`/`NewsShieldPanel.tsx`/`MonteCarloList.tsx` consumen los 4 endpoints/campos nuevos, verificado en vivo.
- ~~**Pipeline**: tabla "Backtest vs Forward" (`CandidateResponse` no trae métricas de
  baseline/IS)~~ **RESUELTO, verificado 2026-09-27**: esta entrada quedó obsoleta desde
  G13-41/49 sin que nadie la tachara. `import_archived_sqx_mt5_evidence.py` sí crea filas
  `Baseline` reales (también `sqx_baseline_parser.py`/`admin_imports.py`). Consulta
  read-only a `stratos_operational` confirma **2 filas reales**: `id=2` (bot 42, magic
  295) e `id=3` (bot 43, magic 243), ambas `source='BACKTEST'` — coincide exactamente con
  `baseline_id=2`/`baseline_id=3` que ya documentaba `phase_status.md` G13-49. La línea
  564 de este mismo fichero ya decía "RESUELTO EN CÓDIGO" para este mismo punto; esta
  entrada (más antigua, de G7) simplemente no se había reconciliado con esa.
- ~~**Escalado**: columnas Trades/Retorno/Max DD de "Evolución mensual"~~ **RESUELTO en G10**: `services/ums.py::monthly_evolution_metrics()` (trades cerrados reales + curva de equity real, TDD) se mezcla en `metrics` tanto en `confirm_advance` como en `check_automatic_downgrade`. Sin equity suficiente en la ventana, `retorno_pct`/`max_dd_pct` quedan en `None`, no se inventan. **Wiring de frontend: RESUELTO en G10 (m-05)** — `MonthlyEvolutionTable.tsx` añade las 3 columnas, `—` cuando la fila no trae el dato (filas que no corresponden a un evento de ascenso/bajada real).
- ~~**Graveyard**: fecha de inicio del rango~~ **RESUELTO 2026-09-27, parcialmente**: la
  tabla de histórico que G10 daba por inexistente en realidad ya existía sin que este
  ítem ni `docs/adr/0006` lo reflejaran — `PipelinePhaseTransition` (creada en G11,
  append-only) conserva la transición de alta a F1 (`from_phase IS NULL`). `GET
  /api/v1/cemetery` ahora expone `entered_pipeline_at` cruzando `CemeteryEntry.bot_id` →
  `PipelineCandidate` → esa transición; `CemeteryCard.tsx` muestra el rango completo
  cuando existe. Sigue `None` (declarado, no inventado) para bots admitidos antes de G11
  o sembrados sin pasar por F1-F7 — mismo criterio de "no inventar" que motivó el ADR
  original. La captura de referencia no cambia: el seed de demo no crea
  `PipelineCandidate` para sus 9 lápidas. Tests: 3 nuevos en `test_cemetery.py`
  (con historial, sin candidato, caso base), suite completa core-engine verificada.
- ~~**Auditoría**: lista de "tramos sin envío" detallados~~ **RESUELTO en G10**: `compute_send_continuity()` ya calculaba `gaps` con detalle por tramo desde G5, solo faltaba exponerlo — `GET /audit/continuity-gaps` (no era una fórmula nueva, solo wiring). **Wiring de frontend: RESUELTO en G10 (m-06)** — `ContinuityCard.tsx` lista los tramos por cuenta (inicio → fin, duración), verificado en vivo.
- ~~**Cuentas/EA**: equity/balance/margen libre/margin level por cuenta~~ **RESUELTO en G10** (`AccountResponse` incluye el `EquitySnapshot` más reciente por `account_id`; `None` si la cuenta nunca reportó uno). **Wiring de frontend: RESUELTO en G10 (m-07)** — `AccountCard.tsx` muestra las 4 celdas (grid siempre presente, "—" por celda faltante — mismo criterio anti-desplazamiento que G9-06/G9-07), verificado en vivo con cuenta con snapshot parcial y cuenta sin snapshot. `ea_required_version` sigue sin resolver (no existe el concepto de "versión esperada" en ningún sitio del sistema — fuera de alcance de G10, ver Contexto del plan de la fase).
- **Ejecución/Cuentas-EA**: TCA y Perfil de broker — no es un hueco a resolver con una fórmula nueva, la propia captura documenta que depende de la v1.1 del EA reporter (fuera de alcance del conector actual, PARTE 9.1 "sin consumidor aún" para `/ingest/execution`).

## G13-76 — agotamiento del pool DB por single-worker de core-engine (RESUELTO 2026-09-28)

Encontrado en un "smoke real" pedido explícitamente por el operador ("creo que hay cosas
rotas y el acceso también da problemas"), tras dos fixes previos en la misma sesión
(crash de `AppHeader`, email-normalization en login) que NO explicaban el patrón completo
de fallos que el operador seguía viendo.

**Síntoma**: casi cualquier ruta de la API (`/auth/refresh`, `/header/summary`, `/bots/*`,
`/pipeline-orchestrator/f5/incubation`, `/config/semaphore-instructions`, etc.) devolvía
500 de forma intermitente, con una ventana sostenida de ~40s de fallos observada en vivo
con navegación real (Chrome, pestañas Pipeline/Bots).

**Causa raíz**: `core-engine/Dockerfile` arrancaba `uvicorn` sin `--workers` → 1 solo
proceso, 1 solo event loop, sirviendo a la vez: (a) ingesta MT5 continua de BEPB+JJTI
(positions cada 5s, deals incremental, equity cada 30s, heartbeat cada 60s) y (b) toda la
API que consume la UI. Bajo ráfaga de peticiones concurrentes, el pool de conexiones DB
(20+20 por defecto, ver `core-engine/src/core/db/base.py`) se agotaba —
`sqlalchemy.exc.TimeoutError: QueuePool limit of size 20 overflow 20 reached` en el log
real de `core-engine` — dejando sesiones en Postgres en estado `idle in transaction`
durante 4-13s cada una (33 conexiones así en el momento de la captura). `api-gateway`
proxeaba fielmente y esperaba, recibiendo `httpx.ReadTimeout` sin ningún bug propio —
diagnóstico erróneo inicial (de esta misma sesión) apuntaba al gateway; corregido antes de
tocar código, con evidencia: un `curl` DIRECTO a `core-engine:8300` (sin pasar por el
gateway) reproducía la misma latencia de 46s para un simple 401.

**Riesgo estructural adicional encontrado de paso**: `core-engine`, `worker` y `scheduler`
comparten el mismo `Dockerfile`/imagen pero corren como 3 procesos independientes, cada
uno con su propio engine/pool SQLAlchemy. Con los defaults de código (20+20 cada uno), el
techo combinado posible era **120 conexiones** contra un Postgres con
**`max_connections=100`** — insuficiente incluso antes de este incidente, por pura suerte
de que los 3 procesos rara vez pican a la vez.

**Fix (commit `1590342`, StratOS-QXPro-v2; puntero de submódulo actualizado en
`SQX_144_Full2`)**:
- `core-engine/Dockerfile`: `CMD` de `uvicorn` con `--workers 4` — 4 procesos reales
  (paralelismo de verdad, no un solo núcleo sirviéndolo todo en serie).
- `docker-compose.operational.yml`: `DB_POOL_SIZE=5`/`DB_MAX_OVERFLOW=5` por proceso para
  `core-engine`, `worker` y `scheduler` (sin tocar `.env.operational`, que no se lee/edita
  por regla del proyecto) — techo combinado baja de 120 a **60** de 100, con margen real.
- `.env.example`: documentadas `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` (cero hardcoding, quedan
  declaradas con su default de código, 20+20, para uso de un solo proceso).
- Verificado ANTES de desplegar que `core/ws/bridge.py` reenvía WebSockets vía Redis
  Pub/Sub (8 topics), sin estado de conexión en memoria por proceso — pasar a 4 workers
  no rompe tiempo real.

**Verificación post-deploy (en vivo, no solo teoría)**:
- `docker logs core-engine`: 4 procesos arrancados (`Started server process [8/9/10/11]`
  + `Started parent process [1]`), ingesta `positions`/`heartbeat` fluyendo con 200 OK.
- `curl` directo a `core-engine:8300/api/v1/bots`: **46s → 7ms**.
- Postgres `pg_stat_activity`: **33 → 1** conexión `idle in transaction` (transitoria,
  normal).
- Smoke real en navegador (recarga `/login`): 0 errores 500, 0 timeouts, solo asset
  loads 200/304.

**Pendiente (no bloqueante, fuera de mi alcance sin credenciales)**: smoke test
AUTENTICADO — navegar las 10 pestañas ya logueado. No tengo ni debo usar las credenciales
reales del operador (cuentas Darwinex reales conectadas). El operador debería confirmar
con su propio login que la navegación completa va fluida ahora.

## G14 — alcance por cuenta: deuda y aplazados (2026-09-29)

Contexto: ADR 0013/0014, `docs/phase_status.md` G14. Lo que sigue queda fuera de la unidad o
depende de datos/decisiones externas.

- **Matriz teórica (backtest) de BEPB/JJTI vacía.** `baseline` tiene 0 filas para las cuentas
  1 y 2 y no hay trades de Strategy Tester en `import_artifact` para los 40 EAs reales.
  Hace falta importar los exports del Tester de esos EAs (¿dónde están? decisión del
  operador) y ejecutar `scripts/record_mt5_backtest_correlation_snapshot.py` por cuenta
  (ahora deriva la cuenta de los candidatos). Hasta entonces la UI declara "Sin evidencia
  de backtest sellada", no inventa.
- **Atribución de trades huérfanos.** 5.743 de 6.101 trades de JJTI y 6.912 de 7.394 de
  BEPB tienen `bot_id` NULL (magic heredado o 0): la matriz observada solo ve el ~6 %.
  `scripts/backfill_legacy_magic_attribution.py` existe; ejecutarlo toca datos reales
  (BD interna, no MT5) y quedó excluido por decisión del operador.
- **Correlación con 10 puntos es ruido.** Umbral bajado de 30 a 10 días u operaciones por
  petición expresa; los pares con <30 observaciones se marcan "baja confianza". Revisar si
  con más historia conviene volver a exigir más.
- **Publicación de eventos WS con `account_id`.** Ningún evento `events:*` lo lleva y
  `events:equity/trade/heartbeat/decision` no se publican nunca: la cabecera vive del
  polling de 5 s. Filtrar WS por cuenta queda pendiente de que existan publicadores.
- **Métricas duplicadas en Bots** ("Rolling vs Baseline" vs "Métricas completas": Sharpe,
  expectancy, DD). Se mantienen porque la captura las muestra así (ADR 0014 §7).
- **`equity_eur` de la cabecera suma equity crudo sin conversión FX** (documentado en
  `header.py`); con una sola cuenta seleccionada deja de mezclar divisas, pero la cifra sigue
  sin convertir si la cuenta no está en EUR.
- **`test_g8_acceptance_criteria.py` sigue usando escalera KS/UMS de portfolio (NULL)** en el
  seed; funcionan porque el seed usa el barrido heredado. Etiquetar los eventos del seed con
  cuenta queda pendiente si se quiere que el seed ejerza el camino por cuenta.
- ~~**Baselines Playwright linux**~~ **RESUELTO 2026-09-29**: renderizados por CI (artefacto
  `playwright-report` del run 36565739973) e instalados; CI 11/11 verde en el run 36566325460.
  Causa de la flakiness que apareció al regenerarlos: los screenshots se tomaban antes de que
  llegaran los datos bajo carga en paralelo; ahora todos esperan `networkidle`.
