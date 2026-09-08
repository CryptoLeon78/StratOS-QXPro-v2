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
