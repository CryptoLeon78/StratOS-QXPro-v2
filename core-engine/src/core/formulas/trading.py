"""PARTE 8: metricas de trade/baseline individuales.

win_rate_drift/payoff_ratio/avg_trade_duration/calmar_ratio/ulcer_index/
recovery_factor (G10, docs/backlog.md): no son formulas contractuales de
PARTE 8 -- son definiciones estandar de la industria de trading (payoff
ratio, Calmar ratio, Ulcer Index, Recovery Factor), sin umbral de negocio
que decidir (a diferencia de `state_machines/`)."""

from datetime import timedelta
from decimal import Decimal

import numpy as np

# PARTE 8: "gross_loss==0 y profit>0 -> inf (cap visual 99)" -- constante de
# convencion de visualizacion citada literalmente en la spec (P11: excepcion
# de constante matematica pura nombrada, no un umbral de negocio).
PROFIT_FACTOR_DISPLAY_CAP = 99.0


def r_multiple(
    profit_net: Decimal,
    entry: Decimal,
    sl: Decimal | None,
    volume: Decimal,
    tick_value: Decimal,
    tick_size: Decimal,
) -> Decimal | None:
    """riesgo_inicial = |entry-sl|/tick_size*tick_value*volume; sl None o
    riesgo 0 -> None (r_multiple NULL, PARTE 8)."""
    if sl is None:
        return None
    risk = abs(entry - sl) / tick_size * tick_value * volume
    if risk == 0:
        return None
    return profit_net / risk


def r_multiple_net_of_costs(
    profit: Decimal,
    commission: Decimal,
    swap: Decimal,
    entry: Decimal,
    sl: Decimal | None,
    volume: Decimal,
    tick_value: Decimal,
    tick_size: Decimal,
) -> Decimal | None:
    """G10: envoltorio de `r_multiple()` con `profit_net = profit +
    commission + swap` (comision/swap ya llevan su propio signo en
    `Trade`, negativos si son coste) -- PARTE 8 no fija esta suma a nivel
    de trade individual; decision propia documentada en ASSUMPTIONS G10.
    Unica fuente de esta convencion: reutilizada tal cual por
    `core/ingest/services/trades.py` y `scripts/backfill_r_multiple.py`."""
    return r_multiple(
        profit_net=profit + commission + swap,
        entry=entry,
        sl=sl,
        volume=volume,
        tick_value=tick_value,
        tick_size=tick_size,
    )


def expectancy_r(r_multiples: list[Decimal]) -> float:
    """Media; ventana vacia -> ValueError (PARTE 8)."""
    if not r_multiples:
        raise ValueError("expectancy_r: ventana vacia")
    return float(sum(r_multiples) / len(r_multiples))


def rolling_profit_factor(profits: list[Decimal], window: int) -> float | None:
    """gross_loss==0 y profit>0 -> inf (cap visual 99); ambos 0 -> None
    (PARTE 8). Toma los ultimos `window` elementos disponibles."""
    recent = profits[-window:] if profits else []
    gross_profit = sum((p for p in recent if p > 0), start=Decimal("0"))
    gross_loss = -sum((p for p in recent if p < 0), start=Decimal("0"))
    if gross_loss == 0:
        return PROFIT_FACTOR_DISPLAY_CAP if gross_profit > 0 else None
    return float(gross_profit / gross_loss)


def loss_streak(r_multiples: list[Decimal]) -> int:
    """Racha consecutiva de perdidas mas larga (orden cronologico)."""
    longest = 0
    current = 0
    for r in r_multiples:
        if r < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def streak_p99_threshold(
    r_multiples_baseline: list[Decimal], n_boot: int = 10_000, seed: int = 42
) -> int:
    """Bootstrap: remuestrea la baseline `n_boot` veces (con reemplazo,
    reproducible por seed), calcula `loss_streak` de cada remuestreo, y
    devuelve el percentil 99 de esa distribucion como umbral de alerta."""
    if not r_multiples_baseline:
        raise ValueError("streak_p99_threshold: baseline vacia")
    rng = np.random.default_rng(seed)
    n = len(r_multiples_baseline)
    streaks = []
    for _ in range(n_boot):
        sample_idx = rng.integers(0, n, size=n)
        sample = [r_multiples_baseline[i] for i in sample_idx]
        streaks.append(loss_streak(sample))
    return int(np.percentile(streaks, 99))


