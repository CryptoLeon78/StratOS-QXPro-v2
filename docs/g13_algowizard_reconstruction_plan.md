# G13 — Plan de reconstrucción SQX mediante AlgoWizard

## Propósito y límites

Recuperar una representación SQX trazable de estrategias F7 externas que
conservan el EA MQL5, pero no su `.sqx`. Es una reconstrucción nueva, no una
recuperación ni una prueba de equivalencia del artefacto histórico. No modifica
las cuentas reales, los EAs desplegados ni la cola de `SQX_vs_MT5` activa.

Cada resultado se etiquetará `RECONSTRUCTED_FROM_MQL5` y conservará los hashes
del fuente y del binario observado. Nunca sustituirá, sobrescribirá ni elevará
automáticamente al EA externo original.

## Inventario inicial

| Unidad de reconstrucción | Despliegue | Fuente MQL5 | Estado |
| --- | --- | --- | --- |
| `OROLONGLIMITSPPSTRH1D1 4.7.77` | BEPB y JJTI, XAUUSD/H1 | SHA-256 `15F9576D10A06C9A4FCD4992EFAFBD615F2811152F4AB3129F48D583666FB516` | Reconstruible; una sola unidad para los dos despliegues. |
| `SP500LONGD1 REVERSION SL 2.86.54` | BEPB, SP500/D1 | SHA-256 `EC291BC22B276D5FE6EAE7A8AECCE5086E0C1A947F8AF9ED59D94F35CB0DFACA` | Reconstruible. |
| `SPA35LONGD1 REVERSION SL 1.31.56` | BEPB, SPA35/D1 | SHA-256 `19A6CC8BF2E752ED377055A9831D8D785DD897DEBE62175FDCDBC34D07D78076` | Reconstruible. |
| `EURUSD_SELL_STOP_H4_LC_3.8.141` | BEPB, EURUSD/H4 | Sólo `.ex5` localizado; no hay `.mq5` en las fuentes ni en `C:\BOTS\EAs` | Bloqueada por fuente. No se hace ingeniería inversa del binario. |

Los tres fuentes disponibles fueron generados por StrategyQuant. Los dos
reversionistas usan sólo ATR de SQX, entrada long a mercado, SL ATR y salida
por número de barras. La estrategia ORO usa EMA, ATR y Heiken Ashi de SQX,
orden buy-limit a las 14:00 y trailing. Esto permite una reconstrucción
semántica con AlgoWizard, pero no demuestra equivalencia todavía.

## Flujo propuesto

1. Crear un directorio de evidencia por unidad bajo
   `runtime/operational/algowizard_reconstruction/<strategy_slug>/`, ignorado
   por Git. El manifiesto inicial contendrá identidad de cuenta/despliegue,
   ruta, hash `.mq5`, hash `.ex5` si existe, símbolo, timeframe, magic y
   parámetros efectivos del gráfico. La configuración de despliegue (magic,
   comentario y money management) se conserva separada de la lógica.
2. Extraer del MQL5 una especificación humana mínima: condiciones de entrada,
   orden, SL/PT/trailing, salida temporal, filtros de sesión y todas las
   constantes. Una segunda lectura comprueba cada regla contra el fuente antes
   de abrir AlgoWizard.
3. Crear en AlgoWizard una estrategia vacía, con nombre nuevo
   `<original>__RECONSTRUCTED_MQL5__v1`; usar sólo bloques nativos equivalentes
   y guardar el `.sqx` nuevo fuera de las carpetas de fuentes F7. Si falta un
   bloque, se registra `UNSUPPORTED_BLOCK`, sin aproximarlo silenciosamente.
4. Exportar el EA reconstruido con los mismos parámetros lógicos, pero un
   magic de laboratorio no desplegable. Compilarlo en el terminal aislado.
5. Ejecutar comparación reproducible en el Tester Darwinex: mismo símbolo,
   timeframe, sesiones/coste, ticks reales y ventana 2018-01-01 hasta la fecha
   de la corrida. Comparar EA fuente y EA reconstruido antes de comparar con
   el OOS real. Se sellan HTML, trades, configuración y diferencias.
6. Aplicar el veredicto por capas: `STRUCTURAL_MATCH` (señales/órdenes
   esperadas), `MT5_MATCH` (trades y métricas dentro de tolerancias declaradas)
   y, por separado, comparación frente al OOS real por cuenta. Un fallo queda
   `WITHHELD_RECONSTRUCTION_MISMATCH`; un pase sólo habilita análisis, nunca
   operación real ni promoción automática.

## Prioridad de ejecución

