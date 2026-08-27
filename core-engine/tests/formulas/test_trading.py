"""PARTE 8: r_multiple, expectancy_r, rolling_profit_factor, loss_streak,
streak_p99_threshold, max_drawdown_pct. Pie de PARTE 8: nominal, ventana
vacia, division por cero, un elemento, extremos, property-based donde
aplica (max_dd_pct >= 0).

win_rate_drift/payoff_ratio/avg_trade_duration/calmar_ratio/ulcer_index/
recovery_factor (G10, docs/backlog.md): NO son formulas contractuales de
PARTE 8 -- son definiciones estandar de la industria (payoff ratio, Calmar,
Ulcer Index, Recovery Factor) sin ambiguedad de negocio que resolver, a
diferencia de los umbrales de `state_machines/` -- mismo pie de pagina que
el resto de este archivo."""

from datetime import timedelta
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from core.formulas.trading import (
    avg_trade_duration,
    calmar_ratio,
    expectancy_r,
    loss_streak,
    max_drawdown_pct,
    payoff_ratio,
    r_multiple,
    r_multiple_net_of_costs,
    recovery_factor,
    rolling_profit_factor,
    streak_p99_threshold,
    ulcer_index,
    win_rate_drift,
)


class TestRMultiple:
    def test_nominal(self) -> None:
        r = r_multiple(
            profit_net=Decimal("100"),
            entry=Decimal("1.1000"),
            sl=Decimal("1.0950"),
            volume=Decimal("1"),
            tick_value=Decimal("1"),
            tick_size=Decimal("0.0001"),
        )
        assert r == Decimal("2")

    def test_sl_none_returns_none(self) -> None:
        assert (
            r_multiple(
                profit_net=Decimal("100"),
                entry=Decimal("1.1000"),
                sl=None,
                volume=Decimal("1"),
                tick_value=Decimal("1"),
                tick_size=Decimal("0.0001"),
            )
            is None
        )

    def test_zero_risk_returns_none(self) -> None:
        assert (
            r_multiple(
                profit_net=Decimal("100"),
                entry=Decimal("1.1000"),
                sl=Decimal("1.1000"),
                volume=Decimal("1"),
                tick_value=Decimal("1"),
                tick_size=Decimal("0.0001"),
            )
            is None
        )

    def test_loss_gives_negative_r(self) -> None:
        r = r_multiple(
            profit_net=Decimal("-75"),
            entry=Decimal("1.1000"),
            sl=Decimal("1.0950"),
            volume=Decimal("1"),
            tick_value=Decimal("1"),
            tick_size=Decimal("0.0001"),
        )
        assert r == Decimal("-1.5")


class TestRMultipleNetOfCosts:
    def test_subtracts_costs_from_profit(self) -> None:
        # riesgo = |1.1000-1.0950|/0.0001*1*1 = 50; profit_net = 100-2-1 = 97
        r = r_multiple_net_of_costs(
            profit=Decimal("100"),
            commission=Decimal("-2"),
            swap=Decimal("-1"),
            entry=Decimal("1.1000"),
            sl=Decimal("1.0950"),
            volume=Decimal("1"),
            tick_value=Decimal("1"),
            tick_size=Decimal("0.0001"),
        )
        assert r == Decimal("1.94")

    def test_sl_none_returns_none(self) -> None:
        r = r_multiple_net_of_costs(
            profit=Decimal("100"),
            commission=Decimal("0"),
            swap=Decimal("0"),
            entry=Decimal("1.1000"),
            sl=None,
            volume=Decimal("1"),
            tick_value=Decimal("1"),
            tick_size=Decimal("0.0001"),
        )
        assert r is None


class TestExpectancyR:
    def test_nominal(self) -> None:
        assert expectancy_r([Decimal("1"), Decimal("-1"), Decimal("2")]) == pytest.approx(2 / 3)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="vac"):
            expectancy_r([])

    def test_single_element(self) -> None:
        assert expectancy_r([Decimal("1.5")]) == pytest.approx(1.5)

    def test_extreme_values(self) -> None:
        assert expectancy_r([Decimal("1000"), Decimal("-999")]) == pytest.approx(0.5)


