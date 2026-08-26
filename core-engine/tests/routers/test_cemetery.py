from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import CemeteryCause
from core.db.models.pipeline import CemeteryEntry
from tests.factories import AccountFactory, BotFactory


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class TestListCemetery:
    async def test_lists_entries(
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
            CemeteryEntry(
                bot_id=bot.id,
                retired_at=datetime.now(UTC),
                cause=CemeteryCause.ALPHA_DECAY,
                autopsy_text="a",
                lesson="b",
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/cemetery")
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestReactivate:
    async def test_always_returns_409(self, api_client: AsyncClient) -> None:
        response = await api_client.post("/api/v1/cemetery/1/reactivate")
        assert response.status_code == 409
        assert "Fase 3" in response.json()["detail"]