1. `SP500LONGD1 REVERSION SL 2.86.54` y `SPA35LONGD1 REVERSION SL 1.31.56`:
   son los más directos, ambos SQX144 y de lógica compacta.
2. `OROLONGLIMITSPPSTRH1D1 4.7.77`: requiere validar el mapeo exacto de
   Heiken Ashi/SqATR entre el exportador SQ 3.9 y SQX144.
3. `EURUSD_SELL_STOP_H4_LC_3.8.141`: queda como prioridad de recuperación de
   fuente. Sólo entra al flujo cuando aparezca un `.mq5` verificable.

## Controles

- SQX puede permanecer abierto para editar en AlgoWizard cuando se autorice la
  ejecución del flujo; esta fase de plan no ha creado ni cargado estrategias.
- No se usa ni modifica la instancia MT5 real. El único Tester permitido es
  `SQX_vs_MT5` con AutoTrading desactivado.
- Cada nueva evidencia se añade append-only; no se altera la evidencia ni los
  veredictos existentes de F7.

## Registro de ejecución (2026-08-31)

- `SP500LONGD1 REVERSION SL 2.86.54`: existe el artefacto nuevo
  `SP500LONGD1_REVERSION_SL_2.86.54__RECONSTRUCTED_MQL5__v1.sqx`, sellado en
  evidencia operacional. Su lógica confirmada es la de la fuente (entrada
  long, `2 x ATR(25)`, salida a dos barras), pero el archivo guardado conserva
  MM fijo de 0,1 y capital 10.000. Queda `STRUCTURAL_ONLY`; una versión v2 con
  perfil equivalente debe guardarse como artefacto distinto, nunca
  sobrescribiendo v1.
- El usuario creó dos borradores vacíos en AlgoWizard. Se reservaron sin
  sobrescribir artefactos: `New strategy (2)` para SPA35 y `New strategy` para
  ORO. Ambos quedan con cambios sin guardar deliberadamente hasta completar la
  lógica y asignar su nombre final.
- SPA35 quedó parametrizada para `SPA35_darwinex`, `D1`, motor
  `MetaTrader5 (hedged)`, intervalo `2018.01.01`--`2026.08.21` (fin disponible
  en SQX) y perfil `FixedAmount`: capital 100.000, riesgo monetario 200,
  dos decimales, fallback 0,1 y máximo 5 lotes. Sus Trading Options conservan
  filtros temporales desactivados y máximo de una operación diaria, como el
  fuente. Falta materializar y revisar las cuatro condiciones de entrada, SL
  `3 x ATR(10)` y salida a tres barras.
- ORO quedó parametrizada para `XAUUSD_darwinex`, `H1`, motor
  `MetaTrader5 (hedged)` e intervalo `2018.01.01`--`2026.08.21`. Mantiene el
  `FixedSize` de fuente 0,01; el tamaño observado 0,1 de los gráficos reales
  sigue siendo una sobreescritura de despliegue, no parte de la lógica. Sus
  Trading Options sí fijan salida viernes 22:00, rango 02:00--19:00, salida al
  final del rango y una operación diaria. Faltan la orden limit, expiración,
  EMA/ATR/Heiken Ashi, SL/PT/trailing y revisión estructural.
- La interfaz muestra todavía en el resumen la precisión rápida aunque el
  selector interno quedó en `Real Tick - real spread`; no se toma esa UI como
  evidencia de que la precisión haya quedado persistida. Se comprobará al
  guardar/reabrir, antes de cualquier backtest.
- SPA35: se materializaron en `New strategy (2)` las cuatro condiciones
  verificadas contra el fuente: `Low[1] <= High[4]`, `Open[2] < Close[2]`,
  `Open[3] >= Close[2]` y `Low[1] < Close[1]`. La acción es entrada long a
  mercado con MM global, `ExitAfterBars=3` y `StopLoss=3 x ATR(...)`.
  El control remoto no reflejaba de forma fiable el valor mientras se editaba,
  por lo que se verificó el artefacto guardado directamente. En
  `New strategy (2).sqx`, `AtrPeriodSpa35=10`, sin aproximación. El mismo
  archivo conserva `testPrecision=4`, motor `MetaTrader5 (hedged)`,
  `SPA35_darwinex/D1`, capital 100.000 y perfil FixedAmount de 200. Queda
  pendiente la recarga del artefacto y su revisión estructural antes del
  backtest; ya no está retenido por precisión del parámetro.
