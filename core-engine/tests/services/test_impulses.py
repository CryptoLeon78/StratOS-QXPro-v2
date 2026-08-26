from datetime import UTC, datetime, timedelta
from decimal import Decimal

from core.db.enums import ImpulseAction, ImpulseStatus
from core.db.models.decisions import ImpulseLog
from core.services.impulses import (
    ImpulseServiceConfig,
    create_impulse,
    evaluate_pending_impulses,
    quarterly_report,
)
from tests.factories import AccountFactory, BotFactory, IngestBatchFactory, TradeFactory

CONFIG = ImpulseServiceConfig(eval_days=7)


async def _account_and_bot(db_session: object) -> tuple[object, object]:
    account = AccountFactory()
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    bot = BotFactory(account_id=account.id)
    db_session.add(bot)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return account, bot


class TestCreateImpulse:
    async def test_persists_pending_impulse(self, db_session: object) -> None:
        _, bot = await _account_and_bot(db_session)
        now = datetime.now(UTC)
        impulse = await create_impulse(  # type: ignore[arg-type]
            db_session, bot.id, "quiero cerrar la posicion", ImpulseAction.CLOSE_POSITION, now
        )
        assert impulse.status == ImpulseStatus.PENDING
        assert impulse.executed is False


class TestEvaluatePendingImpulses:
    async def test_ignores_impulses_not_yet_due(self, db_session: object) -> None:
        _, bot = await _account_and_bot(db_session)
        now = datetime.now(UTC)
        impulse = await create_impulse(  # type: ignore[arg-type]
            db_session, bot.id, "d", ImpulseAction.PAUSE_BOT, now - timedelta(days=1)
        )
        await evaluate_pending_impulses(db_session, CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]
        refreshed = await db_session.get(ImpulseLog, impulse.id)  # type: ignore[attr-defined]
        assert refreshed.status == ImpulseStatus.PENDING

    async def test_pause_bot_avoided_cost_equals_real_result(self, db_session: object) -> None:
        account, bot = await _account_and_bot(db_session)
        now = datetime.now(UTC)
        impulse_ts = now - timedelta(days=7, hours=1)
        impulse = await create_impulse(  # type: ignore[arg-type]
            db_session, bot.id, "pausar el bot", ImpulseAction.PAUSE_BOT, impulse_ts
        )
        batch = IngestBatchFactory(account_id=account.id)
        db_session.add(batch)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        for i, profit in enumerate([Decimal("30"), Decimal("-10")]):
            db_session.add(  # type: ignore[attr-defined]
                TradeFactory(
                    bot_id=bot.id,
                    account_id=account.id,
                    magic_number=bot.magic_number,
                    close_time=impulse_ts + timedelta(days=1 + i),
                    close_price=Decimal("1.1"),
                    profit=profit,
                    commission=Decimal("0.00"),
                    swap=Decimal("0.00"),
                    ingest_batch_id=batch.id,
                )
            )
        await db_session.flush()  # type: ignore[attr-defined]

        await evaluate_pending_impulses(db_session, CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        refreshed = await db_session.get(ImpulseLog, impulse.id)  # type: ignore[attr-defined]
        assert refreshed.status == ImpulseStatus.CLOSED
        assert refreshed.counterfactual_result_7d_eur == Decimal("20")
        # PAUSE_BOT: simulado=0 -> avoided_cost = real - 0 = real
        assert refreshed.avoided_cost_eur == Decimal("20")
        assert refreshed.evaluated_at is not None


class TestQuarterlyReport:
    async def test_sums_avoided_cost_for_closed_impulses_in_quarter(
        self, db_session: object
    ) -> None:
        _, bot = await _account_and_bot(db_session)
        in_quarter = datetime(2026, 8, 10, tzinfo=UTC)
        db_session.add(  # type: ignore[attr-defined]
            ImpulseLog(
                ts=in_quarter,
                bot_id=bot.id,
                description="d1",
                desired_action=ImpulseAction.PAUSE_BOT,
                executed=False,
                status=ImpulseStatus.CLOSED,
                counterfactual_result_7d_eur=Decimal("100"),
                avoided_cost_eur=Decimal("400.30"),
                evaluated_at=in_quarter + timedelta(days=7),
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            ImpulseLog(
                ts=in_quarter,
                bot_id=bot.id,
                description="d2",
                desired_action=ImpulseAction.PAUSE_BOT,
                executed=False,
                status=ImpulseStatus.CLOSED,
                counterfactual_result_7d_eur=Decimal("50"),
                avoided_cost_eur=Decimal("254.50"),
                evaluated_at=in_quarter + timedelta(days=7),
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            ImpulseLog(
                ts=datetime(2026, 1, 1, tzinfo=UTC),
                bot_id=bot.id,
                description="fuera de trimestre",
                desired_action=ImpulseAction.PAUSE_BOT,
                executed=False,
                status=ImpulseStatus.CLOSED,
                counterfactual_result_7d_eur=Decimal("999"),
                avoided_cost_eur=Decimal("999"),
                evaluated_at=datetime(2026, 1, 8, tzinfo=UTC),
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        report = await quarterly_report(db_session, "2026-Q3")  # type: ignore[arg-type]
        assert report.count == 2
        assert report.total_avoided_cost_eur == Decimal("654.80")
