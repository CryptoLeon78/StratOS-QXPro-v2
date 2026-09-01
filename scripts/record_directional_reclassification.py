"""Persiste una reclasificación direccional sellada como eventos append-only.

`reclassify_external_f7_backtests.py` reevalúa manifiestos de `SQX_vs_MT5` ya sellados bajo
el contrato direccional (ASSUMPTIONS G13-25) y produce un JSON con el veredicto nuevo de cada
corrida. Ese JSON vivía sólo en disco: el sistema no conocía la relectura, así que la verdad
contractual vigente y lo que la base sabía divergían.

Este script cierra ese hueco **sin reescribir nada**. Los eventos originales permanecen
inmutables y siguen siendo correctos —un F7 externo es `WITHHELD` con independencia del
veredicto de comparación—; lo que se añade es un evento nuevo por cada corrida cuyo veredicto
cambió, enlazado al `run_id` y al hash del manifiesto original.

Reglas:

- Sólo se registran las corridas con **cambio** de veredicto. Reafirmar un veredicto idéntico
  no es información nueva y ensuciaría la cadena.
- El estado del evento nuevo se deriva igual que en el registro original: `VALIDADA` sería
  `BACKTEST_VALIDATED`, pero un F7 externo se mantiene `WITHHELD` en todo caso. Una
  reclasificación **no promueve**: no crea baseline, bot ni entrada en Incubadora.
- Idempotente: una segunda ejecución no añade eventos.
- Fail-closed: si el JSON no trae su `payload_sha256`, si no cuadra, o si una corrida no
  corresponde a ningún asset conocido, no se escribe nada.

Uso:
    python scripts/record_directional_reclassification.py \\
        --reclassification runtime/operational/backtests_live/reclassification.json
    (añadir --apply para escribir; sin él sólo informa)
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core-engine" / "src"))

REASON_PREFIX = "DIRECTIONAL_RECLASSIFICATION"
PARSER_VERSION = "directional-reclassification-v1"


def seal_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_reclassification(path: Path) -> dict[str, Any]:
    """Lee el JSON sellado y comprueba su propio hash antes de dejar escribir nada."""
    data = json.loads(path.read_text(encoding="utf-8"))
    seal = data.get("payload_sha256")
    if not isinstance(seal, str) or not seal:
        raise ValueError(f"{path.name} no declara payload_sha256: no es una evidencia sellada")
    payload = {k: v for k, v in data.items() if k != "payload_sha256"}
    if seal_payload(payload) != seal:
        raise ValueError(f"el sello de {path.name} no cuadra con su contenido")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"{path.name} no contiene corridas reevaluadas")
    return data


def changed_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Sólo las corridas cuyo veredicto cambió: reafirmar no es información nueva."""
    return [
        entry
        for entry in data["entries"]
        if entry.get("original_verdict") != entry.get("reclassified_verdict")
    ]


