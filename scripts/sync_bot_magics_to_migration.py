"""Alinea el `magic_number` de los bots F7 con la identidad vigente tras la migración MN.

Los 40 bots `EXTERNAL_PRODUCTION` se dieron de alta el 2026-08-31 con los magics que los EAs
emitían **entonces**. La migración de identidad compacta (G13-18/G13-20) se aplicó después en
los terminales, así que desde el 2026-09-01 esos mismos EAs emiten su magic **nuevo** y la
ingesta ya no los reconoce: cada operación nueva de un EA migrado entra huérfana.

No son los 38 trades que hay hoy: es que **la atribución está rota hacia adelante**. Sin esto,
la telemetría real de JJTI y BEPB deja de asociarse a ningún bot de forma permanente.

Qué hace, y qué deliberadamente no hace:

- Actualiza `Bot.magic_number` del legacy al vigente **sólo** cuando el registro append-only
  aprobado declara esa correspondencia, la cuenta coincide y el magic nuevo no está ya en uso
  en esa cuenta. Cualquier otro caso se retiene y se informa.
- **No toca `Trade.bot_id`.** Los trades ya atribuidos conservan su `bot_id`: la atribución
  ocurrió con la identidad válida en su momento y reescribirla sería falsear el histórico. Los
  trades históricos con magic legacy que todavía no se hayan ingerido se normalizan en la
  ingesta con `import_mt5_history_export.py --identity-registry`.
- **No contacta MT5 ni modifica ningún EA.** La migración ya está aplicada y confirmada por el
  operador; esto sólo hace que la base refleje lo que el terminal ya emite.

Uso:
    python scripts/sync_bot_magics_to_migration.py --identity-registry <registry.jsonl>
    (añadir --apply para escribir; sin él sólo informa)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "core-engine" / "src"))

from magic_identity import build_legacy_magic_map  # noqa: E402


def accounts_of(entry: dict[str, Any]) -> list[str]:
    return [str(label) for label in entry.get("accounts") or []]


async def sync(registry_path: Path, apply: bool, reattribute_orphans: bool = False) -> list[str]:
    from core.db.base import async_session_factory
    from core.db.models.accounts import Account, Bot
    from sqlalchemy import select

    legacy_map = build_legacy_magic_map(registry_path)
    lineas: list[str] = []

    async with async_session_factory() as session:
        cuentas = {a.id: a for a in (await session.execute(select(Account))).scalars().all()}
        bots = (await session.execute(select(Bot))).scalars().all()
        magics_por_cuenta: dict[int, set[int]] = {}
        for bot in bots:
            magics_por_cuenta.setdefault(bot.account_id, set()).add(bot.magic_number)

        cambios = 0
        for bot in sorted(bots, key=lambda b: (b.account_id, b.magic_number)):
            destino = legacy_map.get(bot.magic_number)
            if destino is None:
                continue
            nuevo = int(destino["magic_number"])
            cuenta = cuentas.get(bot.account_id)
            etiquetas = accounts_of(destino)
            # La asignación declara a qué cuenta pertenece (por la etiqueta corta que usa el
            # operador, BEPB/JJTI). No se migra un bot cuya cuenta no aparece en la evidencia,
            # aunque el magic legacy coincida: dos cuentas pueden reutilizar un magic.
            nombre_cuenta = (cuenta.name if cuenta is not None else "") or ""
            if etiquetas and not any(
                etiqueta.upper() in nombre_cuenta.upper() for etiqueta in etiquetas
            ):
                lineas.append(
                    f"  RETENIDO bot {bot.id} ({bot.name}): magic {bot.magic_number} pertenece "
                    f"a {etiquetas}, y la cuenta {bot.account_id} es {nombre_cuenta!r}"
                )
                continue
            if nuevo in magics_por_cuenta.get(bot.account_id, set()):
                lineas.append(
                    f"  RETENIDO bot {bot.id} ({bot.name}): el magic {nuevo} ya está en uso "
                    f"en la cuenta {bot.account_id}"
                )
                continue
            lineas.append(
                f"  bot {bot.id} {bot.name}: {bot.magic_number} -> {nuevo} "
                f"({destino['comment_identity']})"
            )
            cambios += 1
            if apply:
                magics_por_cuenta[bot.account_id].discard(bot.magic_number)
                magics_por_cuenta[bot.account_id].add(nuevo)
                bot.magic_number = nuevo
        if apply and cambios:
            await session.commit()
        lineas.append(f"  -- {cambios} bot(s) {'actualizados' if apply else 'a actualizar'}")

        if reattribute_orphans:
            lineas.extend(await _reattribute(session, apply))
    return lineas


async def _reattribute(session: Any, apply: bool) -> list[str]:
    """Completa el `bot_id` de trades que quedaron huérfanos por el desfase de magic.

    Estos trades entraron mientras el bot tenía todavía su magic anterior, así que la ingesta
    no encontró a quién atribuirlos. Ahora el magic del bot coincide, pero la deduplicación
    por `ticket_mt5` impide que una reimportación los corrija.

    Rellenar un `bot_id` que estaba a NULL **completa una ausencia**, no reescribe una
    atribución: no hay ningún caso en que se cambie el bot de un trade ya atribuido. La
    condición exige coincidencia exacta de cuenta y magic, y `magic_number <> 0` para no
    tocar las operaciones sin EA, que son ausencia declarada.
    """
    from sqlalchemy import text

    consulta = text(
        """
        UPDATE trade t
           SET bot_id = b.id
          FROM bot b
         WHERE t.bot_id IS NULL
           AND t.magic_number <> 0
           AND b.account_id = t.account_id
           AND b.magic_number = t.magic_number
        """
    )
    contar = text(
        """
        SELECT count(*) FROM trade t JOIN bot b
            ON b.account_id = t.account_id AND b.magic_number = t.magic_number
         WHERE t.bot_id IS NULL AND t.magic_number <> 0
        """
    )
    pendientes = (await session.execute(contar)).scalar_one()
    if apply and pendientes:
        await session.execute(consulta)
        await session.commit()
    verbo = "reatribuidos" if apply else "reatribuibles"
    return [f"  -- {pendientes} trade(s) huérfano(s) {verbo}"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity-registry", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--reattribute-orphans",
        action="store_true",
        help=(
            "completa el bot_id de los trades que quedaron huérfanos por el desfase "
            "de magic; nunca cambia una atribución existente"
        ),
    )
    args = parser.parse_args()

    from core.config import get_settings

    if get_settings().deployment_profile != "operational":
        raise SystemExit("sólo en DEPLOYMENT_PROFILE=operational")

    for linea in asyncio.run(
        sync(args.identity_registry, args.apply, args.reattribute_orphans)
    ):
        print(linea)
    print("aplicado" if args.apply else "simulación: repite con --apply para escribir")


if __name__ == "__main__":
    main()
