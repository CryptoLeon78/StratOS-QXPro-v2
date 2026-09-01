import zipfile
from pathlib import Path

from refresh_live_backtest_queue_sources import refresh_entry


def _sqx(path: Path, date_from: str = "2018.01.01", date_to: str = "2026.08.28") -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("lastSettings.xml", f'<Setup dateFrom="{date_from}" dateTo="{date_to}" />')


def test_refresh_resolves_renamed_files_but_keeps_deployed_magic(tmp_path: Path) -> None:
    root = tmp_path / "sources"
    folder = root / "DAXM30_4.20.23_MN35"
    folder.mkdir(parents=True)
    _sqx(folder / "DAXM30_4.20.23_MN35.sqx")
    (folder / "DAXM30_4.20.23_MN35.mq5").write_text("// source", encoding="utf-8")
    assignment = {
        "magic_number": 35,
        "comment_identity": "DAXM30_4.20.23_MN35",
        "legacy_magic_numbers": [10826],
        "evidence": {"deployments": [{"account_login": "1"}]},
    }
    entry = {"account_login": "1", "magic_number": 10826, "status": "READY_FOR_TICK_BACKTEST"}

    refreshed = refresh_entry(entry, [assignment], root, "2018-01-01", "2026-08-28")

    assert refreshed["magic_number"] == 10826
    assert refreshed["planned_magic_number"] == 35
    assert refreshed["planned_comment_identity"] == "DAXM30_4.20.23_MN35"
    assert refreshed["status"] == "READY_FOR_TICK_BACKTEST"


def test_refresh_withholds_an_unaligned_retest_window(tmp_path: Path) -> None:
    root = tmp_path / "sources"
    folder = root / "DAXM30_4.20.23_MN35"
    folder.mkdir(parents=True)
    _sqx(folder / "DAXM30_4.20.23_MN35.sqx", date_to="2026.08.27")
    (folder / "DAXM30_4.20.23_MN35.mq5").write_text("// source", encoding="utf-8")
    assignment = {
        "magic_number": 35,
        "comment_identity": "DAXM30_4.20.23_MN35",
        "legacy_magic_numbers": [10826],
        "evidence": {"deployments": [{"account_login": "1"}]},
    }
    entry = {"account_login": "1", "magic_number": 10826, "status": "READY_FOR_TICK_BACKTEST"}

    refreshed = refresh_entry(entry, [assignment], root, "2018-01-01", "2026-08-28")

    assert refreshed["status"] == "WITHHELD_SOURCE_WINDOW"
