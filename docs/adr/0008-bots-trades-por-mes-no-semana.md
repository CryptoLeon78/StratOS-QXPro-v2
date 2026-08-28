# 0008 — Bots: "Métricas completas" muestra Trades/mes, no Trades/sem

## Contexto

La captura de referencia (`pestaña Bots.jpg`) muestra una celda "TRADES/SEM" en el panel "Métricas completas" del detalle de bot. El backend (`GET /api/v1/bots/{id}/metrics`, G10) calcula `trades_per_month` — una ventana de 30 días vía `formulas/pipeline.py::trades_per_week` multiplicada por `_WEEKS_PER_MONTH = 4.345` (constante de diseño propio, documentada como tal en `routers/bots.py`, sin cifra contractual). No existe ningún endpoint que sirva un valor semanal directo.

Convertir `trades_per_month` a semanal en el propio frontend exigiría duplicar la constante `4.345` (o `52/12`) como un literal nuevo sin hogar declarado — viola P11 (CERO HARDCODING): antes de escribir una función, cada literal necesita un sitio declarado (`SystemConfig`/`design_tokens.json`/etc.), y una conversión de unidad puramente matemática no tiene uno.

## Decisión

`BotDetail.tsx` muestra la celda como "TRADES/MES" (interpolando `body.trades_per_month` directo, sin conversión), en vez de "TRADES/SEM". Es el dato real que el backend ya calcula, sin introducir un literal nuevo sin hogar.

## Consecuencias

- Desviación literal del texto de la captura (unidad de tiempo, no del concepto).
- Si en el futuro se decide que la cadencia semanal es la que de verdad importa, la ruta correcta es exponer `trades_per_week` como campo propio del backend (reutilizando `trades_per_week_formula` ya invocado en el propio endpoint, sin el paso intermedio a mensual) — no una conversión ad-hoc en frontend.
