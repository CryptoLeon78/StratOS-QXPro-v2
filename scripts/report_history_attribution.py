"""Cuánto del histórico exportado se puede atribuir a un bot, antes de ingerirlo.

Un CSV de `StratOSHistoryExport.mq5` trae el magic real de cada deal, pero eso no equivale a
poder atribuirlo: la migración de identidad compacta cambió los magics, y un portfolio con
años de rotación acumula magics de EAs que ya no existen.

Este informe no escribe nada en la base ni en MT5: lee el CSV y el registro de identidad y
dice qué proporción del histórico quedará atribuida, cuánta se rescata traduciendo magics
anteriores a la migración y cuánta seguirá huérfana. Sirve para decidir con un número
delante, en vez de descubrirlo después de importar.

Las categorías son excluyentes:

- `magic_vigente`   — el magic del deal es el de una identidad `ASSIGNED` actual.
- `magic_legacy`    — el magic es anterior a la migración y traduce a una identidad actual.
- `sin_ea`          — `magic=0`: operación manual o del bróker, ausencia declarada.
- `sin_identidad`   — el magic no está en el registro. EA retirado o nunca inventariado;
                      se declara huérfano, **nunca se adivina** por nombre o comentario.

Uso:
    python scripts/report_history_attribution.py \\
        --csv runtime/operational/history/history_deals_BEPB.csv \\
        --identity-registry runtime/operational/magic_identity/magic_identity_registry.jsonl
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from magic_identity import build_legacy_magic_map  # noqa: E402

MAGIC_SIN_EA = 0


def current_magics(registry_path: Path) -> set[int]:
    """Magics de las identidades vigentes, según los eventos `ASSIGNED` del registro."""
    vigentes: set[int] = set()
    with registry_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            event = json.loads(line)
            if event.get("event_type") == "ASSIGNED":
                vigentes.add(int(event["magic_number"]))
    return vigentes


def classify(csv_path: Path, registry_path: Path) -> dict[str, Any]:
    vigentes = current_magics(registry_path)
    legacy_map = build_legacy_magic_map(registry_path)

    por_magic: Counter[int] = Counter()
    fechas: list[str] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            por_magic[int(row["magic"])] += 1
            fechas.append(row["time"])

    categorias: Counter[str] = Counter()
    huerfanos: Counter[int] = Counter()
    for magic, count in por_magic.items():
        if magic == MAGIC_SIN_EA:
            categorias["sin_ea"] += count
        elif magic in vigentes:
            categorias["magic_vigente"] += count
        elif magic in legacy_map:
            categorias["magic_legacy"] += count
        else:
            categorias["sin_identidad"] += count
            huerfanos[magic] += count

    total = sum(por_magic.values())
    atribuibles = categorias["magic_vigente"] + categorias["magic_legacy"]
    return {
        "csv": str(csv_path),
        "deals": total,
        "magics_distintos": len(por_magic),
        "rango": {"desde": min(fechas), "hasta": max(fechas)} if fechas else None,
        "categorias": dict(categorias),
        "cobertura_pct": round(100 * atribuibles / total, 2) if total else 0.0,
        "cobertura_sin_traducir_pct": (
            round(100 * categorias["magic_vigente"] / total, 2) if total else 0.0
        ),
        "magics_huerfanos_top": [
            {"magic": magic, "deals": count} for magic, count in huerfanos.most_common(10)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path, action="append")
    parser.add_argument("--identity-registry", required=True, type=Path)
    parser.add_argument("--json", type=Path, default=None, help="vuelca el informe a un fichero")
    args = parser.parse_args()

    informes = [classify(ruta, args.identity_registry) for ruta in args.csv]
    for informe in informes:
        cat = informe["categorias"]
        print(f"\n{Path(informe['csv']).name}: {informe['deals']} deals, "
              f"{informe['magics_distintos']} magics distintos")
        if informe["rango"]:
            print(f"  rango             {informe['rango']['desde']} .. {informe['rango']['hasta']}")
        for clave in ("magic_vigente", "magic_legacy", "sin_ea", "sin_identidad"):
            valor = cat.get(clave, 0)
            pct = 100 * valor / informe["deals"] if informe["deals"] else 0
            print(f"  {clave:<17} {valor:>6}  ({pct:5.1f} %)")
        print(f"  cobertura         {informe['cobertura_sin_traducir_pct']:5.1f} % sin traducir "
              f"-> {informe['cobertura_pct']:5.1f} % traduciendo magics legacy")

    if args.json:
        args.json.write_text(
            json.dumps(informes, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\ninforme escrito en {args.json}")


if __name__ == "__main__":
    main()
