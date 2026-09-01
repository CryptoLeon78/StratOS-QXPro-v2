from pathlib import Path

from import_external_ea_inventory_records import parse_records


ROOT = Path(__file__).resolve().parents[2]


def test_parses_operator_bepb_magic_records() -> None:
    records = parse_records(ROOT / "docs" / "registro_BEPB_MN_bots_real_mt5_vps.md", "BEPB")
    assert len(records) == 32
    assert records[0].magic_number == 7507
    assert sum(record.magic_number == 10827 for record in records) == 2


def test_parses_operator_jjti_magic_records() -> None:
    records = parse_records(ROOT / "docs" / "registro_JJTI_MN_bots_real_mt5_vps.md", "JJTI")
    assert len(records) == 24
    assert records[0].comment_identity == "EURUSDM15S_3.76.81_MN301"
    assert records[-1].magic_number == 200735
