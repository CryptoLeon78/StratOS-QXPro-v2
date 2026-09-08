from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "prepare_incubator_reporter_ea.py"
SPEC = importlib.util.spec_from_file_location("prepare_incubator_reporter_ea", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sample_source() -> str:
    return """#include <Trade/Trade.mqh>\ninput string CustomComment = \"original\";\ninput int MagicNumber = 295;\ninput bool LimitTimeRange = true;\ninput string SignalTimeRangeFrom = \"02:00\";\ninput string SignalTimeRangeTo = \"22:00\";\nint OnInit(){ return INIT_SUCCEEDED; }\n"""


def test_instruments_sqx_ea_without_changing_magic() -> None:
    result = MODULE.instrument_source(
        sample_source(), expected_magic=295, reporter_version="incubadora-v1.1",
        outbox_filename="stratos_incubadora_295.jsonl", operational_mode="REAL", sizing_pct=0.2,
        custom_comment="AUDCADH4L_FxML_3.33.81_MN295",
    )
    assert "STRATOS_INCUBATOR_REPORTER_V11" in result
    assert "MagicNumber = 295" in result
    assert "StratosReporterManagedOnInit" in result
    assert "StratosReporterManagedOnTradeTransaction" in result
    assert 'CustomComment = "AUDCADH4L_FxML_3.33.81_MN295"' in result
    assert "OrderSend(" not in result


def test_rejects_wrong_magic() -> None:
    try:
        MODULE.instrument_source(
            sample_source(), expected_magic=1, reporter_version="v", outbox_filename="stratos_1.jsonl",
            operational_mode="REAL", sizing_pct=0.2, custom_comment="comment",
        )
    except ValueError as exc:
        assert "MagicNumber" in str(exc)
    else:
        raise AssertionError("wrong magic must be rejected")
