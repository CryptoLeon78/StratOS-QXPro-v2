"""`SimulatedMt5Client`: reloj propio, deals acumulados (no reemplazados),
filtrado por rango de fechas en `history_deals_get`."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from connector.protocol import AccountInfoDTO, DealDTO

from simulator.client import SimulatedMt5Client, TimelineStep

_ACCOUNT_A = AccountInfoDTO(
    balance=Decimal("100000"), equity=Decimal("100000"), margin_level=1500.0, margin_free=None
)
_ACCOUNT_B = AccountInfoDTO(
    balance=Decimal("90000"), equity=Decimal("90000"), margin_level=800.0, margin_free=None
)


def _deal(ticket: int, close: datetime) -> DealDTO:
    return DealDTO(
        ticket=ticket,
        symbol="EURUSD",
        type="BUY",
        volume=Decimal("0.1"),
        price_open=Decimal("1.08"),
        price_close=Decimal("1.09"),
        sl=None,
        tp=None,
        profit=Decimal("10"),
        commission=Decimal("0"),
        swap=Decimal("0"),
        magic=118231,
        time_open=close,
        time_close=close,
    )


def test_empty_timeline_raises() -> None:
    with pytest.raises(ValueError, match="timeline"):
        SimulatedMt5Client(timeline=[])


def test_account_info_reflects_current_step_after_advance() -> None:
    client = SimulatedMt5Client(
        [
            TimelineStep(elapsed_seconds=0.0, account=_ACCOUNT_A),
            TimelineStep(elapsed_seconds=60.0, account=_ACCOUNT_B),
        ]
    )
    assert client.account_info() == _ACCOUNT_A
    client.advance(30.0)
    assert client.account_info() == _ACCOUNT_A
    client.advance(31.0)
    assert client.account_info() == _ACCOUNT_B


def test_history_deals_get_accumulates_across_steps() -> None:
    t1 = datetime(2026, 8, 26, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    client = SimulatedMt5Client(
        [
            TimelineStep(elapsed_seconds=0.0, account=_ACCOUNT_A, new_deals=[_deal(1, t1)]),
            TimelineStep(elapsed_seconds=60.0, account=_ACCOUNT_A, new_deals=[_deal(2, t2)]),
        ]
    )
    client.advance(60.0)
    deals = client.history_deals_get(
        datetime(2026, 8, 26, tzinfo=UTC), datetime(2026, 8, 27, tzinfo=UTC)
    )
    assert {d.ticket for d in deals} == {1, 2}


def test_history_deals_get_only_returns_deals_seen_so_far() -> None:
    t1 = datetime(2026, 8, 26, 9, 0, tzinfo=UTC)
    t2 = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    client = SimulatedMt5Client(
        [
            TimelineStep(elapsed_seconds=0.0, account=_ACCOUNT_A, new_deals=[_deal(1, t1)]),
            TimelineStep(elapsed_seconds=60.0, account=_ACCOUNT_A, new_deals=[_deal(2, t2)]),
        ]
    )
    # sin avanzar el reloj: solo el primer step es visible
    deals = client.history_deals_get(
        datetime(2026, 8, 26, tzinfo=UTC), datetime(2026, 8, 27, tzinfo=UTC)
    )
    assert {d.ticket for d in deals} == {1}


def test_lifecycle_and_error_methods_are_no_ops() -> None:
    client = SimulatedMt5Client([TimelineStep(elapsed_seconds=0.0, account=_ACCOUNT_A)])
    assert client.initialize() is True
    assert client.login(100231, "pw", "Darwinex-Live") is True
    assert client.last_error() == (0, "no error")
    assert client.shutdown() is None


def test_history_deals_get_filters_by_date_range() -> None:
    t1 = datetime(2026, 8, 26, 9, 0, tzinfo=UTC)
    client = SimulatedMt5Client(
        [TimelineStep(elapsed_seconds=0.0, account=_ACCOUNT_A, new_deals=[_deal(1, t1)])]
    )
    deals = client.history_deals_get(
        datetime(2026, 8, 27, tzinfo=UTC), datetime(2026, 8, 28, tzinfo=UTC)
    )
    assert deals == []
