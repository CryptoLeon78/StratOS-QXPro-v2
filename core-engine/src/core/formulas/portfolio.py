"""PARTE 8: estadistica de cartera/riesgo.

sortino_ratio (G10, docs/backlog.md): no es formula contractual de PARTE 8
-- definicion estandar de la industria (semi-desviacion downside)."""

from decimal import Decimal

import numpy as np
import pandas as pd
import statsmodels.api as sm

from core.formulas.trading import max_drawdown_pct
from core.formulas.types import AlphaBetaResult, MonteCarloResult

MIN_OLS_POINTS = 3  # alpha+beta = 2 parametros; hacen falta n > 2 grados de libertad


def daily_returns(equity_curve: pd.Series) -> pd.Series:
    """PARTE 8: retornos diarios de una curva de equity."""
    if equity_curve.empty:
        raise ValueError("daily_returns: curva vacia")
    return equity_curve.pct_change().dropna()


def correlation_matrix(returns_by_bot: dict[int, pd.Series], ffill_limit: int = 3) -> pd.DataFrame:
    """Alinea por dia UTC (union de indices), rellena huecos cortos hacia
    adelante hasta `ffill_limit` dias, y el resto (dia sin trade) a 0
    (PARTE 8), antes de calcular la matriz de correlacion de Pearson."""
    if not returns_by_bot:
        raise ValueError("correlation_matrix: diccionario de bots vacio")
    aligned = pd.DataFrame(returns_by_bot)
    if ffill_limit > 0:
        aligned = aligned.ffill(limit=ffill_limit)
    return aligned.fillna(0).corr()


def historical_var(returns: pd.Series, level: float = 0.95) -> float:
    """VaR historico (empirico): magnitud de perdida en el percentil
    (1-level) de la distribucion de retornos, como float positivo."""
    if returns.empty:
        raise ValueError("historical_var: serie vacia")
    percentile = (1 - level) * 100
    return float(-np.percentile(returns, percentile))


def historical_cvar(returns: pd.Series, level: float = 0.99) -> float:
    """CVaR (expected shortfall): media de los retornos peores que el
    umbral VaR al mismo nivel, como float positivo."""
    if returns.empty:
        raise ValueError("historical_cvar: serie vacia")
    percentile = (1 - level) * 100
    threshold = np.percentile(returns, percentile)
    # threshold >= min(returns) siempre (definicion de percentil), asi que
    # la cola nunca queda vacia para una serie no vacia.
    tail = returns[returns <= threshold]
    return float(-tail.mean())


def monte_carlo_maxdd(
    trade_pnls: list[Decimal],
    n_sims: int = 300,
    seed: int = 42,
    initial_equity: Decimal = Decimal("100"),
) -> MonteCarloResult:
    """Bootstrap: remuestrea `trade_pnls` con reemplazo `n_sims` veces
    (reproducible por seed), construye la curva de equity acumulada desde
    `initial_equity` para cada remuestreo y calcula su `max_drawdown_pct`
    (reutilizada de `trading.py`). `initial_equity` no esta en la firma
    compacta de PARTE 8: sin una base, "drawdown en %" no tiene sentido
    (ver ASSUMPTIONS G2)."""
    if not trade_pnls:
        raise ValueError("monte_carlo_maxdd: lista de trades vacia")
    rng = np.random.default_rng(seed)
    n = len(trade_pnls)
    max_dds: list[float] = []
    for _ in range(n_sims):
        idx = rng.integers(0, n, size=n)
        equity = initial_equity
        curve = [equity]
        for i in idx:
            equity = equity + trade_pnls[i]
            curve.append(equity)
        max_dds.append(float(max_drawdown_pct(curve)))
    p50, p75, p95 = (float(x) for x in np.percentile(max_dds, [50, 75, 95]))
    return MonteCarloResult(
        p50=Decimal(str(round(p50, 4))),
        p75=Decimal(str(round(p75, 4))),
        p95=Decimal(str(round(p95, 4))),
        seed=seed,
        n_simulations=n_sims,
    )


def sortino_ratio(returns: pd.Series, periods_per_year: int = 252, target: float = 0.0) -> float:
    """G10: exceso de retorno medio sobre `target` dividido por la
    desviacion tipica de los retornos POR DEBAJO del target (semi-
    desviacion downside), anualizado por raiz del tiempo (misma convencion
    que `historical_var`/`compute_tail_risk`, ASSUMPTIONS G5). Serie vacia
    o sin retornos por debajo del target -> ValueError (semi-desviacion
    indefinida, nunca 0/0 silencioso)."""
    if returns.empty:
        raise ValueError("sortino_ratio: serie vacia")
    downside = returns[returns < target] - target
    if downside.empty:
        raise ValueError("sortino_ratio: sin retornos por debajo del target (downside)")
    downside_deviation = float(np.sqrt((downside**2).mean()))
    mean_excess = float(returns.mean()) - target
    return mean_excess / downside_deviation * float(periods_per_year**0.5)


def ols_alpha_beta(portfolio_monthly: pd.Series, benchmark_monthly: pd.Series) -> AlphaBetaResult:
    """Regresion OLS portfolio = alpha + beta*benchmark + ruido. t_stat/
    p_value son los de alfa (PARTE 1 cita "t-stat del alfa 3,42")."""
    n = len(portfolio_monthly)
    if n < MIN_OLS_POINTS:
        raise ValueError(f"ols_alpha_beta: se necesitan al menos {MIN_OLS_POINTS} puntos")
    design = sm.add_constant(np.asarray(benchmark_monthly, dtype=float))
    model = sm.OLS(np.asarray(portfolio_monthly, dtype=float), design).fit()
    return AlphaBetaResult(
        alpha=float(model.params[0]),
        beta=float(model.params[1]),
        t_stat=float(model.tvalues[0]),
        p_value=float(model.pvalues[0]),
        n=n,
    )
