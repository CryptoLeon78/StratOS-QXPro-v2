from datetime import UTC, datetime
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import BotOriginKind, BotProfile, PipelinePhase
from core.db.models.governance import CorrelationMatrix
from tests.factories import AccountFactory, BotFactory


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class TestPortfolioBlocks:
    async def test_aggregates_capital_by_block(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        session.add(
            BotFactory(
                account_id=account.id,
                profile=BotProfile.TREND,
                pipeline_phase=PipelinePhase.F7,
                capital_allocated_pct=Decimal("4.00"),
            )
        )
        session.add(
            BotFactory(
                account_id=account.id,
                profile=BotProfile.SMART_MONEY,
                pipeline_phase=PipelinePhase.F7,
                capital_allocated_pct=Decimal("4.00"),
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/portfolio/blocks")
        assert response.status_code == 200
        rows = {r["key"]: r for r in response.json()}
        assert rows["CONVEXO"]["real_pct"] == 50.0
        assert rows["HIBRIDO"]["real_pct"] == 50.0
        assert rows["CONCAVO"]["real_pct"] == 0.0

    async def test_excludes_external_observation_without_declared_allocation(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        session.add(
            BotFactory(
                account_id=account.id,
                origin_kind=BotOriginKind.EXTERNAL_PRODUCTION,
                profile=None,
                capital_allocated_pct=None,
                risk_per_trade_pct=None,
                pipeline_phase=PipelinePhase.F7,
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/portfolio/blocks")

        assert response.status_code == 200
        assert all(row["bot_count"] == 0 for row in response.json())


class TestPortfolioProfiles:
    async def test_lists_all_seven_profiles_with_targets(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        response = await api_client.get("/api/v1/portfolio/profiles")
        assert response.status_code == 200
        assert len(response.json()) == 7


class TestPortfolioCorrelations:
    async def test_returns_the_latest_persisted_run(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot_a = BotFactory(account_id=account.id)
        bot_b = BotFactory(account_id=account.id)
        session.add(bot_a)
        session.add(bot_b)
        await session.flush()
        session.add(
            CorrelationMatrix(
                ts=datetime.now(UTC),
                bot_a_id=bot_a.id,
                bot_b_id=bot_b.id,
                correlation=0.52,
                is_redundant_pair=True,
                window_days=1240,
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/portfolio/correlations")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["is_redundant_pair"] is True

    async def test_no_data_returns_empty_list(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/portfolio/correlations")
        assert response.status_code == 200
        assert response.json() == []


class TestPortfolioBenchmark:
    async def test_no_equity_data_returns_null(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/portfolio/benchmark")
        assert response.status_code == 200
        assert response.json() is None