async def persist(data: dict[str, Any], apply: bool) -> list[str]:
    from core.db.base import async_session_factory
    from core.db.enums import AssetAdmissionStatus
    from core.db.models.operations import OperationalAssetEvent
    from sqlalchemy import select

    cambios = changed_entries(data)
    lineas: list[str] = []
    async with async_session_factory() as session:
        eventos = (await session.execute(select(OperationalAssetEvent))).scalars().all()
        por_run: dict[str, list[OperationalAssetEvent]] = {}
        for evento in eventos:
            run_id = (evento.evidence or {}).get("run_id")
            if isinstance(run_id, str):
                por_run.setdefault(run_id, []).append(evento)

        pendientes: list[tuple[dict[str, Any], OperationalAssetEvent]] = []
        for entry in cambios:
            run_id = entry["run_id"]
            originales = por_run.get(run_id)
            if not originales:
                # Fail-closed por entrada, no por lote: una corrida sellada en disco que
                # nunca llegó a registrarse no se puede reclasificar --no se reclasifica lo
                # que el sistema no registró-- pero tampoco puede impedir que las demás se
                # persistan. Se retiene y se reporta para que se registre por su vía
                # canónica (record_operational_backtest.py) antes de reevaluarla.
                lineas.append(
                    f"  {run_id}: RETENIDA, sin evento original en la base "
                    f"({entry['original_verdict']} -> {entry['reclassified_verdict']})"
                )
                continue
            if any(
                (evento.evidence or {}).get("reclassification_payload_sha256")
                == data["payload_sha256"]
                for evento in originales
            ):
                lineas.append(f"  {run_id}: ya registrada")
                continue
            pendientes.append((entry, originales[0]))

        for entry, original in pendientes:
            # Un F7 externo se mantiene WITHHELD aunque el veredicto suba a VALIDADA: la
            # reclasificación es contractual, no una promoción.
            es_externo = bool((original.evidence or {}).get("external_f7"))
            nuevo = entry["reclassified_verdict"]
            status = (
                AssetAdmissionStatus.BACKTEST_VALIDATED
                if nuevo == "VALIDADA" and not es_externo
                else AssetAdmissionStatus.WITHHELD
            )
            lineas.append(
                f"  {entry['run_id']}: {entry['original_verdict']} -> {nuevo} "
                f"(asset_id={original.asset_id}, status={status.value})"
            )
            if not apply:
                continue
            session.add(
                OperationalAssetEvent(
                    asset_id=original.asset_id,
                    status=status,
                    reason=f"{REASON_PREFIX}_{entry['original_verdict']}_TO_{nuevo}",
                    evidence={
                        "run_id": entry["run_id"],
                        "source_manifest_sha256": entry.get("source_manifest_sha256"),
                        "original_verdict": entry["original_verdict"],
                        "verdict": nuevo,
                        "metrics": entry.get("metrics"),
                        "detail": entry.get("detail"),
                        "thresholds": data.get("thresholds"),
                        "panel_config_sha256": data.get("panel_config_sha256"),
                        "reclassification_payload_sha256": data["payload_sha256"],
                        "reclassification_generated_at_utc": data.get("generated_at_utc"),
                        "parser_version": PARSER_VERSION,
                        "supersedes_event_id": original.id,
                        "external_f7": (original.evidence or {}).get("external_f7"),
                        "note": (
                            "Reclasificación contractual bajo el contrato direccional "
                            "(ASSUMPTIONS G13-25). No promueve: no crea baseline, bot ni "
                            "entrada en Incubadora."
                        ),
                    },
                    occurred_at=datetime.now(UTC),
                )
            )
        if apply and pendientes:
            await session.commit()
    return lineas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reclassification", required=True, type=Path)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="escribe los eventos; sin este flag sólo informa de lo que haría",
    )
    args = parser.parse_args()

    if os.getenv("DEPLOYMENT_PROFILE") != "operational":
        raise SystemExit(
            "este registro pertenece al stack operacional: exporta "
            "DEPLOYMENT_PROFILE=operational y su DATABASE_URL antes de aplicarlo"
        )

    data = load_reclassification(args.reclassification)
    cambios = changed_entries(data)
    total = len(data["entries"])
    print(f"{args.reclassification.name}: {total} corridas evaluadas, {len(cambios)} con cambio")
    if not cambios:
        print("nada que registrar: ningún veredicto cambió")
        return
    lineas = asyncio.run(persist(data, args.apply))
    for linea in lineas:
        print(linea)
    retenidas = sum(1 for linea in lineas if "RETENIDA" in linea)
    if retenidas:
        print(
            f"\n{retenidas} corrida(s) retenida(s): su evidencia existe en disco pero no hay "
            "evento original en la base. Regístralas con record_operational_backtest.py antes "
            "de reclasificarlas; no se inventa el evento que falta."
        )
    print("aplicado" if args.apply else "simulación: repite con --apply para escribir")


if __name__ == "__main__":
    main()
