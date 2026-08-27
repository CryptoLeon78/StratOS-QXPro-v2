from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import TradeType
from tests.factories import (
    AccountFactory,
    BaselineFactory,
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


class TestPnlCurve:
    async def test_returns_synthetic_start_plus_one_point_per_closed_trade(
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
                profit=Decimal("20.00"),
                close_time=datetime(2026, 8, 1, tzinfo=UTC),
                close_price=Decimal("1.1"),
                ingest_batch_id=batch.id,
            )
        )
        await session.commit()

        response = await api_client.get(f"/api/v1/bots/{bot.id}/pnl-curve")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert body[0]["ts"] is None
        assert Decimal(body[1]["cumulative_pnl"]) == Decimal("120.00")

    async def test_unknown_bot_returns_404(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/bots/999999/pnl-curve")
        assert response.status_code == 404


class TestRMultiples:
    async def test_returns_populated_r_multiples_only(
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
                profit=Decimal("20.00"),
                close_time=datetime(2026, 8, 1, tzinfo=UTC),
                close_price=Decimal("1.1"),
                r_multiple=Decimal("1.5"),
                ingest_batch_id=batch.id,
            )
        )
        await session.commit()

        response = await api_client.get(f"/api/v1/bots/{bot.id}/r-multiples")
        assert response.status_code == 200
        assert [Decimal(v) for v in response.json()] == [Decimal("1.5")]


class TestBotMetrics:
    async def test_bot_without_baseline_omits_rolling_vs_baseline_fields(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id)
        session.add(bot)
        await session.commit()

        response = await api_client.get(f"/api/v1/bots/{bot.id}/metrics")
        assert response.status_code == 200
        body = response.json()
        assert body["has_baseline"] is False
        assert body["sharpe_rolling"] is None
        assert body["pf_baseline"] is None
        assert body["net_pnl"] == "0"

    async def test_bot_with_baseline_and_trades_populates_everything(
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
        batch = IngestBatchFactory(account_id=account.id)
        session.add(batch)
        await session.flush()
        for i, profit in enumerate([Decimal("20.00"), Decimal("-5.00"), Decimal("15.00")]):
            session.add(
                TradeFactory(
                    bot_id=bot.id,
                    account_id=account.id,
                    magic_number=bot.magic_number,
                    symbol="EURUSD",
                    type=TradeType.BUY,
                    volume=Decimal("1.00"),
                    profit=profit,
                    close_time=datetime(2020, 1, i + 1, tzinfo=UTC),
                    close_price=Decimal("1.1"),
                    ingest_batch_id=batch.id,
                )
            )
        await session.commit()

        response = await api_client.get(f"/api/v1/bots/{bot.id}/metrics")
        assert response.status_code == 200
        body = response.json()
        assert body["has_baseline"] is True
        assert body["pf_baseline"] == baseline.profit_factor
        assert Decimal(body["net_pnl"]) == Decimal("30.00")
        assert Decimal(body["pnl_bot"]) == Decimal("30.00")
        assert Decimal(body["pnl_account"]) == Decimal("30.00")
        assert body["pct_of_total_pnl"] == 100.0
        # las 3 fechas de cierre (2020-01) caen muy fuera de la ventana de
        # 30 dias respecto a "ahora" -- trades_per_month debe ignorarlas,
        # no contarlas como si fueran recientes.
        assert body["trades_per_month"] == 0.0

    async def test_trades_per_month_only_counts_the_last_30_days(
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
        now = datetime.now(UTC)
        # 2 trades recientes (dentro de 30 dias) + 1 trade viejo (fuera)
        session.add(
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("10.00"),
                close_time=now - timedelta(days=1),
                close_price=Decimal("1.1"),
                ingest_batch_id=batch.id,
            )
        )
        session.add(
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("10.00"),
                close_time=now - timedelta(days=2),
                close_price=Decimal("1.1"),
                ingest_batch_id=batch.id,
            )
        )
        session.add(
            TradeFactory(
                bot_id=bot.id,
                account_id=account.id,
                magic_number=bot.magic_number,
                symbol="EURUSD",
                type=TradeType.BUY,
                volume=Decimal("1.00"),
                profit=Decimal("999.00"),
                close_time=now - timedelta(days=200),
                close_price=Decimal("1.1"),
                ingest_batch_id=batch.id,
            )
        )
        await session.commit()

        response = await api_client.get(f"/api/v1/bots/{bot.id}/metrics")
        assert response.status_code == 200
        body = response.json()
        # 2 trades en 30 dias -> 2 trades/semana * 4.345 semanas/mes
        assert body["trades_per_month"] == pytest.approx(2 / (30 / 7) * 4.345)

    async def test_unknown_bot_returns_404(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/bots/999999/metrics")
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
