"""Regresiones puras para los datos deterministas del fixture G11."""

from datetime import UTC, datetime
from decimal import Decimal

from seed_lib.config import FULL_HISTORY_END, profile_for
from seed_lib.trades_history import SEED_PRICE_SPECS, seed_prices_for_symbol


def test_full_profile_ignores_execution_clock() -> None:
    january = profile_for("full", datetime(2026, 1, 1, tzinfo=UTC))
    december = profile_for("full", datetime(2030, 12, 31, tzinfo=UTC))

    assert january.history_end == FULL_HISTORY_END
    assert december.history_end == FULL_HISTORY_END


def test_index_seed_prices_have_realistic_order_of_magnitude() -> None:
    expected = {
        "GDAXI": Decimal("18000.0"),
        "NDX": Decimal("18000.0"),
        "SPX500": Decimal("5000.0"),
        "US30": Decimal("38000.0"),
    }

    for symbol, reference in expected.items():
        open_price, sl, tp = seed_prices_for_symbol(symbol)
        assert open_price == reference
        assert sl < open_price < tp
        assert (tp - open_price) == (open_price - sl)


def test_every_seed_market_has_a_price_spec() -> None:
    expected_markets = {
        "EURUSD",
        "GBPUSD",
        "AUDUSD",
        "USDJPY",
        "XAUUSD",
        "XAGUSD",
        "GDAXI",
        "NDX",
        "USTEC",
        "SPX500",
        "US30",
        "USOIL",
    }
    assert expected_markets <= set(SEED_PRICE_SPECS)
