"""Prosa de PARTE 12 ("bot degradado"): un bot cuya frecuencia observada
cae muy por debajo de la esperada (watchdog "MUERTO"/"DESBOCADO", PARTE
7.8) -- aqui solo se entrega el timeline (un deal temprano, luego silencio
largo); clasificar MUERTO/DESBOCADO/OK es logica de G5 (watchdog), no de
este escenario."""

from datetime import UTC, datetime
from decimal import Decimal

from connector.protocol import AccountInfoDTO, DealDTO

from simulator.client import TimelineStep

MAGIC = 118900
TICKET = 7000001
SILENCE_SECONDS = 3600.0  # ventana larga sin deals nuevos tras el primero


def build_bot_degradado_timeline() -> list[TimelineStep]:
    equity = Decimal("40000.00")
    open_time = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
    close_time = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
    only_deal = DealDTO(
        ticket=TICKET,
        symbol="GBPUSD",
        type="BUY",
        volume=Decimal("0.10"),
        price_open=Decimal("1.27000"),
        price_close=Decimal("1.27200"),
        sl=Decimal("1.26800"),
        tp=Decimal("1.27500"),
        profit=Decimal("20.00"),
        commission=Decimal("-0.50"),
        swap=Decimal("0.00"),
        magic=MAGIC,
        time_open=open_time,
        time_close=close_time,
    )
    account = AccountInfoDTO(balance=equity, equity=equity, margin_level=1500.0, margin_free=equity)
    return [
        TimelineStep(elapsed_seconds=0.0, account=account, new_deals=[only_deal]),
        # silencio prolongado: mismo account, cero deals/positions nuevos
        TimelineStep(elapsed_seconds=SILENCE_SECONDS, account=account),
    ]
