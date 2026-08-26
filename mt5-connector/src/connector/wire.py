"""Forma de los 4 payloads que el poller realmente envia (positions/trades/
equity/heartbeat -- PARTE 12: "polling posiciones/deals/equity/heartbeat".
`signals`/`execution`/`ea_state` no son polling de MT5, son reportes del
propio EA -- fuera del alcance del poller de G4).

Modelos de REQUEST completos (no solo los items), para que TODO campo --
incluido `ts` a nivel de request, no solo los anidados -- pase por el
mismo `model_dump(mode="json")` que el servidor usa al recanonicalizar
(PARTE 6/9.1). Verificado con una llamada HTTP real antes de escribir
esto: Pydantic serializa `datetime` con sufijo "Z", pero
`datetime.isoformat()` puro da "+00:00" -- si UN SOLO campo se construyera
a mano en vez de via Pydantic, el sello no coincidiria byte a byte pese a
representar el mismo dato.

Estos modelos NO son estrictos (son de salida, no de validacion) y NO se
comparten con `core-engine` (serian una dependencia pesada al reves, ver
`stratos-ingest-seal`/ASSUMPTIONS G4) -- solo replican la MISMA forma de
campos y el MISMO modo de dump que `core.ingest.schemas`."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from connector.protocol import AccountInfoDTO, DealDTO, PositionDTO


class WireTrade(BaseModel):
    ticket_mt5: int
    symbol: str
    magic_number: int
    type: str
    volume: Decimal
    open_time: datetime
    close_time: datetime
    open_price: Decimal
    close_price: Decimal
    sl: Decimal | None
    tp: Decimal | None
    profit: Decimal
    commission: Decimal
    swap: Decimal


class WirePosition(BaseModel):
    ticket_mt5: int
    symbol: str
    magic_number: int
    type: str
    volume: Decimal
    open_time: datetime
    open_price: Decimal
    sl: Decimal | None
    tp: Decimal | None
    profit: Decimal


class WireTradesRequest(BaseModel):
    account_login: str
    connector_instance_id: str
    trades: list[WireTrade]


class WirePositionsRequest(BaseModel):
    account_login: str
    connector_instance_id: str
    ts: datetime
    positions: list[WirePosition]


class WireEquityRequest(BaseModel):
    account_login: str
    connector_instance_id: str
    ts: datetime
    equity: Decimal
    balance: Decimal
    margin_level: float | None
    free_margin: Decimal | None


class WireHeartbeatRequest(BaseModel):
    connector_instance_id: str
    account_login: str
    latency_ms: int
    ts: datetime


def deal_to_wire(deal: DealDTO) -> WireTrade:
    return WireTrade(
        ticket_mt5=deal.ticket,
        symbol=deal.symbol,
        magic_number=deal.magic,
        type=deal.type,
        volume=deal.volume,
        open_time=deal.time_open,
        close_time=deal.time_close,
        open_price=deal.price_open,
        close_price=deal.price_close,
        sl=deal.sl,
        tp=deal.tp,
        profit=deal.profit,
        commission=deal.commission,
        swap=deal.swap,
    )


def position_to_wire(position: PositionDTO) -> WirePosition:
    return WirePosition(
        ticket_mt5=position.ticket,
        symbol=position.symbol,
        magic_number=position.magic,
        type=position.type,
        volume=position.volume,
        open_time=position.time,
        open_price=position.price_open,
        sl=position.sl,
        tp=position.tp,
        profit=position.profit,
    )


def account_to_equity_request(
    account: AccountInfoDTO, account_login: str, connector_instance_id: str, ts: datetime
) -> WireEquityRequest:
    return WireEquityRequest(
        account_login=account_login,
        connector_instance_id=connector_instance_id,
        ts=ts,
        equity=account.equity,
        balance=account.balance,
        margin_level=account.margin_level,
        free_margin=account.margin_free,
    )
