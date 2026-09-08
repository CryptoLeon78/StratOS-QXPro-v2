# G13 — Identidad de candidatas Forward no AUDCAD

Fecha: 2026-09-08.

## Alcance

- Se retiró del alcance de análisis `XAU_H4_Capa2\Forward`, que estaba vacía. No se eliminó su carpeta padre.
- Se procesaron 110 parejas `.sqx`/`.mq5`: 6 DAX M30 Capa 2, 60 XAU H1 Capa 2, 1 XTI H4 Capa 2, 40 SPA35 D1 Capa 2 y 3 XAU H1 Capa Mixta/Día Entero.
- Los 60 CSV de operaciones entregados junto a XAU H1 se consumen como fuente de operaciones de SQX cuando el `orders.bin` no es legible. No sustituyen la futura comparación SQX vs MT5.

## Magic Numbers

La política `g13-magic-identity-v3` reserva el intervalo `1_000_000..1_999_999` para candidatas de análisis. El intervalo operativo previo `1..999_999` se conserva intacto.

Las 110 fuentes recibieron una asignación determinista y única `1_000_000..1_000_109`. El manifiesto local de auditoría incluye ruta, valor anterior, valor posterior y hashes SHA-256 antes/después. Esta asignación no registra una identidad operativa ni autoriza una instalación MT5.

## Clasificación estática

El clasificador usa únicamente las reglas ejecutables de entrada del `.mq5`: indicadores resueltos, percentiles, recuperaciones desde mínimos, oscilador Awesome y condiciones direccionales multitimeframe. No usa el nombre, la ruta ni el perfil declarado por el operador.

Resultado del lote: 44 `MEAN_REVERSION`, 59 `MOMENTUM` y 7 `TREND`.

## Límites

Este resultado deja las fuentes preparadas para selección y validación posterior. Cada candidata conserva los gates obligatorios: compilación limpia, Tester MT5 con tick real, contraste SQX/MT5, paquete sellado y veredicto antes de cualquier alta en la incubadora.
