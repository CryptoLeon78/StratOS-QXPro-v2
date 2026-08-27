"""WS broker (G9, PARTE 3/12): hace pipe de frames entre el WebSocket del
cliente y la conexion saliente hacia core-engine en ambas direcciones,
hasta que cualquiera de los 2 lados termina -- entonces cancela la tarea
que sigue viva, nunca deja una tarea huerfana corriendo en background.
El wiring real (aceptar el WS del cliente, `websockets.connect()` hacia
core-engine) vive en main.py; este modulo es logica pura y testable con
dobles de ambos lados."""

import asyncio
from collections.abc import AsyncIterator
from typing import Protocol

from starlette.websockets import WebSocketDisconnect


class ClientSocket(Protocol):
    async def receive_text(self) -> str: ...
    async def send_text(self, data: str) -> None: ...


class UpstreamSocket(Protocol):
    async def send(self, data: str) -> None: ...
    def __aiter__(self) -> AsyncIterator[str]: ...


async def _pipe_client_to_upstream(client: ClientSocket, upstream: UpstreamSocket) -> None:
    try:
        while True:
            message = await client.receive_text()
            await upstream.send(message)
    except WebSocketDisconnect:
        return


async def _pipe_upstream_to_client(upstream: UpstreamSocket, client: ClientSocket) -> None:
    async for message in upstream:
        await client.send_text(message)


async def bridge_frames(client: ClientSocket, upstream: UpstreamSocket) -> None:
    to_upstream = asyncio.create_task(_pipe_client_to_upstream(client, upstream))
    to_client = asyncio.create_task(_pipe_upstream_to_client(upstream, client))
    await asyncio.wait({to_upstream, to_client}, return_when=asyncio.FIRST_COMPLETED)
    for task in (to_upstream, to_client):
        if not task.done():
            task.cancel()
