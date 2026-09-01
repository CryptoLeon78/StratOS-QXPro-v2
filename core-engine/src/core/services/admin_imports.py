"""Servicios de importación administrativa local; no están registrados como rutas HTTP."""

from __future__ import annotations

import csv
import hashlib
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.enums import BaselineSource
from core.db.models.accounts import Baseline, Bot
from core.db.models.market import FxRate, ImportArtifact
from core.services.sqx_baseline_parser import PARSER_VERSION, parse_sqx144_baseline


def _artifact_metadata(path: Path, **metadata: object) -> dict[str, object]:
    return {"source_filename": path.name, **metadata}


async def _get_or_create_artifact(
    session: AsyncSession,
    *,
    kind: str,
    path: Path,
    payload: bytes,
    parser_version: str,
    metadata: dict[str, object],
) -> ImportArtifact:
    digest = hashlib.sha256(payload).hexdigest()
    existing = (
        await session.execute(
            select(ImportArtifact).where(
                ImportArtifact.kind == kind, ImportArtifact.sha256 == digest
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    artifact = ImportArtifact(
        kind=kind,
        sha256=digest,
        original_filename=path.name,
        source_path=str(path.resolve()),
        parser_version=parser_version,
        metadata_json=metadata,
        payload=payload,
        imported_at=datetime.now(UTC),
    )
    session.add(artifact)
    await session.flush()
    return artifact


async def import_sqx_baseline(
    session: AsyncSession, *, bot_id: int, path: Path, dd_contract_pct: Decimal
) -> Baseline:
    """Inserta una baseline nueva; nunca actualiza una baseline anterior."""
    if dd_contract_pct <= 0:
        raise ValueError("dd_contract_pct debe ser positivo")
    bot = await session.get(Bot, bot_id)
    if bot is None:
        raise ValueError("bot_id inexistente")
    payload = path.read_bytes()
    parsed = parse_sqx144_baseline(payload)
    artifact = await _get_or_create_artifact(
        session,
        kind="SQX",
        path=path,
        payload=payload,
        parser_version=PARSER_VERSION,
        metadata=_artifact_metadata(
            path,
            build=parsed.build,
            symbol=parsed.symbol,
            timeframe=parsed.timeframe,
            backtest_from=parsed.backtest_from,
            backtest_to=parsed.backtest_to,
            trade_count=parsed.trade_count,
        ),
    )
    baseline = Baseline(
        bot_id=bot.id,
        source=BaselineSource.BACKTEST,
        profit_factor=parsed.profit_factor,
        expectancy_r=parsed.expectancy_r,
        sharpe=parsed.sharpe,
        max_dd_pct=Decimal(str(parsed.max_dd_pct)),
        win_rate=parsed.win_rate,
        payoff=parsed.payoff,
        avg_trade_duration_min=parsed.avg_trade_duration_min,
        max_consec_losses=parsed.max_consec_losses,
        expected_trades_30d=parsed.expected_trades_30d,
        dd_contract_pct=dd_contract_pct,
        created_at=datetime.now(UTC),
        is_active=True,
        artifact_id=artifact.id,
    )
    # El puntero del bot define la baseline vigente; las filas anteriores se
    # conservan intactas para no romper el contrato append-only.
    session.add(baseline)
    await session.flush()
    bot.baseline_id = baseline.id
    return baseline


async def import_fx_csv(session: AsyncSession, *, path: Path) -> int:
    """Importa CSV sellado ts,base,quote,rate. Conflictos de tasa fallan cerrados."""
    payload = path.read_bytes()
    try:
        rows = list(csv.DictReader(payload.decode("utf-8-sig").splitlines()))
    except UnicodeDecodeError as exc:
        raise ValueError("CSV FX debe estar codificado UTF-8") from exc
    if not rows or set(rows[0]) != {"ts", "base", "quote", "rate"}:
        raise ValueError("CSV FX requiere cabecera exacta ts,base,quote,rate")
    parsed: list[tuple[datetime, str, str, Decimal]] = []
    for row in rows:
        try:
            ts = datetime.fromisoformat(row["ts"].replace("Z", "+00:00"))
            rate = Decimal(row["rate"])
        except (ValueError, InvalidOperation, AttributeError) as exc:
            raise ValueError("fila FX inválida") from exc
        base, quote = row["base"].upper(), row["quote"].upper()
        if ts.tzinfo is None or len(base) != 3 or len(quote) != 3 or base == quote or rate <= 0:
            raise ValueError("fila FX fuera de contrato")
        parsed.append((ts.astimezone(UTC), base, quote, rate))
    artifact = await _get_or_create_artifact(
        session,
        kind="FX_CSV",
        path=path,
        payload=payload,
        parser_version="fx-csv-v1",
        metadata=_artifact_metadata(path, row_count=len(parsed)),
    )
    inserted = 0
    for ts, base, quote, rate in parsed:
        existing = await session.get(FxRate, {"ts": ts, "base": base, "quote": quote})
        if existing is not None:
            if existing.rate != rate:
                raise ValueError(f"conflicto FX para {base}/{quote} en {ts.isoformat()}")
            continue
        session.add(FxRate(ts=ts, base=base, quote=quote, rate=rate, artifact_id=artifact.id))
        inserted += 1
    return inserted
