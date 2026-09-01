"""Alta administrativa G12: sólo DEMO, append-only y con candidatos F3 reales."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

import core.db.models  # noqa: F401
from core.db.base import async_session_factory
from core.db.enums import ActorType, BotProfile, BotRole, PipelinePhase
from core.db.models.accounts import Account, Bot
from core.db.models.pipeline import PipelineCandidate
from core.services.admin_imports import import_sqx_baseline
from core.services.pipeline_history import record_phase_transition


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--login", required=True)
    parser.add_argument("--broker", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--capital-allocated-pct", required=True, type=Decimal)
    parser.add_argument("--risk-per-trade-pct", required=True, type=Decimal)
    parser.add_argument("--dd-contract-pct", required=True, type=Decimal)
    parser.add_argument(
        "--allow-withheld",
        action="store_true",
        help=(
            "permite dar de alta exclusivamente los READY cuando el manifiesto "
            "conserva candidatos WITHHELD con causa explícita; nunca los sustituye"
        ),
    )
    parser.add_argument("--apply", action="store_true", help="sin esta bandera sólo valida el manifiesto")
    return parser.parse_args()


def _ready_candidates(
    manifest: dict[str, object], *, allow_withheld: bool = False
) -> list[dict[str, object]]:
    candidates = manifest.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("manifest sin candidates")
    if len(candidates) != 16:
        raise ValueError(f"alta bloqueada: se esperaban 16 candidatos y hay {len(candidates)}")
    if not all(isinstance(item, dict) for item in candidates):
        raise ValueError("manifest con candidato inválido")
    invalid_status = [item for item in candidates if item.get("status") not in {"READY", "WITHHELD"}]
    if invalid_status:
        names = ", ".join(str(item.get("strategy_name")) for item in invalid_status)
        raise ValueError(f"alta bloqueada: estado de candidato inválido: {names}")
    withheld = [item for item in candidates if item.get("status") == "WITHHELD"]
    if withheld and not allow_withheld:
        names = ", ".join(str(item.get("strategy_name")) for item in withheld)
        raise ValueError(f"alta bloqueada: candidatos retenidos: {names}")
    ready = [item for item in candidates if item.get("status") == "READY"]
    if not ready:
        raise ValueError("alta bloqueada: no hay candidatos READY")
    return ready


async def bootstrap(args: argparse.Namespace) -> None:
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    candidates = _ready_candidates(manifest, allow_withheld=args.allow_withheld)
    total = len(manifest["candidates"])
    withheld_count = total - len(candidates)
    if not args.apply:
        scope = (
            f"{len(candidates)} READY y {withheld_count} WITHHELD retenidos"
            if withheld_count
            else "16 candidatos READY"
        )
        print(f"Validación correcta: {scope}. Añade --apply para escribir en G12.")
        return
    if min(args.capital_allocated_pct, args.risk_per_trade_pct, args.dd_contract_pct) <= 0:
        raise ValueError("capital, riesgo y contrato DD deben ser positivos y explícitos")
    async with async_session_factory() as session:
        existing = await session.scalar(select(Account).where(Account.login == args.login))
        if existing is not None:
            raise ValueError(f"login demo ya registrado: account_id={existing.id}; G12 no sobrescribe")
        account = Account(
            name=args.name,
            broker=args.broker,
            login=args.login,
            server=args.server,
            currency=args.currency.upper(),
            is_demo=True,
            is_active=True,
        )
        session.add(account)
        await session.flush()
        for item in candidates:
            now = datetime.now(UTC)
            bot = Bot(
                account_id=account.id,
                magic_number=int(item["magic_number"]),
                name=str(item["strategy_name"]),
                # Debe coincidir exactamente con el símbolo Darwinex que el
                # parser SQX144 acaba de verificar; es la clave usada para
                # asociar trades/telemetría, no un alias editorial.
                market=str(item["sqx"]["symbol"]),
                timeframe=str(item["timeframe"]),
                profile=BotProfile(str(item["profile"])),
                role=BotRole.CHALLENGER,
                pipeline_phase=PipelinePhase.F3,
                entered_state_at=now,
                capital_allocated_pct=args.capital_allocated_pct,
                risk_per_trade_pct=args.risk_per_trade_pct,
                created_at=now,
                ea_required_version=str(manifest["ea_required_version"]),
            )
            session.add(bot)
            await session.flush()
            await import_sqx_baseline(
                session,
                bot_id=bot.id,
                path=Path(str(item["sqx_path"])),
                dd_contract_pct=args.dd_contract_pct,
            )
            candidate = PipelineCandidate(
                bot_id=bot.id,
                current_phase=PipelinePhase.F3,
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
                to_phase=PipelinePhase.F3,
                actor=ActorType.HUMAN,
                reason="G12_DEMO_ONBOARDING_VERIFIED_SQX_SURVIVOR",
            )
        await session.commit()
    print(
        "G12 DEMO: cuenta y "
        f"{len(candidates)} bots READY registrados; baselines y transiciones append-only creados. "
        f"Retenidos sin sustituir: {withheld_count}."
    )


def main() -> None:
    asyncio.run(bootstrap(_parse_args()))


if __name__ == "__main__":
    main()
