from pathlib import Path

from classify_mql5_strategy import classify_source


def _source(rule: str) -> str:
    return "// Rule: Trading signals\n" + rule + "\n// Rule: Long entry\n"


def test_classifies_a_single_executable_signal_family(tmp_path: Path) -> None:
    source = tmp_path / "trend.mq5"
    source.write_text(_source("SqSuperTrend SqSuperTrend SqGannHiLo"), encoding="utf-8")

    result = classify_source(source)

    assert result["proposed_profile"] == "TREND"
    assert result["requires_operator_confirmation"] is True


def test_holds_an_ambiguous_rule_for_operator_review(tmp_path: Path) -> None:
    source = tmp_path / "mixed.mq5"
    source.write_text(_source("SqSuperTrend SqStochastic"), encoding="utf-8")

    assert classify_source(source)["proposed_profile"] == "UNCLASSIFIED"


def test_resolves_sqx_indicator_definitions_used_by_the_entry_rule(tmp_path: Path) -> None:
    source = tmp_path / "trend.mq5"
    source.write_text(
        '#define SUPERTREND_1 0 //iCustom(NULL,0, "SqSuperTrend", 1)\n'
        + _source("SUPERTREND_1"),
        encoding="utf-8",
    )

    assert classify_source(source)["proposed_profile"] == "TREND"
