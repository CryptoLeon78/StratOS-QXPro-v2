from datetime import UTC, datetime, timedelta
from decimal import Decimal

import fakeredis
from sqlalchemy import select

from core.db.models.decisions import KillSwitchEvent
from core.services.killswitch_sweep import (
    KillSwitchSweepConfig,
    compute_portfolio_dd_pct,
    current_episode_stats,
    sweep_portfolio,
)
from core.state_machines.types import KillSwitchConfig
from tests.factories import AccountFactory, EquitySnapshotFactory

CONFIG = KillSwitchConfig()
SWEEP_CONFIG = KillSwitchSweepConfig(equity_lookback_days=3650)


async def _real_account(db_session: object) -> object:
    account = AccountFactory(is_demo=False)
    db_session.add(account)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    return account


async def _seed_equity(
    db_session: object, account: object, values: list[tuple[int, Decimal]], now: datetime
) -> None:
    for days_ago, equity in values:
        db_session.add(  # type: ignore[attr-defined]
            EquitySnapshotFactory(
                account_id=account.id,  # type: ignore[attr-defined]
                ts=now - timedelta(days=days_ago),
                equity=equity,
                balance=equity,
            )
        )
    await db_session.flush()  # type: ignore[attr-defined]


class TestComputePortfolioDdPct:
    async def test_computes_peak_to_current_drawdown(self, db_session: object) -> None:
        account = await _real_account(db_session)
        now = datetime.now(UTC)
        await _seed_equity(
            db_session,
            account,
            [(10, Decimal("100000")), (5, Decimal("110000")), (0, Decimal("88000"))],
            now,
        )
        dd = await compute_portfolio_dd_pct(db_session, SWEEP_CONFIG, now)  # type: ignore[arg-type]
        assert dd is not None
        assert dd == Decimal(str((110000 - 88000) / 110000 * 100))

    async def test_no_data_returns_none(self, db_session: object) -> None:
        dd = await compute_portfolio_dd_pct(db_session, SWEEP_CONFIG, datetime.now(UTC))  # type: ignore[arg-type]
        assert dd is None


class TestSweepPortfolio:
    async def test_crash_21_style_drop_can_jump_directly_to_l4(self, db_session: object) -> None:
        # PARTE 13 (crash_21): un corte severo debe poder escalar de L0
        # directo a L4 sin pasar visiblemente por L1-L3 (docstring de
        # evaluate_killswitch_escalation, G3).
        account = await _real_account(db_session)
        now = datetime.now(UTC)
        await _seed_equity(
            db_session,
            account,
            [(10, Decimal("100000")), (0, Decimal("75000"))],  # DD=25% >= kill_l4=20
            now,
        )

        redis = fakeredis.FakeAsyncRedis()
        await sweep_portfolio(db_session, redis, CONFIG, SWEEP_CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        from core.db.models.decisions import KillSwitchEvent

        event = (
            await db_session.execute(  # type: ignore[attr-defined]
                select(KillSwitchEvent).order_by(KillSwitchEvent.ts.desc()).limit(1)
            )
        ).scalar_one()
        assert event.level == 4
        await redis.aclose()

    async def test_no_data_is_a_noop(self, db_session: object) -> None:
        redis = fakeredis.FakeAsyncRedis()
        now = datetime.now(UTC)
        await sweep_portfolio(db_session, redis, CONFIG, SWEEP_CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        from core.db.models.decisions import KillSwitchEvent

        rows = (
            (await db_session.execute(select(KillSwitchEvent)))  # type: ignore[attr-defined]
            .scalars()
            .all()
        )
        assert rows == []
        await redis.aclose()

    async def test_small_drop_stays_below_l1_and_creates_no_event(self, db_session: object) -> None:
        account = await _real_account(db_session)
        now = datetime.now(UTC)
        await _seed_equity(
            db_session,
            account,
            [(10, Decimal("100000")), (0, Decimal("97000"))],  # DD=3% < kill_l1=8
            now,
        )

        redis = fakeredis.FakeAsyncRedis()
        await sweep_portfolio(db_session, redis, CONFIG, SWEEP_CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        from core.db.models.decisions import KillSwitchEvent

        rows = (
            (await db_session.execute(select(KillSwitchEvent)))  # type: ignore[attr-defined]
            .scalars()
            .all()
        )
        assert rows == []
        await redis.aclose()


class TestCurrentEpisodeStats:
    async def test_no_events_returns_none(self, db_session: object) -> None:
        assert await current_episode_stats(db_session, datetime.now(UTC)) is None  # type: ignore[arg-type]

    async def test_latest_level_zero_returns_none(self, db_session: object) -> None:
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            KillSwitchEvent(
                ts=now - timedelta(hours=1),
                level=0,
                portfolio_dd_pct=Decimal("2"),
                actions={},
                instruction_text="",
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]
        assert await current_episode_stats(db_session, now) is None  # type: ignore[arg-type]

    async def test_computes_max_dd_and_duration_of_the_active_episode(
        self, db_session: object
    ) -> None:
        now = datetime.now(UTC)
        started = now - timedelta(hours=3)
        db_session.add(  # type: ignore[attr-defined]
            KillSwitchEvent(
                ts=started,
                level=1,
                portfolio_dd_pct=Decimal("8"),
                actions={},
                instruction_text="",
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            KillSwitchEvent(
                ts=started + timedelta(hours=1),
                level=2,
                portfolio_dd_pct=Decimal("12"),
                actions={},
                instruction_text="",
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            KillSwitchEvent(
                ts=now,
                level=2,
                portfolio_dd_pct=Decimal("10"),  # bajo del pico, pero max sigue siendo 12
                actions={},
                instruction_text="",
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        stats = await current_episode_stats(db_session, now)  # type: ignore[arg-type]
        assert stats is not None
        assert stats.max_dd_pct == Decimal("12")
        assert stats.started_at == started
        assert stats.duration == timedelta(hours=3)

    async def test_stops_at_the_last_level_zero_boundary(self, db_session: object) -> None:
        now = datetime.now(UTC)
        db_session.add(  # type: ignore[attr-defined]
            KillSwitchEvent(
                ts=now - timedelta(days=10),
                level=3,
                portfolio_dd_pct=Decimal("15"),  # episodio VIEJO, ya cerrado
                actions={},
                instruction_text="",
            )
        )
        db_session.add(  # type: ignore[attr-defined]
            KillSwitchEvent(
                ts=now - timedelta(days=5),
                level=0,  # desescalado -- cierra el episodio viejo
                portfolio_dd_pct=Decimal("1"),
                actions={},
                instruction_text="",
                confirmed_by="operator@test",
            )
        )
        started = now - timedelta(hours=1)
        db_session.add(  # type: ignore[attr-defined]
            KillSwitchEvent(
                ts=started,
                level=1,
                portfolio_dd_pct=Decimal("9"),
                actions={},
                instruction_text="",
            )
        )
        await db_session.flush()  # type: ignore[attr-defined]

        stats = await current_episode_stats(db_session, now)  # type: ignore[arg-type]
        assert stats is not None
        assert stats.max_dd_pct == Decimal("9")  # NO el 15 del episodio viejo
        assert stats.started_at == started
