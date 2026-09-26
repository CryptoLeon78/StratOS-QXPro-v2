"""Contrato sellado de adjunto demo y comprobación contra telemetría EA.

No hay automatización de MT5 aquí: el manifiesto registra una acción humana
ya realizada y ``EaState`` sólo llega por la ingesta autenticada del reporter.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import AccountDataOrigin, ActorType, AssetAdmissionStatus, PipelinePhase
from core.db.models.accounts import Account, Baseline, Bot
from core.db.models.market import EaState, ImportArtifact
from core.db.models.operations import DemoChartAttachment, OperationalAsset, OperationalAssetEvent
from core.db.models.pipeline import PipelineCandidate
from core.services.pipeline_history import record_phase_transition

_ARTIFACT_KIND = "DEMO_ATTACHMENT"
_MANIFEST_PARSER_VERSION = "demo-attachment-manifest-v1"
_REQUIRED_MODE: Literal["REAL"] = "REAL"


class DemoAttachmentManifest(BaseModel):
    """Campos explícitos, sin inferencia desde nombre de EA o ruta."""

    asset_id: int
    account_login: str
    magic_number: int
    symbol: str
    timeframe: str
    ea_version: str
    mql5_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    compiled_ex5_sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    comment_identity: str = Field(min_length=1)
    expert_relative_path: str = Field(min_length=1)
    reporter_outbox: str = Field(min_length=1)
    required_mode: Literal["REAL"] = _REQUIRED_MODE
    required_autotrading: Literal[True] = True
    required_sizing_pct: Decimal = Field(gt=0, max_digits=5, decimal_places=2)


@dataclass(frozen=True)
class DemoAttachmentEvaluation:
    attachment: DemoChartAttachment | None
    requirements: dict[str, bool]

    @property
    def verified(self) -> bool:
        return self.attachment is not None and all(self.requirements.values())


def canonical_manifest_payload(manifest: DemoAttachmentManifest) -> bytes:
    return json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


async def candidate_asset(
    session: AsyncSession, candidate: PipelineCandidate, bot: Bot
) -> OperationalAsset | None:
    """Resolve the exact validated asset linked to this F3 admission.

    A sealed SQX hash alone is not an asset identity: the static inventory and
    a later SQX-vs-MT5 import can legitimately share it.  The latter records
    the explicit ``candidate_id`` in its append-only BACKTEST_VALIDATED event.
    Never select an arbitrary asset row from a shared SQX hash.
    """
    if bot.baseline_id is None:
        return None
    baseline = await session.get(Baseline, bot.baseline_id)
    if baseline is None or baseline.artifact_id is None:
        return None
    artifact = await session.get(ImportArtifact, baseline.artifact_id)
    if artifact is None:
        return None
    events = list(
        (
            await session.scalars(
                select(OperationalAssetEvent)
                .where(OperationalAssetEvent.status == AssetAdmissionStatus.BACKTEST_VALIDATED)
                .order_by(OperationalAssetEvent.id)
            )
        ).all()
    )
    asset_ids = {
        event.asset_id for event in events if event.evidence.get("candidate_id") == candidate.id
    }
    if len(asset_ids) != 1:
        return None
    asset = await session.get(OperationalAsset, asset_ids.pop())
    if (
        asset is None
        or asset.sqx_sha256 is None
        or asset.sqx_sha256.lower() != artifact.sha256.lower()
    ):
        return None
    return asset


async def has_validated_backtest(session: AsyncSession, asset: OperationalAsset | None) -> bool:
    if asset is None:
        return False
    return (
        await session.scalar(
            select(OperationalAssetEvent.id).where(
                OperationalAssetEvent.asset_id == asset.id,
                OperationalAssetEvent.status == AssetAdmissionStatus.BACKTEST_VALIDATED,
            )
        )
    ) is not None


async def evaluate_demo_attachment(
    session: AsyncSession, candidate: PipelineCandidate, bot: Bot, account: Account
) -> DemoAttachmentEvaluation:
    """Fail closed until a declared attachment has fresh matching reporter state."""
    attachment = await session.scalar(
        select(DemoChartAttachment)
        .where(DemoChartAttachment.candidate_id == candidate.id)
        .order_by(DemoChartAttachment.declared_at.desc(), DemoChartAttachment.id.desc())
    )
    if attachment is None:
        return DemoAttachmentEvaluation(
            attachment=None,
            requirements={
                "demo_attachment_manifest": False,
                "reporter_telemetry": False,
                "reporter_version_match": False,
                "reporter_mode_match": False,
                "reporter_autotrading_match": False,
                "reporter_sizing_match": False,
            },
        )
    state = await session.get(EaState, (account.id, bot.magic_number))
    if state is None or state.last_ingested_at < attachment.declared_at:
        return DemoAttachmentEvaluation(
            attachment=attachment,
            requirements={
                "demo_attachment_manifest": True,
                "reporter_telemetry": False,
                "reporter_version_match": False,
                "reporter_mode_match": False,
                "reporter_autotrading_match": False,
                "reporter_sizing_match": False,
            },
        )
    return DemoAttachmentEvaluation(
        attachment=attachment,
        requirements={
            "demo_attachment_manifest": True,
            "reporter_telemetry": True,
            "reporter_version_match": state.ea_version == attachment.ea_version,
            "reporter_mode_match": state.mode.upper() == attachment.required_mode,
            "reporter_autotrading_match": state.autotrading == attachment.required_autotrading,
            "reporter_sizing_match": state.sizing_pct == attachment.required_sizing_pct,
        },
    )


async def register_demo_attachment(
    session: AsyncSession,
    *,
    candidate: PipelineCandidate,
    manifest: DemoAttachmentManifest,
    source_path: Path,
) -> DemoChartAttachment:
    """Persist one explicit, identity-checked attachment declaration idempotently."""
    if candidate.current_phase != PipelinePhase.F3:
        raise ValueError("demo attachment registration requires candidate in F3")
    bot = await session.get(Bot, candidate.bot_id)
    if bot is None:
        raise ValueError("candidate has no bot")
    account = await session.get(Account, bot.account_id)
    if account is None or account.data_origin != AccountDataOrigin.BROKER_DEMO:
        raise ValueError("demo attachment requires registered BROKER_DEMO account")
    if account.login != manifest.account_login:
        raise ValueError("manifest account does not match candidate account")
    asset = await candidate_asset(session, candidate, bot)
    if asset is None or asset.id != manifest.asset_id:
        raise ValueError("manifest asset does not match candidate sealed baseline")
    if not await has_validated_backtest(session, asset):
        raise ValueError("asset lacks BACKTEST_VALIDATED evidence")
    if (
        bot.magic_number != manifest.magic_number
        or bot.market != manifest.symbol
        or bot.timeframe != manifest.timeframe
        or bot.ea_required_version != manifest.ea_version
        or asset.mql5_sha256 is None
        or asset.mql5_sha256.lower() != manifest.mql5_sha256.lower()
    ):
        raise ValueError("manifest EA identity does not match candidate contract")
    payload = canonical_manifest_payload(manifest)
    sha256 = hashlib.sha256(payload).hexdigest()
    artifact = await session.scalar(
        select(ImportArtifact).where(
            ImportArtifact.kind == _ARTIFACT_KIND, ImportArtifact.sha256 == sha256
        )
    )
    if artifact is None:
        artifact = ImportArtifact(
            kind=_ARTIFACT_KIND,
            sha256=sha256,
            original_filename=source_path.name,
            source_path=str(source_path),
            parser_version=_MANIFEST_PARSER_VERSION,
            metadata_json={"candidate_id": candidate.id, "asset_id": asset.id},
            payload=payload,
            imported_at=datetime.now(UTC),
        )
        session.add(artifact)
        await session.flush()
    existing = await session.scalar(
        select(DemoChartAttachment).where(
            DemoChartAttachment.candidate_id == candidate.id,
            DemoChartAttachment.artifact_id == artifact.id,
        )
    )
    if existing is not None:
        return existing
    attachment = DemoChartAttachment(
        candidate_id=candidate.id,
        asset_id=asset.id,
        account_id=account.id,
        artifact_id=artifact.id,
        magic_number=manifest.magic_number,
        symbol=manifest.symbol,
        timeframe=manifest.timeframe,
        ea_version=manifest.ea_version,
        mql5_sha256=manifest.mql5_sha256.lower(),
        compiled_ex5_sha256=manifest.compiled_ex5_sha256.lower(),
        comment_identity=manifest.comment_identity,
        expert_relative_path=manifest.expert_relative_path,
        reporter_outbox=manifest.reporter_outbox,
        required_mode=manifest.required_mode,
        required_autotrading=manifest.required_autotrading,
        required_sizing_pct=manifest.required_sizing_pct,
        declared_at=datetime.now(UTC),
    )
    session.add(attachment)
    await session.flush()
    return attachment


async def advance_verified_f3_candidates(
    session: AsyncSession, redis: Redis, account: Account, magics: list[int]
) -> list[int]:
    """Advance only F3 candidates whose just-ingested reporter state verifies.

    This is invoked by sealed ``ea_state`` ingestion, not by a UI click. It
    never opens MT5; it merely records the contractual F3->F4 transition.
    """
    candidates = list(
        (
            await session.scalars(
                select(PipelineCandidate)
                .join(Bot, Bot.id == PipelineCandidate.bot_id)
                .where(
                    PipelineCandidate.current_phase == PipelinePhase.F3,
                    Bot.account_id == account.id,
                    Bot.magic_number.in_(magics),
                )
            )
        ).all()
    )
    advanced: list[int] = []
    for candidate in candidates:
        bot = await session.get(Bot, candidate.bot_id)
        if bot is None or bot.baseline_id is None:
            continue
        asset = await candidate_asset(session, candidate, bot)
        attachment = await evaluate_demo_attachment(session, candidate, bot, account)
        if (
            account.data_origin != AccountDataOrigin.BROKER_DEMO
            or not await has_validated_backtest(session, asset)
            or not attachment.verified
        ):
            continue
        candidate.current_phase = PipelinePhase.F4
        candidate.entered_phase_at = datetime.now(UTC)
        bot.pipeline_phase = PipelinePhase.F4
        record_phase_transition(
            session,
            candidate,
            from_phase=PipelinePhase.F3,
            to_phase=PipelinePhase.F4,
            actor=ActorType.SYSTEM,
            reason="DEMO_ATTACHMENT_AND_REPORTER_VERIFIED",
        )
        await redis.publish(
            "events:pipeline",
            json.dumps(
                {
                    "type": "pipeline.demo_admission_verified",
                    "candidate_id": candidate.id,
                    "bot_id": candidate.bot_id,
                    "from_phase": PipelinePhase.F3.value,
                    "to_phase": PipelinePhase.F4.value,
                }
            ),
        )
        advanced.append(candidate.id)
    return advanced
