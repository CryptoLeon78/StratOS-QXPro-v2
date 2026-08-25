# Auditoría de estrategias de trading: del Win Rate viral a una validación robusta

## 1. Idea central

El documento analizado parte de un caso muy habitual en trading: una estrategia que promete un **83% de Win Rate**.

La conclusión principal es que un porcentaje de aciertos alto **no demuestra que una estrategia sea buena**.

Lo importante es analizar conjuntamente:

- Expectativa matemática.
- Profit Factor.
- Costes de ejecución.
- Cómo se contabilizan las operaciones.
- Drawdown.
- Robustez.
- Out-of-Sample.
- Sensibilidad de parámetros.
- Monte Carlo.
- Validación estadística.
- Comportamiento sobre datos sintéticos.

El caso analizado demuestra que puede existir una estrategia con aproximadamente un 90% de operaciones ganadoras y, aun así, tener un **Profit Factor inferior a 1** y perder dinero.

Por tanto:

> **Win Rate nunca debe ser un criterio primario de aceptación de una estrategia.**

Debe utilizarse como una métrica descriptiva dentro de un sistema de validación mucho más amplio.

---

# 2. Las cinco ideas principales que podemos aprovechar

## 2.1. Break-even real

El documento calcula el Win Rate necesario para alcanzar el punto de equilibrio según el payoff medio y, posteriormente, propone exigir un margen adicional.

La idea fundamental es:

```text
Break-even Win Rate ≈ 1 / (1 + Payoff)
```

Por ejemplo, con un payoff medio de 1.8R:

```text
1 / (1 + 1.8) ≈ 35.7%
```

Por tanto, una estrategia no necesita ganar el 83% de las operaciones para ser rentable.

Sin embargo, no basta con superar ligeramente el break-even.

El documento propone exigir aproximadamente **12-15 puntos porcentuales de margen** sobre el break-even.

### Aplicación que podemos hacer

En SQX podemos calcular:

```text
Win Rate
Average Win
Average Loss
Break-even Win Rate
Margin over Break-even
Expectancy
Expectancy after costs
```

Y especialmente:

```text
Expectancy = WinRate × AvgWin − LossRate × AvgLoss − Costs
```

La expectativa después de costes debería tener mucho más peso que el Win Rate.

---

# 3. Costes de ejecución

Una de las críticas más importantes del documento está relacionada con el backtesting sin microestructura.

Para estrategias rápidas, especialmente scalping, hay que considerar:

- Spread.
- Comisión.
- Slippage.
- Costes de entrada.
- Costes de salida.
- Múltiples ejecuciones provocadas por cierres parciales.

El documento explica que ignorar estos factores puede transformar una estrategia aparentemente rentable en una estrategia perdedora.

Un ejemplo utilizado:

```text
Cuenta: $10.000
Riesgo por operación: 1%
Riesgo: $100
Número de operaciones: 1.912
Coste medio: $2,50 por operación
Coste acumulado: aproximadamente $4.778
```

La conclusión es importante:

> Los costes aparentemente pequeños pueden convertirse en una parte enorme del resultado acumulado cuando se realizan muchas operaciones.

## Aplicación al proyecto

Podemos crear un **Cost Sensitivity Test**.

Ejemplo:

```text
Coste base       PF 1.42
+25% costes      PF 1.31
+50% costes      PF 1.18
+75% costes      PF 1.04
+100% costes     PF 0.89
```

Esto permite conocer cuánto margen de seguridad tiene realmente la estrategia.

Una estrategia que solamente funciona con costes ideales debería recibir una penalización fuerte.

---

# 4. El problema de los cierres parciales

Esta es probablemente una de las ideas más importantes del documento.

La estrategia analizada aparentemente tenía un Win Rate extraordinario.

Pero al revisar cómo se contabilizaban las operaciones, se descubrió que una operación se consideraba ganadora si alcanzaba el primer objetivo parcial, incluso aunque posteriormente el resto de la posición terminase en Stop Loss.

El documento recalcula:

```text
Win Rate viral ≈ 83%
```

y observa que al considerar simplemente las operaciones que alcanzaron el primer parcial se obtenía aproximadamente:

```text
79%
```

Es decir, gran parte del supuesto Win Rate viral procedía de esa forma de contabilizar.

## Esto nos da una idea muy potente para SQX Analyzer

Podemos diferenciar:

