"""PARTE 8: watchdog_deviation, page_hinkley. Pie de PARTE 8: nominal,
ventana vacia, un elemento, extremos."""

import pytest

from core.formulas.monitoring import page_hinkley, watchdog_deviation
from core.formulas.types import WatchdogState


class TestWatchdogDeviation:
    def test_nominal_ok(self) -> None:
        assert watchdog_deviation(observed=6, expected=7) == WatchdogState.OK

    def test_expected_none_is_insufficient_data(self) -> None:
        assert watchdog_deviation(observed=5, expected=None) == WatchdogState.INSUFFICIENT_DATA

    def test_expected_zero_is_insufficient_data(self) -> None:
        assert watchdog_deviation(observed=5, expected=0) == WatchdogState.INSUFFICIENT_DATA

    def test_zero_observed_with_positive_expected_is_dead(self) -> None:
        assert watchdog_deviation(observed=0, expected=12) == WatchdogState.DEAD

    def test_runaway_beyond_default_factor(self) -> None:
        assert watchdog_deviation(observed=35, expected=10) == WatchdogState.RUNAWAY

    def test_out_of_tolerance(self) -> None:
        assert watchdog_deviation(observed=7, expected=10) == WatchdogState.OUT_OF_TOLERANCE

    def test_matches_real_seed_example_lyra(self) -> None:
        # PARTE 1: "Lyra Scalper esperaba 58 y lleva 59" -> dentro de tolerancia
        assert watchdog_deviation(observed=59, expected=58) == WatchdogState.OK

    def test_custom_tolerance_and_runaway_factor(self) -> None:
        assert (
            watchdog_deviation(observed=25, expected=10, tolerance=0.6, runaway_factor=2.0)
            == WatchdogState.RUNAWAY
        )


class TestPageHinkley:
    def test_nominal_detects_mean_shift(self) -> None:
        stable = [0.01, -0.01, 0.02, -0.02, 0.01, -0.01, 0.02, -0.01]
        shifted = [-0.5, -0.6, -0.55, -0.62, -0.58]
        result = page_hinkley(stable + shifted, delta=0.005, lambda_=0.05)
        assert result.change_detected is True
        assert result.change_point is not None
        assert result.change_point >= len(stable) - 2

    def test_no_shift_no_detection(self) -> None:
        flat = [0.01, -0.01, 0.02, -0.02, 0.01, -0.01, 0.02, -0.01, 0.0, 0.01]
        result = page_hinkley(flat, delta=0.005, lambda_=10.0)
        assert result.change_detected is False
        assert result.change_point is None

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="vac"):
            page_hinkley([], delta=0.005, lambda_=0.05)

    def test_single_element_does_not_crash(self) -> None:
        result = page_hinkley([0.5], delta=0.005, lambda_=0.05)
        assert isinstance(result.change_detected, bool)

    def test_extreme_shift_detected_immediately(self) -> None:
        series = [0.0, 0.0, 0.0, -100.0, -100.0]
        result = page_hinkley(series, delta=0.01, lambda_=1.0)
        assert result.change_detected is True