- La inspección XML posterior del artefacto sellado confirma el orden y los
  desplazamientos de las cuatro comparaciones, la entrada long con MM global,
  `ExitAfterBars=3` y la fórmula de SL con multiplicador 3 enlazada a
  `AtrPeriodSpa35=10`. Resultado: `STRUCTURAL_MATCH` para SPA35. No equivale
  todavía a `MT5_MATCH`: falta exportar el EA reconstruido, compilarlo en el
  terminal aislado y ejecutar la comparación tick-real frente al `.mq5`
  fuente.
- Cola `SQX_vs_MT5`: el backtest de `XAU1H1BUYSTOP_0620_Strategy 3.10.66`
  finalizó con `TOLERABLE` (NP/PF dentro de tolerancia; DD y número de trades
  requieren revisión). `SP500H1D1BUYSTPeof_R615_7.13.55` se retuvo por no
  disponer de ticks reales completos en el rango exigido.

## Registro de ejecución (2026-08-31, continuación)

- SPA35: AlgoWizard exportó el EA nuevo a
  `runtime/operational/algowizard_reconstruction/spa35longd1_reversion_sl_1_31_56/SPA35LONGD1_REVERSION_SL_1.31.56__RECONSTRUCTED_MQL5__v1.mq5`.
  La compilación en MetaEditor del terminal aislado Darwinex terminó con
  `0 errors, 0 warnings`. El archivo es evidencia de laboratorio: no se copió
  a ningún terminal ni gráfico de JJTI/BEPB.
- Se extendió el lanzador operacional y `SQX_vs_MT5` para aceptar
  `--sqx-trades-csv`. Un `.sqx` guardado desde AlgoWizard puede no contener
  `orders.bin`; en ese caso, el CSV de operaciones exportado por el propio
  AlgoWizard es la fuente primaria sellada y `lastSettings.xml` aporta
  símbolo/timeframe. La ausencia de `orders.bin` ya no se trata como una
  plantilla vacía ni se rellena con datos derivados. Las pruebas del lanzador:
  `6 passed`.
- ORO: se verificó el fuente MQL5 de nuevo. La señal es exclusivamente la hora
  `14:00`; genera una `BUY_LIMIT` a `EMA(Median,14)[1] - 0,5 x
  SmallestRange(50)[1]`, SL fijo de 1075 pips, PT `8,5 x ATR(48)[1]`, trailing
  `1,2 x ATR(36)[1]` y expiración de dos barras. Los handles Heiken Ashi se
  inicializan por la plantilla SQ 3.9, pero no se consumen por ninguna regla:
  quedan explícitamente excluidos de la reconstrucción, no aproximados.
- ORO: la materialización se hizo como XML nativo de AlgoWizard y se sometió
  al exportador local de SQX144. Se conservan dos intentos retenidos, sin
  sobrescritura: `v1` falló la compilación porque el bloque EMA utilizaba una
  clave de parámetro incompatible (`#TimePeriod#`); `v2` compiló, pero el
  exportador materializó `mmLots=0`, contrario al tamaño fijo de fuente.
- ORO `v3` corrige ambos contratos. El artefacto sellado es
  `runtime/operational/algowizard_reconstruction/orolonglimitspstrh1d1_4_7_77/OROLONGLIMITSPPSTRH1D1_4.7.77__RECONSTRUCTED_MQL5__v3.sqx`
  (`SHA-256 CD43AA51558E1539785CBAE3F7BEAC08EAFB5AA5D1D9E63C20C26C5B8E710918`),
  con EA exportado (`SHA-256
  2951CF8150F755BFD066811FEB5DE501D80DDBECB7E3604C48A3D0A763686527`).
  MetaEditor Darwinex lo compiló con `0 errors, 0 warnings`; la inspección
  estática confirma EMA Median/14, hora 14:00, limit a `EMA - 0,5 x
  SmallestRange(50)`, SL 1075, PT `8,5 x ATR(48)`, trailing `1,2 x ATR(36)`,
  expiración de dos barras y `mmLots=0,01`.
- Se publicó una copia idéntica, sólo como fuente de investigación, en
  `EAs_SQX_guardados/OROLONGLIMITSPPSTRH1D1_4.7.77__RECONSTRUCTED_MQL5__v3.sqx`.
  Veredicto: `STRUCTURAL_MATCH`. Sigue pendiente `MT5_MATCH` mediante dos
  backtests tick-real en el terminal aislado (fuente y reconstruido), y luego
  la comparación sellada contra el OOS real de cada cuenta. No se ha copiado
  ni adjuntado el EA a terminales o gráficos JJTI/BEPB.
