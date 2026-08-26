from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import ChecklistType
from tests.factories import ChecklistRunFactory


async def _session(db_connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


class TestWithdrawalsCalculator:
    async def test_returns_zero_without_equity_history(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/withdrawals/calculator")
        assert response.status_code == 200
        assert float(response.json()["suggested_amount_eur"]) == 0.0


class TestRegisterWithdrawal:
    async def test_requires_an_existing_checklist(self, api_client: AsyncClient) -> None:
        response = await api_client.post(
            "/api/v1/withdrawals",
            json={"amount": "2500.00", "checklist_type": "MONTHLY", "period_key": "2099-99"},
        )
        assert response.status_code == 404

    async def test_registers_with_a_completed_checklist(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = await _session(db_connection)
        session.add(
            ChecklistRunFactory(
                checklist_type=ChecklistType.MONTHLY, period_key="2026-08", completed=True
            )
        )
        await session.commit()

        response = await api_client.post(
            "/api/v1/withdrawals",
            json={"amount": "2500.00", "checklist_type": "MONTHLY", "period_key": "2026-08"},
        )
        assert response.status_code == 200
        assert response.json()["amount"] == "2500.00"
