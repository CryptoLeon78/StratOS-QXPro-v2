"""Registra una cuenta observada sin crear ni promocionar bots.

La alta es idempotente y sólo admite el perfil operacional. Un bot F7 exige
además identidad de EA, magic, perfil y sizing verificados; este script no los
infiere a partir del nombre de un fichero ni de un deal aislado.

Admite las dos procedencias con las que StratOS trabaja, y la elección es
explícita porque no significan lo mismo:

- `BROKER_REAL` — cuenta con dinero real, observada estrictamente read-only.
- `BROKER_DEMO` — la cuenta de Incubadora, única ruta con operaciones futuras.

`is_demo` se deriva de la procedencia, no se pide aparte: una cuenta no puede
declararse `BROKER_DEMO` y no ser demo. Los metadatos (login, servidor, moneda)
se leen del terminal, nunca se deducen del nombre de una carpeta.
"""

from __future__ import annotations

import argparse
import asyncio

from core.config import get_settings
from core.db.base import async_session_factory
from core.db.enums import AccountDataOrigin
from core.db.models.accounts import Account
from sqlalchemy import select


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", required=True)
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--broker", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument(
        "--data-origin",
        choices=[AccountDataOrigin.BROKER_REAL.value, AccountDataOrigin.BROKER_DEMO.value],
        default=AccountDataOrigin.BROKER_REAL.value,
        help="procedencia de la cuenta; BROKER_DEMO es la Incubadora",
    )
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def register(args: argparse.Namespace) -> str:
    if get_settings().deployment_profile != "operational":
        raise RuntimeError("alta externa permitida sólo en DEPLOYMENT_PROFILE=operational")
    if len(args.currency) != 3 or not args.currency.isalpha():
        raise ValueError("currency debe ser ISO-4217 de tres letras")
    origen = AccountDataOrigin(args.data_origin)
    if not args.apply:
        return f"planned login={args.login} origin={origen.value}"
    async with async_session_factory() as session:
        account = await session.scalar(select(Account).where(Account.login == args.login))
        if account is None:
            account = Account(
                name=args.account_name,
                broker=args.broker,
                login=args.login,
                server=args.server,
                currency=args.currency.upper(),
                # Derivado de la procedencia: una cuenta no puede declararse BROKER_DEMO
                # y no ser demo. No se pide aparte para que no puedan discrepar.
                is_demo=origen is AccountDataOrigin.BROKER_DEMO,
                data_origin=origen,
                is_active=True,
            )
            session.add(account)
            await session.flush()
            await session.commit()
            return f"created account_id={account.id} origin={origen.value}"
        if account.data_origin != origen:
            raise RuntimeError(
                f"el login {args.login} ya existe como {account.data_origin.value}, no como "
                f"{origen.value}; la procedencia de una cuenta no se reescribe"
            )
        if (account.broker, account.server, account.currency) != (
            args.broker,
            args.server,
            args.currency.upper(),
        ):
            raise RuntimeError("metadatos de cuenta existentes difieren; no se sobrescribe")
        return f"existing account_id={account.id} origin={origen.value}"


def main() -> None:
    try:
        print(asyncio.run(register(parse_args())))
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(f"BLOQUEADO: {exc}") from exc


if __name__ == "__main__":
    main()
