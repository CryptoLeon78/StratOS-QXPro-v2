from decimal import Decimal

import pytest

from core.services.mt5_tester_report import parse_sqx_vs_mt5_closed_deals


def test_parses_only_explicit_closed_deals() -> None:
    payload = (
        b"- List of deals ---------------------------------------------\n"
        b"2;2;AUDCAD;2017.12.04 04:00:00;2017.12.04 04:00:00;0;0.9;buy;in;0.2;-0.38;0;0;;0;0\n"
        b"3;2;AUDCAD;2017.12.08 20:40:00;2017.12.08 20:40:00;0;0.9;"
        b"sell;out;0.2;-0.38;3.01;-48.96;;0;0\n"
        b"- Summary ---------------------------------------------\n"
    )
    deals = parse_sqx_vs_mt5_closed_deals(payload)
    assert len(deals) == 1
    assert deals[0].net_pnl == Decimal("-46.33")


def test_accepts_mt5_utf16_bom_export() -> None:
    payload = (
        "- List of deals ---------------------------------------------\n"
        "3;2;AUDCAD;2017.12.08 20:40:00;2017.12.08 20:40:00;0;0.9;"
        "sell;out;0.2;-0.38;3.01;-48.96;;0;0\n"
    ).encode("utf-16")
    assert len(parse_sqx_vs_mt5_closed_deals(payload)) == 1


def test_rejects_rows_without_the_contract_shape() -> None:
    with pytest.raises(ValueError, match="fewer than 13"):
        parse_sqx_vs_mt5_closed_deals(b"- List of deals\n1;2;bad;out\n")
