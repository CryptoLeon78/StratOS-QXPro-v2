"""G10 (docs/backlog.md): curva de P&L acumulado sintetica por bot +
posiciones abiertas por bot. CAVEAT probado aqui tal cual el docstring de
`services/bot_equity.py`: es SUM(Trade.profit) acumulado, no equity real
de cuenta a nivel de bot (eso no existe -- EquitySnapshot es por
account_id)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from core.db.enums import TradeType
from core.services.bot_equity import bot_open_positions, bot_pnl_curve, compute_curve_metrics
from tests.factories import AccountFactory, BotFactory, IngestBatchFactory, TradeFactory


async def _bot(db_session: object) -> object:
    account = AccountFactory()  # type: ignore[call-arg]
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    bot = BotFactory(account_id=account.id)  # type: ignore[call-arg]
    db_session.add(bot)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    batch = IngestBatchFactory(account_id=account.id)  # type: ignore[call-arg]
    db_session.add(batch)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return bot, account, batch


class TestBotPnlCurve:
    async def test_accumulates_closed_trades_in_close_time_order(self, db_session: object) -> None:
        bot, account, batch = await _bot(db_session)
        now = datetime.now(UTC)
        # insertados fuera de orden -- la curva debe respetar close_time, no orden de insercion
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("30.00"),
                close_time=now - timedelta(days=1),
                close_price=Decimal("1.1"),
                ingest_batch_id=batch.id,
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.SELL,
                volume=Decimal("1.00"),
                profit=Decimal("-10.00"),
                close_time=now - timedelta(days=2),
                close_price=Decimal("1.1"),
                ingest_batch_id=batch.id,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        curve = await bot_pnl_curve(db_session, bot.id, initial_equity=Decimal("100"))  # type: ignore[arg-type]
        assert curve == [Decimal("100"), Decimal("90"), Decimal("120")]

    async def test_ignores_open_trades(self, db_session: object) -> None:
        bot, account, batch = await _bot(db_session)
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("999.00"),
                close_time=None,
                ingest_batch_id=batch.id,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        curve = await bot_pnl_curve(db_session, bot.id)  # type: ignore[arg-type]
        assert curve == [Decimal("100")]

    async def test_no_trades_returns_only_the_base(self, db_session: object) -> None:
        bot, _account, _batch = await _bot(db_session)
        curve = await bot_pnl_curve(db_session, bot.id, initial_equity=Decimal("50"))  # type: ignore[arg-type]
        assert curve == [Decimal("50")]

    async def test_default_initial_equity_is_nominal_100(self, db_session: object) -> None:
        bot, _account, _batch = await _bot(db_session)
        curve = await bot_pnl_curve(db_session, bot.id)  # type: ignore[arg-type]
        assert curve == [Decimal("100")]


class TestBotOpenPositions:
    async def test_returns_only_open_trades_for_the_bot(self, db_session: object) -> None:
        bot, account, batch = await _bot(db_session)
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("5.00"),
                close_time=None,
                ingest_batch_id=batch.id,
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.SELL,
                volume=Decimal("1.00"),
                profit=Decimal("999.00"),
                close_time=datetime.now(UTC),
                close_price=Decimal("1.1"),
                ingest_batch_id=batch.id,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        positions = await bot_open_positions(db_session, bot.id)  # type: ignore[arg-type]
        assert len(positions) == 1
        assert positions[0].profit == Decimal("5.00")

    async def test_no_open_positions_returns_empty_list(self, db_session: object) -> None:
        bot, _account, _batch = await _bot(db_session)
        assert await bot_open_positions(db_session, bot.id) == []  # type: ignore[arg-type]


class TestComputeCurveMetrics:
    def test_nominal_curve_produces_all_metrics(self) -> None:
        curve = [
            Decimal("100"),
            Decimal("110"),
            Decimal("105"),
            Decimal("120"),
            Decimal("115"),
            Decimal("130"),
        ]
        metrics = compute_curve_metrics(curve)
        assert metrics.net_pnl == Decimal("30")
        assert metrics.max_dd_pct > 0
        assert metrics.ulcer_index > 0
        assert metrics.calmar is not None
        assert metrics.recovery_factor is not None
        assert metrics.sortino is not None

    def test_monotonic_curve_has_no_drawdown_calmar_and_recovery_none(self) -> None:
        curve = [Decimal("100"), Decimal("110"), Decimal("120"), Decimal("130")]
        metrics = compute_curve_metrics(curve)
        assert metrics.max_dd_pct == 0
        assert metrics.ulcer_index == 0
        # sin drawdown, calmar_ratio()/recovery_factor() levantan ValueError
        # (division por max_dd cero) -- no se inventa, queda en None.
        assert metrics.calmar is None
        assert metrics.recovery_factor is None

    def test_single_point_curve_returns_neutral_metrics(self) -> None:
        metrics = compute_curve_metrics([Decimal("100")])
        assert metrics.net_pnl == Decimal("0")
        assert metrics.max_dd_pct == 0
        assert metrics.sortino is None
        assert metrics.calmar is None
        assert metrics.recovery_factor is None

    def test_empty_curve_returns_neutral_metrics(self) -> None:
        metrics = compute_curve_metrics([])
        assert metrics.net_pnl == Decimal("0")
        assert metrics.sortino is None

    def test_no_downside_returns_leaves_sortino_none(self) -> None:
        # todos los retornos positivos -- sortino_ratio() levanta ValueError
        # (sin retornos por debajo del target), no se inventa.
        curve = [Decimal("100"), Decimal("101"), Decimal("103"), Decimal("106")]
        metrics = compute_curve_metrics(curve)
        assert metrics.sortino is None


class TestComputePortfolioContribution:
    async def test_computes_pct_of_total_and_account_pnl(self, db_session: object) -> None:
        from core.services.bot_equity import compute_portfolio_contribution

        bot, account, batch = await _bot(db_session)
        other_bot = BotFactory(account_id=account.id)  # type: ignore[call-arg]
        db_session.add(other_bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("30.00"),
                close_time=datetime.now(UTC),
                close_price=Decimal("1.1"),
                ingest_batch_id=batch.id,
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=other_bot.id,
                account_id=account.id,
                magic_number=other_bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("70.00"),
                close_time=datetime.now(UTC),
                close_price=Decimal("1.1"),
                ingest_batch_id=batch.id,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        contribution = await compute_portfolio_contribution(db_session, bot)  # type: ignore[arg-type]
        assert contribution.pnl_bot == Decimal("30.00")
        assert contribution.pnl_account == Decimal("100.00")
        assert contribution.pct_of_total_pnl == pytest.approx(30.0)
        assert contribution.correlation_vs_rest is None  # sin CorrelationMatrix sembrada

    async def test_averages_correlation_across_all_pairs_involving_the_bot(
        self, db_session: object
    ) -> None:
        from core.db.models.governance import CorrelationMatrix
        from core.services.bot_equity import compute_portfolio_contribution

        bot, account, _batch = await _bot(db_session)
        bot_b = BotFactory(account_id=account.id)  # type: ignore[call-arg]
        bot_c = BotFactory(account_id=account.id)  # type: ignore[call-arg]
        db_session.add(bot_b)  # type: ignore[attr-defined]
        db_session.add(bot_c)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            CorrelationMatrix(
                ts=now,
                bot_a_id=bot.id,
                bot_b_id=bot_b.id,
                correlation=0.2,
                is_redundant_pair=False,
                window_days=90,
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            CorrelationMatrix(
                ts=now,
                bot_a_id=bot_c.id,
                bot_b_id=bot.id,
                correlation=0.6,
                is_redundant_pair=False,
                window_days=90,
            )
        )
        # par SIN el bot -- no debe contar
        db_session.add(  # type: ignore[attr-defined]
            CorrelationMatrix(
                ts=now,
                bot_a_id=bot_b.id,
                bot_b_id=bot_c.id,
                correlation=0.9,
                is_redundant_pair=True,
                window_days=90,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        contribution = await compute_portfolio_contribution(db_session, bot)  # type: ignore[arg-type]
        assert contribution.correlation_vs_rest == pytest.approx(0.4)  # (0.2+0.6)/2

    async def test_bot_with_zero_trades_returns_zero_not_a_crash(self, db_session: object) -> None:
        # Bug real encontrado en verificacion en vivo (G10, bot_id=33 "Zephyr
        # Trend AUDUSD" del seed real, F1 sin trades): `trade` es hypertable
        # TimescaleDB -- un agregado SIN GROUP BY que no toca ningun chunk
        # (filtro que no coincide con NINGUN trade fisico ya commiteado)
        # devuelve CERO filas, no la fila unica que garantiza el estandar
        # SQL (COALESCE(SUM(...),0)); `.scalar_one()` lanzaba NoResultFound.
        # Esta fixture (transaccion/savepoint, sin datos commiteados a nivel
        # de chunk) NO reproduce el quirk fisico de Timescale -- pero fija
        # el contrato correcto (0, no crash) que el fix (`.scalar()` +
        # fallback) garantiza en ambos casos.
        from core.services.bot_equity import compute_portfolio_contribution

        bot, _account, _batch = await _bot(db_session)

        contribution = await compute_portfolio_contribution(db_session, bot)  # type: ignore[arg-type]
        assert contribution.pnl_bot == Decimal("0")
        assert contribution.pnl_account == Decimal("0")
        assert contribution.pct_of_total_pnl is None
        assert contribution.correlation_vs_rest is None


class TestBotPnlCurveWithDates:
    async def test_pairs_each_point_with_its_close_time(self, db_session: object) -> None:
        from core.services.bot_equity import bot_pnl_curve_with_dates

        bot, account, batch = await _bot(db_session)
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("20.00"),
                close_time=now - timedelta(days=1),
                close_price=Decimal("1.1"),
                ingest_batch_id=batch.id,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        points = await bot_pnl_curve_with_dates(db_session, bot.id)  # type: ignore[arg-type]
        assert points[0] == (None, Decimal("100"))
        assert points[1][0] is not None
        assert points[1][1] == Decimal("120")

    async def test_no_trades_returns_only_the_synthetic_start(self, db_session: object) -> None:
        from core.services.bot_equity import bot_pnl_curve_with_dates

        bot, _account, _batch = await _bot(db_session)
        points = await bot_pnl_curve_with_dates(db_session, bot.id)  # type: ignore[arg-type]
        assert points == [(None, Decimal("100"))]


class TestBotRMultiples:
    async def test_returns_only_populated_r_multiples_for_closed_trades(
        self, db_session: object
    ) -> None:
        from core.services.bot_equity import bot_r_multiples

        bot, account, batch = await _bot(db_session)
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("20.00"),
                close_time=datetime.now(UTC),
                close_price=Decimal("1.1"),
                r_multiple=Decimal("2.0"),
                ingest_batch_id=batch.id,
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.SELL,
                volume=Decimal("1.00"),
                profit=Decimal("-10.00"),
                close_time=datetime.now(UTC),
                close_price=Decimal("1.1"),
                r_multiple=None,
                ingest_batch_id=batch.id,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        r_multiples = await bot_r_multiples(db_session, bot.id)  # type: ignore[arg-type]
        assert r_multiples == [Decimal("2.0")]
