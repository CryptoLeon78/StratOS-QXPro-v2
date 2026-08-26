"""PARTE 9.1: DTOs de ingesta. `model_validate(dict)` es exactamente lo que
FastAPI hace internamente tras decodificar el JSON del body (verificado con
una llamada HTTP real antes de escribir schemas.py: parsea el JSON a dict
primero, no usa `model_validate_json`) -- por eso estos tests usan dicts
"tal cual llegarian por JSON" (numeros float, fechas ISO string), no
instancias de Decimal/datetime ya construidas."""

import pytest
from pydantic import ValidationError

from core.ingest.schemas import (
    EaStateIngestRequest,
    EquityIngestRequest,
    ExecutionIngestRequest,
    HeartbeatIngestRequest,
    PositionsIngestRequest,
    SignalsIngestRequest,
    TradesIngestRequest,
)

SEAL = "a" * 64


class TestLaxDecimalAndDatetimeAcceptRealisticJson:
    def test_trades_accepts_float_and_iso_datetime(self) -> None:
        req = TradesIngestRequest.model_validate(
            {
                "account_login": "100231",
                "connector_instance_id": "conn-1",
                "batch_sha256": SEAL,
                "trades": [
                    {
                        "ticket_mt5": 3000001,
                        "symbol": "EURUSD",
                        "magic_number": 118231,
                        "type": "BUY",
                        "volume": 0.1,
                        "open_time": "2026-08-20T09:00:00Z",
                        "close_time": "2026-08-20T10:00:00Z",
                        "open_price": 1.085,
                        "close_price": 1.086,
                        "sl": 1.08,
                        "tp": 1.09,
                        "profit": 10.5,
                        "commission": -0.5,
                        "swap": 0.0,
                    }
                ],
            }
        )
        assert req.trades[0].ticket_mt5 == 3000001
        assert str(req.trades[0].profit) == "10.5"

    def test_positions_accepts_float_and_iso_datetime(self) -> None:
        req = PositionsIngestRequest.model_validate(
            {
                "account_login": "100231",
                "connector_instance_id": "conn-1",
                "batch_sha256": SEAL,
                "ts": "2026-08-26T12:00:00Z",
                "positions": [
                    {
                        "ticket_mt5": 3000002,
                        "symbol": "XAUUSD",
                        "magic_number": 118344,
                        "type": "SELL",
                        "volume": 0.05,
                        "open_time": "2026-08-26T11:00:00Z",
                        "open_price": 2400.0,
                        "sl": None,
                        "tp": None,
                        "profit": -3.2,
                    }
                ],
            }
        )
        assert req.positions[0].sl is None

    def test_equity_accepts_float(self) -> None:
        req = EquityIngestRequest.model_validate(
            {
                "account_login": "100231",
                "connector_instance_id": "conn-1",
                "batch_sha256": SEAL,
                "ts": "2026-08-26T12:00:00Z",
                "equity": 179642.70,
                "balance": 179642.70,
                "margin_level": 1500.0,
                "free_margin": 175000.0,
            }
        )
        assert str(req.equity) == "179642.7"


class TestStrictFieldsRejectTypeConfusion:
    def test_magic_number_as_string_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PositionsIngestRequest.model_validate(
                {
                    "account_login": "100231",
                    "connector_instance_id": "conn-1",
                    "batch_sha256": SEAL,
                    "ts": "2026-08-26T12:00:00Z",
                    "positions": [
                        {
                            "ticket_mt5": 3000002,
                            "symbol": "XAUUSD",
                            "magic_number": "118344",  # deberia ser int
                            "type": "SELL",
                            "volume": 0.05,
                            "open_time": "2026-08-26T11:00:00Z",
                            "open_price": 2400.0,
                            "profit": -3.2,
                        }
                    ],
                }
            )

    def test_autotrading_as_string_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            EaStateIngestRequest.model_validate(
                {
                    "account_login": "100231",
                    "connector_instance_id": "conn-1",
                    "batch_sha256": SEAL,
                    "eas": [
                        {
                            "magic": 118231,
                            "ea_version": "1.0.0",
                            "mode": "REAL",
                            "autotrading": "true",  # deberia ser bool
                        }
                    ],
                }
            )

    def test_invalid_trade_type_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SignalsIngestRequest.model_validate(
                {
                    "account_login": "100231",
                    "connector_instance_id": "conn-1",
                    "batch_sha256": SEAL,
                    "magic": 118344,
                    "signals": [
                        {
                            "signal_id": "sig-1",
                            "symbol": "XAUUSD",
                            "type": "HOLD",  # no existe en TradeType
                            "volume": 0.1,
                            "entry_price": 2400.0,
                            "ts": "2026-08-26T12:00:00Z",
                        }
                    ],
                }
            )


class TestBatchSha256Shape:
    def test_wrong_length_seal_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            HeartbeatIngestRequest.model_validate(
                {
                    "connector_instance_id": "conn-1",
                    "account_login": "100231",
                    "latency_ms": 42,
                    "batch_sha256": "too-short",
                }
            )

    def test_heartbeat_valid_payload(self) -> None:
        req = HeartbeatIngestRequest.model_validate(
            {
                "connector_instance_id": "conn-1",
                "account_login": "100231",
                "latency_ms": 42,
                "batch_sha256": SEAL,
            }
        )
        assert req.latency_ms == 42


class TestExecutionAndEaStateShapes:
    def test_execution_valid_payload(self) -> None:
        req = ExecutionIngestRequest.model_validate(
            {
                "account_login": "100231",
                "connector_instance_id": "conn-1",
                "batch_sha256": SEAL,
                "magic": 118231,
                "fills": [
                    {
                        "order_id": "ord-1",
                        "symbol": "EURUSD",
                        "requested_price": 1.0850,
                        "executed_price": 1.0851,
                        "spread": 0.0001,
                        "ts": "2026-08-26T12:00:00Z",
                    }
                ],
            }
        )
        assert req.fills[0].order_id == "ord-1"

    def test_ea_state_valid_payload_with_jsonb_fields(self) -> None:
        req = EaStateIngestRequest.model_validate(
            {
                "account_login": "100231",
                "connector_instance_id": "conn-1",
                "batch_sha256": SEAL,
                "eas": [
                    {
                        "magic": 118231,
                        "ea_version": "1.0.3",
                        "mode": "REAL",
                        "autotrading": True,
                        "schedule_filter": {"days": ["MON", "TUE"]},
                        "news_windows": [{"from": "12:00", "to": "13:00"}],
                    }
                ],
            }
        )
        assert req.eas[0].schedule_filter == {"days": ["MON", "TUE"]}
