# 0003 — Bots: "Historial del pipeline" sustituido por "Historial de semáforo"

## Contexto

La captura de referencia (`pestaña Bots.jpg`) incluye una sección "Historial del pipeline" en el panel de detalle del bot, con entradas del tipo "2021-11-03 F6 → F7 — Promoción a Producción tras rotación". No existe ningún endpoint que sirva el historial de transiciones de fase de un candidato — `PipelineCandidate` no tiene tabla de auditoría de fases, y `DecisionLog` no está expuesto con ese filtro.

`GET /api/v1/bots/{id}/semaphore-history` sí existe y sirve datos reales y directamente relevantes (transiciones VERDE/AMARILLO/NARANJA con fecha).

## Decisión

El panel de detalle de Bots (`BotDetail.tsx`) muestra "Historial de semáforo" en el mismo lugar del layout donde la captura muestra "Historial del pipeline", con los datos reales de `semaphore-history`.

## Consecuencias

- El usuario no ve el historial de ascensos de fase del bot en esta pestaña (si se necesita, la pestaña Pipeline muestra la fase actual del candidato mientras esté activo, y Graveyard el motivo de retiro si fue archivado).
- Si en el futuro se añade una tabla de auditoría de transiciones de `PipelineCandidate.current_phase`, este ADR queda obsoleto y ambas secciones podrían convivir.
