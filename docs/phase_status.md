# Estado de fase — StratOS-QXPro

> Se actualiza SIEMPRE al cerrar trabajo (regla de continuidad entre sesiones). Al abrir sesión, leer esto + `CLAUDE.md` + `ASSUMPTIONS.md` antes de proponer nada.

## Fase activa: G13 — Stack operacional real/incubadora/análisis — FUNDACIÓN IMPLEMENTADA; GATES EXTERNOS ABIERTOS

G13 crea `stratos_operational` como instalación local aislada de G12: volumen PostgreSQL distinto, puertos `57432/6580/8300/8380/5473`, `DEPLOYMENT_PROFILE=operational` y una guardia que rechaza `seed full` en ese perfil. El fichero local `.env.operational` y las rutas reales quedan fuera de Git; la única plantilla versionada es `.env.operational.example` y `config/operational_sources.example.yaml`.

- La retirada de G12 de la Incubadora quedó registrada en `runtime/operational/g12-incubator-retirement.json`: se detuvo sólo el terminal local cuya ruta fue comprobada y se retiraron exclusivamente `Experts\\StratOS_G12` y los dos perfiles `StratOS_G12_Demo_11Ready`; se conserva `MQL5\\Experts\\StratOS` y los includes genéricos. El manifiesto contiene hashes y fecha, no se versiona.
- El esquema incorpora procedencia persistente `BROKER_REAL|BROKER_DEMO|FIXTURE`, origen de bot `EXTERNAL_PRODUCTION|INCUBATION|ANALYSIS` e inventario append-only con `DISCOVERED` a `REJECTED`. Las APIs de Bots y Pipeline aceptan filtros por `account_id` y `data_origin`; sus respuestas y las tarjetas muestran procedencia. Los agregados restantes aún requieren su etiquetado visual y filtros equivalentes antes de un recorrido G13 autenticado.
- El catálogo local de Análisis genera manifiesto sellado sin mutar la base: 237 artefactos, 227 `STATIC_VALIDATED` y 10 `WITHHELD`. La validación requiere SQX144 parseable, MQL5, magic y coincidencia de símbolo/timeframe extraídos de ambos; esto no equivale a compilación ni a backtest.
- El extractor `scripts/extract_operational_validation_evidence.py` convierte la procedencia SQX resuelta en evidencia sellada sin arrancar SQX ni MT5: verifica de nuevo los hashes de Forward/RETEST OOS/WFM, registra cada pase SQX como `STATIC_VALIDATED_WFM` desde el artefacto WFM sellado y los criterios activos de su `project.cfx`, recalcula Monte Carlo bootstrap sobre los PnL OOS con `mc_sims=300`/`mc_seed=42` y extrae spread, comisión, slippage, swap y alcance de sesión del `lastSettings.xml` efectivo. La razón OOS/IS de la celda WFM se conserva como `DERIVED_UNMAPPED`, informativa/no bloqueante, pues no se ha demostrado su equivalencia con F2. La corrida corregida produjo 227/227 expedientes y WFM estáticos completos; todos declaran alcance `No Session` y todos conservan P95 sin ruina.
- El prefiltro `scripts/operational_prefilter.py` es el gate previo al Strategy Tester: aplica los mínimos existentes de `thresholds.seed.json`, excluye los hashes ya testeados y exige Monte Carlo P95 y costes por sesión sellados. F2/WFE sólo se aplica si la política se habilita tras registrar `VALIDATED_EQUIVALENCE`, `FORWARD_VALIDATED` o `MT5_COMPARISON_VALIDATED`; `DERIVED_UNMAPPED` nunca satisface ni bloquea ese gate. Después de que SQX reescribiera los 227 databanks se renovaron resolución, hashes y evidencia: 217 estrategias superan el prefiltro; cuatro hashes ya tienen Tester y seis no pasan PF/Sharpe. Por concentración `AUDCAD/H4`, la cola determinista expone sólo dos por tanda (`2.38.65` y `1.14.75`) y mantiene 215 en espera de diversidad; no inicia una incubación.
- El resolutor `scripts/resolve_operational_validation_sources.py` elimina rutas hardcodeadas por candidato: recorre el root local de proyectos que se indique, exige coincidencia SHA o firma histórica SQX (`orders.bin` + `lastSettings.xml`) y, ante copias como `PortfolioSeleccion`, sólo elige el proyecto cuyo nombre normalizado coincide con el linaje de la fuente Análisis. La primera corrida resolvió los 227 candidatos estáticos al proyecto S de AUDCAD H4 y selló sus artefactos `Forward`, `WFM`, `MC`, `MC2`, `RETEST OOS`, `TICK` y `TICK OPT`; las cinco fuentes L no forman parte de los 227 porque ya están retenidas estáticamente. La presencia de esos databanks no equivale todavía a veredicto WFE/MC/costes.
- El exportador `StratOSHistoryExport` se ejecutó manualmente en ambas sesiones reales, sin APIs de trading. Los CSV recuperados por SSH read-only quedaron sellados como `cedc0cb8174c…` (JJTI) y `3804c3ea5ff6…` (BEPB); su importación canónica aceptó 2.041 y 2.486 trades completos respectivamente, y una repetición aceptó 0/0 con 2.041/2.486 duplicados. Se retuvieron 5/15 posiciones no simples. Los magics históricos fuera del rango compacto del inventario se preservan como `BIGINT` y permanecen huérfanos auditables (`bot_id=NULL`), sin asociación heurística.
- JJTI (`4000059903`) y BEPB (`4000055216`) son cuentas `BROKER_REAL` Darwinex Live/USD y permanecen sin cambios en MT5. Los dos `Detallado_*` legados siguen archivados como evidencia no importable. Los HTML de historial entregados por el operador se sellaron como `MT5_HISTORY_HTML` y aportaron 1.945 trades JJTI y 2.359 BEPB, todos huérfanos (`bot_id=NULL`, magic reservado 0 con ausencia declarada) porque el reporte no publica magic. Se retuvieron 88 y 117 posiciones respectivamente al no tener una salida única reconciliable. La referencia temporal está sellada como Darwinex/SQX `EETUS` -> IANA `Europe/Helsinki`. Los 40 bots F7 externos ya registrados son observacionales: conservan `profile`, capital y riesgo como ausencia declarada y no afirman promoción por gates internos.
- Los registros comprobados por el operador se sellaron como dos artefactos `MT5_EA_MAGIC_RECORD`; un barrido SSH de sólo lectura añadió 26 filas BEPB y 14 JJTI a `external_ea_inventory`, con comentario, magic, cuenta, ruta `.ex5` y SHA-256. Dieciséis quedan retenidas: trece por binarios distintos con igual versión, una sin versión contrastable y dos BEPB por colisión interna `magic=10827`. Esta evidencia permite preparar backtests por EA confirmado, pero no reasigna el histórico HTML anterior que carece de magic.
- La gracia de incubación sólo espera `mode=REAL`, permiso de EA y sizing `10 %`/riesgo `0,2 %` hasta `incubation_grace_until`; al expirar vuelve el semáforo normal. La capacidad máxima sigue fijada en 8 y ningún EA de Análisis ha sido adjuntado ni puede abrir operaciones todavía.
- `dist\StratOS_Operational.exe` ya proporciona el punto de entrada guiado: arranca/comprueba el stack, resella inventario/evidencia/prefiltro y pide `SI` antes de cada Strategy Tester. Cada resultado se registra append-only; el ejecutable termina con Incubadora bloqueada hasta implementar el adjunto demo por gráfico y registrar una cuenta `BROKER_DEMO`. El binario y `--refresh-only` se verificaron sin abrir MT5.

**Gates pendientes antes de operaciones demo:** el histórico CSV sellado ya está importado y reconciliado idempotentemente. Faltan candidatas de Análisis `BACKTEST_VALIDATED`, su veredicto/baseline aplicable y la integración demo de adjuntar/observar hasta ocho EAs; sólo entonces podrá consumirse la cola FIFO. JJTI/BEPB siguen observabilidad estrictamente read-only; StratOS nunca envía órdenes a cuentas reales.

**G13 cola local y símbolo:** `StratOS_Operational` publica una vista sellada de la cola FIFO local y un JSONL append-only de cada presentación, confirmación, omisión, fallo o sellado. Pipeline la monta sólo lectura: el navegador nunca ejecuta MT5. Cada Tester exige `SI` individual en el lanzador. `SQX_vs_MT5` además bloquea por API cualquier símbolo MT5 distinto del declarado por SQX hasta recibir confirmación explícita; analizar/cancelar no memoriza aliases.

### G13-01 — arranque aislado y catálogo de análisis — OPERATIVO, SIN FIXTURE

