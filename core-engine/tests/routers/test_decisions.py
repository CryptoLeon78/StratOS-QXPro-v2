from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import DecisionStatus
from core.db.models.decisions import Decision
from tests.routers.conftest import TEST_OPERATOR


async def _pending_decision(db_connection: AsyncConnection) -> Decision:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    decision = Decision(
        ts=datetime.now(UTC),
        module="semaphore",
        title="Bot X cambia de VERDE a AMARILLO",
        description="d",
        instruction_text="Reducir sizing al 50%.",
        status=DecisionStatus.PENDING,
    )
    session.add(decision)
    await session.commit()
    return decision


class TestListDecisions:
    async def test_lists_all_decisions(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        await _pending_decision(db_connection)
        response = await api_client.get("/api/v1/decisions")
        assert response.status_code == 200
        assert len(response.json()) == 1

    async def test_filters_by_status(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        await _pending_decision(db_connection)
        response = await api_client.get(
            "/api/v1/decisions", params={"decision_status": "CONFIRMED"}
        )
        assert response.status_code == 200
        assert response.json() == []


class TestConfirmDecision:
    async def test_confirms_a_pending_decision(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        decision = await _pending_decision(db_connection)
        response = await api_client.post(f"/api/v1/decisions/{decision.id}/confirm")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "CONFIRMED"
        assert body["decided_by"] == TEST_OPERATOR.email

    async def test_confirming_twice_returns_409(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        decision = await _pending_decision(db_connection)
        await api_client.post(f"/api/v1/decisions/{decision.id}/confirm")
        response = await api_client.post(f"/api/v1/decisions/{decision.id}/confirm")
        assert response.status_code == 409

    async def test_unknown_decision_returns_404(self, api_client: AsyncClient) -> None:
        response = await api_client.post("/api/v1/decisions/999999/confirm")
        assert response.status_code == 404


class TestPostponeDecision:
    async def test_postpones_with_a_future_date(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        decision = await _pending_decision(db_connection)
        postpone_until = "2027-01-01T00:00:00Z"
        response = await api_client.post(
            f"/api/v1/decisions/{decision.id}/postpone",
            json={"postpone_until": postpone_until},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "POSTPONED"
        assert body["postpone_until"].startswith("2027-01-01")


class TestDismissDecision:
    async def test_dismisses_a_pending_decision(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        decision = await _pending_decision(db_connection)
        response = await api_client.post(f"/api/v1/decisions/{decision.id}/dismiss")
        assert response.status_code == 200
        assert response.json()["status"] == "DISMISSED"
