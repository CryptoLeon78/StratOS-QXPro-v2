"""Resumen de estado de la admisión operacional.

Lo que importa de este resumen es que responda a "¿hay algo que hacer?" sin obligar a leer
el volcado de comandos del lanzador, y que **no invente estado cuando no lo hay**: sin
artefactos, lo honesto es decir que no hay inventario, no pintar ceros que parecen medidas.
"""

from __future__ import annotations

import json
from pathlib import Path

from operational_status import render


def _escribir(runtime: Path, nombre: str, payload: dict) -> None:
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / nombre).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_without_artifacts_it_says_so_instead_of_showing_zeros(tmp_path: Path) -> None:
    texto = "\n".join(render(tmp_path))

    assert "Sin inventario todavia" in texto
    assert "Export -> MQL5" in texto


def test_it_reports_the_inventory_broken_down_by_status(tmp_path: Path) -> None:
    _escribir(
        tmp_path,
        "analysis-inventory.json",
        {
            "generated_at_utc": "2026-09-02T08:00:00+00:00",
            "items": [
                {"status": "STATIC_VALIDATED", "symbol": "AUDCAD", "timeframe": "H4"},
                {"status": "STATIC_VALIDATED", "symbol": "DAX40", "timeframe": "M30"},
                {"status": "WITHHELD", "symbol": "DAX40", "timeframe": "M30"},
            ],
        },
    )

    texto = "\n".join(render(tmp_path))

    assert "3 candidatas" in texto
    assert "STATIC_VALIDATED" in texto and "WITHHELD" in texto
    assert "DAX40/M30" in texto


def test_a_queue_with_work_points_at_the_backtests_launcher(tmp_path: Path) -> None:
    _escribir(tmp_path, "analysis-inventory.json", {"items": []})
    _escribir(
        tmp_path,
        "operational-tester-queue.json",
        {"max_backtests_per_run": 2, "entries": [{"strategy_name": "AUDCADH4S 1.14.75"}]},
    )

    texto = "\n".join(render(tmp_path))

    assert "1 backtests" in texto
    assert "AUDCADH4S 1.14.75" in texto
    assert "Backtests SQX vs MT5" in texto


def test_an_empty_queue_points_at_the_export_bottleneck(tmp_path: Path) -> None:
    """Sin cola no hay nada que correr: lo util es recordar que falta exportar el .mq5."""
    _escribir(tmp_path, "analysis-inventory.json", {"items": []})
    _escribir(tmp_path, "operational-tester-queue.json", {"entries": []})

    texto = "\n".join(render(tmp_path))

    assert "no hay backtests en cola" in texto
    assert "Forward_finalistas" in texto


def test_a_corrupt_artifact_does_not_break_the_summary(tmp_path: Path) -> None:
    """Un JSON roto no puede dejar al operador sin saber en que estado esta."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "analysis-inventory.json").write_text("{ roto", encoding="utf-8")

    texto = "\n".join(render(tmp_path))

    assert "Sin inventario todavia" in texto
