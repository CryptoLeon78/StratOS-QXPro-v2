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
    trades, withheld, _ = parse_closed_positions(source, ZoneInfo("Europe/Helsinki"))

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

    trades, withheld, _ = parse_closed_positions(source, ZoneInfo("Europe/Helsinki"))

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


# --- Traducción de magics anteriores a la migración MN (P2.2) --------------------------
#
# La migración de identidad compacta cambió el magic de los EAs desplegados, así que los
# deals previos llevan el magic viejo. Sin traducir, una atribución por magic actual los
# deja huérfanos: en el export real de JJTI/BEPB la traducción triplica la cobertura
# (de 2,3 % a 10,3 % en BEPB y de 1,1 % a 8,2 % en JJTI).

_CSV_CABECERA = (
    "deal_ticket,position_id,time,magic,symbol,entry,type,volume,price,profit,commission,swap,reason\n"
)


def _csv_una_posicion(tmp_path: Path, magic: int) -> Path:
    source = tmp_path / f"history_{magic}.csv"
    source.write_text(
        _CSV_CABECERA
        + f"1,99,2026.01.01 00:00:00,{magic},EURUSD,0,0,0.10,1.10000,0,0,0,0\n"
        + f"2,99,2026.01.02 00:00:00,{magic},EURUSD,1,0,0.10,1.11000,10,0,0,0\n",
        encoding="utf-8",
    )
    return source


def test_legacy_magic_is_translated_to_the_current_identity(tmp_path: Path) -> None:
    source = _csv_una_posicion(tmp_path, 7786)
    mapa = {7786: {"magic_number": 1, "comment_identity": "XAUH1BUYSTOPeof_1.8.81_MN1"}}

    trades, withheld, traducciones = parse_closed_positions(
        source, ZoneInfo("Europe/Helsinki"), mapa
    )

    assert trades[0].magic_number == 1
    assert traducciones == {7786: 1}
    assert withheld == 0


def test_a_current_magic_is_left_untouched(tmp_path: Path) -> None:
    source = _csv_una_posicion(tmp_path, 1)
    mapa = {7786: {"magic_number": 1, "comment_identity": "XAUH1BUYSTOPeof_1.8.81_MN1"}}

    trades, _, traducciones = parse_closed_positions(source, ZoneInfo("Europe/Helsinki"), mapa)

    assert trades[0].magic_number == 1
    assert traducciones == {}


def test_an_unknown_magic_stays_orphan_instead_of_being_guessed(tmp_path: Path) -> None:
    """El 87-90 % del histórico real es de EAs ya retirados: se declaran huérfanos."""
    source = _csv_una_posicion(tmp_path, 987654)
    mapa = {7786: {"magic_number": 1, "comment_identity": "XAUH1BUYSTOPeof_1.8.81_MN1"}}

    trades, _, traducciones = parse_closed_positions(source, ZoneInfo("Europe/Helsinki"), mapa)

    assert trades[0].magic_number == 987654
    assert traducciones == {}


def test_without_a_registry_nothing_is_translated(tmp_path: Path) -> None:
    source = _csv_una_posicion(tmp_path, 7786)

    trades, _, traducciones = parse_closed_positions(source, ZoneInfo("Europe/Helsinki"))

    assert trades[0].magic_number == 7786
    assert traducciones == {}
