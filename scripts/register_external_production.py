"""Alta administrativa idempotente de un EA ya observado en producción.

No contacta MT5, no escribe en el VPS y no convierte el origen externo en
una promoción automática: el candidato queda F7 con transición explícita.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import core.db.models  # noqa: F401
from core.config import get_settings
from core.db.base import async_session_factory
from core.db.enums import (
    AccountDataOrigin,
    ActorType,
    BotOriginKind,
    BotProfile,
    BotRole,
    PipelinePhase,
)
from core.db.models.accounts import Account, Bot
from core.db.models.pipeline import PipelineCandidate
from core.services.admin_imports import import_sqx_baseline
from core.services.pipeline_history import record_phase_transition
from sqlalchemy import select


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", required=True)
    parser.add_argument("--broker", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument("--account-name", required=True)
    parser.add_argument("--magic", required=True, type=int)
    parser.add_argument("--bot-name", required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--profile", choices=[item.value for item in BotProfile])
    parser.add_argument("--capital-pct", type=Decimal)
    parser.add_argument("--risk-pct", type=Decimal)
    parser.add_argument("--sqx", type=Path)
    parser.add_argument("--dd-contract-pct", type=Decimal)
    return parser.parse_args()


def _validate_internal_contract(args: argparse.Namespace) -> bool:
    """Return whether the external record carries a declared internal contract.

    An external observation is valid with all three fields absent. Supplying
    one of them is an explicit claim, so it must be complete and positive.
    """

    internal_contract = (args.profile, args.capital_pct, args.risk_pct)
    if any(value is not None for value in internal_contract) and any(
        value is None for value in internal_contract
    ):
        raise SystemExit(
            "--profile, --capital-pct y --risk-pct se declaran juntos o se omiten "
            "para una observación externa sin contrato interno"
        )
    if args.capital_pct is not None and min(args.capital_pct, args.risk_pct) <= 0:
        raise SystemExit("capital y riesgo deben ser positivos")
    return args.profile is not None


async def register(args: argparse.Namespace) -> None:
    if get_settings().deployment_profile != "operational":
        raise SystemExit("alta F7 externa permitida sólo en DEPLOYMENT_PROFILE=operational")
    if (args.sqx is None) != (args.dd_contract_pct is None):
        raise SystemExit("--sqx y --dd-contract-pct se usan juntos o se omiten juntos")
    has_internal_contract = _validate_internal_contract(args)
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
        elif account.data_origin != AccountDataOrigin.BROKER_REAL:
            raise SystemExit("login existente no pertenece a BROKER_REAL; no se sobrescribe")

        existing = await session.scalar(
            select(Bot).where(Bot.account_id == account.id, Bot.magic_number == args.magic)
        )
        if existing is not None:
            print(f"existing_bot_id={existing.id} account_id={account.id}")
            return
        now = datetime.now(UTC)
        bot = Bot(
            account_id=account.id,
            magic_number=args.magic,
            name=args.bot_name,
            market=args.market,
            timeframe=args.timeframe,
            profile=BotProfile(args.profile) if args.profile is not None else None,
            role=BotRole.CHAMPION,
            origin_kind=BotOriginKind.EXTERNAL_PRODUCTION,
            pipeline_phase=PipelinePhase.F7,
            entered_state_at=now,
            capital_allocated_pct=args.capital_pct,
            risk_per_trade_pct=args.risk_pct,
            created_at=now,
        )
        session.add(bot)
        await session.flush()
        if args.sqx is not None:
            await import_sqx_baseline(
                session, bot_id=bot.id, path=args.sqx, dd_contract_pct=args.dd_contract_pct
            )
        candidate = PipelineCandidate(
            bot_id=bot.id,
            current_phase=PipelinePhase.F7,
            entered_phase_at=now,
            incubation_days=0,
            oos_trades=0,
        )
        session.add(candidate)
        await session.flush()
        record_phase_transition(
            session,
            candidate,
            from_phase=None,
            to_phase=PipelinePhase.F7,
            actor=ActorType.HUMAN,
            reason="EXTERNAL_PRODUCTION_REGISTERED",
        )
        await session.commit()
        contract_state = "DECLARED" if has_internal_contract else "NOT_DECLARED"
        print(
            f"account_id={account.id} bot_id={bot.id} candidate_id={candidate.id} "
            f"external_contract={contract_state}"
        )


if __name__ == "__main__":
    asyncio.run(register(_args()))
