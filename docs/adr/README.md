# ADRs — StratOS-QXPro

Cada desviación necesaria de la fidelidad visual 1:1 (P12) o de una decisión de arquitectura ya fijada en `PROMPT_MAESTRO.md` se documenta aquí como `NNNN-titulo-corto.md` (formato estándar: contexto, decisión, consecuencias). Ninguna desviación de las capturas sin su ADR correspondiente (P15.13).

## ADRs

- [0001](0001-portfolio-grid-scalping-fusionados.md) — Portfolio: perfiles GRID y SCALPING fusionados en una fila.
- [0002](0002-salud-ph-booleano.md) — Salud: Page-Hinkley se muestra como Sí/No, no como número.
- [0003](0003-bots-historial-semaforo-no-pipeline.md) — Bots: "Historial del pipeline" sustituido por "Historial de semáforo".
- [0004](0004-pipeline-7-criterios-reales-vs-mockup.md) — Pipeline: "Detalle del gate" muestra los 7 criterios reales, no los del mockup.
- [0005](0005-pipeline-mover-a-sustituido.md) — Pipeline: dropdown "Mover a…" sustituido por los botones reales.
- [0006](0006-graveyard-sin-fecha-inicio.md) — Graveyard: solo se muestra la fecha de retiro, no el rango completo. **Parcialmente superado por G13-66** (`docs/phase_status.md`): `PipelinePhaseTransition` sí existe desde G11 y `GET /api/v1/cemetery` ya expone `entered_pipeline_at`; este ADR no se ha reescrito para reflejarlo.
- [0007](0007-gateway-sin-token-de-servicio.md) — api-gateway: proxy pass-through, sin "token de servicio" propio (desviación de la tabla de auth de PARTE 3, no de una captura).
- [0008](0008-bots-trades-por-mes-no-semana.md) — Bots: "Métricas completas" muestra Trades/mes (el dato real que calcula el backend), no Trades/sem.
- [0009](0009-g12-demo-local-conector-solo-lectura.md) — G12: EAs sólo en demo local; el conector permanece read-only y el VPS queda excluido.
- [0011](0011-pipeline-operacional-g13.md) — Pipeline operacional G13: evidencia, acciones y frontera demo (F0–F7 encolable). **Supersedido por 0012** (`docs/phase_status.md` G13-54/55: el Kanban F1–F7 se retiró de la superficie operacional); el propio 0011 no tiene nota de superseded.
- [0012](0012-pipeline-operacional-incubadora-portfolios.md) — Pipeline operacional: Incubadora y portfolios reales (decisión vigente).
- [0013](0013-alcance-por-cuenta.md) — Alcance por cuenta: selector global, KS/UMS/retiros por cuenta y correlación por cuenta (G14).

Los 6 primeros llegaron en G7 (PARTE 12, fidelidad de las 10 pestañas restantes). El 0007 llegó en G9 (Hardening) — primer ADR de arquitectura, no de fidelidad visual (el propio README del apartado ya cubre ambos casos). El 0008 llegó también en G9/G10. El 0011 y 0012 documentan la evolución de Pipeline en G13; el 0012 es la decisión activa.
