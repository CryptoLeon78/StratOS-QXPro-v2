"""TDD G11: FX local auditado, idempotencia y conflicto fail-closed."""

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.models.market import FxRate, ImportArtifact
from core.services.admin_imports import import_fx_csv


async def test_fx_import_keeps_artifact_and_is_idempotent(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    path = tmp_path / "fx.csv"
    path.write_text("ts,base,quote,rate\n2026-08-01T00:00:00Z,USD,EUR,0.92\n", encoding="utf-8")
    assert await import_fx_csv(db_session, path=path) == 1
    await db_session.flush()
    assert await import_fx_csv(db_session, path=path) == 0
    assert len((await db_session.execute(select(FxRate))).scalars().all()) == 1
    artifact = (await db_session.execute(select(ImportArtifact))).scalar_one()
    assert artifact.kind == "FX_CSV"


async def test_fx_import_rejects_conflicting_rate(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_text("ts,base,quote,rate\n2026-08-01T00:00:00Z,USD,EUR,0.92\n", encoding="utf-8")
    second.write_text("ts,base,quote,rate\n2026-08-01T00:00:00Z,USD,EUR,0.91\n", encoding="utf-8")
    await import_fx_csv(db_session, path=first)
    with pytest.raises(ValueError, match="conflicto FX"):
        await import_fx_csv(db_session, path=second)