- El operador creó `.env.operational` localmente; se validó el Compose sin leer ni mostrar sus valores. El proyecto `stratos_operational` está activo con volumen, red y puertos propios. PostgreSQL y Redis están healthy; core (`8300`), gateway (`8380`) y frontend (`5473`) responden HTTP 200; worker y scheduler ARQ están conectados.
- La imagen de `core-engine` incorpora ahora `alembic.ini` y las revisiones, de modo que la migración se puede reproducir dentro del contenedor. La base nueva quedó en `b0a1c2d3e4f5` y contiene las tablas de admisión operacional.
- La prueba controlada de `scripts/seed.py --profile ci` abortó antes de escribir por la guardia `DEPLOYMENT_PROFILE=operational`; la comprobación posterior confirma 0 cuentas y 0 trades. El bootstrap creó el operador desde el email/hash locales sin revelarlos ni rotar una cuenta existente.
- El escaneo de `Analisis` se ejecutó desde un montaje read-only y persistió 237 eventos: 227 `STATIC_VALIDATED` y 10 `WITHHELD`. No crea bots, cuentas, baselines ni adjuntos demo.
- JJTI/BEPB siguen accesibles por SSH en modo lectura. JJTI contiene un exportador CSV legado, pero su formato no es el contrato sellado actual y sólo presenta cabecera. Ejecutar automáticamente un script MQL5 requeriría iniciar/cerrar la instancia real, por lo que permanece bloqueado hasta disponer de una instancia/exportación que no altere el terminal de producción.
- El operador autorizó el terminal Darwinex seleccionado por `SQX_vs_MT5` exclusivamente como Strategy Tester: conserva AutoTrading desactivado y el lanzador operacional sólo consulta `terminal_backtest`, nunca `terminal_despliegue`. `scripts/run_operational_sqx_mt5_backtest.py` exige autorización explícita por corrida, identidad exacta de terminal, ticks reales continuos desde 2018 y fuentes SQX/MQL5 explícitas. `--manage-backtest-terminal` solicita el cierre limpio sólo de esa instancia si quedó abierta, sin matar procesos ni tocar BEPB/JJTI. Dos variantes AUDCAD H4 completaron el Tester con evidencia sellada y ambas recibieron `DISCREPANTE`, persistidas append-only como `WITHHELD`; no entran en cola ni Incubadora. El lote no puede conservar MT5 abierto con la vía `/config`, pues MT5 no inicia el siguiente Tester sobre una instancia viva.
- La primera tanda resultante del prefiltro ejecutó otros dos AUDCAD H4 sobre ticks reales 2018-actual: `1.14.75_wfm720` quedó `DISCREPANTE` (NP 12,86 %, PF 11,44 % y trades 5,79 % fuera de los límites del comparador) y `4.25.70_wfm520` quedó `TOLERABLE` (NP/PF/DD dentro de umbral, pero trades 6,69 % frente a un límite 5 %). Ambos manifiestos e informes HTML/TXT se verificaron por SHA-256 y se persistieron append-only como `WITHHELD`; `TOLERABLE` no equivale a `BACKTEST_VALIDATED`, por lo que no hay bot, baseline ni gráfico de Incubadora creado.

**G13-15 — Alta F7 externa idempotente:** `register_external_f7_manifest.py` lee exclusivamente los dos manifiestos sellados de inventario y admite sólo `MATCHED_UNIQUE_VERSION` o `MATCHED_EQUIVALENT_EX5_COPIES`. Exige coincidencia exacta con una observación previa de cuenta, magic, comentario, símbolo, timeframe, ruta y hash; los 16 `WITHHELD` quedan fuera. La aplicación autorizada creó 40 bots `EXTERNAL_PRODUCTION` en F7, sus candidatos y transiciones append-only, y una nueva observación de inventario enlazada a cada `bot_id`; no se actualizó el inventario anterior ni se reasignaron los trades HTML huérfanos. Los campos internos `profile`, capital y riesgo permanecen como ausencia declarada. La repetición registró 0 altas y 40 existentes; ambos resultados se sellaron bajo `runtime/operational/external_inventory/`. No se contactó ni modificó MT5.

**G13-16 — Cola F7 de comparación real/OOS:** `run_live_backtest_queue.py` limita cada ejecución al Strategy Tester autorizado, exige manifiesto F7 sellado y `--max-runs` positivo, y sólo acepta las identidades verificadas de los 40 externos. Los estados `COMPLETED` y `WITHHELD_TICKS` son terminales incluso en registros heredados sin campo `status`; los errores restantes se reintentan. El cálculo estático actual deja 35 comparaciones tick-real pendientes; no se lanzó MT5 durante esta actualización.

**G13-17 — Preflight y arranque controlado de F7:** el preflight de los 35 pares no abre ni cierra MT5. Ocho expedientes tienen fuente y ticks completos; 25 quedan `WITHHELD_TICKS` (alias o cobertura Darwinex insuficiente) y dos `WITHHELD_SOURCE` porque el `.sqx` carece de operaciones binarias y exige CSV SQX explícito. La ejecución de la cola se restringe a identidades `PREFLIGHT_OK`. Un primer intento fue rechazado antes del Tester porque la instancia configurada no aceptó cierre limpio; no se forzó el proceso. Tras el cierre confirmado por el operador, la corrida F7 BEPB `magic=120726` terminó con veredicto `DISCREPANTE`. Sus artefactos y manifiesto se verificaron por hash y se registraron append-only como `asset_id=238`, `WITHHELD`; no se creó baseline ni promoción.

**Pausa de comparaciones F7 — 2026-08-31:** tras completar y sellar JJTI `DAX40M30stat_2.13.18` (`magic=10826`, `asset_id=242`, `DISCREPANTE`), el operador detiene expresamente nuevos lanzamientos de MT5. Actualizará los retests SQX al mismo intervalo temporal usado por el Tester Darwinex. Hasta una confirmación explícita de que esas fuentes SQX están actualizadas, la cola permanece en espera: no se lanza, reintenta ni promueve ninguna comparación; JJTI/BEPB continúan estrictamente read-only.

**Identidad compacta de magics/comments — COMPLETADA EN LECTURA:** la migración mantiene comments MT5 de hasta 30 caracteres y magics cortos no reutilizables. La identidad aprobada usa `<label>_MN<nuevo_magic>` y el nombre de archivo operativo es exactamente el mismo comment. La aprobación explícita del hash `318e99792860a513e531bf5c716c52b19d4fac0d3f7594b8343ef05c8df7be7f` registró 40 `ASSIGNED` y 40 `MIGRATION_PLANNED` en la cadena append-only local; una repetición produjo 0 eventos. Tras guardar los perfiles `Default`, el post-scan read-only observa los 40 pares aprobados cuenta+magic como identidades lógicas únicas y registra el NQ/JJTI magic `38` como excepción retenida por decisión del operador. Las copias `.chr` que comparten ID raíz MT5 se colapsan sólo si su identidad coincide completamente; cualquier desacuerdo queda retenido. Para perfiles MT5 sólo se aceptan las dos codificaciones exactas observadas de `CustomComment` (`.` o `_`); no hay una normalización libre. La política conserva aliases explícitos `DAX|DAX40` F7/SQX → `GDAXI` Darwinex MT5. Bajo la confirmación del operador de que sólo cambian archivo/magic/comment, hash EX5 y timeframe se heredan del F7 sellado; los demás campos se releen del perfil. StratOS no cambió ningún EA, gráfico, cuenta, Forja, histórico ni MT5. Esta evidencia no abre ni altera los gates F7/demostración.

