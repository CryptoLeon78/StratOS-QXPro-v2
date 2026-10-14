import json
from pathlib import Path

import pytest

from register_incubator_observed_bots import load_manifest

PROFILES = {"TREND", "MOMENTUM"}


def _record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "magic_number": 1000109,
        "name": "XTIH4L_2.2.27_MN1000109",
        "comment_identity": "XTIH4L_2.2.27_MN1000109",
        "symbol": "XTIUSD",
        "timeframe": "H4",
        "ea_relative_path": "XTIH4L_2.2.27_MN1000109.ex5",
        "ea_sha256": "a" * 64,
        "profile": "TREND",
        "capital_allocated_pct": "0.20",
        "risk_per_trade_pct": "0.200",
    }
    record.update(overrides)
    return record


def _manifest(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"account_login": "3000108092", "records": records}))
    return path


def test_loads_a_complete_manifest(tmp_path: Path) -> None:
    login, records = load_manifest(_manifest(tmp_path, [_record()]), PROFILES)

    assert login == "3000108092"
    assert records[0].magic_number == 1000109
    assert str(records[0].risk_per_trade_pct) == "0.200"


@pytest.mark.parametrize(
    "overrides",
    [
        {"profile": None},
        {"capital_allocated_pct": ""},
        {"ea_sha256": "xyz"},
        {"profile": "GRIDX"},
        {"ea_relative_path": r"otro\OTRO_MN1.ex5"},
    ],
)
def test_rejects_incomplete_or_inconsistent_records(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    with pytest.raises(SystemExit):
        load_manifest(_manifest(tmp_path, [_record(**overrides)]), PROFILES)


def test_rejects_duplicated_magics(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="duplicado"):
        load_manifest(_manifest(tmp_path, [_record(), _record()]), PROFILES)
