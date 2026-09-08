from pathlib import Path

from classify_mql5_strategy import classify_source


def _source(rule: str) -> str:
    return "// Rule: Trading signals\n" + rule + "\n// Rule: Long entry\n"


def test_classifies_a_single_executable_signal_family(tmp_path: Path) -> None:
    source = tmp_path / "trend.mq5"
    source.write_text(_source("SqSuperTrend SqSuperTrend SqGannHiLo"), encoding="utf-8")

    result = classify_source(source)

    assert result["proposed_profile"] == "TREND"
    assert result["requires_operator_confirmation"] is False


def test_holds_an_ambiguous_rule_for_operator_review(tmp_path: Path) -> None:
    source = tmp_path / "mixed.mq5"
    source.write_text(_source("SqSuperTrend SqStochastic"), encoding="utf-8")

    assert classify_source(source)["proposed_profile"] == "UNCLASSIFIED"


def test_resolves_sqx_indicator_definitions_used_by_the_entry_rule(tmp_path: Path) -> None:
    source = tmp_path / "trend.mq5"
    source.write_text(
        '#define SUPERTREND_1 0 //iCustom(NULL,0, "SqSuperTrend", 1)\n' + _source("SUPERTREND_1"),
        encoding="utf-8",
    )

    assert classify_source(source)["proposed_profile"] == "TREND"


def test_classifies_higher_timeframe_price_continuation_as_trend(tmp_path: Path) -> None:
    source = tmp_path / "trend_price.mq5"
    source.write_text(
        _source(
            'sqMonthly(NULL,0, "Close", 2) > sqMonthly(NULL,0, "Close", 1) '
            '&& sqWeekly(NULL,0, "Open", 1) > 0'
        ),
        encoding="utf-8",
    )

    assert classify_source(source)["proposed_profile"] == "TREND"


def test_classifies_low_percentile_recovery_as_mean_reversion(tmp_path: Path) -> None:
    source = tmp_path / "mean_reversion.mq5"
    source.write_text(
        _source(
            'indyCrossesBelow("sqLow(NULL,0,2)", "sqOpen(NULL,0,1)", 0,0,0,0) && '
            'sqIsLowerPercentile("sqDaily(NULL,0,\\"Low\\",5)",10.0,100,2)'
        ),
        encoding="utf-8",
    )

    assert classify_source(source)["proposed_profile"] == "MEAN_REVERSION"


def test_classifies_regression_high_percentile_as_momentum(tmp_path: Path) -> None:
    source = tmp_path / "momentum.mq5"
    source.write_text(
        _source('sqIsGreaterPercentile("sqGetIndicatorValue(LINEARREGRESSION_1,0,1)",95.0,800,2)'),
        encoding="utf-8",
    )

    assert classify_source(source)["proposed_profile"] == "MOMENTUM"


def test_classifies_low_price_recovery_cross_as_mean_reversion(tmp_path: Path) -> None:
    source = tmp_path / "mean_reversion_cross.mq5"
    source.write_text(
        _source('indyCrossesAbove("sqOpen(NULL,0,1)", "sqLow(NULL,0,2)",0,0,0,0)'),
        encoding="utf-8",
    )

    assert classify_source(source)["proposed_profile"] == "MEAN_REVERSION"


def test_classifies_lowest_range_direction_as_trend(tmp_path: Path) -> None:
    source = tmp_path / "trend_lowest.mq5"
    source.write_text(
        _source("sqGetIndicatorValue(LOWESTINRANGE_1,0,5) >= SessionClose(NULL,0,6,30,2)"),
        encoding="utf-8",
    )

    assert classify_source(source)["proposed_profile"] == "TREND"


def test_classifies_awesome_oscillator_rise_as_momentum(tmp_path: Path) -> None:
    source = tmp_path / "awesome.mq5"
    source.write_text(_source("changesUp(AWESOMEOSCILLATOR_1,1)"), encoding="utf-8")

    assert classify_source(source)["proposed_profile"] == "MOMENTUM"
