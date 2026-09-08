"""Append-only admission of one sealed candidate into Incubadora F3."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import core.db.models  # noqa: F401
from core.db.base import async_session_factory
from core.db.enums import (
    AccountDataOrigin,
    ActorType,
    AssetAdmissionStatus,
    BotOriginKind,
    BotProfile,
    BotRole,
    PipelinePhase,
)
from core.db.models.accounts import Account, Baseline, Bot
from core.db.models.market import ImportArtifact
from core.db.models.operations import OperationalAsset, OperationalAssetEvent
from core.db.models.pipeline import PipelineCandidate
from core.services.admin_imports import import_sqx_baseline
from core.services.incubator_admission import AdmissionConfig, IncubatorSlot, evaluate_admission
from core.services.pipeline_history import record_phase_transition
from core.services.sqx_baseline_parser import _parse_trades, parse_sqx144_baseline
from sqlalchemy import select


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-id", type=int, required=True)
    parser.add_argument("--login", required=True)
    parser.add_argument("--sqx-path", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--magic", type=int, required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--profile", choices=[item.value for item in BotProfile], required=True)
    parser.add_argument("--ea-version", required=True)
    parser.add_argument("--capital-allocated-pct", type=Decimal, required=True)
    parser.add_argument("--risk-per-trade-pct", type=Decimal, required=True)
    parser.add_argument("--dd-contract-pct", type=Decimal, required=True)
    parser.add_argument("--prefilter", type=Path, default=Path("config/operational_prefilter.json"))
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def admission_config(path: Path) -> AdmissionConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    item = payload["incubator_admission"]
    return AdmissionConfig(
        max_per_symbol_timeframe=int(item["max_per_symbol_timeframe"]),
        max_concurrent=int(item["max_concurrent"]),
        max_abs_correlation=float(item["max_abs_correlation"]),
    )


def pnl_series_from_sqx(payload: bytes) -> list[float]:
    """Read only PnL sequence from the same sealed SQX orders used by the baseline."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        return [float(row[2]) for row in _parse_trades(archive.read("orders.bin"))]


async def run(value: argparse.Namespace) -> None:
    if min(value.capital_allocated_pct, value.risk_per_trade_pct, value.dd_contract_pct) <= 0:
        raise ValueError("capital, risk and drawdown contract must be positive")
    if not value.sqx_path.is_file():
        raise ValueError("sealed SQX source does not exist")
    sqx_payload = value.sqx_path.read_bytes()
    parsed = parse_sqx144_baseline(sqx_payload)
    config = admission_config(value.prefilter)
    async with async_session_factory() as session:
        account = await session.scalar(select(Account).where(Account.login == value.login))
        if account is None or account.data_origin != AccountDataOrigin.BROKER_DEMO:
            raise ValueError("Incubadora requires a registered BROKER_DEMO account")
        asset = await session.get(OperationalAsset, value.asset_id)
        if asset is None or asset.magic_number != value.magic:
            raise ValueError("asset identity does not match the deployment contract")
        if hashlib.sha256(sqx_payload).hexdigest().lower() != asset.sqx_sha256.lower():
            raise ValueError("sealed SQX source hash does not match the validated asset")
        statuses = list(
            (
                await session.scalars(
                    select(OperationalAssetEvent.status).where(
                        OperationalAssetEvent.asset_id == asset.id
                    )
                )
            ).all()
        )
        if AssetAdmissionStatus.BACKTEST_VALIDATED not in statuses:
            raise ValueError("asset lacks BACKTEST_VALIDATED evidence")
        existing = await session.scalar(
            select(Bot).where(
                Bot.account_id == account.id,
                Bot.magic_number == value.magic,
            )
        )
        if existing is not None:
            raise ValueError(f"magic already registered as bot_id={existing.id}")
        incumbents = list(
            (
                await session.scalars(
                    select(Bot).where(Bot.origin_kind == BotOriginKind.INCUBATION)
                )
            ).all()
        )
        occupied: list[IncubatorSlot] = []
        for item in incumbents:
            baseline = await session.scalar(select(Baseline).where(Baseline.id == item.baseline_id))
            artifact = (
                await session.scalar(
                    select(ImportArtifact).where(ImportArtifact.id == baseline.artifact_id)
                )
                if baseline
                else None
            )
            series = (
                pnl_series_from_sqx(bytes(artifact.payload))
                if artifact and artifact.payload
                else []
            )
            occupied.append(
                IncubatorSlot(
                    bot_id=item.id,
                    symbol=item.market,
                    timeframe=item.timeframe,
                    pnl_series=series,
                )
            )
        candidate_series = pnl_series_from_sqx(sqx_payload)
        decision = evaluate_admission(
            symbol=value.market,
            timeframe=value.timeframe,
            pnl_series=candidate_series,
            occupied=occupied,
            config=config,
        )
        if not decision.admitted:
            raise ValueError(f"admission rejected: {decision.reason}")
        if not value.apply:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "mode": "dry_run",
                        "trade_count": parsed.trade_count,
                        "admission": decision.as_evidence(),
                    },
                    ensure_ascii=False,
                )
            )
            return
        now = datetime.now(UTC)
        bot = Bot(
            account_id=account.id,
            magic_number=value.magic,
            name=value.name,
            market=value.market,
            timeframe=value.timeframe,
            profile=BotProfile(value.profile),
            role=BotRole.CHALLENGER,
            origin_kind=BotOriginKind.INCUBATION,
            pipeline_phase=PipelinePhase.F3,
            entered_state_at=now,
            capital_allocated_pct=value.capital_allocated_pct,
            risk_per_trade_pct=value.risk_per_trade_pct,
            sizing_current_pct=value.risk_per_trade_pct,
            created_at=now,
            ea_required_version=value.ea_version,
        )
        session.add(bot)
        await session.flush()
        baseline = await import_sqx_baseline(
            session, bot_id=bot.id, path=value.sqx_path, dd_contract_pct=value.dd_contract_pct
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
            reason="INCUBATOR_ONBOARDING_SEALED_VALIDADA",
        )
        session.add(
            OperationalAssetEvent(
                asset_id=asset.id,
                status=AssetAdmissionStatus.INCUBATING,
                reason="INCUBATOR_F3_ADMISSION",
                evidence={
                    "bot_id": bot.id,
                    "baseline_id": baseline.id,
                    "admission": decision.as_evidence(),
                    "ea_version": value.ea_version,
                },
                occurred_at=now,
            )
        )
        await session.commit()
        print(
            json.dumps(
                {
                    "ok": True,
                    "bot_id": bot.id,
                    "baseline_id": baseline.id,
                    "candidate_id": candidate.id,
                    "phase": "F3",
                }
            )
        )


if __name__ == "__main__":
    asyncio.run(run(args()))
