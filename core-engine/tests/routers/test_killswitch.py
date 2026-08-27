from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.models.decisions import KillSwitchEvent
from tests.factories import AccountFactory, EquitySnapshotFactory


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class TestKillswitchStatus:
    async def test_no_events_means_level_zero(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/killswitch/status")
        assert response.status_code == 200
        assert response.json()["level"] == 0
        assert response.json()["instruction_text"] is None
        assert response.json()["episode_max_dd_pct"] is None
        assert response.json()["episode_duration_seconds"] is None

    async def test_active_episode_reports_max_dd_and_duration(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        started = datetime.now(UTC) - timedelta(hours=2)
        session.add(
            KillSwitchEvent(
                ts=started,
                level=1,
                portfolio_dd_pct=Decimal("9"),
                actions={},
                instruction_text="",
            )
        )
        session.add(
            KillSwitchEvent(
                ts=started + timedelta(hours=1),
                level=2,
                portfolio_dd_pct=Decimal("13"),
                actions={},
                instruction_text="",
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/killswitch/status")
        assert response.status_code == 200
        body = response.json()
        assert body["level"] == 2
        assert Decimal(body["episode_max_dd_pct"]) == Decimal("13")
        assert body["episode_duration_seconds"] >= timedelta(hours=2).total_seconds()


class TestConfirmDeescalation:
    async def test_deescalates_when_dd_recovers_below_hysteresis(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        session.add(
            KillSwitchEvent(
                ts=datetime.now(UTC) - timedelta(hours=1),
                level=2,
                portfolio_dd_pct=Decimal("13.0"),
                actions={},
                instruction_text="Reducir sizing 50% en todos los bots.",
            )
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
        session.add(EquitySnapshotFactory(account_id=account.id, ts=now, equity=Decimal("95000")))
        await session.commit()

        response = await api_client.post("/api/v1/killswitch/confirm")
        assert response.status_code == 200
        assert response.json()["level"] == 0

        event = (
            await session.execute(
                select(KillSwitchEvent).order_by(KillSwitchEvent.ts.desc()).limit(1)
            )
        ).scalar_one()
        assert event.level == 0

    async def test_noop_at_level_zero(self, api_client: AsyncClient) -> None:
        response = await api_client.post("/api/v1/killswitch/confirm")
        assert response.status_code == 200
        assert response.json()["level"] == 0
