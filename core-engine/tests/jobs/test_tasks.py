from datetime import UTC, datetime, timedelta
from decimal import Decimal

import fakeredis
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import SemaphoreState
from core.db.models.decisions import Alert, KillSwitchEvent
from core.jobs import tasks
from tests.factories import (
    AccountFactory,
    BaselineFactory,
    BotFactory,
    EquitySnapshotFactory,
    IngestBatchFactory,
    TradeFactory,
)


def _ctx(db_connection: AsyncConnection, redis: object) -> dict[str, object]:
    def _session_factory() -> AsyncSession:
        return AsyncSession(
            bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )

    return {"session_factory": _session_factory, "redis": redis}


async def test_task_run_watchdog_creates_alert_for_dead_bot(db_connection: AsyncConnection) -> None:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    account = AccountFactory()
    session.add(account)
    await session.flush()
    bot = BotFactory(account_id=account.id)
    session.add(bot)
    await session.flush()
    baseline = BaselineFactory(bot_id=bot.id, expected_trades_30d=10)
    session.add(baseline)
    await session.flush()
    bot.baseline_id = baseline.id
    await session.commit()

    redis = fakeredis.FakeAsyncRedis()
    await tasks.task_run_watchdog(_ctx(db_connection, redis))

    alert = (
        await session.execute(select(Alert).where(Alert.dedup_key == f"watchdog:{bot.id}"))
    ).scalar_one()
    assert alert is not None
    await redis.aclose()


async def test_task_run_killswitch_sweep_escalates_on_real_drawdown(
    db_connection: AsyncConnection,
) -> None:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    account = AccountFactory(is_demo=False)
    session.add(account)
    await session.flush()
    now = datetime.now(UTC)
    session.add(
        EquitySnapshotFactory(
            account_id=account.id, ts=now - timedelta(days=5), equity=Decimal("100000")
        )
    )
    session.add(EquitySnapshotFactory(account_id=account.id, ts=now, equity=Decimal("75000")))
    await session.commit()

    redis = fakeredis.FakeAsyncRedis()
    await tasks.task_run_killswitch_sweep(_ctx(db_connection, redis))

    event = (
        await session.execute(select(KillSwitchEvent).order_by(KillSwitchEvent.ts.desc()).limit(1))
    ).scalar_one()
    assert event.level == 4
    await redis.aclose()


async def test_task_run_config_drift_flags_orange_bot_in_real_mode(
    db_connection: AsyncConnection,
) -> None:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    account = AccountFactory()
    session.add(account)
    await session.flush()
    bot = BotFactory(account_id=account.id, semaphore_state=SemaphoreState.NARANJA)
    session.add(bot)
    await session.flush()
    batch = IngestBatchFactory(account_id=account.id)
    session.add(batch)
    await session.flush()
    from tests.factories import EaStateFactory

    session.add(
        EaStateFactory(
            account_id=account.id,
            magic_number=bot.magic_number,
            mode="REAL",
            ingest_batch_id=batch.id,
        )
    )
    await session.commit()

    redis = fakeredis.FakeAsyncRedis()
    await tasks.task_run_config_drift(_ctx(db_connection, redis))

    alert = (
        await session.execute(select(Alert).where(Alert.dedup_key == f"config_drift:{bot.id}"))
    ).scalar_one()
    assert alert is not None
    await redis.aclose()


async def test_task_run_montecarlo_check_persists_a_run_for_a_due_bot(
    db_connection: AsyncConnection,
) -> None:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    account = AccountFactory()
    session.add(account)
    await session.flush()
    bot = BotFactory(account_id=account.id)
    session.add(bot)
    await session.flush()
    batch = IngestBatchFactory(account_id=account.id)
    session.add(batch)
    await session.flush()
    now = datetime.now(UTC)
    session.add(
        TradeFactory(
            bot_id=bot.id,
            account_id=account.id,
            magic_number=bot.magic_number,
            close_time=now - timedelta(days=1),
            close_price=Decimal("1.1"),
            profit=Decimal("5.00"),
            ingest_batch_id=batch.id,
        )
    )
    await session.commit()

    redis = fakeredis.FakeAsyncRedis()
    await tasks.task_run_montecarlo_check(_ctx(db_connection, redis))

    from core.db.models.governance import MonteCarloRun

    run = (
        await session.execute(select(MonteCarloRun).where(MonteCarloRun.bot_id == bot.id))
    ).scalar_one()
    assert run is not None
    await redis.aclose()


async def test_task_evaluate_impulses_closes_a_due_impulse(db_connection: AsyncConnection) -> None:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    account = AccountFactory()
    session.add(account)
    await session.flush()
    bot = BotFactory(account_id=account.id)
    session.add(bot)
    await session.flush()
    from core.db.enums import ImpulseAction, ImpulseStatus
    from core.db.models.decisions import ImpulseLog

    now = datetime.now(UTC)
    impulse = ImpulseLog(
        ts=now - timedelta(days=8),
        bot_id=bot.id,
        description="d",
        desired_action=ImpulseAction.PAUSE_BOT,
        executed=False,
        status=ImpulseStatus.PENDING,
    )
    session.add(impulse)
    await session.commit()

    redis = fakeredis.FakeAsyncRedis()
    await tasks.task_evaluate_impulses(_ctx(db_connection, redis))

    await session.refresh(impulse)
    assert impulse.status == ImpulseStatus.CLOSED
    await redis.aclose()


class _FixedHourDatetime(datetime):
    _fixed_hour: int = 20

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        return datetime(2026, 8, 26, cls._fixed_hour, 0, 0, tzinfo=tz)


async def test_task_maybe_send_digest_noop_outside_the_configured_hour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.jobs.tasks as tasks_module

    class _WrongHour(_FixedHourDatetime):
        _fixed_hour = 9

    monkeypatch.setattr(tasks_module, "datetime", _WrongHour)  # type: ignore[attr-defined]
    redis = fakeredis.FakeAsyncRedis()
    await redis.rpush("telegram:digest:pending", '{"message": "no deberia tocarse"}')

    await tasks_module.task_maybe_send_digest({"redis": redis})

    remaining = await redis.lrange("telegram:digest:pending", 0, -1)
    assert len(remaining) == 1
    await redis.aclose()


async def test_task_maybe_send_digest_drains_the_queue_at_the_configured_hour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import core.jobs.tasks as tasks_module

    class _RightHour(_FixedHourDatetime):
        _fixed_hour = 20

    monkeypatch.setattr(tasks_module, "datetime", _RightHour)  # type: ignore[attr-defined]
    redis = fakeredis.FakeAsyncRedis()
    await redis.rpush("telegram:digest:pending", '{"message": "alerta 1"}')
    await redis.rpush("telegram:digest:pending", '{"message": "alerta 2"}')

    await tasks_module.task_maybe_send_digest({"redis": redis})

    remaining = await redis.lrange("telegram:digest:pending", 0, -1)
    assert remaining == []
    await redis.aclose()
