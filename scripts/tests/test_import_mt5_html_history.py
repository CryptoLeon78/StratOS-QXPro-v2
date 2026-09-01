from pathlib import Path

from import_mt5_html_history import load_time_reference, parse_report


def test_html_history_reconciles_simple_position_without_magic(tmp_path: Path) -> None:
    report = tmp_path / "report.html"
    report.write_text(
        """<html><title>4000055216: Test - Report</title><table>
        <tr><th>Posiciones</th></tr><tr><th>header</th></tr>
        <tr><td>2026.01.01 10:00:00</td><td>99</td><td>EURUSD</td><td>buy</td><td class='hidden'>EA</td><td>0.10</td><td>1.1000</td><td>1.0900</td><td>1.1200</td><td>2026.01.02 10:00:00</td><td>1.1100</td><td>-2</td><td>0</td><td>8</td></tr>
        <tr><th>Transacciones</th></tr><tr><th>header</th></tr>
        <tr><td>2026.01.01 10:00:00</td><td>1</td><td>EURUSD</td><td>buy</td><td>in</td><td>0.10</td><td>1.1000</td><td>99</td><td></td><td>-1</td><td>1</td><td>0</td><td>0</td><td>0</td><td>EA</td></tr>
        <tr><td>2026.01.02 10:00:00</td><td>2</td><td>EURUSD</td><td>sell</td><td>out</td><td>0.10</td><td>1.1100</td><td>101</td><td></td><td>-1</td><td>1</td><td>0</td><td>8</td><td>0</td><td>EA</td></tr>
        </table></html>""",
        encoding="utf-16",
    )
    account, trades, withheld = parse_report(report, "UTC")
    assert account == "4000055216"
    assert len(trades) == 1
    assert trades[0].ticket_mt5 == 99
    assert trades[0].magic_number == 0
    assert not withheld


def test_time_reference_requires_sqx_and_iana_timezones(tmp_path: Path) -> None:
    reference = tmp_path / "time.json"
    reference.write_text(
        '{"broker_profile":"Darwinex","sqx_timezone":"EETUS","iana_timezone":"Europe/Helsinki","mt5_timestamp_semantics":"broker_server_wall_time"}',
        encoding="utf-8",
    )
    assert load_time_reference(reference)["iana_timezone"] == "Europe/Helsinki"
