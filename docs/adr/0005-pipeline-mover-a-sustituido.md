# 0005 — Pipeline: dropdown "Mover a…" sustituido por los botones reales

## Contexto

La captura de referencia muestra en cada tarjeta un desplegable genérico "Mover a…" además del botón "Promover a FX". `core/routers/pipeline.py` no expone ningún endpoint de movimiento arbitrario de fase — solo `POST /{id}/promote` (F1→F2→F3→F4 únicamente, rechaza con 409 fuera de F1-F3) y `POST /{id}/kill` (archiva a cementerio). No existe forma de mover un candidato a una fase arbitraria ni de retroceder fase manualmente.

## Decisión

`CandidateCard.tsx` no implementa ningún dropdown "Mover a…". Ofrece únicamente los dos controles que el backend soporta de verdad: "Promover a FX" (habilitado solo F1-F3, texto ya usado en `ui_strings.pipeline.promoteTo`) y "Matar" (abre `KillDialog`, autopsia obligatoria).

## Consecuencias

- El operador no puede reordenar candidatos arbitrariamente desde la UI — coherente con P6.3 ("F4+ solo por gate automático") y con que el backend nunca ofreció esa capacidad.
- Si en el futuro se añade un endpoint de movimiento manual (fuera de alcance de G7, requeriría discutir si contradice P6.3), este ADR queda obsoleto.
