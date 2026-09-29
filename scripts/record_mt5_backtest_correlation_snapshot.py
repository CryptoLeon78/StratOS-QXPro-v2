"""Create one source-scoped MT5_BACKTEST correlation snapshot from sealed reports.

The command only reads already imported BACKTEST_VALIDATED evidence. Candidate
IDs are required explicitly; it never maps a strategy name to a bot.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from core.services.correlations import (
    CorrelationServiceConfig,
    TradePnl,
    persist_mt5_backtest_correlation_snapshot,
)
from core.services.mt5_tester_report import PARSER_VERSION, parse_sqx_vs_mt5_closed_deals


async def record(candidate_ids: list[int], tester_timezone: str) -> str:
    from sqlalchemy import select

    from core.config import get_settings
    from core.db.base import async_session_factory
    from core.db.enums import AssetAdmissionStatus
    from core.db.models.accounts import Bot
    from core.db.models.market import ImportArtifact
    from core.db.models.operations import OperationalAssetEvent
    from core.db.models.pipeline import PipelineCandidate

    if get_settings().deployment_profile != "operational":
        raise ValueError("operational profile required")
    if len(set(candidate_ids)) < 2:
        raise ValueError("at least two explicit candidate IDs are required")
    try:
        source_timezone = ZoneInfo(tester_timezone)
    except Exception as exc:
        raise ValueError("--tester-timezone must be a valid IANA timezone") from exc
    async with async_session_factory() as session, session.begin():
        trades_by_bot: dict[int, list[TradePnl]] = {}
        evidence: list[dict[str, object]] = []
        account_ids: set[int] = set()
        for candidate_id in sorted(set(candidate_ids)):
            candidate = await session.get(PipelineCandidate, candidate_id)
            if candidate is None:
                raise ValueError(f"candidate {candidate_id} does not exist")
            bot = await session.get(Bot, candidate.bot_id)
            if bot is None:
                raise ValueError(f"candidate {candidate_id} has no bot")
            account_ids.add(bot.account_id)
            events = list(
                (
                    await session.scalars(
                        select(OperationalAssetEvent).where(
                            OperationalAssetEvent.status == AssetAdmissionStatus.BACKTEST_VALIDATED
                        )
                    )
                ).all()
            )
            matching = [event for event in events if event.evidence.get("candidate_id") == candidate_id]
            # El ledger puede conservar reintentos append-only del mismo
            # manifiesto. Sólo son equivalentes si el manifiesto archivado y
            # cada artefacto referenciado son idénticos; dos procedencias
            # distintas siguen retenidas en vez de escoger una por fecha.
            evidence_groups: dict[tuple[str, tuple[object, ...]], list[OperationalAssetEvent]] = {}
            for event in matching:
                archive_hash = event.evidence.get("archive_manifest_sha256")
                event_artifact_ids = event.evidence.get("artifact_ids")
                if not isinstance(archive_hash, str) or not isinstance(event_artifact_ids, list):
                    raise ValueError(f"candidate {candidate_id} event lacks canonical archive evidence")
                evidence_groups.setdefault((archive_hash, tuple(event_artifact_ids)), []).append(event)
            if len(evidence_groups) != 1:
                raise ValueError(f"candidate {candidate_id} requires one canonical BACKTEST_VALIDATED evidence group")
            _, grouped_events = next(iter(evidence_groups.items()))
            artifact_ids = grouped_events[0].evidence["artifact_ids"]
            if not isinstance(artifact_ids, list):
                raise ValueError(f"candidate {candidate_id} event lacks artifact IDs")
            artifacts = [await session.get(ImportArtifact, int(item)) for item in artifact_ids]
            csvs = [artifact for artifact in artifacts if artifact and artifact.original_filename.lower().endswith(".csv")]
            if len(csvs) != 1:
                raise ValueError(f"candidate {candidate_id} requires exactly one sealed MT5 CSV artifact")
            artifact = csvs[0]
            import hashlib
            if hashlib.sha256(artifact.payload).hexdigest().lower() != artifact.sha256.lower():
                raise ValueError(f"candidate {candidate_id} MT5 CSV artifact hash mismatch")
            deals = parse_sqx_vs_mt5_closed_deals(artifact.payload)
            trades_by_bot[bot.id] = [
                TradePnl(deal.closed_at.replace(tzinfo=source_timezone).astimezone(UTC), deal.net_pnl)
                for deal in deals
            ]
            evidence.append(
                {
                    "candidate_id": candidate_id,
                    "bot_id": bot.id,
                    "artifact_id": artifact.id,
                    "artifact_sha256": artifact.sha256,
                    "parser_version": PARSER_VERSION,
                    "tester_timezone": tester_timezone,
                    "closed_deals": [
                        {
                            "closed_at": deal.closed_at.replace(tzinfo=source_timezone)
                            .astimezone(UTC)
                            .isoformat(),
                            "profit": str(deal.profit),
                            "commission": str(deal.commission),
                            "swap": str(deal.swap),
                        }
                        for deal in deals
                    ],
                }
            )
        if len(account_ids) != 1:
            raise ValueError("candidates must belong to a single account (ADR 0013)")
        all_dates = [trade.closed_at for trades in trades_by_bot.values() for trade in trades]
        result = await persist_mt5_backtest_correlation_snapshot(
            session,
            now=datetime.now(UTC),
            window_start=min(all_dates),
            window_end=max(all_dates),
            window_days=(max(all_dates).date() - min(all_dates).date()).days + 1,
            input_manifest={"schema_version": "mt5-backtest-correlation-v1", "evidence": evidence},
            trades_by_bot=trades_by_bot,
            config=CorrelationServiceConfig(),
            account_id=next(iter(account_ids)),
        )
    return f"snapshot_id={result.snapshot.id} source=MT5_BACKTEST status={result.snapshot.status} created={result.created}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", type=int, action="append", required=True)
    parser.add_argument("--tester-timezone", required=True)
    args = parser.parse_args()
    print(asyncio.run(record(args.candidate_id, args.tester_timezone)))


if __name__ == "__main__":
    main()
