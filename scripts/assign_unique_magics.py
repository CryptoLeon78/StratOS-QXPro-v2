"""Asigna magics únicos a EAs exportados en lote desde SQX.

SQX no aleatoriza el `MagicNumber` al exportar varios EAs de golpe: salen todos con el valor
por defecto. En el export de `DAX40_m30` fueron 28 EAs compartiendo `11111`, y el inventario
operacional los retiene con `DUPLICATE_MAGIC_NUMBER` — con razón: un magic repetido hace
imposible atribuir un trade a su bot, que es el contrato sobre el que se sostiene toda la
telemetría. Es el mismo problema que ya apareció con seis EAs del stock compartiendo `11111`.

Qué hace y qué no:

- **Sólo toca los duplicados.** Un conjunto ya correcto se deja intacto, y dentro de cada
  grupo duplicado el primero por nombre conserva su valor: se cambia lo mínimo necesario.
- **Determinista**: dos ejecuciones sobre el mismo conjunto proponen exactamente lo mismo, y
  una segunda pasada sobre un conjunto ya corregido no cambia nada.
- **Nunca reutiliza** un magic presente en el conjunto, aunque parezca libre.
- **No inventa** un magic donde no hay `MagicNumber`: ese fichero no es un EA exportado
  normal y se deja como está.

El magic definitivo de un bot desplegado lo asigna la migración de identidad compacta
(G13-18); esto sólo resuelve la colisión que impide inventariar la candidata.
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

MAGIC_PATTERN = re.compile(r"(input\s+int\s+MagicNumber\s*=\s*)(\d+)")


def read_magic(path: Path) -> int | None:
    try:
        match = MAGIC_PATTERN.search(path.read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        return None
    return int(match.group(2)) if match else None


def _write_magic(path: Path, magic: int) -> None:
    texto = path.read_text(encoding="utf-8", errors="ignore")
    path.write_text(MAGIC_PATTERN.sub(rf"\g<1>{magic}", texto, count=1), encoding="utf-8")


def assign_unique_magics(root: Path, *, apply: bool) -> list[tuple[Path, int, int]]:
    """Devuelve los cambios `(fichero, magic_anterior, magic_nuevo)` necesarios o aplicados."""
    actuales: dict[Path, int] = {}
    for ruta in sorted(root.rglob("*.mq5")):
        magic = read_magic(ruta)
        if magic is not None:
            actuales[ruta] = magic

    por_magic: dict[int, list[Path]] = defaultdict(list)
    for ruta, magic in actuales.items():
        por_magic[magic].append(ruta)

    # Un magic en uso no se reutiliza aunque el hueco parezca libre: si no, reasignar un
    # duplicado podria crear otro.
    ocupados = set(actuales.values())
    cambios: list[tuple[Path, int, int]] = []
    siguiente = max(ocupados, default=0) + 1

    for magic in sorted(por_magic):
        rutas = por_magic[magic]
        # El primero por nombre conserva su valor; sólo se mueven los que colisionan con él.
        for ruta in rutas[1:]:
            while siguiente in ocupados:
                siguiente += 1
            cambios.append((ruta, magic, siguiente))
            ocupados.add(siguiente)
            if apply:
                _write_magic(ruta, siguiente)
            siguiente += 1
    return cambios


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    cambios = assign_unique_magics(args.root, apply=args.apply)
    if not cambios:
        print("sin magics duplicados: nada que reasignar")
        return
    for ruta, antes, despues in cambios:
        print(f"  {ruta.name}: {antes} -> {despues}")
    verbo = "reasignados" if args.apply else "a reasignar"
    print(f"{len(cambios)} magic(s) {verbo}")
    if not args.apply:
        print("simulación: repite con --apply para escribir")


if __name__ == "__main__":
    main()
