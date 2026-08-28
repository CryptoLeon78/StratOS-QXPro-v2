"""Adaptador real del paquete `MetaTrader5` (PyPI, Windows-only, requiere
terminal instalado y sesion iniciada). NO VERIFICADO contra un terminal
real en esta sesion (PARTE 0.2 regla 6, anti-alucinacion) -- implementado
contra la forma de la API publica documentada oficialmente (`initialize`,
`login`, `account_info`, `positions_get`, `history_deals_get`,
`last_error`, `shutdown`), sin poder confirmar tipos/campos exactos en
tiempo de ejecucion real.

Import perezoso (dentro de cada metodo, nunca a nivel de modulo): asi este
modulo se importa sin fallar en Linux CI, donde el paquete `MetaTrader5`
no esta instalado (ni puede estarlo -- Windows-only, no listado como
dependencia en pyproject.toml a proposito).

Nota de diseno IMPORTANTE, tambien sin verificar: en MT5 real, un trade
cerrado no es UNA fila de `history_deals_get` -- son DOS (entrada
`DEAL_ENTRY_IN=0` + salida `DEAL_ENTRY_OUT=1`), enlazadas por
`position_id`. `_pair_deals_into_closed_trades` las empareja para producir
el `DealDTO` "abre+cierra en una fila" que `Mt5ClientProtocol` espera
(mismo shape que `Trade` en core-engine, PARTE 5.2). Si el campo real
difiere (nombre, tipo, ausencia de `position_id` en alguna version del
paquete), esto fallara en el primer uso real contra un terminal de
verdad -- flag explicito, no una garantia."""

from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from connector.protocol import AccountInfoDTO, DealDTO, PositionDTO

_ORDER_TYPE_TO_STR = {0: "BUY", 1: "SELL"}
_DEAL_ENTRY_IN = 0
_DEAL_ENTRY_OUT = 1


def _order_type_str(raw_type: int) -> str:
    return _ORDER_TYPE_TO_STR.get(raw_type, "BUY")


def _optional_decimal(value: float | None) -> Decimal | None:
    return None if not value else Decimal(str(value))


def _pair_deals_into_closed_trades(raw_deals: Iterable[Any]) -> list[DealDTO]:
    entries: dict[int, Any] = {}
    exits: dict[int, Any] = {}
    for deal in raw_deals:
        if deal.entry == _DEAL_ENTRY_IN:
            entries[deal.position_id] = deal
        elif deal.entry == _DEAL_ENTRY_OUT:
            exits[deal.position_id] = deal

    trades: list[DealDTO] = []
    for position_id, exit_deal in exits.items():
        entry_deal = entries.get(position_id)
        if entry_deal is None:
            continue  # posicion abierta antes del rango consultado: sin par
        trades.append(
            DealDTO(
                ticket=exit_deal.ticket,
                symbol=exit_deal.symbol,
                type=_order_type_str(entry_deal.type),
                volume=Decimal(str(exit_deal.volume)),
                price_open=Decimal(str(entry_deal.price)),
                price_close=Decimal(str(exit_deal.price)),
                sl=_optional_decimal(getattr(exit_deal, "sl", None)),
                tp=_optional_decimal(getattr(exit_deal, "tp", None)),
                profit=Decimal(str(exit_deal.profit)),
                commission=Decimal(str(entry_deal.commission + exit_deal.commission)),
                swap=Decimal(str(exit_deal.swap)),
                magic=exit_deal.magic,
                time_open=datetime.fromtimestamp(entry_deal.time, tz=UTC),
                time_close=datetime.fromtimestamp(exit_deal.time, tz=UTC),
            )
        )
    return trades


class RealMt5Client:
    def initialize(self, path: str | None = None) -> bool:
        import MetaTrader5 as mt5

        if path:
            return bool(mt5.initialize(path=path))
        return bool(mt5.initialize())

    def login(self, login: int, password: str, server: str) -> bool:
        import MetaTrader5 as mt5

        return bool(mt5.login(login, password=password, server=server))

    def account_info(self) -> AccountInfoDTO | None:
        import MetaTrader5 as mt5

        info = mt5.account_info()
        if info is None:
            return None
        return AccountInfoDTO(
            balance=Decimal(str(info.balance)),
            equity=Decimal(str(info.equity)),
            margin_level=float(info.margin_level) if info.margin_level else None,
            margin_free=_optional_decimal(info.margin_free),
        )

    def positions_get(self) -> list[PositionDTO]:
        import MetaTrader5 as mt5

        positions = mt5.positions_get()
        if positions is None:
            return []
        return [
            PositionDTO(
                ticket=p.ticket,
                symbol=p.symbol,
                type=_order_type_str(p.type),
                volume=Decimal(str(p.volume)),
                price_open=Decimal(str(p.price_open)),
                sl=_optional_decimal(p.sl),
                tp=_optional_decimal(p.tp),
                profit=Decimal(str(p.profit)),
                magic=p.magic,
                time=datetime.fromtimestamp(p.time, tz=UTC),
            )
            for p in positions
        ]

    def history_deals_get(self, date_from: datetime, date_to: datetime) -> list[DealDTO]:
        import MetaTrader5 as mt5

        deals = mt5.history_deals_get(date_from, date_to)
        if deals is None:
            return []
        return _pair_deals_into_closed_trades(deals)

    def last_error(self) -> tuple[int, str]:
        import MetaTrader5 as mt5

        code, description = mt5.last_error()
        return (int(code), str(description))

    def shutdown(self) -> None:
        import MetaTrader5 as mt5

        mt5.shutdown()
