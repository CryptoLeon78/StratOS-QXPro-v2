# 0004 — Pipeline: "Detalle del gate" muestra los 7 criterios reales, no los del mockup

## Contexto

La sección de detalle "Sigma MR SPX" de la captura de referencia (`detalles_seccion_incubacionOOS_de_pestaña_pipeline.jpg`) muestra un desglose de gate con: Profit Factor, Expectancy(R), Sharpe, **Sortino**, Max DD, **Asymmetry**, Muestra(trades) — y una tabla adicional "Backtest vs Forward".

`state_machines/pipeline.py::evaluate_pipeline_gate` (G3, ya implementado y testeado contra PARTE 6.3 antes de que existiera G7) usa exactamente estos 7 criterios: `profit_factor`, `expectancy_r`, `sharpe`, `max_dd_pct`, `sample` (oos_trades), `incubation` (incubation_days), `frequency` (trades_per_week). No hay Sortino ni Asymmetry en ningún punto del backend — ni en `PipelineGateMetrics`, ni en `CandidateResponse`, ni en ninguna fórmula de PARTE 8.

Por jerarquía de fuentes de verdad de `CLAUDE.md` ("1. PROMPT_MAESTRO.md — spec funcional y técnica. 2. capturas — spec VISUAL 1:1."), la spec funcional (PARTE 6.3, ya implementada en G3) tiene prioridad sobre un mockup visual que aparentemente quedó desactualizado respecto a la implementación final del gate.

## Decisión

`GateChecklist.tsx` recalcula client-side los 7 criterios REALES (profit_factor/expectancy_r/sharpe/max_dd_pct/sample/incubation/frequency) a partir de los campos crudos ya presentes en `CandidateResponse` + los umbrales del nuevo `GET /api/v1/config/pipeline-gate` (G7), reproduciendo exactamente la lógica de `evaluate_pipeline_gate` (mayor/menor estricto, sin banda de marginalidad para el semáforo ✓/✗ — la banda solo afecta al `verdict_reason` de HOLD, no al desglose visual).

Se omite la tabla "Backtest vs Forward" (`CandidateResponse` no trae métricas de baseline/IS) — ver `docs/backlog.md`.

## Consecuencias

- El desglose visual no coincide pixel a pixel con el mockup (7 etiquetas distintas), pero SÍ coincide con la lógica de negocio real que decide GO/HOLD/KILL — el operador ve exactamente los criterios que determinan el veredicto mostrado en la misma tarjeta.
- Si en el futuro se decide añadir Sortino/Asymmetry como criterios reales del gate (cambio en PARTE 6.3 + `evaluate_pipeline_gate` + migración de `PipelineCandidate`), este ADR y `GateChecklist.tsx` deben actualizarse juntos.
