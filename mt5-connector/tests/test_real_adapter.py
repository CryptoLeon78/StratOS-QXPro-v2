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

from connector.real_adapter import RealMt5Client, _pair_deals_into_closed_trades


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
    def test_every_method_fails_lazily_not_at_import_time(self, call: object) -> None:
        # las 7 confirman que ninguna se salto el import perezoso: si UNA
        # importara MetaTrader5 a nivel de modulo, la clase entera fallaria
        # al cargar (verificado arriba), no solo esa llamada.
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
