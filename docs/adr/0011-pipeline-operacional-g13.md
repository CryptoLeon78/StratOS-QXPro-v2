# ADR 0011 — Pipeline operacional G13: evidencia, acciones y frontera demo

Fecha: 2026-09-09  
Estado: transición a orquestador F0--F7 iniciada; F1 encolable, pendiente de configuración local y evidencia demo

## Decisión

## Evolución G13-43

Pipeline pasa a ser el plano de control auditable de Cola, F1--F7. El core
persiste `pipeline_work_item` y `pipeline_agent_command`; no ejecuta Windows.
El agente local sólo podrá consumir comandos autenticados dirigidos a DEMO,
con confirmación individual para instalar un EA. FORJA/SQX/MT5 real quedan
fuera del plano de control.

## Evolución G13-46 — acciones F1 encoladas

F1 admite tres solicitudes: `FORJA_GENERATE`, `SQX_START` y `SQX_STOP`.
Todas llevan una idempotency key, se dirigen exclusivamente al grupo local
`ANALYSIS` y se convierten en una fila de `pipeline_agent_command`. El agente
de Contabo devuelve exactamente un evento terminal `SUCCEEDED` o `FAILED` en
`pipeline_agent_command_event`; ambos ledgers no permiten `UPDATE` ni
`DELETE` al rol de aplicación. El estado visible del ítem F1 se actualiza
como proyección: `QUEUED`, `GENERATED`, `MINING`, `STOPPED` o `FAILED`.

El navegador sólo encola. Para FORJA requiere entrada de catálogo, base, capa
y dirección; para SQX requiere una ruta de proyecto que el agente vuelve a
comprobar contra `allowed_source_roots`. El agente no acepta shell arbitraria:
la generación usa la sintaxis fija del catálogo y los lanzadores SQX vienen
de listas locales versionadas fuera de Git. Sin esa configuración el comando
falla cerrado y queda su evento persistente.
fuera del contenedor y JJTI/BEPB no son destinos admisibles.

Pipeline es el registro auditable del ciclo de vida de una estrategia; no es un
lanzador de MetaTrader ni una pantalla que autorice trading. Cada columna debe
indicar evidencia, siguiente acción permitida y bloqueador. Ninguna acción de
la UI abre MT5, adjunta un EA, cambia AutoTrading o envía órdenes.

```
SQX/Análisis → cola sellada de Tester → comparación SQX↔MT5
    → BACKTEST_VALIDATED → F3 + baseline → adjunto demo verificado
    → F4/F5 con telemetría demo → F6 staging → F7 champion
```

La cola sellada es una bandeja de entrada, no otra fase. Una estrategia puede
ser visible en la cola y en F3 por motivos distintos: la primera acredita su
trabajo de Tester; F3 acredita su registro interno y baseline. La UI debe
explicar ambas procedencias, nunca sumar ambas como dos candidatas.

## Acciones por fase

| Fase | Acción de interfaz | Regla |
|---|---|---|
| F1 | Promover a F2 | Decisión humana, registrada. |
| F2 | Promover a F3 | Decisión humana; la admisión operacional exige además expediente sellado. |
| F3 | Comprobar admisión demo | Consulta baseline, cuenta demo y `BACKTEST_VALIDATED`; falla cerrada sin evidencia de adjunto de gráfico. |
| F4–F5 | Recolección/evaluación automática | Sólo telemetría MT5 ya ingerida; F5 acumula días válidos y trades posteriores a su entrada. |
| F6 | Evaluación contractual automática | `APPROVE` F5→F6 sólo con GO 7/7; `POSTPONE` conserva F5 si falta muestra/tiempo/evidencia; `REJECT` se audita y exige autopsia antes de Cementerio. No modifica MT5. |
| F7 | Observación de champion | Challenger sólo sustituye tras comparación contractual del mismo slot. |

La promoción manual termina en F2. F3 no puede avanzar por clic: F4 requiere
un manifiesto de adjunto demo y preflight de telemetría. La ausencia de ese
manifiesto se muestra como bloqueo, no se estima a partir de un nombre de EA o
una carpeta.

## Evolución G13-52 — Evaluador F6 desde F5

`f6_evaluation` conserva de forma append-only cada resultado con la huella de
la evidencia F5 y el hash del snapshot de `PipelineGateConfig`. La misma
evidencia no puede duplicar una decisión. El evaluador sólo toma trades demo
cerrados que se abrieron después de `entered_phase_at` de F5, los días con
heartbeat y equity en UTC, y el estado contractual del reporter; el baseline
de Tester queda fuera de las métricas de gate.

La ingesta read-only de trades, heartbeat, equity o `ea_state` vuelve a evaluar
las candidatas F5 afectadas. Antes de los mínimos contractuales de muestra y
tiempo, el resultado obligatorio es `POSTPONE` con `HOLD` y no se aplica la
regla genérica de KILL por varios criterios todavía inmaduros. Con evidencia
suficiente, se evalúan los siete gates: `APPROVE` registra F5→F6 con actor
`SYSTEM`; `REJECT` conserva F5 y abre el rastro de KILL/autopsia, sin archivar
ni controlar MT5. F7 sigue fuera de este automatismo.

