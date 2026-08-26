from datetime import UTC, datetime

import fakeredis
from sqlalchemy import select

from core.db.enums import AlertLevel, SemaphoreState
from core.db.models.decisions import Alert
from core.services.config_drift import compute_drift, compute_orphans_and_missing, run_drift_check
from tests.factories import AccountFactory, BotFactory, EaStateFactory, IngestBatchFactory


async def _account(db_session: object) -> object:
    account = AccountFactory()
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return account


async def _ea_state(db_session: object, account: object, magic: int, mode: str) -> None:
    batch = IngestBatchFactory(account_id=account.id)  # type: ignore[attr-defined]
    db_session.add(batch)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    db_session.add(  # type: ignore[attr-defined]
        EaStateFactory(
            account_id=account.id,  # type: ignore[attr-defined]
            magic_number=magic,
            mode=mode,
            ingest_batch_id=batch.id,
        )
    )
    await db_session.flush()  # type: ignore[attr-defined]


class TestComputeDrift:
    async def test_orange_bot_still_in_real_mode_is_drift(self, db_session: object) -> None:
        account = await _account(db_session)
        bot = BotFactory(account_id=account.id, semaphore_state=SemaphoreState.NARANJA)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        await _ea_state(db_session, account, bot.magic_number, "REAL")

        rows = await compute_drift(db_session)  # type: ignore[arg-type]
        row = next(r for r in rows if r.bot_id == bot.id)
        assert row.drift is True
        assert row.expected_mode == "PAPER"
        assert row.reported_mode == "REAL"

    async def test_orange_bot_correctly_in_paper_mode_is_not_drift(
        self, db_session: object
    ) -> None:
        account = await _account(db_session)
        bot = BotFactory(account_id=account.id, semaphore_state=SemaphoreState.NARANJA)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        await _ea_state(db_session, account, bot.magic_number, "PAPER")

        rows = await compute_drift(db_session)  # type: ignore[arg-type]
        row = next(r for r in rows if r.bot_id == bot.id)
        assert row.drift is False

    async def test_green_bot_in_real_mode_is_not_drift(self, db_session: object) -> None:
        account = await _account(db_session)
        bot = BotFactory(account_id=account.id, semaphore_state=SemaphoreState.VERDE)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        await _ea_state(db_session, account, bot.magic_number, "REAL")

        rows = await compute_drift(db_session)  # type: ignore[arg-type]
        row = next(r for r in rows if r.bot_id == bot.id)
        assert row.drift is False

    async def test_bot_without_ea_state_is_excluded(self, db_session: object) -> None:
        account = await _account(db_session)
        bot = BotFactory(account_id=account.id)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        rows = await compute_drift(db_session)  # type: ignore[arg-type]
        assert all(r.bot_id != bot.id for r in rows)


class TestComputeOrphansAndMissing:
    async def test_ea_state_without_bot_is_orphan(self, db_session: object) -> None:
        account = await _account(db_session)
        await _ea_state(db_session, account, 999888, "REAL")

        report = await compute_orphans_and_missing(db_session)  # type: ignore[arg-type]
        assert (account.id, 999888) in report.orphan_magics

    async def test_bot_without_ea_state_is_missing(self, db_session: object) -> None:
        account = await _account(db_session)
        bot = BotFactory(account_id=account.id)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]

        report = await compute_orphans_and_missing(db_session)  # type: ignore[arg-type]
        assert (account.id, bot.magic_number) in report.missing_magics


class TestRunDriftCheck:
    async def test_mode_drift_creates_critica_alert(self, db_session: object) -> None:
        account = await _account(db_session)
        bot = BotFactory(account_id=account.id, semaphore_state=SemaphoreState.NARANJA)
        db_session.add(bot)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        await _ea_state(db_session, account, bot.magic_number, "REAL")

        redis = fakeredis.FakeAsyncRedis()
        now = datetime.now(UTC)
        await run_drift_check(db_session, redis, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        alert = (
            await db_session.execute(  # type: ignore[attr-defined]
                select(Alert).where(Alert.dedup_key == f"config_drift:{bot.id}")
            )
        ).scalar_one()
        assert alert.level == AlertLevel.CRITICA
        await redis.aclose()
