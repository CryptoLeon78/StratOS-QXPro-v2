"""Registra UNA cuenta real y, opcionalmente, UN bot real (G11: primera
puesta en marcha real, Nodo A local) -- sin correr `scripts/seed.py`, que
fabrica 32 bots sinteticos. Genérico y parametrizado por CLI: ningun dato
real (login, magic number) queda hardcodeado en el repo.

No destructivo: falla si `Account.login` ya existe en vez de duplicar o
sobrescribir (mismo criterio que `import_instrument_specs.py`/
`backfill_r_multiple.py` de G10 -- re-ejecutable con seguridad solo cuando
la fila todavia no existe).

Uso (solo cuenta):
    PYTHONPATH=core-engine/src python scripts/register_real_account_bot.py \
        --login 3000080873 --broker Darwinex --server Darwinex-Demo \
        --currency USD --demo --name "Darwinex Demo Incubacion"

Uso (cuenta + bot):
    PYTHONPATH=core-engine/src python scripts/register_real_account_bot.py \
        --login 3000080873 --broker Darwinex --server Darwinex-Demo \
        --currency USD --demo --name "Darwinex Demo Incubacion" \
        --magic 300000024 --bot-name "XAUUSD H4 BreakoutStop" \
        --market XAUUSD --timeframe H4 --profile TREND --role CHAMPION \
        --pipeline-phase F1 --capital-pct 10 --risk-pct 0.5
"""

import argparse
import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import core.db.models  # noqa: F401 -- registra las tablas en Base.metadata
from core.db.base import async_session_factory
from core.db.enums import BotProfile, BotRole, PipelinePhase
from core.db.models.accounts import Account, Bot
from sqlalchemy import select


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    account = parser.add_argument_group("cuenta")
    account.add_argument("--login", required=True, help="Account.login (numero de cuenta MT5)")
    account.add_argument("--broker", required=True)
    account.add_argument("--server", required=True, help="p.ej. Darwinex-Demo")
    account.add_argument("--currency", required=True, help="ISO 3 letras, p.ej. USD")
    account.add_argument("--name", required=True, help="Nombre descriptivo de la cuenta")
    demo_group = account.add_mutually_exclusive_group(required=True)
    demo_group.add_argument("--demo", action="store_true", dest="is_demo")
    demo_group.add_argument("--real", action="store_false", dest="is_demo")

    bot = parser.add_argument_group("bot (opcional -- omitir para registrar solo la cuenta)")
    bot.add_argument("--magic", type=int, default=None, help="magic_number del EA real")
    bot.add_argument("--bot-name", default=None)
    bot.add_argument("--market", default=None)
    bot.add_argument("--timeframe", default=None)
    bot.add_argument("--profile", choices=[p.value for p in BotProfile], default=None)
    bot.add_argument("--role", choices=[r.value for r in BotRole], default=BotRole.CHAMPION.value)
    bot.add_argument(
        "--pipeline-phase",
        choices=[p.value for p in PipelinePhase],
        default=PipelinePhase.F1.value,
    )
    bot.add_argument("--capital-pct", type=Decimal, default=None)
    bot.add_argument("--risk-pct", type=Decimal, default=None)
    bot.add_argument(
        "--ea-required-version",
        default=None,
        help="Versión exacta esperada del reporter EA; omitir = no verificable",
    )

    args = parser.parse_args(argv)
    bot_fields = [args.magic, args.bot_name, args.market, args.timeframe, args.profile]
    if any(f is not None for f in bot_fields) and not all(f is not None for f in bot_fields):
        parser.error(
            "--magic/--bot-name/--market/--timeframe/--profile van juntos: "
            "o se dan los 5 (registra el bot) o ninguno (solo la cuenta)"
        )
    if args.magic is not None and (args.capital_pct is None or args.risk_pct is None):
        parser.error("--capital-pct y --risk-pct son obligatorios al registrar un bot")
    return args


async def register(args: argparse.Namespace) -> None:
    async with async_session_factory() as session:
        existing = await session.scalar(select(Account).where(Account.login == args.login))
        if existing is not None:
            raise SystemExit(
                f"Account.login={args.login!r} ya existe (id={existing.id}) -- "
                "este script nunca duplica ni sobrescribe. Usa el id existente a mano si "
                "hace falta añadir un Bot nuevo bajo esa cuenta."
            )

        account = Account(
            name=args.name,
            broker=args.broker,
            login=args.login,
            server=args.server,
            currency=args.currency.upper(),
            is_demo=args.is_demo,
            is_active=True,
        )
        session.add(account)
        await session.flush()  # asigna account.id sin cerrar la transaccion

        if args.magic is not None:
            now = datetime.now(UTC)
            bot = Bot(
                account_id=account.id,
                magic_number=args.magic,
                name=args.bot_name,
                market=args.market,
                timeframe=args.timeframe,
                profile=BotProfile(args.profile),
                role=BotRole(args.role),
                pipeline_phase=PipelinePhase(args.pipeline_phase),
                entered_state_at=now,
                capital_allocated_pct=args.capital_pct,
                risk_per_trade_pct=args.risk_pct,
                created_at=now,
                ea_required_version=args.ea_required_version,
            )
            session.add(bot)

        await session.commit()
        print(f"Account id={account.id} login={account.login!r} registrada.")
        if args.magic is not None:
            print(f"Bot magic_number={args.magic} registrado bajo account_id={account.id}.")


def main() -> None:
    args = _parse_args()
    asyncio.run(register(args))


if __name__ == "__main__":
    main()
