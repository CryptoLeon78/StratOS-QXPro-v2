# G12 — checklist de validación operativa y demo

## Alcance y reglas de parada

- Entorno único de esta fase: Docker Compose `stratos_g12`; no reutiliza volúmenes ni credenciales de G11.
- Terminal permitido: demo local. VPS, terminales reales y canales de orden de StratOS están fuera de alcance.
- El conector sólo puede leer la telemetría del outbox y enviarla a la ingesta. No emite órdenes.
- Una ficha debe tener artefacto SQX144 verificable, fuente MQL5, hash, magic único, compilación limpia, coincidencia exacta símbolo/timeframe Darwinex contra SQX, baseline importada y sizing demo aprobado antes de adjuntarse y armarse.
- Cada fase requiere evidencia de API/WS, contraste con la especificación `stratos`, captura y aceptación expresa del operador. Un defecto abre una corrección y se repite la misma fase.

## Inventario inicial

| Estado | Cantidad | Tratamiento |
| --- | ---: | --- |
| READY | 11 | Compilados, registrados y adjuntados al perfil aislado `StratOS_G12_Demo_11Ready`; contrato G12-02 conforme en `PAPER`, no armados para abrir operaciones mientras el semáforo siga en NARANJA. |
| WITHHELD | 5 | Conservan nombre y causa en el manifiesto; no se sustituyen ni se les asigna otro magic. |

## Recorrido de aceptación

| Fase | Superficie | Evidencia mínima |
| --- | --- | --- |
| G12-00 | Arranque | Login, rutas directas, gateway, WS, alertas y marca visual de datos demo. |
| G12-01 | Resumen | Cabecera, equity/P&L/DD, periodo, decisiones, pipeline, stale y reconexión WS. |
| G12-02 | Cuentas/EA | Cuenta demo, heartbeat, EAs, versión, AutoTrading, filtros, sizing y drift. |
| G12-03 | Pipeline | Candidatos, baseline/SHA/procedencia, Backtest-vs-Forward, F3 y timeline real. |
| G12-04 | Bots | Listado, detalle, métricas, posiciones, semáforo e historial; estados sin fill honestos. |
| G12-05 | Portfolio | Composición, perfiles, correlación, benchmark y separación fixture/telemetría. |
| G12-06 | Salud | Chips, alertas, heartbeats, degradación y ausencia de falsos verdes. |
| G12-07 | Riesgo | Exposición, FX, `unconverted_currencies`, límites, News Shield y Kill Switch confirmado por humano. |
| G12-08 | Ejecución | Fills demo inmutables/idempotentes, rechazos, spread, slippage, TCA y estados sin datos. |
| G12-09 | Escalado | UMS y límites visibles, sin promoción ni cambio automático de sizing. |
| G12-10 | Graveyard | Historial disponible, retiro y rechazo HTTP 409 de reactivación. |
| G12-11 | Auditoría | Cadena append-only, sellos, procedencia, filtros y errores. |
| G12-12 | Dominical | `/dominical` consistente y sin cifras/acciones de trading. |

## Estado de G12-00

- [x] Stack aislado levantado; core, gateway y frontend responden HTTP 200.
- [x] Migraciones y seed `full` realizados dentro de `stratos_g12`.
- [x] Backup acotado de las rutas MT5 que G12 modifica.
- [x] Inventario SQX/MQL5 y hashes de los 16 nombres `MANTENER`.
- [x] Validación fail-closed de símbolo/timeframe Darwinex desde SQX; el alta usará ese símbolo exacto para asociar telemetría.
- [x] Fuentes de 11 candidatos copiadas e instrumentadas de forma separada.
- [x] Perfil de conector read-only aislado: buffer G12 y filtro exclusivo `stratos_g12_*.jsonl`; un outbox por magic.
- [x] Compilación limpia registrada por MetaEditor para los 11 `READY` tras actualizar el reporter v1.1 (`0 errors`, `0 warnings`).
- [x] Sizing demo explícito y alta append-only: 11 bots F3, 11 baselines con contrato DD de 5 %, `capital_allocated_pct=10` y `risk_per_trade_pct=0.2`; excepción `--allow-withheld` limita el alcance a los 11 `READY`.
- [x] Perfil `StratOS_G12_Demo_11Ready` materializado y recargado: 11 gráficos con su magic, EA, símbolo MT5 y outbox independientes. La copia anterior queda en `StratOS_G12_Demo_11Ready.backup`.
- [x] Los 8 indicadores custom `Sq*` requeridos fueron compilados por MetaEditor antes de la última recarga; el arranque posterior de los 11 EAs no repite los errores `4802` de indicador ausente.
- [x] Conector activo: 11 `ea_state` aceptados con sello válido; sin magics G12 ausentes ni huérfanos.
- [x] Login visual confirmado por el operador en `http://localhost:5373/`; la autenticación atraviesa el proxy local `/api` de G12.
- [ ] Rutas directas y WebSocket confirmados durante el recorrido de superficies G12-01 a G12-12.

