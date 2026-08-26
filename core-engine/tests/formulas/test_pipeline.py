"""PARTE 8: walk_forward_efficiency, trades_per_week, decision_eta_days.
Pie de PARTE 8: nominal, division por cero, un elemento, extremos,
property-based (WFE acotada, ETA monotona en frecuencia)."""

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from core.formulas.pipeline import decision_eta_days, trades_per_week, walk_forward_efficiency

NOW = datetime(2026, 8, 26, tzinfo=UTC)


class TestWalkForwardEfficiency:
    def test_nominal(self) -> None:
        assert walk_forward_efficiency(oos_return=0.6, is_return=1.0) == pytest.approx(0.6)

    def test_is_return_zero_raises(self) -> None:
        with pytest.raises(ZeroDivisionError):
            walk_forward_efficiency(oos_return=0.5, is_return=0.0)

    def test_negative_is_return(self) -> None:
        assert walk_forward_efficiency(oos_return=-0.2, is_return=-0.4) == pytest.approx(0.5)

    def test_extreme_small_is_return(self) -> None:
        wfe = walk_forward_efficiency(oos_return=1.0, is_return=0.001)
        assert wfe == pytest.approx(1000.0)

    @given(
        oos=st.floats(min_value=-10, max_value=10, allow_nan=False),
        is_=st.floats(min_value=0.1, max_value=10, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_property_bounded_with_bounded_inputs(self, oos: float, is_: float) -> None:
        wfe = walk_forward_efficiency(oos_return=oos, is_return=is_)
        assert -100.0 <= wfe <= 100.0


class TestTradesPerWeek:
    def test_nominal(self) -> None:
        trades = [NOW - timedelta(days=i) for i in range(12)]
        assert trades_per_week(trades, window_days=30) == pytest.approx(12 / (30 / 7))

    def test_empty_returns_zero(self) -> None:
        assert trades_per_week([], window_days=30) == 0.0

    def test_single_trade(self) -> None:
        assert trades_per_week([NOW], window_days=30) == pytest.approx(1 / (30 / 7))

    def test_extreme_small_window(self) -> None:
        trades = [NOW] * 5
        result = trades_per_week(trades, window_days=1)
        assert result == pytest.approx(5 / (1 / 7))


class TestDecisionEtaDays:
    def test_nominal(self) -> None:
        eta = decision_eta_days(
            oos_trades=10,
            min_trades=30,
            entered_phase_at=NOW - timedelta(days=10),
            min_days=60,
            freq_week=2.0,
            now=NOW,
        )
        assert eta is not None
        assert eta > 0

    def test_freq_zero_returns_none(self) -> None:
        eta = decision_eta_days(
            oos_trades=5,
            min_trades=30,
            entered_phase_at=NOW - timedelta(days=10),
            min_days=60,
            freq_week=0.0,
            now=NOW,
        )
        assert eta is None

    def test_already_satisfied_is_zero(self) -> None:
        eta = decision_eta_days(
            oos_trades=40,
            min_trades=30,
            entered_phase_at=NOW - timedelta(days=90),
            min_days=60,
            freq_week=5.0,
            now=NOW,
        )
        assert eta == 0

    @given(freq_week=st.floats(min_value=0.5, max_value=20))
    @settings(max_examples=25)
    def test_property_monotonic_in_frequency(self, freq_week: float) -> None:
        lower = decision_eta_days(
            oos_trades=5,
            min_trades=30,
            entered_phase_at=NOW - timedelta(days=5),
            min_days=10,
            freq_week=freq_week,
            now=NOW,
        )
        higher = decision_eta_days(
            oos_trades=5,
            min_trades=30,
            entered_phase_at=NOW - timedelta(days=5),
            min_days=10,
            freq_week=freq_week * 2,
            now=NOW,
        )
        assert lower is not None
        assert higher is not None
        assert higher <= lower
