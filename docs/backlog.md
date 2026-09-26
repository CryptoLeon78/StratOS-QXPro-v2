# Backlog — StratOS-QXPro

- **[G13-49] Cierre de F3 a F4 para las dos candidatas AUDCAD:** ya tienen `BACKTEST_VALIDATED` archivado y baseline enlazada; queda registrar por candidata el adjunto existente con su hash EX5, identidad de comentario y ruta reporter, y esperar un `ea_state` posterior al registro. No se reinstalan ni sustituyen los gráficos/magics 243 y 295 durante esta reconciliación.

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

- **[A38] El worker compite con el scheduler por los jobs de cron** — *corregido el
  diagnóstico 2026-09-26*. **Lo que escribí primero era falso**: dije que el kill-switch, el
  barrido de semáforos y el watchdog llevaban sin ejecutarse, leyendo sólo los logs del worker
  (`function 'cron:task_run_killswitch_sweep' not found`, cada minuto). Los logs del
  **scheduler** muestran lo contrario: `← cron:task_run_killswitch_sweep ●` cada minuto, en
  0,4-0,5 s. **Los barridos sí se ejecutan.** Lo real es que worker y scheduler comparten la
  cola ARQ por defecto: el worker ve encolados unos `cron:*` que no declara y los descarta con
  ese mensaje. Queda el riesgo de que el worker se adelante y un barrido concreto se pierda.
  Se resuelve dando al scheduler su propia `queue_name`.

- ~~**[A39] Tres accesos distintos y ninguno abría la aplicación**~~ **RESUELTO 2026-09-26**:
  `StratOS_Operacional.bat` (refresca admisión), `StratOS_Backtests.bat` (comparaciones) y
  `StratOS_Stack_Operacional.bat` (abría **Swagger**, `8300/docs`, que es herramienta de
  desarrollo). La aplicación real —el panel React con sus 11 pestañas— es **`localhost:5473`**, y
  no tenía acceso. Ahora `StratOS.bat` es el único: si el panel ya responde entra directo, y si
  no levanta el stack, espera a que sirva de verdad y lo abre. Los otros dos siguen en disco y
  sus accesos directos están recogidos en *"StratOS - otras herramientas"* del escritorio.

## Deuda de garantía — abierta desde la auditoría 2026-09-02

Detalle y comandos en [`AUDITORIA_2026-09-02.md`](AUDITORIA_2026-09-02.md). Nada de esto es un hueco
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
- **[A16] La importación del histórico está construida pero sin ejecutar** — la traducción de
  magics legacy, el sellado de la traducción en el artefacto y el informe de cobertura están
  probados (17 tests), pero `import_mt5_history_export.py --identity-registry` no se ha
  corrido todavía contra el stack operacional. Cobertura esperada: 10,3 % BEPB y 8,2 % JJTI.
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
- **[A13] Los `docs/registro_*_MN_*.md` se mantienen a mano y divergen del despliegue** —
  ninguno de sus 56 `comment_identity` coincide con los 40 `ASSIGNED` aprobados, porque
  registran el comment con el magic *legacy* mientras la propuesta asigna magics cortos. Los
  deals reales demuestran que lo desplegado usa los magics **nuevos**, así que son esos
  documentos los que están desactualizados. Regenerarlos desde el post-scan en vez de
  mantenerlos a mano.
