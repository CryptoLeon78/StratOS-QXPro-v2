# Strategy Robustness Auditor (SRA)

## Especificación Formal de Proyecto

**Proyecto:** SQX Analyzer Pro  
**Módulo:** Strategy Robustness Auditor  
**Identificador:** SRA  
**Tipo:** Módulo de auditoría y validación de estrategias  
**Estado:** Especificación inicial / Diseño técnico  
**Versión:** 1.0  
**Fecha:** 2026-08-22

---

# 1. Resumen ejecutivo

Strategy Robustness Auditor (SRA) será un módulo de auditoría automática de estrategias de trading diseñado para integrarse en el ecosistema de **SQX Analyzer Pro**.

Su objetivo no será optimizar estrategias ni buscar el mejor backtest.

Su objetivo será determinar:

> **Cuánto podemos confiar en que el edge observado en una estrategia no sea simplemente consecuencia de sobreajuste, costes irreales, gestión de posiciones, condiciones particulares del histórico o azar estadístico.**

El módulo analizará una estrategia mediante una batería de filtros independientes y producirá:

- Resultados individuales por filtro.
- Métricas cuantitativas.
- Advertencias.
- Fallos críticos.
- Calidad de los datos.
- Puntuación global.
- Veredicto final.
- Informe HTML.
- Informe PDF.
- Exportación CSV.
- Exportación JSON.

La filosofía fundamental del módulo será:

```text
NO BUSCAR LA ESTRATEGIA CON EL MEJOR BACKTEST.

BUSCAR LA ESTRATEGIA CUYO EDGE
SOBREVIVE A LOS INTENTOS DE DESTRUIRLO.
```

---

# 2. Problema que resuelve

Un backtest puede presentar resultados aparentemente excelentes sin que exista evidencia suficiente de robustez.

Ejemplos:

- Win Rate artificialmente elevado.
- Beneficios obtenidos solamente en condiciones históricas concretas.
- Sensibilidad extrema a un parámetro.
- Dependencia excesiva de costes ideales.
- Degradación severa fuera de muestra.
- Drawdown real mucho mayor bajo Monte Carlo.
- Distribuciones sintéticas incompatibles con los resultados originales.
- Estadísticas insuficientes.
- Cierres parciales que hacen parecer ganadoras operaciones que finalmente no lo son.

Por tanto:

```text
Win Rate alto
        ≠
Estrategia robusta
```

El SRA deberá analizar la estrategia como un sistema completo:

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
OOS
     ↓
ROBUSTEZ
     ↓
MONTE CARLO
     ↓
SYNTHETIC DATA
     ↓
VALIDACIÓN ESTADÍSTICA
     ↓
