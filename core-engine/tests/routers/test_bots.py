from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import TradeType
from tests.factories import (
    AccountFactory,
    BotFactory,
    IngestBatchFactory,
    SemaphoreTransitionFactory,
    TradeFactory,
)


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class TestListBots:
    async def test_lists_bots(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        session.add(BotFactory(account_id=account.id))
        await session.commit()

        response = await api_client.get("/api/v1/bots")
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestGetBot:
    async def test_returns_the_bot(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id)
        session.add(bot)
        await session.commit()

        response = await api_client.get(f"/api/v1/bots/{bot.id}")
        assert response.status_code == 200
        assert response.json()["magic_number"] == bot.magic_number

    async def test_unknown_bot_returns_404(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/bots/999999")
        assert response.status_code == 404


class TestOpenPositions:
    async def test_returns_only_open_trades_for_the_bot(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id)
        session.add(bot)
        await session.flush()
        batch = IngestBatchFactory(account_id=account.id)
        session.add(batch)
        await session.flush()
        session.add(
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("5.00"),
                close_time=None,
                ingest_batch_id=batch.id,
            )
        )
        await session.commit()

        response = await api_client.get(f"/api/v1/bots/{bot.id}/open-positions")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["symbol"] == "EURUSD"

    async def test_unknown_bot_returns_404(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/bots/999999/open-positions")
        assert response.status_code == 404


class TestSemaphoreHistory:
    async def test_returns_transitions_for_the_bot(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id)
        session.add(bot)
        await session.flush()
        session.add(SemaphoreTransitionFactory(bot_id=bot.id))
        await session.commit()

        response = await api_client.get(f"/api/v1/bots/{bot.id}/semaphore-history")
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_unknown_bot_returns_404(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/bots/999999/semaphore-history")
        assert response.status_code == 404
