"""G10 (docs/backlog.md): `import_instrument_specs.py` lee `INSTRUMENTS` de
`user/data/data.db` (SQLite real de SQX). Aqui se prueba `_read_darwinex_specs`
contra un SQLite temporal con el mismo esquema minimo -- sin depender del
fichero real (no existe en CI) y sin tocar Postgres (esa parte, el UPSERT
real, se verifico a mano contra infraestructura real, ver ASSUMPTIONS G10)."""

import sqlite3
from decimal import Decimal
from pathlib import Path

from import_instrument_specs import _ALIAS, _read_darwinex_specs


def _make_data_db(tmp_path: Path, rows: list[tuple[str, float | None, float | None]]) -> Path:
    db = tmp_path / "data.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE INSTRUMENTS (INSTRUMENT TEXT, TICKSIZE REAL, POINTVALUE REAL)")
    con.executemany("INSERT INTO INSTRUMENTS VALUES (?, ?, ?)", rows)
    con.commit()
    con.close()
    return db


def test_strips_darwinex_suffix(tmp_path: Path) -> None:
    db = _make_data_db(tmp_path, [("EURUSD_darwinex", 0.0001, 100000.0)])
    specs = _read_darwinex_specs(db)
    assert specs == {"EURUSD": (Decimal("0.0001"), Decimal("100000.0"))}


def test_ignores_instruments_from_other_brokers(tmp_path: Path) -> None:
    db = _make_data_db(
        tmp_path,
        [
            ("EURUSD_darwinex", 0.0001, 100000.0),
            ("EURUSD_roboforex", 0.0001, 100000.0),
            ("EURUSD_ftmo", 0.0001, 100000.0),
        ],
    )
    specs = _read_darwinex_specs(db)
    assert list(specs.keys()) == ["EURUSD"]


def test_skips_rows_with_null_ticksize_or_pointvalue(tmp_path: Path) -> None:
    db = _make_data_db(
        tmp_path,
        [
            ("EURUSD_darwinex", None, 100000.0),
            ("GBPUSD_darwinex", 0.0001, None),
            ("XAUUSD_darwinex", 0.01, 100.0),
        ],
    )
    specs = _read_darwinex_specs(db)
    assert list(specs.keys()) == ["XAUUSD"]


def test_applies_known_symbol_aliases(tmp_path: Path) -> None:
    # Los 3 casos reales verificados a mano (ASSUMPTIONS G10) contra
    # SQX_vs_MT5_Panel/sqx_mt5_config.py::DATA -- StratOS los siembra bajo
    # un nombre, SQX los define bajo otro.
    db = _make_data_db(
        tmp_path,
        [
            ("SP500_darwinex", 0.1, 1.0),
            ("WS30_darwinex", 1.0, 1.0),
            ("XTIUSD_darwinex", 0.01, 10.0),
        ],
    )
    specs = _read_darwinex_specs(db)
    assert set(specs.keys()) == {"SPX500", "US30", "USOIL"}


def test_alias_map_has_no_duplicate_targets() -> None:
    # Si dos simbolos de StratOS mapearan al mismo INSTRUMENT de SQX, el
    # segundo pisaria al primero en el dict invertido -- un bug silencioso.
    targets = list(_ALIAS.values())
    assert len(targets) == len(set(targets))