VEREDICTO
```

---

# 3. Objetivos

## 3.1. Objetivo principal

Determinar si una estrategia presenta evidencia suficiente de robustez y viabilidad estadística.

## 3.2. Objetivos secundarios

El módulo deberá:

1. Evitar que el Win Rate sea utilizado como criterio principal.
2. Calcular correctamente el break-even.
3. Medir la expectativa matemática.
4. Detectar sensibilidad a costes.
5. Detectar posible inflación del Win Rate mediante parciales.
6. Analizar tamaño y calidad de la muestra.
7. Evaluar OOS.
8. Medir degradación IS → OOS.
9. Evaluar robustez paramétrica.
10. Consumir resultados de Monte Carlo.
11. Consumir resultados de Synthetic Data.
12. Integrarse con `BootstrapValidator`.
13. Utilizar KS, ACF y Ljung-Box cuando exista evidencia suficiente.
14. Diferenciar entre fallo y ausencia de evidencia.
15. Generar un veredicto explicable.
16. Generar informes reutilizables por otras aplicaciones.

---

# 4. No objetivos

El SRA inicialmente **NO** deberá:

- Optimizar parámetros.
- Generar estrategias.
- Modificar la estrategia auditada.
- Elegir automáticamente la mejor combinación de parámetros.
- Sustituir al backtester de SQX.
- Fabricar datos estadísticos cuando no existan.
- Convertir datos faltantes en PASS.
- Utilizar OOS para optimizar.
- Utilizar Win Rate como criterio único.

---

# 5. Filosofía de validación

El módulo deberá actuar como un sistema adversarial.

No debe preguntar:

```text
¿La estrategia parece buena?
```

Debe preguntar:

```text
¿Qué ocurre si intento romperla?
```

Los principales mecanismos de ataque serán:

```text
Costes mayores
OOS
Variación de parámetros
Monte Carlo
Datos sintéticos
Pruebas estadísticas
Análisis de parciales
```

Una estrategia que sobrevive a varios ataques independientes tendrá una evidencia de robustez superior a una estrategia que solamente presenta un backtest espectacular.

---

# 6. Estados globales

El SRA deberá poder producir los siguientes estados:

```text
ROBUST
PROMISING
FRAGILE
FAIL
INSUFFICIENT_DATA
```

## ROBUST

La estrategia supera los filtros principales sin fallos críticos y presenta evidencia consistente de estabilidad.

## PROMISING

La estrategia presenta resultados interesantes pero existen advertencias o áreas que requieren revisión.

## FRAGILE

La estrategia presenta un edge aparente, pero depende demasiado de parámetros, costes, condiciones o supuestos concretos.

## FAIL

Existe evidencia clara de que la estrategia no supera uno o más criterios críticos.

## INSUFFICIENT_DATA

No existe evidencia suficiente para emitir un veredicto fiable.

---

# 7. Estados de cada filtro

Cada filtro tendrá:

```java
enum AuditStatus {
    PASS,
    WARNING,
    FAIL,
    INSUFFICIENT_DATA,
    NOT_APPLICABLE
}
```

---

# 8. Estado de calidad de datos

Todo resultado estadístico deberá incluir:

```java
enum DataStatus {
    VALID,
    INSUFFICIENT,
    INVALID,
    MISSING
}
```

Regla fundamental:

```text
MISSING
    ≠
FAIL

MISSING
    ≠
PASS
```

La ausencia de evidencia deberá permanecer explícitamente identificada.

---

# 9. Arquitectura general

```text
StrategyRobustnessAuditor
│
├── StrategyInput
│
├── MetricsEngine
│
├── PartialProfitAnalyzer
│
├── BreakEvenAnalyzer
│
├── CostSensitivityAnalyzer
│
├── SampleAnalyzer
│
├── OOSAnalyzer
│
├── DegradationAnalyzer
│
├── ParameterRobustnessAnalyzer
│
├── MonteCarloAnalyzer
│
├── SyntheticDataAnalyzer
│
├── StatisticalValidator
│
├── VerdictEngine
│
└── ReportGenerator
```

---

# 10. Flujo de ejecución

```text
SQX Strategy
     │
     ▼
INPUT VALIDATION
     │
     ▼
BASIC METRICS
     │
     ▼
PARTIAL PROFIT ANALYSIS
     │
     ▼
BREAK-EVEN
     │
     ▼
COST SENSITIVITY
     │
     ▼
SAMPLE SIZE
     │
     ▼
OOS
     │
     ▼
IS/OOS DEGRADATION
     │
     ▼
PARAMETER ROBUSTNESS
     │
     ▼
MONTE CARLO
     │
     ▼
SYNTHETIC DATA
     │
     ▼
STATISTICAL VALIDATION
     │
     ▼
VERDICT ENGINE
     │
     ▼
FINAL REPORT
```

---

# 11. Modelo de datos principal

## 11.1. AuditContext

```java
class AuditContext {

    StrategyInput strategy;

    AuditThresholds thresholds;

    MetricsSnapshot metrics;

    PartialProfitResult partialProfit;

    OOSResult oos;

    CostSensitivityResult costs;

    ParameterRobustnessResult parameters;

    MonteCarloResult monteCarlo;

