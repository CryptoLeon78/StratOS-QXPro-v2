from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from tests.factories import AccountFactory, EquitySnapshotFactory


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class TestAuditStatus:
    async def test_reports_mismatched_account(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        now = datetime.now(UTC)
        session.add(
            EquitySnapshotFactory(
                account_id=account.id, ts=now - timedelta(days=10), balance=Decimal("30000.00")
            )
        )
        session.add(
            EquitySnapshotFactory(account_id=account.id, ts=now, balance=Decimal("99999.00"))
        )
        await session.commit()

        response = await api_client.get("/api/v1/audit/status")
        assert response.status_code == 200
        row = next(r for r in response.json() if r["account_id"] == account.id)
        assert row["breached"] is True


class TestAuditRun:
    async def test_creates_alert_for_breached_account(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        account = AccountFactory()
        session.add(account)
        await session.flush()
        now = datetime.now(UTC)
        session.add(
            EquitySnapshotFactory(
                account_id=account.id, ts=now - timedelta(days=10), balance=Decimal("30000.00")
            )
        )
        session.add(
            EquitySnapshotFactory(account_id=account.id, ts=now, balance=Decimal("99999.00"))
        )
        await session.commit()

        response = await api_client.post("/api/v1/audit/run")
        assert response.status_code == 200

        from sqlalchemy import select

        from core.db.models.decisions import Alert

        alert = (
            await session.execute(select(Alert).where(Alert.dedup_key == f"audit:{account.id}"))
        ).scalar_one()
        assert alert is not None


class TestAuditSeals:
    async def test_returns_a_summary(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/audit/seals")
        assert response.status_code == 200
        assert "total_batches" in response.json()
