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


class _Parsed:
    symbol = "GBPJPY"
    timeframe = "H1"


def _valid_parser(monkeypatch) -> None:
    import core.services.sqx_baseline_parser as parser

    monkeypatch.setattr(parser, "parse_sqx144_baseline", lambda payload: _Parsed())


def _ea(path: Path, magic: int, body: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    source = f"// Backtested on GBPJPY / H1\ninput int MagicNumber = {magic};\n{body}"
    path.write_text(source, encoding="utf-8")


def _sqx(path: Path, content: bytes = b"sqx") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def test_stage_copies_of_one_ea_are_not_a_magic_collision(tmp_path: Path, monkeypatch) -> None:
    """Misma estrategia exportada una vez (FORWARD) y conservada como .sqx en MC/OOS: un EA."""
    _valid_parser(monkeypatch)
    for stage in ("FORWARD", "MC", "OOS"):
        _sqx(tmp_path / "P" / stage / "S 0.9.sqx", stage.encode())
    _ea(tmp_path / "P" / "FORWARD" / "S 0.9.mq5", 12368)

    rows = {Path(row["sqx_path"]).parent.name: row for row in build_inventory(tmp_path, "ANALYSIS")}

    assert rows["FORWARD"]["status"] == "STATIC_VALIDATED"
    assert {rows[s]["reason"] for s in ("MC", "OOS")} == {"SQX_STAGE_COPY_OF_PAIRED_EA"}
    assert {rows[s]["status"] for s in ("MC", "OOS")} == {"WITHHELD"}


def test_two_different_eas_with_the_same_magic_still_collide(tmp_path: Path, monkeypatch) -> None:
    _valid_parser(monkeypatch)
    _sqx(tmp_path / "A" / "FORWARD" / "S1.sqx")
    _ea(tmp_path / "A" / "FORWARD" / "S1.mq5", 11111, "// logic A")
    _sqx(tmp_path / "B" / "FORWARD" / "S2.sqx")
    _ea(tmp_path / "B" / "FORWARD" / "S2.mq5", 11111, "// logic B")

    rows = build_inventory(tmp_path, "ANALYSIS")

    assert {row["reason"] for row in rows} == {"DUPLICATE_MAGIC_NUMBER"}


def test_identical_copies_of_one_ea_are_one_ea(tmp_path: Path, monkeypatch) -> None:
    """Copias idénticas del .mq5 con otro nombre (FORWARD y Forward_finalistas): un solo EA."""
    _valid_parser(monkeypatch)
    _sqx(tmp_path / "P" / "FORWARD" / "S1.sqx")
    _ea(tmp_path / "P" / "FORWARD" / "S1.mq5", 777)
    _sqx(tmp_path / "P" / "Forward_finalistas" / "S1 copia.sqx")
    _ea(tmp_path / "P" / "Forward_finalistas" / "S1 copia.mq5", 777)

    rows = build_inventory(tmp_path, "ANALYSIS")

    assert {row["status"] for row in rows} == {"STATIC_VALIDATED"}


def test_stage_copy_without_a_sibling_sqx_keeps_one_deterministic_candidate(
    tmp_path: Path, monkeypatch
) -> None:
    """Sin .sqx junto al .mq5, una sola copia (la primera por ruta) queda como candidata."""
    _valid_parser(monkeypatch)
    _sqx(tmp_path / "P" / "MC" / "S.sqx")
    _sqx(tmp_path / "P" / "OOS" / "S.sqx")
    _ea(tmp_path / "P" / "EXPORT" / "S.mq5", 5)

    rows = sorted(build_inventory(tmp_path, "ANALYSIS"), key=lambda row: str(row["sqx_path"]))

    assert [row["status"] for row in rows] == ["STATIC_VALIDATED", "WITHHELD"]
    assert rows[1]["reason"] == "SQX_STAGE_COPY_OF_PAIRED_EA"