    SyntheticValidationResult synthetic;

    BootstrapValidationResult statistics;
}
```

---

# 12. AuditResult

```java
class AuditResult {

    String filterId;

    String filterName;

    AuditStatus status;

    double score;

    String summary;

    DataStatus dataStatus;

    List<AuditFinding> findings;

    Map<String, Double> metrics;
}
```

---

# 13. AuditFinding

```java
class AuditFinding {

    Severity severity;

    String code;

    String message;

    String recommendation;
}
```

---

# 14. Threshold configuration

Los umbrales deberán ser configurables.

Ejemplo:

```text
Minimum Trades             300
Minimum Synthetic Returns  500
Break-even Margin          15 pp
Max OOS Degradation        40%
Cost Scenarios             +25/+50/+75/+100%
Parameter Range            ±20%
KS Alpha                   5%
Minimum MC Simulations     1000
```

No deberán estar hardcoded en las clases de análisis.

---

# 15. Filtro 0 — Input Validation

## Objetivo

Comprobar que la estrategia dispone de los datos mínimos necesarios.

## Datos

- Trades.
- Fechas.
- PnL.
- Entrada.
- Salida.
- Position size.
- Costes.
- Parámetros.
- IS/OOS.
- Monte Carlo.
- Synthetic Data.

## Resultado

```text
VALID
PARTIAL
INVALID
```

Ejemplo:

```text
WARNING:
Synthetic returns unavailable.

Monte Carlo unavailable.

Audit can continue, but final confidence
will be limited.
```

---

# 16. Filtro 1 — Profitability Sanity Check

## Objetivo

Determinar si la estrategia tiene una expectativa económica positiva.

## Métricas

```text
Total Trades
Winning Trades
Losing Trades
Win Rate
Loss Rate
Average Win
Average Loss
Payoff
Gross Profit
Gross Loss
Net Profit
Profit Factor
Expectancy
Net Expectancy
```

## Fórmulas

```text
WinRate =
WinningTrades / TotalTrades

LossRate =
LosingTrades / TotalTrades

Payoff =
AverageWin / AverageLoss

Expectancy =
WinRate × AverageWin
-
LossRate × AverageLoss
```

Con costes:

```text
NetExpectancy =
GrossExpectancy - AverageCostPerTrade
```

## Regla crítica

Si:

```text
Profit Factor <= 1
```

o:

```text
Net Expectancy <= 0
```

la estrategia no puede ser clasificada como ROBUST.

---

# 17. Filtro transversal — Partial Profit Analyzer

Este componente deberá detectar posibles distorsiones provocadas por cierres parciales.

## Métricas

```text
TP1 Win Rate
TP2 Win Rate
TP3 Win Rate
True Trade Win Rate
TP1 Inflation
```

## Fórmula

```text
TP1 Inflation =
TP1 Win Rate - True Trade Win Rate
```

## Clasificación inicial

```text
< 5 pp        LOW
5–10 pp       MODERATE
10–20 pp      HIGH
> 20 pp       CRITICAL
```

## Ejemplo

```text
TP1 Win Rate       79.1%
Final Win Rate     53.4%

Difference         25.7 pp

STATUS: CRITICAL
```

## Finding

```text
Code:
PARTIAL_WINRATE_INFLATION

Severity:
HIGH

Message:
TP1 Win Rate exceeds final Trade Win Rate significantly.

Recommendation:
Evaluate the strategy using final trade outcomes.
```

Este análisis no deberá cambiar los resultados reales del backtest; solamente debe revelar cómo las estadísticas pueden ser interpretadas incorrectamente.

---

# 18. Filtro 2 — Break-even

## Objetivo

Determinar cuánto Win Rate necesita la estrategia para alcanzar el equilibrio.

## Fórmula

```text
BreakEvenWR =
AverageLoss /
(AverageWin + AverageLoss)
```

Equivalente:

```text
BreakEvenWR =
1 / (1 + Payoff)
```

## Margen

```text
Margin =
ActualWinRate - BreakEvenWinRate
```

## Umbral inicial

```text
PASS
Margin >= 15 pp

