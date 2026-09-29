"""ADR 0013: KS, UMS y retiros por cuenta. Cada cuenta lleva su propia
escalera, calculada sobre su propia curva de equity; ningun evento de una
cuenta afecta a otra y los eventos heredados (account_id NULL) tampoco."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import fakeredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.decisions import Alert, KillSwitchEvent
from core.db.models.governance import UmsPhaseLog
from core.services.killswitch_sweep import (
    KillSwitchSweepConfig,
    compute_portfolio_dd_pct,
    current_episode_stats,
    current_killswitch_level,
    sweep_accounts,
)
from core.services.risk import real_portfolio_equity_curve
from core.services.ums import UmsConfig, check_automatic_downgrade, current_phase
from core.state_machines.types import KillSwitchConfig
from tests.factories import AccountFactory, EquitySnapshotFactory, KillSwitchEventFactory

SWEEP_CONFIG = KillSwitchSweepConfig(equity_lookback_days=3650)


async def _account(session: AsyncSession, *, is_demo: bool = False) -> int:
    account = AccountFactory(is_demo=is_demo)
    session.add(account)
    await session.flush()
    return int(account.id)


async def _equity(
    session: AsyncSession, account_id: int, start: Decimal, end: Decimal, now: datetime
) -> None:
    for days_ago, value in ((10, start), (0, end)):
        session.add(
            EquitySnapshotFactory(
                account_id=account_id,
                ts=now - timedelta(days=days_ago),
                equity=value,
                balance=value,
            )
        )
    await session.flush()


class TestEquityCurveScope:
    async def test_scoped_curve_is_only_that_accounts_equity(
        self, db_session: AsyncSession
    ) -> None:
        now = datetime.now(UTC)
        a = await _account(db_session)
        b = await _account(db_session)
        await _equity(db_session, a, Decimal("100000"), Decimal("90000"), now)
        await _equity(db_session, b, Decimal("50000"), Decimal("55000"), now)

        curve_a = await real_portfolio_equity_curve(db_session, now - timedelta(days=30), a)
        portfolio = await real_portfolio_equity_curve(db_session, now - timedelta(days=30))

        assert float(curve_a.iloc[-1]) == 90000.0
        assert float(portfolio.iloc[-1]) == 145000.0

    async def test_scoped_curve_includes_a_demo_account(self, db_session: AsyncSession) -> None:
        now = datetime.now(UTC)
        demo = await _account(db_session, is_demo=True)
        await _equity(db_session, demo, Decimal("10000"), Decimal("10500"), now)

        scoped = await real_portfolio_equity_curve(db_session, now - timedelta(days=30), demo)
        portfolio = await real_portfolio_equity_curve(db_session, now - timedelta(days=30))

        assert float(scoped.iloc[-1]) == 10500.0
        assert portfolio.empty


class TestKillSwitchPerAccount:
    async def test_dd_uses_only_the_requested_account(self, db_session: AsyncSession) -> None:
        now = datetime.now(UTC)
        a = await _account(db_session)
        b = await _account(db_session)
        await _equity(db_session, a, Decimal("100000"), Decimal("75000"), now)
        await _equity(db_session, b, Decimal("100000"), Decimal("99000"), now)

        dd_a = await compute_portfolio_dd_pct(db_session, SWEEP_CONFIG, now, a)
        dd_b = await compute_portfolio_dd_pct(db_session, SWEEP_CONFIG, now, b)

        assert dd_a == Decimal("25")
        assert dd_b == Decimal("1")

    async def test_sweep_escalates_only_the_account_in_drawdown(
        self, db_session: AsyncSession
    ) -> None:
        now = datetime.now(UTC)
        hit = await _account(db_session)
        calm = await _account(db_session, is_demo=True)
        await _equity(db_session, hit, Decimal("100000"), Decimal("75000"), now)
        await _equity(db_session, calm, Decimal("100000"), Decimal("99000"), now)

        redis = fakeredis.FakeAsyncRedis()
        await sweep_accounts(db_session, redis, KillSwitchConfig(), SWEEP_CONFIG, now)
        await db_session.commit()

        events = (await db_session.execute(select(KillSwitchEvent))).scalars().all()
        assert [(e.account_id, e.level) for e in events] == [(hit, 4)]
        assert await current_killswitch_level(db_session, hit) == 4
        assert await current_killswitch_level(db_session, calm) == 0
        alerts = (await db_session.execute(select(Alert))).scalars().all()
        assert {a.account_id for a in alerts} == {hit}
        await redis.aclose()

    async def test_legacy_portfolio_events_do_not_leak_into_an_account(
        self, db_session: AsyncSession
    ) -> None:
        now = datetime.now(UTC)
        a = await _account(db_session)
        db_session.add(KillSwitchEventFactory(level=3, ts=now, account_id=None))
        await db_session.flush()

        assert await current_killswitch_level(db_session, a) == 0
        assert await current_killswitch_level(db_session) == 3
        assert await current_episode_stats(db_session, now, a) is None

    async def test_sweep_skips_inactive_accounts(self, db_session: AsyncSession) -> None:
        now = datetime.now(UTC)
        account = AccountFactory(is_active=False)
        db_session.add(account)
        await db_session.flush()
        await _equity(db_session, account.id, Decimal("100000"), Decimal("70000"), now)

        redis = fakeredis.FakeAsyncRedis()
        await sweep_accounts(db_session, redis, KillSwitchConfig(), SWEEP_CONFIG, now)

        assert (await db_session.execute(select(KillSwitchEvent))).scalars().all() == []
        await redis.aclose()


class TestUmsPerAccount:
    async def test_each_account_has_its_own_phase(self, db_session: AsyncSession) -> None:
        now = datetime.now(UTC)
        a = await _account(db_session)
        b = await _account(db_session)
        db_session.add(
            UmsPhaseLog(
                ts=now,
                phase=3,
                equity_at=Decimal("50000"),
                metrics={},
                ready_to_advance=True,
                signed_by="op",
                account_id=a,
            )
        )
        await db_session.flush()

        phase_a = await current_phase(db_session, a)
        assert phase_a is not None and phase_a.phase == 3
        assert await current_phase(db_session, b) is None

    async def test_automatic_downgrade_is_scoped_and_alerts_are_tagged(
        self, db_session: AsyncSession
    ) -> None:
        now = datetime.now(UTC)
        a = await _account(db_session)
        b = await _account(db_session)
        top_phase = len(UmsConfig().phases)
        for account_id in (a, b):
            db_session.add(
                UmsPhaseLog(
                    ts=now - timedelta(days=60),
                    phase=top_phase,
                    equity_at=Decimal("999999"),
                    metrics={},
                    ready_to_advance=True,
                    signed_by="op",
                    account_id=account_id,
                )
            )
        await db_session.flush()

        redis = fakeredis.FakeAsyncRedis()
        await check_automatic_downgrade(db_session, redis, UmsConfig(), Decimal("100"), now, a)
        await db_session.flush()

        phase_a = await current_phase(db_session, a)
        phase_b = await current_phase(db_session, b)
        assert phase_a is not None and phase_a.phase < top_phase
        assert phase_b is not None and phase_b.phase == top_phase
        alerts = (
            (await db_session.execute(select(Alert).where(Alert.module == "ums"))).scalars().all()
        )
        assert [al.account_id for al in alerts] == [a]
        await redis.aclose()
