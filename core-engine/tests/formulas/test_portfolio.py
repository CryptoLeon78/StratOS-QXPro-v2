"""PARTE 8: daily_returns, correlation_matrix, historical_var, historical_cvar,
ols_alpha_beta, monte_carlo_maxdd. Pie de PARTE 8: nominal, ventana vacia,
un elemento, extremos, reproducibilidad MC por seed, property-based
(|correlation_matrix| <= 1).

sortino_ratio (G10, docs/backlog.md): no es formula contractual de PARTE 8
-- definicion estandar de la industria (semi-desviacion downside), cierra
parte del gap "Sharpe rolling... panel Metricas completas" de Bots."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.formulas.portfolio import (
    correlation_matrix,
    daily_returns,
    historical_cvar,
    historical_var,
    monte_carlo_maxdd,
    ols_alpha_beta,
    sortino_ratio,
)


def _dates(n: int) -> pd.DatetimeIndex:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return pd.DatetimeIndex([start + timedelta(days=i) for i in range(n)])


class TestDailyReturns:
    def test_nominal(self) -> None:
        curve = pd.Series([100.0, 110.0, 99.0], index=_dates(3))
        returns = daily_returns(curve)
        assert len(returns) == 2
        assert returns.iloc[0] == pytest.approx(0.10)
        assert returns.iloc[1] == pytest.approx(-0.1, abs=1e-9)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="vac"):
            daily_returns(pd.Series([], dtype=float))

    def test_single_element_returns_empty_series(self) -> None:
        curve = pd.Series([100.0], index=_dates(1))
        assert len(daily_returns(curve)) == 0

    def test_extreme_full_wipeout(self) -> None:
        curve = pd.Series([100.0, 0.0], index=_dates(2))
        returns = daily_returns(curve)
        assert returns.iloc[0] == pytest.approx(-1.0)


class TestCorrelationMatrix:
    def test_nominal_identical_series_is_one(self) -> None:
        s = pd.Series([0.01, -0.02, 0.03], index=_dates(3))
        result = correlation_matrix({1: s, 2: s})
        assert result.loc[1, 2] == pytest.approx(1.0)

    def test_inverse_series_is_minus_one(self) -> None:
        s1 = pd.Series([0.01, -0.02, 0.03, 0.01], index=_dates(4))
        s2 = -s1
        result = correlation_matrix({1: s1, 2: s2})
        assert result.loc[1, 2] == pytest.approx(-1.0)

    def test_empty_dict_raises(self) -> None:
        with pytest.raises(ValueError, match="vac"):
            correlation_matrix({})

    def test_single_bot_diagonal_is_one(self) -> None:
        s = pd.Series([0.01, -0.02], index=_dates(2))
        result = correlation_matrix({1: s})
        assert result.loc[1, 1] == pytest.approx(1.0)

    def test_missing_day_filled_with_zero_not_dropped(self) -> None:
        s1 = pd.Series([0.01, 0.02], index=_dates(2))
        s2 = pd.Series([0.01], index=_dates(1))  # falta el segundo dia
        result = correlation_matrix({1: s1, 2: s2}, ffill_limit=0)
        assert result.shape == (2, 2)

    @given(st.integers(min_value=2, max_value=6))
    @settings(max_examples=15, deadline=None)
    def test_property_all_values_within_unit_bounds(self, n_bots: int) -> None:
        rng = np.random.default_rng(1)
        series = {i: pd.Series(rng.normal(size=10), index=_dates(10)) for i in range(n_bots)}
        result = correlation_matrix(series)
        assert ((result >= -1.0001) & (result <= 1.0001)).all().all()


class TestHistoricalVar:
    def test_nominal(self) -> None:
        returns = pd.Series([0.01, -0.02, 0.03, -0.05, 0.02, -0.01, 0.0, 0.01, -0.03, 0.02])
        var = historical_var(returns, level=0.9)
        assert var > 0

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="vac"):
            historical_var(pd.Series([], dtype=float))

    def test_single_value(self) -> None:
        assert historical_var(pd.Series([-0.05])) == pytest.approx(0.05)


class TestHistoricalCvar:
    def test_nominal_worse_than_var(self) -> None:
        returns = pd.Series([0.01, -0.02, 0.03, -0.05, 0.02, -0.01, 0.0, 0.01, -0.03, 0.02])
        var = historical_var(returns, level=0.9)
        cvar = historical_cvar(returns, level=0.9)
        assert cvar >= var

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="vac"):
            historical_cvar(pd.Series([], dtype=float))


class TestOlsAlphaBeta:
    def test_nominal_perfect_line(self) -> None:
        benchmark = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05])
        portfolio = 0.5 * benchmark + 0.01
        result = ols_alpha_beta(portfolio, benchmark)
        assert result.beta == pytest.approx(0.5, abs=1e-6)
        assert result.alpha == pytest.approx(0.01, abs=1e-6)
        assert result.n == 5

    def test_too_few_points_raises(self) -> None:
        with pytest.raises(ValueError, match="al menos"):
            ols_alpha_beta(pd.Series([0.01, 0.02]), pd.Series([0.01, 0.02]))


class TestMonteCarloMaxdd:
    def test_nominal(self) -> None:
        pnls = [Decimal("10"), Decimal("-5"), Decimal("20"), Decimal("-15"), Decimal("8")]
        result = monte_carlo_maxdd(pnls, n_sims=100, seed=42)
        assert result.p50 >= Decimal("0")
        assert result.p95 >= result.p75 >= result.p50
        assert result.seed == 42
        assert result.n_simulations == 100

    def test_reproducible_by_seed(self) -> None:
        pnls = [Decimal("10"), Decimal("-5"), Decimal("20"), Decimal("-15")]
        a = monte_carlo_maxdd(pnls, n_sims=200, seed=7)
        b = monte_carlo_maxdd(pnls, n_sims=200, seed=7)
        assert a == b

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="vac"):
            monte_carlo_maxdd([], n_sims=100, seed=42)


class TestSortinoRatio:
    def test_nominal_positive_for_upward_drift(self) -> None:
        returns = pd.Series([0.02, -0.01, 0.03, -0.005, 0.01, -0.02, 0.015])
        ratio = sortino_ratio(returns, periods_per_year=252)
        assert ratio > 0

    def test_nominal_negative_for_downward_drift(self) -> None:
        returns = pd.Series([-0.02, 0.01, -0.03, 0.005, -0.01, 0.02, -0.015])
        ratio = sortino_ratio(returns, periods_per_year=252)
        assert ratio < 0

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="vac"):
            sortino_ratio(pd.Series([], dtype=float))

    def test_no_downside_returns_raises(self) -> None:
        returns = pd.Series([0.01, 0.02, 0.03])
        with pytest.raises(ValueError, match="downside"):
            sortino_ratio(returns, target=0.0)

    def test_custom_target(self) -> None:
        # todos los retornos superan el target de 0.05 -> sin downside
        returns = pd.Series([0.06, 0.07, 0.08])
        with pytest.raises(ValueError, match="downside"):
            sortino_ratio(returns, target=0.05)