WARNING
Margin >= 10 pp

FAIL
Margin < 10 pp
```

Los valores deberán ser configurables.

---

# 19. Filtro 3 — Cost Sensitivity

## Objetivo

Medir cuánto margen tiene el edge ante costes superiores a los utilizados en el backtest.

## Escenarios

```text
BASE
+25%
+50%
+75%
+100%
```

## Métricas

Para cada escenario:

```text
Net Profit
Profit Factor
Expectancy
Drawdown
Average Trade
```

## Ejemplo

```text
Scenario       PF       DD       Expectancy

BASE           1.62     12.4%     +0.27R
+25%           1.51     13.1%     +0.24R
+50%           1.39     14.0%     +0.21R
+75%           1.24     15.6%     +0.17R
+100%          1.08     17.2%     +0.11R
```

El módulo deberá calcular un indicador de supervivencia de costes.

---

# 20. Filtro 4 — Sample Size

## Objetivo

Evaluar la calidad de la muestra y no únicamente el número bruto de operaciones.

## Variables

```text
Total Trades
Trades/Year
Trades/Month
Years
Market Regimes
Longest Inactivity Period
```

También podrá utilizar:

```text
Confidence Interval
```

## Regla

El valor de 300 operaciones será un umbral configurable, no una ley universal.

La calidad de muestra deberá considerar el contexto temporal y de mercado.

---

# 21. Filtro 5 — OOS

## Objetivo

Validar la estrategia sobre datos no utilizados durante el desarrollo.

## Separación

```text
IN-SAMPLE
    ↓
Development
    ↓
Strategy Frozen
    ↓
OUT-OF-SAMPLE
    ↓
Validation
```

## Métricas

```text
IS PF
OOS PF

IS Expectancy
OOS Expectancy

IS Drawdown
OOS Drawdown

IS Win Rate
OOS Win Rate

IS Trades
OOS Trades
```

El OOS no podrá utilizarse para optimización.

---

# 22. Filtro 6 — IS/OOS Degradation

## Objetivo

Cuantificar la pérdida de rendimiento fuera de muestra.

Para métricas donde mayor sea mejor:

```text
Degradation =
1 - OOSMetric / ISMetric
```

Ejemplo:

```text
IS PF       1.83
OOS PF      1.21

Degradation = 33.9%
```

Para métricas donde menor sea mejor, como Drawdown, deberá utilizarse una fórmula específica que respete la dirección de la métrica.

## Clasificación

```text
LOW
MODERATE
HIGH
CRITICAL
```

Los thresholds deberán ser configurables.

---

# 23. Filtro 7 — Parameter Robustness

## Objetivo

Comprobar que la estrategia no depende de un único valor exacto.

## Robustez local

Cada parámetro se probará alrededor de su valor original:

```text
-20%
-15%
-10%
-5%
0
+5%
+10%
+15%
+20%
```

## Robustez combinada

Opcionalmente se podrán variar varios parámetros simultáneamente.

Ejemplo:

```text
EMA
RSI
ATR
BB Period
BB Deviation
```

La robustez combinada tendrá un coste computacional mayor.

---

# 24. Plateau Analysis

El objetivo no será encontrar el máximo PF.

Será encontrar una zona estable.

Una estrategia será más interesante si existe una meseta:

```text
PF
│
│    ┌──────────┐
│   /            \
│  /              \
└──────────────────────
```

que si presenta un único pico:

```text
PF
│
│       X
│      / \
│     /   \
└──────────────────────
```

El módulo deberá calcular, cuando sea posible:

```text
Plateau Width
Plateau Density
Median Performance
Worst Neighbor Performance
```

---

# 25. Filtro 8 — Monte Carlo

## Objetivo

Determinar la sensibilidad del sistema a diferentes secuencias y escenarios estadísticos.

## Datos

```text
Simulation Count
Return Distribution
Equity Distribution
Drawdown Distribution
Profit Factor Distribution
```

## Percentiles

```text
P05
P25
P50
P75
P95
```

## Ejemplo

```text
Monte Carlo Drawdown

