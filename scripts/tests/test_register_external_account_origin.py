"""Elección explícita de procedencia al dar de alta una cuenta (P5.1).

`BROKER_REAL` y `BROKER_DEMO` no significan lo mismo: la primera se observa
estrictamente read-only y la segunda es la Incubadora, la única ruta con operaciones
futuras. Por eso la procedencia se declara, no se adivina — y `is_demo` se deriva de
ella para que no puedan discrepar.
"""

from __future__ import annotations

import argparse
import asyncio

import pytest

from core.db.enums import AccountDataOrigin
from register_external_account import parse_args, register


def _args(**kwargs: object) -> argparse.Namespace:
    base = {
        "login": "5055093171",
        "account_name": "INCUBADORA",
        "broker": "MetaQuotes Ltd.",
        "server": "MetaQuotes-Demo",
        "currency": "USD",
        "data_origin": AccountDataOrigin.BROKER_DEMO.value,
        "apply": False,
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_a_dry_run_declares_the_chosen_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "register_external_account.get_settings",
        lambda: argparse.Namespace(deployment_profile="operational"),
    )

    resultado = asyncio.run(register(_args()))

    assert "origin=BROKER_DEMO" in resultado


def test_real_stays_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quien no elija procedencia no acaba dando de alta una demo por descuido."""
    monkeypatch.setattr(
        "register_external_account.get_settings",
        lambda: argparse.Namespace(deployment_profile="operational"),
    )

    resultado = asyncio.run(register(_args(data_origin=AccountDataOrigin.BROKER_REAL.value)))

    assert "origin=BROKER_REAL" in resultado


def test_the_fixture_profile_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "register_external_account.get_settings",
        lambda: argparse.Namespace(deployment_profile="ci"),
    )

    with pytest.raises(RuntimeError, match="operational"):
        asyncio.run(register(_args()))


def test_a_bad_currency_is_rejected_before_touching_the_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "register_external_account.get_settings",
        lambda: argparse.Namespace(deployment_profile="operational"),
    )

    with pytest.raises(ValueError, match="ISO-4217"):
        asyncio.run(register(_args(currency="DOLARES")))


def test_the_cli_only_offers_the_two_observable_origins() -> None:
    """`FIXTURE` no es una procedencia que se pueda dar de alta: la produce el seed."""
    import sys

    argv = [
        "prog", "--login", "1", "--account-name", "X", "--broker", "B",
        "--server", "S", "--currency", "USD", "--data-origin", "FIXTURE",
    ]
    sys.argv = argv
    with pytest.raises(SystemExit):
        parse_args()