## Evolución G13-53 — Plan F6 de staging y comparación de slot

`f6_staging_evaluation` es un ledger inmutable, distinto de la decisión F5→F6.
Cada fila sella la evidencia recibida desde el comienzo de F6, el snapshot de
los umbrales, el siguiente escalón solicitado y la lectura challenger. La
primera solicitud es 10% sólo después de comprobar `sizing_total_cap`; 25, 50
y 100 requieren además los `staging_min_trades` desde la entrada F6 y una
revalidación `GO` de los siete gates. El resultado no escribe
`Bot.sizing_current_pct`, no emite comando al agente y no modifica MT5: es un
plan visible para confirmación humana fuera de la promoción F7.

La comparación requiere datos explícitos y contemporáneos: challenger con
rol/slot declarados, exactamente un champion F7/PRODUCCION en el mismo slot,
una matriz de correlación común para ambos y R-multiples cerrados comparables.
Se usa Welch unilateral sobre R (challenger mayor), y correlación media en
valor absoluto contra el bloque; ambos detalles se conservan como decisión
operativa porque el prompt fija el p-value pero no su prueba estadística. La
ausencia de cualquiera de estos hechos devuelve un estado declarativo y no
infiere identidad por nombre. Incluso con cinco criterios favorables sólo se
inserta `ChallengerEvaluation`: la rotación, retiro y F7 siguen siendo una
decisión humana.

## Evolución G13-54 — Contención visual por fase

La captura contractual muestra una única superficie Kanban de siete columnas,
F1--F7. Los auxiliares operativos no constituyen nuevas filas ni fases:
la Cola y los proyectos de minado se contienen en F1, los activos
`STATIC_VALIDATED` y su cola Tester en F2, y las evidencias
`BACKTEST_VALIDATED` en F3. Permanecen plegados al abrir la página para evitar
cargar listas extensas. Esta decisión afecta exclusivamente a la composición
del frontend; conserva APIs, ledger, transiciones, evidencia y controles de
seguridad existentes.

## Implementación

Se añade `POST /api/v1/pipeline/{id}/demo-readiness`, una comprobación de F3
sin efectos sobre MT5. La tarjeta F3 ejecuta esa comprobación y desglosa los
requisitos. `POST /promote` rechaza desde F3 para impedir saltos ficticios a
F4.

La segunda unidad añade `demo_chart_attachment`, una tabla append-only cuyo
manifiesto completo se conserva como artefacto `DEMO_ATTACHMENT` sellado. El
registro normal se realiza desde el formulario F3 `Registrar adjunto demo`; el
script `scripts/record_demo_chart_attachment.py` queda como respaldo operativo
para la misma validación y verifica
contra el candidato F3: cuenta `BROKER_DEMO`, hash SQX de baseline, hash de
fuente MQL5, magic, símbolo, timeframe y versión EA. La declaración no basta:
`demo-readiness` sólo la reconoce cuando llega después un `ea_state` sellado
que coincide en versión, modo `REAL`, AutoTrading y sizing. El script no abre
MT5, no escribe perfiles ni compila o adjunta EAs.

Cuando `POST /ingest/ea_state` recibe ese estado sellado, el core vuelve a
evaluar los candidatos F3 del mismo `(account_id, magic)`. Sólo si todos los
requisitos siguen presentes registra la transición append-only F3→F4 con actor
`SYSTEM` y publica `pipeline.demo_admission_verified`; si no, no cambia nada.

## Consecuencias

- Los candidatos F3 existentes siguen visibles pero no se declaran incubando
  por aparecer en el tablero.
- F4 y F5 continúan sin datos hasta que el adjunto demo y el reporter aporten
  telemetría read-only reconciliada.
- Registrar un manifiesto sin telemetría posterior deja el candidato bloqueado;
  nunca se promueve a F4 por haber ejecutado un script o por un nombre de EA.
- Los 40 F7 `EXTERNAL_PRODUCTION` permanecen observacionales; no se les asigna
  una promoción histórica ni se inventa baseline.

## Despliegue Contabo — 2026-09-09

El agente se instaló en `C:\StratOS\pipeline-agent` como tarea interactiva
`StratOSPipelineAgent`. Un túnel SSH inverso persistente expone el core local
sólo como `127.0.0.1:8300` en Contabo. `PIPELINE_AGENT_API_KEY` es exclusiva
del agente; no reutiliza la clave de ingesta.

El preflight autenticado terminó con código cero tras instalar `PyYAML` en el
venv remoto y aplicar la migración `f5a6b7c8d9e0`. El perfil activo demo
`StratOS_Incubadora` contiene los magics 243 y 295. Los perfiles de recuperación
pueden repetirlos: la guardia inspecciona únicamente el perfil activo.

F1 y Tester siguen bloqueados hasta declarar lanzadores locales. F4 permanece
fail-closed hasta instalar el helper de adjunto por gráfico con plan sellado.