def max_drawdown_pct(equity_curve: list[Decimal]) -> Decimal:
    """Maximo drawdown porcentual (pico-a-valle) de la curva de equity."""
    if not equity_curve:
        raise ValueError("max_drawdown_pct: curva vacia")
    peak = equity_curve[0]
    max_dd = Decimal("0")
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            drawdown = (peak - value) / peak * 100
            max_dd = max(max_dd, drawdown)
    return max_dd


def win_rate_drift(profits: list[Decimal], baseline_win_rate: float, window: int) -> float:
    """G10: % de trades ganadores (profit>0) en los ultimos `window`
    trades, menos `baseline_win_rate` -- mismo patron rolling-vs-baseline
    que `rolling_profit_factor`. Positivo = mejorando frente a la
    baseline; negativo = empeorando. Ventana vacia -> ValueError."""
    recent = profits[-window:] if profits else []
    if not recent:
        raise ValueError("win_rate_drift: ventana vacia")
    wins = sum(1 for p in recent if p > 0)
    return wins / len(recent) - baseline_win_rate


def payoff_ratio(profits: list[Decimal]) -> float | None:
    """G10: ganancia media de un trade ganador / perdida media (magnitud)
    de un trade perdedor. Sin perdidas y con ganancias -> cap visual
    `PROFIT_FACTOR_DISPLAY_CAP` (mismo criterio que rolling_profit_factor);
    sin ganancias ni perdidas -> None; con perdidas pero sin ganancias -> 0."""
    wins = [p for p in profits if p > 0]
    losses = [-p for p in profits if p < 0]
    avg_win = sum(wins, start=Decimal("0")) / len(wins) if wins else Decimal("0")
    avg_loss = sum(losses, start=Decimal("0")) / len(losses) if losses else Decimal("0")
    if avg_loss == 0:
        return PROFIT_FACTOR_DISPLAY_CAP if avg_win > 0 else None
    return float(avg_win / avg_loss)


def avg_trade_duration(durations: list[timedelta]) -> timedelta:
    """G10: duracion media de un trade (close_time - open_time). Lista
    vacia -> ValueError."""
    if not durations:
        raise ValueError("avg_trade_duration: lista vacia")
    return sum(durations, timedelta()) / len(durations)


def calmar_ratio(equity_curve: list[Decimal], periods_per_year: int = 252) -> float:
    """G10: retorno anualizado compuesto (geometrico, sobre el rango
    propio de la curva) dividido por el maximo drawdown porcentual
    (reutiliza `max_drawdown_pct`). Curva con <2 puntos o max drawdown
    cero -> ValueError."""
    if len(equity_curve) < 2:
        raise ValueError("calmar_ratio: se necesitan al menos 2 puntos")
    n_periods = len(equity_curve) - 1
    total_return = float(equity_curve[-1] / equity_curve[0])
    annualized_return = float(total_return ** (periods_per_year / n_periods)) - 1
    max_dd_pct = float(max_drawdown_pct(equity_curve)) / 100
    if max_dd_pct == 0:
        raise ValueError("calmar_ratio: max drawdown cero")
    return annualized_return / max_dd_pct


def ulcer_index(equity_curve: list[Decimal]) -> float:
    """G10: raiz cuadrada de la media de los drawdowns porcentuales al
    cuadrado, uno por punto de la curva (pico-a-fecha) -- a diferencia de
    `max_drawdown_pct`, no colapsa a un unico maximo, penaliza drawdowns
    sostenidos en el tiempo. Curva vacia -> ValueError."""
    if not equity_curve:
        raise ValueError("ulcer_index: curva vacia")
    peak = equity_curve[0]
    squared_dds: list[float] = []
    for value in equity_curve:
        peak = max(peak, value)
        dd_pct = float((peak - value) / peak * 100) if peak > 0 else 0.0
        squared_dds.append(dd_pct**2)
    return float((sum(squared_dds) / len(squared_dds)) ** 0.5)


def recovery_factor(equity_curve: list[Decimal]) -> float:
    """G10: beneficio neto (ultimo punto - primero) dividido por el
    maximo drawdown en valor ABSOLUTO (no porcentual -- denominador
    distinto de Calmar). Curva con <2 puntos o max drawdown cero ->
    ValueError."""
    if len(equity_curve) < 2:
        raise ValueError("recovery_factor: se necesitan al menos 2 puntos")
    net_profit = equity_curve[-1] - equity_curve[0]
    peak = equity_curve[0]
    max_dd_abs = Decimal("0")
    for value in equity_curve:
        peak = max(peak, value)
        max_dd_abs = max(max_dd_abs, peak - value)
    if max_dd_abs == 0:
        raise ValueError("recovery_factor: max drawdown cero")
    return float(net_profit / max_dd_abs)
