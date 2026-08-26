from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.models.market import HeartbeatLog
from tests.factories import AccountFactory, BaselineFactory, BotFactory


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class TestExecutionWatchdog:
    async def test_dead_bot_is_reported(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
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

        response = await api_client.get("/api/v1/execution/watchdog")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["bot_id"] == bot.id)
        assert row["state"] == "DEAD"


class TestExecutionHeartbeat:
    async def test_reports_last_heartbeat_and_connected(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        session.add(
            HeartbeatLog(
                ts=datetime.now(UTC),
                connector_instance_id="c1",
                account_id=account.id,
                latency_ms=42,
                status="ok",
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/execution/heartbeat")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["account_id"] == account.id)
        assert row["latency_ms"] == 42
        assert row["connected"] is True

    async def test_account_without_heartbeat_is_disconnected(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.commit()

        response = await api_client.get("/api/v1/execution/heartbeat")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["account_id"] == account.id)
        assert row["connected"] is False
        assert row["last_ts"] is None
