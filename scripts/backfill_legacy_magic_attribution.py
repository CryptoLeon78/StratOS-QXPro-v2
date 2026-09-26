"""Corrige `Trade.magic_number`/`bot_id` en posiciones históricas ya importadas
que quedaron bajo un magic anterior a la migración de identidad compacta (P2.2).

Por qué hace falta un script aparte (no basta con re-ejecutar
`import_mt5_history_export.py --identity-registry`):

`core/ingest/services/trades.py::ingest_trades` es idempotente por diseño
--- un reenvío de un trade YA CERRADO no toca nada (`ON CONFLICT ...
WHERE close_time IS NULL`), para que un resend nunca pueda mutar en
silencio una atribución ya asentada. Los dos CSV de histórico
(`docs/history_deals_BEPB.csv`, `docs/history_deals_JJTI.csv`) se
importaron el 2026-09-01 SIN `--identity-registry`: sus 2.486/2.041
posiciones quedaron cerradas con el magic legacy tal cual. Repetir esa
importación con el registro no cambia nada: las filas siguen cerradas, la
guarda de idempotencia sigue vigente, y `_get_or_create_artifact` devuelve
el mismo artefacto sin volver a evaluar `legacy_magic_numbers`.

Esto SÍ es el caso legítimo de mutar una fila cerrada: no es un reenvío
del conector, es una traducción de identidad aprobada por el operador
(mismo `legacy_magic_map` que ya usa el importador, misma fuente ---
`runtime/operational/magic_identity/magic_identity_registry.jsonl`,
eventos `ASSIGNED`).

Un `bot_id` ya asignado bajo un magic legacy NO implica que no haya nada
que hacer: `scripts/sync_bot_magics_to_migration.py` corrigió antes el
`magic_number` de 34 `Bot` de legacy a vigente, así que un trade atribuido
ANTES de esa sincronización conserva su `bot_id` correcto pero su propio
`magic_number` sigue siendo el valor viejo (verificado contra el stack
real 2026-09-26: 184 trades BEPB en ese estado exacto, los 21 magics
legacy implicados traducen -- vía este mismo registro -- exactamente al
magic vigente del bot al que ya apuntan). Para esas filas sólo se corrige
`magic_number`; `bot_id` no cambia porque ya era el correcto.

Lo que sí se retiene sin tocar es la verdadera anomalía: un `bot_id` ya
asignado que, tras traducir, apuntaría a un bot *distinto* del que la
fila ya tiene (o a ninguno). Ahí algo más no cuadra -- por ejemplo un EA
que sigue emitiendo deliberadamente su magic legacy en el terminal real
pese a que el registro proponga una traducción -- y se declara para
revisión humana en vez de decidir a ciegas.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

import core.db.models  # noqa: F401 -- registra las tablas en Base.metadata
from core.config import get_settings
from core.db.base import async_session_factory
from core.db.models.accounts import Account
from core.db.models.market import Trade
from core.ingest.services.trades import _resolve_bot_id
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from magic_identity import build_legacy_magic_map


@dataclass
class BackfillReport:
    """Resultado por magic legacy, en tres categorías excluyentes."""

    newly_attributed_by_legacy_magic: dict[int, int] = field(default_factory=dict)
    stale_magic_fixed_by_legacy_magic: dict[int, int] = field(default_factory=dict)
    conflicts_by_legacy_magic: dict[int, int] = field(default_factory=dict)

    @property
    def total_newly_attributed(self) -> int:
        return sum(self.newly_attributed_by_legacy_magic.values())

    @property
    def total_stale_magic_fixed(self) -> int:
        return sum(self.stale_magic_fixed_by_legacy_magic.values())

    @property
    def total_conflicts(self) -> int:
        return sum(self.conflicts_by_legacy_magic.values())

    @property
    def total_translated(self) -> int:
        """Filas cuyo `magic_number` se corrige (atribuidas de nuevo + ya
        atribuidas con campo obsoleto). Los conflictos no cuentan: no se
        tocan."""
        return self.total_newly_attributed + self.total_stale_magic_fixed


async def backfill_legacy_magic_attribution(
    session: AsyncSession,
    *,
    account_id: int,
    legacy_magic_map: dict[int, dict[str, object]],
    apply: bool,
) -> BackfillReport:
    report = BackfillReport()
    if not legacy_magic_map:
        return report

    trades = (
        (
            await session.execute(
                select(Trade).where(
                    Trade.account_id == account_id,
                    Trade.close_time.is_not(None),
                    Trade.magic_number.in_(legacy_magic_map.keys()),
                )
            )
        )
        .scalars()
        .all()
    )

    for trade in trades:
        legacy_magic = trade.magic_number
        new_magic = int(legacy_magic_map[legacy_magic]["magic_number"])
        new_bot_id = await _resolve_bot_id(session, account_id, new_magic)

        if trade.bot_id is None:
            bucket = report.newly_attributed_by_legacy_magic
        elif trade.bot_id == new_bot_id:
            # Ya apuntaba al bot correcto -- lo unico obsoleto es este campo.
            bucket = report.stale_magic_fixed_by_legacy_magic
        else:
            # bot_id ya asignado y NO coincide con a donde traduciria el
            # magic legacy: alguna otra cosa no cuadra (p. ej. un EA que
            # sigue emitiendo su magic legacy de verdad). No se toca.
            report.conflicts_by_legacy_magic[legacy_magic] = (
                report.conflicts_by_legacy_magic.get(legacy_magic, 0) + 1
            )
            continue

        bucket[legacy_magic] = bucket.get(legacy_magic, 0) + 1
        if apply:
            trade.magic_number = new_magic
            if trade.bot_id is None:
                trade.bot_id = new_bot_id

    if apply:
        await session.commit()
    else:
        await session.rollback()
    return report


async def run(args: argparse.Namespace) -> None:
    if get_settings().deployment_profile != "operational":
        raise SystemExit("backfill de histórico permitido sólo en DEPLOYMENT_PROFILE=operational")
    legacy_magic_map = build_legacy_magic_map(args.identity_registry)
    async with async_session_factory() as session:
        account = await session.scalar(select(Account).where(Account.login == args.account_login))
        if account is None:
            raise SystemExit(f"cuenta no registrada: {args.account_login}")
        report = await backfill_legacy_magic_attribution(
            session, account_id=account.id, legacy_magic_map=legacy_magic_map, apply=args.apply
        )
    modo = "APLICADO" if args.apply else "DRY-RUN (repite con --apply para escribir)"
    print(f"[{modo}] cuenta {args.account_login}")
    print(f"  magic_number corregido: {report.total_translated}")
    print(f"    atribuidas de nuevo (bot_id era NULL): {report.total_newly_attributed}")
    print(f"    ya atribuidas, solo magic_number obsoleto: {report.total_stale_magic_fixed}")
    if report.total_conflicts:
        print(
            f"  RETENIDAS por conflicto (bot_id ya apunta a otro bot, revisar a mano): "
            f"{report.total_conflicts}"
        )
        for legacy, count in sorted(report.conflicts_by_legacy_magic.items()):
            print(f"    {legacy} -> {legacy_magic_map[legacy]['magic_number']}: {count} trades")
    print("  detalle por magic legacy traducido:")
    todos = sorted(
        set(report.newly_attributed_by_legacy_magic) | set(report.stale_magic_fixed_by_legacy_magic)
    )
    for legacy in todos:
        nuevo = legacy_magic_map[legacy]["magic_number"]
        nuevas = report.newly_attributed_by_legacy_magic.get(legacy, 0)
        obsoletas = report.stale_magic_fixed_by_legacy_magic.get(legacy, 0)
        print(f"    {legacy} -> {nuevo}: {nuevas} nuevas + {obsoletas} solo campo obsoleto")


def main() -> None:
    import asyncio

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-login", required=True)
    parser.add_argument("--identity-registry", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
