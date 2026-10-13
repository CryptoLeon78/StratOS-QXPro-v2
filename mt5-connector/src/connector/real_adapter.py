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

import logging
import ntpath
import subprocess
import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from connector.protocol import AccountInfoDTO, DealDTO, PositionDTO

logger = logging.getLogger(__name__)

_ORDER_TYPE_TO_STR = {0: "BUY", 1: "SELL"}
_DEAL_ENTRY_IN = 0
_DEAL_ENTRY_OUT = 1
# `MetaTrader5.last_error()` code 1 is RES_S_OK: a None result with this code
# means "nothing to return", not a failure (documented error-code table).
_RES_S_OK = 1


class Mt5UnavailableError(RuntimeError):
    """El terminal no responde ni tras reconectar.

    Se lanza en vez de devolver una lista vacía: con el terminal caído, un
    `positions_get()` vacío se enviaría como "no hay posiciones abiertas" y un
    `history_deals_get()` vacío haría avanzar la marca de agua de deals, perdiendo
    para siempre los cierres de ese intervalo (incidente 2026-09-28 → 2026-10-13).
    """


def _order_type_str(raw_type: int) -> str:
    return _ORDER_TYPE_TO_STR.get(raw_type, "BUY")


def _optional_decimal(value: float | None) -> Decimal | None:
    return None if not value else Decimal(str(value))


def _pair_deals_into_closed_trades(
    raw_deals: Iterable[Any],
    entry_lookup: Callable[[int], Any | None] | None = None,
) -> list[DealDTO]:
    """Empareja deals IN/OUT por `position_id`.

    Con sondeo incremental la entrada casi nunca cae en la misma ventana que la
    salida (la posición se abrió horas o días antes): `entry_lookup` la busca por
    `position_id`. Sin él, una salida sin su entrada se descarta.
    """
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
        if entry_deal is None and entry_lookup is not None:
            entry_deal = entry_lookup(position_id)
        if entry_deal is None:
            logger.warning(
                "deal de salida %s sin entrada localizable: no se envia", exit_deal.ticket
            )
            continue
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
                position_id=position_id,
            )
        )
    return trades


def _terminal_process_running(path: str) -> bool:
    """True si hay un `terminal64.exe` vivo con exactamente esa ruta.

    `mt5.initialize(path)` ARRANCA el terminal si no está abierto. En el VPS el
    conector corre como servicio (sesión 0): relanzarlo ahí abriría un terminal
    de cuenta real invisible, con sus EAs, cuando el operador lo hubiera cerrado
    a propósito. Por eso sólo se reconecta a un terminal que ya está corriendo.
    """
    image = ntpath.basename(path)
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"(Get-CimInstance Win32_Process -Filter \"Name='{image}'\").ExecutablePath",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    running = {line.strip().lower() for line in result.stdout.splitlines() if line.strip()}
    return path.strip().lower() in running


class AccountMismatchError(RuntimeError):
    """El terminal conectado tiene abierta otra cuenta que la del servicio."""