**G13-21 — Cola F7 alineada a retests SQX:** los retests SQX renovados se comprobaron como `precision=TICK`/`testPrecision=4`, con ventana común `2018-01-01`–`2026-08-28`. Las rutas antiguas de cola quedaron obsoletas por el renombrado MN; `refresh_live_backtest_queue_sources.py` reconstruye una nueva cola sellada mediante la asignación MN aprobada, conserva el magic actualmente desplegado para F7 y exige la ventana exacta del SQX. Resultado: 13 fuentes resueltas, 6 `PREFLIGHT_OK` y 7 `WITHHELD_TICKS` por alias/cobertura Darwinex. El primer lanzamiento de la campaña renovada no generó artefacto ni evento mientras la instancia Darwinex ya estaba abierta; no se forzó ni terminó ese proceso. Tras el cierre confirmado por el operador, la primera comparación renovada `XAU1H1BUYSTP_3.10.66_MN28` sobre `XAUUSD/H1`, modelo tick real (`Model=4`) y ventana `2018-01-01`–`2026-08-28`, terminó `VALIDADA`: NP 3,05 %, PF 1,34 %, DD 14,40 % y 0 % de diferencia en trades, dentro de sus umbrales. Sus informes y hashes se registraron append-only como `asset_id=243`, que permanece `WITHHELD` por tratarse de un F7 externo: no se creó baseline ni promoción. La segunda comparación, `XAUH1BUYSTOPeof_1.8.81_MN1`, terminó `TOLERABLE`: NP 1,46 %, PF 0,15 % y trades 1,34 % dentro de umbral; DD 16,45 % excede el 15 %. Se selló como `asset_id=244`, `WITHHELD`, sin diagnóstico individual ni promoción. La tercera comparación, `EURJPYM15L_1.29.59_MN9`, terminó `DISCREPANTE`: NP 23,56 % y PF 10,43 % superan el 10 %; DD 1,45 % y trades 1,79 % se mantuvieron dentro de límites. Se selló como `asset_id=245`, `WITHHELD`, sin promoción. La cuarta, `USDJPYH1L_5.15.110_MN8`, terminó `DISCREPANTE`: NP 16,99 % y DD 36,37 % exceden los umbrales; PF 1,15 % y trades 0,43 % quedan dentro. Se selló como `asset_id=246`, `WITHHELD`. A petición del operador, no se inicia otra corrida automática: quedan dos expedientes `PREFLIGHT_OK` para lanzamiento manual y posterior sellado por StratOS (`USDJPYH1Lcity_3.16.113` y `USDJPYH1Lcity_2.22.171`). **Veredictos supersedidos por G13-25 (2026-09-01):** bajo el contrato direccional, `XAUH1BUYSTOPeof_1.8.81_MN1` pasa de `TOLERABLE` a `VALIDADA` y `USDJPYH1L_5.15.110_MN8` de `DISCREPANTE` a `TOLERABLE`; `XAU1H1BUYSTP_3.10.66_MN28` sigue `VALIDADA` y `EURJPYM15L_1.29.59_MN9` sigue `DISCREPANTE`. Los cuatro siguen `WITHHELD` por ser F7 externos: ningún cambio de veredicto crea baseline ni promoción.

**G13-25 — Contrato direccional SQX↔MT5** (renumerado 2026-09-02: `G13-24` ya estaba ocupado en `ASSUMPTIONS.md` por las serializaciones duplicadas de perfiles MT5; la decisión completa vive ahora en `ASSUMPTIONS.md` G13-25)**:** por decisión explícita del operador, el comparador deja de tratar rendimiento y riesgo como discrepancias simétricas. Sus límites viven en `sqx_mt5_panel.json`: para NP/PF, caída adversa 10 % y alza favorable 35 %; para DD, aumento adverso 15 % y reducción favorable 35 %; trades mantiene ±20 %. Los informes expresan variación con signo y margen aplicado. `reclassify_external_f7_backtests.py` verificó los manifiestos originales y sus hashes sin relanzar MT5, y selló `runtime/operational/backtests_live/directional_reclassification_20260901.json`: 11 corridas evaluadas, tres cambios de veredicto. Los eventos previos permanecen inmutables; esta evidencia es una reclasificación contractual, no una promoción automática ni una operación real.

**Post-scan G13 — perfiles persistidos, verificación estricta:** el 2026-09-01 se releyeron los perfiles `Default` remotos de JJTI/BEPB sin arrancar MT5, después de su guardado manual. El informe `runtime/operational/magic_identity/post_migration_scan_report.json` registra 40 `MIGRATION_OBSERVED`, uno por cada par aprobado cuenta+magic; el NQ/JJTI magic `38` se conserva bajo `OPERATOR_RETAINED_OUT_OF_PROPOSAL` en un manifiesto sellado separado. Las copias JJTI `chart17`/`chart19` (magic `30`) y `chart18`/`chart20` (magic `19`) son serializaciones físicas del mismo ID raíz de gráfico MT5 y se contabilizan una sola vez; no son EAs ni identidades duplicadas. Sólo se colapsan si EA, magic, comment y símbolo coinciden; un desacuerdo para el mismo ID queda `MIGRATION_UNVERIFIED`. Se aceptan exclusivamente las dos codificaciones exactas comprobadas de `CustomComment`: puntos configurados o guiones bajos persistidos. Los aliases de símbolo conservan literal y auditadamente `DAX`/`DAX40` F7-SQX junto a `GDAXI` Darwinex MT5. La propuesta F7 sellada aporta hash EX5/timeframe porque el operador confirmó una migración exclusiva de archivo/magic/comment; cuenta, gráfico, archivo, magic, comment y símbolo se contrastan de nuevo desde el perfil.

## Auditoría de estado y cierre de deuda — 2026-09-02 — GARANTÍAS RECUPERADAS

Auditoría independiente tras el trabajo en paralelo con Codex, y ejecución de los bloques
P0-P2 del plan que salió de ella. Informe completo con comandos de reproducción en
[`docs/AUDITORIA_2026-09-02.md`](AUDITORIA_2026-09-02.md); orden de trabajo y decisiones
pendientes en [`docs/PLAN_CONTINUACION_2026-09-02.md`](PLAN_CONTINUACION_2026-09-02.md).

### Lo que estaba roto y ya no

| | Antes | Ahora |
|---|---|---|
| Historial | último commit en G10, **194 ficheros sólo en el working tree** | 15 commits temáticos, **pusheados a `origin/main`** |
| `ruff` / `format` | 7 errores, 8 ficheros | limpio, 210 formateados |
| `mypy --strict` | 7 errores en 3 ficheros | Success, 108 ficheros |
| `pytest core-engine` | 598 + 1 fallo | **600 passed** |
| `pytest scripts` | 120 + 1 fallo | **150 passed** |
| `SQX_vs_MT5_Panel` | 8 tests | **21 passed** |
| `dist/StratOS_Operational.exe` | 23 scripts por detrás | **0**, arranque verificado |

Dos fugas del `.gitignore` corregidas antes del push: `.env.operational.example` estaba
ignorado pese a declararse la única plantilla versionada, y `docs/history_deals_*.csv`
—9.082 deals de cuentas reales— se habrían commiteado.

### Deuda cerrada

- **Reclasificación direccional persistida** (G13-25): 2 eventos append-only en
  `operational_asset_event`, idempotente. La verdad contractual ya no vive sólo en un JSON.
- **Extracción de símbolo corregida**: la causa raíz del `alias_simbolos` contaminado era que
  **27 de 73 `.sqx` traen el nombre de la estrategia en el campo `symbol` de la cabecera
  binaria**. Ahora manda `lastSettings.xml` y los 73 resuelven sin ningún alias parche.
- **Salvaguarda de símbolo extendida al lote** (G13-26), con una corrección de criterio: la
  comparación era sobre símbolos crudos y saltaba en 3 de 3 estrategias por el sufijo
  `_darwinex`. Una alerta que salta siempre entrena a confirmar por costumbre.
- **`scan_hardcoding` consolidado** (G13-28): 5 literales migrados a constante, el resto
  clasificado por categoría. El único que era un umbral real se corrigió en G13-29.
- **Tope de validación separado del de admisión** (G13-29): la cola pasa de **2 a 24** y las
  193 restantes esperan por presupuesto de CPU, no por diversidad. El tope de portfolio queda
  declarado y anotado, no aplicado, hasta que exista admisión a Incubadora.
- **Atribución del histórico** (G13-27): traducción de magics anteriores a la migración desde
  los `legacy_magic_numbers` del registro aprobado, sellada en el artefacto de importación, y
  un informe que mide la cobertura antes de importar.

### Lo que la auditoría descubrió y sigue abierto

1. **El histórico exportado no llega a 2018**, sino a `2025-02-03` (BEPB) y `2025-03-20`
   (JJTI). El caché de deals del terminal guarda ~19 meses. La documentación que prometía
   2018 queda corregida; la decisión sobre el tramo anterior es del operador.
2. **La migración MN está aplicada casi por completo, no del todo**: medido sobre los deals
   del 1-2 de septiembre, 14 por cuenta llevan magic nuevo pero **dos EAs siguen emitiendo su
   legacy** (`2004262` en BEPB, `2084` en JJTI) y tres magics desplegados no pertenecen al
   lote aprobado de 40 (`9519`, `90727`, `0`).
3. **Una comparación completada no está registrada**: `20260830T210536Z_91538465c20a` tiene
   evidencia sellada en disco y ningún evento en la base (`backlog A15`).
4. **El 87-90 % del histórico es de EAs ya retirados** (`backlog A17`). La traducción de
   magics triplica la cobertura y aun así deja huérfana la mayoría. No es un fallo: es la
   rotación real del portfolio, y conviene tenerlo medido antes de prometer métricas por bot
   sobre el histórico completo.
