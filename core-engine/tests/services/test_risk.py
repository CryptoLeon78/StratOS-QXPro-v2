from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import TradeType
from core.services.risk import (
    ExposureRow,
    RiskServiceConfig,
    compute_exposure,
    compute_tail_risk,
    exposure_subtotals_by_currency,
)
from tests.factories import AccountFactory, BotFactory, IngestBatchFactory, TradeFactory

CONFIG = RiskServiceConfig(window_days=15)


async def _real_account(db_session: object) -> object:
    account = AccountFactory(is_demo=False)
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return account


async def _snapshot_series(
    db_session: object, account: object, equities: list[Decimal], now: datetime
) -> None:
    from tests.factories import EquitySnapshotFactory

    n = len(equities)
    for i, equity in enumerate(equities):
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(
                account_id=account.id,  # type: ignore[attr-defined]
                ts=now - timedelta(days=n - i),
                equity=equity,
                balance=equity,
            )
        )
    await db_session.flush()  # type: ignore[attr-defined]


class TestComputeTailRisk:
    async def test_returns_none_when_no_real_account_data(self, db_session: object) -> None:
        account = AccountFactory(is_demo=True)
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        equities = [Decimal("10000") * Decimal(str(1 + 0.5 * i)) for i in range(16)]
        await _snapshot_series(db_session, account, equities, datetime.now(UTC))
        result = await compute_tail_risk(db_session, CONFIG, datetime.now(UTC))  # type: ignore[arg-type]
        assert result is None

    async def test_calm_equity_curve_stays_within_gates(self, db_session: object) -> None:
        account = await _real_account(db_session)
        now = datetime.now(UTC)
        # oscila entre pequenas ganancias y perdidas (no monotona) para que
        # VaR/CVaR reflejen perdidas reales, con magnitud pequena para
        # quedar comodamente dentro de los gates.
        daily_pct = [
            Decimal("1.001"),
            Decimal("0.9993"),
            Decimal("1.0012"),
            Decimal("0.9988"),
            Decimal("1.0006"),
        ]
        equity = Decimal("10000")
        equities = [equity]
        for i in range(15):
            equity = equity * daily_pct[i % len(daily_pct)]
            equities.append(equity)
        await _snapshot_series(db_session, account, equities, now)

        result = await compute_tail_risk(db_session, CONFIG, now)  # type: ignore[arg-type]
        assert result is not None
        assert result.breached is False
        assert result.var95_daily >= 0
        assert result.cvar99_daily >= result.var99_daily
        assert result.var99_monthly == result.var99_daily * (21**0.5)
        assert result.cvar99_annual == result.cvar99_daily * (252**0.5)

    async def test_a_large_daily_drop_breaches_the_gate(self, db_session: object) -> None:
        account = await _real_account(db_session)
        now = datetime.now(UTC)
        equities = [Decimal("10000")] * 8 + [Decimal("7500")] + [Decimal("7500")] * 7
        await _snapshot_series(db_session, account, equities, now)

        result = await compute_tail_risk(db_session, CONFIG, now)  # type: ignore[arg-type]
        assert result is not None
        assert result.breached is True
        assert result.cvar99_daily > CONFIG.cvar99_daily_gate_pct


class TestComputeExposure:
    async def test_aggregates_open_positions_by_symbol_net_and_gross(
        self, db_session: object
    ) -> None:
        account = await _real_account(db_session)
        bot = BotFactory(account_id=account.id)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        batch = IngestBatchFactory(account_id=account.id)
        db_session.add(batch)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("50.00"),
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
                volume=Decimal("0.40"),
                profit=Decimal("-10.00"),
                close_time=None,
                ingest_batch_id=batch.id,
            )
        )
        # cerrada -- no debe contar
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("5.00"),
                profit=Decimal("999.00"),
                close_time=datetime.now(UTC),
                close_price=Decimal("1.1"),
                ingest_batch_id=batch.id,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        rows = await compute_exposure(db_session)  # type: ignore[arg-type]
        row = next(r for r in rows if r.symbol == "EURUSD")
        assert row.net_volume == Decimal("0.60")
        assert row.gross_volume == Decimal("1.40")
        assert row.pnl == Decimal("40.00")
        assert row.currency == "EUR"  # symbol_currency, sembrado en la migracion 288e484ba382


async def test_compute_exposure_currency_is_none_for_an_unmapped_symbol(
    db_session: AsyncSession,
) -> None:
    account = AccountFactory()  # type: ignore[call-arg]
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    bot = BotFactory(account_id=account.id)  # type: ignore[call-arg]
    db_session.add(bot)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    batch = IngestBatchFactory(account_id=account.id)  # type: ignore[call-arg]
    db_session.add(batch)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]

    db_session.add(  # type: ignore[attr-defined]
        TradeFactory(
            bot_id=bot.id,
            account_id=account.id,
            magic_number=bot.magic_number,
            symbol="ZZZUNKNOWN",
            type=TradeType.BUY,
            volume=Decimal("1.00"),
            profit=Decimal("10.00"),
            close_time=None,
            ingest_batch_id=batch.id,
        )
    )
    await db_session.flush()  # type: ignore[attr-defined]

    rows = await compute_exposure(db_session)  # type: ignore[arg-type]
    row = next(r for r in rows if r.symbol == "ZZZUNKNOWN")
    assert row.currency is None  # sin fila en symbol_currency, no inventado


async def test_exposure_subtotals_by_currency_groups_native_units(db_session: AsyncSession) -> None:
    rows = [
        ExposureRow(
            symbol="EURUSD",
            net_volume=Decimal("1"),
            gross_volume=Decimal("1"),
            pnl=Decimal("10"),
            currency="EUR",
        ),
        ExposureRow(
            symbol="XAUUSD",
            net_volume=Decimal("2"),
            gross_volume=Decimal("2"),
            pnl=Decimal("20"),
            currency="USD",
        ),
        ExposureRow(
            symbol="XAGUSD",
            net_volume=Decimal("1"),
            gross_volume=Decimal("1"),
            pnl=Decimal("5"),
            currency="USD",
        ),
        ExposureRow(
            symbol="ZZZUNKNOWN",
            net_volume=Decimal("1"),
            gross_volume=Decimal("1"),
            pnl=Decimal("1"),
            currency=None,
        ),
    ]
    subtotals = exposure_subtotals_by_currency(rows)
    assert subtotals["USD"].gross_volume == Decimal("3")
    assert subtotals["USD"].pnl == Decimal("25")
    assert subtotals["EUR"].pnl == Decimal("10")
    assert "ZZZUNKNOWN" not in subtotals  # sin divisa, fuera del agrupado (no inventado)
