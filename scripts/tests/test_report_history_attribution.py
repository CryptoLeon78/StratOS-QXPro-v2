"""Informe de atribución del histórico (P2.2).

Lo que importa aquí es que las cuatro categorías sean excluyentes y que un magic
desconocido se declare huérfano en vez de adivinarse. En el histórico real de JJTI/BEPB
esa categoría es el 87-90 % de los deals: son EAs ya retirados, y el informe existe para
que ese número se vea antes de importar, no después.
"""

from __future__ import annotations

import json
from pathlib import Path

from report_history_attribution import classify, current_magics


CABECERA = (
    "deal_ticket,position_id,time,magic,symbol,entry,type,volume,price,profit,commission,swap,reason\n"
)


def _registro(tmp_path: Path) -> Path:
    ruta = tmp_path / "registry.jsonl"
    eventos = [
        {
            "event_type": "ASSIGNED",
            "comment_identity": "XAUH1BUYSTOPeof_1.8.81_MN1",
            "magic_number": 1,
            "legacy_magic_numbers": [7786],
            "accounts": ["BEPB"],
        },
        {"event_type": "MIGRATION_PLANNED", "magic_number": 1, "legacy_magic_numbers": [7786]},
    ]
    ruta.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in eventos) + "\n", encoding="utf-8"
    )
    return ruta


def _csv(tmp_path: Path, magics: list[int]) -> Path:
    ruta = tmp_path / "history.csv"
    filas = "".join(
        f"{i},{i},2026.01.0{(i % 9) + 1} 00:00:00,{magic},EURUSD,0,0,0.10,1.10,0,0,0,0\n"
        for i, magic in enumerate(magics, start=1)
    )
    ruta.write_text(CABECERA + filas, encoding="utf-8")
    return ruta


def test_current_magics_only_counts_assignments(tmp_path: Path) -> None:
    assert current_magics(_registro(tmp_path)) == {1}


def test_the_four_categories_are_exclusive_and_add_up(tmp_path: Path) -> None:
    csv_path = _csv(tmp_path, [1, 1, 7786, 0, 987654, 987654, 987654])

    informe = classify(csv_path, _registro(tmp_path))

    assert informe["deals"] == 7
    assert informe["categorias"] == {
        "magic_vigente": 2,
        "magic_legacy": 1,
        "sin_ea": 1,
        "sin_identidad": 3,
    }
    assert sum(informe["categorias"].values()) == informe["deals"]


def test_translation_is_what_moves_the_coverage(tmp_path: Path) -> None:
    csv_path = _csv(tmp_path, [1, 7786, 7786, 7786])

    informe = classify(csv_path, _registro(tmp_path))

    assert informe["cobertura_sin_traducir_pct"] == 25.0
    assert informe["cobertura_pct"] == 100.0


def test_unknown_magics_are_listed_so_they_can_be_investigated(tmp_path: Path) -> None:
    csv_path = _csv(tmp_path, [55555, 55555, 66666])

    informe = classify(csv_path, _registro(tmp_path))

    assert informe["magics_huerfanos_top"][0] == {"magic": 55555, "deals": 2}
    assert informe["cobertura_pct"] == 0.0
