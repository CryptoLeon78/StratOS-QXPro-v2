"""Las corridas de campañas superseded no entran en la reclasificación (backlog A19).

El renombrado MN movió las carpetas de estrategia, así que un `sqx_path` que ya no existe
identifica una comparación de la campaña **anterior**. Su evidencia sigue sellada y su
veredicto es válido para lo que se midió entonces, pero esas corridas nunca llegaron a
registrarse en la base: incluirlas inflaba el recuento e forzaba una retención en cada
persistencia (ver `record_directional_reclassification.py`).
"""

from __future__ import annotations

from pathlib import Path

from reclassify_external_f7_backtests import _fuente_desaparecida


def test_a_run_whose_sqx_source_is_gone_is_superseded(tmp_path: Path) -> None:
    manifest = {"source": {"sqx_path": str(tmp_path / "no_existe.sqx"), "mq5_path": ""}}

    assert _fuente_desaparecida(manifest) == str(tmp_path / "no_existe.sqx")


def test_a_run_whose_sources_exist_is_current(tmp_path: Path) -> None:
    sqx = tmp_path / "vive.sqx"
    mq5 = tmp_path / "vive.mq5"
    sqx.write_bytes(b"x")
    mq5.write_bytes(b"x")
    manifest = {"source": {"sqx_path": str(sqx), "mq5_path": str(mq5)}}

    assert _fuente_desaparecida(manifest) is None


def test_a_missing_mq5_also_marks_the_run_as_superseded(tmp_path: Path) -> None:
    sqx = tmp_path / "vive.sqx"
    sqx.write_bytes(b"x")
    manifest = {"source": {"sqx_path": str(sqx), "mq5_path": str(tmp_path / "falta.mq5")}}

    assert _fuente_desaparecida(manifest) == str(tmp_path / "falta.mq5")


def test_a_manifest_without_source_is_not_treated_as_superseded() -> None:
    """Sin rutas declaradas no hay nada que comprobar: no se descarta por si acaso."""
    assert _fuente_desaparecida({}) is None
    assert _fuente_desaparecida({"source": {}}) is None
    assert _fuente_desaparecida({"source": {"sqx_path": ""}}) is None
