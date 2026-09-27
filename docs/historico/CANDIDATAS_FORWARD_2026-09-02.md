# Candidatas Forward para poblar la Incubadora — 2026-09-02

Barrido de las carpetas `Forward` / `OOS-Forward` de todos los proyectos SQX, medido con
el mismo parser que usa el panel `SQX_vs_MT5`. **No escribe nada en SQX ni en la base.**

- Candidatas encontradas: **442** (433 legibles, 9 ilegibles)
- Elegibles por el criterio del prefiltro operacional: **333**

## Por qué el gate F4 completo daría cero

Con el gate de pipeline aplicado entero **no pasa ninguna de las 433**, y el único
criterio que las tumba es `pipeline_min_freq_week >= 2`: la mediana de frecuencia va de
0,53 a 0,95 operaciones por semana según el activo, y la mejor de todo el universo llega
a 1,95. No es que las estrategias sean malas — es que **este umbral no encaja con el
estilo minado**, que opera aproximadamente una vez por semana.

El prefiltro operacional ya lo contempla (`ASSUMPTIONS.md` G13-05): la frecuencia es una
advertencia de fiabilidad, no un veto aislado, y el mínimo absoluto son 30 trades. Las
cifras de abajo usan ese criterio: PF >= 1,5 · DD <= 20 % · >= 30 trades · >= 60 días.

## El cuello de botella: falta el `.mq5`

El inventario operacional exige `.sqx` **y** fuente MQL5 (G13-01). Las carpetas `Forward`
sólo contienen `.sqx`: el `.mq5` se genera exportando desde SQX, y su API remota no expone
esa operación. **Por eso el inventario actual sólo tiene AUDCAD**: es lo único exportado a
`EAs_SQX_guardados/Analisis/`.

## Universo elegible por grupo

| Símbolo / TF | Elegibles | Sin `.mq5` | Mejor PF | Mejor DD |
|---|---|---|---|---|
| AUDCAD_darwinex/H4 | 238 | 12 | 2.16 | 0.31 % |
| DAX40_darwinex/M30 | 52 | 52 | 2.17 | 1.66 % |
| XAUUSD_darwinex/H1 | 21 | 21 | 1.70 | 1.28 % |
| XAUUSD_darwinex/H4 | 20 | 20 | 2.19 | 0.81 % |
| NASDAQ_darwinex/H1 | 2 | 2 | 2.69 | 6.10 % |

## Qué exportar, por orden de prioridad

Las 5 mejores de cada grupo que **aún no tienen `.mq5`**, ordenadas por
NP/DD (rendimiento relativo al riesgo asumido, que penaliza el drawdown alto).

El tope de admisión a Incubadora es de 2 por símbolo/timeframe y 8 concurrentes, pero
conviene exportar 5 por grupo: la experiencia de esta campaña es que la mayoría
cae en la comparación SQX↔MT5 a tick real (de 6 comparadas, 2 VALIDADA y 4 no).

### AUDCAD_darwinex/H4 — 12 sin exportar, 5 seleccionadas

Proyecto: `Project_AUDCAD_H4_S_BS_ForexMinorLateral_capa1` · databank `Forward`

| Estrategia | PF | DD % | Net profit | Trades | Días | Op/sem |
|---|---|---|---|---|---|---|
| `Strategy 6.74.58.sqx` | 1.834 | 1.913 | 24,656 | 235 | 3220 | 0.51 |
| `Strategy 5.84.85.sqx` | 1.873 | 1.978 | 24,428 | 246 | 3192 | 0.54 |
| `Strategy 5.60.72.sqx` | 1.837 | 1.608 | 16,442 | 170 | 3192 | 0.37 |
| `Strategy 4.13.78.sqx` | 1.721 | 2.403 | 24,135 | 253 | 3198 | 0.55 |
| `Strategy 5.72.64.sqx` | 1.931 | 2.762 | 25,784 | 237 | 3192 | 0.52 |

### DAX40_darwinex/M30 — 52 sin exportar, 5 seleccionadas

Proyecto: `Project_DAX40_M30_BreakoutStop_EOD_ORB_L_SesionManana` · databank `FORWARD`

