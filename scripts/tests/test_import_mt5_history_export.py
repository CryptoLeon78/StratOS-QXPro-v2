from asyncio import run
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

import import_mt5_history_export
from import_mt5_history_export import parse_closed_positions


def test_history_importer_accepts_one_entry_one_exit(tmp_path: Path) -> None:
    source = tmp_path / "history.csv"
    source.write_text(
        "deal_ticket,position_id,time,magic,symbol,entry,type,volume,price,profit,commission,swap,reason\n"
        "1,99,2026.01.01 00:00:00,42,EURUSD,0,0,0.10,1.10000,0,0,0,0\n"
        "2,99,2026.01.02 00:00:00,42,EURUSD,1,0,0.10,1.11000,10,0,0,0\n",
        encoding="utf-8",
    )
    trades, withheld = parse_closed_positions(source, ZoneInfo("Europe/Helsinki"))

    assert len(trades) == 1
    assert trades[0].ticket_mt5 == 2
    assert trades[0].open_time.isoformat() == "2025-12-31T22:00:00+00:00"
    assert withheld == 0


def test_history_importer_preserves_large_mt5_magic(tmp_path: Path) -> None:
    source = tmp_path / "history.csv"
    source.write_text(
        "deal_ticket,position_id,time,magic,symbol,entry,type,volume,price,profit,commission,swap,reason\n"
        "1,99,2026.01.01 00:00:00,20260317480,EURUSD,0,0,0.10,1.10000,0,0,0,0\n"
        "2,99,2026.01.02 00:00:00,20260317480,EURUSD,1,0,0.10,1.11000,10,0,0,0\n",
        encoding="utf-8",
    )

    trades, withheld = parse_closed_positions(source, ZoneInfo("Europe/Helsinki"))

    assert len(trades) == 1
    assert trades[0].magic_number == 20260317480
    assert withheld == 0


def test_history_import_rejects_fixture_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        import_mt5_history_export,
        "get_settings",
        lambda: SimpleNamespace(deployment_profile="full"),
    )

    with pytest.raises(SystemExit, match="DEPLOYMENT_PROFILE=operational"):
        run(import_mt5_history_export.run(SimpleNamespace()))
