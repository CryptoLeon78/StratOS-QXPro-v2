from pathlib import Path
from zipfile import ZipFile

from operational_inventory import build_inventory


def test_inventory_withholds_unpaired_mql5(tmp_path: Path) -> None:
    (tmp_path / "candidate.sqx").write_bytes(b"sqx")
    (tmp_path / "orphan.mq5").write_text("input int MagicNumber = 42;", encoding="utf-8")

    rows = build_inventory(tmp_path, "ANALYSIS")

    assert len(rows) == 2
    assert {row["status"] for row in rows} == {"WITHHELD"}
    assert {row["reason"] for row in rows} == {"MQL5_PAIR_NOT_UNIQUE_OR_MISSING", "SQX_PAIR_MISSING"}


def test_inventory_persists_declared_source_root(tmp_path: Path) -> None:
    (tmp_path / "candidate.sqx").write_bytes(b"sqx")

    rows = build_inventory(tmp_path, "ANALYSIS", source_root=r"C:\private\analysis")

    assert rows[0]["source_root"] == r"C:\private\analysis"


def test_inventory_requires_sqx_mql5_symbol_and_timeframe_identity(tmp_path: Path) -> None:
    sqx_path = tmp_path / "candidate.sqx"
    with ZipFile(sqx_path, "w") as archive:
        archive.writestr("orders.bin", b"invalid")
        archive.writestr("strategy_Portfolio.xml", '<Strategy AppVersion="SQX Build 144.1"/>')
        archive.writestr(
            "lastSettings.xml",
            '<Chart symbol="EURUSD" timeframe="H1"/><Setup dateFrom="2018.01.01" dateTo="2026.01.01"/><InitialCapital>10000</InitialCapital>',
        )
    (tmp_path / "candidate.mq5").write_text(
        "// Backtested on GBPUSD / H1\ninput int MagicNumber = 42;", encoding="utf-8"
    )

    rows = build_inventory(tmp_path, "ANALYSIS")

    assert rows[0]["status"] == "WITHHELD"