P05       8.1%
P25      11.7%
P50      15.2%
P75      20.8%
P95      31.4%
```

Se deberán registrar además:

```text
Probability of Loss
Probability of Ruin
Probability PF < 1
Maximum Drawdown Percentiles
```

cuando dichos datos estén disponibles.

---

# 26. Filtro 9 — Synthetic Data

## Objetivo

Comprobar si las propiedades fundamentales de la estrategia sobreviven sobre datos sintéticos.

## Pipeline

```text
Real Returns
     ↓
Synthetic Generator
     ↓
N Simulations
     ↓
Synthetic Returns
     ↓
BootstrapValidator
```

## Minimum data

Antes de realizar pruebas:

```text
syntheticCount >= minimumRequired
```

Si no:

```text
INSUFFICIENT_DATA
```

Nunca deberán fabricarse valores estadísticos para permitir el PASS.

---

# 27. Integración con BootstrapValidator

El SRA deberá reutilizar la lógica estadística existente siempre que sea posible.

Resultado esperado:

```java
class BootstrapValidationResult {

    double ksStatistic;
    double ksPValue;

    double acfSimilarity;
    double ljungBoxPValue;

    int realReturns;
    int syntheticReturns;

    boolean sufficientData;

    boolean ksPass;
    boolean acfPass;
    boolean ljungBoxPass;

    boolean overallPass;
}
```

El SRA consumirá este resultado.

No deberá duplicar innecesariamente el cálculo de KS, ACF o Ljung-Box.

---

# 28. Filtro 10 — Statistical Validation

## Tests iniciales

```text
Kolmogorov-Smirnov
ACF
Ljung-Box
```

## Cada resultado deberá incluir

```text
Statistic
P-value
Threshold
PASS/FAIL
Data Count
Data Status
```

Ejemplo:

```text
KS

Statistic       0.082
P-value         0.214
Alpha           0.05

PASS
```

---

# 29. Integridad estadística

Regla obligatoria:

```text
Insufficient Data
        ↓
No statistical verdict
```

Nunca:

```text
0 returns
    ↓
KS = 0
    ↓
PASS
```

ni:

```text
Empty list
    ↓
ACF = 0
    ↓
PASS
```

ni:

```text
Missing result
    ↓
Default value
    ↓
PASS
```

Los datos insuficientes deben producir:

```text
INSUFFICIENT_DATA
```

---

# 30. Verdict Engine

El `VerdictEngine` será responsable del resultado final.

No deberá limitarse a contar cuántos filtros han pasado.

Deberá aplicar reglas de veto.

---

# 31. Critical Failures

Ejemplos de veto:

```text
Profit Factor <= 1
        → FAIL

Net Expectancy <= 0
        → FAIL

OOS Profit Factor <= 1
        → FAIL

Catastrophic Monte Carlo
        → FAIL

Critical robustness failure
        → FAIL
```

Estos thresholds deberán ser configurables.

---

# 32. Score global

El score estará entre:

```text
0–100
```

Clasificación:

```text
95–100    EXCELLENT
85–94     HIGH
70–84     GOOD
55–69     MODERATE
40–54     WEAK
0–39      FRAGILE
```

El score nunca podrá anular un fallo crítico.

Ejemplo:

```text
Score: 91/100

Critical failures: 1

Verdict: FAIL

Reason:
OOS Profit Factor < 1
```

---

# 33. Data Confidence

Además del score de robustez deberá existir un indicador separado de confianza de datos.

Ejemplo:

```text
Robustness Score: 84
Data Confidence: 96
```

Otra estrategia podría tener:

```text
Robustness Score: 87
Data Confidence: 51
```

En este segundo caso el resultado global no debería ser considerado plenamente ROBUST.

---

# 34. Findings y recomendaciones

Cada alerta deberá ser interpretable.

Ejemplo:

```text
Code:
COST_SENSITIVITY_HIGH

