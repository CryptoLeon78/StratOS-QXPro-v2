"""G11: `_parse_args` es la logica pura (validacion de argumentos) de
`register_real_account_bot.py` -- el INSERT real contra Postgres se
verifica a mano contra infraestructura real, mismo precedente que
`import_instrument_specs.py`/`backfill_r_multiple.py` de G10."""

import pytest

from register_real_account_bot import _parse_args

_ACCOUNT_ARGS = [
    "--login", "3000080873",
    "--broker", "Darwinex",
    "--server", "Darwinex-Demo",
    "--currency", "USD",
    "--name", "Darwinex Demo Incubacion",
    "--demo",
]

_BOT_ARGS = [
    "--magic", "300000024",
    "--bot-name", "XAUUSD H4 BreakoutStop",
    "--market", "XAUUSD",
    "--timeframe", "H4",
    "--profile", "TREND",
    "--capital-pct", "10",
    "--risk-pct", "0.5",
]


def test_account_only_parses_cleanly() -> None:
    args = _parse_args(_ACCOUNT_ARGS)
    assert args.login == "3000080873"
    assert args.is_demo is True
    assert args.magic is None


def test_account_plus_bot_parses_cleanly() -> None:
    args = _parse_args([*_ACCOUNT_ARGS, *_BOT_ARGS])
    assert args.magic == 300000024
    assert args.role == "CHAMPION"  # default
    assert args.pipeline_phase == "F1"  # default


def test_partial_bot_fields_is_rejected() -> None:
    with pytest.raises(SystemExit):
        _parse_args([*_ACCOUNT_ARGS, "--magic", "300000024"])  # falta bot-name/market/...


def test_magic_without_capital_or_risk_pct_is_rejected() -> None:
    incomplete = [
        "--magic", "300000024",
        "--bot-name", "X",
        "--market", "XAUUSD",
        "--timeframe", "H4",
        "--profile", "TREND",
    ]
    with pytest.raises(SystemExit):
        _parse_args([*_ACCOUNT_ARGS, *incomplete])


def test_real_flag_sets_is_demo_false() -> None:
    real_args = [a if a != "--demo" else "--real" for a in _ACCOUNT_ARGS]
    args = _parse_args(real_args)
    assert args.is_demo is False
