"""TDD G11: contrato cerrado del parser SQX144, sin fixture externo."""

import io
import struct
import zipfile
from datetime import UTC, datetime, timedelta

import pytest

from core.services.sqx_baseline_parser import parse_sqx144_baseline


def _record(opened: datetime, closed: datetime, pnl: float) -> bytes:
    row = bytearray(149)
    row[:4] = b"\x04\x03\x02\x01"
    row[15:23] = struct.pack(">q", int(opened.timestamp() * 1000))
    row[44:52] = struct.pack(">q", int(closed.timestamp() * 1000))
    row[66:70] = struct.pack(">f", pnl)
    return bytes(row)


def _artifact(build: str = "SQX Build 144.2938", include_orders: bool = True) -> bytes:
    stream = io.BytesIO()
    now = datetime(2025, 1, 1, tzinfo=UTC)
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("strategy_Portfolio.xml", f'<Strategy AppVersion="{build}"/>')
        archive.writestr(
            "lastSettings.xml",
            '<Chart symbol="EURUSD" timeframe="H1"/>'
            '<Setup dateFrom="2024.01.01" dateTo="2025.01.01"/>'
            "<InitialCapital>10000</InitialCapital>",
        )
        if include_orders:
            records = _record(now, now + timedelta(hours=1), 120.0) + _record(
                now + timedelta(days=1), now + timedelta(days=1, hours=1), -60.0
            )
            archive.writestr("orders.bin", b"\x7a" + struct.pack(">I", len(records)) + records)
    return stream.getvalue()


def test_accepts_complete_sqx144_artifact() -> None:
    parsed = parse_sqx144_baseline(_artifact())
    assert parsed.build == "SQX Build 144.2938"
    assert parsed.symbol == "EURUSD"
    assert parsed.trade_count == 2
    assert parsed.profit_factor == pytest.approx(2.0)


def test_rejects_non_sqx144_or_missing_required_member() -> None:
    with pytest.raises(ValueError, match="SQX144"):
        parse_sqx144_baseline(_artifact("SQX Build 143.999"))
    with pytest.raises(ValueError, match="faltan miembros"):
        parse_sqx144_baseline(_artifact(include_orders=False))