### Win Rate tradicional

Número de operaciones consideradas ganadoras según el resultado final disponible.

### TP1 Win Rate

Porcentaje de operaciones que llegaron a tocar el primer objetivo.

### True Trade Win Rate

Porcentaje de operaciones cuya posición completa terminó realmente con resultado positivo.

Ejemplo:

```text
Trades totales                 1.284

Trades que tocaron TP1           921
Trades finalmente positivos       714

TP1 Win Rate                    71.7%
True Win Rate                   55.6%
```

Podemos calcular la diferencia:

```text
TP1 Inflation = TP1 Win Rate - True Win Rate
```

Si la diferencia es elevada:

```text
⚠ WARNING

La estrategia presenta una diferencia importante
entre TP1 Win Rate y True Trade Win Rate.

Posible inflación artificial del Win Rate
mediante cierres parciales.
```

Esto sería especialmente útil para detectar estrategias que parecen excelentes por su porcentaje de aciertos pero tienen una expectativa mediocre.

---

# 5. La estrategia no es solamente la entrada

El documento muestra algo especialmente interesante.

Después de modificar la gestión de la posición y eliminar los cierres parciales, el sistema pasó aproximadamente de:

```text
PF < 1
```

a:

```text
Win Rate = 48.2%
Profit Factor = 1.57
```

La estrategia pasó de ser perdedora a rentable sin modificar necesariamente sus indicadores principales ni la lógica básica de entrada.

Esto demuestra que una estrategia debe analizarse como un sistema completo:

```text
INDICADORES
     ↓
ENTRY LOGIC
     ↓
EXIT LOGIC
     ↓
POSITION MANAGEMENT
     ↓
COSTES
     ↓
ROBUSTEZ
     ↓
OOS
     ↓
MONTE CARLO
     ↓
SYNTHETIC DATA
     ↓
VEREDICTO
```

Y no:

```text
Win Rate > 70%
        ↓
"ESTRATEGIA BUENA"
```

---

# 6. Reverse engineering y formalización

El documento destaca otro concepto importante: una estrategia que no puede describirse mediante reglas objetivas no es fácilmente automatizable ni reproducible.

Por ejemplo:

> "Entrar cuando el histograma MACD haga un pico y empiece a girarse."

Eso no es una condición completamente objetiva.

Hay que definir:

- Qué es un pico.
- Cuántas velas intervienen.
- Qué diferencia debe existir.
- Cuánto tiempo puede durar.
- Qué valor debe tener el indicador.
- Qué ocurre si aparecen varios picos.

El documento formaliza estas condiciones para que puedan ser ejecutadas por una máquina.

La conclusión es:

> Si no puedes escribir las reglas de forma que otra persona o una máquina pueda ejecutarlas exactamente igual, no tienes una estrategia completamente definida; tienes una interpretación.

Esto es muy relevante para SQX porque las estrategias generadas por el sistema ya poseen condiciones objetivas y cuantificables.

---

# 7. OOS y degradación

El documento propone reservar datos para Out-of-Sample.

La idea:

```text
IN-SAMPLE
   ↓
Diseño / desarrollo / optimización
   ↓
ESTRATEGIA CERRADA
   ↓
OUT-OF-SAMPLE
   ↓
Validación
```

El OOS nunca debería utilizarse para seguir optimizando.

## Podemos añadir un indicador de degradación

Ejemplo:

```text
IS

PF              1.83
WR             62.4%
Return         +147%

OOS

PF              1.21
WR             55.1%
Return          +31%
```

Podríamos calcular:

```text
PF degradation = 1 - OOS PF / IS PF
```

En este ejemplo:

```text
1 - 1.21 / 1.83 ≈ 33.9%
```

El sistema podría clasificar la degradación como:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Esto permite distinguir una estrategia que simplemente pierde algo de rendimiento fuera de muestra de otra que colapsa completamente.

---

# 8. Robustez paramétrica

El documento propone modificar los parámetros aproximadamente ±20%.

Ejemplo conceptual:

```text
EMA 55
```

se prueba también con:

```text
44
45
46
...
66
```

La idea no es encontrar el mejor número.

La idea es comprobar si alrededor del parámetro elegido existe una zona razonablemente estable.

## Lo importante es buscar una meseta

Ejemplo:

```text
              EMA
           40  45  50  55  60  65  70

RSI 35      .   +   +   +   +   .   .
RSI 40      +   +   +   +   +   +   .
RSI 45      +   +   +   +   +   +   +
RSI 50      .   +   +   +   +   +   .
RSI 55      .   .   +   +   +   .   .
```

Lo que queremos evitar:

```text
              PF
              ↑
              │       X
              │      / \
              │     /   \
──────────────┼────/─────\────────
              │
```

Es decir, un único pico de rendimiento.

Queremos algo parecido a:

```text
              PF
              ↑
              │    ┌──────────┐
              │   /            \
              │  /              \
──────────────┼─/────────────────\────
              │
```

Una meseta es mucho más interesante porque indica que pequeñas variaciones del parámetro no destruyen el sistema.

---

# 9. El protocolo de cinco filtros del documento

El documento propone cinco filtros:

## Filtro 1 — Break-even

Calcular el Win Rate necesario para no perder dinero y exigir un margen de seguridad.

No basta con:

```text
Actual WR > Break-even WR
```

Se busca:

```text
Actual WR > Break-even WR + margen
```

El documento habla de aproximadamente 12-15 puntos.

---

## Filtro 2 — Mínimo dos años

El backtest debería:

- Tener suficiente duración.
- Incluir costes reales.
- Utilizar spread variable.
- Incluir comisión.
- Considerar slippage.
- Contener distintos regímenes.

El documento menciona explícitamente:

```text
Bull market
Bear market
Range-bound market
```

---

## Filtro 3 — Muestra

Se propone un mínimo de aproximadamente:

```text
300 operaciones
```

El razonamiento es que 50 operaciones ofrecen una evidencia estadística limitada.

### Matiz para nuestro sistema

No deberíamos convertir necesariamente 300 en una regla absoluta.

Podemos hacerlo mejor mediante:

- Número de operaciones.
- Intervalos de confianza.
- Variabilidad del resultado.
- Duración temporal.
- Régimen de mercado.
- Monte Carlo.

El número de operaciones debería ser un factor de confianza, no el único criterio.

---

## Filtro 4 — Out-of-Sample

Reservar una parte final de los datos.

No tocarla durante el desarrollo.

Después:

```text
ESTRATEGIA FINAL
       ↓
OOS
       ↓
VALIDACIÓN
```

Si funciona en IS pero colapsa en OOS:

```text
FAIL
```

porque existe una alta sospecha de sobreoptimización.

---

## Filtro 5 — Robustez paramétrica

Mover los parámetros aproximadamente ±20%.

Si pequeños cambios provocan el colapso del sistema:

```text
FAIL
```

Si existe una zona amplia con resultados razonables:

```text
PASS
```

---

# 10. Limitación del protocolo original

El protocolo del documento es útil, pero nosotros podemos ir bastante más lejos.

El protocolo básicamente cubre:

```text
Backtest
OOS
Parameter Robustness
Costs
Sample Size
```

Nuestro sistema ya puede añadir:

```text
Monte Carlo
Synthetic Data
Statistical Validation
KS
ACF
Ljung-Box
```

Por tanto, podemos construir un protocolo mucho más completo.

---

# 11. Propuesta: 10 filtros para SQX

La propuesta es convertir los cinco filtros originales en diez.

## Filtro 1 — Profitability Sanity Check

Comprueba:

- Net Profit.
- Profit Factor.
- Expectancy.
- Average Trade.
- Win Rate.
- Average Win.
- Average Loss.

El Win Rate no decide el resultado.

---

## Filtro 2 — Break-even + Margin

Calcula:

```text
Break-even WR
Actual WR
Margin over BE
```

También debe considerar el payoff real.

---

## Filtro 3 — Cost Sensitivity

Recalcular la robustez bajo diferentes niveles de costes:

```text
Base
+25%
+50%
+75%
+100%
```

El objetivo es conocer cuánto margen de seguridad tiene el edge.

---

## Filtro 4 — Sample Size

Evaluar:

- Número de trades.
- Trades por año.
- Distribución temporal.
- Concentración de operaciones.
- Régimen de mercado.

No convertir 300 operaciones en una regla rígida sin contexto.

---

## Filtro 5 — OOS

Validar el período no utilizado en desarrollo.

---

## Filtro 6 — IS → OOS Degradation

Comparar:

```text
PF
Expectancy
Return
Drawdown
Win Rate
Average Trade
```

