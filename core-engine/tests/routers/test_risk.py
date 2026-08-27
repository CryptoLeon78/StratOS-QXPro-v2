from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import TradeType
from core.db.models.governance import MonteCarloRun
from tests.factories import (
    AccountFactory,
    BotFactory,
    EquitySnapshotFactory,
    IngestBatchFactory,
    TradeFactory,
)


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class TestRiskTail:
    async def test_returns_none_without_equity_history(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/risk/tail")
        assert response.status_code == 200
        assert response.json() is None

    async def test_returns_computed_tail_risk(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory(is_demo=False)
        session.add(account)
        await session.flush()
        now = datetime.now(UTC)
        daily_pct = [Decimal("1.001"), Decimal("0.9993"), Decimal("1.0012")]
        equity = Decimal("10000")
        for i in range(15):
            session.add(
                EquitySnapshotFactory(
                    account_id=account.id, ts=now - timedelta(days=15 - i), equity=equity
                )
            )
            equity = equity * daily_pct[i % len(daily_pct)]
        await session.commit()

        response = await api_client.get("/api/v1/risk/tail")
        assert response.status_code == 200
        assert response.json() is not None
        assert "verdict" in response.json()


class TestRiskExposure:
    async def test_aggregates_open_positions(
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
                profit=Decimal("10.00"),
                close_time=None,
                ingest_batch_id=batch.id,
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/risk/exposure")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["symbol"] == "EURUSD")
        assert Decimal(row["net_volume"]) == Decimal("1.00")
        assert row["currency"] == "EUR"  # symbol_currency, migracion 288e484ba382

    async def test_exposure_by_currency_groups_subtotals(
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
                symbol="XAUUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("15.00"),
                close_time=None,
                ingest_batch_id=batch.id,
            )
        )
        session.add(
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="XAGUSD",
                type=TradeType.BUY,
                volume=Decimal("2.00"),
                profit=Decimal("5.00"),
                close_time=None,
                ingest_batch_id=batch.id,
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/risk/exposure/by-currency")
        assert response.status_code == 200
        usd = next(r for r in response.json() if r["currency"] == "USD")
        assert Decimal(usd["gross_volume"]) >= Decimal("3.00")
        assert Decimal(usd["pnl"]) >= Decimal("20.00")


class TestRiskMontecarlo:
    async def test_returns_the_latest_run_for_the_bot(
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
            MonteCarloRun(
                bot_id=bot.id,
                ts=datetime.now(UTC),
                n_simulations=300,
                dd_p50=Decimal("2.3"),
                dd_p75=Decimal("3.0"),
                dd_p95=Decimal("3.9"),
                dd_contract_pct=Decimal("3.9"),
                seed=42,
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/risk/montecarlo", params={"bot_id": bot.id})
        assert response.status_code == 200
        assert response.json()["seed"] == 42

    async def test_returns_none_without_a_run(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/risk/montecarlo", params={"bot_id": 999999})
        assert response.status_code == 200
        assert response.json() is None
