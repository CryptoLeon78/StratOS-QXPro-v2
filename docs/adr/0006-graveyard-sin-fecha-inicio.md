# 0006 — Graveyard: solo se muestra la fecha de retiro, no el rango completo

## Contexto

La captura de referencia muestra un rango de fechas por tarjeta ("2021-03-01 → 2022-09-12"). `CemeteryEntryResponse` (`GET /api/v1/cemetery`) solo trae `retired_at` (fecha de archivado) — no hay ningún campo con la fecha de entrada a incubación/pipeline del bot retirado, ni en `CemeteryEntry` ni cruzando con otro endpoint (`PipelineCandidate.entered_phase_at` se pierde/no es accesible una vez el candidato se archiva).

## Decisión

`CemeteryCard.tsx` muestra únicamente `retired_at` (fecha de retiro), sin fecha de inicio ni rango.

## Consecuencias

- Se pierde la noción visual de "cuánto duró" el bot en el sistema antes de ser retirado.
- Si en el futuro se decide persistir la fecha de alta original en `CemeteryEntry` (columna nueva, migración aditiva) o exponerla cruzando con el histórico de `PipelineCandidate`, este ADR queda obsoleto.
