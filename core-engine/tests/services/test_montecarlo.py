from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from core.db.models.governance import MonteCarloRun
from core.services.montecarlo import (
    MonteCarloServiceConfig,
    bots_due_for_recalc,
    run_montecarlo_for_bot,
)
from tests.factories import AccountFactory, BotFactory, IngestBatchFactory, TradeFactory

CONFIG = MonteCarloServiceConfig(n_sims=50, seed=42, recalc_every_trades=50)


async def _account_and_bot(db_session: object) -> tuple[object, object]:
    account = AccountFactory()
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    bot = BotFactory(account_id=account.id)
    db_session.add(bot)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return account, bot


async def _closed_trade(
    db_session: object,
    account: object,
    bot: object,
    batch: object,
    profit: Decimal,
    closed_at: datetime,
) -> None:
    db_session.add(  # type: ignore[attr-defined]
        TradeFactory(
            bot_id=bot.id,  # type: ignore[attr-defined]
            account_id=account.id,  # type: ignore[attr-defined]
            magic_number=bot.magic_number,  # type: ignore[attr-defined]
            open_time=closed_at - timedelta(hours=1),
            close_time=closed_at,
            close_price=Decimal("1.0"),
            profit=profit,
            ingest_batch_id=batch.id,  # type: ignore[attr-defined]
        )
    )


class TestBotsDueForRecalc:
    async def test_bot_without_any_run_is_due(self, db_session: object) -> None:
        _, bot = await _account_and_bot(db_session)
        due = await bots_due_for_recalc(db_session, CONFIG, datetime.now(UTC))  # type: ignore[arg-type]
        assert bot.id in {b.id for b in due}

    async def test_bot_with_recent_run_and_few_trades_is_not_due(self, db_session: object) -> None:
        account, bot = await _account_and_bot(db_session)
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            MonteCarloRun(
                bot_id=bot.id,
                ts=now - timedelta(days=1),
                n_simulations=50,
                dd_p50=Decimal("2.0"),
                dd_p75=Decimal("3.0"),
                dd_p95=Decimal("4.0"),
                dd_contract_pct=Decimal("4.0"),
                seed=42,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]
        due = await bots_due_for_recalc(db_session, CONFIG, now)  # type: ignore[arg-type]
        assert bot.id not in {b.id for b in due}

    async def test_bot_with_run_older_than_a_month_is_due(self, db_session: object) -> None:
        _, bot = await _account_and_bot(db_session)
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            MonteCarloRun(
                bot_id=bot.id,
                ts=now - timedelta(days=31),
                n_simulations=50,
                dd_p50=Decimal("2.0"),
                dd_p75=Decimal("3.0"),
                dd_p95=Decimal("4.0"),
                dd_contract_pct=Decimal("4.0"),
                seed=42,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]
        due = await bots_due_for_recalc(db_session, CONFIG, now)  # type: ignore[arg-type]
        assert bot.id in {b.id for b in due}

    async def test_bot_with_50_trades_since_last_run_is_due(self, db_session: object) -> None:
        account, bot = await _account_and_bot(db_session)
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            MonteCarloRun(
                bot_id=bot.id,
                ts=now - timedelta(days=1),
                n_simulations=50,
                dd_p50=Decimal("2.0"),
                dd_p75=Decimal("3.0"),
                dd_p95=Decimal("4.0"),
                dd_contract_pct=Decimal("4.0"),
                seed=42,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]
        batch = IngestBatchFactory(account_id=account.id)
        db_session.add(batch)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        for i in range(50):
            await _closed_trade(
                db_session, account, bot, batch, Decimal("1.0"), now - timedelta(minutes=i)
            )
        await db_session.flush()  # type: ignore[attr-defined]
        due = await bots_due_for_recalc(db_session, CONFIG, now)  # type: ignore[arg-type]
        assert bot.id in {b.id for b in due}


class TestRunMontecarloForBot:
    async def test_bot_with_no_closed_trades_is_skipped(self, db_session: object) -> None:
        _, bot = await _account_and_bot(db_session)
        result = await run_montecarlo_for_bot(db_session, bot, CONFIG, datetime.now(UTC))  # type: ignore[arg-type]
        assert result is None

    async def test_persists_run_with_contract_equal_to_p95(self, db_session: object) -> None:
        account, bot = await _account_and_bot(db_session)
        batch = IngestBatchFactory(account_id=account.id)
        db_session.add(batch)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        now = datetime.now(UTC)
        pnls = [Decimal("10"), Decimal("-15"), Decimal("8"), Decimal("-5"), Decimal("12")]
        for i, pnl in enumerate(pnls):
            await _closed_trade(db_session, account, bot, batch, pnl, now - timedelta(hours=i))
        await db_session.flush()  # type: ignore[attr-defined]

        run = await run_montecarlo_for_bot(db_session, bot, CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]
        assert run is not None
        assert run.dd_contract_pct == run.dd_p95
        assert run.n_simulations == CONFIG.n_sims
        assert run.seed == CONFIG.seed

        persisted = (
            await db_session.execute(select(MonteCarloRun).where(MonteCarloRun.bot_id == bot.id))  # type: ignore[attr-defined]
        ).scalar_one()
        assert persisted.dd_p95 == run.dd_p95

    async def test_is_reproducible_for_the_same_trade_history_and_seed(
        self, db_session: object
    ) -> None:
        account, bot = await _account_and_bot(db_session)
        batch = IngestBatchFactory(account_id=account.id)
        db_session.add(batch)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        now = datetime.now(UTC)
        pnls = [Decimal("10"), Decimal("-15"), Decimal("8"), Decimal("-5"), Decimal("12")]
        for i, pnl in enumerate(pnls):
            await _closed_trade(db_session, account, bot, batch, pnl, now - timedelta(hours=i))
        await db_session.flush()  # type: ignore[attr-defined]

        first = await run_montecarlo_for_bot(db_session, bot, CONFIG, now)  # type: ignore[arg-type]
        second = await run_montecarlo_for_bot(db_session, bot, CONFIG, now)  # type: ignore[arg-type]
        assert first is not None
        assert second is not None
        assert first.dd_p50 == second.dd_p50
        assert first.dd_p95 == second.dd_p95