Severity:
HIGH

Message:
Profit Factor falls from 1.62 to 1.08
under a +100% cost scenario.

Recommendation:
Review spread, commission and slippage assumptions.
```

Otro:

```text
Code:
OOS_DEGRADATION_HIGH

Severity:
HIGH

Message:
OOS Profit Factor is 38% below IS Profit Factor.

Recommendation:
Review parameter dependency and possible overfitting.
```

---

# 35. Informe HTML

## Portada

```text
STRATEGY ROBUSTNESS AUDITOR

Strategy:
EURUSD_MeanReversion_017

Overall Score:
82 / 100

Verdict:
PROMISING
```

## Resumen

```text
✓ Profitability
✓ Break-even
✓ Costs
✓ Sample
✓ OOS
⚠ Degradation
✓ Parameters
✓ Monte Carlo
⚠ Synthetic
✓ Statistics
```

## Secciones

1. Executive Summary.
2. Strategy Information.
3. Core Metrics.
4. Partial Profit Analysis.
5. Break-even.
6. Cost Sensitivity.
7. Sample Analysis.
8. OOS.
9. IS/OOS Degradation.
10. Parameter Robustness.
11. Monte Carlo.
12. Synthetic Data.
13. Statistical Validation.
14. Findings.
15. Final Verdict.

---

# 36. Informe PDF

El PDF deberá contener:

1. Identificación de estrategia.
2. Resumen ejecutivo.
3. Métricas principales.
4. Resultado de los 10 filtros.
5. Alertas.
6. Monte Carlo.
7. Robustez paramétrica.
8. Synthetic Data.
9. Validación estadística.
10. Veredicto final.
11. Justificación del veredicto.

Se deberá incluir una sección:

## Why this strategy passed/failed

Ejemplo:

```text
WHY THIS STRATEGY FAILED

1. OOS PF = 0.87
2. Cost +50% reduces PF below 1
3. Parameter robustness is fragile
4. Monte Carlo P95 drawdown = 42%
```

---

# 37. Exportaciones

El módulo deberá soportar:

```text
HTML
PDF
CSV
JSON
```

El JSON deberá permitir integración posterior con otras aplicaciones.

Ejemplo:

```json
{
  "strategy": "EURUSD_MeanReversion_017",
  "score": 82,
  "dataConfidence": 96,
  "verdict": "PROMISING",
  "filters": {
    "profitability": "PASS",
    "breakEven": "PASS",
    "costs": "PASS",
    "sample": "PASS",
    "oos": "PASS",
    "degradation": "WARNING",
    "parameters": "PASS",
    "monteCarlo": "PASS",
    "synthetic": "WARNING",
    "statistics": "PASS"
  }
}
```

---

# 38. Arquitectura de paquetes

Propuesta:

```text
strategyrobustness/
│
├── StrategyRobustnessAuditor.java
│
├── core/
│   ├── AuditContext.java
│   ├── AuditResult.java
│   ├── AuditFinding.java
│   ├── AuditStatus.java
│   ├── DataStatus.java
│   ├── Severity.java
│   └── AuditThresholds.java
│
├── input/
│   └── StrategyInput.java
│
├── metrics/
│   ├── MetricsEngine.java
│   ├── MetricsSnapshot.java
│   └── ExpectancyAnalyzer.java
│
├── filters/
│   ├── ProfitabilityFilter.java
│   ├── BreakEvenFilter.java
│   ├── CostSensitivityFilter.java
│   ├── SampleSizeFilter.java
│   ├── OOSFilter.java
│   ├── DegradationFilter.java
│   ├── ParameterRobustnessFilter.java
│   ├── MonteCarloFilter.java
│   ├── SyntheticDataFilter.java
│   └── StatisticalFilter.java
│
├── analysis/
│   ├── PartialProfitAnalyzer.java
│   ├── CostAnalyzer.java
│   ├── RobustnessAnalyzer.java
│   └── DegradationAnalyzer.java
│
├── montecarlo/
│   └── MonteCarloResultAdapter.java
│
├── synthetic/
│   └── SyntheticValidationAdapter.java
│
├── statistics/
│   └── BootstrapValidationAdapter.java
│
├── verdict/
│   └── VerdictEngine.java
│
└── report/
    ├── HtmlReportGenerator.java
    ├── PdfReportGenerator.java
    ├── CsvExporter.java
    └── JsonExporter.java
