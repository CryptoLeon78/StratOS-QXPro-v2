"""`run()`: prueba de humo del cableado (buffer+poller+sender+cliente MT5),
NO una verificacion de servicio real (ver docstring de `main.py`). Corre
`run()` con intervalos muy cortos y un `core_engine_url` que nunca
respondera con exito (puerto sin nada escuchando -- el sender absorbe el
fallo, igual que un corte de red real), lo cancela tras una ventana breve
y confirma que no crashea ni deja tareas sin cancelar."""

import asyncio
from pathlib import Path

import pytest
from simulator.client import SimulatedMt5Client
from simulator.scenarios.posicion_sin_sl import build_posicion_sin_sl_timeline

from connector.buffer import Buffer
from connector.config import ConnectorSettings
from connector.main import _get_or_create_connector_instance_id, run


class _FailingInitClient(SimulatedMt5Client):
    def initialize(self, path: str | None = None) -> bool:  # type: ignore[override]
        return False

    def last_error(self) -> tuple[int, str]:
        return (1, "terminal no disponible")


async def test_get_or_create_connector_instance_id_reuses_existing(tmp_path: Path) -> None:
    buffer = Buffer(str(tmp_path / "outbox.sqlite"))
    await buffer.connect()
    first = await _get_or_create_connector_instance_id(buffer)
    second = await _get_or_create_connector_instance_id(buffer)
    assert first == second
    await buffer.close()


async def test_run_propagates_mt5_terminal_path_to_initialize(tmp_path: Path) -> None:
    """G11: confirma que `run()` propaga `settings.mt5_terminal_path` hasta
    `initialize()` -- con 2+ terminales instalados, `initialize()` sin
    `path` es ambiguo (ver `real_adapter.py`)."""
    received_paths: list[str | None] = []

    class _PathSpyClient(SimulatedMt5Client):
        def initialize(self, path: str | None = None) -> bool:  # type: ignore[override]
            received_paths.append(path)
            return False

        def last_error(self) -> tuple[int, str]:
            return (1, "terminal no disponible")

    settings = ConnectorSettings(
        core_engine_url="http://127.0.0.1:1",
        ingest_api_key="key",
        account_login="100231",
        buffer_db_path=str(tmp_path / "outbox.sqlite"),
        mt5_terminal_path=r"C:\Program Files\MetaTrader 5\terminal64.exe",
    )
    client = _PathSpyClient(build_posicion_sin_sl_timeline())
    with pytest.raises(RuntimeError, match="initialize"):
        await run(client, settings)
    assert received_paths == [r"C:\Program Files\MetaTrader 5\terminal64.exe"]


async def test_run_raises_when_mt5_initialize_fails(tmp_path: Path) -> None:
    settings = ConnectorSettings(
        core_engine_url="http://127.0.0.1:1",
        ingest_api_key="key",
        account_login="100231",
        buffer_db_path=str(tmp_path / "outbox.sqlite"),
    )
    client = _FailingInitClient(build_posicion_sin_sl_timeline())
    with pytest.raises(RuntimeError, match="initialize"):
        await run(client, settings)


async def test_run_wires_up_and_shuts_down_cleanly_on_cancel(tmp_path: Path) -> None:
    settings = ConnectorSettings(
        core_engine_url="http://127.0.0.1:1",  # nada escucha ahi: falla rapido, no cuelga
        ingest_api_key="key",
        account_login="100231",
        positions_poll_interval_s=0.01,
        deals_poll_interval_s=0.01,
        equity_poll_interval_s=0.01,
        heartbeat_interval_s=0.01,
        buffer_db_path=str(tmp_path / "outbox.sqlite"),
    )
    client = SimulatedMt5Client(build_posicion_sin_sl_timeline())

    task = asyncio.create_task(run(client, settings))
    await asyncio.sleep(0.2)
    assert not task.done()  # sigue vivo (los bucles nunca retornan por si solos)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