- **[A14] `docs/history_deals_*.csv` viven en `docs/`** — son evidencia operativa, no
  documentación. Moverlos a `runtime/operational/history/` cuando la ingesta deje de leerlos
  de ahí; hoy están ignorados por Git en su ubicación actual.
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
- **[A34] El operador del stack operacional no puede iniciar sesión** — su fila en `user`
  guarda **13 caracteres en claro** donde va un hash Argon2 (verificado en la base:
  `hashed_password` no empieza por `$argon2`). `verify_password` llama a `Argon2.verify`, que
  lanza `InvalidHashError` con un texto plano y devuelve `False`: **ningún login puede
  funcionar**, y falla sin decir por qué. Es la causa real de que P4.2 (recorrido autenticado)
  siguiera pendiente. `bootstrap_operational_operator.py` ya rechaza el alta si el valor no es
  un hash Argon2 y da el comando para generarlo, pero **la fila existente hay que repararla**:
  eso exige tocar `.env.operational` y la base, y lo hace el operador. La credencial **nunca
  llegó al historial de git** (auditado: `.env.operational` jamás rastreado, el `.example`
  siempre con placeholders); sí se escribió por error en `.env.operational.example`, revertido
  antes de comitear.

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
- **[A30] Falta correr RETEST OOS y Walk-Forward Matrix en cinco proyectos** —
  *reformulado 2026-09-02 tras cerrar A32/A33*: con los dos bugs de emparejamiento fuera, el
  bloqueo restante es hueco de datos real en SQX, no código. **Un databank `WFM` con `.sqx`
  dentro no prueba que la matriz se corriera**: el `.sqx` de AUDCAD que sí funciona lleva 30
  corridas `Results/WF: N runs : X % OOS`; los de XAUUSD H1 y DAX40 SesionTarde sólo llevan
  `Results/Main`. Estado verificado por proyecto:

  | proyecto | retenidas | falta |
  | --- | --- | --- |
  | `XAUUSD_H1_Reemplazo2_KER_LinReg_noTP_EOD` | 99 | WFM (101 `.sqx`, **0 con matriz**) |
  | `Project_DAX40_M30_..._ORB_L_SesionManana` | 28 | RETEST OOS (0 `.sqx`) |
  | `Project_XAUUSD_H4_..._DiaEntero ( copia... )` | 22 | RETEST OOS **y** WFM (ambos a 0) |
  | `Project_DAX40_M30_..._v7_L_SesionTarde` | 14 | WFM (14 `.sqx`, **0 con matriz**) |
  | `Project_NASDAQ_H1_BS_Volumen_v7_L_Capa2` | 1 | WFM (0 `.sqx`) |
  | `XAUUSD_H1_Reemplazo1_ATR_LinReg Copia de Trabajo` | 1 | WFM (13 `.sqx`, **0 con matriz**) |

  Retener sin evidencia de robustez es lo correcto; no es un fallo del prefiltro. Hasta que se
  corran, la cola de validación la llena `AUDCAD/H4`, que es el único grupo con evidencia
  completa (232 de 397).
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

- **[A23] Los MCP de MT5 no conectan en esta sesión** — `mt5_bepb`, `mt5_jjti` y `mt5-darwinex`
  devuelven `ConnectionRefused`. Bloquea P2.3 (telemetría viva read-only en continuo), que
  necesita hablar con esos terminales. No es una capacidad ausente: es una conexión caída.

- **[A47] Admisión contractual de las tres observaciones externas de Incubadora** — `external_ea_inventory` ya conserva las identidades verificadas de `SPH4L_1.26.31_4.2.29_MN24`, `USDJPYH1L_2.22.171_MN13` y `USDJPYH1L_5.15.110_MN8`, pero ninguna tiene `OperationalAsset` validado, baseline ni `PipelineCandidate`. Implementar la ruta sellada `incubator_admission` de ADR 0012 y evaluar evidencia reproducible, plaza y correlación antes de crear cualquier F5; jamás inferirla del adjunto manual ni del nombre del archivo.

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
- **G13 incubadora:** la cuenta `BROKER_DEMO` ya existe. Tres EAs manualmente adjuntados (`SPH4L_1.26.31_4.2.29_MN24`, `USDJPYH1L_2.22.171_MN13`, `USDJPYH1L_5.15.110_MN8`) quedaron registrados como observaciones externas append-only, con ruta y SHA-256 `.ex5` contrastados en lectura y `bot_id=NULL`; no son `BACKTEST_VALIDATED`, baseline, bot ni F5. Ver `docs/g13_incubator_external_observations_2026-09-14.md`. La cola FIFO y el límite de 8 sólo pueden actuar después del gate de backtest/baseline y de la admisión sellada explícita por EA; el contrato demo será 10 % de capital, 0,2 % por trade y DD contractual 5 % durante la gracia explícita. Ver `docs/g13_closure_gate_matrix.md`.
- **G13 UI:** Bots, Pipeline y Cuentas/EA exponen procedencia y filtros de API. Faltan selectores/etiquetas consistentes para Portfolio, Salud, Riesgo, Auditoría y Dominical, más el recorrido autenticado/WebSocket que diferencie `BROKER_REAL`, `BROKER_DEMO`, `FIXTURE`, `DERIVED` y `ABSENT`.
- **G13 Pipeline, fidelidad de estructura:** superado por ADR 0012. Ya no se preserva el Kanban F1--F7 como objetivo de producto; la superficie de operación se limita a Incubadora y portfolios reales.
- **G13 Pipeline operacional (ADR 0012):** el operador ha retirado F1--F3 del producto visible. Sustituir la tarea anterior de fidelidad F1--F7 por un E2E de Incubadora → evaluación → propuesta humana de cartera, más telemetría read-only separada de BEPB/JJTI. Implementar `incubator_admission` como ledger sellado que acepte sólo identidad, perfil y evidencia explícita; no reutilizar las acciones F1/F2/F3 ni inferir admisiones desde HTML, nombres o carpetas.
- **G13 ejecución segura del histórico:** el terminal remoto JJTI tiene EAs reales en funcionamiento. No se debe usar `terminal64.exe /config` para lanzar un script de exportación sobre esa instancia hasta contar con un procedimiento que no abra/cierre ni cambie el perfil de la terminal activa; el CSV legado no se importa porque no cumple el contrato de deduplicación sellada.

