# G12 — recorrido de procedencia por pestaña

Fecha de evidencia: 2026-08-29. Alcance read-only sobre el stack
`stratos_g12`, el core en ejecución y la telemetría de MetaQuotes Demo. No se
envían órdenes, no se modifican transiciones de pipeline y no se resembran
datos.

## Regla de clasificación

- **Demo real**: dato recibido por el conector desde MetaQuotes Demo G12.
- **Derivado**: cálculo reproducible sobre datos identificados.
- **Ausente**: el dato no existe; debe mostrarse como ausencia, nunca como
  cero, éxito o historial real.
- **Fixture**: dato del perfil `full`, útil para demostrar componentes, pero
  no atribuible a la cuenta demo G12.

## Inventario de partida

| Fuente | Bots | Trades | Snapshots equity | Heartbeats |
| --- | ---: | ---: | ---: | ---: |
| `Prod` fixture | 50 | 15.810 | 1.433 | 43.201 |
| `Quarry` fixture demo | 15 | 0 | 0 | 43.201 |
| `MetaQuotes Demo G12` | 11 | 0 | 471 | 271 |

Los 11 bots G12 están en F3 y NARANJA. Los 11 `EaState` son conformes
(`PAPER`, AutoTrading OFF, sizing 50 %). No hay fills demo.

## Resultado por superficie

| Fase | Demo real | Derivado | Ausencia presentada con honestidad | Veredicto |
| --- | --- | --- | --- | --- |
| G12-03 Pipeline | 11 candidatas G12, sin OOS trades | Gate 0/7 a partir de ausencia de muestra | Forward sin datos es `—` | **BLOQUEADO**: 10 candidatas están F3, pero `USDJPYH1Lcity_5.15.110` figura F4 en `PipelineCandidate` mientras su bot administrativo es F3. El tablero mezcla 35 candidatas sin distintivo de fuente/cuenta. |
| G12-04 Bots | 11 bots G12, sin trades/fills | Salud/curvas se derivan del histórico disponible | Sin fill puede ser ausencia | **BLOQUEADO**: el listado global devuelve 76 bots y no marca fixture frente a demo. No se puede atribuir cada métrica visual a G12. |
| G12-05 Portfolio | Ninguna contribución G12 a F7 | 3 bloques, 7 perfiles y 496 correlaciones del conjunto fixture | Tail risk es `None` | **BLOQUEADO**: la exposición disponible es `XAGUSD`, fuera del universo G12; no hay etiqueta de procedencia. El benchmark lanza `FileNotFoundError` en el contenedor en vez de un estado de ausencia. |
| G12-06 Salud | 11 EAs demo con baseline, sin trades | Métricas rolling quedan en estado de muestra vacía | El contrato NARANJA/PAPER sí es real | **BLOQUEADO**: `/health/bots` devuelve 43 tarjetas mezcladas. La tarjeta no identifica fuente y no expone los valores numéricos de sus chips. |
| G12-07 Riesgo | Sin posición/fill G12 demostrable | FX/exposición se calculan sobre el conjunto global | VaR/CVaR devuelve ausencia | **BLOQUEADO**: la única exposición visible no es un símbolo G12; no hay aislamiento por cuenta ni etiqueta fixture/demo. |
| G12-09 Escalado | No hay eventos UMS G12 | No aplicable | `/scaling/ums` es `None`, historial vacío | **CONFORME COMO AUSENCIA**, siempre que la UI mantenga el estado vacío; no hay evidencia demo que permita fase UMS. |
| G12-10 Graveyard | Ninguna tumba G12 | 9 tumbas históricas fixture | No existe fecha inicial honesta de pipeline | **CONFORME COMO HISTÓRICO, NO COMO DEMO**: la UI no debe sugerir que las 9 tumbas proceden de G12. |
| G12-11 Auditoría | 4.006 lotes G12, 271 heartbeats y 471 snapshots | Continuidad/sellos son cálculos reproducibles | 0 trades/fills G12 | **BLOQUEADO**: sellos y trades se agregan globalmente (93.305 lotes, 15.810 trades); el resultado no separa G12 del fixture. |
| G12-12 Dominical | Alertas de deriva G12 vacías; heartbeat demo existe | Watchdog/News Shield reutilizan agregados | Rechazos estáticos como pendientes | **PARCIAL**: no muestra rentabilidad por diseño, pero sus paneles reutilizados no declaran procedencia. |

## Límites de la verificación UI

Las rutas del frontend y login responden, pero los endpoints protegidos
responden 401 sin sesión autenticada. No se lee ni se restablece la contraseña
del operador. Por ello este recorrido valida el runtime de core, sus contratos
de presentación y las rutas, pero no declara screenshot-diff autenticado ni
aceptación visual final.

El MCP `stratos` tampoco está expuesto como herramienta en esta sesión; no se
declara verificado el control `get_module_spec`/`scan_hardcoding` de este
recorrido.

## Gates antes de cerrar estas fases

1. Añadir una procedencia explícita y persistente (`demo_real`, `fixture`,
   `derived`, `absent`) a las respuestas y a cada superficie agregada.
2. Corregir el desfase F3/F4 de la candidata `USDJPYH1Lcity_5.15.110` mediante
   una transición de pipeline auditada, no una edición directa.
3. Resolver el benchmark inaccesible en contenedor para que devuelva una
   ausencia controlada o una serie operativa trazable.
4. Aislar por cuenta los agregados de Portfolio, Salud, Riesgo y Auditoría, o
   señalarlos inequívocamente como fixture.
5. Repetir el recorrido con sesión autenticada y evidencia visual, sin cambiar
   el bloqueo NARANJA/PAPER de los EAs G12.
