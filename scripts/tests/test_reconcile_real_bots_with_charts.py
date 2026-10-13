import json
from pathlib import Path

import pytest

from reconcile_real_bots_with_charts import (
    BotRow,
    InstalledEa,
    build_plan,
    load_installed,
    manifest_records,
)

BEPB = "4000055216"
JJTI = "4000059903"


def _ea(login: str, magic: int, name: str = "EA") -> InstalledEa:
    return InstalledEa(login, magic, f"{name}_MN{magic}", f"{name}_MN{magic}", "XAUUSD", "H1")


def _bot(bot_id: int, login: str, magic: int, phase: str = "F7") -> BotRow:
    return BotRow(bot_id, login, magic, f"bot{magic}", phase, "EXTERNAL_PRODUCTION")


def test_registers_installed_eas_and_retires_bots_without_an_installed_ea() -> None:
    installed = [_ea(BEPB, 12), _ea(BEPB, 26), _ea(JJTI, 1)]
    bots = [_bot(1, BEPB, 26), _bot(2, BEPB, 1), _bot(3, JJTI, 12)]

    plan = build_plan(installed, bots, {BEPB, JJTI})

    assert [(ea.account_login, ea.magic_number) for ea in plan.register] == [(BEPB, 12), (JJTI, 1)]
    assert sorted(bot.bot_id for bot in plan.retire) == [2, 3]
    assert [bot.bot_id for bot in plan.kept] == [1]


def test_never_retires_bots_already_retired_or_outside_the_given_accounts() -> None:
    bots = [
        _bot(1, BEPB, 5, phase="CEMENTERIO"),
        _bot(2, "3000108092", 7),
        BotRow(3, BEPB, 8, "analysis", "F3", "ANALYSIS"),
    ]

    plan = build_plan([], bots, {BEPB})

    assert plan.retire == []


def test_a_retired_bot_still_blocks_a_new_bot_with_the_same_magic_in_that_account() -> None:
    # (account_id, magic_number) es único: no se puede registrar otro bot encima.
    plan = build_plan([_ea(BEPB, 5)], [_bot(1, BEPB, 5, phase="CEMENTERIO")], {BEPB})

    assert plan.register == []


def _scan(tmp_path: Path, charts: list[dict[str, object]], **extra: object) -> Path:
    path = tmp_path / "scan.json"
    path.write_text(
        json.dumps({"account_login": BEPB, "charts": charts, **extra}), encoding="utf-8"
    )
    return path


def _chart(magic: int | None, period: str | None = "H1") -> dict[str, object]:
    return {
        "magic_number": magic,
        "comment_identity": f"X_MN{magic}",
        "ea_filename": f"X_MN{magic}",
        "symbol": "XAUUSD",
        "period": period,
    }


def test_load_installed_skips_charts_without_magic(tmp_path: Path) -> None:
    installed = load_installed([_scan(tmp_path, [_chart(12), _chart(None)])])

    assert [ea.magic_number for ea in installed] == [12]


@pytest.mark.parametrize(
    "charts,extra",
    [
        ([_chart(12, period=None)], {}),
        ([_chart(12), _chart(12)], {}),
        ([_chart(12)], {"profile_chart_id_conflicts": [{"mt5_chart_id": "1"}]}),
    ],
)
def test_load_installed_fails_closed_on_ambiguous_scans(
    tmp_path: Path, charts: list[dict[str, object]], extra: dict[str, object]
) -> None:
    with pytest.raises(SystemExit):
        load_installed([_scan(tmp_path, charts, **extra)])


def test_manifest_records_require_the_ex5_of_the_chart() -> None:
    ea = _ea(BEPB, 12, "XAUH1D1L__3.12.88")
    hashes = {
        BEPB: {
            "12": {
                "relative_path": r"StratOS_BEPB\XAUH1D1L__3.12.88_MN12\XAUH1D1L__3.12.88_MN12.ex5",
                "sha256": "a" * 64,
            }
        }
    }

    rows = manifest_records([ea], hashes)[BEPB]

    assert rows[0]["ea_sha256"] == "a" * 64
    assert rows[0]["status"] == "MATCHED_UNIQUE_VERSION"
    with pytest.raises(SystemExit):
        manifest_records([_ea(BEPB, 30)], hashes)
    other = {BEPB: {"12": {"relative_path": r"x\OTRO_MN12.ex5", "sha256": "b" * 64}}}
    with pytest.raises(SystemExit):
        manifest_records([ea], other)
