"""Corrige el SEGUNDO bug (introducido por `fix_a16_cross_account_magic_bug.py`
al aplicarse): su `revert_one()` seleccionaba con
`Trade.magic_number == 40 AND Trade.bot_id.is_(None)` para JJTI, sin
distinguir por ticket. Esa selección no sólo capturó las filas realmente
mal-escritas por A16 (magic 40 aplicado por error a JJTI, legacy real
333335), sino tambien 15 trades genuinamente NATIVOS de JJTI que ya
estaban en magic=40 desde antes de que A16 existiera -- nunca fueron
tocados por el bug original, así que revertirlos a 333335 fue un error
mío, no una reversión de nada.

Verificado antes de escribir esto (no se adivina): los 15 `ticket_mt5`
listados abajo aparecen en `runtime/operational/history/history_deals_JJTI.csv` (sellado,
`ImportArtifact` id=47) con magic=40 exacto -- el CSV es anterior a
cualquiera de los dos bugs, así que su valor es el histórico real.

Alcance deliberadamente estrecho: por `ticket_mt5` explícito, no por
`magic_number`, para no repetir el mismo error de selección amplia.
"""

from __future__ import annotations

import argparse

import core.db.models  # noqa: F401 -- registra las tablas en Base.metadata
from core.config import get_settings
from core.db.base import async_session_factory
from core.db.models.accounts import Account
from core.db.models.market import Trade
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

JJTI_LOGIN = "4000059903"
MAGIC_NATIVO_CORRECTO = 40
MAGIC_MAL_REVERTIDO = 333335

TICKETS_NATIVOS_MAL_REVERTIDOS = (
    99051505, 99101512, 99541025, 99782679, 99854449,
    100447280, 100513570, 101036006, 101057571, 101102794,
    101191639, 101283273, 102853273, 102974179, 103195260,
)


async def run(apply: bool) -> None:
    if get_settings().deployment_profile != "operational":
        raise SystemExit("corrección permitida sólo en DEPLOYMENT_PROFILE=operational")
    async with async_session_factory() as session:
        account = await session.scalar(select(Account).where(Account.login == JJTI_LOGIN))
        if account is None:
            raise SystemExit(f"cuenta no registrada: {JJTI_LOGIN}")

        trades = (
            (
                await session.execute(
                    select(Trade).where(
                        Trade.account_id == account.id,
                        Trade.ticket_mt5.in_(TICKETS_NATIVOS_MAL_REVERTIDOS),
                        Trade.magic_number == MAGIC_MAL_REVERTIDO,
                    )
                )
            )
            .scalars()
            .all()
        )

        vistos = {t.ticket_mt5 for t in trades}
        faltantes = set(TICKETS_NATIVOS_MAL_REVERTIDOS) - vistos
        if faltantes:
            print(
                f"AVISO: {len(faltantes)} tickets esperados no encontrados con "
                f"magic={MAGIC_MAL_REVERTIDO}: {sorted(faltantes)}"
            )

        modo = "APLICADO" if apply else "DRY-RUN (repite con --apply para escribir)"
        print(
            f"[{modo}] JJTI ({JJTI_LOGIN}): {len(trades)} filas "
            f"magic={MAGIC_MAL_REVERTIDO} -> {MAGIC_NATIVO_CORRECTO}"
        )
        for t in sorted(trades, key=lambda t: t.ticket_mt5):
            print(f"    ticket={t.ticket_mt5} open_time={t.open_time} bot_id={t.bot_id}")
            if apply:
                t.magic_number = MAGIC_NATIVO_CORRECTO

        if apply:
            await session.commit()
        else:
            await session.rollback()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    import asyncio

    asyncio.run(run(args.apply))


if __name__ == "__main__":
    main()
