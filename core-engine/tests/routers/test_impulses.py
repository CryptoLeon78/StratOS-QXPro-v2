from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import ImpulseAction, ImpulseStatus
from core.db.models.decisions import ImpulseLog
from tests.factories import AccountFactory, BotFactory


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class TestPostImpulse:
    async def test_creates_a_pending_impulse(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id)
        session.add(bot)
        await session.commit()

        response = await api_client.post(
            "/api/v1/impulses",
            json={"bot_id": bot.id, "description": "d", "desired_action": "PAUSE_BOT"},
        )
        assert response.status_code == 201
        assert response.json()["status"] == "PENDING"

    async def test_unknown_bot_returns_404(self, api_client: AsyncClient) -> None:
        response = await api_client.post(
            "/api/v1/impulses",
            json={"bot_id": 999999, "description": "d", "desired_action": "PAUSE_BOT"},
        )
        assert response.status_code == 404


class TestListImpulses:
    async def test_lists_impulses(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id)
        session.add(bot)
        await session.flush()
        session.add(
            ImpulseLog(
                ts=datetime.now(UTC),
                bot_id=bot.id,
                description="d",
                desired_action=ImpulseAction.PAUSE_BOT,
                executed=False,
                status=ImpulseStatus.PENDING,
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/impulses")
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestImpulseReport:
    async def test_returns_zero_for_an_empty_quarter(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/impulses/report", params={"quarter": "2020-Q1"})
        assert response.status_code == 200
        assert response.json()["count"] == 0
