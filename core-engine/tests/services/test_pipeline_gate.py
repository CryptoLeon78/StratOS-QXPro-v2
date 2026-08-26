from datetime import UTC, datetime, timedelta
from decimal import Decimal

import fakeredis

from core.db.enums import PipelinePhase, Verdict
from core.db.models.pipeline import PipelineCandidate
from core.services.pipeline_gate import assemble_metrics, evaluate_and_persist
from core.state_machines.types import PipelineGateConfig
from tests.factories import AccountFactory, BotFactory, IngestBatchFactory, TradeFactory

CONFIG = PipelineGateConfig()


async def _account_bot_batch(db_session: object) -> tuple[object, object, object]:
    account = AccountFactory()
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    bot = BotFactory(account_id=account.id, pipeline_phase=PipelinePhase.F4)
    db_session.add(bot)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    batch = IngestBatchFactory(account_id=account.id)
    db_session.add(batch)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return account, bot, batch


async def _seed_go_worthy_trades(
    db_session: object, account: object, bot: object, batch: object, now: datetime
) -> None:
    for i in range(30):
        is_loss = i % 5 == 0
        profit = Decimal("-2.00") if is_loss else Decimal("10.00")
        r_multiple = Decimal("-0.50") if is_loss else Decimal("1.00")
        close_time = now - timedelta(days=90 - i * 3)
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,  # type: ignore[attr-defined]
                account_id=account.id,  # type: ignore[attr-defined]
                magic_number=bot.magic_number,  # type: ignore[attr-defined]
                open_time=close_time - timedelta(hours=1),
                close_time=close_time,
                close_price=Decimal("1.1"),
                profit=profit,
                commission=Decimal("0.00"),
                swap=Decimal("0.00"),
                r_multiple=r_multiple,
                ingest_batch_id=batch.id,  # type: ignore[attr-defined]
            )
        )
    await db_session.flush()  # type: ignore[attr-defined]


class TestAssembleMetrics:
    async def test_metrics_reflect_real_closed_trades(self, db_session: object) -> None:
        account, bot, batch = await _account_bot_batch(db_session)
        now = datetime.now(UTC)
        await _seed_go_worthy_trades(db_session, account, bot, batch, now)
        candidate = PipelineCandidate(
            bot_id=bot.id,  # type: ignore[attr-defined]
            current_phase=PipelinePhase.F4,
            entered_phase_at=now - timedelta(days=90),
            incubation_days=0,
            oos_trades=0,
        )
        db_session.add(candidate)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        metrics = await assemble_metrics(db_session, candidate, now)  # type: ignore[arg-type]
        assert metrics.oos_trades == 30
        assert metrics.profit_factor > 1.5
        assert metrics.expectancy_r > 0.15
        assert metrics.sharpe > 1.0
        assert metrics.max_dd_pct < 20.0
        assert metrics.trades_per_week >= 2.0
        assert metrics.incubation_days == 90

    async def test_missing_r_multiples_fall_back_to_zero_expectancy(
        self, db_session: object
    ) -> None:
        account, bot, batch = await _account_bot_batch(db_session)
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                close_time=now - timedelta(days=1),
                close_price=Decimal("1.1"),
                profit=Decimal("10.00"),
                r_multiple=None,
                ingest_batch_id=batch.id,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]
        candidate = PipelineCandidate(
            bot_id=bot.id,
            current_phase=PipelinePhase.F4,
            entered_phase_at=now - timedelta(days=10),
            incubation_days=0,
            oos_trades=0,
        )
        db_session.add(candidate)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        metrics = await assemble_metrics(db_session, candidate, now)  # type: ignore[arg-type]
        assert metrics.expectancy_r == 0.0


class TestEvaluateAndPersist:
    async def test_go_worthy_history_persists_go_and_raw_metrics(self, db_session: object) -> None:
        account, bot, batch = await _account_bot_batch(db_session)
        now = datetime.now(UTC)
        await _seed_go_worthy_trades(db_session, account, bot, batch, now)
        candidate = PipelineCandidate(
            bot_id=bot.id,  # type: ignore[attr-defined]
            current_phase=PipelinePhase.F4,
            entered_phase_at=now - timedelta(days=90),
            incubation_days=0,
            oos_trades=0,
        )
        db_session.add(candidate)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        result = await evaluate_and_persist(db_session, redis, candidate, CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        assert result.verdict == Verdict.GO.value
        assert candidate.verdict == Verdict.GO
        assert candidate.oos_trades == 30
        assert candidate.profit_factor is not None and candidate.profit_factor > 1.5
        await redis.aclose()

    async def test_too_few_trades_and_days_persists_kill(self, db_session: object) -> None:
        # 3 criterios fallan a la vez (muestra, incubacion, frecuencia) ->
        # KILL por la regla "len(failing) >= 2" de evaluate_pipeline_gate
        # (G3), no HOLD -- comportamiento correcto, no un bug de este test.
        account, bot, batch = await _account_bot_batch(db_session)
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                close_time=now - timedelta(days=1),
                close_price=Decimal("1.1"),
                profit=Decimal("10.00"),
                ingest_batch_id=batch.id,
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]
        candidate = PipelineCandidate(
            bot_id=bot.id,
            current_phase=PipelinePhase.F4,
            entered_phase_at=now - timedelta(days=5),
            incubation_days=0,
            oos_trades=0,
        )
        db_session.add(candidate)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        redis = fakeredis.FakeAsyncRedis()
        result = await evaluate_and_persist(db_session, redis, candidate, CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        assert result.verdict == Verdict.KILL.value
        await redis.aclose()