- **G13-59 costes — autorización posterior y bloqueo probatorio:** el operador autorizó el 2026-09-24 una segunda corrida diagnóstica excepcional en copia aislada de `AUDCADH4L_ForexMinorLateral_Strategy 2.92.87`, fuera de cola/Incubadora. No se ejecutó porque no existe proyecto/databank duplicado recalculable para reexportar la List of Trades con ajustes y no se dispone de costes históricos Darwinex para el rango completo. No editar sólo `lastSettings.xml` ni calibrar contra el CSV del Tester: eso mezcla costes de una configuración con resultados de otra o introduce circularidad. Reanudar cuando haya copia reproducible y fuente histórica de comisiones/swaps; entonces una única corrida, veredicto de costes independiente, y sello sólo si el gate queda `PROVEN`.

- **[G13-61] Sensibilidad de tarifa vigente como gate alternativo — gate implementado; persistencia pendiente:** el operador autorizó aceptar el escenario tarifario vigente para `BACKTEST_VALIDATED`, pues refleja mejor las condiciones actuales. Implementado en `scripts/build_current_tariff_sensitivity.py` y `scripts/record_operational_backtest.py`: paquete derivado y sellado que enlaza corrida padre inmutable, snapshot oficial fechado, export real de deals y `REAL_TICKS`, sin reclamar equivalencia histórica SQX↔MT5. Paquete generado y dry-run `VALIDADA`: `runtime/operational/backtests_diagnostic/current_tariff_sensitivity_20260924_077d74f1cd98/run-manifest.json`; 245 tests scripts pasan. La escritura del evento no se completó: `stratos_operational` no existe en Postgres local; no se creó base, inventario, F3 ni admisión a Incubadora. Reanudar sólo cuando esté disponible el Postgres operacional y verificar el activo por hashes exactos.

## Estado activo G12

### Defectos a corregir

- ~~G12 Cuentas/EA: modo operativo, permiso por gráfico, sizing y panel de deriva.~~ **RESUELTO Y REPETIDO EN G12-02**: 11/11 `PAPER`/OFF/50 %, alerta de deriva de tres campos y cobertura de contrato documentadas.
- G12 procedencia de pestañas: Pipeline, Bots, Portfolio, Salud, Riesgo, Auditoría y Dominical mezclan fixture `full`, derivadas y telemetría demo sin una etiqueta/contrato de procedencia visible. Ver `docs/g12_tabs_provenance_validation.md`.
- G12 Pipeline: `USDJPYH1Lcity_5.15.110` tiene candidato F4 y bot F3. Requiere una transición append-only auditada; queda prohibida una edición directa.
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
- **`e2e-acceptance-full` roto: criterio 9 (Lyra×Phoenix redundante) — encontrado en G10-14, no resuelto**: `test_criterion_9_lyra_phoenix_redundante` falla de forma reproducible (`is_redundant_pair` da `False` en vez de `True`) desde después del checkpoint de pausa de G10 (backend), confirmado que el mismo job pasaba en el run de ese checkpoint (`53b5bef`, run `33121230739`) y que ningún commit del frontend de Salud/font-fix (G10-14) toca `services/correlations.py` ni `scripts/seed_lib/`. Ver `ASSUMPTIONS.md` G10-14 para el detalle y la hipótesis no verificada (ventana de fechas del perfil `full` relativa a `now`, el par está diseñado a propósito para quedar cerca del umbral). Decisión explícita del operador: documentar y seguir con el frontend, no investigar ahora.
- **Precios de seed no realistas en GDAXI/NDX/SPX500/US30** (encontrado en G10 al correr `backfill_r_multiple.py` contra Postgres real): varios trades sembrados de estos 4 índices tienen `open_price`/`sl` en una escala que no corresponde al price level real del instrumento (p.ej. `open_price=1.00000`/`sl=0.99000` para `US30`, que en realidad cotiza en el orden de 30.000-40.000) — probablemente `scripts/seed_lib/trades_history.py` generó el rango de SL sin tener en cuenta la escala de precio real de cada símbolo. Consecuencia real: `r_multiple` calculado sobre esos trades da magnitudes absurdas (hasta ~6,8x10⁴ en `US30`, miles en `GDAXI`/`NDX`/`SPX500`), lo que ya obligó a ampliar `RMultiple` de `NUMERIC(8,4)` a `NUMERIC(12,4)` (ver `column_types.py`) solo para poder escribirlo sin overflow — el valor en sí sigue sin ser interpretable como un R real hasta que el seed use precios realistas por símbolo. No se corrige aquí (fuera de alcance de G10, que no toca `scripts/seed.py`).