5. **Los `docs/registro_*_MN_*.md` se mantienen a mano y divergen del despliegue** — registran
   el comment con el magic legacy mientras la propuesta aprobada asigna magics cortos, y los
   deals demuestran que lo desplegado usa los nuevos (`backlog A13`).

## Fase actual: G12 — Validación operativa por pestaña y demo SQX — BASE DEMO OPERATIVA; G12-02 CONTRACTUAL CONFORME, OPERACIONES BLOQUEADAS POR NARANJA

G12 mantiene G11 íntegramente reproducible y levanta el proyecto Docker aislado `stratos_g12`: PostgreSQL `56432`, Redis `6480`, core `8200`, gateway `8280` y frontend `5373`. La migración y el seed `full` se aplicaron sólo a ese proyecto; core, gateway y frontend responden HTTP 200.

### Recorrido G12-03..07 / G12-09..12 — BLOQUEADO POR PROCEDENCIA MEZCLADA

- El recorrido read-only confirma telemetría real de MetaQuotes Demo G12 (11 bots, 471 snapshots, 271 heartbeats) y ausencia honesta de 0 trades/0 fills. También confirma que el fixture `full` sigue presente (50 bots `Prod`, 15.810 trades) y que varias superficies agregan ambos universos sin un marcador visual o contrato de procedencia.
- Hallazgos concretos: una candidata G12 tiene `PipelineCandidate=F4` mientras su `Bot=F3`; Portfolio/Riesgo/Auditoría muestran agregados fixture/globales como si fueran de la misma superficie; el benchmark falla en el contenedor por CSV inaccesible; Salud lista 43 filas mezcladas y sus chips no muestran valores. Escalado está conforme como ausencia (`None`/historial vacío) y Graveyard es histórico fixture, no evidencia demo.
- No se modifican datos ni estados durante el recorrido. Falta sesión UI autenticada y el MCP `stratos` no está expuesto en esta sesión, por lo que no se declara screenshot-diff ni scan de hardcoding. Matriz y gates en `docs/g12_tabs_provenance_validation.md`.

### G12-00 — arranque e inventario demo — RECONCILIADO; CIERRE DE UI/WS PENDIENTE

- El manifiesto de los 16 supervivientes `MANTENER` se construye desde artefactos locales y exige SQX144 parseable, fuente MQL5 recuperable, SHA-256, magic explícito y coincidencia exacta de símbolo/timeframe Darwinex contra el contenido SQX. Resultado actual: 11 `READY` y 5 `WITHHELD`, sin sustituciones automáticas.
- Retenidos: `DAX40H1stat_5.29.24` (magic duplicado), `WF Matrix - Strategy 3.43.69` (no aparecen artefactos exactos), y tres SQX cuyo contenido no permite verificar el backtest SQX144 de forma cerrada. Las causas quedan en `runtime/g12/survivors-manifest.json`; este artefacto operativo no se versiona.
- Se creó una copia de seguridad acotada de las rutas que G12 puede modificar en el terminal demo, se compilaron once copias instrumentadas bajo `MQL5\\Experts\\StratOS_G12` y se adjuntaron al perfil aislado `StratOS_G12_Demo_11Ready`. El perfil contiene 11 gráficos con los símbolos MT5 explícitos `DE40`, `EURGBP`, `US500` y `USDJPY`; sólo cubre los 11 `READY`.
- El alta administrativa se ejecutó con la excepción autorizada `--allow-withheld`: creó una cuenta DEMO, 11 bots F3, 11 baselines append-only y sus transiciones. Los valores persistidos son `capital_allocated_pct=10`, `risk_per_trade_pct=0.2` y `dd_contract_pct=5`; los cinco `WITHHELD` permanecen fuera del perfil y de la cuenta.
- No se invocan herramientas de trading ni se toca el VPS/una cuenta real. El conector continúa read-only.
- La regresión de aceptación sobre el seed `full` de G12 está verde: `e2e-acceptance-full` local 9/9. La suite altera casos de prueba y el perfil `full` se resembró inmediatamente después dentro de `stratos_g12`.
- `scan_hardcoding` del MCP `stratos` no detecta hallazgos en los seis módulos G12 nuevos/modificados de preparación, alta e instrumentación.
- El build G12 muestra el badge `DEMO LOCAL · G12` en la cabecera. Es una configuración de build aislada; no cambia el comportamiento del build ordinario ni simula telemetría.
- La ruta de login se comprobó con navegador real y se guardó una captura local de evidencia ignorada por Git. Se creó el usuario operador exclusivo de G12 para el correo indicado por el operador y se verificó `POST /api/auth/token` a través del frontend (200, token presente). El operador confirmó el acceso visual. La contraseña se entregó una sola vez fuera del repositorio; no se guarda en `.env.g12`, documentación ni logs. El frontend directo de G12 ahora proxifica `/api` y `/ws` al gateway, conservando el mismo contrato que el nginx de entrada y sin acceso directo a core-engine.
- **Ingesta real de base**: el conector read-only está activo con buffer SQLite G12 y patrón exclusivo `stratos_g12_*.jsonl`. Se han sellado y aceptado 11 estados `ea_state`; no hay magics G12 ausentes ni huérfanos y los sellos de los lotes comprobados son válidos. Heartbeat, equity y posiciones continúan llegando desde MT5 demo. Esta evidencia no equivale a fills ni a TCA: el mercado cerrado y la ausencia de ejecución real mantienen G12-08 abierto.
- **Hallazgo G12-01 (operador)**: Resumen conserva el fixture `full` para probar la superficie y sus cifras no se presentan como telemetría demo. No se ajustan cifras a mano ni se infiere telemetría.
- El login y proxy `/api` fueron comprobados. Falta la comprobación autenticada de rutas directas, WebSocket y alertas durante el recorrido por pestañas; por eso G12-00 no se declara cerrado por completo.

### G12-02 — Cuentas/EA — CONTRATO CORREGIDO Y REPETIDO; SIN ARMAR OPERACIONES

- Los 11 EAs reportan la versión requerida `g12-reporter-v1.1`, el filtro horario y las ventanas de noticias; su asociación `(cuenta, magic)` es completa y sin huérfanos.
- La repetición confirma 11/11 `PAPER`, `autotrading=false` y `sizing_pct=50.00`, conformes con 11 bots `NARANJA` y `sizing_current_pct=50.00`. Los gráficos contienen 11/11 `expertmode=0`; el perfil previo se conserva como backup antes de aplicar la corrección.
- Los ocho indicadores custom `Sq*` requeridos se compilaron y se reinició el perfil. El arranque posterior de los once EAs no reproduce los errores MT5 `4802` que impedían resolver indicadores.
- `config_drift` ahora compara modo, permiso AutoTrading y sizing, con alerta CRITICA si cualquiera diverge. El job real se ejecutó sin alerta abierta porque el contrato está conforme. Cuentas/EA expone los tres campos más filtro, noticias y último estado reportado; no fabrica señal/trade cuando aún no hay fills.
- El barrido de semáforos respeta `baseline_grace_days=5` antes de evaluar una baseline recién creada. Es una corrección prospectiva: no reescribe las transiciones append-only existentes. Hasta una transición de semáforo válida, `NARANJA` exige `PAPER` y prohíbe abrir operaciones demo.

El checklist y el informe de contraste están en `docs/g12_validation_checklist.md` y `docs/g12_cuentas_ea_contract_validation.md`. No se toca el VPS ni ninguna cuenta real; el conector permanece read-only.

## G11 — coherencia documental y cierre de pendientes reales — CERRADA EN CÓDIGO; GATE DEMO OPERATIVO BLOQUEADO

G10 quedó cerrada tras el grupo (o): PHASE REPORT completo en `ASSUMPTIONS.md` G10-16 y `scan_hardcoding` consolidado limpio. G11 se abrió con autorización del operador para resolver los pendientes registrados, sin habilitar trading automático. El orden de ejecución es: (a) documentación/gobierno; (b) determinismo de seed, criterio 9 y auditoría TimescaleDB; (c) importación local trazable de `.sqx` y FX; (d) histórico de pipeline; (e) reporter v1.1/TCA; (f) validación demo. Los `.sqx` locales ya están disponibles en databanks y se usan como evidencia de parser; el acceso VPS/MT5 sigue siendo un gate demo y no se sustituye por datos inventados.

### G11-a — coherencia documental y gobierno — COMPLETO FUNCIONAL; scan con deuda histórica clasificada

