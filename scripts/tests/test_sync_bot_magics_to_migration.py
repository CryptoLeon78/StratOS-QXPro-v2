"""Sincronización del magic de los bots F7 con la identidad vigente (P2.2).

Los 40 bots se dieron de alta el 2026-08-31 con los magics que los EAs emitían entonces; la
migración MN se aplicó después en los terminales. Desde el 2026-09-01 esos EAs emiten su magic
nuevo y la ingesta dejó de reconocerlos: no son los 38 trades que había ese día, es que la
atribución quedaba rota **hacia adelante**.

Aquí se prueba la parte pura -- qué correspondencias son admisibles -- sin base de datos.
"""

from __future__ import annotations

import json
from pathlib import Path

from magic_identity import build_legacy_magic_map
from sync_bot_magics_to_migration import accounts_of


def _registro(tmp_path: Path, eventos: list[dict[str, object]]) -> Path:
    ruta = tmp_path / "registry.jsonl"
    ruta.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in eventos) + "\n", encoding="utf-8"
    )
    return ruta


def _asignacion(comment: str, magic: int, legacy: list[int], accounts: list[str]):
    return {
        "event_type": "ASSIGNED",
        "comment_identity": comment,
        "magic_number": magic,
        "legacy_magic_numbers": legacy,
        "accounts": accounts,
    }


def test_the_map_points_from_the_deployed_legacy_to_the_current_magic(tmp_path: Path) -> None:
    ruta = _registro(tmp_path, [_asignacion("EUUSH1Seof_7.30.121_MN5", 5, [2004262], ["BEPB"])])

    mapa = build_legacy_magic_map(ruta)

    assert mapa[2004262]["magic_number"] == 5
    assert accounts_of(mapa[2004262]) == ["BEPB"]


def test_the_target_account_travels_with_the_correspondence(tmp_path: Path) -> None:
    """Dos cuentas pueden reutilizar un magic: la evidencia dice a cuál pertenece."""
    ruta = _registro(tmp_path, [_asignacion("A_MN9", 9, [2084], ["JJTI"])])

    mapa = build_legacy_magic_map(ruta)

    assert accounts_of(mapa[2084]) == ["JJTI"]


def test_an_ambiguous_legacy_is_not_synced(tmp_path: Path) -> None:
    ruta = _registro(
        tmp_path,
        [_asignacion("A_MN1", 1, [5000], ["BEPB"]), _asignacion("B_MN2", 2, [5000], ["JJTI"])],
    )

    assert build_legacy_magic_map(ruta) == {}


def test_a_bot_whose_magic_did_not_change_is_left_alone(tmp_path: Path) -> None:
    ruta = _registro(tmp_path, [_asignacion("A_MN7507", 7507, [7507], ["BEPB"])])

    assert build_legacy_magic_map(ruta) == {}


def test_an_assignment_without_accounts_does_not_invent_one(tmp_path: Path) -> None:
    ruta = _registro(tmp_path, [_asignacion("A_MN3", 3, [900], [])])

    assert accounts_of(build_legacy_magic_map(ruta)[900]) == []
