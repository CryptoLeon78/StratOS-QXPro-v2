"""Prosa de PARTE 12 ("posicion sin SL"): una posicion abierta con `sl=None`
para ejercitar P5 end-to-end (Alert CRITICA via `/ingest/positions`)."""

from datetime import UTC, datetime
from decimal import Decimal

from connector.protocol import AccountInfoDTO, PositionDTO

from simulator.client import TimelineStep

MAGIC = 118231
TICKET = 5000001


def build_posicion_sin_sl_timeline() -> list[TimelineStep]:
    equity = Decimal("50000.00")
    position = PositionDTO(
        ticket=TICKET,
        symbol="EURUSD",
        type="BUY",
        volume=Decimal("0.10"),
        price_open=Decimal("1.08500"),
        sl=None,
        tp=Decimal("1.09000"),
        profit=Decimal("3.20"),
        magic=MAGIC,
        time=datetime(2026, 8, 26, 9, 0, tzinfo=UTC),
    )
    return [
        TimelineStep(
            elapsed_seconds=0.0,
            account=AccountInfoDTO(
                balance=equity, equity=equity, margin_level=1500.0, margin_free=equity
            ),
            positions=[position],
        )
    ]