class TestRollingProfitFactor:
    def test_nominal(self) -> None:
        pf = rolling_profit_factor(
            [Decimal("10"), Decimal("-5"), Decimal("20"), Decimal("-10")], window=4
        )
        assert pf == pytest.approx(2.0)

    def test_window_smaller_than_history_uses_last_n(self) -> None:
        pf = rolling_profit_factor(
            [Decimal("1000"), Decimal("10"), Decimal("-5")],
            window=2,
        )
        assert pf == pytest.approx(2.0)

    def test_zero_loss_positive_profit_caps_at_99(self) -> None:
        pf = rolling_profit_factor([Decimal("10"), Decimal("5")], window=2)
        assert pf == 99.0

    def test_both_zero_returns_none(self) -> None:
        assert rolling_profit_factor([Decimal("0"), Decimal("0")], window=2) is None

    def test_empty_returns_none(self) -> None:
        assert rolling_profit_factor([], window=5) is None


class TestLossStreak:
    def test_nominal(self) -> None:
        r = [Decimal("1"), Decimal("-1"), Decimal("-1"), Decimal("-1"), Decimal("2"), Decimal("-1")]
        assert loss_streak(r) == 3

    def test_empty_returns_zero(self) -> None:
        assert loss_streak([]) == 0

    def test_single_loss(self) -> None:
        assert loss_streak([Decimal("-1")]) == 1

    def test_single_win(self) -> None:
        assert loss_streak([Decimal("1")]) == 0

    def test_all_losses(self) -> None:
        assert loss_streak([Decimal("-1")] * 5) == 5


class TestStreakP99Threshold:
    def test_nominal_returns_int(self) -> None:
        baseline = [Decimal("1"), Decimal("-1"), Decimal("-1"), Decimal("2")] * 20
        threshold = streak_p99_threshold(baseline, n_boot=200, seed=42)
        assert isinstance(threshold, int)
        assert threshold >= 0

    def test_reproducible_by_seed(self) -> None:
        baseline = [Decimal("1"), Decimal("-1"), Decimal("-1"), Decimal("2")] * 20
        a = streak_p99_threshold(baseline, n_boot=200, seed=7)
        b = streak_p99_threshold(baseline, n_boot=200, seed=7)
        assert a == b

    def test_empty_baseline_raises(self) -> None:
        with pytest.raises(ValueError, match="vac"):
            streak_p99_threshold([], n_boot=100, seed=42)


class TestMaxDrawdownPct:
    def test_nominal(self) -> None:
        curve = [Decimal("100"), Decimal("110"), Decimal("90"), Decimal("120")]
        dd = max_drawdown_pct(curve)
        assert dd == pytest.approx(Decimal("18.181818"), abs=Decimal("0.001"))

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="vac"):
            max_drawdown_pct([])

    def test_single_element_is_zero(self) -> None:
        assert max_drawdown_pct([Decimal("100")]) == Decimal("0")

    def test_monotonic_increase_is_zero(self) -> None:
        curve = [Decimal("100"), Decimal("110"), Decimal("120"), Decimal("130")]
        assert max_drawdown_pct(curve) == Decimal("0")

    def test_extreme_full_wipeout(self) -> None:
        curve = [Decimal("100"), Decimal("0")]
        assert max_drawdown_pct(curve) == Decimal("100")

    @given(
        st.lists(
            st.decimals(min_value="0.01", max_value="1000000", places=2, allow_nan=False),
            min_size=1,
            max_size=50,
        )
    )
    def test_property_always_non_negative(self, curve: list[Decimal]) -> None:
        assert max_drawdown_pct(curve) >= Decimal("0")


