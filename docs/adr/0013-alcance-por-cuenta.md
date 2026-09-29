# ADR 0013 — Alcance por cuenta: selector de cuenta, KS/UMS/retiros por cuenta y correlación por cuenta

## Contexto

El stack operacional gobierna tres cuentas MT5 (BEPB y JJTI reales en lectura,
Incubadora demo). Hasta G13 la UI y la API agregaban todo en un único
portfolio: cabecera, Resumen, Riesgo, Portfolio, Salud y Escalado mezclaban
cuentas, y la matriz de correlación real pooleaba BEPB+JJTI con un mínimo de 30
días por bot (hoy solo 2 bots de JJTI y ninguno de BEPB lo alcanzan). El
operador (2026-09-29) pidió que la cuenta elegida gobierne toda la aplicación.

## Decisión

1. **Selector de cuenta global.** "Cuentas" es la primera pestaña y contiene un
   selector de las cuentas con datos; la elección (persistida en el navegador)
   se envía como `account_id` a todos los endpoints de lectura. No hay opción
   "todas las cuentas". Identidad y rol de cuenta siguen viniendo de
   `Account.name` / `Account.data_origin`, no de una lista en frontend.
2. **KS, UMS y retiros por cuenta** (desviación de PARTE 6/10 del prompt
   maestro, que los define como escalera única de portfolio). Cada cuenta tiene
   su propio nivel de kill-switch (8/12/15/20 % de DD sobre SU curva de equity),
   su propia fase UMS y su propio registro de retiros. Las tablas append-only
   (`kill_switch_event`, `ums_phase_log`, `withdrawal_log`) ganan una columna
   `account_id` nullable: `NULL` = evento heredado de portfolio. No se hace
   UPDATE de filas antiguas. Las reglas (umbrales, histéresis, firma) no cambian.
3. **Decisiones y alertas** ganan `account_id` nullable; las filas sin cuenta
   (`NULL`) se muestran en todas las cuentas marcadas como "portfolio".
4. **Correlación por cuenta, dos matrices**: observada (trades reales de la
   cuenta) y teórica (backtest sellado de los bots de la cuenta). Mínimo
   configurable de 10 días con operaciones o 10 operaciones cerradas por bot
   (antes 30 días); los pares con pocas observaciones comunes se marcan como
   "baja confianza". Los bots instalados que no entran se listan con el motivo.

## Consecuencias

- La curva de equity deja de excluir cuentas demo cuando se pide una cuenta
  concreta (`account_equity_curve`), para que la Incubadora tenga curva.
- Correlaciones con ~10 puntos son estadísticamente débiles: la UI lo declara,
  no lo oculta.
- BEPB/JJTI no tienen evidencia de backtest en BD (0 `baseline`); su matriz
  teórica queda vacía y explícita hasta importar los trades del Strategy Tester
  (tarea de backlog, no se inventa el dato).
- El 94 % de los trades reales tiene `bot_id` NULL (magic legado); la
  atribución retroactiva queda fuera de esta decisión (backlog).
- Los criterios G8 y el seed deben etiquetar sus eventos globales con cuenta.
