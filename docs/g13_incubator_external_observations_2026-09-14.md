# G13 — Observaciones externas de Incubadora (2026-09-14)

## Propósito y límite

Este expediente registra tres EAs que el operador adjuntó manualmente a la cuenta demo `INCUBADORA_DARWINEX_DEMO` (login `3000108092`). Es una observación de inventario, no una admisión a Incubadora, un alta de bot, una transición F5 ni una recomendación de cartera.

La inserción se realizó mediante `record_external_ea_inventory.py`, que no contacta MT5 ni crea un `Bot` o `PipelineCandidate`. Las filas append-only resultantes son `external_ea_inventory.id` 81, 82 y 83, con `bot_id = NULL`. Por ello no participan en agregados de portfolio, gates, sizing ni cualquier ruta hacia BEPB/JJTI.

## Evidencia contrastada

La fuente de preparación es el manifiesto local read-only `Apps_entorno_SQX/mt5_ops_dashboard/config/incubator_forward_candidates.yaml`. La lectura SSH/SFTP de `contabo_incubator_demo` verificó que cada `.ex5` instalado existe bajo `Experts/` y que su SHA-256 coincide exactamente con el artefacto de preparación. El exporter v2.1 del dashboard también observó la identidad de gráfico por nombre, símbolo y timeframe. Esta última observación no sustituye un `EaState` contractual de StratOS.

| Estrategia | Magic | Identidad de gráfico observada | Ruta `.ex5` observada | SHA-256 `.ex5` | SHA-256 `.sqx` | Inventario |
| --- | ---: | --- | --- | --- | --- | ---: |
| `SPH4L_1.26.31_4.2.29_MN24` | 24 | `SP500` / `H4` | `Experts/SPH4L_1.26.31_4.2.29_MN24/SPH4L_1.26.31_4.2.29_MN24.ex5` | `5783540c3f4b794fc3a1eaef176d401a230b771622a94d167c200f37badc2ac4` | `debe2e0905fa5a362e76cd302606b1019dff10e6d7e741d22025433d023ba7a4` | 81 |
| `USDJPYH1L_2.22.171_MN13` | 13 | `USDJPY` / `H1` | `Experts/USDJPYH1L_2.22.171_MN13/USDJPYH1L_2.22.171_MN13.ex5` | `55e35ccc0338143318c5f7f6d4734224f954b4b888e0d9898ef4e4451fc445d8` | `939cdc7385ef9b9b151ddcd9e4e14b871702a042f5a064a9a8041bdbd650f14e` | 82 |
| `USDJPYH1L_5.15.110_MN8` | 8 | `USDJPY` / `H1` | `Experts/USDJPYH1L_5.15.110_MN8/USDJPYH1L_5.15.110_MN8.ex5` | `734effa5aa0d995240d6ffecba7f88fa4ae42bf62fe00ff0d4de81dbf1bfe9c2` | `97b9e2e819a456c6fdb872bcf246a814b00a877ea0f901ee3c802286575bf626` | 83 |

La corrección del primer EA a `SP500/H4` quedó observada por el exporter a `2026-09-14T22:51:09+02:00`; los dos USDJPY/H1 se observaron a `2026-09-14T22:46:39+02:00`.

## Estado de maduración declarado

| Estrategia | Trades forward cerrados | Días forward | Motivo de observación, no promoción |
| --- | ---: | ---: | --- |
| `SPH4L_1.26.31_4.2.29_MN24` | 9 | 240 | Menos de 11 trades forward cerrados. |
| `USDJPYH1L_2.22.171_MN13` | 18 | 169 | Menos de 182 días forward. |
| `USDJPYH1L_5.15.110_MN8` | 8 | 169 | Menos de 11 trades y de 182 días forward. |

Estas métricas sólo explican por qué se inició la observación; no son una validación de estrategia ni habilitan un cambio de cuenta.

## Siguiente condición admisible

La transición desde esta observación requiere implementar y ejecutar la ruta sellada `incubator_admission` definida por ADR 0012: identidad y perfil explícitos, evidencia de backtest reproducible, baseline importada, plaza y correlación evaluadas, y posterior telemetría contractual `EaState`, heartbeat y equity. Hasta entonces, estos registros permanecen fuera de F5 y ningún proceso de StratOS cambia gráficos, EAs u órdenes MT5.
