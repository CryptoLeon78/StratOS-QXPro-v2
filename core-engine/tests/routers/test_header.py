from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.main import app
from tests.factories import AccountFactory, EquitySnapshotFactory


async def test_header_summary_requires_auth() -> None:
    # sin dependency_overrides: get_current_user real, sin token -> 401.
    # El flujo completo de auth ya esta probado en tests/auth/.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/header/summary")
    assert response.status_code == 401


async def test_header_summary_reflects_real_equity_and_open_positions(
    api_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    account = AccountFactory(is_demo=False)
    session.add(account)
    await session.flush()
    now = datetime.now(UTC)
    session.add(
        EquitySnapshotFactory(
            account_id=account.id, ts=now - timedelta(days=10), equity=Decimal("100000")
        )
    )
    session.add(EquitySnapshotFactory(account_id=account.id, ts=now, equity=Decimal("105000")))
    await session.commit()

    response = await api_client.get("/api/v1/header/summary")
    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["equity_eur"]) == Decimal("105000")
    assert body["open_positions"] == 0
    assert body["mt_connected"] is False


async def test_equity_curve_returns_points_for_range(
    api_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    account = AccountFactory(is_demo=False)
    session.add(account)
    await session.flush()
    now = datetime.now(UTC)
    session.add(
        EquitySnapshotFactory(
            account_id=account.id, ts=now - timedelta(days=5), equity=Decimal("50000")
        )
    )
    await session.commit()

    response = await api_client.get("/api/v1/summary/equity-curve", params={"range": "30d"})
    assert response.status_code == 200
    assert len(response.json()) >= 1
