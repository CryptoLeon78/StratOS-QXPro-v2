"""G10 (docs/backlog.md): `r_multiple_for_trade` es la logica pura de
`backfill_r_multiple.py` (sin BBDD) -- la orquestacion real (SELECT/UPDATE
sobre Trade/InstrumentSpec) se verifico a mano contra Postgres local, mismo
precedente que `import_instrument_specs.py::import_instrument_specs`."""

from decimal import Decimal

from backfill_r_multiple import r_multiple_for_trade


def test_computes_r_multiple_with_profit_net_including_costs() -> None:
    # riesgo = |1.1000-1.0950|/0.0001*1*1 = 50; profit_net = 100-2-1 = 97
    r = r_multiple_for_trade(
        profit=Decimal("100"),
        commission=Decimal("-2"),
        swap=Decimal("-1"),
        entry=Decimal("1.1000"),
        sl=Decimal("1.0950"),
        volume=Decimal("1"),
        spec=(Decimal("1"), Decimal("0.0001")),
    )
    assert r == Decimal("1.94")


def test_no_sl_returns_none() -> None:
    r = r_multiple_for_trade(
        profit=Decimal("100"),
        commission=Decimal("0"),
        swap=Decimal("0"),
        entry=Decimal("1.1000"),
        sl=None,
        volume=Decimal("1"),
        spec=(Decimal("1"), Decimal("0.0001")),
    )
    assert r is None


def test_no_spec_returns_none() -> None:
    r = r_multiple_for_trade(
        profit=Decimal("100"),
        commission=Decimal("0"),
        swap=Decimal("0"),
        entry=Decimal("1.1000"),
        sl=Decimal("1.0950"),
        volume=Decimal("1"),
        spec=None,
    )
    assert r is None


def test_loss_gives_negative_r() -> None:
    r = r_multiple_for_trade(
        profit=Decimal("-75"),
        commission=Decimal("0"),
        swap=Decimal("0"),
        entry=Decimal("1.1000"),
        sl=Decimal("1.0950"),
        volume=Decimal("1"),
        spec=(Decimal("1"), Decimal("0.0001")),
    )
    assert r == Decimal("-1.5")