- Se actualizan solo los textos que describen el estado presente: README, arquitectura, runbook y cabecera de fase.
- Las entradas históricas de G0–G10 en `ASSUMPTIONS.md` se preservan; una nota posterior deja constancia del cierre efectivo de G10.
- `docs/backlog.md` conserva la evidencia anterior y clasifica el trabajo abierto como defecto, capacidad bloqueada por datos o decisión deliberada.
- El MCP `stratos` queda registrado globalmente y el servidor responde; la sesión abierta requiere reinicio para exponerlo como tool nativa. Se ejecutó `scan_hardcoding` mediante el servidor: 67 hallazgos en `services` y 13 en `mt5-connector`, deuda previa de configuración/constantes de protocolo que no se debe ocultar. G11 no declara un scan limpio global sin la migración explícita de esos umbrales.

### G11-b — integridad de fixtures y agregados TimescaleDB — COMPLETO

- El perfil `full` usa un final histórico fijo y los precios sintéticos pasan a depender del símbolo; regresiones puras cubren ambas propiedades.
- Se sustituyeron únicamente los agregados sobre `Trade` que pueden observar el caso de hypertable sin chunks por lecturas que aceptan la ausencia de fila y devuelven el neutro correcto.
- Se verificó contra el proyecto Docker aislado `stratos_g11_test`: migración aplicada, seed `full` de 15.810 trades/65 bots y `e2e-acceptance-full` local 9/9 verde. Lyra×Phoenix mide 0,5316 y queda marcada redundante. No se tocó el volumen existente de desarrollo.

### G11-c — importación administrativa y procedencia — COMPLETO

- `import_sqx_baseline.py` exige `--bot-id`, valida SQX144 fail-closed y guarda bytes, SHA-256, procedencia y metadatos antes de crear una baseline append-only.
- `import_fx_csv.py` sólo acepta la cabecera fechada `ts,base,quote,rate`; no hay rutas HTTP de escritura ni proveedores externos.
- Se validó el parser con el artefacto local `Strategy 7.74.64.sqx` (SQX Build 144.2938). Pipeline expone Backtest-vs-Forward con fecha/procedencia y la UI muestra explícitamente la ausencia de baseline. Tests aislados cubren parser SQX144 y CSV FX (idempotencia/conflicto).

### G11-d — historial de pipeline — COMPLETO (backend)

- `PipelinePhaseTransition` registra desde G11 altas F1, promociones manuales y KILL con actor, motivo y fecha; no se fabrican fechas anteriores.
- El detalle se expone como historial de candidato. Cementerio sigue bloqueando reactivación y no modifica los registros históricos.

### G11-e — reporter EA v1.1, fills y TCA — COMPLETO EN CÓDIGO Y COMPILACIÓN

- `mt5-connector/mql5/StratosReporter_v11.mqh` sólo escribe telemetría JSONL; no contiene APIs de envío de órdenes. El conector lo lee, lo deduplica atómicamente en SQLite y lo envía por su buffer existente. `execution_fill` es append-only/idempotente y conserva tanto fills como rechazos, sin precio ejecutado inventado. `GET /execution/tca` sólo muestra TCA, perfil de broker y rechazos cuando existe telemetría.
- `ea_required_version` se configura en el registro administrativo. `NULL` significa no verificable, nunca conforme; Cuentas/EA muestra el resultado de la comparación únicamente cuando hay requisito y snapshot.
- El smoke EA dedicado del terminal demo compila con MetaEditor sin errores ni avisos. Es sólo de telemetría y no se adjuntó a ningún EA de incubadora.

### G11-f — VPS/MT5 demo — CONECTIVIDAD READ-ONLY VERIFICADA; GATE OPERATIVO EXTERNO BLOQUEADO

- El MCP del MT5 demo local autentica y responde a `initialize`. El bridge SSH ya existente hacia Contabo autentica contra los dos terminales reales (JJTI y BEPB); sus MCP internos responden a `initialize`, `get_workspace_info`, `get_time_information` y `get_trading_account_info` exclusivamente por una allowlist de lectura.
- El MCP nativo de MT5 también anuncia herramientas de escritura y trading. StratOS no las invocó: no se habilitó AutoTrading, no se modificaron EAs de incubadora y no se enviaron órdenes. Sólo se creó y compiló el smoke EA aislado.
- `tester_run_backtest` del MCP demo devuelve `ok=false, run_id=0` antes de iniciar; por tanto no hay outbox, ingesta, WS ni TCA que se pueda certificar honestamente. Se requiere que el operador deje operativo el Strategy Tester/permita una ejecución local del smoke antes de un ciclo completo. El VPS real queda excluido de pruebas de reporter y de cualquier despliegue.

## G10 — Cierre de huecos de negocio (docs/backlog.md) — CERRADA

G0-G9 (PARTE 12, plan original) están cerradas — ver más abajo. G10 es trabajo nuevo, fuera de ese plan, iniciado a petición del operador para abordar el backlog de huecos de negocio acumulado en G4-G9 (plan aprobado, `~/.claude/plans/immutable-bouncing-cascade.md`).

**Backend cerrado (grupos a-l), CI verde 9/9 en cada checkpoint, último run [`33120563244`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33120563244)**. ~13 commits, todos TDD-first donde aplica (rojo confirmado antes de implementar), verificados contra Postgres/Redis reales:
- (a) Esquema: `Account.login` UNIQUE · `instrument_spec` (real desde SQX vía `spread_sqx`) · `symbol_currency`.
- (b) 7 fórmulas nuevas (Sortino/Calmar/Ulcer/RecoveryFactor/WinRateDrift/Payoff/AvgTradeDuration), 100% cobertura.
- (c) `services/bot_equity.py` — curva de P&L por bot + posiciones abiertas.
- (d) `Trade.r_multiple` — backfill real (15.944 trades) + wiring en ingest. Overflow real de columna corregido (`NUMERIC(8,4)→(12,4)`, hypertable comprimida).
- (e) `services/fx.py` — conversión real a EUR de exposición (sin FxRate poblado todavía, servicio funcional y probado).
- (f) `services/news.py` — News Shield retrospectivo (trades en ventana de noticias).
- (g) 5 endpoints aditivos (posiciones abiertas, MC histórico, episodio kill-switch, equity/balance de cuenta). "Graveyard fecha de inicio" investigado y confirmado irresoluble sin tabla de histórico nueva.
- (h) `services/ums.py` — evolución mensual real (trades/retorno/max DD).
- (i) `GET /audit/continuity-gaps` — tramos sin envío detallados.
- (j) `services/benchmark.py` — Portfolio vs S&P500 (CAGR/alfa/beta/IR/Batting/Capture).
- (k) Pipeline Backtest vs Forward — investigado, gap real confirmado (sin ingest de backtest, fuera de alcance).
- (l) `EaState.sizing_pct` + deriva de sizing — backend a spec, no verificado contra EA real.

**Detalle completo de las 14 decisiones/hallazgos en `ASSUMPTIONS.md` G10-00 a G10-13.**

