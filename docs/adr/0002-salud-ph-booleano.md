# 0002 — Salud: Page-Hinkley se muestra como Sí/No, no como número

## Contexto

La captura de referencia (`pestaña Salud.jpg`) muestra un chip "PH 1.3" (u otro valor numérico) por cada tarjeta de bot. `HealthRow` (`GET /api/v1/health/bots`) solo trae `page_hinkley_triggered: bool` — el valor numérico del estadístico de Page-Hinkley no se persiste ni se expone en ningún endpoint.

## Decisión

`HealthCard.tsx` muestra el chip "PH" con el texto "Sí"/"No" (interpolado desde `page_hinkley_triggered`), coloreado en `danger` cuando es `true`. No se inventa ni se aproxima un número.

## Consecuencias

- Se pierde la granularidad visual de la captura (un número real transmite más información que un booleano).
- Si en el futuro se decide persistir el valor numérico del estadístico (cambio en `core/formulas/monitoring.py::page_hinkley` + el modelo/schema correspondiente), este ADR queda obsoleto y el chip puede volver a mostrar el número — anotado en `docs/backlog.md`.
