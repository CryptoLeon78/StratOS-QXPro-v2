"""Copia un artefacto MT5 por SSH en lectura y lo sella localmente.

No ejecuta terminal64.exe, MetaEditor ni comandos remotos de modificación.
Requiere un alias ya configurado en mt5_bridge y conserva los bytes originales.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-root", required=True, type=Path)
    parser.add_argument("--terminal", required=True)
    parser.add_argument("--remote-mql5-path", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bridge_root = args.bridge_root.resolve()
    if not (bridge_root / "config.py").is_file() or not (bridge_root / "target.py").is_file():
        raise SystemExit("--bridge-root no contiene mt5_bridge")
    sys.path.insert(0, str(bridge_root))
    from config import resolver_terminal  # noqa: PLC0415
    from target import crear_target  # noqa: PLC0415

    target = crear_target(resolver_terminal(args.terminal))
    source = target.ruta_absoluta(args.remote_mql5_path)
    payload = target.leer_bytes(source)
    digest = hashlib.sha256(payload).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = args.output_dir / f"{Path(args.remote_mql5_path).name}.{digest[:12]}.raw"
    if destination.exists() and destination.read_bytes() != payload:
        raise SystemExit(f"colisión de destino con bytes distintos: {destination}")
    destination.write_bytes(payload)
    print(f"artifact={destination} sha256={digest} bytes={len(payload)}")


if __name__ == "__main__":
    main()
