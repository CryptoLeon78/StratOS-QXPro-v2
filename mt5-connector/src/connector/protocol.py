"""Forma de datos que expone el paquete `MetaTrader5` (PyPI, Windows-only,
requiere terminal instalado): `account_info()`, `positions_get()`,
`history_deals_get(date_from, date_to)`. Campos tomados de la API publica
documentada del paquete -- NO verificados contra un terminal MT5 real en
esta sesion (PARTE 0.2 regla 6, anti-alucinacion: declarar la incertidumbre
en vez de inventar con falsa confianza). `real_adapter.py` es el unico
punto de contacto real con el paquete; todo lo demas (poller, buffer,
sender) solo conoce este Protocol, nunca `MetaTrader5` directamente.

`Mt5ClientProtocol` se satisface estructuralmente (typing.Protocol): tanto
`RealMt5Client` (este paquete) como `SimulatedMt5Client`
(`stratos-mt5-simulator`) lo implementan sin heredar de nada -- solo hace
falta que los metodos coincidan en firma."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class AccountInfoDTO:
    balance: Decimal
    equity: Decimal
    margin_level: float | None
    margin_free: Decimal | None


@dataclass(frozen=True)
class PositionDTO:
    ticket: int
    symbol: str
    type: str  # "BUY" | "SELL"
    volume: Decimal
    price_open: Decimal
    sl: Decimal | None
    tp: Decimal | None
    profit: Decimal
    magic: int
    time: datetime


@dataclass(frozen=True)
class DealDTO:
    ticket: int
    symbol: str
    type: str
    volume: Decimal
    price_open: Decimal
    price_close: Decimal
    sl: Decimal | None
    tp: Decimal | None
    profit: Decimal
    commission: Decimal
    swap: Decimal
    magic: int
    time_open: datetime
    time_close: datetime


@runtime_checkable
class Mt5ClientProtocol(Protocol):
    """Superficie minima que `poller.py` necesita. `login`/`initialize`
    devuelven `bool` (exito/fallo) igual que el paquete real; no lanzan
    excepcion, el poller consulta `last_error()` tras un fallo."""

    def initialize(self) -> bool: ...
    def login(self, login: int, password: str, server: str) -> bool: ...
    def account_info(self) -> AccountInfoDTO | None: ...
    def positions_get(self) -> list[PositionDTO]: ...
    def history_deals_get(self, date_from: datetime, date_to: datetime) -> list[DealDTO]: ...
    def last_error(self) -> tuple[int, str]: ...
    def shutdown(self) -> None: ...
