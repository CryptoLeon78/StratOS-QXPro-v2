"""PARTE 12: backoff exponencial + POST sellado. TDD real (rojo confirmado
contra el stub `NotImplementedError`)."""

import httpx
import pytest

from connector.http_client import BackoffConfig, next_delay, send_batch

CONFIG = BackoffConfig(base_seconds=5.0, multiplier=2.0, max_seconds=300.0)


class TestNextDelay:
    def test_sequence_matches_connector_settings_defaults(self) -> None:
        delays = [next_delay(n, CONFIG) for n in range(8)]
        assert delays == [5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 300.0, 300.0]

    def test_never_exceeds_the_cap(self) -> None:
        assert next_delay(100, CONFIG) == CONFIG.max_seconds

    def test_monotonically_non_decreasing(self) -> None:
        delays = [next_delay(n, CONFIG) for n in range(10)]
        assert delays == sorted(delays)


class TestSendBatch:
    async def test_posts_payload_with_api_key_header(self) -> None:
        captured: dict[str, httpx.Request] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["request"] = request
            return httpx.Response(200, json={"accepted": 1, "duplicated": 0, "batch_id": 1})

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, base_url="http://core.test") as client:
            response = await send_batch(client, "/ingest/trades", "key-123", '{"a":1}')

        assert response.status_code == 200
        request = captured["request"]
        assert request.headers["X-API-Key"] == "key-123"
        assert request.headers["Content-Type"] == "application/json"
        assert request.content == b'{"a":1}'
        assert request.url.path == "/ingest/trades"

    async def test_propagates_connect_errors(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route to host", request=request)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport, base_url="http://core.test") as client:
            with pytest.raises(httpx.ConnectError):
                await send_batch(client, "/ingest/trades", "key-123", "{}")
