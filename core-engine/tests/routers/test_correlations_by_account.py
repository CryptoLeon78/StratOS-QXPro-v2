"""ADR 0013: matriz observada por cuenta, umbral de inclusion 10 dias u 10
operaciones y pares marcados como baja confianza."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from core.db.enums import CorrelationSource
from core.db.models.governance import CorrelationSnapshotPair
from core.services.correlations import (
    CorrelationServiceConfig,
    run_mt5_real_correlation_snapshot,
    run_mt5_real_correlation_snapshots_by_account,
)
from tests.factories import AccountFactory, BotFactory, IngestBatchFactory, TradeFactory

CONFIG = CorrelationServiceConfig()
NOW = datetime(2026, 9, 29, 12, tzinfo=UTC)


async def _bot_with_trades(
    session: AsyncSession, account_id: int, batch_id: int, *, days: int, per_day: int, seed: int
) -> int:
    bot = BotFactory(account_id=account_id)
    session.add(bot)
    await session.flush()
    for day in range(days):
        for n in range(per_day):
            profit = Decimal((seed * (day + 3) + n * 7) % 23 - 9)
            session.add(
                TradeFactory(
                    account_id=account_id,
                    bot_id=bot.id,
                    magic_number=bot.magic_number,
                    ingest_batch_id=batch_id,
                    open_time=NOW - timedelta(days=day + 1, hours=2),
                    close_time=NOW - timedelta(days=day + 1),
                    profit=profit,
                )
            )
    await session.flush()
    return int(bot.id)


async def _account(session: AsyncSession) -> tuple[int, int]:
    account = AccountFactory()
    session.add(account)
    await session.flush()
    batch = IngestBatchFactory(account_id=account.id)
    session.add(batch)
    await session.flush()
    return int(account.id), int(batch.id)


async def test_matrix_is_computed_per_account_with_the_lower_threshold(
    db_session: AsyncSession,
) -> None:
    a, batch_a = await _account(db_session)
    b, batch_b = await _account(db_session)
    a1 = await _bot_with_trades(db_session, a, batch_a, days=12, per_day=1, seed=3)
    a2 = await _bot_with_trades(db_session, a, batch_a, days=12, per_day=1, seed=5)
    b1 = await _bot_with_trades(db_session, b, batch_b, days=12, per_day=1, seed=7)
    b2 = await _bot_with_trades(db_session, b, batch_b, days=12, per_day=1, seed=11)

    results = await run_mt5_real_correlation_snapshots_by_account(db_session, CONFIG, NOW)

    assert len(results) == 2
    by_account = {r.snapshot.account_scope["account_id"]: r.snapshot for r in results}
    assert set(by_account) == {a, b}
    for account_id, expected in ((a, {a1, a2}), (b, {b1, b2})):
        snapshot = by_account[account_id]
        assert snapshot.status == "COMPLETED"
        pairs = (
            (
                await db_session.execute(
                    select(CorrelationSnapshotPair).where(
                        CorrelationSnapshotPair.snapshot_id == snapshot.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert {p.bot_a_id for p in pairs} | {p.bot_b_id for p in pairs} == expected
        assert all(p.n_obs == 12 for p in pairs)


async def test_inclusion_rule_is_days_or_trades(db_session: AsyncSession) -> None:
    a, batch = await _account(db_session)
    by_days = await _bot_with_trades(db_session, a, batch, days=10, per_day=1, seed=3)
    by_trades = await _bot_with_trades(db_session, a, batch, days=2, per_day=5, seed=5)
    too_little = await _bot_with_trades(db_session, a, batch, days=3, per_day=1, seed=9)

    result = await run_mt5_real_correlation_snapshot(db_session, CONFIG, NOW, a)

    pairs = (
        (
            await db_session.execute(
                select(CorrelationSnapshotPair).where(
                    CorrelationSnapshotPair.snapshot_id == result.snapshot.id
                )
            )
        )
        .scalars()
        .all()
    )
    included = {p.bot_a_id for p in pairs} | {p.bot_b_id for p in pairs}
    assert by_days in included and by_trades in included
    assert too_little not in included


async def test_api_marks_low_confidence_and_lists_uncovered_bots(
    api_client: AsyncClient, db_connection: AsyncConnection
) -> None:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    a, batch = await _account(session)
    await _bot_with_trades(session, a, batch, days=12, per_day=1, seed=3)
    await _bot_with_trades(session, a, batch, days=12, per_day=1, seed=5)
    thin = await _bot_with_trades(session, a, batch, days=3, per_day=1, seed=9)
    await run_mt5_real_correlation_snapshot(session, CONFIG, datetime.now(UTC), a)
    await session.commit()

    latest = await api_client.get(
        f"/api/v1/portfolio/correlations/latest?account_id={a}&source={CorrelationSource.MT5_REAL.value}"
    )
    pairs = latest.json()["pairs"]
    assert len(pairs) == 1
    assert pairs[0]["n_obs"] == 12 and pairs[0]["low_confidence"] is True

    coverage = (
        await api_client.get(f"/api/v1/portfolio/correlations/coverage?account_id={a}")
    ).json()
    by_bot = {row["bot_id"]: row for row in coverage}
    assert by_bot[thin]["included"] is False
    assert by_bot[thin]["reason"] == "HISTORIA_INSUFICIENTE"
    assert sum(row["included"] for row in coverage) == 2

    other = await api_client.get(f"/api/v1/portfolio/correlations/latest?account_id={a + 999}")
    assert other.status_code == 404


@pytest.mark.parametrize("source", ["MT5_BACKTEST"])
async def test_backtest_coverage_without_evidence_is_explicit(
    api_client: AsyncClient, db_connection: AsyncConnection, source: str
) -> None:
    session = AsyncSession(
        bind=db_connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    a, _ = await _account(session)
    bot = BotFactory(account_id=a)
    session.add(bot)
    await session.commit()

    coverage = (
        await api_client.get(
            f"/api/v1/portfolio/correlations/coverage?account_id={a}&source={source}"
        )
    ).json()

    assert [(row["bot_id"], row["included"], row["reason"]) for row in coverage] == [
        (bot.id, False, "SIN_EVIDENCIA_BACKTEST")
    ]
