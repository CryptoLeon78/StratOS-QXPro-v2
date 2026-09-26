"""Corrige el bug de alcance de cuenta de A16: `backfill_legacy_magic_attribution.py`
usó `build_legacy_magic_map()` sin filtrar por cuenta, así que aplicó traducciones
aprobadas para UNA cuenta a trades de LA OTRA.

Cada entrada de `magic_identity_registry.jsonl` declara `accounts` (p.ej. `["JJTI"]`),
pero ni ese script ni `regenerate_mn_registry_docs.py` (A13, detectado antes de
aplicarse) lo respetaban. Cuatro pares cuenta/magic quedaron mal escritos en
producción el 2026-09-26:

    BEPB  magic=12  (legacy real: 7508,   aprobado sólo para JJTI)
    JJTI  magic=28  (legacy real: 7507,   aprobado sólo para BEPB)
    JJTI  magic=38  (legacy real: 120726, aprobado sólo para BEPB)
    JJTI  magic=40  (legacy real: 333335, aprobado sólo para BEPB)

Verificado antes de escribir esto (no se adivina):
- Las 91 filas afectadas tienen `bot_id IS NULL` -- ninguna atribución cruzada
  ocurrió, porque tampoco existe un `Bot` con esos magics para la cuenta
  equivocada. El daño es sólo el campo `magic_number`.
- Ninguna aparece en el CSV histórico sellado (`runtime/operational/history/history_deals_*.csv`):
  llegaron por el conector en vivo después del 2026-09-01, probablemente de
  los EAs rezagados que siguen emitiendo su magic legacy (`backlog A25`).
- Cada magic objetivo tiene una única fuente legacy posible en TODO el
  registro (`build_legacy_magic_map` es 1:1 por magic), así que la reversión
  no es ambigua.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import core.db.models  # noqa: F401 -- registra las tablas en Base.metadata
from core.config import get_settings
from core.db.base import async_session_factory
from core.db.models.accounts import Account
from core.db.models.market import Trade
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class CorreccionConocida:
    account_login: str
    wrong_magic: int
    correct_legacy_magic: int


CORRECCIONES = (
    CorreccionConocida("4000055216", 12, 7508),
    CorreccionConocida("4000059903", 28, 7507),
    CorreccionConocida("4000059903", 38, 120726),
    CorreccionConocida("4000059903", 40, 333335),
)


async def revert_one(
    session: AsyncSession, account_id: int, c: CorreccionConocida, apply: bool
) -> int:
    trades = (
        (
            await session.execute(
                select(Trade).where(
                    Trade.account_id == account_id,
                    Trade.magic_number == c.wrong_magic,
                    Trade.bot_id.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for trade in trades:
        if apply:
            trade.magic_number = c.correct_legacy_magic
    return len(trades)


async def run(apply: bool) -> None:
    if get_settings().deployment_profile != "operational":
        raise SystemExit("corrección permitida sólo en DEPLOYMENT_PROFILE=operational")
    async with async_session_factory() as session:
        for c in CORRECCIONES:
            account = await session.scalar(select(Account).where(Account.login == c.account_login))
            if account is None:
                raise SystemExit(f"cuenta no registrada: {c.account_login}")
            n = await revert_one(session, account.id, c, apply)
            modo = "APLICADO" if apply else "DRY-RUN"
            print(
                f"[{modo}] cuenta {c.account_login}: {n} trades con magic={c.wrong_magic} "
                f"revertidos a {c.correct_legacy_magic}"
            )
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
