# G12 — Validación contractual de Cuentas/EA

## Alcance

Validación read-only ejecutada sobre `stratos_g12`, MetaQuotes-Demo y el
perfil `StratOS_G12_Demo_11Ready`. No envía órdenes, no modifica gráficos,
no utiliza credenciales de cuentas reales y no altera los JSONL del reporter.

## Evidencia aceptada

| Control | Resultado |
| --- | --- |
| Alta administrativa | 11 bots F3, 11 baselines append-only y contrato DD de 5 %. |
| Configuración de cartera | Los 11 bots persisten 10 % de capital asignado y 0,2 % de riesgo por operación. |
| Perfil MT5 | 11 gráficos, con magic y outbox independientes; símbolos MT5 `DE40`, `EURGBP`, `US500`, `USDJPY`. |
| Asociación MT5 | 11 `EaState` para 11 bots G12; cero ausentes y cero huérfanos. |
| Reporter | Las 11 versiones coinciden con `g12-reporter-v1.1`; filtros y ventanas se persisten. |
| Canal | Heartbeat, equity, posiciones y estados se ingieren con sellos SHA-256 válidos. |
| Ejecución | Sin fills/rechazos demo todavía. Este resultado es esperado mientras el mercado no genera una operación del EA y no completa G12-08. |

## Repetición G12-02 — 2026-08-29

| Control corregido | Resultado repetido |
| --- | --- |
| Modo operativo | 11/11 `PAPER`, igual al modo esperado de los bots `NARANJA`. El reporter ya no emite el literal semánticamente ambiguo `DEMO`. |
| Permiso por gráfico | 11/11 `autotrading=false`; el perfil tiene 11/11 `expertmode=0`. La bandera global del terminal no se usa como sustituto del permiso individual. |
| Sizing | 11/11 `sizing_pct=50.00`, igual a `Bot.sizing_current_pct=50.00`. |
| Deriva y alerta | El job real se ejecutó contra PostgreSQL/Redis sin alertas abiertas. La alerta CRITICA cubre modo, permiso AutoTrading y sizing; sus regresiones pasan. |
| Integridad | 11 bots, 11 `EaState`, 0 magics ausentes, 0 huérfanos, 11 baselines con DD contractual de 5 %. |
| UI | El build de Cuentas/EA muestra el modo, permiso, sizing, filtro, ventanas de noticias y último estado; el panel de deriva incluye los tres campos comparables. Sin fills no se inventa una última operación/señal. |
| Dependencias EA | Los 8 indicadores custom `Sq*` requeridos compilan sin errores; tras recargar el perfil no se repiten los errores MT5 `4802` anteriores. |

## Límite operativo vigente

La repetición contractual pasa 11/11, pero **no autoriza operaciones demo**.
Los 11 bots permanecen `NARANJA`; por contrato se mantienen en `PAPER` con
`expertmode=0`. La corrección de grace period evita que un baseline recién
creado vuelva a degradarse de forma inmediata, pero no borra ni reinicia el
historial append-only de transiciones que ya llevó estos bots a `NARANJA`.

Sólo una transición de semáforo válida y auditada puede permitir volver a
`REAL`; entonces se debe regenerar el perfil con permiso por gráfico `ON` y
repetir G12-02 antes de que un EA demo pueda abrir una operación. StratOS y el
conector siguen siendo read-only.
