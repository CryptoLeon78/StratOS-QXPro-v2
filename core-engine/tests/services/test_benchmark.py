"""G10 (docs/backlog.md): "¿Añade valor real el portfolio?" -- CAGR/Beta/
alfa/t-stat/Information Ratio/Batting Average/Up-Down capture del
portfolio real contra el S&P 500 (scripts/data/sp500_monthly.csv, 72
meses desde G8). alpha/beta/t_stat/p_value reutilizan `ols_alpha_beta`
(formulas/portfolio.py, G2, 100% cobertura) -- el resto son definiciones
estandar de la industria, no formulas contractuales de PARTE 8."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pandas as pd
import pytest

from core.services.benchmark import (
    compare_to_benchmark,
    load_sp500_monthly,
    portfolio_monthly_returns,
)
from tests.factories import AccountFactory, EquitySnapshotFactory


def _dates(n: int) -> pd.DatetimeIndex:
    start = pd.Timestamp("2026-01-31")
    return pd.DatetimeIndex([start + pd.DateOffset(months=i) for i in range(n)])


class TestCompareToBenchmark:
    def test_recovers_a_known_beta_with_controlled_data(self) -> None:
        benchmark = pd.Series(
            [0.02, -0.01, 0.03, 0.01, -0.02, 0.015, 0.005, -0.005], index=_dates(8)
        )
        # relacion controlada portfolio = 0.01 + 0.5*benchmark (sin ruido,
        # beta exacta recuperable)
        portfolio = 0.01 + 0.5 * benchmark

        result = compare_to_benchmark(portfolio, benchmark)
        assert result is not None
        assert result.beta == pytest.approx(0.5, abs=1e-6)
        assert result.n_months == 8

    def test_outperforming_every_month_has_batting_average_100(self) -> None:
        benchmark = pd.Series([0.01, 0.02, -0.01, 0.03], index=_dates(4))
        portfolio = benchmark + 0.01  # siempre 1pp mejor
        result = compare_to_benchmark(portfolio, benchmark)
        assert result is not None
        assert result.batting_average == pytest.approx(100.0)

    def test_identical_series_has_zero_information_ratio(self) -> None:
        benchmark = pd.Series([0.01, 0.02, -0.01, 0.03], index=_dates(4))
        result = compare_to_benchmark(benchmark.copy(), benchmark)
        assert result is not None
        assert result.information_ratio == pytest.approx(0.0)

    def test_up_and_down_capture_with_double_amplitude(self) -> None:
        # portfolio se mueve exactamente el doble que el benchmark en
        # ambas direcciones -- capture = 200% arriba y abajo.
        benchmark = pd.Series([0.02, -0.03, 0.01, -0.02], index=_dates(4))
        portfolio = benchmark * 2
        result = compare_to_benchmark(portfolio, benchmark)
        assert result is not None
        assert result.up_capture == pytest.approx(200.0)
        assert result.down_capture == pytest.approx(200.0)

    def test_too_few_overlapping_months_returns_none(self) -> None:
        benchmark = pd.Series([0.01, 0.02], index=_dates(2))
        portfolio = pd.Series([0.01, 0.02], index=_dates(2))
        assert compare_to_benchmark(portfolio, benchmark) is None

    def test_no_overlap_returns_none(self) -> None:
        benchmark = pd.Series([0.01, 0.02, 0.03], index=_dates(3))
        old_dates = pd.DatetimeIndex(
            [pd.Timestamp("2020-01-31"), pd.Timestamp("2020-02-29"), pd.Timestamp("2020-03-31")]
        )
        portfolio = pd.Series([0.01, 0.02, 0.03], index=old_dates)
        assert compare_to_benchmark(portfolio, benchmark) is None


class TestLoadSp500Monthly:
    def test_loads_the_real_csv_with_at_least_66_months(self) -> None:
        from pathlib import Path

        csv_path = Path(__file__).resolve().parents[3] / "scripts" / "data" / "sp500_monthly.csv"
        series = load_sp500_monthly(csv_path)
        assert len(series) >= 66


class TestPortfolioMonthlyReturns:
    async def test_computes_month_over_month_returns_from_real_accounts(
        self, db_session: object
    ) -> None:
        account = AccountFactory(is_demo=False)  # type: ignore[call-arg]
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(
                account_id=account.id, ts=now - timedelta(days=60), equity=Decimal("100000")
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(
                account_id=account.id, ts=now - timedelta(days=30), equity=Decimal("110000")
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(account_id=account.id, ts=now, equity=Decimal("121000"))
        )
        await db_session.flush()  # type: ignore[attr-defined]

        result = await portfolio_monthly_returns(db_session, now)  # type: ignore[arg-type]
        assert len(result) >= 1

    async def test_no_snapshots_returns_empty_series(self, db_session: object) -> None:
        result = await portfolio_monthly_returns(db_session, datetime.now(UTC))  # type: ignore[arg-type]
        assert result.empty