```

---

# 39. Integración con SQX

El módulo deberá utilizar la estrategia recibida por SQX y adaptarla a un modelo interno:

```text
SQX Strategy
      ↓
StrategyInput
      ↓
AuditContext
      ↓
Filters
      ↓
Verdict
```

El módulo no deberá modificar la estrategia original.

---

# 40. Compatibilidad con SQX GRID

El punto de entrada deberá ser defensivo.

Ejemplo conceptual:

```java
filterStrategy(...)
```

deberá estar protegido contra excepciones.

Una excepción del auditor:

```text
NO debe propagarse
```

para provocar un fallo del GRID.

En caso de error:

```text
AuditStatus = WARNING
```

o:

```text
AuditStatus = INSUFFICIENT_DATA
```

según el contexto.

Además deberá registrarse:

```text
[SRA] audit failed safely
strategy=XYZ
reason=...
```

---

# 41. Logging

Durante desarrollo se utilizarán logs detallados.

Formato:

```text
[SRA] strategy=XYZ
[SRA] trades=842
[SRA] PF=1.54
[SRA] expectancy=0.23
[SRA] breakEvenWR=38.4
[SRA] actualWR=57.1
[SRA] breakEvenMargin=18.7
[SRA] costSensitivity=PASS
[SRA] OOS PF=1.31
[SRA] degradation=14.9
[SRA] MC simulations=5000
[SRA] syntheticReturns=742
[SRA] KS p=0.214
[SRA] ACF similarity=0.91
[SRA] LjungBox p=0.38
[SRA] FINAL=ROBUST
```

Una vez estabilizado, se reducirá el nivel de logging.

---

# 42. Fases de implementación

## Fase 1 — Core MVP

Implementar:

```text
AuditContext
AuditResult
AuditFinding
AuditThresholds
VerdictEngine
```

Filtros:

```text
Profitability
Break-even
Sample Size
```

---

## Fase 2 — Execution & OOS

Añadir:

```text
Partial Profit Analyzer
Cost Sensitivity
OOS
IS/OOS Degradation
```

---

## Fase 3 — Robustness

Añadir:

```text
Parameter Robustness
Monte Carlo
```

---

## Fase 4 — Synthetic & Statistics

Integrar:

```text
Synthetic Data
BootstrapValidator
KS
ACF
Ljung-Box
```

---

## Fase 5 — Reporting

Implementar:

```text
HTML
PDF
CSV
JSON
```

---

# 43. MVP funcional

El primer MVP deberá incluir:

```text
1. Profitability
2. Break-even
3. Partial Profit Detection
4. Cost Sensitivity
5. Sample Size
6. OOS
7. IS/OOS Degradation
```

La segunda etapa añadirá:

```text
8. Parameter Robustness
9. Monte Carlo
10. Synthetic + Statistical Validation
```

---

# 44. Criterios de aceptación

El MVP se considerará funcional cuando:

- Pueda recibir una estrategia SQX.
- Calcule métricas básicas correctamente.
- Calcule Break-even.
- Detecte inflación de Win Rate por parciales cuando existan datos suficientes.
- Ejecute escenarios de costes.
- Diferencie IS y OOS.
- Calcule degradación.
- Genere resultados independientes por filtro.
- Produzca PASS/WARNING/FAIL/INSUFFICIENT_DATA.
- No convierta datos faltantes en PASS.
- No rompa SQX GRID ante excepciones.
- Genere un veredicto explicable.
- Genere JSON.
- Genere un informe HTML básico.

---

# 45. Reglas de diseño críticas

## Regla 1

**Nunca utilizar Win Rate como criterio primario.**

## Regla 2

**Nunca fabricar estadísticas cuando no existen datos.**

## Regla 3

**Nunca utilizar OOS para optimización.**

## Regla 4

**Nunca confundir TP1 alcanzado con trade ganador.**

## Regla 5

**Un score alto no puede ocultar un fallo crítico.**

## Regla 6

**Los thresholds deben ser configurables.**

## Regla 7

**Los módulos estadísticos deben declarar la calidad y cantidad de datos utilizados.**

## Regla 8

**El auditor no modifica la estrategia.**

## Regla 9

**El auditor debe intentar encontrar debilidades, no confirmar una hipótesis.**

## Regla 10

**La ausencia de evidencia debe ser explícita.**

---

# 46. Resultado esperado

Ejemplo de resultado final:

```text
╔════════════════════════════════════╗
║        STRATEGY ROBUSTNESS         ║
║              AUDITOR               ║
╠════════════════════════════════════╣
║ Strategy: EURUSD_MR_017            ║
║                                    ║
║ Score:          84 / 100           ║
║ Data Confidence: 96 / 100          ║
║                                    ║
║ Verdict: PROMISING                 ║
╠════════════════════════════════════╣
║ Profitability       PASS            ║
║ Break-even          PASS            ║
║ Partial Analysis    PASS            ║
║ Costs               PASS            ║
║ Sample              PASS            ║
║ OOS                 PASS            ║
║ Degradation         WARNING         ║
║ Parameters          PASS            ║
║ Monte Carlo         PASS            ║
║ Synthetic Data      WARNING         ║
║ Statistics          PASS            ║
╚════════════════════════════════════╝
```

---

# 47. Principio final del proyecto

El SRA no pretende demostrar que una estrategia vaya a ganar dinero en el futuro.

Ningún protocolo serio puede garantizar eso.

Su función es mucho más concreta:

> **Reducir la probabilidad de aceptar estrategias cuyo rendimiento depende de condiciones frágiles, errores estadísticos, costes irreales, sobreoptimización, secuencias favorables o una interpretación engañosa de sus resultados.**

La filosofía final será:

```text
BACKTEST
   ↓
