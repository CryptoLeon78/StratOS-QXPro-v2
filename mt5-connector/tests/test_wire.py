"""`wire.py`: `model_dump(mode="json")` preserva la precision exacta del
Decimal (no la del float) y usa sufijo "Z" en datetime -- el mismo
criterio que `core.ingest.schemas` del lado servidor (verificado con una
llamada HTTP real antes de escribir wire.py). La paridad byte a byte
completa contra el servidor real se prueba en integration-tests/, no aqui
(mt5-connector no depende de core-engine a proposito)."""

from datetime import UTC, datetime
from decimal import Decimal

from connector.protocol import AccountInfoDTO, DealDTO, PositionDTO
from connector.wire import (
    WireEquityRequest,
    WireHeartbeatRequest,
    WirePositionsRequest,
    WireTradesRequest,
    account_to_equity_request,
    deal_to_wire,
    position_to_wire,
)


def test_decimal_preserves_trailing_zeros() -> None:
    trade = deal_to_wire(
        DealDTO(
            ticket=1,
            symbol="EURUSD",
            type="BUY",
            volume=Decimal("0.10"),
            price_open=Decimal("1.08500"),
            price_close=Decimal("1.08600"),
            sl=Decimal("1.08000"),
            tp=None,
            profit=Decimal("10.50"),
            commission=Decimal("-0.50"),
            swap=Decimal("0.00"),
            magic=118231,
            time_open=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
            time_close=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
        )
    )
    dumped = trade.model_dump(mode="json")
    assert dumped["profit"] == "10.50"
    assert dumped["volume"] == "0.10"
    assert dumped["tp"] is None


def test_datetime_uses_z_suffix_not_plus_00_00() -> None:
    position = position_to_wire(
        PositionDTO(
            ticket=1,
            symbol="EURUSD",
            type="BUY",
            volume=Decimal("0.10"),
            price_open=Decimal("1.085"),
            sl=None,
            tp=None,
            profit=Decimal("0"),
            magic=118231,
            time=datetime(2026, 8, 26, 9, 0, tzinfo=UTC),
        )
    )
    dumped = position.model_dump(mode="json")
    assert dumped["open_time"] == "2026-08-26T09:00:00Z"


def test_wire_trades_request_shape() -> None:
    trade = deal_to_wire(
        DealDTO(
            ticket=1,
            symbol="EURUSD",
            type="BUY",
            volume=Decimal("0.1"),
            price_open=Decimal("1.085"),
            price_close=Decimal("1.086"),
            sl=None,
            tp=None,
            profit=Decimal("10"),
            commission=Decimal("0"),
            swap=Decimal("0"),
            magic=118231,
            time_open=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
            time_close=datetime(2026, 8, 20, 10, 0, tzinfo=UTC),
        )
    )
    request = WireTradesRequest(
        account_login="100231", connector_instance_id="conn-1", trades=[trade]
    )
    dumped = request.model_dump(mode="json")
    assert set(dumped.keys()) == {"account_login", "connector_instance_id", "trades"}
    assert len(dumped["trades"]) == 1


def test_wire_positions_request_shape() -> None:
    request = WirePositionsRequest(
        account_login="100231",
        connector_instance_id="conn-1",
        ts=datetime(2026, 8, 26, 12, 0, tzinfo=UTC),
        positions=[],
    )
    dumped = request.model_dump(mode="json")
    assert dumped["ts"] == "2026-08-26T12:00:00Z"
    assert dumped["positions"] == []


def test_account_to_equity_request() -> None:
    account = AccountInfoDTO(
        balance=Decimal("100000.00"),
        equity=Decimal("99000.50"),
        margin_level=1500.0,
        margin_free=Decimal("95000.00"),
    )
    request = account_to_equity_request(
        account, "100231", "conn-1", datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    )
    assert isinstance(request, WireEquityRequest)
    dumped = request.model_dump(mode="json")
    assert dumped["equity"] == "99000.50"
    assert dumped["margin_level"] == 1500.0


def test_wire_heartbeat_request_shape() -> None:
    request = WireHeartbeatRequest(
        connector_instance_id="conn-1",
        account_login="100231",
        latency_ms=42,
        ts=datetime(2026, 8, 26, 12, 0, tzinfo=UTC),
    )
    dumped = request.model_dump(mode="json")
    assert dumped["latency_ms"] == 42
    assert dumped["ts"] == "2026-08-26T12:00:00Z"
