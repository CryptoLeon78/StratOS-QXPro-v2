"""PARTE 8: r_multiple, expectancy_r, rolling_profit_factor, loss_streak,
streak_p99_threshold, max_drawdown_pct. Pie de PARTE 8: nominal, ventana
vacia, division por cero, un elemento, extremos, property-based donde
aplica (max_dd_pct >= 0)."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from core.formulas.trading import (
    expectancy_r,
    loss_streak,
    max_drawdown_pct,
    r_multiple,
    rolling_profit_factor,
    streak_p99_threshold,
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
