"""Da de alta en Incubadora los EAs que ya operan en su terminal y StratOS no tiene.

Decisión del operador (2026-10-14, G14-07): lo instalado en la Incubadora es lo
que debe verse, sin pasar de nuevo por la puerta de admisión. Cada alta deja una
observación de inventario con el SHA-256 del `.ex5` real, el bot en F5
(`origin_kind=INCUBATION`) con el contrato interno que dio el operador y su
transición de fase. Nunca contacta MT5.

Uso:
    python scripts/register_incubator_observed_bots.py --manifest m.json --result r.json [--apply]

Manifiesto: {"account_login": "...", "records": [{"magic_number", "name",
"comment_identity", "symbol", "timeframe", "ea_relative_path", "ea_sha256",
"profile", "capital_allocated_pct", "risk_per_trade_pct"}]}
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path, PureWindowsPath
from typing import Any

_SHA256 = re.compile(r"[0-9a-f]{64}")
_REQUIRED = (
    "magic_number",
    "name",
    "comment_identity",
    "symbol",
    "timeframe",
    "ea_relative_path",
    "ea_sha256",
    "profile",
    "capital_allocated_pct",
    "risk_per_trade_pct",
)


@dataclass(frozen=True)
class IncubatorRecord:
    magic_number: int
    name: str
    comment_identity: str
    symbol: str
    timeframe: str
    ea_relative_path: str
    ea_sha256: str
    profile: str
    capital_allocated_pct: Decimal
    risk_per_trade_pct: Decimal


def load_manifest(path: Path, profiles: set[str]) -> tuple[str, list[IncubatorRecord]]:
    """Valida el manifiesto entero antes de escribir nada (fail-closed)."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    login = str(payload["account_login"])
    records: list[IncubatorRecord] = []
    for raw in payload["records"]:
        missing = [key for key in _REQUIRED if raw.get(key) in (None, "")]
        if missing:
            raise SystemExit(f"magic={raw.get('magic_number')}: faltan {missing}")
        if not _SHA256.fullmatch(str(raw["ea_sha256"])):
            raise SystemExit(f"magic={raw['magic_number']}: sha256 invalido")
        if str(raw["profile"]) not in profiles:
            raise SystemExit(f"magic={raw['magic_number']}: perfil desconocido {raw['profile']}")
        if PureWindowsPath(str(raw["ea_relative_path"])).stem != str(raw["name"]):
            raise SystemExit(f"magic={raw['magic_number']}: el .ex5 no corresponde al EA")
        records.append(
            IncubatorRecord(
                magic_number=int(raw["magic_number"]),
                name=str(raw["name"]),
                comment_identity=str(raw["comment_identity"]),
                symbol=str(raw["symbol"]),
                timeframe=str(raw["timeframe"]),
                ea_relative_path=str(raw["ea_relative_path"]),
                ea_sha256=str(raw["ea_sha256"]),
                profile=str(raw["profile"]),
                capital_allocated_pct=Decimal(str(raw["capital_allocated_pct"])),
                risk_per_trade_pct=Decimal(str(raw["risk_per_trade_pct"])),
            )
        )
    magics = [record.magic_number for record in records]
    if len(magics) != len(set(magics)):
        raise SystemExit("magic duplicado en el manifiesto")
    return login, records


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


async def _register(args: argparse.Namespace) -> dict[str, Any]:
    import core.db.models  # noqa: F401
    from core.config import get_settings
    from core.db.base import async_session_factory
    from core.db.enums import ActorType, BotOriginKind, BotProfile, BotRole, PipelinePhase
    from core.db.models.accounts import Account, Bot
    from core.db.models.operations import ExternalEaInventory
    from core.db.models.pipeline import PipelineCandidate
    from core.services.pipeline_history import record_phase_transition
    from sqlalchemy import select

    if get_settings().deployment_profile != "operational":
        raise SystemExit("sólo en DEPLOYMENT_PROFILE=operational")
    login, records = load_manifest(args.manifest, {profile.value for profile in BotProfile})
    result: dict[str, Any] = {
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "account_login": login,
        "created": [],
        "existing": [],
    }
    async with async_session_factory() as session:
        account = await session.scalar(select(Account).where(Account.login == login))
        if account is None or not account.is_demo:
            raise SystemExit("la cuenta de Incubadora no existe o no es demo")
        for record in records:
            existing = await session.scalar(
                select(Bot).where(
                    Bot.account_id == account.id, Bot.magic_number == record.magic_number
                )
            )
            if existing is not None:
                result["existing"].append({"magic": record.magic_number, "bot_id": existing.id})
                continue
            if not args.apply:
                result["created"].append({"magic": record.magic_number, "dry_run": True})
                continue
            now = datetime.now(UTC)
            bot = Bot(
                account_id=account.id,
                magic_number=record.magic_number,
                name=record.name,
                market=record.symbol,
                timeframe=record.timeframe,
                profile=BotProfile(record.profile),
                role=BotRole.CHALLENGER,
                origin_kind=BotOriginKind.INCUBATION,
                pipeline_phase=PipelinePhase.F5,
                entered_state_at=now,
                capital_allocated_pct=record.capital_allocated_pct,
                risk_per_trade_pct=record.risk_per_trade_pct,
                created_at=now,
            )
            session.add(bot)
            await session.flush()
            candidate = PipelineCandidate(
                bot_id=bot.id,
                current_phase=PipelinePhase.F5,
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
                to_phase=PipelinePhase.F5,
                actor=ActorType.HUMAN,
                reason="INCUBATOR_OBSERVED_REGISTERED",
            )
            session.add(
                ExternalEaInventory(
                    account_id=account.id,
                    bot_id=bot.id,
                    ea_filename=PureWindowsPath(record.ea_relative_path).name,
                    ea_relative_path=record.ea_relative_path,
                    ea_sha256=record.ea_sha256,
                    comment_identity=record.comment_identity,
                    magic_number=record.magic_number,
                    symbol=record.symbol,
                    timeframe=record.timeframe,
                    observed_at=now,
                )
            )
            result["created"].append({"magic": record.magic_number, "bot_id": bot.id})
        if args.apply:
            await session.commit()
    return result


def main() -> None:
    args = _args()
    result = asyncio.run(_register(args))
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("mode", "created", "existing")}))


if __name__ == "__main__":
    main()
