"""Los 5 escenarios de PARTE 12/13 producen timelines bien formados."""

from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from simulator.client import SimulatedMt5Client
from simulator.scenarios.bot_degradado import build_bot_degradado_timeline
from simulator.scenarios.corte_de_red import FlakyTransport
from simulator.scenarios.crash_21 import PEAK_EQUITY, build_crash_21_timeline
from simulator.scenarios.huerfanos import ORPHAN_MAGIC, build_huerfanos_timeline
from simulator.scenarios.posicion_sin_sl import MAGIC, build_posicion_sin_sl_timeline


def test_crash_21_drops_equity_by_at_least_21_pct() -> None:
    timeline = build_crash_21_timeline()
    client = SimulatedMt5Client(timeline)
    client.advance(60.0)
    account = client.account_info()
    assert account is not None
    drop_pct = (PEAK_EQUITY - account.equity) / PEAK_EQUITY * 100
    assert drop_pct >= Decimal("21")


def test_bot_degradado_has_a_single_deal_then_silence() -> None:
    timeline = build_bot_degradado_timeline()
    client = SimulatedMt5Client(timeline)
    client.advance(4000.0)  # mas alla del ultimo step
    deals = client.history_deals_get(
        datetime(2026, 1, 1, tzinfo=UTC), datetime(2027, 1, 1, tzinfo=UTC)
    )
    assert len(deals) == 1


def test_posicion_sin_sl_has_no_stop_loss() -> None:
    timeline = build_posicion_sin_sl_timeline()
    client = SimulatedMt5Client(timeline)
    positions = client.positions_get()
    assert len(positions) == 1
    assert positions[0].sl is None
    assert positions[0].magic == MAGIC


def test_huerfanos_uses_a_magic_number_with_no_registered_bot() -> None:
    timeline = build_huerfanos_timeline()
    client = SimulatedMt5Client(timeline)
    positions = client.positions_get()
    assert all(p.magic == ORPHAN_MAGIC for p in positions)
    deals = client.history_deals_get(
        datetime(2026, 1, 1, tzinfo=UTC), datetime(2027, 1, 1, tzinfo=UTC)
    )
    assert all(d.magic == ORPHAN_MAGIC for d in deals)


class _StubTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, request=request)


async def test_flaky_transport_fails_then_recovers() -> None:
    transport = FlakyTransport(wrapped=_StubTransport(), fail_calls=2)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with pytest.raises(httpx.ConnectError):
            await client.get("/x")
        with pytest.raises(httpx.ConnectError):
            await client.get("/x")
        response = await client.get("/x")
        assert response.status_code == 200
    assert transport.attempts == 3
