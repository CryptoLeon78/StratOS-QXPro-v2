from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import SemaphoreState
from tests.factories import (
    AccountFactory,
    BotFactory,
    EaStateFactory,
    EquitySnapshotFactory,
    IngestBatchFactory,
)


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class TestListAccounts:
    async def test_lists_accounts(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        session.add(AccountFactory())
        await session.commit()

        response = await api_client.get("/api/v1/accounts")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["equity"] is None  # sin snapshot -- no inventado

    async def test_includes_the_latest_equity_snapshot(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        now = datetime.now(UTC)
        session.add(
            EquitySnapshotFactory(
                account_id=account.id,
                ts=now - timedelta(hours=1),
                equity=Decimal("9000"),
                balance=Decimal("9000"),
            )
        )
        session.add(
            EquitySnapshotFactory(
                account_id=account.id, ts=now, equity=Decimal("9500"), balance=Decimal("9400")
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/accounts")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["id"] == account.id)
        assert Decimal(row["equity"]) == Decimal("9500")  # el mas reciente, no el mas viejo
        assert Decimal(row["balance"]) == Decimal("9400")


class TestListEas:
    async def test_lists_ea_states_for_the_account(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        batch = IngestBatchFactory(account_id=account.id)
        session.add(batch)
        await session.flush()
        session.add(
            EaStateFactory(account_id=account.id, magic_number=118231, ingest_batch_id=batch.id)
        )
        await session.commit()

        response = await api_client.get(f"/api/v1/accounts/{account.id}/eas")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["magic_number"] == 118231

    async def test_unknown_account_returns_404(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/accounts/999999/eas")
        assert response.status_code == 404

    async def test_version_is_unverifiable_without_a_requirement(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        batch = IngestBatchFactory(account_id=account.id)
        session.add(batch)
        await session.flush()
        session.add(
            EaStateFactory(
                account_id=account.id, magic_number=118232, ingest_batch_id=batch.id
            )
        )
        await session.commit()

        response = await api_client.get(f"/api/v1/accounts/{account.id}/eas")
        row = response.json()[0]
        assert row["ea_required_version"] is None
        assert row["version_verifiable"] is False
        assert row["version_matches"] is None

    async def test_version_compares_with_the_registered_bot_requirement(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id, magic_number=118233, ea_required_version="1.1.0")
        session.add(bot)
        batch = IngestBatchFactory(account_id=account.id)
        session.add(batch)
        await session.flush()
        session.add(
            EaStateFactory(
                account_id=account.id,
                magic_number=bot.magic_number,
                ea_version="1.1.0",
                ingest_batch_id=batch.id,
            )
        )
        await session.commit()

        response = await api_client.get(f"/api/v1/accounts/{account.id}/eas")
        row = response.json()[0]
        assert row["version_verifiable"] is True
        assert row["version_matches"] is True


class TestAccountDrift:
    async def test_flags_orange_bot_in_real_mode(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        bot = BotFactory(account_id=account.id, semaphore_state=SemaphoreState.NARANJA)
        session.add(bot)
        await session.flush()
        batch = IngestBatchFactory(account_id=account.id)
        session.add(batch)
        await session.flush()
        session.add(
            EaStateFactory(
                account_id=account.id,
                magic_number=bot.magic_number,
                mode="REAL",
                ingest_batch_id=batch.id,
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/accounts/drift")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["bot_id"] == bot.id)
        assert row["drift"] is True
