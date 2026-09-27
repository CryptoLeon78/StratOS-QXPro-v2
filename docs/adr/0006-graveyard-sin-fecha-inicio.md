# 0006 — Graveyard: solo se muestra la fecha de retiro, no el rango completo

## Contexto

La captura de referencia muestra un rango de fechas por tarjeta ("2021-03-01 → 2022-09-12"). `CemeteryEntryResponse` (`GET /api/v1/cemetery`) solo trae `retired_at` (fecha de archivado) — no hay ningún campo con la fecha de entrada a incubación/pipeline del bot retirado, ni en `CemeteryEntry` ni cruzando con otro endpoint (`PipelineCandidate.entered_phase_at` se pierde/no es accesible una vez el candidato se archiva).

## Decisión

`CemeteryCard.tsx` muestra únicamente `retired_at` (fecha de retiro), sin fecha de inicio ni rango.

## Consecuencias

- Se pierde la noción visual de "cuánto duró" el bot en el sistema antes de ser retirado.
- Si en el futuro se decide persistir la fecha de alta original en `CemeteryEntry` (columna nueva, migración aditiva) o exponerla cruzando con el histórico de `PipelineCandidate`, este ADR queda obsoleto.

## Actualización G10 (investigado, sigue sin resolverse)

Se revisó el código real de `routers/pipeline.py::promote_candidate` esperando poder cruzar `CemeteryEntry.bot_id` con `PipelineCandidate.entered_phase_at` para recuperar la fecha de entrada a F1. Hallazgo: `entered_phase_at` se **sobrescribe** en cada promoción manual (`candidate.entered_phase_at = datetime.now(UTC)`, línea 132) — no es un histórico, es "fecha de la última transición de fase", que para un bot archivado tras pasar por varias fases NO es su fecha de entrada a F1. No existe ninguna tabla de histórico de transiciones de pipeline (a diferencia de `SemaphoreTransition`/`UmsPhaseLog`, que sí son append-only) — el dato de "cuándo entró a F1" está genuinamente perdido para cualquier bot que haya sido promovido al menos una vez, no solo "difícil de exponer".

`Bot.created_at` se descartó como sustituto: no todos los bots pasan por F1-F7 (los de producción pueden sembrarse directamente), así que usarlo como "fecha de inicio" sería incorrecto para ese subconjunto — mismo criterio de "no inventar" que rige el resto del proyecto.

Esta ADR sigue vigente: solo se muestra `retired_at`. Resolverlo de verdad exigiría una tabla nueva de histórico de fases (migración + lógica de escritura en cada transición, sin datos históricos que backfillear) — fuera de alcance de un endpoint aditivo, candidato a fase futura si el operador lo prioriza.

## Actualización 2026-09-27 (parcialmente resuelto)

Esa tabla nueva ya existía sin que este ADR lo reflejara: `PipelinePhaseTransition`
(`core/db/models/pipeline.py`, creada en G11) registra append-only cada transición de
fase, incluida el alta a F1 (`from_phase IS NULL`, escrita una única vez en
`create_candidate`). `GET /api/v1/cemetery` (`routers/cemetery.py`) ahora cruza
`CemeteryEntry.bot_id` → `PipelineCandidate.id` → esa transición de alta, y expone
`entered_pipeline_at` en `CemeteryEntryResponse`. `CemeteryCard.tsx` muestra el rango
completo (`entered_pipeline_at → retired_at`) cuando existe.

**Sigue siendo `None` (ausencia declarada, nunca inventada) para dos casos reales**: un
bot admitido antes de G11 (sin ese rastro histórico) y un bot sembrado directo en
producción sin pasar nunca por F1-F7 (sin fila `PipelineCandidate`). Ninguno de los dos
se sustituye por `Bot.created_at` — mismo criterio que la versión original de este ADR.
El seed de demo actual (`scripts/seed_lib/graveyard.py`) no crea `PipelineCandidate`
para sus 9 lápidas, así que la captura de referencia sigue mostrando solo `retired_at`
sin ningún cambio visual — el hueco está cerrado para datos reales, no retroactivamente
para el fixture de demo.
