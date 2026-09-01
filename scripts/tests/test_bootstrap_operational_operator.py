from asyncio import run
from types import SimpleNamespace

import pytest

import bootstrap_operational_operator


def test_bootstrap_operator_rejects_non_operational_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bootstrap_operational_operator,
        "get_settings",
        lambda: SimpleNamespace(deployment_profile="full"),
    )

    with pytest.raises(SystemExit, match="DEPLOYMENT_PROFILE=operational"):
        run(bootstrap_operational_operator.bootstrap())