class RealMt5Client:
    def __init__(
        self,
        reconnect_min_interval_s: float = 0.0,
        is_terminal_running: Callable[[str], bool] = _terminal_process_running,
        expected_login: str | None = None,
    ) -> None:
        self._path: str | None = None
        self._expected_login = expected_login
        self._reconnect_min_interval_s = reconnect_min_interval_s
        self._is_terminal_running = is_terminal_running
        self._last_reconnect_at: float | None = None

    def initialize(self, path: str | None = None) -> bool:
        import MetaTrader5 as mt5

        self._path = path
        if path:
            # La API publica de MetaQuotes exige `path` como primer argumento
            # posicional. Como keyword puede caer en la seleccion automatica
            # del terminal, ambigua cuando el VPS tiene varias instalaciones.
            return bool(mt5.initialize(path))
        return bool(mt5.initialize())

    def _query(self, what: str, call: Callable[[Any], Any], allow_empty: bool) -> Any:
        """Ejecuta `call(mt5)`; si falla, reconecta una vez y reintenta.

        El paquete `MetaTrader5` no se recupera solo cuando el terminal se
        reinicia: la conexión IPC queda muerta y toda llamada devuelve None.
        `allow_empty` distingue "sin datos" (código RES_S_OK) de un fallo real.
        """
        import MetaTrader5 as mt5

        for attempt in (1, 2):
            result = call(mt5)
            if result is not None:
                return result
            code, description = mt5.last_error()
            if allow_empty and code == _RES_S_OK:
                return ()
            if attempt == 1:
                refused = self._reconnect_refusal()
                if refused is not None:
                    raise Mt5UnavailableError(
                        f"MT5 {what} sin respuesta ({code} {description}); {refused}"
                    )
                logger.warning(
                    "MT5 %s devolvio None (%s %s): se reconecta al terminal",
                    what,
                    code,
                    description,
                )
                self._last_reconnect_at = time.monotonic()
                mt5.shutdown()
                if not self.initialize(self._path):
                    code, description = mt5.last_error()
                    break
        raise Mt5UnavailableError(f"MT5 {what} sin respuesta tras reconectar: {code} {description}")

    def _reconnect_refusal(self) -> str | None:
        """Motivo para NO reconectar ahora, o None si se puede."""
        if not self._path:
            return "sin ruta de terminal configurada no se reconecta (podria elegir otro)"
        if (
            self._last_reconnect_at is not None
            and time.monotonic() - self._last_reconnect_at < self._reconnect_min_interval_s
        ):
            return "reconexion reciente; se reintenta en el siguiente ciclo"
        if not self._is_terminal_running(self._path):
            return f"el terminal {self._path} no esta abierto y el conector no lo arranca"
        return None

    def login(self, login: int, password: str, server: str) -> bool:
        import MetaTrader5 as mt5

        return bool(mt5.login(login, password=password, server=server))

    def _checked_account(self) -> Any:
        """`account_info` del terminal, exigiendo que sea la cuenta del servicio.

        El conector etiqueta todo lo que envía con su `account_login` configurado,
        no con la cuenta que tiene abierta el terminal: si la ruta apunta al
        terminal de otra cuenta (o el operador cambia de cuenta en él), los datos
        de una cuenta real entrarían como si fueran de la otra. Se comprueba en
        cada sondeo; ante discrepancia no se envía nada.
        """
        info = self._query("account_info", lambda mt5: mt5.account_info(), allow_empty=False)
        if self._expected_login is not None and str(info.login) != self._expected_login:
            raise AccountMismatchError(
                f"el terminal {self._path} tiene abierta la cuenta {info.login}, "
                f"no la {self._expected_login} del servicio: no se envia nada"
            )
        return info

    def account_info(self) -> AccountInfoDTO | None:
        info = self._checked_account()
        return AccountInfoDTO(
            balance=Decimal(str(info.balance)),
            equity=Decimal(str(info.equity)),
            margin_level=float(info.margin_level) if info.margin_level else None,
            margin_free=_optional_decimal(info.margin_free),
        )

    def positions_get(self) -> list[PositionDTO]:
        self._checked_account()
        positions = self._query("positions_get", lambda mt5: mt5.positions_get(), allow_empty=True)
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

    def _entry_deal_of(self, position_id: int) -> Any | None:
        deals = self._query(
            "history_deals_get(position)",
            lambda mt5: mt5.history_deals_get(position=position_id),
            allow_empty=True,
        )
        return next((d for d in deals if d.entry == _DEAL_ENTRY_IN), None)

    def history_deals_get(self, date_from: datetime, date_to: datetime) -> list[DealDTO]:
        self._checked_account()
        deals = self._query(
            "history_deals_get",
            lambda mt5: mt5.history_deals_get(date_from, date_to),
            allow_empty=True,
        )
        return _pair_deals_into_closed_trades(deals, self._entry_deal_of)

    def last_error(self) -> tuple[int, str]:
        import MetaTrader5 as mt5

        code, description = mt5.last_error()
        return (int(code), str(description))

    def shutdown(self) -> None:
        import MetaTrader5 as mt5

        mt5.shutdown()
