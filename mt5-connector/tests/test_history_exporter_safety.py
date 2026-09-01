from pathlib import Path

EXPORTER = Path(__file__).parents[1] / "mql5" / "StratOSHistoryExport.mq5"


def test_history_exporter_has_no_trading_functions() -> None:
    source = EXPORTER.read_text(encoding="utf-8")
    prohibited = ("OrderSend", "PositionClose", "OrderDelete", "trade.", "CTrade")

    assert "HistorySelect" in source
    assert "HistoryDealGet" in source
    assert not any(token.lower() in source.lower() for token in prohibited)
