# ADR 0014 — Alcance por cuenta: desviaciones visuales respecto a las capturas

## Contexto

ADR 0013 hace que la cuenta elegida gobierne toda la aplicación. Eso obliga a
apartarse de las capturas contractuales (`capturas_proyecto_dashboard`) en unos
pocos puntos, cada uno declarado aquí (P15.13: ninguna desviación sin ADR).

## Decisión

1. **Barra de cuenta y orden de pestañas.** Entre la cabecera y la TabBar se
   añade un conmutador de cuenta (una opción por cuenta con datos). "Cuentas"
   pasa a ser la primera pestaña (etiqueta "Cuentas", antes "Cuentas/EA") y
   "Resumen" la segunda. La ruta de Resumen sigue siendo `/`; sin cuenta elegida
   cualquier pestaña redirige a Cuentas.
2. **Correlación, pestaña propia.** La matriz sale de Portfolio (donde la
   captura `pestaña Portfolio.jpg` la muestra) y pasa a `/correlacion`, con dos
   tarjetas por cuenta (teórica y observada), fecha de snapshot, bots incluidos y
   excluidos con motivo, y marca de "baja confianza". Portfolio conserva macro,
   micro y benchmark.
3. **Título de la tarjeta de equity.** "Equity del portfolio (todos los bots)"
   pasa a "Equity de {cuenta}": la cifra ya no agrega todas las cuentas.
4. **Contribución al portfolio.** El literal "% del P&L total" pasa a "% del P&L
   de la cuenta", que es lo que el backend calcula ahora.
5. **Panel Pipeline de Resumen.** Cuenta F4–F7 (ADR 0012 ya retiró F1–F3 de la
   superficie operativa; este panel se había quedado atrás).
6. **Cementerio.** La etiqueta de pestaña "Graveyard" pasa a "Cementerio".
7. **Bots.** Orden de grupos por fase (producción primero), filtro por semáforo,
   selección por defecto y enlace directo `?bot=ID`. Se mantienen sin cambios los
   paneles "Rolling vs Baseline" y "Métricas completas" tal como los muestra la
   captura, aunque repitan algunas métricas: quitarlas es una desviación mayor
   que este cambio no justifica (anotado en backlog).

## Consecuencias

Los baselines de Playwright de las 12 vistas se regeneran (win32 en local, linux
en CI). Los textos nuevos viven en `ui_strings.es.json` (`accountScope`, `tabs`,
`portfolio.coverage*`).