- `EURUSD_SELL_STOP_H4_LC_3.8.141`: se buscó por identidad y versión exactas
  en `C:\BOTS\EAs`, `EAs_SQX_guardados` y el inventario de estrategias reales.
  Sólo existen dos copias idénticas del binario `.ex5` (205.894 bytes,
  `SHA-256 1E5414380EC28949E6AA55D810A66E20ADD6FFC048208937160AEA7893E443C5`),
  sin `.mq5` ni `.sqx` verificables. Se mantiene
  `WITHHELD_SOURCE_MISSING`: no se descompila el binario ni se infiere una
  lógica desde el nombre. La recuperación requiere localizar el fuente
  original o crear una reconstrucción nueva con especificación funcional
  explícita antes de entrar en AlgoWizard.
- Comparación ORO (ventana efectiva `2018-01-03`--`2026-08-18`): se sellaron
  el CSV de AlgoWizard (`SHA-256
  CCBFF80FCBEA4EEA522916E2DD3132F8E16E28D31FF8DBE143568178708F9B6A`) y el
  informe MT5 (`SHA-256
  96194D0200196ACC557C8B5233A0B121070B37A8992044E2B8B5FCFF44B21B75`). La
  identidad temporal es fuerte: 682 de 702 operaciones SQX se emparejan y
  sólo hay 6 exclusivamente MT5. Sin embargo, el report MT5 se ejecutó con
  `mmLots=0,1` y el CSV SQX con `0,01`; por ello el comparador marca
  `DISCREPANTE` en NP/PF/DD. El tamaño desigual invalida la comparación
  monetaria, pero no explica la discrepancia de PF ni los distintos motivos
  de cierre observados. El veredicto de reconstrucción es
  `WITHHELD_RECONSTRUCTION_MISMATCH`, con `CONFIGURATION_MISMATCH_SIZING`
  como causa adicional: hay que igualar el tamaño y reconstruir/validar de
  nuevo la interacción entre SL, trailing y salida de rango. Los informes
  derivados sellados están en
  `runtime/operational/comparisons/orolonglimitspstrh1d1_4_7_77_20260831/`.
- Comparación SPA35: el CSV AlgoWizard está disponible y sellado (`SHA-256
  74824AF4686EFC01AEFD46ACB517A7043B8958504C3AB5D7EB82C333FF0D7D3D`), pero
  el HTML MT5 suministrado (`SHA-256
  3D38A1519DB680F324BA21A0A2E14D85DC90955BD6EBA11F3CD475D1B010D43D`)
  declara `Total de operaciones ejecutadas: 0` y `Total de transacciones: 0`.
  No existe tabla de deals que comparar; queda `WITHHELD_MT5_REPORT_EMPTY`.
  Hace falta repetir ese Tester y exportar su informe completo antes de
  evaluar `MT5_MATCH`.

## Repetición de Tester (2026-08-31)

- ORO: el nuevo report MT5 con `mmLots=0,01` quedó sellado (`SHA-256
  E54B0FED2C4A269705E5BC443A8F7D184857C97468D3E30BD0B3D47DEDF3DE01`).
  Con sizing igualado, 682/702 operaciones SQX se emparejan y no existe
  escalado sistemático de valor de punto (mediana MT5/SQX `1,0049`). Aun así,
  NP `474,84` vs `1.135,22` (58,17 %), PF `1,20` vs `1,46` (17,75 %) y DD
  relativo difieren (29,80 %). Sigue
  `WITHHELD_RECONSTRUCTION_MISMATCH`: el tamaño ya no es una explicación;
  los cierres SL/trailing/rango y el tratamiento tick-real deben explicarse
  antes de retomar la reconstrucción. Informe sellado SHA-256
  `4CE9F8534A1BF088199FE5F45D8616787885312F985D3D41C89C37AFCA27C698`.
- SPA35: el nuevo report MT5 sí contiene operaciones y está sellado (`SHA-256
  1DF765E665DB47E49A016E791283804557BBD78482395E52CB9F7D18070A14C9`).
  La comparación con lote fijo `0,1` queda en NP `5.655,00` vs `7.621,21`
  (25,80 %), PF `1,38` vs `1,58` (12,43 %), DD `2,13 %` vs `1,94 %` y
  217 vs 211 operaciones. Sólo se emparejan 135/217 operaciones SQX
  (76 exclusivamente MT5); la desviación temporal aumenta a partir de 2023.
  Veredicto `WITHHELD_RECONSTRUCTION_MISMATCH`: la escala es compatible,
  pero hay que investigar timezone/DST y la evaluación de barras diaria antes
  de atribuir el resultado a la lógica. Informe sellado SHA-256
  `D8EAF3BC105C1BE2DA28231D7B57272E11F80352852E558B2BDB723FCDD2E2A1`.
