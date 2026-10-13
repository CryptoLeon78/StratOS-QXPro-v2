"""`real_adapter.py`: NO VERIFICADO contra un terminal MT5 real (ver su
docstring). Aqui solo se prueba lo que es responsabilidad de este repo
verificar: (1) el modulo importa limpio en CI (Linux, sin `MetaTrader5`
instalado -- import perezoso, nunca a nivel de modulo); (2) el
emparejamiento IN/OUT de deals, que es logica Python pura y si se puede
probar sin el paquete real."""

import sys
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from connector.real_adapter import (
    Mt5UnavailableError,
    RealMt5Client,
    _pair_deals_into_closed_trades,
)


def _raw_deal(**kwargs: object) -> SimpleNamespace:
    defaults = {
        "ticket": 1,
        "position_id": 100,
        "symbol": "EURUSD",
        "type": 0,
        "entry": 0,
        "volume": 0.1,
        "price": 1.085,
        "profit": 0.0,
        "commission": 0.0,
        "swap": 0.0,
        "magic": 118231,
        "time": 1798700000,
        "sl": 0.0,
        "tp": 0.0,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestModuleImportsCleanly:
    def test_real_mt5_client_can_be_instantiated_without_the_real_package(self) -> None:
        # MetaTrader5 no esta instalado en este entorno (Linux CI) -- si el
        # import fuera a nivel de modulo, esto ya habria fallado al cargar
        # connector.real_adapter. Instanciar la clase NO debe tocar el
        # paquete todavia (import perezoso, dentro de cada metodo).
        client = RealMt5Client()
        assert client is not None

    @pytest.mark.parametrize(
        "call",
        [
            lambda c: c.initialize(),
            lambda c: c.login(100231, "pw", "Darwinex-Live"),
            lambda c: c.account_info(),
            lambda c: c.positions_get(),
            lambda c: c.history_deals_get(datetime(2026, 1, 1, tzinfo=UTC), datetime.now(UTC)),
            lambda c: c.last_error(),
            lambda c: c.shutdown(),
        ],
    )
    def test_every_method_fails_lazily_not_at_import_time(
        self, call: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # las 7 confirman que ninguna se salto el import perezoso: si UNA
        # importara MetaTrader5 a nivel de modulo, la clase entera fallaria
        # al cargar (verificado arriba), no solo esa llamada.
        # El paquete se bloquea a proposito: en un Windows con MetaTrader5
        # instalado este test llamaba de verdad a initialize() sin ruta y a
        # login() contra el terminal abierto (incidente 2026-10-13, cuenta real).
        monkeypatch.setitem(sys.modules, "MetaTrader5", None)
        client = RealMt5Client()
        with pytest.raises(ModuleNotFoundError):
            call(client)  # type: ignore[operator]


class TestInitializePropagatesTerminalPath:
    """G11: con 2+ terminales MT5 instalados en la misma maquina,
    `mt5.initialize()` sin `path` es ambiguo (se conecta a "la instancia que
    encuentre"). `RealMt5Client.initialize(path=...)` debe pasar ese `path`
    como primer argumento posicional al paquete real. Se verifica inyectando
    un modulo `MetaTrader5`
    falso en `sys.modules` (el paquete real no esta instalado aqui, mismo
    truco que hace falta para probar cualquier import perezoso sin el
    paquete Windows-only presente)."""

    def test_path_is_forwarded_to_the_real_package(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[object, ...]] = []
        fake_mt5 = SimpleNamespace(initialize=lambda *args: calls.append(args) or True)
        monkeypatch.setitem(sys.modules, "MetaTrader5", fake_mt5)

        result = RealMt5Client().initialize(path=r"C:\Program Files\MetaTrader 5\terminal64.exe")

        assert result is True
        assert calls == [(r"C:\Program Files\MetaTrader 5\terminal64.exe",)]

    def test_no_path_calls_initialize_without_arguments(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[tuple[object, ...]] = []
        fake_mt5 = SimpleNamespace(initialize=lambda *a, **kw: calls.append((a, kw)) or True)
        monkeypatch.setitem(sys.modules, "MetaTrader5", fake_mt5)

        result = RealMt5Client().initialize()

        assert result is True
        assert calls == [((), {})]


class TestPairDealsIntoClosedTrades:
    def test_matched_in_and_out_produce_one_deal_dto(self) -> None:
        entry = _raw_deal(entry=0, price=1.08000, time=1798700000, commission=-0.20, type=0)
        exit_ = _raw_deal(
            ticket=2,
            entry=1,
            price=1.08500,
            time=1798703600,
            profit=5.0,
            commission=-0.20,
            swap=-0.05,
            sl=1.07500,
            tp=1.09000,
        )
        trades = _pair_deals_into_closed_trades([entry, exit_])
        assert len(trades) == 1
        trade = trades[0]
        assert trade.ticket == 2
        assert trade.type == "BUY"
        assert str(trade.price_open) == "1.08"
        assert str(trade.price_close) == "1.085"
        assert str(trade.commission) == "-0.4"
        assert trade.sl is not None and str(trade.sl) == "1.075"
        assert trade.time_open == datetime.fromtimestamp(1798700000, tz=UTC)
        assert trade.time_close == datetime.fromtimestamp(1798703600, tz=UTC)

    def test_unmatched_exit_without_entry_is_skipped(self) -> None:
        exit_only = _raw_deal(entry=1, position_id=999)
        trades = _pair_deals_into_closed_trades([exit_only])
        assert trades == []

    def test_entry_only_position_still_open_produces_no_trade(self) -> None:
        entry_only = _raw_deal(entry=0, position_id=200)
        trades = _pair_deals_into_closed_trades([entry_only])
        assert trades == []

    def test_sell_type_is_mapped(self) -> None:
        entry = _raw_deal(entry=0, type=1)
        exit_ = _raw_deal(entry=1, ticket=2)
        trades = _pair_deals_into_closed_trades([entry, exit_])
        assert trades[0].type == "SELL"

    def test_zero_sl_tp_are_treated_as_absent(self) -> None:
        entry = _raw_deal(entry=0)
        exit_ = _raw_deal(entry=1, ticket=2, sl=0.0, tp=0.0)
        trades = _pair_deals_into_closed_trades([entry, exit_])
        assert trades[0].sl is None
        assert trades[0].tp is None


class _FakeMt5:
    """Módulo `MetaTrader5` falso: cada llamada consume la siguiente respuesta."""

    def __init__(self, **responses: list[object]) -> None:
        self.responses = responses
        self.calls: list[str] = []
        self.error: tuple[int, str] = (-10004, "No IPC connection")

    def _next(self, name: str) -> object:
        self.calls.append(name)
        return self.responses[name].pop(0)

    def initialize(self, *args: object) -> bool:
        self.calls.append("initialize")
        return True

    def shutdown(self) -> None:
        self.calls.append("shutdown")

    def last_error(self) -> tuple[int, str]:
        return self.error

    def positions_get(self) -> object:
        return self._next("positions_get")

    def account_info(self) -> object:
        return self._next("account_info")

    def history_deals_get(self, *args: object, **kwargs: object) -> object:
        return self._next("history_deals_get")


_PATH = r"C:\Program Files\Darwinex MetaTrader 5 - BEPB\terminal64.exe"


def _client(
    monkeypatch: pytest.MonkeyPatch, fake: _FakeMt5, running: bool = True, interval: float = 0.0
) -> RealMt5Client:
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
    client = RealMt5Client(reconnect_min_interval_s=interval, is_terminal_running=lambda _: running)
    client.initialize(path=_PATH)
    fake.calls.clear()
    return client


class TestLostTerminalConnection:
    """Incidente 2026-09-28: tras reiniciarse el terminal, el IPC quedó muerto y
    el conector envió 15 días de posiciones vacías y ningún equity ni cierre."""

    def test_reconnects_and_retries_when_the_terminal_stops_answering(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeMt5(positions_get=[None, ()])
        client = _client(monkeypatch, fake)

        assert client.positions_get() == []
        assert fake.calls == ["positions_get", "shutdown", "initialize", "positions_get"]

    def test_empty_result_with_success_code_is_not_a_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeMt5(positions_get=[None])
        fake.error = (1, "Success")
        client = _client(monkeypatch, fake)

        assert client.positions_get() == []
        assert "initialize" not in fake.calls

    def test_never_reports_an_empty_snapshot_while_the_terminal_is_dead(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeMt5(positions_get=[None, None])
        client = _client(monkeypatch, fake)

        with pytest.raises(Mt5UnavailableError):
            client.positions_get()

    def test_account_info_none_raises_instead_of_silently_skipping(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeMt5(account_info=[None, None])
        fake.error = (1, "Success")
        client = _client(monkeypatch, fake)

        with pytest.raises(Mt5UnavailableError):
            client.account_info()

    def test_does_not_launch_a_terminal_that_is_not_running(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeMt5(positions_get=[None])
        client = _client(monkeypatch, fake, running=False)

        with pytest.raises(Mt5UnavailableError, match="no lo arranca"):
            client.positions_get()
        assert "initialize" not in fake.calls

    def test_never_reconnects_without_an_explicit_terminal_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = _FakeMt5(positions_get=[None])
        monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
        client = RealMt5Client(is_terminal_running=lambda _: True)
        client.initialize()
        fake.calls.clear()

        with pytest.raises(Mt5UnavailableError, match="sin ruta"):
            client.positions_get()
        assert "initialize" not in fake.calls

    def test_reconnection_is_throttled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = _FakeMt5(positions_get=[None, None, None])
        client = _client(monkeypatch, fake, interval=3600.0)

        with pytest.raises(Mt5UnavailableError):
            client.positions_get()
        with pytest.raises(Mt5UnavailableError, match="reconexion reciente"):
            client.positions_get()
        assert fake.calls.count("initialize") == 1


class TestClosedTradeEntryLookup:
    def test_exit_whose_entry_is_outside_the_window_is_paired_by_position(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        entry = _raw_deal(entry=0, ticket=10, position_id=555, price=1.08, time=1798600000)
        exit_ = _raw_deal(entry=1, ticket=11, position_id=555, price=1.09, time=1798700000)
        fake = _FakeMt5(history_deals_get=[(exit_,), (entry, exit_)])
        client = _client(monkeypatch, fake)

        trades = client.history_deals_get(datetime(2026, 1, 1, tzinfo=UTC), datetime.now(UTC))

        assert len(trades) == 1
        assert trades[0].ticket == 11
        assert trades[0].position_id == 555
        assert trades[0].time_open == datetime.fromtimestamp(1798600000, tz=UTC)

    def test_pairing_keeps_the_position_id(self) -> None:
        entry = _raw_deal(entry=0, position_id=321)
        exit_ = _raw_deal(entry=1, ticket=2, position_id=321)

        assert _pair_deals_into_closed_trades([entry, exit_])[0].position_id == 321
