"""Corrige el magic/comment legacy en `docs/registro_{BEPB,JJTI}_MN_bots_real_mt5_vps.md`
usando el registro append-only de identidad (mismo `legacy_magic_map` que ya usa
`import_mt5_history_export.py` y `backfill_legacy_magic_attribution.py`).

Por qué hacía falta (A13): ambos documentos se transcribieron a mano desde el
diálogo de propiedades del EA en MT5, con el `CustomComment`/`MagicNumber`
**legacy** (previos a la migración de identidad compacta). Los deals reales y
el post-scan demuestran que lo desplegado usa los magics nuevos, así que eran
los documentos los que estaban desactualizados. Mantenerlos a mano garantiza
que se desincronicen de nuevo en la próxima migración; regenerarlos desde el
registro no.

Qué toca y qué no: sólo el par `<label>_MN<magic>` / `MagicNumber: <magic>`
de cada estrategia, y sólo si su magic **legacy** está en el registro
aprobado. El resto de la línea (parámetros de entrada, gestión de capital,
nombre de la estrategia, símbolo/timeframe) no se toca -- ese detalle no está
en el registro de identidad y no se puede regenerar sin inventarlo.

Un magic que no aparece en el registro se deja exactamente como está y se
declara en el reporte, nunca se adivina: puede ser un magic que nunca
necesitó traducción (ya era el vigente) o uno fuera del lote de 40 aprobado
(`backlog A12`) -- distinguir cuál de los dos es cada caso queda fuera de
este script.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

from magic_identity import build_legacy_magic_map, entry_matches_account

# BEPB: una sola linea por estrategia, campos separados por " | ".
_PATRON_BEPB = re.compile(
    r"CustomComment:\s*(?P<label>.+?)_MN(?P<magic>\d+)\s*\|\s*MagicNumber:\s*(?P<magic2>\d+)"
)

# JJTI: dos lineas -- "Identificadores: <label>_MN<magic>" seguida de
# "MagicNumber: <magic>", ambas dentro del mismo bloque de estrategia.
_PATRON_JJTI = re.compile(
    r"Identificadores:\s*(?P<label>.+?)_MN(?P<magic>\d+)\s*\n"
    r"MagicNumber:\s*(?P<magic2>\d+)"
)


@dataclass
class RegenerateReport:
    translated: dict[int, str] = field(default_factory=dict)  # legacy -> comment_identity nuevo
    left_as_is: list[int] = field(default_factory=list)  # legacy magics vistos, no en el registro
    inconsistent: list[tuple[int, int]] = field(default_factory=list)  # comment vs MagicNumber

    @property
    def total_seen(self) -> int:
        return len(self.translated) + len(self.left_as_is) + len(self.inconsistent)


def _translate(
    texto: str, patron: re.Pattern[str], legacy_magic_map: dict[int, dict[str, object]]
) -> tuple[str, RegenerateReport]:
    reporte = RegenerateReport()

    def reemplazo(m: re.Match[str]) -> str:
        legacy = int(m.group("magic"))
        legacy2 = int(m.group("magic2"))
        if legacy != legacy2:
            # El propio documento se contradice entre el comment y el campo
            # MagicNumber: no se decide cual es el bueno, se retiene entero.
            reporte.inconsistent.append((legacy, legacy2))
            return m.group(0)
        entrada = legacy_magic_map.get(legacy)
        if entrada is None:
            reporte.left_as_is.append(legacy)
            return m.group(0)
        nuevo_comment = str(entrada["comment_identity"])
        nuevo_magic = int(entrada["magic_number"])
        reporte.translated[legacy] = nuevo_comment
        return (
            m.group(0)
            .replace(f"{m.group('label')}_MN{legacy}", nuevo_comment)
            .replace(f"MagicNumber: {legacy2}", f"MagicNumber: {nuevo_magic}", 1)
        )

    nuevo_texto = patron.sub(reemplazo, texto)
    return nuevo_texto, reporte


def regenerate_bepb(
    texto: str, legacy_magic_map: dict[int, dict[str, object]]
) -> tuple[str, RegenerateReport]:
    return _translate(texto, _PATRON_BEPB, legacy_magic_map)


def regenerate_jjti(
    texto: str, legacy_magic_map: dict[int, dict[str, object]]
) -> tuple[str, RegenerateReport]:
    return _translate(texto, _PATRON_JJTI, legacy_magic_map)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity-registry", type=Path, required=True)
    parser.add_argument(
        "--docs-dir", type=Path, default=Path("docs"), help="carpeta con los dos .md"
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    legacy_magic_map_global = build_legacy_magic_map(args.identity_registry)

    for cuenta, patron_fn in (("BEPB", regenerate_bepb), ("JJTI", regenerate_jjti)):
        ruta = args.docs_dir / f"registro_{cuenta}_MN_bots_real_mt5_vps.md"
        texto = ruta.read_text(encoding="utf-8")
        # Incidente A16 (2026-09-26): cada entrada del registro aplica solo a
        # las cuentas que declara `accounts` -- aplicar el mapa global sin
        # filtrar traduce magics aprobados para UNA cuenta en el documento
        # de LA OTRA.
        legacy_magic_map = {
            legacy: entry
            for legacy, entry in legacy_magic_map_global.items()
            if entry_matches_account(entry, cuenta)
        }
        nuevo_texto, reporte = patron_fn(texto, legacy_magic_map)

        modo = "APLICADO" if args.apply else "DRY-RUN (repite con --apply para escribir)"
        print(f"[{modo}] {ruta.name}")
        print(f"  entradas vistas: {reporte.total_seen}")
        print(f"  traducidas: {len(reporte.translated)}")
        print(f"  sin cambio (magic no esta en el registro): {len(reporte.left_as_is)}")
        if reporte.inconsistent:
            print(
                f"  INCONSISTENTES (comment != MagicNumber en el propio doc, retenidas): "
                f"{reporte.inconsistent}"
            )
        for legacy, nuevo in sorted(reporte.translated.items()):
            print(f"    MN{legacy} -> {nuevo}")

        if args.apply and nuevo_texto != texto:
            ruta.write_text(nuevo_texto, encoding="utf-8")


if __name__ == "__main__":
    main()
