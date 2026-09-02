# G13 — Matriz de cierre operacional

> Estado comprobado: 2026-09-02. Esta matriz separa lo que ya es evidencia
> reproducible de lo que requiere una candidata real y una configuración de EA
> explícita. No autoriza operaciones en JJTI ni BEPB.

## Gates de entrada a Incubadora

| Gate | Estado | Evidencia o bloqueo |
|---|---|---|
| Aislamiento operacional y rechazo de fixture | CERRADO | Compose `stratos_operational`, puertos/volumen propios y guardia de seed operacional. |
| Cuentas reales e histórico | CERRADO EN SOLO LECTURA | JJTI/BEPB `BROKER_REAL`; CSV de histórico sellado e importado idempotentemente. |
| Cuenta de Incubadora | CERRADO | `account_id=3`, `BROKER_DEMO`, MetaQuotes-Demo; no se infiere del nombre de una carpeta. |
| Inventario y prefiltro de Análisis | CERRADO | Inventario, hashes, WFM informativo, costes y Monte Carlo sellados; la cola es local y auditada. |
| Comparación SQX↔MT5 | ABIERTO | A fecha de comprobación no hay ningún evento `BACKTEST_VALIDATED`; los HTML manuales sin CSV/veredicto permanecen `manual_report_only`. |
| Baseline aplicable | BLOQUEADO POR EL ANTERIOR | No hay baseline de Incubadora: crear una sin una candidata `VALIDADA` sería inventar evidencia. |
| Contrato de EA por gráfico | ABIERTO | Para cada candidata validada falta un manifiesto explícito de inputs: magic, comentario, símbolo MT5, timeframe, mapping de sizing/riesgo y fuente MQL5 instrumentada/compilada. No se deduce de los nombres de los inputs. |
| Adjunto y observación demo | BLOQUEADO POR LOS DOS ANTERIORES | Debe crear un perfil aislado, comprobar `mode=REAL`, `autotrading=true`, `expertmode=1`, reporter y alerta de deriva antes de declarar `INCUBATING`. |
| Capacidad y descorrelación | IMPLEMENTADO, A LA ESPERA DE CANDIDATA | Capacidad 8, tope estructural por símbolo/timeframe y correlación absoluta configurables; no se aplica contra datos ausentes. |

## Contrato de promoción que no se relaja

Una candidata de Análisis sólo puede pasar a la cola de Incubadora cuando exista,
para el mismo hash SQX/MQL5, un paquete sellado que incluya:

1. informe de comparación con `VEREDICTO: VALIDADA`;
2. CSV de trades MT5 usado por la comparación, HTML nativo y configuración efectiva;
3. fuente SQX que permita crear la baseline y su contrato de DD;
4. manifest de despliegue por gráfico, compilado e instrumentado, con los inputs
   específicos de ese EA y sin inferencia de nombre;
5. decisión de admisión que pase capacidad, límite estructural y correlación.

El paso F3, la baseline y el estado `INCUBATING` se registrarán de forma
append-only únicamente cuando los cinco elementos estén presentes. Mientras
tanto una estrategia puede seguir siendo una candidata de Análisis, pero nunca
un bot demo operativo por anticipación.

## Siguiente acción operativa

Ejecutar las corridas de candidatos nuevos desde `SQX_vs_MT5` v1.3.4 y archivar
el paquete completo. Después, importar cada paquete con
`Importar_corrida_manual_G13.bat`. El primer resultado `VALIDADA` desbloquea el
diseño concreto de su manifest de despliegue; no se reutiliza la configuración
de otro EA por parecido de nombre.
