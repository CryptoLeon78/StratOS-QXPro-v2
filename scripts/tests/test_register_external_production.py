import sys
from asyncio import run
from types import SimpleNamespace

import pytest

import register_external_production
from register_external_production import _args, _validate_internal_contract


def test_external_production_cli_allows_observation_without_internal_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "register_external_production.py",
            "--login", "1", "--broker", "broker", "--server", "server", "--currency", "EUR",
            "--account-name", "JJTI", "--magic", "10", "--bot-name", "bot", "--market", "EURUSD",
            "--timeframe", "H1",
        ],
    )
    args = _args()
    assert args.magic == 10
    assert args.profile is None
    assert args.capital_pct is None
    assert args.risk_pct is None
    assert args.sqx is None
    assert _validate_internal_contract(args) is False


def test_external_production_cli_accepts_complete_declared_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "register_external_production.py",
            "--login", "1", "--broker", "broker", "--server", "server", "--currency", "EUR",
            "--account-name", "JJTI", "--magic", "10", "--bot-name", "bot", "--market", "EURUSD",
            "--timeframe", "H1", "--profile", "TREND", "--capital-pct", "10", "--risk-pct", "0.2",
        ],
    )
    args = _args()
    assert args.profile == "TREND"
    assert args.capital_pct == 10
    assert _validate_internal_contract(args) is True


def test_external_production_rejects_partial_internal_contract() -> None:
    args = SimpleNamespace(profile="TREND", capital_pct=None, risk_pct=None)

    with pytest.raises(SystemExit, match="se declaran juntos"):
        _validate_internal_contract(args)


def test_external_production_registration_rejects_fixture_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        register_external_production,
        "get_settings",
        lambda: SimpleNamespace(deployment_profile="full"),
    )

    with pytest.raises(SystemExit, match="DEPLOYMENT_PROFILE=operational"):
        run(register_external_production.register(SimpleNamespace()))
