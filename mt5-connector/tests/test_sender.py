"""PARTE 12: sender. `drain_once` es la unica pieza que toca la red;
verifica exito (mark_sent), fallo transitorio (mark_failed con backoff) y
rechazo permanente (descartado, sin reintento)."""

from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from connector.buffer import Buffer
from connector.http_client import BackoffConfig
from connector.sender import drain_once

BACKOFF = BackoffConfig(base_seconds=5.0, multiplier=2.0, max_seconds=300.0)


@pytest.fixture
async def buffer(tmp_path: Path) -> Buffer:
    buf = Buffer(str(tmp_path / "outbox.sqlite"))
    await buf.connect()
    return buf


def _client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler, base_url="http://core.test")


async def test_successful_send_marks_sent(buffer: Buffer) -> None:
    await buffer.enqueue("trades", '{"a":1}')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"accepted": 1})

    async with _client(httpx.MockTransport(handler)) as client:
        sent = await drain_once(client, buffer, "key", BACKOFF, datetime.now(UTC))

    assert sent == 1
    due = await buffer.due_batches(datetime.now(UTC), limit=10)
    assert due == []


async def test_connect_error_marks_failed_with_backoff(buffer: Buffer) -> None:
    row_id = await buffer.enqueue("trades", '{"a":1}')

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("corte de red", request=request)

    async with _client(httpx.MockTransport(handler)) as client:
        sent = await drain_once(client, buffer, "key", BACKOFF, datetime.now(UTC))

    assert sent == 0
    # no vencido todavia (el backoff lo empujo al futuro)
    due_now = await buffer.due_batches(datetime.now(UTC), limit=10)
    assert due_now == []
    due_later = await buffer.due_batches(datetime.now(UTC).replace(year=2030), limit=10)
    assert len(due_later) == 1
    assert due_later[0].id == row_id
    assert due_later[0].attempts == 1


async def test_500_is_retryable(buffer: Buffer) -> None:
    await buffer.enqueue("trades", '{"a":1}')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with _client(httpx.MockTransport(handler)) as client:
        sent = await drain_once(client, buffer, "key", BACKOFF, datetime.now(UTC))

    assert sent == 0
    due_later = await buffer.due_batches(datetime.now(UTC).replace(year=2030), limit=10)
    assert len(due_later) == 1
    assert due_later[0].attempts == 1


async def test_429_is_retryable(buffer: Buffer) -> None:
    await buffer.enqueue("trades", '{"a":1}')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    async with _client(httpx.MockTransport(handler)) as client:
        await drain_once(client, buffer, "key", BACKOFF, datetime.now(UTC))

    due_later = await buffer.due_batches(datetime.now(UTC).replace(year=2030), limit=10)
    assert len(due_later) == 1


@pytest.mark.parametrize("status_code", [401, 403])
async def test_auth_failures_are_retained_for_retry(buffer: Buffer, status_code: int) -> None:
    """Una credencial rotada no puede convertir telemetria real en perdida."""
    await buffer.enqueue("heartbeat", '{"a":1}')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    async with _client(httpx.MockTransport(handler)) as client:
        sent = await drain_once(client, buffer, "key", BACKOFF, datetime.now(UTC))

    assert sent == 0
    due_later = await buffer.due_batches(datetime.now(UTC).replace(year=2030), limit=10)
    assert len(due_later) == 1
    assert due_later[0].attempts == 1


async def test_422_seal_mismatch_is_discarded_not_retried(buffer: Buffer) -> None:
    await buffer.enqueue("trades", '{"a":1}')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": "seal mismatch"})

    async with _client(httpx.MockTransport(handler)) as client:
        sent = await drain_once(client, buffer, "key", BACKOFF, datetime.now(UTC))

    assert sent == 0
    due = await buffer.due_batches(datetime.now(UTC).replace(year=2030), limit=10)
    assert due == []  # descartado, no queda en la cola


async def test_404_unknown_account_is_discarded_not_retried(buffer: Buffer) -> None:
    await buffer.enqueue("trades", '{"a":1}')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with _client(httpx.MockTransport(handler)) as client:
        await drain_once(client, buffer, "key", BACKOFF, datetime.now(UTC))

    due = await buffer.due_batches(datetime.now(UTC).replace(year=2030), limit=10)
    assert due == []


async def test_processes_multiple_rows_in_order(buffer: Buffer) -> None:
    await buffer.enqueue("trades", '{"a":1}')
    await buffer.enqueue("equity", '{"a":2}')
    seen_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        return httpx.Response(200)

    async with _client(httpx.MockTransport(handler)) as client:
        sent = await drain_once(client, buffer, "key", BACKOFF, datetime.now(UTC))

    assert sent == 2
    assert seen_paths == ["/ingest/trades", "/ingest/equity"]


async def test_respects_limit(buffer: Buffer) -> None:
    for i in range(5):
        await buffer.enqueue("heartbeat", f'{{"i":{i}}}')

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with _client(httpx.MockTransport(handler)) as client:
        sent = await drain_once(client, buffer, "key", BACKOFF, datetime.now(UTC), limit=2)

    assert sent == 2
