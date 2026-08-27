import asyncio

import pytest
from starlette.websockets import WebSocketDisconnect

from gateway.ws_proxy import bridge_frames


class _FakeClient:
    """Simula un WebSocket de FastAPI/Starlette. `receive_text()` bloquea
    indefinidamente si no hay mas mensajes en cola (un cliente real bloquea
    en receive() hasta el proximo frame o la desconexion real -- una cola
    vacia por si sola no es senal de nada)."""

    def __init__(self, incoming: list[str]) -> None:
        self._incoming = list(incoming)
        self.sent: list[str] = []

    async def receive_text(self) -> str:
        if self._incoming:
            return self._incoming.pop(0)
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    async def send_text(self, data: str) -> None:
        self.sent.append(data)


class _DisconnectingClient(_FakeClient):
    """Variante que SI señala el fin: agota la cola y lanza
    WebSocketDisconnect, igual que Starlette cuando el cliente cierra."""

    async def receive_text(self) -> str:
        if self._incoming:
            return self._incoming.pop(0)
        raise WebSocketDisconnect()


class _FakeUpstream:
    """Simula la conexion saliente de `websockets` hacia core-engine.
    `__anext__` bloquea indefinidamente si no hay mas mensajes (mismo
    criterio que _FakeClient: una cola vacia no es un cierre)."""

    def __init__(self, incoming: list[str]) -> None:
        self._incoming = list(incoming)
        self.sent: list[str] = []

    async def send(self, data: str) -> None:
        self.sent.append(data)

    def __aiter__(self) -> "_FakeUpstream":
        return self

    async def __anext__(self) -> str:
        if self._incoming:
            return self._incoming.pop(0)
        await asyncio.Event().wait()
        raise AssertionError("unreachable")


class _ClosingUpstream(_FakeUpstream):
    """Variante que SI señala el fin: agota la cola y termina la
    iteracion (`websockets` hace exactamente esto en un cierre limpio)."""

    async def __anext__(self) -> str:
        if self._incoming:
            return self._incoming.pop(0)
        raise StopAsyncIteration


@pytest.mark.asyncio
async def test_relays_client_messages_to_upstream_in_order_until_client_disconnects() -> None:
    client = _DisconnectingClient(["a", "b"])
    upstream = _FakeUpstream([])

    await asyncio.wait_for(bridge_frames(client, upstream), timeout=2)

    assert upstream.sent == ["a", "b"]


@pytest.mark.asyncio
async def test_relays_upstream_messages_to_client_in_order_until_upstream_closes() -> None:
    client = _FakeClient([])
    upstream = _ClosingUpstream(["x", "y"])

    await asyncio.wait_for(bridge_frames(client, upstream), timeout=2)

    assert client.sent == ["x", "y"]
