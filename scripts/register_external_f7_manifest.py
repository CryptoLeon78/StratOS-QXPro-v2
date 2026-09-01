"""Register verified real EAs as idempotent F7 external observations.

The source manifests are read-only evidence. Only rows with an unambiguous
EX5 association are accepted; withheld rows are reported but never inserted.
This command never contacts MT5 or the VPS.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import core.db.models  # noqa: F401
from core.config import get_settings
from core.db.base import async_session_factory
from core.db.enums import (
    AccountDataOrigin,
    ActorType,
    BotOriginKind,
    BotRole,
    PipelinePhase,
)
from core.db.models.accounts import Account, Bot
from core.db.models.operations import ExternalEaInventory
from core.db.models.pipeline import PipelineCandidate
from core.services.pipeline_history import record_phase_transition
from sqlalchemy import select

_ELIGIBLE_STATUSES = frozenset({"MATCHED_EQUIVALENT_EX5_COPIES", "MATCHED_UNIQUE_VERSION"})


@dataclass(frozen=True)
class ManifestRecord:
    account_login: str
    account_label: str
    strategy_name: str
    comment_identity: str
    magic_number: int
    symbol: str
    timeframe: str
    ea_relative_path: str
    ea_sha256: str
    status: str


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", action="append", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument(
        "--apply", action="store_true", help="Persist F7 external records after validation."
    )
    return parser.parse_args()


def _load_manifest(path: Path) -> tuple[str, list[ManifestRecord], int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    login = str(payload["account_login"])
    label = str(payload["account_label"])
    records: list[ManifestRecord] = []
    withheld = 0
    for raw in payload["records"]:
        status = str(raw["status"])
        if status not in _ELIGIBLE_STATUSES:
            withheld += 1
            continue
        required = (
            "strategy_name",
            "comment_identity",
            "magic_number",
            "symbol",
            "timeframe",
            "ea_relative_path",
            "ea_sha256",
        )
        if any(raw.get(field) in (None, "") for field in required):
            raise SystemExit(
                f"fila elegible incompleta en {path.name}: magic={raw.get('magic_number')}"
            )
        records.append(
            ManifestRecord(
                account_login=login,
                account_label=label,
                strategy_name=str(raw["strategy_name"]),
                comment_identity=str(raw["comment_identity"]),
                magic_number=int(raw["magic_number"]),
                symbol=str(raw["symbol"]),
                timeframe=str(raw["timeframe"]),
                ea_relative_path=str(raw["ea_relative_path"]),
                ea_sha256=str(raw["ea_sha256"]),
                status=status,
            )
        )
    return login, records, withheld


def _canonical_hash(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.read_bytes())
    return digest.hexdigest()


async def register_manifests(args: argparse.Namespace) -> dict[str, Any]:
    if get_settings().deployment_profile != "operational":
        raise SystemExit("alta F7 externa permitida sólo en DEPLOYMENT_PROFILE=operational")

    manifest_paths = [path.resolve() for path in args.manifest]
    loaded = [_load_manifest(path) for path in manifest_paths]
    records = [record for _, group, _ in loaded for record in group]
    withheld = sum(count for _, _, count in loaded)
    seen = {(record.account_login, record.magic_number) for record in records}
    if len(seen) != len(records):
        raise SystemExit("magic duplicado entre filas elegibles; no se puede registrar")

    result: dict[str, Any] = {
        "schema_version": 1,
        "run_at": datetime.now(UTC).isoformat(),
        "mode": "APPLY" if args.apply else "DRY_RUN",
        "manifest_sha256": _canonical_hash(manifest_paths),
        "eligible_records": len(records),
        "withheld_records": withheld,
        "created": [],
        "existing": [],
    }
    async with async_session_factory() as session:
        for record in records:
            account = await session.scalar(
                select(Account).where(Account.login == record.account_login)
            )
            if account is None or account.data_origin != AccountDataOrigin.BROKER_REAL:
                raise SystemExit(f"cuenta operacional BROKER_REAL ausente: {record.account_label}")
            inventory = await session.scalar(
                select(ExternalEaInventory).where(
                    ExternalEaInventory.account_id == account.id,
                    ExternalEaInventory.magic_number == record.magic_number,
                    ExternalEaInventory.comment_identity == record.comment_identity,
                    ExternalEaInventory.symbol == record.symbol,
                    ExternalEaInventory.timeframe == record.timeframe,
                    ExternalEaInventory.ea_relative_path == record.ea_relative_path,
                    ExternalEaInventory.ea_sha256 == record.ea_sha256,
                )
            )
            if inventory is None:
                raise SystemExit(
                    "inventario no coincide para "
                    f"{record.account_label} magic={record.magic_number}"
                )
            existing = await session.scalar(
                select(Bot).where(
                    Bot.account_id == account.id, Bot.magic_number == record.magic_number
                )
            )
            if existing is not None:
                if existing.origin_kind != BotOriginKind.EXTERNAL_PRODUCTION:
                    raise SystemExit(
                        "magic ocupado por bot no externo: "
                        f"{record.account_label} {record.magic_number}"
                    )
                result["existing"].append(
                    {"account_id": account.id, "bot_id": existing.id, "magic": record.magic_number}
                )
                continue
            if not args.apply:
                result["created"].append(
                    {"account_id": account.id, "magic": record.magic_number, "dry_run": True}
                )
                continue

            now = datetime.now(UTC)
            bot = Bot(
                account_id=account.id,
                magic_number=record.magic_number,
                name=record.strategy_name,
                market=record.symbol,
                timeframe=record.timeframe,
                profile=None,
                role=BotRole.CHAMPION,
                origin_kind=BotOriginKind.EXTERNAL_PRODUCTION,
                pipeline_phase=PipelinePhase.F7,
                entered_state_at=now,
                capital_allocated_pct=None,
                risk_per_trade_pct=None,
                created_at=now,
            )
            session.add(bot)
            await session.flush()
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
            # The prior inventory observation stays immutable. This is the
            # linked observation created when the F7 registration is evidenced.
            session.add(
                ExternalEaInventory(
                    account_id=account.id,
                    bot_id=bot.id,
                    ea_filename=Path(record.ea_relative_path).name,
                    ea_relative_path=record.ea_relative_path,
                    ea_sha256=record.ea_sha256,
                    comment_identity=record.comment_identity,
                    magic_number=record.magic_number,
                    symbol=record.symbol,
                    timeframe=record.timeframe,
                    observed_at=now,
                )
            )
            result["created"].append(
                {"account_id": account.id, "bot_id": bot.id, "magic": record.magic_number}
            )
        if args.apply:
            await session.commit()
    return result


def main() -> None:
    args = _args()
    result = asyncio.run(register_manifests(args))
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {key: result[key] for key in ("mode", "eligible_records", "withheld_records")}
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
