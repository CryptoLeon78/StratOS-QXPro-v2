"""Import archived SQX_vs_MT5 evidence into the operational admission ledger.

The importer is deliberately fail-closed. It validates every archived hash,
requires a sealed ``VEREDICTO: VALIDADA`` TXT and an MT5 trades CSV, and links
the result to an already registered Pipeline candidate by numeric ID. It never
resolves a candidate or bot from a strategy name.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path, PureWindowsPath
from typing import Any

from core.services.sqx_baseline_parser import PARSER_VERSION, parse_sqx144_baseline

VERDICT = re.compile(r"VEREDICTO:\s*VALIDADA")
_PARSER_VERSION = "archived-evidence-import-v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_archived_path(raw_path: str, evidence_dir: Path) -> Path:
    """Use the original path when present, otherwise its sealed archive copy."""
    declared = Path(raw_path)
    try:
        if declared.is_file():
            return declared
    except OSError:
        # A Windows absolute path is one filename on Linux.  Its stat can
        # exceed NAME_MAX before we get the chance to select the archive copy.
        pass
    filename = PureWindowsPath(raw_path).name if "\\" in raw_path else declared.name
    for root in (evidence_dir, evidence_dir.parent):
        candidate = root / filename
        if candidate.is_file():
            return candidate
    return declared


def _sealed_artifacts(raw: dict[str, Any], evidence_dir: Path) -> tuple[list[dict[str, str]], Path, Path]:
    entries = list(raw.get("artifacts") or []) + list(raw.get("comparison_artifacts") or [])
    if not entries:
        raise ValueError("archived evidence has no artifacts")
    resolved: list[dict[str, str]] = []
    verdict_txt: Path | None = None
    mt5_csv: Path | None = None
    for entry in entries:
        declared_path = str(entry.get("path") or entry.get("name") or "")
        expected = entry.get("sha256")
        if not declared_path or not isinstance(expected, str):
            raise ValueError("archived artifact lacks path or sha256")
        path = _resolve_archived_path(declared_path, evidence_dir)
        if not path.is_file() or sha256(path).lower() != expected.lower():
            raise ValueError(f"archived artifact missing or hash mismatch: {path.name}")
        resolved.append({"path": str(path.resolve()), "sha256": expected.lower()})
        if path.suffix.lower() == ".txt":
            verdict_txt = path
        if path.suffix.lower() == ".csv":
            mt5_csv = path
    if verdict_txt is None or mt5_csv is None:
        raise ValueError("VALIDADA TXT or MT5 CSV is absent")
    if not VERDICT.search(verdict_txt.read_text(encoding="utf-8", errors="strict")):
        raise ValueError("sealed TXT does not contain VEREDICTO: VALIDADA")
    return resolved, verdict_txt, mt5_csv


def build_import_manifest(evidence_dir: Path, candidate_id: int) -> dict[str, Any]:
    """Build a derived canonical manifest without mutating operational data."""
    source = evidence_dir / "evidence-manifest.json"
    if not source.is_file():
        raise ValueError("evidence-manifest.json absent")
    raw = json.loads(source.read_text(encoding="utf-8"))
    artifacts, verdict_txt, mt5_csv = _sealed_artifacts(raw, evidence_dir)
    sqx = _resolve_archived_path(str(raw.get("sqx_path", "")), evidence_dir)
    if not sqx.is_file():
        raise ValueError("sealed SQX source is absent")
    mq5 = _resolve_archived_path(str(raw.get("mql5_path") or sqx.with_suffix(".mq5")), evidence_dir)
    if not mq5.is_file():
        raise ValueError("sealed MQL5 source is absent")
    baseline = parse_sqx144_baseline(sqx.read_bytes())
    return {
        "schema_version": _PARSER_VERSION,
        "provenance": "archived_evidence_import",
        "candidate_id": candidate_id,
        "archive_manifest_path": str(source.resolve()),
        "archive_manifest_sha256": sha256(source),
        "strategy_name": raw.get("strategy_name"),
        "source": {
            "sqx_path": str(sqx.resolve()),
            "sqx_sha256": sha256(sqx),
            "mq5_path": str(mq5.resolve()),
            "mq5_sha256": sha256(mq5),
        },
        "artifacts": artifacts,
        "verdict_txt_path": str(verdict_txt.resolve()),
        "mt5_csv_path": str(mt5_csv.resolve()),
        "verdict": "VALIDADA",
        "baseline": baseline.__dict__,
    }


def _seal(manifest: dict[str, Any]) -> str:
    canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def persist(manifest: dict[str, Any], manifest_path: Path, dd_contract_pct: Decimal | None) -> str:
    """Persist evidence, optional baseline, and BACKTEST_VALIDATED atomically."""
    from sqlalchemy import select

    from core.config import get_settings
    from core.db.base import async_session_factory
    from core.db.enums import AssetAdmissionStatus, BaselineSource, PipelinePhase
    from core.db.models.accounts import Baseline, Bot
    from core.db.models.market import ImportArtifact
    from core.db.models.operations import OperationalAsset, OperationalAssetEvent
    from core.db.models.pipeline import PipelineCandidate
    from core.services.admin_imports import _artifact_metadata, _get_or_create_artifact

    if get_settings().deployment_profile != "operational":
        raise ValueError("operational profile required")
    source = manifest["source"]
    async with async_session_factory() as session, session.begin():
        candidate = await session.get(PipelineCandidate, manifest["candidate_id"])
        if candidate is None or candidate.current_phase != PipelinePhase.F3:
            raise ValueError("candidate_id must identify a current F3 candidate")
        bot = await session.get(Bot, candidate.bot_id)
        if bot is None:
            raise ValueError("candidate has no registered bot")
        asset = await session.scalar(select(OperationalAsset).where(
            OperationalAsset.sqx_sha256 == source["sqx_sha256"],
            OperationalAsset.mql5_sha256 == source["mq5_sha256"],
        ))
        if asset is None:
            raise ValueError("sealed source is not an operational asset")
        if asset.symbol != bot.market or asset.timeframe != bot.timeframe:
            raise ValueError("candidate bot does not match sealed asset symbol/timeframe")
        previous = list((await session.scalars(
            select(OperationalAssetEvent).where(OperationalAssetEvent.asset_id == asset.id)
        )).all())
        if any(
            event.evidence.get("archive_manifest_sha256") == manifest["archive_manifest_sha256"]
            and event.evidence.get("candidate_id") == candidate.id
            for event in previous
        ):
            return "already_recorded"

        parsed = manifest["baseline"]
        sqx_path = Path(source["sqx_path"])
        sqx_artifact = await _get_or_create_artifact(
            session, kind="SQX", path=sqx_path, payload=sqx_path.read_bytes(),
            parser_version=PARSER_VERSION,
            metadata=_artifact_metadata(
                sqx_path, provenance=manifest["provenance"], build=parsed["build"],
                symbol=parsed["symbol"], timeframe=parsed["timeframe"],
                backtest_from=parsed["backtest_from"], backtest_to=parsed["backtest_to"],
                trade_count=parsed["trade_count"],
            ),
        )
        baseline = await session.get(Baseline, bot.baseline_id) if bot.baseline_id else None
        baseline_created = False
        if baseline is not None:
            artifact = await session.get(ImportArtifact, baseline.artifact_id) if baseline.artifact_id else None
            if artifact is None or artifact.sha256.lower() != source["sqx_sha256"].lower():
                raise ValueError("candidate baseline does not reference the sealed SQX source")
        else:
            if dd_contract_pct is None or dd_contract_pct <= 0:
                raise ValueError("--dd-contract-pct is required to create a missing baseline")
            baseline = Baseline(
                bot_id=bot.id, source=BaselineSource.BACKTEST,
                profit_factor=parsed["profit_factor"], expectancy_r=parsed["expectancy_r"],
                sharpe=parsed["sharpe"], max_dd_pct=Decimal(str(parsed["max_dd_pct"])),
                win_rate=parsed["win_rate"], payoff=parsed["payoff"],
                avg_trade_duration_min=parsed["avg_trade_duration_min"],
                max_consec_losses=parsed["max_consec_losses"],
                expected_trades_30d=parsed["expected_trades_30d"],
                dd_contract_pct=dd_contract_pct, created_at=datetime.now(UTC), is_active=True,
                artifact_id=sqx_artifact.id,
            )
            session.add(baseline)
            await session.flush()
            bot.baseline_id = baseline.id
            baseline_created = True

        artifact_ids: list[int] = []
        for entry in manifest["artifacts"]:
            path = Path(entry["path"])
            artifact = await _get_or_create_artifact(
                session, kind="SQX_MT5_REPORT", path=path, payload=path.read_bytes(),
                parser_version=_PARSER_VERSION,
                metadata={
                    "archived_manifest_sha256": manifest["manifest_sha256"],
                    "sha256": entry["sha256"],
                    "role": "MT5_TESTER_DEALS" if path.suffix.lower() == ".csv" else "SUPPORTING_REPORT",
                },
            )
            artifact_ids.append(artifact.id)
        mq5_path = Path(source["mq5_path"])
        mq5_artifact = await _get_or_create_artifact(
            session, kind="MQL5", path=mq5_path, payload=mq5_path.read_bytes(),
            parser_version=_PARSER_VERSION,
            metadata={"archived_manifest_sha256": manifest["manifest_sha256"]},
        )
        manifest_artifact = await _get_or_create_artifact(
            session, kind="SQX_MT5_ARCHIVE_MAN", path=manifest_path,
            payload=manifest_path.read_bytes(), parser_version=_PARSER_VERSION,
            metadata={"candidate_id": candidate.id, "verdict": "VALIDADA"},
        )
        session.add(OperationalAssetEvent(
            asset_id=asset.id, status=AssetAdmissionStatus.BACKTEST_VALIDATED,
            reason="ARCHIVED_EVIDENCE_IMPORT",
            evidence={
                "archived_manifest_sha256": manifest["manifest_sha256"],
                "archive_manifest_sha256": manifest["archive_manifest_sha256"],
                "provenance": manifest["provenance"], "candidate_id": candidate.id,
                "baseline_id": baseline.id, "baseline_created": baseline_created,
                "source_sqx_artifact_id": sqx_artifact.id, "source_mq5_artifact_id": mq5_artifact.id,
                "manifest_artifact_id": manifest_artifact.id, "artifact_ids": artifact_ids,
                "verdict": "VALIDADA",
            }, occurred_at=datetime.now(UTC),
        ))
    return f"asset_id={asset.id} candidate_id={candidate.id} baseline_id={baseline.id} status=BACKTEST_VALIDATED"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dd-contract-pct", type=Decimal)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    manifest = build_import_manifest(args.evidence_dir.resolve(), args.candidate_id)
    manifest["manifest_sha256"] = _seal(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"verified archived evidence manifest={args.output}")
    if args.apply:
        print(asyncio.run(persist(manifest, args.output.resolve(), args.dd_contract_pct)))


if __name__ == "__main__":
    main()
