from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import AccountDataOrigin
from core.main import app
from tests.factories import AccountFactory, BotFactory, EquitySnapshotFactory


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


class TestDataProvenance:
    """De qué universos se compone lo que muestran las vistas agregadas.

    En Portfolio, Salud, Riesgo, Auditoría y Dominical la procedencia no es un campo de una
    fila: es una propiedad del agregado. El recorrido G12 encontró que esas superficies
    sumaban fixture y telemetría real sin que nada lo dijera. Este endpoint declara la
    composición real de los datos, para que la UI pueda decirlo en vez de callarlo.
    """

    async def test_reports_a_single_origin_when_everything_comes_from_one(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        session = AsyncSession(
            bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        account = AccountFactory(data_origin=AccountDataOrigin.BROKER_REAL)
        session.add(account)
        await session.flush()
        session.add(BotFactory(account_id=account.id))
        await session.commit()

        response = await api_client.get("/api/v1/data-provenance")

        assert response.status_code == 200
        body = response.json()
        assert body["is_mixed"] is False
        assert [row["data_origin"] for row in body["accounts"]] == ["BROKER_REAL"]
        assert body["accounts"][0]["accounts"] == 1
        assert body["accounts"][0]["bots"] == 1

    async def test_flags_a_mixed_surface(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        """Fixture y telemetría real en la misma cifra: el hallazgo abierto de G12."""
        session = AsyncSession(
            bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        real = AccountFactory(data_origin=AccountDataOrigin.BROKER_REAL)
        fixture = AccountFactory(data_origin=AccountDataOrigin.FIXTURE)
        session.add_all([real, fixture])
        await session.commit()

        response = await api_client.get("/api/v1/data-provenance")

        body = response.json()
        assert body["is_mixed"] is True
        assert set(row["data_origin"] for row in body["accounts"]) == {"BROKER_REAL", "FIXTURE"}

    async def test_an_empty_base_is_absence_not_a_guess(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        response = await api_client.get("/api/v1/data-provenance")

        body = response.json()
        assert body["accounts"] == []
        assert body["is_mixed"] is False