¿Parece buena?
   ↓
INTENTAR ROMPERLA
   ↓
COSTES
OOS
PARÁMETROS
MONTE CARLO
SYNTHETIC DATA
ESTADÍSTICA
   ↓
¿SOBREVIVE?
   ↓
SÍ ───────────────→ EVIDENCIA DE ROBUSTEZ
NO ───────────────→ RECHAZAR / REVISAR
```

Y la regla conceptual que debe guiar todo el desarrollo será:

```text
NO BUSCAMOS EL MEJOR BACKTEST.

BUSCAMOS EL EDGE QUE SOBREVIVE
A LOS INTENTOS DE DESTRUIRLO.
```

---

# 48. Próximo paso técnico recomendado

La implementación debería comenzar por el **Core MVP**, no por Monte Carlo ni Synthetic Data.

Orden recomendado:

```text
AuditContext
     ↓
AuditResult
     ↓
AuditThresholds
     ↓
ProfitabilityFilter
     ↓
BreakEvenFilter
     ↓
SampleSizeFilter
     ↓
PartialProfitAnalyzer
     ↓
CostSensitivityFilter
     ↓
OOSFilter
     ↓
DegradationFilter
     ↓
VerdictEngine
```

Una vez estable esta capa, se conectarán:

```text
Parameter Robustness
        ↓
Monte Carlo
        ↓
Synthetic Data
        ↓
BootstrapValidator
        ↓
KS / ACF / Ljung-Box
```

Esto reduce el riesgo de construir un sistema grande antes de haber validado correctamente su núcleo.