## G7 — huecos de negocio por pestaña (backend no calcula el dato, no es solo falta de exponerlo)

Decisión del operador antes de empezar G7 (ver `ASSUMPTIONS.md` G7-01): estos huecos se documentan y se omiten en la UI, no se inventan. Cada uno requeriría una fórmula/servicio/endpoint nuevo en core-engine — fuera de alcance de una fase de frontend.

- ~~**Portfolio**: sección "¿Añade valor real el portfolio?"~~ **RESUELTO en G10**: `services/benchmark.py` (nuevo) — `portfolio_monthly_returns()` (EquitySnapshot real) + `load_sp500_monthly()` + `compare_to_benchmark()` (CAGR/alfa/beta/t-stat/Information Ratio/Batting Average/Up-Down capture, reutiliza `ols_alpha_beta` de G2). `GET /portfolio/benchmark`. **Caveat heredado de G8** (`scripts/tests/test_sp500_benchmark.py`): el CSV solo tiene datos de mercado reales para 2021, el resto es sintético — comparar contra el seed real de este sistema puede dar una correlación espuria, no es un bug del cálculo (documentado en el propio docstring del servicio). **Wiring de frontend: RESUELTO en G10 (m-04)** — `PortfolioBenchmarkCard.tsx` consume el endpoint completo (8 celdas de métricas + badge de veredicto + chart de 2 líneas), incluido `monthly_points` (campo nuevo, la serie mensual alineada ya se calculaba internamente y se descartaba antes de esta unidad).
- ~~**Salud**: Sharpe rolling, Win Rate drift, Payoff, Duración media de trade~~ **RESUELTO en G10**: `formulas/trading.py::rolling_sharpe()` (nueva, refactor DRY sobre `pipeline_gate.py::_trade_sharpe`) + `win_rate_drift`/`payoff_ratio`/`avg_trade_duration` (ya en el grupo (b) de G10) — `services/semaphore_sweep.py::assemble_health_chips()` las ensambla, `HealthCard.tsx` las muestra en el mismo orden que la captura. **Bots** sigue con el mismo gap pendiente para su propia vista (ver más abajo, "panel Métricas completas").
- ~~**Bots**: panel "Métricas completas" (Sortino, Calmar, Ulcer Index, Recovery Factor, MCL)~~ **RESUELTO en G10**: `formulas/trading.py`/`formulas/portfolio.py` (Sortino, Calmar, Ulcer, RecoveryFactor, TDD 100%) + `services/bot_equity.py::bot_pnl_curve()` como base de curva por bot (base nominal 100, no es equity real por bot — ver su docstring); MCL ya existía (`loss_streak()`, G2). ~~"Posiciones abiertas" por bot~~ **RESUELTO en G10** (`GET /bots/{id}/open-positions`). ~~"Histograma de retornos (R)"~~ **RESUELTO en G10** (`Trade.r_multiple` poblado, ver entrada más arriba). ~~P&L acumulado por bot~~ **RESUELTO en G10** (`bot_pnl_curve()`). ~~"Contribución al portfolio" más allá de `capital_allocated_pct`~~ **RESUELTO en G10 (m-02a/m-02b)**: `compute_portfolio_contribution()` (`services/bot_equity.py`) — `pct_of_total_pnl`/`correlation_vs_rest`/`pnl_bot`/`pnl_account`, `GET /bots/{id}/metrics`. `BotDetail.tsx` consume todo el endpoint (Rolling vs Baseline de 7 filas, Métricas completas de 15 celdas, Contribución, Posiciones abiertas, Histograma de retornos R, P&L acumulado con selector de rango).
- ~~**Riesgo**: "Histórico" DD% ... de Monte Carlo~~ **RESUELTO en G10** (`GET /risk/montecarlo/history`; la fecha de firma, `ts`, ya estaba en `MonteCarloResponse` desde G5). ~~"Trades en ventana de noticias (30 días)" de News Shield~~ **RESUELTO en G10** (`services/news.py::trades_in_news_window()` + `GET /news/shield/trades`, cruza trades reales contra `NewsEvent` por `symbol_currency`). ~~MAX DD/DURACIÓN DD del panel de kill-switch~~ **RESUELTO en G10** (`services/killswitch_sweep.py::current_episode_stats()` + `KillSwitchStatusResponse.episode_max_dd_pct`/`episode_duration_seconds`). ~~subtotales por divisa de Exposición~~ **RESUELTO en G10** (ver entrada de `compute_exposure()` más arriba). **Wiring de frontend de los 4 cierres de arriba: RESUELTO en G10 (m-03)** — `KillSwitchPanel.tsx`/`ExposureCard.tsx`/`NewsShieldPanel.tsx`/`MonteCarloList.tsx` consumen los 4 endpoints/campos nuevos, verificado en vivo.
- **Pipeline**: tabla "Backtest vs Forward" (`CandidateResponse` no trae métricas de baseline/IS, solo las OOS actuales). **Verificado en G10 (docs/backlog.md), sigue sin resolverse**: `Baseline.source` ya distingue `BACKTEST`/`HISTORICO` en el esquema (campo con el shape correcto: profit_factor/expectancy_r/sharpe/max_dd_pct, mismo set que las métricas OOS de `PipelineCandidate`) — pero `grep` completo confirma que **ningún código del repo crea nunca una fila `Baseline`** (ni ingest, ni seed, ni servicio). No hay ningún endpoint `/ingest/*` para datos de backtest (los 7 de PARTE 9.1 son trades/positions/equity/heartbeat/signals/execution/ea_state, ninguno de baseline). Resolverlo de verdad exigiría un contrato de ingesta nuevo (como `tick_value`/`tick_size` para `r_multiple`) más parsear los exports de backtest de SQX (la plataforma de minado, sistema externo) — no hay una fuente ya disponible como `spread_sqx` para instrument_spec. Fuera de alcance de un endpoint aditivo.
- ~~**Escalado**: columnas Trades/Retorno/Max DD de "Evolución mensual"~~ **RESUELTO en G10**: `services/ums.py::monthly_evolution_metrics()` (trades cerrados reales + curva de equity real, TDD) se mezcla en `metrics` tanto en `confirm_advance` como en `check_automatic_downgrade`. Sin equity suficiente en la ventana, `retorno_pct`/`max_dd_pct` quedan en `None`, no se inventan. **Wiring de frontend: RESUELTO en G10 (m-05)** — `MonthlyEvolutionTable.tsx` añade las 3 columnas, `—` cuando la fila no trae el dato (filas que no corresponden a un evento de ascenso/bajada real).
- **Graveyard**: fecha de inicio del rango (solo existe `retired_at` en `CemeteryEntryResponse`) — ver `docs/adr/0006`. **Investigado en G10, sigue sin resolverse**: `PipelineCandidate.entered_phase_at` se sobrescribe en cada promoción de fase (no es histórico), así que para un bot ya archivado no representa su entrada a F1 — recuperarlo de verdad exigiría una tabla de histórico de transiciones de pipeline que no existe (a diferencia de `SemaphoreTransition`/`UmsPhaseLog`). No se inventa un sustituto (`Bot.created_at` fue descartado: no todos los bots pasan por F1-F7).
- ~~**Auditoría**: lista de "tramos sin envío" detallados~~ **RESUELTO en G10**: `compute_send_continuity()` ya calculaba `gaps` con detalle por tramo desde G5, solo faltaba exponerlo — `GET /audit/continuity-gaps` (no era una fórmula nueva, solo wiring). **Wiring de frontend: RESUELTO en G10 (m-06)** — `ContinuityCard.tsx` lista los tramos por cuenta (inicio → fin, duración), verificado en vivo.
- ~~**Cuentas/EA**: equity/balance/margen libre/margin level por cuenta~~ **RESUELTO en G10** (`AccountResponse` incluye el `EquitySnapshot` más reciente por `account_id`; `None` si la cuenta nunca reportó uno). **Wiring de frontend: RESUELTO en G10 (m-07)** — `AccountCard.tsx` muestra las 4 celdas (grid siempre presente, "—" por celda faltante — mismo criterio anti-desplazamiento que G9-06/G9-07), verificado en vivo con cuenta con snapshot parcial y cuenta sin snapshot. `ea_required_version` sigue sin resolver (no existe el concepto de "versión esperada" en ningún sitio del sistema — fuera de alcance de G10, ver Contexto del plan de la fase).
- **Ejecución/Cuentas-EA**: TCA y Perfil de broker — no es un hueco a resolver con una fórmula nueva, la propia captura documenta que depende de la v1.1 del EA reporter (fuera de alcance del conector actual, PARTE 9.1 "sin consumidor aún" para `/ingest/execution`).
