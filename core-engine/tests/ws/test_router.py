"""End-to-end contra Redis real (no fakeredis: TestClient corre el ASGI
app en un hilo/loop propio, distinto del loop de pytest -- el cache de
core/redis.py::get_redis_client, indexado por loop, resuelve esto solo).
Publica con el cliente SINCRONO de `redis-py` (mismo paquete que
`redis.asyncio`, distribucion unica) -- el test en si es sincrono
(TestClient.websocket_connect es un context manager bloqueante), publicar
desde el hilo del test evita mezclar loops de asyncio."""

from datetime import UTC, datetime

import pytest
import redis as sync_redis
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from core.auth.jwt import create_access_token
from core.config import Settings, get_settings
from core.main import app

_TEST_SETTINGS = Settings(
    database_url="postgresql+asyncpg://u:p@localhost/db",
    app_database_url="postgresql+asyncpg://u:p@localhost/db",
    app_db_password="x",
    redis_url="redis://localhost/0",
    jwt_secret="test-secret-at-least-32-bytes-long-for-hs256",
    ingest_api_keys="x",
)  # type: ignore[call-arg]


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_settings] = lambda: _TEST_SETTINGS
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _valid_token() -> str:
    return create_access_token(
        user_id=1,
        email="ivan@stratos.local",
        role="operator",
        settings=_TEST_SETTINGS,
        now=datetime.now(UTC),
    )


class TestWsAuth:
    def test_missing_token_closes_with_policy_violation(self, client: TestClient) -> None:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/equity"):
                pass
        assert exc_info.value.code == 1008

    def test_valid_token_is_accepted(self, client: TestClient) -> None:
        with client.websocket_connect(f"/ws/health?token={_valid_token()}"):
            pass  # accept() sin excepcion ya prueba la autenticacion


class TestWsRouting:
    def test_publish_on_semaphore_arrives_via_pipeline_not_equity(self, client: TestClient) -> None:
        # get_redis_client() lee get_settings() en directo, no pasa por
        # dependency_overrides -- se publica con el mismo REDIS_URL real
        # que resolvera el server dentro del ASGI app.
        from core.config import get_settings as real_get_settings

        publisher = sync_redis.Redis.from_url(real_get_settings().redis_url)
        token = _valid_token()
        try:
            with client.websocket_connect(f"/ws/pipeline?token={token}") as pipeline_ws:
                with client.websocket_connect(f"/ws/equity?token={token}") as equity_ws:
                    publisher.publish("events:semaphore", "hola-pipeline")
                    received = pipeline_ws.receive_text()
                    assert received == "hola-pipeline"
                    equity_ws.close()
        finally:
            publisher.close()


class TestWsConnectionsGauge:
    def test_gauge_increments_while_connected_and_decrements_after(
        self, client: TestClient
    ) -> None:
        from core.metrics import WS_CONNECTIONS_ACTIVE

        before = WS_CONNECTIONS_ACTIVE.labels(channel="/ws/health")._value.get()
        with client.websocket_connect(f"/ws/health?token={_valid_token()}"):
            during = WS_CONNECTIONS_ACTIVE.labels(channel="/ws/health")._value.get()
            assert during == before + 1
        after = WS_CONNECTIONS_ACTIVE.labels(channel="/ws/health")._value.get()
        assert after == before
