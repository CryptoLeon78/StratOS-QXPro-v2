from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.bootstrap_g12_demo import _ready_candidates
from scripts.build_g12_manifest import _identity_mismatch, _select


def test_g12_config_declares_exactly_the_maintained_universe() -> None:
    config_path = Path(__file__).parents[2] / "config" / "g12_survivors.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    names = [candidate["strategy_name"] for candidate in config["candidates"]]

    assert len(names) == 16
    assert len(names) == len(set(names))
    assert config["ea_required_version"] == "g12-reporter-v1.1"
    assert all(candidate["darwinex_symbol"].endswith("_darwinex") for candidate in config["candidates"])


def test_g12_bootstrap_rejects_any_withheld_candidate() -> None:
    candidates = [{"strategy_name": f"bot-{index}", "status": "READY"} for index in range(15)]
    candidates.append({"strategy_name": "unverified", "status": "WITHHELD"})

    with pytest.raises(ValueError, match="retenidos"):
        _ready_candidates({"candidates": candidates})


def test_g12_bootstrap_only_allows_verified_subset_with_explicit_flag() -> None:
    candidates = [{"strategy_name": f"bot-{index}", "status": "READY"} for index in range(11)]
    candidates.extend(
        {"strategy_name": f"retained-{index}", "status": "WITHHELD"} for index in range(5)
    )

    ready = _ready_candidates({"candidates": candidates}, allow_withheld=True)

    assert [candidate["strategy_name"] for candidate in ready] == [f"bot-{index}" for index in range(11)]


def test_g12_bootstrap_requires_all_sixteen_ready_candidates() -> None:
    candidates = [{"strategy_name": f"bot-{index}", "status": "READY"} for index in range(15)]

    with pytest.raises(ValueError, match="se esperaban 16"):
        _ready_candidates({"candidates": candidates})


def test_artifact_selection_normalizes_windows_path_separator() -> None:
    preferred = Path("/eas/00_PORTFOLIOS/20072026/candidate.mq5")
    fallback = Path("/eas/000_StatOasis/candidate.mq5")

    assert _select([fallback, preferred], r"00_PORTFOLIOS\20072026") == preferred


def test_g12_manifest_rejects_a_sqx_symbol_or_timeframe_mismatch() -> None:
    candidate = {"darwinex_symbol": "EURUSD_darwinex", "timeframe": "H1"}

    assert _identity_mismatch(candidate, symbol="EURUSD_darwinex", timeframe="H1") is None
    assert "símbolo SQX no coincide" in _identity_mismatch(
        candidate, symbol="EURUSD", timeframe="H1"
    )
    assert "timeframe SQX no coincide" in _identity_mismatch(
        candidate, symbol="EURUSD_darwinex", timeframe="M15"
    )
