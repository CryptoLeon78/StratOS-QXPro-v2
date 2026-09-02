"""Resumen legible del estado de admisión operacional.

El lanzador vuelca los comandos que ejecuta —rutas Docker larguísimas— y al terminar deja al
operador leyendo un muro de texto para saber si hay algo que hacer. Esto responde a la única
pregunta que importa después de un refresco: **cuántas candidatas hay, en qué punto están y
qué bloquea a las que no avanzan.**

Sólo lee artefactos de `runtime/operational/`. No toca la base, ni SQX, ni MT5.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Las candidatas de Análisis necesitan `.sqx` Y `.mq5` juntos para inventariarse; el `.mq5`
# se genera exportando desde SQX. Es el cuello real y conviene recordarlo donde se ve.
EXPORT_HINT = (
    "Para que aparezcan candidatas nuevas: exporta desde SQX (Export -> MQL5 Expert Advisor)\n"
    "  y deja el .sqx y el .mq5 juntos en\n"
    "  EAs_SQX_guardados\\Analisis\\<proyecto>\\Forward_finalistas\\"
)


def _load(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _age(iso: str | None) -> str:
    if not iso:
        return "fecha desconocida"
    try:
        cuando = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso
    horas = (datetime.now(UTC) - cuando).total_seconds() / 3600
    if horas < 1:
        return f"hace {int(horas * 60)} min"
    if horas < 48:
        return f"hace {horas:.0f} h"
    return f"hace {horas / 24:.0f} dias"


def render(runtime: Path) -> list[str]:
    out: list[str] = []
    inventario = _load(runtime / "analysis-inventory.json")
    prefiltro = _load(runtime / "analysis-prefilter.json")
    cola = _load(runtime / "operational-tester-queue.json")

    out.append("")
    out.append("  ESTADO DE LA ADMISION OPERACIONAL")
    out.append("  " + "-" * 52)

    if inventario is None:
        out.append("  Sin inventario todavia. Ejecuta un refresco.")
        out.append("")
        out.append("  " + EXPORT_HINT.replace("\n", "\n  "))
        return out

    items = inventario.get("items") or []
    estados = Counter(str(i.get("status")) for i in items)
    grupos = Counter(f"{i.get('symbol')}/{i.get('timeframe')}" for i in items if i.get("symbol"))
    edad_inv = _age(inventario.get("generated_at_utc"))
    out.append(f"  Inventario         {len(items):>4} candidatas   ({edad_inv})")
    for estado, n in estados.most_common():
        out.append(f"     {estado:<22} {n:>4}")
    if grupos:
        out.append("  Por simbolo/timeframe:")
        for k, n in grupos.most_common(6):
            out.append(f"     {k:<22} {n:>4}")

    if prefiltro is not None:
        s = prefiltro.get("summary") or {}
        out.append("")
        edad_pre = _age(prefiltro.get("generated_at_utc"))
        out.append(f"  Prefiltro                         ({edad_pre})")
        out.append(f"     superan los criterios  {s.get('eligible_before_diversity', '?'):>4}")
        out.append(f"     en cola para MT5       {s.get('mt5_queue', '?'):>4}")
        out.append(f"     en espera              {s.get('hold', '?'):>4}")
        out.append(f"     ya comparadas          {s.get('already_tested', '?'):>4}")

    if cola is not None:
        entradas = cola.get("entries") or []
        out.append("")
        tope = cola.get("max_backtests_per_run", "?")
        out.append(
            f"  Siguiente tanda    {len(entradas):>4} backtests    (tope por sesion: {tope})"
        )
        for e in entradas[:5]:
            nombre = e.get("strategy_name") or Path(str(e.get("sqx_path", ""))).stem
            out.append(f"     - {nombre[:52]}")

    out.append("")
    if cola and (cola.get("entries") or []):
        out.append("  QUE HACER: abre 'StratOS - Backtests SQX vs MT5' en el escritorio.")
        out.append("  Refresca solo, cierra MT5 si hace falta y pide confirmacion por corrida.")
    else:
        out.append("  QUE HACER: no hay backtests en cola.")
        out.append("  " + EXPORT_HINT.replace("\n", "\n  "))
    out.append("")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "runtime" / "operational",
    )
    args = parser.parse_args()
    for linea in render(args.runtime):
        print(linea)


if __name__ == "__main__":
    main()
