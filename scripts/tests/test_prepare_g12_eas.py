import argparse
import json
from pathlib import Path

from scripts.prepare_g12_eas import MARKER, instrument_source, prepare, reporter_header_is_compatible


def test_instrument_source_adds_reporter_without_order_api() -> None:
    source = """#include <Trade/Trade.mqh>\ninput int MagicNumber = 42;\ninput bool LimitTimeRange = true;\ninput string SignalTimeRangeFrom = \"01:00\";\ninput string SignalTimeRangeTo = \"02:00\";\ndouble mmMultiplier = 1.0;\nint OnInit()\n{\n return(INIT_SUCCEEDED);\n}\n"""

    instrumented = instrument_source(source, "g12-reporter-v1.1", 42)

    assert MARKER in instrumented
    assert "StratosReporterManagedOnInit" in instrumented
    assert "StratosReporterManagedOnTradeTransaction" in instrumented
    assert 'StratosReporterOutbox = "stratos_g12_42.jsonl"' in instrumented
    assert "OrderSend(" not in instrumented


def test_instrument_source_rejects_existing_transaction_handler() -> None:
    source = "#include <Trade/Trade.mqh>\nvoid OnTradeTransaction() {}\n"

    try:
        instrument_source(source, "g12-reporter-v1.1", 42)
    except ValueError as exc:
        assert "OnTradeTransaction" in str(exc)
    else:
        raise AssertionError("la doble instrumentación debe rechazarse")


def test_reporter_header_requires_only_read_only_v11_api() -> None:
    compatible = " ".join(
        [
            "StratosJsonEscape",
            "StratosAppendReporterEvent",
            "StratosReportEaState",
            "StratosReportFill",
            "StratosReportRejectedOrder",
        ]
    )

    assert reporter_header_is_compatible(compatible + " // OrderSend( no se usa")
    assert not reporter_header_is_compatible(compatible + " OrderSend(")


def test_reporter_adapter_formats_unsigned_deal_ticket_without_longtostring() -> None:
    adapter = (
        Path(__file__).parents[2]
        / "mt5-connector"
        / "mql5"
        / "StratosReporterAdapter_v11.mqh"
    ).read_text(encoding="utf-8")

    assert "LongToString" not in adapter
    assert 'StringFormat("%I64u",transaction.deal)' in adapter


def test_refresh_reporter_replaces_only_existing_adapter(tmp_path: Path) -> None:
    source = tmp_path / "candidate.mq5"
    source.write_text(
        "#include <Trade/Trade.mqh>\n"
        "input int MagicNumber = 42;\n"
        "input bool LimitTimeRange = true;\n"
        "input string SignalTimeRangeFrom = \"01:00\";\n"
        "input string SignalTimeRangeTo = \"02:00\";\n"
        "double mmMultiplier = 1.0;\n"
        "int OnInit()\n{\n return(INIT_SUCCEEDED);\n}\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "ea_required_version": "g12-reporter-v1.1",
                "candidates": [
                    {
                        "status": "READY",
                        "strategy_name": "candidate",
                        "mq5_path": str(source),
                        "magic_number": 42,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    terminal_root = tmp_path / "terminal"
    adapter_target = terminal_root / "MQL5" / "Include" / "StratOS" / "StratosReporterAdapter_v11.mqh"
    adapter_target.parent.mkdir(parents=True)
    adapter_target.write_text("old incompatible adapter", encoding="utf-8")
    reporter_root = Path(__file__).parents[2] / "mt5-connector" / "mql5"

    prepare(
        argparse.Namespace(
            manifest=manifest,
            terminal_data_root=terminal_root,
            reporter_source_root=reporter_root,
            report=tmp_path / "report.json",
            apply=True,
            resume=True,
            refresh_reporter=True,
        )
    )

    assert adapter_target.read_text(encoding="utf-8") == (
        reporter_root / "StratosReporterAdapter_v11.mqh"
    ).read_text(encoding="utf-8")
