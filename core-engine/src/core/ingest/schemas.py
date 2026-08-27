"""PARTE 9.1: DTOs de los 7 payloads de ingesta. Pydantic v2 `strict=True`
(PARTE 4, contractual) a nivel de modelo -- `int`/`str`/`bool` quedan
genuinamente estrictos (un `magic_number` como `"118231"` string se
rechaza, no se coacciona en silencio).

`Decimal`/`datetime`/`TradeType` son la excepcion, verificada con una
llamada HTTP real contra un `TestClient`/`ASGITransport`: en modo estricto,
Pydantic solo acepta una INSTANCIA ya construida en Python de esos tipos --
JSON no tiene `Decimal`/`datetime` nativos (solo float/string), y un
`StrEnum` en modo estricto exige el miembro del enum, no el string que lo
representa. CUALQUIER payload real (float, string ISO-8601, o el literal
"BUY"/"SELL") se rechazaria con 422 si se dejan estrictos. Se marcan
`Field(strict=False)` campo a campo (`LaxDecimal`/`LaxDatetime`/
`LaxTradeType`) para que acepten el JSON real que el conector va a enviar,
sin renunciar al strict=True del resto de campos (`int`/`str`/`bool` siguen
rechazando texto/numeros confundidos de tipo).

Todos los payloads llevan `batch_sha256` (PARTE 6: sello del lote, ver
`ingest_seal`) -- el conector lo calcula antes de tocar la red; el servicio
de cada ruta lo revalida antes de persistir nada (fail-closed).

Todos los payloads llevan tambien `connector_instance_id`: `IngestBatch`
(G1) lo exige NOT NULL en TODO lote, no solo en heartbeat -- la notacion
compacta de PARTE 9.1 ({account_login, trades:[...]}) solo lo muestra
explicito para `/ingest/heartbeat` porque ahi es el dato relevante del
endpoint, no porque sea el unico payload que lo lleve (esa misma notacion
tampoco enumera los campos reales de un Trade, y aun asi hacen falta).

`HeartbeatIngestRequest` lleva ademas `ts` (tampoco en la notacion
compacta): `HeartbeatLog.ts` es parte de su PK compuesta
`(ts, connector_instance_id, account_id)` -- si `ts` lo pusiera el
servidor en cada request, un reenvio real (mismo heartbeat, misma
`batch_sha256`) generaria una fila NUEVA en vez de deduplicar, rompiendo
P9 igual que le pasaria a `trades`/`equity` si `open_time`/`ts` no
vinieran del cliente."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from core.db.enums import TradeType

LaxDecimal = Annotated[Decimal, Field(strict=False)]
LaxDatetime = Annotated[datetime, Field(strict=False)]
LaxTradeType = Annotated[TradeType, Field(strict=False)]


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True)


class TradeIn(_Strict):
    ticket_mt5: int
    symbol: str
    magic_number: int
    type: LaxTradeType
    volume: LaxDecimal
    open_time: LaxDatetime
    close_time: LaxDatetime
    open_price: LaxDecimal
    close_price: LaxDecimal
    sl: LaxDecimal | None = None
    tp: LaxDecimal | None = None
    profit: LaxDecimal
    commission: LaxDecimal
    swap: LaxDecimal


class TradesIngestRequest(_Strict):
    account_login: str
    connector_instance_id: str
    trades: list[TradeIn]
    batch_sha256: str = Field(min_length=64, max_length=64)


class PositionIn(_Strict):
    ticket_mt5: int
    symbol: str
    magic_number: int
    type: LaxTradeType
    volume: LaxDecimal
    open_time: LaxDatetime
    open_price: LaxDecimal
    sl: LaxDecimal | None = None
    tp: LaxDecimal | None = None
    profit: LaxDecimal


class PositionsIngestRequest(_Strict):
    account_login: str
    connector_instance_id: str
    ts: LaxDatetime
    positions: list[PositionIn]
    batch_sha256: str = Field(min_length=64, max_length=64)


class EquityIngestRequest(_Strict):
    account_login: str
    connector_instance_id: str
    ts: LaxDatetime
    equity: LaxDecimal
    balance: LaxDecimal
    margin_level: float | None = None
    free_margin: LaxDecimal | None = None
    batch_sha256: str = Field(min_length=64, max_length=64)


class HeartbeatIngestRequest(_Strict):
    connector_instance_id: str
    account_login: str
    latency_ms: int
    ts: LaxDatetime
    batch_sha256: str = Field(min_length=64, max_length=64)


class SignalIn(_Strict):
    signal_id: str
    symbol: str
    type: LaxTradeType
    volume: LaxDecimal
    entry_price: LaxDecimal
    sl: LaxDecimal | None = None
    tp: LaxDecimal | None = None
    ts: LaxDatetime


class SignalsIngestRequest(_Strict):
    account_login: str
    connector_instance_id: str
    magic: int
    signals: list[SignalIn]
    batch_sha256: str = Field(min_length=64, max_length=64)


class FillIn(_Strict):
    order_id: str
    symbol: str
    requested_price: LaxDecimal
    executed_price: LaxDecimal
    spread: LaxDecimal | None = None
    ts: LaxDatetime


class ExecutionIngestRequest(_Strict):
    account_login: str
    connector_instance_id: str
    magic: int
    fills: list[FillIn]
    batch_sha256: str = Field(min_length=64, max_length=64)


class EaStateIn(_Strict):
    magic: int
    ea_version: str
    mode: str
    autotrading: bool
    schedule_filter: dict[str, Any] | None = None
    news_windows: list[dict[str, Any]] | None = None
    # G10 (docs/backlog.md): opcional -- el conector/EA real no lo manda
    # todavia (mt5-connector/src/connector/protocol.py, sin cambios en
    # G10), no verificable sin hardware real (mismo patron que G4).
    sizing_pct: LaxDecimal | None = None


class EaStateIngestRequest(_Strict):
    account_login: str
    connector_instance_id: str
    eas: list[EaStateIn]
    batch_sha256: str = Field(min_length=64, max_length=64)


class IngestResponse(BaseModel):
    accepted: int
    duplicated: int
    batch_id: int
    server_time: datetime
