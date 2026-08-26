import json
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import fakeredis
import pandas as pd
import pytest
from sqlalchemy import select

from core.db.models.governance import CorrelationMatrix
from core.services.correlations import (
    CorrelationServiceConfig,
    TradePnl,
    build_daily_pnl_by_bot,
    classify_redundant_pairs,
    run_correlation_job,
)
from tests.factories import AccountFactory, BotFactory, IngestBatchFactory, TradeFactory

CONFIG = CorrelationServiceConfig(min_days_for_correlation=30, redundant_factor=3.0)


class TestBuildDailyPnlByBot:
    def test_sums_pnl_per_calendar_day(self) -> None:
        day = datetime(2026, 1, 1, tzinfo=UTC)
        trades = {
            1: [
                TradePnl(closed_at=day, net_pnl=Decimal("10")),
                TradePnl(closed_at=day + timedelta(hours=5), net_pnl=Decimal("5")),
                TradePnl(closed_at=day + timedelta(days=1), net_pnl=Decimal("-3")),
            ]
        }
        result = build_daily_pnl_by_bot(trades)
        series = result[1]
        assert series[pd.Timestamp("2026-01-01")] == pytest.approx(15.0)
        assert series[pd.Timestamp("2026-01-02")] == pytest.approx(-3.0)

    def test_bot_with_no_trades_yields_empty_series(self) -> None:
        result = build_daily_pnl_by_bot({1: []})
        assert result[1].empty


class TestClassifyRedundantPairs:
    def test_pair_far_above_mean_is_redundant(self) -> None:
        # 4 bots -> 6 pares: 1 par "medio gemelo" (0.9) y 5 pares bajos
        # (0.05) para que la media (~0.19) deje al par alto por encima de
        # 3x umbral (~0.57) sin que se arrastre a si misma hacia arriba.
        corr = pd.DataFrame(
            {
                1: [1.0, 0.9, 0.05, 0.05],
                2: [0.9, 1.0, 0.05, 0.05],
                3: [0.05, 0.05, 1.0, 0.05],
                4: [0.05, 0.05, 0.05, 1.0],
            },
            index=[1, 2, 3, 4],
        )
        result = classify_redundant_pairs(corr, redundant_factor=3.0)
        assert result[(1, 2)] is True
        assert result[(1, 3)] is False
        assert result[(3, 4)] is False

    def test_nan_correlation_is_never_redundant(self) -> None:
        corr = pd.DataFrame(
            {1: [1.0, float("nan")], 2: [float("nan"), 1.0]},
            index=[1, 2],
        )
        result = classify_redundant_pairs(corr, redundant_factor=3.0)
        assert result[(1, 2)] is False

    def test_single_bot_has_no_pairs(self) -> None:
        corr = pd.DataFrame({1: [1.0]}, index=[1])
        assert classify_redundant_pairs(corr, redundant_factor=3.0) == {}


async def _bot_with_daily_trades(
    db_session: object, account_id: int, days: int, pnl_by_day: list[Decimal], now: datetime
) -> object:
    bot = BotFactory(account_id=account_id)
    db_session.add(bot)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    batch = IngestBatchFactory(account_id=account_id)
    db_session.add(batch)  # type: ignore[attr-defined]
    await db_session.flush()  # type: ignore[attr-defined]
    for i in range(days):
        closed_at = now - timedelta(days=days - i)
        db_session.add(  # type: ignore[attr-defined]
            TradeFactory(
                bot_id=bot.id,
                account_id=account_id,
                magic_number=bot.magic_number,
                open_time=closed_at - timedelta(hours=1),
                close_time=closed_at,
                close_price=Decimal("1.0"),
                profit=pnl_by_day[i % len(pnl_by_day)],
                ingest_batch_id=batch.id,
            )
        )
    await db_session.flush()  # type: ignore[attr-defined]
    return bot


class TestRunCorrelationJob:
    async def test_excludes_bots_with_insufficient_history(self, db_session: object) -> None:
        account = AccountFactory()
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        now = datetime.now(UTC)

        long_history = [Decimal("10"), Decimal("-5"), Decimal("3")]
        bot_a = await _bot_with_daily_trades(db_session, account.id, 35, long_history, now)
        bot_b = await _bot_with_daily_trades(db_session, account.id, 35, long_history, now)
        bot_short = await _bot_with_daily_trades(db_session, account.id, 5, long_history, now)

        redis = fakeredis.FakeAsyncRedis()
        await run_correlation_job(db_session, redis, CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        rows = (
            (await db_session.execute(select(CorrelationMatrix)))  # type: ignore[attr-defined]
            .scalars()
            .all()
        )
        pairs = {(r.bot_a_id, r.bot_b_id) for r in rows}
        assert (min(bot_a.id, bot_b.id), max(bot_a.id, bot_b.id)) in pairs
        assert not any(bot_short.id in pair for pair in pairs)
        await redis.aclose()

    async def test_perfectly_correlated_bots_flagged_redundant_and_cached(
        self, db_session: object
    ) -> None:
        account = AccountFactory()
        db_session.add(account)  # type: ignore[attr-defined]
        await db_session.flush()  # type: ignore[attr-defined]
        now = datetime.now(UTC)

        pattern = [Decimal("10"), Decimal("-4"), Decimal("2"), Decimal("-1"), Decimal("7")]
        twin_a = await _bot_with_daily_trades(db_session, account.id, 35, pattern, now)
        twin_b = await _bot_with_daily_trades(db_session, account.id, 35, pattern, now)

        redis = fakeredis.FakeAsyncRedis()
        await run_correlation_job(db_session, redis, CONFIG, now)  # type: ignore[arg-type]
        await db_session.commit()  # type: ignore[attr-defined]

        key = min(twin_a.id, twin_b.id), max(twin_a.id, twin_b.id)
        row = (
            await db_session.execute(  # type: ignore[attr-defined]
                select(CorrelationMatrix).where(
                    CorrelationMatrix.bot_a_id == key[0], CorrelationMatrix.bot_b_id == key[1]
                )
            )
        ).scalar_one()
        assert row.correlation == pytest.approx(1.0, abs=1e-6)
        assert not math.isnan(row.correlation)

        cache_keys = await redis.keys("corr:*")
        assert cache_keys
        cached = json.loads(await redis.get(cache_keys[0]))
        assert any(entry["bot_a_id"] == key[0] and entry["bot_b_id"] == key[1] for entry in cached)
        await redis.aclose()
