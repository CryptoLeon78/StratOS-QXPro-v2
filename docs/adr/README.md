# ADRs — StratOS-QXPro

Cada desviación necesaria de la fidelidad visual 1:1 (P12) o de una decisión de arquitectura ya fijada en `PROMPT_MAESTRO.md` se documenta aquí como `NNNN-titulo-corto.md` (formato estándar: contexto, decisión, consecuencias). Ninguna desviación de las capturas sin su ADR correspondiente (P15.13).

## ADRs

- [0001](0001-portfolio-grid-scalping-fusionados.md) — Portfolio: perfiles GRID y SCALPING fusionados en una fila.
- [0002](0002-salud-ph-booleano.md) — Salud: Page-Hinkley se muestra como Sí/No, no como número.
- [0003](0003-bots-historial-semaforo-no-pipeline.md) — Bots: "Historial del pipeline" sustituido por "Historial de semáforo".
- [0004](0004-pipeline-7-criterios-reales-vs-mockup.md) — Pipeline: "Detalle del gate" muestra los 7 criterios reales, no los del mockup.
- [0005](0005-pipeline-mover-a-sustituido.md) — Pipeline: dropdown "Mover a…" sustituido por los botones reales.
- [0006](0006-graveyard-sin-fecha-inicio.md) — Graveyard: solo se muestra la fecha de retiro, no el rango completo.
- [0007](0007-gateway-sin-token-de-servicio.md) — api-gateway: proxy pass-through, sin "token de servicio" propio (desviación de la tabla de auth de PARTE 3, no de una captura).
- [0009](0009-g12-demo-local-conector-solo-lectura.md) — G12: EAs sólo en demo local; el conector permanece read-only y el VPS queda excluido.

Los 6 primeros llegaron en G7 (PARTE 12, fidelidad de las 10 pestañas restantes). El 0007 llegó en G9 (Hardening) — primer ADR de arquitectura, no de fidelidad visual (el propio README del apartado ya cubre ambos casos).