**(m) frontend — EN CURSO** (reanudado tras el checkpoint de pausa, a petición explícita del operador "Continua con el frontend"):
- **Salud** (`ec0fc31`) — hecha, verificada en CI real.
- **Bots** (`f2d8d2f` backend + `b5bf044` loss_streak_baseline + `6e49f9c` frontend) — hecha, verificada en vivo (bot con baseline y bot sin trades) y en CI real. 2 bugs reales encontrados y arreglados via verificación en vivo: timestamps duplicados en `BotPnlChart.tsx` (lightweight-charts exige orden estrictamente ascendente) y `compute_portfolio_contribution()` crasheaba con 500 para cualquier bot sin trades (agregado SQL sin GROUP BY sobre el hypertable `trade` de TimescaleDB devuelve 0 filas en vez de la fila que garantiza el estándar SQL). Ver `ASSUMPTIONS.md` G10-15.
- **Hallazgo mayor de infraestructura E2E, resuelto** (`4f41df4`/`2bf52d3`/`1971978`, ver `ASSUMPTIONS.md` G10-14): `e2e-playwright` estaba roto de forma sistémica (fuente `Inter` no auto-hospedada, resuelta entre máquinas efímeras del runner de forma inconsistente — no era un baseline desactualizado por el trabajo de Salud) + 2 bugs de máscara reales (`headerMask()` sin el badge STALE, `resumen.spec.ts` con máscara duplicada sin el equity-chart cubierto). **`e2e-playwright` verde 12/12 en CI real**, confirmado de nuevo en el run del commit de Bots ([`33144135903`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33144135903)).
- **Hallazgo separado, documentado, NO resuelto (decisión explícita del operador)**: `e2e-acceptance-full` roto (criterio 9, Lyra×Phoenix redundante, perfil `full`) — confirmado pre-existente a G10-14, no relacionado con el trabajo de frontend, sigue rojo en cada run desde entonces. Ver `ASSUMPTIONS.md` G10-14 y `docs/backlog.md`.
- **Tarea aparte flageada, no bloqueante**: auditar los otros 14 usos de `.scalar_one()` en core-engine por el mismo riesgo de hypertable-sin-chunks (ver `ASSUMPTIONS.md` G10-15).
- **Riesgo** (`7c4c415`, m-03) — hecha, verificada en CI real (`e2e-playwright` verde, run [`33144739367`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33144739367)) y en vivo. 4 gaps de G10 cerrados en frontend (backend ya construido en grupos (g)/(c) antes del checkpoint de pausa): `KillSwitchPanel.tsx` (MAX DD/DURACIÓN DD del episodio), `ExposureCard.tsx` (subtotales por divisa, nativa no EUR), `NewsShieldPanel.tsx` (trades en ventana de noticias agrupado por bot), `MonteCarloList.tsx` (histórico de runs + fecha de firma del contrato).
- **Portfolio** (`1fc1351`, m-04) — hecha, verificada en CI real (`e2e-playwright` verde, run [`33146440551`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33146440551)) y en vivo. Último gap de G10 para esta pestaña: sección "¿Añade valor real el portfolio?" (`PortfolioBenchmarkCard.tsx`, 8 métricas + badge de veredicto + chart de 2 líneas). TDD real: `compare_to_benchmark()` calculaba la serie mensual alineada internamente pero la descartaba — nuevo campo `monthly_points` (test rojo confirmado antes de implementar).
- **Escalado** (`25415a9`, m-05) — hecha, verificada en CI real (`e2e-playwright` verde, run [`33146884718`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33146884718)) y en vivo (estados vacíos correctos, sin `UmsPhaseLog` sembrado en el dev DB local). `MonthlyEvolutionTable.tsx` añade Trades/Retorno/Max DD (backend ya construido en grupo (h)).
- **Graveyard** — revisado, SIN gap de G10 pendiente (fecha de inicio ya investigada y confirmada irresoluble en el checkpoint de pausa, ver `docs/adr/0006`; el resto ya estaba completo desde G7). No requirió commit.
- **Auditoría** (`1bdc6f5`, m-06) — hecha, verificada en CI real (`e2e-playwright` verde, run [`33147293299`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33147293299)) y en vivo. `ContinuityCard.tsx` lista los tramos sin envío detallados por cuenta (backend ya construido en grupo (i)).
- **Cuentas/EA** (`1544fc2` + `5016275` baseline, m-07) — hecha, verificada en CI real (`e2e-playwright` verde, run [`33148244916`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33148244916)) y en vivo (cuenta con snapshot parcial + cuenta sin snapshot). `AccountCard.tsx` añade el grid de 4 celdas Equity/Balance/Margen libre/Margin level (backend ya construido en grupo (g)) — grid siempre presente, "—" por celda faltante (mismo criterio anti-desplazamiento que G9-06/G9-07). Baseline `cuentas_ea.png` regenerado (cambio de altura real de la tarjeta, no flake).

**(m) COMPLETO — las 7 pestañas regulares del plan cerradas y verificadas en CI real** (Salud/Bots/Riesgo/Portfolio/Escalado/Graveyard[sin gap]/Auditoría/Cuentas-EA).

**(n) COMPLETO — Vista `/dominical`** (`7376513`), aprobada explícitamente por el operador antes de construirla, verificada en CI real (`e2e-playwright` verde, run [`33149603328`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33149603328)) y en vivo. Ruta de nivel superior (NO en `RootLayout`, NO en `TabBar`), punto de entrada: enlace discreto en `AppHeader`. Backend nuevo `GET /alerts` (TDD, gap real: `Alert(module="config_drift")` nunca se listaba). Reusa `HeartbeatCard`/`WatchdogTable` (desconexiones) y `NewsShieldPanel` con `hours=168` (noticias semana entrante, ahora prop configurable). "Órdenes rechazadas" documentado pendiente (v1.1 EA reporter). Criterio literal PARTE 16 #14 verificado con test de contenido real (`vista_dominical.spec.ts`): EQUITY/P&L DÍA/DRAWDOWN nunca aparecen.

**(o) Cierre — COMPLETO**: `scan_hardcoding` consolidado sobre todo el repo ejecutado, ficheros tocados por G10 verificados uno a uno (constantes con nombre+comentario de origen o docstring, cero hallazgos nuevos sin justificar). `docs/backlog.md` y `ASSUMPTIONS.md` (G10-00 a G10-16) al día. PHASE REPORT completo en `ASSUMPTIONS.md` G10-16 (5 secciones: archivos, tests, criterios de salida uno a uno, entradas nuevas, screenshot-diff).

**Fuera de alcance de G10, dejado explícitamente sin resolver, con razón documentada** (no bloquea el cierre): `ea_required_version` (Cuentas/EA), "Backtest vs Forward" del pipeline, "Graveyard fecha de inicio", precios de seed no realistas en GDAXI/NDX/SPX500/US30, `e2e-acceptance-full` criterio 9 (Lyra×Phoenix). Ver `docs/backlog.md` para el detalle de cada uno.

## Fases cerradas (G0-G9, PARTE 12, plan original)

### G9 — Hardening (cerrada, CI verde 9/9)

**Estado**: 29 commits, pusheados en 9 tandas (una por checkpoint de grupos relacionados, más 4 rondas extra de diagnóstico/fix cuando `e2e-playwright` volvió a romper tras el push del grupo (j) por un motivo no relacionado con el código de G9 — ver hallazgos 6-8 abajo), cada tanda confirmada con CI real antes de continuar a la siguiente — mismo estándar que G8. Todos los grupos previstos en el plan (a-j) completos. **Última confirmación, definitiva: CI verde 9/9 real con el workflow en su forma normal (sin ningún paso temporal), run [`33105823894`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33105823894)**.

**Los 3 items que el backlog de G4-G8 ya había prometido "para G9-hardening" están resueltos**: `api-gateway/` real (proxy transparente + rate-limit + WS broker, deja de ser el placeholder de G0) · revocación de JWT vía denylist Redis (rotación de refresh + `POST /auth/logout`) · code-splitting del bundle de frontend (1.007kB→329kB, sin aviso de Rollup). Más la línea literal de G9: backups `pg_dump`+WAL (verificados de verdad contra Postgres real) · rotación de API keys (documentación, ya soportado desde G4) · playbook de alertas · `config/small_scale.yaml` · `docs/runbook.md` completo · ADRs cerrados (0007 nuevo, primero de arquitectura).

**8 bugs reales encontrados y corregidos, todos verificados contra infraestructura real (no simulados)**:
1. WS broker del gateway no propagaba el código de cierre real de core-engine (1008 con token inválido) — el cliente veía siempre el 1000 genérico.
2. `pydantic-settings` sin declarar en `api-gateway/pyproject.toml` — pasaba en el venv compartido del repo, rompía en CI (instalación aislada) y en un venv aislado real que se usó para reproducirlo antes de repushear.
3. `pg_restore` ignora 6 FK constraints sobre hypertables comprimidas de TimescaleDB (`trade`/`equity_snapshot`/`heartbeat_log`) — los datos restauran al 100%, esas FK se reaplican a mano (SQL exacto en el runbook); el script ahora lo señala explícito en vez de quedar "verde" en silencio.
4. `frontend/Dockerfile` nunca fijaba `VITE_API_BASE_URL`/`VITE_WS_BASE_URL` en tiempo de build — la imagen de producción arrancaba con los defaults de desarrollo (`http://localhost:8100`) horneados en el JS, rotos para cualquier visitante real.
5. El nginx interno del contenedor `frontend` no tenía `try_files $uri /index.html` — cualquier ruta de React Router navegada directa devolvía 404. (Los bugs 4/5 solo salieron a la luz al levantar `docker compose --profile prod up` de punta a punta con un navegador real por primera vez desde que existen los Dockerfiles — G8-13 solo había verificado que los builds compilaban, nunca el runtime del bundle servido.)
6. `scripts/seed.py::bulk_insert_heartbeats` anclaba el último heartbeat al `now` del INICIO del script completo, no al momento real de inserción — reducía pero no eliminaba una carrera de tiempo real (ver 7).
7. **`AppHeader.tsx`/`AccountCard.tsx` montaban/desmontaban el badge "DATOS STALE" y el bloque heartbeat/latencia/uptime según el estado en vivo** (no el seed) — cuando cualquiera cambiaba de presente→ausente entre la captura del baseline de Playwright y la corrida del test, la página entera se desplazaba verticalmente. Confirmado con evidencia directa (no solo teoría): un intento de regenerar los 11 baselines vía CI dio los 11 ficheros byte-idénticos a los ya commiteados — esa corrida coincidió por pura casualidad. Rompió `e2e-playwright` real 2 veces, incluida una vez sobre un push puramente de documentación.
8. **Fix de raíz de (7), a petición explícita del operador tras el 2º fallo real**: los 2 componentes ahora reservan SIEMPRE su altura (`invisible` en vez de ausentes). **Determinismo probado con tiempo real transcurrido**: mismo baseline, antes y después de esperar 130+ segundos reales cruzando a propósito el umbral de 120s que antes causaba el fallo — sigue pasando. Confirmado además en Linux CI real tras el fix (run `33105823894`, workflow normal, sin trucos).

