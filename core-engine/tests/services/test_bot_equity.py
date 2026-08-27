"""G10 (docs/backlog.md): curva de P&L acumulado sintetica por bot +
posiciones abiertas por bot. CAVEAT probado aqui tal cual el docstring de
`services/bot_equity.py`: es SUM(Trade.profit) acumulado, no equity real
de cuenta a nivel de bot (eso no existe -- EquitySnapshot es por
account_id)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from core.db.enums import TradeType
from core.services.bot_equity import bot_open_positions, bot_pnl_curve
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
