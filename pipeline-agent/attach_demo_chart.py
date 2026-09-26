"""Materializa un gráfico demo desde un plan F4 ya sellado.

No compila, no abre terminales y no reemplaza perfiles: esas responsabilidades
permanecen en el agente interactivo. Sólo crea un `.chr` nuevo en el perfil
activo cuando el plan y su SHA-256 son verificables.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def canonical_sha256(plan: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--active-profile", required=True)
    parser.add_argument("--expert", required=True, type=Path)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    if not isinstance(plan, dict) or canonical_sha256(plan) != args.sha256:
        raise SystemExit("sealed plan hash mismatch")
    magic, symbol, timeframe = plan.get("magic_number"), plan.get("symbol"), plan.get("timeframe")
    if not isinstance(magic, int) or not isinstance(symbol, str) or not isinstance(timeframe, str):
        raise SystemExit("sealed plan lacks chart identity")
    profile = args.data_root / "MQL5" / "Profiles" / "Charts" / args.active_profile
    if not profile.is_dir() or not args.expert.is_file():
        raise SystemExit("active profile or compiled expert is absent")
    existing = list(profile.glob("*.chr"))
    if any(f"MagicNumber={magic}" in path.read_text(encoding="utf-16", errors="strict") for path in existing):
        raise SystemExit("magic already exists in active profile")
    target = profile / f"stratos_{magic}.chr"
    if target.exists():
        raise SystemExit("target chart already exists")
    target.write_text(
        f"<chart>\nsymbol={symbol}\nperiod={timeframe}\n<expert>\nname={args.expert.stem}\npath=Experts\\{plan['expert_relative_path']}\nexpertmode=1\n<inputs>\nMagicNumber={magic}\n</inputs>\n</expert>\n</chart>\n",
        encoding="utf-16",
    )
    print(f"chart={target}")


if __name__ == "__main__":
    main()
