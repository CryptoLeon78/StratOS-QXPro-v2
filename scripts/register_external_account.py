"""Registra una cuenta real observada sin crear ni promocionar bots.

La alta es idempotente y sólo admite el perfil operacional. Un bot F7 exige
además identidad de EA, magic, perfil y sizing verificados; este script no los
infiere a partir del nombre de un fichero ni de un deal aislado.
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from core.config import get_settings
from core.db.base import async_session_factory
from core.db.enums import AccountDataOrigin
from core.db.models.accounts import Account


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", required=True)
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--broker", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def register(args: argparse.Namespace) -> str:
    if get_settings().deployment_profile != "operational":
        raise RuntimeError("alta externa permitida sólo en DEPLOYMENT_PROFILE=operational")
    if len(args.currency) != 3 or not args.currency.isalpha():
        raise ValueError("currency debe ser ISO-4217 de tres letras")
    if not args.apply:
        return f"planned login={args.login} origin=BROKER_REAL"
    async with async_session_factory() as session:
        account = await session.scalar(select(Account).where(Account.login == args.login))
        if account is None:
            account = Account(
                name=args.account_name,
                broker=args.broker,
                login=args.login,
                server=args.server,
                currency=args.currency.upper(),
                is_demo=False,
                data_origin=AccountDataOrigin.BROKER_REAL,
                is_active=True,
            )
            session.add(account)
            await session.flush()
            await session.commit()
            return f"created account_id={account.id} origin=BROKER_REAL"
        if account.data_origin != AccountDataOrigin.BROKER_REAL:
            raise RuntimeError("login existente no es BROKER_REAL; no se sobrescribe")
        if (account.broker, account.server, account.currency) != (
            args.broker,
            args.server,
            args.currency.upper(),
        ):
            raise RuntimeError("metadatos de cuenta existentes difieren; no se sobrescribe")
        return f"existing account_id={account.id} origin=BROKER_REAL"


def main() -> None:
    try:
        print(asyncio.run(register(parse_args())))
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(f"BLOQUEADO: {exc}") from exc


if __name__ == "__main__":
    main()
