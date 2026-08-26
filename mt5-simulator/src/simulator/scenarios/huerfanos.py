"""Prosa de PARTE 12 ("huerfanos"): deals/posiciones con un `magic_number`
que no corresponde a ningun `Bot` registrado -- `bot_id` queda NULL en la
ingesta (PARTE 5.2), nunca se rechaza."""

from datetime import UTC, datetime
from decimal import Decimal

from connector.protocol import AccountInfoDTO, DealDTO, PositionDTO

from simulator.client import TimelineStep

ORPHAN_MAGIC = 999999
ORPHAN_TICKET = 6000001


def build_huerfanos_timeline() -> list[TimelineStep]:
    equity = Decimal("50000.00")
    open_time = datetime(2026, 8, 26, 9, 0, tzinfo=UTC)
    close_time = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
    deal = DealDTO(
        ticket=ORPHAN_TICKET,
        symbol="XAUUSD",
        type="SELL",
        volume=Decimal("0.05"),
        price_open=Decimal("2400.00000"),
        price_close=Decimal("2395.00000"),
        sl=Decimal("2410.00000"),
        tp=Decimal("2380.00000"),
        profit=Decimal("25.00"),
        commission=Decimal("-0.50"),
        swap=Decimal("0.00"),
        magic=ORPHAN_MAGIC,
        time_open=open_time,
        time_close=close_time,
    )
    position = PositionDTO(
        ticket=ORPHAN_TICKET + 1,
        symbol="XAUUSD",
        type="SELL",
        volume=Decimal("0.05"),
        price_open=Decimal("2400.00000"),
        sl=Decimal("2410.00000"),
        tp=Decimal("2380.00000"),
        profit=Decimal("1.10"),
        magic=ORPHAN_MAGIC,
        time=open_time,
    )
    return [
        TimelineStep(
            elapsed_seconds=0.0,
            account=AccountInfoDTO(
                balance=equity, equity=equity, margin_level=1500.0, margin_free=equity
            ),
            positions=[position],
            new_deals=[deal],
        )
    ]