**1 desviación de arquitectura documentada formalmente**: PROMPT_MAESTRO PARTE 3 especifica que `api-gateway`↔`core-engine` debería usar un "token de servicio" propio; se construyó y verificó un proxy pass-through más simple (reenvía el JWT del usuario intacto, sin `JWT_SECRET` en el gateway) — decisión confirmada con el operador, documentada en `docs/adr/0007-gateway-sin-token-de-servicio.md` (primer ADR de arquitectura del proyecto, los 6 anteriores eran de fidelidad visual).

**Verificado end-to-end de verdad, con navegador real, contra la topología de producción completa** (`docker compose --profile prod build/up`: core-engine+worker+scheduler+api-gateway+frontend+nginx+postgres+redis, los 4 servicios con Dockerfile propio construidos de cero): login real por `http://localhost/` → dashboard Resumen completo con datos reales → navegación directa a `/portfolio` sin 404 → WS a través de nginx con un cliente real → consola sin errores. Además: backup/restore de Postgres real (4.6MB, recuentos de filas confirmados) y todo el flujo HTTP/WS del gateway verificado contra `core-engine` real antes de tocar Docker.

**Caveats reales, no ocultados**:
- Instalación de los 2 nodos (Windows+MT5/Linux+certbot) escrita a spec en `docs/runbook.md`, **no ejecutada contra infraestructura real** en ninguna sesión (mismo patrón que `install_service.ps1` desde G4) — ni un VPS real, ni un terminal MT5 real, ni un dominio real han existido en este proyecto.
- `config/small_scale.yaml` es un documento de referencia sin efecto en el sistema (decisión ya tomada con el operador, no wireado en runtime).
- Coste de UX aceptado explícitamente por el fix de (8): el badge "DATOS STALE" y la línea de heartbeat de una cuenta ahora reservan siempre su espacio (invisible cuando no aplican) — un hueco vacío mínimo en vez de un layout que se re-acomoda. No se ha visto ninguna captura de referencia que lo prohíba.

Detalle completo (9 decisiones/hallazgos numerados) en `ASSUMPTIONS.md` G9-00 a G9-07.

### G8 — Seed + E2E (cerrada, CI verde 9/9)

**Estado**: 21 commits, pusheado y confirmado con **3 runs reales de GitHub Actions** tras el push inicial (no solo verificación local). El primer push (`4f7cbf5`+`c3da7d0`..) destapó 3 bugs reales que la verificación local no había visto — los 3 corregidos y confirmados con CI verde 9/9 en el run [`33078966721`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33078966721):
1. **`test-backend` rompía** (9 fallos, `relation "bot" does not exist`) — `test_g8_acceptance_criteria.py` se conecta directo a `stratos` sin migrar en ese job; local llevaba la BBDD ya migrada toda la sesión, el runner limpio lo destapó. Fix: `--ignore` en `test-backend` (G8-14).
2. **`e2e-playwright` sin baselines `-linux.png`** — los 11 capturados en esta sesión son `-win32.png` (Windows), el runner es `ubuntu-latest`. Generados vía el propio CI real (`--update-snapshots` temporal + `upload-artifact`, 2 pushes, `gh run download`, revertido) — un intento previo de replicarlo con Docker local (`host.docker.internal`) conectaba pero el login nunca renderizaba, causa no diagnosticada, abandonado por no ser el entorno real (G8-15).
3. **2 bugs reales en los specs de Playwright**, enmascarados hasta entonces por el fallo de snapshot en TODOS los tests: `flujo_operativo.spec.ts` apuntaba a "Hipnos" (solo dispara `Alert`, nunca `Decision`) en vez de "Poseidón" (sí genera `Decision` confirmable vía el sweep real); `portfolio.spec.ts` asertaba la calibración de correlación a ~0,16 que solo aplica bajo `--profile full`, pero el job siembra `--profile ci` (G8-15).

**Los 17 criterios de aceptación de PARTE 16 están verificados**: `scripts/seed.py` completo y auto-verificado (`--profile full|ci`, `--inject-audit-error`) · 9 tests de aceptación (`test_g8_acceptance_criteria.py`, 9/9 verde en CI real, perfil `full`) · 11 specs de Playwright (12 tests, 12/12 verde en CI real, perfil `ci`) · 2 jobs de CI nuevos (`e2e-playwright`/`e2e-acceptance-full`) · `docker compose up` + seed timado de verdad (~101s, <10min).

**9 bugs reales en total encontrados y corregidos en esta fase** (6 en verificación local + 3 solo visibles en CI real — ver arriba): `Trade.r_multiple` nunca poblado disparaba AMARILLO en los 32 bots de producción (G8-07) · `_already_seeded()` nunca escribía su propia marca de idempotencia (G8-08) · CORS bloqueaba el harness E2E completo (G8-11) · 3 bugs en los Dockerfiles de `core-engine`/`frontend` (G8-13) · los 3 de CI real de arriba (G8-14/G8-15).

**Hallazgo real documentado, no corregido** (G8-07): 28/32 bots de producción caen en AMARILLO en el sweep de semáforo — desajuste real entre la calibración de `semaphore_sweep.py` y los 5,5 años densos que exige el seed. No bloquea ningún criterio; fuera de alcance sin autorización del operador.

**"Vista dominical" (criterio 14) confirmada ausente como superficie de UI** — mismo tratamiento que la UI de checklist: construirla es frontend nuevo, fuera de "Seed + E2E". Entrada en `docs/backlog.md`.

Detalle completo (15 decisiones/hallazgos) en `ASSUMPTIONS.md` G8-00 a G8-15.

### G7 — Frontend pestañas 2–11 (cerrada, CI verde 7/7)

Las 10 pestañas (Portfolio, Salud, Riesgo, Bots, Pipeline, Ejecución, Escalado, Graveyard, Auditoría, Cuentas/EA) tienen contenido real, cada una verificada en vivo contra `core-engine` real con datos de prueba sembrados vía scripts desechables (nunca commiteados). Prerequisito: nuevo router `core/routers/config.py` (solo lectura, expone la escalera Kill-Switch, las 6 fases UMS, los umbrales del gate y las instrucciones de semáforo — ninguno tenía endpoint antes de G7).

**6 ADRs** (`docs/adr/0001`-`0006`, primeros del proyecto) documentan desviaciones de fidelidad visual respecto a las capturas: fusión GRID/SCALPING en Portfolio, PH booleano en Salud, "Historial de semáforo" en vez de "del pipeline" en Bots, 7 criterios reales del gate (no Sortino/Asymmetry del mockup) en Pipeline, botones reales en vez de "Mover a…" en Pipeline, sin fecha de inicio en Graveyard.

**Huecos de negocio reales, documentados y omitidos (no inventados)**: decisión explícita del operador antes de empezar la fase (ver ASSUMPTIONS G7-01) de mantener G7 estrictamente frontend — el grupo más grande de huecos cae en Bots (Métricas completas Sortino/Calmar/Ulcer/Recovery Factor, posiciones abiertas, histograma de retornos, P&L acumulado por bot), seguido de Riesgo/Portfolio/Escalado/Auditoría/Cuentas-EA con huecos puntuales. Lista completa por pestaña en `docs/backlog.md`.

**48 tests de Vitest** (24 nuevos sobre los de G6) + **447 tests de pytest** de core-engine (sin regresión), `tsc --noEmit`/`npx eslint .`/`npx vite build` limpios en cada commit. `scan_hardcoding` sobre `frontend/src/` limpio o justificado (100 hallazgos nuevos, mismas 4 categorías de precedente de G6-02 + 1 constante matemática de interpolación de color sin categoría de negocio — ver ASSUMPTIONS G7-09).

**Caveats reales, no ocultados**:
- Bundle de producción sube a ~1 MB (311 kB gzip) con `recharts` añadido para Portfolio — code-splitting sigue siendo tarea de G9.
- Screenshot-diff automatizado de las 10 pestañas nuevas queda para G8 (mismo patrón que G6: el spec mínimo de Playwright no está wireado en CI todavía) — la verificación visual de G7 fue manual en vivo, no automatizada.

