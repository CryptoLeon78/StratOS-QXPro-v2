# G13 — Onboarding verificable de Incubadora demo

Fecha: 2026-09-08. Alcance: una sola candidata demo; JJTI y BEPB permanecen fuera de alcance.

## Candidata y contrato

- Activo operacional `958`: `AUDCADH4L_ForexMinorLateral_Strategy 3.33.81`.
- Contrato de gráfico: `AUDCAD`, `H4`, magic `295`, perfil ejecutable `TREND`.
- Sizing confirmado: `mmRiskedMoney=200.0`; equity demo observada de referencia 100000 USD, equivalente a 0.20 %.
- Fuente SQX sellada: SHA-256 `45f1dd4fc5dc5d7876c00b6a781bafcc7884bdc811321231efdfd3698438de62`.

## Evidencia de despliegue

- Perfil aislado `StratOS_Incubadora_3_33_81` con un único gráfico y EA.
- Reporter v1.1 instalado como telemetría JSONL; no contiene APIs de orden.
- El conector read-only lee `stratos_incubadora_295.jsonl` desde `Terminal\\Common\\Files`.
- Ingesta observada: heartbeat, equity y `ea_state` para magic 295.

## Registro contractual

- Bot `42`, origen `INCUBATION`, rol `CHALLENGER`, fase `F3`.
- Baseline `2`, fuente `BACKTEST`, contrato DD 5 %.
- Candidata `42`: F3, 0 trades OOS y 0 días de incubación; no hay promoción F4.
- Evento append-only del activo: `INCUBATING` con decisión de admisión aprobada. El primer slot pasó capacidad, límite estructural y no requirió correlación con ocupantes.

## Alerta y recuperación

Se reportó temporalmente `mode=PAPER` desde el propio EA, generando la alerta real CRÍTICA `config_drift` para el bot 42. Tras restaurar `mode=REAL`, AutoTrading activo y sizing 0.20 %, el job operativo resolvió la misma alerta mediante `system:config_drift`.

Esto certifica observación, alerta y recuperación. No certifica fills, TCA ni promoción de fase: siguen sujetos a evidencia forward real.

## Segunda candidata registrada, pendiente de adjunto demo

- Activo operacional `479`: `AUDCADH4L_ForexMinorLateral_Strategy 3.4.65`.
- Contrato ejecutable: `AUDCAD`, `H4`, magic `243`, perfil `TREND`, `mmRiskedMoney=200.0` e `InitialCapital=100000`.
- El nombre almacenado del activo conserva un sufijo histórico `(1)`, pero el paquete físico sellado es `AUDCADH4L_ForexMinorLateral_Strategy 3.4.65.sqx`. Su SHA-256 `334c8b9f3253651e92d5ed839522c466c62abf4e9c03dcb6eca8a6f2de9ad71d` coincide con el activo validado.
- Gate de admisión ejecutado con los PnL de ambos SQX sellados: 214 trades de la candidata, correlación absoluta `0.0222859482` con el bot `42`, por debajo de `0.70`. Capacidad posterior: 2 de 8 plazas y 2 de 2 para `AUDCAD/H4`.
- Registro append-only: bot `43`, baseline `3` de fuente `BACKTEST`, rol `CHALLENGER`, fase `F3`, contrato DD 5 %, 0 trades OOS y 0 días de incubación. El activo `479` tiene el evento `INCUBATING` con la evidencia del gate.
- Se generó localmente el EA telemetry-only `AUDCADH4L_FxML_3.4.65_MN243.mq5`, con SHA-256 instrumentado `b19eb0ba6b06b7ae96ab7c48e0f78dc97e16e2e44a6fa2d9dfe3ef806884bbc1`, outbox `stratos_incubadora_243.jsonl` y comentario `AUDCADH4L_FxML_3.4.65_MN243`.

Para el despliegue manual, conservar `StratOS_Incubadora_3_33_81` y crear `StratOS_Incubadora_3_4_65` como perfiles de recuperación de un solo gráfico. El perfil **activo** `StratOS_Incubadora` debe contener exactamente los dos gráficos autorizados `AUDCAD/H4`, uno con magic 295 y otro con magic 243: en un mismo terminal MT5 sólo se ejecuta el perfil activo. Compilar y adjuntar el EA 243 en su gráfico, y actualizar el servicio read-only ya existente para observar ambos ficheros con `CONNECTOR_REPORTER_OUTBOX_FILENAME=stratos_incubadora_*.jsonl`. No hay evidencia de heartbeat, equity, `ea_state` o fills del magic 243 hasta completar esos pasos; F4 continúa bloqueada por el contrato forward.
