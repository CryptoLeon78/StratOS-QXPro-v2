"""Crea en Windows un índice relativo de artefactos SQX/MQL5 para G12."""

from __future__ import annotations

import argparse
from pathlib import Path


EXTENSIONS = {".sqx", ".mq5", ".ex5"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ea-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = [
        path.relative_to(args.ea_root).as_posix()
        for path in args.ea_root.rglob("*")
        if path.is_file() and path.suffix.lower() in EXTENSIONS
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(paths) + "\n", encoding="utf-8")
    print(f"Índice G12 creado: {len(paths)} artefactos")


if __name__ == "__main__":
    main()