CI verde run [`33048222928`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33048222928) — los 7 jobs.

Detalle completo (11 decisiones/hallazgos) en `ASSUMPTIONS.md` G7-00 a G7-11.

### G6 — Frontend shell + pestaña Resumen (cerrada, CI verde 7/7)
Stack de PARTE 4 instalado sobre el scaffold de G0: Tailwind v3 (theme generado 1:1 desde `design_tokens.json`) · shadcn/ui vendorizado y adaptado a tokens (8 componentes: button/card/badge/collapsible/input/label/form/dialog) · TanStack Query + Zustand + react-router-dom v7 (Data Router) · React Hook Form + Zod · Lightweight Charts v5 (equity) · Vitest+RTL+MSW + ESLint 10 + Playwright. Router de 11 pestañas + `/login` (solo Resumen con contenido real, las otras 10 placeholders navegables para G7). Login JWT completo (RHF+Zod, `authStore` con persist, `api/client.ts` con refresh-on-401 deduplicado). `AppHeader` con las 6 StatCard reales + WS (`/ws/equity`+`/ws/alerts`, reconexión con backoff, fallback a polling 5s ya existente). Pestaña Resumen completa: card de equity + selector de rango + panel "Requiere acción" (DecisionCard+PostponeDialog+mutations) + panel Pipeline (contadores F1-F7 + novedades).

**24 tests de Vitest + 1 de Playwright (verificado localmente 3 veces, no en CI todavía), 0 errores/0 warnings de ESLint, `scan_hardcoding` limpio o justificado** (~40 hallazgos nuevos, todos en 5 categorías con precedente ya establecido — ver ASSUMPTIONS G6-02). Criterios de salida literales cumplidos: cabecera <2s (asegurado con aserción dura de Playwright + medido en vivo), screenshot-diff de Resumen dentro de umbral (`maxDiffPixelRatio=0.02`, nuevo, sin cifra contractual — a confirmar por el operador, G6-03). `npx tsc --noEmit` y `npx vite build` limpios en cada commit.

**Todo verificado end-to-end contra `core-engine` real en el navegador de este entorno** (no solo mocks): login real, refresh-on-401 disparado de verdad por un token expirado durante la sesión, WS conectando (`[accepted]`/`connection open` en el log del servidor), mutations de decisiones (confirm/postpone) contra la API real con persistencia confirmada en Postgres.

**Caveats reales, no ocultados**:
- Playwright (`tests/e2e/resumen.spec.ts`) **no está wireado en CI** — el job `lint-and-build-frontend` no levanta Postgres/Redis/core-engine; verificado solo localmente (3 corridas deterministas). Wireado completo es tarea de G8 ("Seed + E2E").
- Bundle de producción >500 kB (aviso de Rollup, `lightweight-charts` es el mayor contribuyente) — code-splitting es tarea de G9.
- Un icono pequeño no perteneciente a la app aparece en la esquina de la baseline de Playwright — confirmado que no es del DOM, consistente con un artefacto de renderizado por software del Chrome for Testing headless de este entorno (ASSUMPTIONS G6-04), dentro de tolerancia.
CI verde run [`33039521500`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33039521500) — los 7 jobs, incluido el `lint-and-build-frontend` ampliado con Lint (ESLint) + Unit tests (Vitest) además del build que ya tenía.

Detalle completo (15 decisiones de diseño, `scan_hardcoding` categorizado, artefactos de test) en `ASSUMPTIONS.md` G6-00 a G6-04.

### G5 — Servicios, jobs ARQ, API 9.2, WS, Telegram, Prometheus (cerrada, CI verde 7/7)
Auth JWT completo (login/refresh/401 sin token) · 14 servicios de dominio (`watchdog`, `correlations`, `montecarlo`, `risk`, `audit`, `impulses`, `ums`, `withdrawals`, `checklists`, `config_drift`, `staging`/SIZING_CAP, `pipeline_gate`, `semaphore_sweep`, `killswitch_sweep`) · ARQ (10 cron jobs, `tasks.py`+`worker.py`+`scheduler.py`) · API 9.2 (16 routers) · WS (4 endpoints) · Telegram + Prometheus. **440 tests, 98% cobertura agregada** (3624 statements) — único caveat real: `ws/router.py` mide 53-74% pese a que sus 4 endpoints SÍ se ejercitan (`tests/ws/test_router.py`), déficit de instrumentación de `coverage.py` con TestClient basado en hilos, no código sin probar. Criterios de salida literales cumplidos uno a uno (auth, validaciones, 409 cementerio, SIZING_CAP, deriva EA, posición sin SL+Telegram<60s — este último un hueco real cerrado en el cierre de fase). OpenAPI sin warnings (`tests/test_openapi.py`) · `scan_hardcoding` limpio o justificado (207 hallazgos, 2 reales corregidos) · `ruff`/`mypy --strict` limpios.

CI verde run [`33018969105`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/33018969105) — pero el primer push (run `33018551295`) SÍ falló de verdad: `RuntimeError: Form data requires "python-multipart" to be installed` (`auth/router.py::POST /token` usa `OAuth2PasswordRequestForm`, resuelto por FastAPI en runtime). El paquete estaba instalado en el venv local de forma incidental, nunca declarado en `pyproject.toml` — 440/440 pasaban en local sin que nadie lo notara, el runner limpio de GitHub lo destapó. Corregido (commit `7c45c6f`), reproducido y verificado en local antes de repushear.

Pendiente para más adelante (no bloquea G6): investigar el déficit de cobertura de `ws/router.py` si algún día hace falta un número real · 5 gaps de negocio en `docs/backlog.md` (chips de Salud sin fórmula, `r_multiple` nunca poblado, sin equity/Sharpe por bot, `ea_state` sin sizing, exposición sin conversión de divisa) · `ums_max_dd_gate_pct=8` aún sin confirmar por el operador. Detalle completo en `ASSUMPTIONS.md` G5-00 a G5-14.

### G4 — mt5-connector + mt5-simulador + ingesta real (cerrada)
5 paquetes nuevos/tocados, 299 tests, 100% en 3 de ellos (`core-engine/ingest/` 213 statements, `shared-ingest-seal` 17, `mt5-simulator` 97) · `mt5-connector` 94% (371 statements, 100% salvo `real_adapter.py`/`main.py`, no verificables sin Windows+MT5 real) · criterio de salida (corte de red, cero pérdidas/duplicados) probado contra Postgres real. CI: run [`32986481038`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/32986481038) falló por congestión de runners de GitHub (jobs nunca llegaron a `queued`→ejecutar), no por el código — nunca se confirmó CI verde para G4 antes de que G5 empezara. Detalle en `ASSUMPTIONS.md` G4-01 a G4-21.

### G3 — Máquinas de estado (cerrada)
3 máquinas de estado (semáforo/kill-switch/pipeline+challenger), 100% cobertura (357/357 statements, 66/66 tests), CI verde 3/3 (run [`32956020786`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/32956020786)). Detalle en `ASSUMPTIONS.md` G3-01 a G3-06.

### G2 — Fórmulas (cerrada)
20 fórmulas de PARTE 8, 100% cobertura (217/217 statements, 87/87 tests), CI verde 3/3 (run [`32939959347`](https://github.com/CryptoLeon78/StratOS-QXPro-v2/actions/runs/32939959347)). Detalle en `ASSUMPTIONS.md` G2-01 a G2-07.

### G1 — Modelo de datos (cerrada)
25/25 tablas de PARTE 5.2, migraciones Alembic 0001/0002, rol `stratos_app` con grants exactos, 16/16 tests contra Postgres/TimescaleDB real. Detalle en `ASSUMPTIONS.md` G1-01 a G1-14 y el historial de commits.

### G0 — Scaffold + tooling de gobierno (cerrada)
Repo git independiente en `https://github.com/CryptoLeon78/StratOS-QXPro-v2` (privado), `.mcp.json` operativo, `docker compose up -d postgres redis` healthy, CI verde, `config/thresholds.seed.json` (61 claves), scaffolds de `core-engine`/`api-gateway`/`frontend`. Detalle en `ASSUMPTIONS.md` G0-01 a G0-14.

## Fases futuras (PARTE 12)

Ninguna dentro de PARTE 12 — G0 a G9 era el plan original completo, ya cerrado. G10 (ver arriba, en curso) es trabajo nuevo fuera de ese marco. Trabajo futuro más allá de G10 (nuevas features, bugs reales que aparezcan en operación, ADRs revisados si cambian las circunstancias que los motivaron) se planifica cuando llegue.
