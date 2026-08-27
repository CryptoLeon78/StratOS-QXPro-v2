# 0001 — Portfolio: perfiles GRID y SCALPING fusionados en una fila

## Contexto

`GET /api/v1/portfolio/profiles` devuelve 7 filas (`PROFILE_TARGET` en `core/routers/portfolio.py`: TREND 30%, MEAN_REVERSION 25%, MOMENTUM 15%, SMART_MONEY 10%, GRID 5%, SCALPING 5%, AI_ML 10%). La captura de referencia (`pestaña Portfolio.jpg`) muestra "Los 6 perfiles (micro)" con una única fila "Grid / Scalping" al 10%.

## Decisión

`MicroProfilesTable.tsx` fusiona client-side las filas `GRID` y `SCALPING` en una sola fila mostrada ("Grid / Scalping"), sumando `target_pct`/`real_pct`/`delta_pct`/`bot_count` de ambas. La API sigue devolviendo 7 filas sin cambios — la fusión es puramente de presentación.

## Consecuencias

- Fidelidad visual 1:1 con la captura (6 filas, no 7).
- Si en el futuro se necesita el desglose GRID vs SCALPING por separado en otra vista, los datos ya están disponibles sin cambios de API — solo hay que dejar de fusionar.
- La suma de dos porcentajes ya calculados sobre el mismo total es aritméticamente correcta (no requiere volver a dividir por el total).
