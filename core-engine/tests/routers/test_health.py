from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from tests.factories import AccountFactory, BaselineFactory, BotFactory


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class TestHealthBots:
    async def test_lists_bots_with_a_baseline(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id)
        session.add(bot)
        await session.flush()
        baseline = BaselineFactory(bot_id=bot.id)
        session.add(baseline)
        await session.flush()
        bot.baseline_id = baseline.id
        await session.commit()

        response = await api_client.get("/api/v1/health/bots")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["bot_id"] == bot.id)
        assert row["magic_number"] == bot.magic_number
        assert row["pf_baseline"] == baseline.profit_factor
        # G10 (docs/backlog.md): sin trades cerrados, chips rodantes neutras
        assert row["win_rate_drift"] == 0.0
        assert row["payoff"] is None
        assert row["avg_trade_duration_min"] is None
        assert row["sharpe_rolling"] == 0.0

    async def test_excludes_bots_without_a_baseline(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id)
        session.add(bot)
        await session.commit()

        response = await api_client.get("/api/v1/health/bots")
        assert response.status_code == 200
        assert all(r["bot_id"] != bot.id for r in response.json())
