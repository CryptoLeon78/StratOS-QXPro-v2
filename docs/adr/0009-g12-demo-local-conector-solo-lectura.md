# ADR 0009 — G12 usa sólo demo local y conserva el conector de lectura

## Contexto

G11 entregó el reporter v1.1 y la ingesta idempotente, pero el ciclo operativo no se pudo certificar sobre el terminal. G12 necesita comprobar el flujo con EAs reales de incubadora sin convertir StratOS en un canal de ejecución ni afectar cuentas reales.

## Decisión

- G12 opera exclusivamente sobre el terminal MT5 demo local y un Docker Compose aislado llamado `stratos_g12`.
- Los EAs pueden operar únicamente dentro de esa cuenta demo, tras ficha técnica individual, compilación comprobada y sizing explícito del operador.
- El reporter escribe telemetría en su outbox local; `mt5-connector` únicamente lee y transmite esa telemetría. No se añade ninguna API, ruta ni acción de envío de órdenes desde StratOS.
- El VPS y las cuentas reales quedan expresamente excluidos.
- Un superviviente sin verificaciones completas se conserva como `WITHHELD`; no se reemplaza ni se le inventa historial, baseline o magic.

## Consecuencias

La validación puede producir fills demo reales y por tanto TCA, pero no constituye autorización de producción. Cualquier paso hacia VPS/real exige una fase posterior, backup/restore comprobado, TLS y una confirmación independiente del operador.