## Resultado de G12-02 — Cuentas/EA

- [x] Cuenta DEMO con heartbeat, equity, posiciones y 11 EAs reportados por MT5 demo.
- [x] Las 11 versiones reportadas coinciden con `ea_required_version=g12-reporter-v1.1`; filtros horarios y ventanas de noticias se persisten en `EaState`.
- [x] Asociación de cuenta y magic completa: 11/11 estados, cero magics G12 ausentes y cero huérfanos.
- [x] Modo operativo: 11/11 reportan `PAPER`, que coincide con los 11 bots en `NARANJA`.
- [x] Permiso por gráfico: 11/11 reportan `autotrading=false` y los 11 gráficos contienen `expertmode=0`; es el estado esperado de `PAPER`, no una autorización de órdenes.
- [x] Sizing: 11/11 reportan 50.00 %, igual a `sizing_current_pct=50.00` de sus bots NARANJA.
- [x] Alertado de deriva: `config_drift` compara modo, permiso AutoTrading y sizing; el job real se ejecutó sin alerta abierta porque los 11 contratos están conformes. Tests cubren la alerta CRITICA para las tres clases de deriva.
- [x] Cobertura técnica: Cuentas/EA muestra modo, permiso, sizing, filtro horario, ventanas de noticias y último estado reportado; el panel de deriva muestra modo, permiso y sizing. La integridad de magics se comprueba en el inventario (0 ausentes, 0 huérfanos). No se presenta una "última señal/trade" inexistente: G12 sigue sin fills.

**Resultado repetido:** G12-02 contractual pasa 11/11. No habilita operaciones demo: los once bots permanecen en `NARANJA` y el contrato exige `PAPER`/`expertmode=0`. El paso siguiente exige una transición de semáforo válida y una nueva comprobación antes de cambiar un gráfico a `REAL`.

Evidencia detallada y límites en `docs/g12_cuentas_ea_contract_validation.md`.

## Resultado G12-03..07 / G12-09..12 — procedencia por pestaña

- [ ] G12-03 Pipeline: bloqueado por el desfase auditado pendiente F3/F4 y por
  el tablero global sin procedencia visible.
- [ ] G12-04 Bots, G12-05 Portfolio, G12-06 Salud y G12-07 Riesgo: bloqueados
  porque sus agregados mezclan fixture, derivadas y telemetría demo sin
  separarlos de forma visible y trazable.
- [x] G12-09 Escalado: conforme como ausencia (`ums_current=None`, historial
  vacío); no se inventa fase UMS.
- [x] G12-10 Graveyard: conforme sólo como histórico fixture; no hay tumbas
  G12 y no debe presentarse como evidencia demo.
- [ ] G12-11 Auditoría: bloqueada por sellos y trades agregados globalmente,
  sin corte por cuenta demo G12.
- [ ] G12-12 Dominical: parcial; omite correctamente rentabilidad, pero los
  paneles reutilizados no declaran su procedencia.

La matriz de evidencia, datos reales, derivados, ausencias y gates está en
`docs/g12_tabs_provenance_validation.md`. La verificación visual autenticada y
WebSocket queda pendiente; no se usó ni se alteró la credencial del operador.
