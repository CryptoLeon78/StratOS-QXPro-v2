"""PARTE 8: metricas de trade/baseline individuales."""

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
