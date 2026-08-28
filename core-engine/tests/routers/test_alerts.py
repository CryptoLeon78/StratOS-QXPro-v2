"""G10 (docs/backlog.md): GET /alerts -- lo unico que faltaba para la
vista dominical (grupo n): "errores de EA" viene de Alert(module=
"config_drift"), sin endpoint de listado hasta ahora (header.py solo
contaba el total, nunca listaba filas)."""

from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import AlertLevel
from core.db.models.decisions import Alert


async def _alert(
    db_connection: AsyncConnection, module: str = "config_drift", resolved: bool = False
) -> Alert:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    alert = Alert(
        ts=datetime.now(UTC),
        level=AlertLevel.CRITICA,
        module=module,
        message="EA en modo incorrecto",
        action_required="Corregir el modo del EA en MetaTrader",
        resolved=resolved,
    )
    session.add(alert)
    await session.commit()
    return alert


class TestListAlerts:
    async def test_lists_all_alerts(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        await _alert(db_connection)
        response = await api_client.get("/api/v1/alerts")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["module"] == "config_drift"
        assert body[0]["level"] == "CRITICA"

    async def test_filters_by_module(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        await _alert(db_connection, module="config_drift")
        await _alert(db_connection, module="watchdog")
        response = await api_client.get("/api/v1/alerts", params={"module": "watchdog"})
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["module"] == "watchdog"

    async def test_excludes_resolved_by_default(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        await _alert(db_connection, resolved=True)
        response = await api_client.get("/api/v1/alerts")
        assert response.status_code == 200
        assert response.json() == []

    async def test_includes_resolved_when_requested(
        self, api_client: AsyncClient, db_connection: AsyncConnection
    ) -> None:
        await _alert(db_connection, resolved=True)
        response = await api_client.get("/api/v1/alerts", params={"include_resolved": "true"})
        assert response.status_code == 200
        assert len(response.json()) == 1
