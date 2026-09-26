"""Contrato F3 de adjunto demo: evidencia explícita y reporter sellado."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from fakeredis.aioredis import FakeRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import AccountDataOrigin, AssetAdmissionStatus, AssetSourceGroup, PipelinePhase
from core.db.models.accounts import Account, Bot
from core.db.models.market import EaState, ImportArtifact
from core.db.models.operations import OperationalAsset, OperationalAssetEvent
from core.db.models.pipeline import PipelineCandidate
from core.services.demo_attachment import (
    DemoAttachmentManifest,
    advance_verified_f3_candidates,
    candidate_asset,
    evaluate_demo_attachment,
    register_demo_attachment,
)
from tests.factories import AccountFactory, BaselineFactory, BotFactory, IngestBatchFactory

_SQX_SHA256 = "a" * 64
_MQL5_SHA256 = "b" * 64
_EX5_SHA256 = "c" * 64
_EA_VERSION = "operational-reporter-v1"


async def _session(connection: AsyncConnection) -> AsyncSession:
    return AsyncSession(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )


async def _f3_candidate(connection: AsyncConnection) -> tuple[PipelineCandidate, Bot, Account]:
    session = await _session(connection)
    account = AccountFactory(data_origin=AccountDataOrigin.BROKER_DEMO)
    session.add(account)
    await session.flush()
    bot = BotFactory(
        account_id=account.id,
        magic_number=295,
        market="AUDCAD_darwinex",
        timeframe="H4",
        pipeline_phase=PipelinePhase.F3,
        ea_required_version=_EA_VERSION,
    )
    session.add(bot)
    await session.flush()
    artifact = ImportArtifact(
        kind="SQX",
        sha256=_SQX_SHA256,
        original_filename="candidate.sqx",
        source_path="sealed/candidate.sqx",
        parser_version="test",
        metadata_json={},
        payload=b"sealed-sqx",
        imported_at=datetime.now(UTC),
    )
    session.add(artifact)
    await session.flush()
    baseline = BaselineFactory(bot_id=bot.id, artifact_id=artifact.id)
    session.add(baseline)
    await session.flush()
    bot.baseline_id = baseline.id
    asset = OperationalAsset(
        source_group=AssetSourceGroup.ANALYSIS,
        source_root="sealed",
        sqx_path="sealed/candidate.sqx",
        mql5_path="sealed/candidate.mq5",
        sqx_sha256=_SQX_SHA256,
        mql5_sha256=_MQL5_SHA256,
        strategy_name="Candidate",
        magic_number=bot.magic_number,
        symbol=bot.market,
        timeframe=bot.timeframe,
        discovered_at=datetime.now(UTC),
    )
    session.add(asset)
    await session.flush()
    candidate = PipelineCandidate(
        bot_id=bot.id,
        current_phase=PipelinePhase.F3,
        entered_phase_at=datetime.now(UTC),
        incubation_days=0,
        oos_trades=0,
    )
    session.add(candidate)
    await session.flush()
    session.add(
        OperationalAssetEvent(
            asset_id=asset.id,
            status=AssetAdmissionStatus.BACKTEST_VALIDATED,
            reason="TEST",
            evidence={"candidate_id": candidate.id},
            occurred_at=datetime.now(UTC),
        )
    )
    await session.commit()
    return candidate, bot, account


async def test_candidate_asset_rejects_a_static_duplicate_without_candidate_evidence(
    db_connection: AsyncConnection,
) -> None:
    candidate, bot, _ = await _f3_candidate(db_connection)
    session = await _session(db_connection)
    duplicate = OperationalAsset(
        source_group=AssetSourceGroup.ANALYSIS,
        source_root="static",
        sqx_path="static/candidate.sqx",
        mql5_path=None,
        sqx_sha256=_SQX_SHA256,
        mql5_sha256=None,
        strategy_name="Static duplicate",
        magic_number=None,
        symbol=bot.market,
        timeframe=bot.timeframe,
        discovered_at=datetime.now(UTC),
    )
    session.add(duplicate)
    await session.commit()

    resolved = await candidate_asset(session, candidate, bot)

    assert resolved is not None
    assert resolved.id != duplicate.id
    assert resolved.mql5_sha256 == _MQL5_SHA256


def _manifest(asset_id: int, account_login: str) -> DemoAttachmentManifest:
    return DemoAttachmentManifest(
        asset_id=asset_id,
        account_login=account_login,
        magic_number=295,
        symbol="AUDCAD_darwinex",
        timeframe="H4",
        ea_version=_EA_VERSION,
        mql5_sha256=_MQL5_SHA256,
        compiled_ex5_sha256=_EX5_SHA256,
        comment_identity="stratos-demo-audcad-h4",
        expert_relative_path="Experts\\StratOS_Operational\\Candidate.ex5",
        reporter_outbox="candidate.jsonl",
        required_sizing_pct=Decimal("0.20"),
    )


async def test_attachment_requires_fresh_matching_reporter_state(
    db_connection: AsyncConnection, tmp_path: Path
) -> None:
    candidate, bot, account = await _f3_candidate(db_connection)
    session = await _session(db_connection)
    asset = await session.scalar(
        select(OperationalAsset).where(OperationalAsset.magic_number == bot.magic_number)
    )
    assert asset is not None
    attachment = await register_demo_attachment(
        session,
        candidate=candidate,
        manifest=_manifest(asset.id, account.login),
        source_path=tmp_path / "attachment.json",
    )
    await session.commit()

    without_reporter = await evaluate_demo_attachment(session, candidate, bot, account)
    assert without_reporter.verified is False
    assert without_reporter.requirements["reporter_telemetry"] is False

    batch = IngestBatchFactory(account_id=account.id, batch_type="ea_state")
    session.add(batch)
    await session.flush()
    session.add(
        EaState(
            account_id=account.id,
            magic_number=bot.magic_number,
            ea_version=_EA_VERSION,
            mode="REAL",
            autotrading=True,
            schedule_filter=None,
            news_windows=None,
            sizing_pct=Decimal("0.20"),
            ingest_batch_id=batch.id,
            last_ingested_at=attachment.declared_at + timedelta(seconds=1),
        )
    )
    await session.commit()

    verified = await evaluate_demo_attachment(session, candidate, bot, account)
    assert verified.verified is True
    advanced = await advance_verified_f3_candidates(
        session, FakeRedis(), account, [bot.magic_number]
    )
    assert advanced == [candidate.id]
    refreshed_candidate = await session.get(PipelineCandidate, candidate.id)
    refreshed_bot = await session.get(Bot, bot.id)
    assert refreshed_candidate is not None
    assert refreshed_bot is not None
    assert refreshed_candidate.current_phase == PipelinePhase.F4
    assert refreshed_bot.pipeline_phase == PipelinePhase.F4


async def test_attachment_registration_is_idempotent(
    db_connection: AsyncConnection, tmp_path: Path
) -> None:
    candidate, bot, account = await _f3_candidate(db_connection)
    session = await _session(db_connection)
    asset = await session.scalar(
        select(OperationalAsset).where(OperationalAsset.magic_number == bot.magic_number)
    )
    assert asset is not None
    manifest = _manifest(asset.id, account.login)
    first = await register_demo_attachment(
        session, candidate=candidate, manifest=manifest, source_path=tmp_path / "attachment.json"
    )
    await session.commit()
    second = await register_demo_attachment(
        session, candidate=candidate, manifest=manifest, source_path=tmp_path / "attachment.json"
    )
    assert second.id == first.id
