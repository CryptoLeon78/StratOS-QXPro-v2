"""El ejecutor de cola reconoce las comparaciones lanzadas a mano (backlog A24).

`logged_identities()` sólo mira el log de la propia cola. Las cuatro comparaciones del
2026-09-01 (`asset_id` 243-246) se lanzaron con `run_operational_sqx_mt5_backtest.py`, así
que no figuran ahí: al ejecutar la cola el 2026-09-02 empezó a **repetirlas** en vez de ir a
las dos pendientes.

La fuente de verdad de "esta identidad ya se comparó" no es el log de un ejecutor concreto,
sino los **manifiestos sellados** de `backtests_live/`. El cruce se hace por `sqx_sha256`,
que es la identidad del artefacto: la ruta no sirve, porque el renombrado MN movió las
carpetas y una comparación válida quedaría sin reconocer.
"""

from __future__ import annotations

import json
from pathlib import Path

from run_live_backtest_queue import sealed_identities


def _queue(tmp_path: Path, entries: list[dict[str, object]]) -> Path:
    ruta = tmp_path / "queue.json"
    ruta.write_text(json.dumps({"entries": entries}, ensure_ascii=False), encoding="utf-8")
    return ruta


def _manifest(
    root: Path, run_id: str, sha: str, *, mode: str = "launch", returncode: int = 0
) -> None:
    carpeta = root / run_id
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "run-manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "mode": mode,
                "source": {"sqx_sha256": sha},
                "result": {"returncode": returncode},
            }
        ),
        encoding="utf-8",
    )


ENTRADA = {
    "account_login": "4000055216",
    "magic_number": 7507,
    "sqx_sha256": "aaa111",
    "status": "READY_FOR_TICK_BACKTEST",
}


def test_a_manually_launched_comparison_counts_as_done(tmp_path: Path) -> None:
    """El caso real: comparación sellada por el lanzador individual, ausente del log."""
    salida = tmp_path / "backtests_live"
    _manifest(salida, "20260901T155216Z_aaa111", "aaa111")

    identidades = sealed_identities(salida, [_queue(tmp_path, [ENTRADA])])

    assert identidades == {("4000055216", 7507)}


def test_the_match_is_by_hash_not_by_path(tmp_path: Path) -> None:
    """El renombrado MN movió las carpetas: cruzar por ruta perdería comparaciones válidas."""
    salida = tmp_path / "backtests_live"
    _manifest(salida, "run", "aaa111")
    entrada = {**ENTRADA, "sqx_path": "C:/otra/ruta/que/ya/no/existe.sqx"}

    assert sealed_identities(salida, [_queue(tmp_path, [entrada])]) == {("4000055216", 7507)}


def test_a_preflight_manifest_is_not_a_comparison(tmp_path: Path) -> None:
    """Los dos manifiestos que dejó la corrida abortada son `mode=preflight`: no cuentan."""
    salida = tmp_path / "backtests_live"
    _manifest(salida, "run", "aaa111", mode="preflight")

    assert sealed_identities(salida, [_queue(tmp_path, [ENTRADA])]) == set()


def test_a_failed_run_is_not_a_comparison(tmp_path: Path) -> None:
    salida = tmp_path / "backtests_live"
    _manifest(salida, "run", "aaa111", returncode=1)

    assert sealed_identities(salida, [_queue(tmp_path, [ENTRADA])]) == set()


def test_a_hash_outside_the_queue_is_ignored(tmp_path: Path) -> None:
    """Una comparación de otra campaña no inventa una identidad que la cola no declara."""
    salida = tmp_path / "backtests_live"
    _manifest(salida, "run", "hash-desconocido")

    assert sealed_identities(salida, [_queue(tmp_path, [ENTRADA])]) == set()


def test_an_entry_without_magic_does_not_produce_an_identity(tmp_path: Path) -> None:
    salida = tmp_path / "backtests_live"
    _manifest(salida, "run", "aaa111")
    entrada = {k: v for k, v in ENTRADA.items() if k != "magic_number"}

    assert sealed_identities(salida, [_queue(tmp_path, [entrada])]) == set()


def test_a_missing_output_root_is_absence_not_an_error(tmp_path: Path) -> None:
    assert sealed_identities(tmp_path / "no_existe", [_queue(tmp_path, [ENTRADA])]) == set()


def test_an_unreadable_manifest_does_not_abort_the_scan(tmp_path: Path) -> None:
    """Un manifiesto corrupto no puede hacer que se repitan todas las demás comparaciones."""
    salida = tmp_path / "backtests_live"
    _manifest(salida, "bueno", "aaa111")
    roto = salida / "roto"
    roto.mkdir(parents=True, exist_ok=True)
    (roto / "run-manifest.json").write_text("{ no es json", encoding="utf-8")

    assert sealed_identities(salida, [_queue(tmp_path, [ENTRADA])]) == {("4000055216", 7507)}
