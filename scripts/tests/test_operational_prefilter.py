from pathlib import Path

from operational_prefilter import evaluate_items, select_queue

THRESHOLDS = {
    "pipeline_min_trades": 30.0,
    "pipeline_min_days": 60.0,
    "pipeline_pf": 1.5,
    "pipeline_exp": 0.15,
    "pipeline_sharpe": 1.0,
    "pipeline_maxdd": 20.0,
    "pipeline_min_freq_week": 2.0,
    "wfe_min": 0.5,
}
POLICY = {
    "version": "test",
    "wfe_f2_gate": {
        "enabled": False,
        "accepted_statuses": [
            "VALIDATED_EQUIVALENCE",
            "FORWARD_VALIDATED",
            "MT5_COMPARISON_VALIDATED",
        ],
    },
    "require_monte_carlo_evidence": True,
    "require_cost_evidence": False,
    "max_per_symbol_timeframe": 1,
    "max_mt5_queue": 2,
}


def _item(tmp_path: Path, name: str, sha: str) -> dict[str, object]:
    path = tmp_path / f"{name}.sqx"
    path.write_bytes(b"test")
    import hashlib

    return {
        "strategy_name": name,
        "sqx_sha256": hashlib.sha256(b"test").hexdigest() if sha == "real" else sha,
        "mql5_sha256": "mql5",
        "sqx_path": str(path),
        "mql5_path": str(tmp_path / f"{name}.mq5"),
        "symbol": "EURUSD",
        "timeframe": "H1",
        "status": "STATIC_VALIDATED",
    }


def _quality_evidence(tmp_path: Path, sha: str) -> dict[str, dict[str, object]]:
    import hashlib

    artifact = tmp_path / "evidence.json"
    artifact.write_text("{}", encoding="utf-8")
    artifact_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    sealed = {"artifact_path": str(artifact), "sha256": artifact_hash}
    return {
        sha: {
            "sqx_sha256": sha,
            "wfe": {"value": 0.6, "f2_gate_status": "NOT_APPLICABLE", **sealed},
            "monte_carlo": {"p95_no_ruin": True, **sealed},
        }
    }


def test_prefilter_holds_without_robustness_evidence(tmp_path: Path, monkeypatch) -> None:
    import operational_prefilter as subject

    monkeypatch.setattr(
        subject,
        "baseline_metrics",
        lambda _: {
            "profit_factor": 1.7,
            "expectancy_r": 0.2,
            "sharpe": 1.1,
            "max_dd_pct": 10,
            "trade_count": 80,
            "history_days": 500,
            "trades_per_week": 2.5,
            "backtest_from": "2020-01-01",
            "backtest_to": "2021-05-15",
            "symbol": "EURUSD",
            "timeframe": "H1",
        },
    )
    item = _item(tmp_path, "candidate", "real")

    result = evaluate_items(
        [item], policy=POLICY, thresholds=THRESHOLDS, quality_evidence={}, completed={}
    )

    assert result[0]["decision"] == "HOLD"
    assert result[0]["reasons"] == ["MISSING_MONTE_CARLO_EVIDENCE"]


def test_prefilter_only_applies_f2_after_validated_mapping(tmp_path: Path, monkeypatch) -> None:
    import copy
    import operational_prefilter as subject

    monkeypatch.setattr(
        subject,
        "baseline_metrics",
        lambda _: {
            "profit_factor": 1.7,
            "expectancy_r": 0.2,
            "sharpe": 1.1,
            "max_dd_pct": 10,
            "trade_count": 80,
            "history_days": 500,
            "trades_per_week": 2.5,
            "backtest_from": "2020-01-01",
            "backtest_to": "2021-05-15",
            "symbol": "EURUSD",
            "timeframe": "H1",
        },
    )
    policy = copy.deepcopy(POLICY)
    policy["wfe_f2_gate"]["enabled"] = True
    item = _item(tmp_path, "candidate", "real")
    sha = str(item["sqx_sha256"])
    evidence = _quality_evidence(tmp_path, sha)

    result = evaluate_items(
        [item], policy=policy, thresholds=THRESHOLDS, quality_evidence=evidence, completed={}
    )

    assert result[0]["reasons"] == ["WFE_F2_EVIDENCE_NOT_VALIDATED"]


def test_prefilter_excludes_completed_before_it_can_queue(tmp_path: Path, monkeypatch) -> None:
    import operational_prefilter as subject

    monkeypatch.setattr(
        subject,
        "baseline_metrics",
        lambda _: {
            "profit_factor": 1.7,
            "expectancy_r": 0.2,
            "sharpe": 1.1,
            "max_dd_pct": 10,
            "trade_count": 80,
            "history_days": 500,
            "trades_per_week": 2.5,
            "backtest_from": "2020-01-01",
            "backtest_to": "2021-05-15",
            "symbol": "EURUSD",
            "timeframe": "H1",
        },
    )
    item = _item(tmp_path, "candidate", "real")
    sha = str(item["sqx_sha256"])
    evidence = _quality_evidence(tmp_path, sha)

    result = evaluate_items(
        [item],
        policy=POLICY,
        thresholds=THRESHOLDS,
        quality_evidence=evidence,
        completed={sha: {"run_id": "run-1", "verdict": "DISCREPANTE"}},
    )

    assert result[0]["decision"] == "EXCLUDED_ALREADY_TESTED"
    assert select_queue(result, POLICY) == []


def test_prefilter_applies_diversity_cap(tmp_path: Path, monkeypatch) -> None:
    import operational_prefilter as subject

    monkeypatch.setattr(
        subject,
        "baseline_metrics",
        lambda _: {
            "profit_factor": 1.7,
            "expectancy_r": 0.2,
            "sharpe": 1.1,
            "max_dd_pct": 10,
            "trade_count": 80,
            "history_days": 500,
            "trades_per_week": 2.5,
            "backtest_from": "2020-01-01",
            "backtest_to": "2021-05-15",
            "symbol": "EURUSD",
            "timeframe": "H1",
        },
    )
    first, second = _item(tmp_path, "first", "real"), _item(tmp_path, "second", "real")
    sha = str(first["sqx_sha256"])
    evidence = _quality_evidence(tmp_path, sha)

    result = evaluate_items(
        [first, second],
        policy=POLICY,
        thresholds=THRESHOLDS,
        quality_evidence=evidence,
        completed={},
    )
    queue = select_queue(result, POLICY)

    assert len(queue) == 1
    assert any(item["decision"] == "HOLD_DIVERSITY_CAP" for item in result)
