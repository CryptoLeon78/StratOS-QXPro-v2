from datetime import UTC, datetime
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.models.governance import UmsPhaseLog


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class TestScalingUms:
    async def test_returns_none_without_any_phase_log(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/scaling/ums")
        assert response.status_code == 200
        assert response.json() is None

    async def test_returns_the_latest_phase(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        session.add(
            UmsPhaseLog(
                ts=datetime.now(UTC),
                phase=4,
                equity_at=Decimal("180000"),
                metrics={},
                ready_to_advance=False,
                signed_by="ivan",
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/scaling/ums")
        assert response.status_code == 200
        assert response.json()["phase"] == 4


class TestScalingMonthly:
    async def test_lists_phase_history(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        session.add(
            UmsPhaseLog(
                ts=datetime.now(UTC),
                phase=3,
                equity_at=Decimal("50000"),
                metrics={},
                ready_to_advance=False,
                signed_by=None,
            )
        )
        await session.commit()

        response = await api_client.get("/api/v1/scaling/monthly")
        assert response.status_code == 200
        assert len(response.json()) == 1
