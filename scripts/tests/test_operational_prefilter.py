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


# --- Separación del tope de validación y el de admisión (P5.0) -------------------------
#
# Hasta la v2 un único `max_per_symbol_timeframe` gobernaba la cola al Strategy Tester,
# mezclando un presupuesto de CPU (cuántas se validan) con una restricción de riesgo de
# portfolio (cuántas conviven en Incubadora). El efecto medido: 215 de 217 candidatas en
# `HOLD_DIVERSITY_CAP` por ser todas AUDCAD/H4, sin que nadie las estuviera admitiendo.

def _politica_v3(validation_bucket_cap, admission_bucket_cap, max_queue=10):
    return {
        "version": "test-v3",
        "wfe_f2_gate": {"enabled": False, "accepted_statuses": ["FORWARD_VALIDATED"]},
        "require_monte_carlo_evidence": True,
        "require_cost_evidence": False,
        "validation_queue": {
            "max_queue": max_queue,
            "max_per_symbol_timeframe": validation_bucket_cap,
        },
        "incubator_admission": {
            "max_per_symbol_timeframe": admission_bucket_cap,
            "max_concurrent": 8,
        },
    }


def _elegibles(n: int) -> list[dict[str, object]]:
    """n candidatas ELIGIBLE del mismo símbolo/timeframe, que es el caso real."""
    return [
        {
            "decision": "ELIGIBLE",
            "symbol": "AUDCAD",
            "timeframe": "H4",
            "sqx_sha256": f"sha{i:03d}",
            "metrics": {
                "profit_factor": 2.0,
                "sharpe": 1.5,
                "expectancy_r": 0.3,
                "max_dd_pct": 10.0,
            },
        }
        for i in range(n)
    ]


def test_validation_queue_without_bucket_cap_admits_the_whole_bucket() -> None:
    """Validar veinte AUDCAD/H4 no concentra riesgo: sólo gasta CPU."""
    decisions = _elegibles(6)

    queue = select_queue(decisions, _politica_v3(None, 2))

    assert len(queue) == 6
    assert not any(item["decision"] == "HOLD_DIVERSITY_CAP" for item in decisions)


def test_validation_queue_still_respects_its_own_size_budget() -> None:
    decisions = _elegibles(6)

    queue = select_queue(decisions, _politica_v3(None, 2, max_queue=4))

    assert len(queue) == 4
    assert sum(item["decision"] == "HOLD_QUEUE_CAP" for item in decisions) == 2


def test_queue_annotates_incubator_concentration_without_enforcing_it() -> None:
    """La concentración se anota, no se aplica: la cola es de validación, no de admisión."""
    decisions = _elegibles(5)

    queue = select_queue(decisions, _politica_v3(None, 2))

    assert [item["admission_bucket_rank"] for item in queue] == [1, 2, 3, 4, 5]
    excede = [item["exceeds_incubator_admission_cap"] for item in queue]
    assert excede == [False, False, True, True, True]


def test_a_validation_bucket_cap_still_works_when_configured() -> None:
    """Quien quiera limitar también la validación puede: deja de ser null."""
    decisions = _elegibles(5)

    queue = select_queue(decisions, _politica_v3(2, 2))

    assert len(queue) == 2
    assert sum(item["decision"] == "HOLD_DIVERSITY_CAP" for item in decisions) == 3


def test_v2_policy_keeps_its_previous_behaviour() -> None:
    """Una configuración antigua no cambia de comportamiento en silencio."""
    decisions = _elegibles(5)

    queue = select_queue(decisions, dict(POLICY))

    assert len(queue) == 1  # max_per_symbol_timeframe=1 en POLICY
    assert sum(item["decision"] == "HOLD_DIVERSITY_CAP" for item in decisions) == 4


# --- Reparto de la cola entre grupos (A28) ---------------------------------------------
#
# Con el tope de validacion sin limite por simbolo (P5.0), la cola se llenaba con las mejores
# en orden global. Medido sobre el inventario real de 424 candidatas: 205 superaban criterios
# y las 24 plazas se las llevaban TODAS AUDCAD/H4, que aporta 232 candidatas. Las de DAX40,
# XAUUSD y NASDAQ no llegaban nunca al Tester, que es justo lo que se buscaba al ampliar el
# universo. Ordenar por metrica global favorece al grupo mas numeroso, no al mejor portfolio.

def _elegibles_de(grupo: str, n: int, pf_base: float) -> list[dict[str, object]]:
    simbolo, timeframe = grupo.split("/")
    return [
        {
            "decision": "ELIGIBLE",
            "symbol": simbolo,
            "timeframe": timeframe,
            "sqx_sha256": f"{simbolo}{i:03d}",
            "metrics": {
                "profit_factor": pf_base - i * 0.001,
                "sharpe": 1.5,
                "expectancy_r": 0.3,
                "max_dd_pct": 10.0,
            },
        }
        for i in range(n)
    ]


def test_the_queue_is_shared_between_groups_not_taken_by_the_biggest() -> None:
    """El caso real: un grupo enorme y algo peor no puede vaciar la cola."""
    decisions = _elegibles_de("AUDCAD/H4", 50, pf_base=2.0) + _elegibles_de("DAX40/M30", 5, 1.9)

    queue = select_queue(decisions, _politica_v3(None, 2, max_queue=10))

    grupos = {f"{item['symbol']}/{item['timeframe']}" for item in queue}
    assert grupos == {"AUDCAD/H4", "DAX40/M30"}
    assert len(queue) == 10


def test_every_group_gets_a_turn_before_any_repeats() -> None:
    """Reparto por turnos: cada grupo coloca su mejor candidata antes de la segunda de nadie."""
    decisions = (
        _elegibles_de("AUDCAD/H4", 10, 2.0)
        + _elegibles_de("DAX40/M30", 10, 1.9)
        + _elegibles_de("XAUUSD/H1", 10, 1.8)
    )

    queue = select_queue(decisions, _politica_v3(None, 2, max_queue=3))

    assert len({f"{i['symbol']}/{i['timeframe']}" for i in queue}) == 3


def test_a_single_group_still_fills_the_queue() -> None:
    """Sin diversidad disponible no se desperdicia cola: el reparto no impone cuotas vacias."""
    decisions = _elegibles_de("AUDCAD/H4", 30, 2.0)

    queue = select_queue(decisions, _politica_v3(None, 2, max_queue=8))

    assert len(queue) == 8


def test_inside_a_group_the_order_is_still_by_merit() -> None:
    decisions = _elegibles_de("AUDCAD/H4", 5, 2.0)

    queue = select_queue(decisions, _politica_v3(None, 2, max_queue=3))

    pfs = [item["metrics"]["profit_factor"] for item in queue]
    assert pfs == sorted(pfs, reverse=True)