| Estrategia | PF | DD % | Net profit | Trades | Días | Op/sem |
|---|---|---|---|---|---|---|
| `Strategy 4.5.178.sqx` | 2.063 | 2.201 | 37,789 | 189 | 1644 | 0.8 |
| `WF Matrix - Strategy 2.29.90.sqx` | 2.173 | 1.997 | 29,056 | 175 | 1656 | 0.74 |
| `Strategy 5.9.112.sqx` | 1.734 | 3.436 | 49,038 | 175 | 1644 | 0.75 |
| `WF Matrix - Strategy 4.5.178.sqx` | 1.952 | 3.091 | 44,109 | 189 | 1644 | 0.8 |
| `WF Matrix - Strategy 4.36.83.sqx` | 2.053 | 3.284 | 44,070 | 192 | 1652 | 0.81 |

### XAUUSD_darwinex/H1 — 21 sin exportar, 5 seleccionadas

Proyecto: `XAUUSD_H1_Reemplazo2_KER_LinReg_noTP_EOD` · databank `Forward`

| Estrategia | PF | DD % | Net profit | Trades | Días | Op/sem |
|---|---|---|---|---|---|---|
| `Strategy 1.33.66.sqx` | 1.537 | 2.075 | 22,286 | 350 | 3139 | 0.78 |
| `Strategy 6.1.50.sqx` | 1.549 | 1.95 | 20,084 | 332 | 3139 | 0.74 |
| `Strategy 5.87.89.sqx` | 1.592 | 1.812 | 16,536 | 344 | 3138 | 0.77 |
| `Strategy 4.2.53.sqx` | 1.577 | 1.434 | 12,467 | 352 | 3138 | 0.79 |
| `Strategy 6.38.97.sqx` | 1.695 | 1.28 | 11,057 | 293 | 3138 | 0.65 |

### XAUUSD_darwinex/H4 — 20 sin exportar, 5 seleccionadas

Proyecto: `Project_XAUUSD_H4_BreakoutStop_v7_L_DiaEntero ( copia para trabajo )` · databank `FORWARD`

| Estrategia | PF | DD % | Net profit | Trades | Días | Op/sem |
|---|---|---|---|---|---|---|
| `Strategy 4.41.55.sqx` | 2.185 | 1.591 | 29,258 | 265 | 3138 | 0.59 |
| `Strategy 6.15.79.sqx` | 1.894 | 1.557 | 26,773 | 277 | 3138 | 0.62 |
| `Strategy 3.47.68.sqx` | 1.536 | 1.492 | 24,449 | 457 | 3139 | 1.02 |
| `Strategy 7.18.60.sqx` | 1.671 | 1.293 | 19,380 | 388 | 3138 | 0.87 |
| `Strategy 4.28.77.sqx` | 1.824 | 1.906 | 27,557 | 351 | 3139 | 0.78 |

### NASDAQ_darwinex/H1 — 2 sin exportar, 2 seleccionadas

Proyecto: `Project_NASDAQ_H1_BS_LaCity_L_CapaMixta` · databank `Forward`

| Estrategia | PF | DD % | Net profit | Trades | Días | Op/sem |
|---|---|---|---|---|---|---|
| `NASDAQH1_L_City_7.13.185.sqx` | 2.689 | 7.23 | 124,244 | 243 | 2792 | 0.61 |
| `NASDAQ_H1_L_LinReg_Strategy 0.511016.sqx` | 1.532 | 6.099 | 47,952 | 182 | 2812 | 0.45 |

## Cómo exportarlas

En SQX, abre el proyecto, ve al databank `Forward`, selecciona las estrategias de la tabla
y usa **Export → MQL5 Expert Advisor**. Deja cada lote en:

```
C:\BOTS\Versiones\SQX_144_Full2\EAs_SQX_guardados\Analisis\<proyecto>\Forward_finalistas
```

con el `.sqx` y el `.mq5` juntos, como están las de AUDCAD. En cuanto estén ahí:

```
python scripts/operational_inventory.py   # inventaría y valida símbolo/timeframe/magic
python scripts/operational_prefilter.py   # aplica umbrales, MC y costes
```

y de ahí a la comparación SQX↔MT5 a tick real. Sólo un veredicto `VALIDADA` llega a
`BACKTEST_VALIDATED`, que es el único estado que puede optar a la Incubadora.

## Lo que sigue faltando para poblarla de verdad

El gate de admisión con los dos criterios de descorrelación está construido y probado
(`core/services/incubator_admission.py`, 13 tests) pero **nadie lo llama todavía**, y el
**adjunto demo por gráfico no existe** (`backlog` A20/A21). Aunque hoy hubiera una
candidata `BACKTEST_VALIDATED`, no habría por dónde meterla en la Incubadora.