entre IS y OOS.

---

## Filtro 7 — Parameter Robustness

Mover parámetros ±20%.

Buscar zonas de estabilidad y no máximos aislados.

---

## Filtro 8 — Monte Carlo

Evaluar la sensibilidad del sistema a diferentes órdenes de las operaciones y escenarios estadísticos.

Entre otros resultados:

- Drawdown.
- Percentiles.
- Probabilidad de ruina.
- Variación del Net Profit.
- Variación del Profit Factor.
- Rachas.
- Distribución de resultados.

---

## Filtro 9 — Synthetic Data

Utilizar datos sintéticos para comprobar si las características esenciales del sistema sobreviven cuando se altera la estructura de los retornos.

Aquí podemos integrar directamente el trabajo que ya estamos haciendo con:

```text
SyntheticBootstrap
SynthDataBus
BootstrapValidator
KS
ACF
Ljung-Box
```

---

## Filtro 10 — Statistical Stability

Comprobar si las propiedades estadísticas de los datos sintéticos y reales presentan una compatibilidad suficiente.

Podemos utilizar:

```text
KS
ACF
Ljung-Box
```

y otras métricas que incorporemos posteriormente.

---

# 12. Arquitectura conceptual

La arquitectura propuesta sería:

```text
             SQX STRATEGY
                  │
                  ▼
        ┌────────────────────┐
        │ Profitability      │
        │ Sanity Check       │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ Break-even         │
        │ + Margin           │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ Cost Sensitivity   │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ Sample Size        │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ OOS                │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ IS/OOS Degradation │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ Parameter          │
        │ Robustness         │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ Monte Carlo        │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ Synthetic Data     │
        └─────────┬──────────┘
                  ▼
        ┌────────────────────┐
        │ Statistical        │
        │ Validation         │
        └─────────┬──────────┘
                  ▼
             FINAL VERDICT
```

---

# 13. Resultado final propuesto

El módulo podría generar un resumen parecido a:

```text
╔════════════════════════════════════╗
║        STRATEGY VERDICT            ║
╠════════════════════════════════════╣
║ Profitability       PASS           ║
║ Break-even          PASS           ║
║ Costs               PASS           ║
║ Sample              PASS           ║
║ OOS                 PASS           ║
║ Degradation         PASS           ║
║ Parameters          PASS           ║
║ Monte Carlo         PASS           ║
║ Synthetic Data      PASS           ║
║ Statistics          PASS           ║
╠════════════════════════════════════╣
║ FINAL: ROBUST                      ║
╚════════════════════════════════════╝
```

Pero también debería poder producir:

```text
FINAL: FAIL
```

o:

```text
FINAL: WARNING
```

cuando exista evidencia insuficiente para aprobar o rechazar definitivamente.

---

# 14. Orden de importancia

Mi propuesta para el sistema sería priorizar:

```text
1. Expectancy
2. Profit Factor
3. Drawdown
4. Cost Robustness
5. OOS
6. Parameter Robustness
7. Monte Carlo
8. Synthetic Data
9. Statistical Validation
10. Win Rate
```

El Win Rate pasa a ser una métrica secundaria.

---

# 15. Conclusión

La lección principal del documento no es que una estrategia con 83% de Win Rate sea necesariamente mala.

La lección es:

> **Un Win Rate aislado no contiene suficiente información para determinar si una estrategia es viable.**

El caso demuestra que:

```text
Win Rate alto
        ≠
Estrategia rentable
```

y que:

```text
Win Rate más bajo
        +
mejor gestión
        +
costes controlados
        +
robustez
        =
posible sistema rentable
```

Esto encaja especialmente bien con nuestro enfoque de SQX.

Podemos utilizar el protocolo del documento como punto de partida, pero ampliarlo con Monte Carlo, Synthetic Data y validación estadística.

El objetivo final sería disponer de un **auditor automático de estrategias SQX** que no premie simplemente estrategias con un Win Rate elevado, sino que determine si existe evidencia suficiente de que el edge es real, estable y resistente a las condiciones que pueden destruirlo.

La idea clave sería:

```text
NO BUSCAR LA ESTRATEGIA CON EL MEJOR BACKTEST.

BUSCAR LA ESTRATEGIA CUYO EDGE
SOBREVIVE A LOS INTENTOS DE DESTRUIRLO.
```