class TestWinRateDrift:
    def test_nominal_improving(self) -> None:
        profits = [Decimal("10"), Decimal("10"), Decimal("-5"), Decimal("10")]
        drift = win_rate_drift(profits, baseline_win_rate=0.5, window=4)
        assert drift == pytest.approx(0.25)

    def test_nominal_worsening(self) -> None:
        profits = [Decimal("-1"), Decimal("-1"), Decimal("1")]
        drift = win_rate_drift(profits, baseline_win_rate=0.8, window=3)
        assert drift == pytest.approx(1 / 3 - 0.8)

    def test_window_smaller_than_history_uses_last_n(self) -> None:
        profits = [Decimal("10"), Decimal("10"), Decimal("-1"), Decimal("-1")]
        drift = win_rate_drift(profits, baseline_win_rate=0.0, window=2)
        assert drift == pytest.approx(0.0)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="vac"):
            win_rate_drift([], baseline_win_rate=0.5, window=5)


class TestPayoffRatio:
    def test_nominal(self) -> None:
        profits = [Decimal("20"), Decimal("20"), Decimal("-10")]
        assert payoff_ratio(profits) == pytest.approx(2.0)

    def test_zero_losses_positive_wins_caps_at_99(self) -> None:
        assert payoff_ratio([Decimal("10"), Decimal("5")]) == 99.0

    def test_both_empty_returns_none(self) -> None:
        assert payoff_ratio([Decimal("0"), Decimal("0")]) is None

    def test_empty_list_returns_none(self) -> None:
        assert payoff_ratio([]) is None

    def test_no_wins_returns_zero(self) -> None:
        assert payoff_ratio([Decimal("-10"), Decimal("-20")]) == pytest.approx(0.0)


class TestAvgTradeDuration:
    def test_nominal(self) -> None:
        durations = [timedelta(hours=1), timedelta(hours=3)]
        assert avg_trade_duration(durations) == timedelta(hours=2)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="vac"):
            avg_trade_duration([])

    def test_single_element(self) -> None:
        assert avg_trade_duration([timedelta(minutes=45)]) == timedelta(minutes=45)


class TestCalmarRatio:
    def test_nominal(self) -> None:
        curve = [Decimal("100")] + [Decimal("100") * Decimal("1.001") ** i for i in range(1, 253)]
        curve[100] = curve[99] - Decimal("5")
        ratio = calmar_ratio(curve, periods_per_year=252)
        assert ratio > 0

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="al menos"):
            calmar_ratio([Decimal("100")])

    def test_zero_drawdown_raises(self) -> None:
        curve = [Decimal("100"), Decimal("110"), Decimal("120")]
        with pytest.raises(ValueError, match="cero"):
            calmar_ratio(curve)


class TestUlcerIndex:
    def test_monotonic_increase_is_zero(self) -> None:
        curve = [Decimal("100"), Decimal("110"), Decimal("120")]
        assert ulcer_index(curve) == pytest.approx(0.0)

    def test_nominal_positive_for_a_drawdown(self) -> None:
        curve = [Decimal("100"), Decimal("90"), Decimal("100")]
        assert ulcer_index(curve) > 0

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="vac"):
            ulcer_index([])

    def test_single_element_is_zero(self) -> None:
        assert ulcer_index([Decimal("100")]) == pytest.approx(0.0)

    @given(
        st.lists(
            st.decimals(min_value="0.01", max_value="1000000", places=2, allow_nan=False),
            min_size=1,
            max_size=50,
        )
    )
    def test_property_always_non_negative(self, curve: list[Decimal]) -> None:
        assert ulcer_index(curve) >= 0.0


class TestRecoveryFactor:
    def test_nominal(self) -> None:
        curve = [Decimal("100"), Decimal("150"), Decimal("120"), Decimal("180")]
        # max dd absoluto = 150-120 = 30; net profit = 180-100 = 80
        assert recovery_factor(curve) == pytest.approx(80 / 30)

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="al menos"):
            recovery_factor([Decimal("100")])

    def test_zero_drawdown_raises(self) -> None:
        curve = [Decimal("100"), Decimal("110"), Decimal("120")]
        with pytest.raises(ValueError, match="cero"):
            recovery_factor(curve)

    def test_net_loss_is_negative(self) -> None:
        curve = [Decimal("100"), Decimal("120"), Decimal("80")]
        assert recovery_factor(curve) < 0
